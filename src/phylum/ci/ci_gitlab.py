"""Define an implementation for the GitLab CI platform.

GitLab References:
  * https://docs.gitlab.com/ee/ci/
  * https://docs.gitlab.com/ee/ci/docker/using_docker_images.html
  * https://docs.gitlab.com/ee/ci/variables/predefined_variables.html
  * https://docs.gitlab.com/ee/ci/jobs/ci_job_token.html
  * https://docs.gitlab.com/ee/api/notes.html#merge-requests
"""

from argparse import Namespace
from functools import cached_property, lru_cache
from inspect import cleandoc
import os
from pathlib import Path
import re
import shlex
import subprocess
from typing import Optional

import requests

from phylum.ci.ci_base import CIBase
from phylum.ci.git import git_branch_exists, git_default_branch_name, git_fetch, git_remote
from phylum.constants import PHYLUM_HEADER, PHYLUM_USER_AGENT, REQ_TIMEOUT
from phylum.exceptions import pprint_subprocess_error
from phylum.logger import LOG


@lru_cache(maxsize=1)
def is_in_mr() -> bool:
    """Indicate if the integration is operating in the context of a merge request pipeline.

    GitLab CI allows for the possibility of running pipelines in different contexts:
      * On every push, for the last commit in the push (e.g., branch pipelines)
      * For merge requests (e.g., merge request pipelines)

    Knowing when the context is within a merge request helps to ensure the logic used
    to determine the dependency file changes is correct. It also helps to ensure output
    is not attempted to be posted when NOT in the context of a review.
    """
    # References:
    # https://github.com/watson/ci-info/blob/master/vendors.json
    # https://docs.gitlab.com/ee/ci/pipelines/merge_request_pipelines.html
    # docs.gitlab.com/ee/ci/variables/predefined_variables.html#predefined-variables-for-merge-request-pipelines
    return bool(os.getenv("CI_MERGE_REQUEST_ID"))


