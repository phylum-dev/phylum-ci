"""Define an implementation for the GitLab CI platform.

GitLab References:
  * https://docs.gitlab.com/ci/
  * https://docs.gitlab.com/ci/docker/using_docker_images
  * https://docs.gitlab.com/ci/variables/predefined_variables
  * https://docs.gitlab.com/ci/jobs/ci_job_token
  * https://docs.gitlab.com/api/notes/#merge-requests
"""

from argparse import Namespace
from functools import cached_property, lru_cache
from inspect import cleandoc
import os
from pathlib import Path
import re
import shlex
import subprocess

import requests

from phylum.ci.ci_base import CIBase
from phylum.ci.common import ReturnCode
from phylum.ci.git import git_branch_exists, git_default_branch_name, git_fetch, git_remote
from phylum.constants import PHYLUM_HEADER, PHYLUM_USER_AGENT, REQ_TIMEOUT
from phylum.exceptions import pprint_subprocess_error
from phylum.logger import LOG


@lru_cache(maxsize=1)
def is_in_mr_pipeline() -> bool:
    """Indicate if the integration is operating in the context of a merge request pipeline.

    GitLab CI allows for the possibility of running pipelines in different contexts:
      * For the last commit in a push to a branch (branch pipelines)
      * For merge requests (merge request pipelines)
      * When a new Git tag is pushed (tag pipelines)

    Knowing when the context is within a merge request helps to ensure the logic used
    to determine the dependency file changes is correct. It also helps to ensure output
    is not attempted to be posted when NOT in the context of a review.
    """
    # References:
    # https://github.com/watson/ci-info/blob/master/vendors.json
    # https://docs.gitlab.com/ci/pipelines/merge_request_pipelines
    # https://docs.gitlab.com/ci/variables/predefined_variables/#predefined-variables-for-merge-request-pipelines
    return bool(os.getenv("CI_MERGE_REQUEST_ID"))


@lru_cache(maxsize=1)
def is_in_tag_pipeline() -> bool:
    """Indicate if the integration is operating in the context of a tag pipeline.

    GitLab CI allows for the possibility of running pipelines in different contexts:
      * For the last commit in a push to a branch (branch pipelines)
      * For merge requests (merge request pipelines)
      * When a new Git tag is pushed (tag pipelines)

    Knowing when the context is within a tag pipeline helps to ensure the logic used
    to determine the dependency file changes is correct. It also helps to ensure output
    is not attempted to be posted when NOT in the context of a review.
    """
    # References:
    # https://docs.gitlab.com/ci/pipelines/pipeline_types/#tag-pipeline
    # https://docs.gitlab.com/ci/variables/predefined_variables/#predefined-variables
    return bool(os.getenv("CI_COMMIT_TAG"))


@lru_cache(maxsize=1)
def is_in_branch_pipeline() -> bool:
    """Indicate if the integration is operating in the context of a branch pipeline.

    GitLab CI allows for the possibility of running pipelines in different contexts:
      * For the last commit in a push to a branch (branch pipelines)
      * For merge requests (merge request pipelines)
      * When a new Git tag is pushed (tag pipelines)

    Knowing when the context is within a branch pipeline helps to ensure the logic used
    to determine the dependency file changes is correct. It also helps to ensure output
    is not attempted to be posted when NOT in the context of a review.
    """
    # References:
    # https://docs.gitlab.com/ci/pipelines/pipeline_types/#branch-pipeline
    # https://docs.gitlab.com/ci/variables/predefined_variables/#predefined-variables
    return bool(os.getenv("CI_COMMIT_BRANCH"))


class CIGitLab(CIBase):
    """Provide methods for a GitLab CI environment."""

    def __init__(self, args: Namespace) -> None:  # noqa: D107 ; the base __init__ docstring is better here
        super().__init__(args)
        self.ci_platform_name = "GitLab CI"
        if is_in_mr_pipeline():
            LOG.debug("Pipeline context: merge request pipeline")
        elif is_in_tag_pipeline():
            LOG.debug("Pipeline context: tag pipeline")
        elif is_in_branch_pipeline():
            LOG.debug("Pipeline context: branch pipeline")

    def _check_prerequisites(self) -> None:
        """Ensure the necessary prerequisites are met and bail when they aren't.

        These are the current prerequisites for operating within a GitLab CI Environment:
          * The environment must actually be within GitLab CI
          * Must be operating within the context of a tag, branch, or merge request pipeline
          * A GitLab token providing API access is available when operating in an MR pipeline
            * Unless comment generation is skipped
        """
        super()._check_prerequisites()

        # References:
        # https://github.com/watson/ci-info/blob/master/vendors.json
        # https://docs.gitlab.com/ci/variables/predefined_variables
        if os.getenv("GITLAB_CI") != "true":
            msg = "Must be working within the GitLab CI environment"
            raise SystemExit(msg)

        # While other pipeline types *may* work, they aren't explicitly supported.
        # This check will prevent undocumented pipeline types from being used.
        if not (is_in_mr_pipeline() or is_in_tag_pipeline() or is_in_branch_pipeline()):
            msg = "Must use a supported pipeline type: branch, tag, or merge request"
            raise SystemExit(msg)

        # A GitLab token with API access is required to use the API (e.g., to post notes/comments).
        # This can be a personal, project, or group access token...and possibly some other types as well.
        # See the GitLab Token Overview Documentation for info: https://docs.gitlab.com/security/tokens
        gitlab_token = os.getenv("GITLAB_TOKEN", "")
        if not gitlab_token and is_in_mr_pipeline() and not self.skip_comments:
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
        if is_in_mr_pipeline():
            mr_iid = os.getenv("CI_MERGE_REQUEST_IID", "unknown-IID")
            mr_src_branch = os.getenv("CI_MERGE_REQUEST_SOURCE_BRANCH_NAME", "unknown-branch")
            label = f"{self.ci_platform_name}_MR#{mr_iid}_{mr_src_branch}"
        elif is_in_tag_pipeline():
            tag_name = os.getenv("CI_COMMIT_TAG", "unknown-tag")
            label = f"{self.ci_platform_name}_tag_{tag_name}"
        elif is_in_branch_pipeline():
            current_branch = os.getenv("CI_COMMIT_BRANCH", "unknown-branch")
            label = f"{self.ci_platform_name}_{current_branch}_{self.depfile_hash_object}"

        label = re.sub(r"\s+", "-", label)
        return label

    @cached_property
    def common_ancestor_commit(self) -> str | None:
        """Find the common ancestor commit.

        Some pre-defined variables are used: https://docs.gitlab.com/ci/variables/predefined_variables
        """
        remote = git_remote()

        if is_in_mr_pipeline():
            common_commit = os.getenv("CI_MERGE_REQUEST_DIFF_BASE_SHA")
            return common_commit

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

        if is_in_tag_pipeline():
            tag_name = os.getenv("CI_COMMIT_TAG")
            if not tag_name:
                msg = "The CI_COMMIT_TAG environment variable must exist and be set"
                raise SystemExit(msg)
            pipeline_trigger_commit_ref = f"refs/tags/{tag_name}"
            LOG.warning("In tag pipeline. Proceeding with analysis of all dependencies ...")
            self._force_analysis = True
            self._all_deps = True
        else:
            # Must be in a branch pipeline.
            # This is a best effort attempt since it will find the merge base between the current commit
            # and the default branch instead of finding the exact commit from which the branch was created.
            src_branch_name = os.getenv("CI_COMMIT_BRANCH")
            if not src_branch_name:
                msg = "The CI_COMMIT_BRANCH environment variable must exist and be set"
                raise SystemExit(msg)
            pipeline_trigger_commit_ref = f"refs/remotes/{remote}/{src_branch_name}"

            if pipeline_trigger_commit_ref == default_branch:
                LOG.warning("Source branch is same as default branch. Proceeding with analysis of all dependencies ...")
                self._force_analysis = True
                self._all_deps = True

        common_commit = git_merge_base(pipeline_trigger_commit_ref, default_branch)
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
            docs.gitlab.com/ci/pipelines/settings/#limit-the-number-of-changes-fetched-during-clone"""
        self._update_depfiles_change_status(diff_base_sha, err_msg)

        return any(depfile.is_depfile_changed for depfile in self.depfiles)

    @property
    def phylum_comment_exists(self) -> bool:
        """Predicate for detecting whether a Phylum-generated note (comment) exists."""
        return bool(self.most_recent_phylum_note)

    @property
    def repo_url(self) -> str | None:
        """Get the repository URL for reference in Phylum project metadata."""
        # Ref: https://docs.gitlab.com/ci/variables/predefined_variables
        return os.getenv("CI_PROJECT_URL")

    def post_output(self) -> None:
        """Post the output of the analysis.

        Post output directly in the logs regardless of the pipeline context.
        Optionally post output as a note (comment) on the GitLab CI Merge
        Request (MR) when operating in a merge request pipeline.
        """
        super().post_output()

        if not is_in_mr_pipeline():
            # Can't post the output to the MR when there is no MR
            return

        if self.returncode == ReturnCode.SUCCESS:
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
    def most_recent_phylum_note(self) -> str | None:
        """Get the raw text of the most recently posted Phylum-generated note.

        Return `None` when one does not exist.
        """
        if not is_in_mr_pipeline():
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
    if not is_in_mr_pipeline():
        msg = "Must be working in the context of a merge request pipeline"
        raise SystemExit(msg)
    # API Reference: https://docs.gitlab.com/api/notes/#merge-requests
    gitlab_api_v4_root_url = os.getenv("CI_API_V4_URL")
    mr_project_id = os.getenv("CI_MERGE_REQUEST_PROJECT_ID")
    mr_iid = os.getenv("CI_MERGE_REQUEST_IID")
    # This is the same endpoint for listing all MR notes (GET) and creating new ones (POST)
    base_mr_notes_api_endpoint = f"/projects/{mr_project_id}/merge_requests/{mr_iid}/notes"
    url = f"{gitlab_api_v4_root_url}{base_mr_notes_api_endpoint}"
    return url


def git_merge_base(commit_1: str, commit_2: str) -> str | None:
    """Get the best common ancestor between two commits and return it.

    When found, it should be returned as a string of the SHA1 sum representing the commit.
    When it can't be found (or there is an error), `None` should be returned.
    """
    cmd = ["git", "merge-base", commit_1, commit_2]
    LOG.debug("Finding common ancestor commit with command: %s", shlex.join(cmd))
    try:
        common_commit = subprocess.run(  # noqa: S603
            cmd,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        ).stdout.strip()
    except subprocess.CalledProcessError as err:
        msg = """
            The common ancestor commit could not be found.
            Ensure the git strategy is set to `clone` for repo checkouts:
            https://docs.gitlab.com/ci/runners/configure_runners/#git-strategy"""
        pprint_subprocess_error(err)
        LOG.warning(cleandoc(msg))
        common_commit = None

    return common_commit