class CIGitLab(CIBase):
    """Provide methods for a GitLab CI environment."""

    def __init__(self, args: Namespace) -> None:  # noqa: D107 ; the base __init__ docstring is better here
        super().__init__(args)
        self.ci_platform_name = "GitLab CI"
        if is_in_mr():
            LOG.debug("Pipeline context: merge request pipeline")
        else:
            LOG.debug("Pipeline context: branch pipeline")

    def _check_prerequisites(self) -> None:
        """Ensure the necessary prerequisites are met and bail when they aren't.

        These are the current prerequisites for operating within a GitLab CI Environment:
          * The environment must actually be within GitLab CI
          * A GitLab token providing API access is available when operating in an MR pipeline
            * Unless comment generation is skipped
        """
        super()._check_prerequisites()

        # References:
        # https://github.com/watson/ci-info/blob/master/vendors.json
        # https://docs.gitlab.com/ee/ci/variables/predefined_variables.html
        if os.getenv("GITLAB_CI") != "true":
            msg = "Must be working within the GitLab CI environment"
            raise SystemExit(msg)

        # A GitLab token with API access is required to use the API (e.g., to post notes/comments).
        # This can be a personal, project, or group access token...and possibly some other types as well.
        # See the GitLab Token Overview Documentation for info: https://docs.gitlab.com/ee/security/token_overview.html
        gitlab_token = os.getenv("GITLAB_TOKEN", "")
        if not gitlab_token and is_in_mr() and not self.skip_comments:
            msg = "A GitLab token with API access must be set at `GITLAB_TOKEN`"
            raise SystemExit(msg)
        self._gitlab_token = gitlab_token

    @property
    def gitlab_token(self) -> str:
        """Get the GitLab token (e.g., personal, project, group, etc.)."""
        return self._gitlab_token

    @cached_property
    def phylum_label(self) -> str:
        """Get a custom label for use when submitting jobs for analysis."""
        if is_in_mr():
            mr_iid = os.getenv("CI_MERGE_REQUEST_IID", "unknown-IID")
            mr_src_branch = os.getenv("CI_MERGE_REQUEST_SOURCE_BRANCH_NAME", "unknown-branch")
            label = f"{self.ci_platform_name}_MR#{mr_iid}_{mr_src_branch}"
        else:
            current_branch = os.getenv("CI_COMMIT_BRANCH", "unknown-branch")
            label = f"{self.ci_platform_name}_{current_branch}_{self.depfile_hash_object}"

        label = re.sub(r"\s+", "-", label)
        return label

    @cached_property
    def common_ancestor_commit(self) -> Optional[str]:
        """Find the common ancestor commit.

        Some pre-defined variables are used: https://docs.gitlab.com/ee/ci/variables/predefined_variables.html
        """
        remote = git_remote()

        if is_in_mr():
            common_commit = os.getenv("CI_MERGE_REQUEST_DIFF_BASE_SHA")
            return common_commit

        src_branch_name = os.getenv("CI_COMMIT_BRANCH")
        if not src_branch_name:
            msg = "The CI_COMMIT_BRANCH environment variable must exist and be set"
            raise SystemExit(msg)
        src_branch = f"refs/remotes/{remote}/{src_branch_name}"

        # The default branch name is used instead of `HEAD` because of a GitLab runner bug where HEAD is not available:
        # https://gitlab.com/gitlab-org/gitlab-runner/-/issues/4078
        default_branch_name = os.getenv("CI_DEFAULT_BRANCH")
        if not default_branch_name:
            default_branch_name = git_default_branch_name(remote)
        default_branch = f"refs/remotes/{remote}/{default_branch_name}"

        project_dir = Path(os.getenv("CI_PROJECT_DIR", ".")).resolve()
        if not git_branch_exists(default_branch, git_c_path=project_dir):
            LOG.warning("The default remote branch is not available. Attempting to fetch it...")
            git_fetch(repo=remote, ref=default_branch_name, git_c_path=project_dir)

        if src_branch == default_branch:
            LOG.warning("Source branch is same as default branch. Proceeding with analysis of all dependencies ...")
            self._force_analysis = True
            self._all_deps = True

        # This is a best effort attempt since it is finding the merge base between the current commit
        # and the default branch instead of finding the exact commit from which the branch was created.
        cmd = ["git", "merge-base", src_branch, default_branch]
        LOG.debug("Finding common ancestor commit with command: %s", shlex.join(cmd))
        try:
            common_commit = subprocess.run(cmd, check=True, capture_output=True, text=True).stdout.strip()  # noqa: S603
        except subprocess.CalledProcessError as err:
            msg = """
                The common ancestor commit could not be found.
                Ensure the git strategy is set to `clone` for repo checkouts:
                https://docs.gitlab.com/ee/ci/runners/configure_runners.html#git-strategy"""
            pprint_subprocess_error(err)
            LOG.warning(cleandoc(msg))
            common_commit = None

        return common_commit

    @property
    def is_any_depfile_changed(self) -> bool:
        """Predicate for detecting if any dependency file has changed."""
        diff_base_sha = self.common_ancestor_commit
        LOG.debug("The common ancestor commit: %s", diff_base_sha)

        # Assume no change when there isn't enough information to tell
        if diff_base_sha is None:
            return False

        err_msg = """
            Consider changing the `GIT_DEPTH` variable in CI settings to
            clone/fetch more branch history. For more info, reference:
            https://docs.gitlab.com/ee/ci/large_repositories/index.html#shallow-cloning"""
        self.update_depfiles_change_status(diff_base_sha, err_msg)

        return any(depfile.is_depfile_changed for depfile in self.depfiles)

    @property
    def phylum_comment_exists(self) -> bool:
        """Predicate for detecting whether a Phylum-generated note (comment) exists."""
        return bool(self.most_recent_phylum_note)

    @property
    def repo_url(self) -> Optional[str]:
        """Get the repository URL for reference in Phylum project metadata."""
        # Ref: https://docs.gitlab.com/ee/ci/variables/predefined_variables.html
        return os.getenv("CI_PROJECT_URL")

    def post_output(self) -> None:
        """Post the output of the analysis.

        Post output directly in the logs regardless of the pipeline context.
        Optionally post output as a note (comment) on the GitLab CI Merge
        Request (MR) when operating in a merge request pipeline.
        """
        super().post_output()

        if not is_in_mr():
            # Can't post the output to the MR when there is no MR
            return

        if self.skip_comments:
            LOG.debug("Posting analysis output as notes on the merge request was disabled.")
            return

        LOG.info("Checking merge request notes for existing content to avoid duplication ...")
        if self.most_recent_phylum_note:
            LOG.debug("The most recently posted Phylum merge request note was found.")
            if self.most_recent_phylum_note == self.analysis_report:
                LOG.debug("It contains the same content as the current analysis. Nothing to do.")
                return
            LOG.debug("It does not contain the same content as the current analysis.")
        else:
            LOG.debug("No existing Phylum merge request notes found.")

        # If we got here, then the most recent Phylum MR note does not match the current analysis output or
        # there were no Phylum MR notes. Either way, create a new MR note.
        url = get_notes_url()
        data = {"body": self.analysis_report}
        LOG.info("Creating new merge request note with POST URL: %s ...", url)
        response = requests.post(url, data=data, headers=self.headers, timeout=REQ_TIMEOUT)
        response.raise_for_status()

    @property
    def headers(self) -> dict:
        """Provide headers to use when making GitLab API calls."""
        headers = {
            "User-Agent": PHYLUM_USER_AGENT,
            "PRIVATE-TOKEN": self.gitlab_token,
        }
        return headers

    @cached_property
    def most_recent_phylum_note(self) -> Optional[str]:
        """Get the raw text of the most recently posted Phylum-generated note.

        Return `None` when one does not exist.
        """
        if not is_in_mr():
            # It only makes sense to reference this property in the context of an MR
            return None

        if self.skip_comments:
            LOG.debug("Posting analysis output as notes on the merge request was disabled.")
            if not self.gitlab_token:
                LOG.debug("GitLab API token not available. Unable to look for notes.")
                return None
            LOG.debug("GitLab API token available but possibly invalid. Attempting use ...")

        url = get_notes_url()
        LOG.info("Getting all current merge request notes with GET URL: %s ...", url)
        req = requests.get(url, headers=self.headers, timeout=REQ_TIMEOUT)
        req.raise_for_status()
        mr_notes: list = req.json()

        if not mr_notes:
            LOG.debug("No existing merge request notes found.")
            return None

        # NOTE: The API defaults to returning the notes in descending order by the `created_at` field.
        #       Detecting Phylum notes is done simply by looking for notes that start with a known string value.
        #       We only care about the most recent Phylum note.
        mr_note: dict
        for mr_note in mr_notes:
            note_body: str = mr_note.get("body", "")
            if note_body.lstrip().startswith(PHYLUM_HEADER.strip()):
                # The most recently posted Phylum merge request note was found
                return note_body

        # No existing Phylum merge request notes found
        return None


def get_notes_url() -> str:
    """Get the notes API URL and return it."""
    if not is_in_mr():
        msg = "Must be working in the context of a merge request pipeline"
        raise SystemExit(msg)
    # API Reference: https://docs.gitlab.com/ee/api/notes.html#merge-requests
    gitlab_api_v4_root_url = os.getenv("CI_API_V4_URL")
    mr_project_id = os.getenv("CI_MERGE_REQUEST_PROJECT_ID")
    mr_iid = os.getenv("CI_MERGE_REQUEST_IID")
    # This is the same endpoint for listing all MR notes (GET) and creating new ones (POST)
    base_mr_notes_api_endpoint = f"/projects/{mr_project_id}/merge_requests/{mr_iid}/notes"
    url = f"{gitlab_api_v4_root_url}{base_mr_notes_api_endpoint}"
    return url
