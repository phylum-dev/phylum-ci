"""Define an implementation for the GitLab CI platform.

GitLab References:
  * https://docs.gitlab.com/ee/ci/
  * https://docs.gitlab.com/ee/ci/docker/using_docker_images.html
  * https://docs.gitlab.com/ee/ci/variables/predefined_variables.html
  * https://docs.gitlab.com/ee/ci/jobs/ci_job_token.html
  * https://docs.gitlab.com/ee/api/notes.html#merge-requests
"""
import os
import subprocess
from argparse import Namespace
from functools import lru_cache
from pathlib import Path
from typing import Optional

import requests

from phylum.ci.ci_base import CIBase, git_remote
from phylum.ci.constants import PHYLUM_HEADER
from phylum.constants import REQ_TIMEOUT

SHA1_ALL_ZEROES = "0000000000000000000000000000000000000000"


@lru_cache(maxsize=1)
def is_in_mr() -> bool:
    """Indicate if the integration is operating in the context of a merge request pipeline.

    GitLab CI allows for the possibility of running pipelines in different contexts:
        * On every push, for the last commit in the push (e.g., branch pipelines)
        * For merge requests (e.g., merge request pipelines)

    Knowing when the context is within a merge request helps to ensure the logic used
    to determine the lockfile changes is correct. It also helps to ensure output is not
    attempted to be posted when NOT in the context of a review.
    """
    # References:
    # https://github.com/watson/ci-info/blob/master/vendors.json
    # https://docs.gitlab.com/ee/ci/pipelines/merge_request_pipelines.html
    # docs.gitlab.com/ee/ci/variables/predefined_variables.html#predefined-variables-for-merge-request-pipelines
    return bool(os.getenv("CI_MERGE_REQUEST_ID"))


class CIGitLab(CIBase):
    """Provide methods for a GitLab CI environment."""

    def __init__(self, args: Namespace) -> None:
        super().__init__(args)
        self.ci_platform_name = "GitLab CI"
        if is_in_mr():
            print(" [-] Pipeline context: merge request pipeline")
        else:
            print(" [-] Pipeline context: branch pipeline")

    def _check_prerequisites(self) -> None:
        """Ensure the necessary pre-requisites are met and bail when they aren't.

        These are the current pre-requisites for operating within a GitLab CI Environment:
          * The environment must actually be within GitLab CI
          * A GitLab token providing API access is available
        """
        super()._check_prerequisites()

        # References:
        # https://github.com/watson/ci-info/blob/master/vendors.json
        # https://docs.gitlab.com/ee/ci/variables/predefined_variables.html
        if os.getenv("GITLAB_CI") != "true":
            raise SystemExit(" [!] Must be working within the GitLab CI environment")

        # A GitLab token with API access is required to use the API (e.g., to post notes/comments).
        # This can be a personal, project, or group access token...and possibly some other types as well.
        # See the GitLab Token Overview Documentation for info: https://docs.gitlab.com/ee/security/token_overview.html
        gitlab_token = os.getenv("GITLAB_TOKEN", "")
        if not gitlab_token and is_in_mr():
            raise SystemExit(" [!] A GitLab token with API access must be set at `GITLAB_TOKEN`")
        self._gitlab_token = gitlab_token

    @property
    def gitlab_token(self) -> str:
        """Get the GitLab token (e.g., personal, project, group, etc.)."""
        return self._gitlab_token

    @property
    def phylum_label(self) -> str:
        """Get a custom label for use when submitting jobs with `phylum analyze`."""
        if is_in_mr():
            mr_iid = os.getenv("CI_MERGE_REQUEST_IID", "unknown-IID")
            mr_title = os.getenv("CI_MERGE_REQUEST_TITLE", "unknown-title")
            label = f"{self.ci_platform_name}_MR#{mr_iid}_{mr_title}"
        else:
            current_branch = os.getenv("CI_COMMIT_BRANCH", "unknown-branch")
            # This is the unique key that git uses to refer to the blob type data object for the lockfile.
            # Reference: https://git-scm.com/book/en/v2/Git-Internals-Git-Objects
            cmd = ["git", "hash-object", str(self.lockfile)]
            lockfile_hash_object = subprocess.run(cmd, check=True, text=True, capture_output=True).stdout.strip()
            label = f"{self.ci_platform_name}_{current_branch}_{lockfile_hash_object[:7]}"

        label = label.replace(" ", "-")
        return label

    @property
    def common_lockfile_ancestor_commit(self) -> Optional[str]:
        """Find the common lockfile ancestor commit."""
        # Reference: https://docs.gitlab.com/ee/ci/variables/predefined_variables.html
        if is_in_mr():
            common_ancestor_commit = os.getenv("CI_MERGE_REQUEST_DIFF_BASE_SHA")
        else:
            # CI_COMMIT_BEFORE_SHA contains the previous latest commit present on the branch *pipeline*.
            # It will always be all zeroes in merge request pipelines.
            # It will be all zeroes for the first pipeline run in branch pipelines,
            # whether or not the commit the pipeline runs on is the first commit in the branch.
            # If there are multiple commits between pipeline runs (e.g., push a collection of commits), the value
            # points to the commit of the previous pipeline run, skipping over all the intermediate commits.
            # Think of this as a pointer to the previous commit **that ran in the same branch pipeline**.
            common_ancestor_commit = os.getenv("CI_COMMIT_BEFORE_SHA")

        # There is not an environment variable provided by GitLab CI to show or determine the common ancestor commit
        # when running in a branch pipeline, on the initial run of that pipeline. Fallback to computing it manually.
        if common_ancestor_commit == SHA1_ALL_ZEROES:
            print(" [-] Detected initial branch pipeline run")
            remote = git_remote()
            # The default branch is found this way because there is a GitLab runner bug where HEAD is not available:
            # https://gitlab.com/gitlab-org/gitlab-runner/-/issues/4078
            default_branch = os.getenv("CI_DEFAULT_BRANCH", "HEAD")
            # This is a best effort attempt since it is finding the merge base between the current commit
            # and the default branch instead of finding the exact commit from which the branch was created.
            cmd = ["git", "merge-base", "HEAD", f"refs/remotes/{remote}/{default_branch}"]
            try:
                common_ancestor_commit = subprocess.run(cmd, check=True, capture_output=True, text=True).stdout.strip()
            except subprocess.CalledProcessError as err:
                print(f" [!] The common lockfile ancestor commit could not be found: {err}")
                print(f" [!] stdout:\n{err.stdout}")
                print(f" [!] stderr:\n{err.stderr}")
                common_ancestor_commit = None

        return common_ancestor_commit

    def _is_lockfile_changed(self, lockfile: Path) -> bool:
        """Predicate for detecting if the given lockfile has changed."""
        diff_base_sha = self.common_lockfile_ancestor_commit
        print(f" [+] The common lockfile ancestor commit: {diff_base_sha}")

        # Assume no change when there isn't enough information to tell
        if diff_base_sha is None:
            return False

        # `--exit-code` will make git exit with 1 if there were differences while 0 means no differences.
        # Any other exit code is an error and a reason to re-raise.
        cmd = ["git", "diff", "--exit-code", "--quiet", diff_base_sha, "--", str(lockfile.resolve())]
        ret = subprocess.run(cmd, check=False)
        if ret.returncode == 0:
            return False
        if ret.returncode == 1:
            return True
        # Reference: https://docs.gitlab.com/ee/ci/large_repositories/index.html#shallow-cloning
        print(" [!] Consider changing the `GIT_DEPTH` variable in CI settings to clone/fetch more branch history")
        ret.check_returncode()
        return False  # unreachable code but this makes mypy happy

    def post_output(self) -> None:
        """Post the output of the analysis.

        Post output directly in the logs regardless of the pipeline context.
        Post output as a note (comment) on the GitLab CI Merge Request (MR) when operating in a merge request pipeline.
        """
        super().post_output()

        if not is_in_mr():
            # Can't post the output to the MR when there is no MR
            return

        # API Reference: https://docs.gitlab.com/ee/api/notes.html#merge-requests
        gitlab_api_v4_root_url = os.getenv("CI_API_V4_URL")
        mr_project_id = os.getenv("CI_MERGE_REQUEST_PROJECT_ID")
        mr_iid = os.getenv("CI_MERGE_REQUEST_IID")
        # This is the same endpoint for listing all MR notes (GET) and creating new ones (POST)
        base_mr_notes_api_endpoint = f"/projects/{mr_project_id}/merge_requests/{mr_iid}/notes"
        url = f"{gitlab_api_v4_root_url}{base_mr_notes_api_endpoint}"
        headers = {"PRIVATE-TOKEN": self.gitlab_token}

        print(f" [*] Getting all current merge request notes with GET URL: {url} ...")
        req = requests.get(url, headers=headers, timeout=REQ_TIMEOUT)
        req.raise_for_status()
        mr_notes = req.json()

        print(" [*] Checking existing merge request notes for existing content to avoid duplication ...")
        if not mr_notes:
            print(" [+] No existing merge request notes found.")
        # NOTE: The API defaults to returning the notes in descending order by the `created_at` field.
        #       Detecting Phylum notes is done simply by looking for notes that start with a known string value.
        #       We only care about the most recent Phylum note.
        for mr_note in mr_notes:
            if mr_note.get("body", "").lstrip().startswith(PHYLUM_HEADER.strip()):
                print(" [+] The most recently posted Phylum merge request note was found.")
                if mr_note.get("body", "") == self.analysis_output:
                    print(" [+] It contains the same content as the current analysis. Nothing to do.")
                    return
                print(" [+] It does not contain the same content as the current analysis.")
                break

        # If we got here, then the most recent Phylum MR note does not match the current analysis output or
        # there were no Phylum MR notes. Either way, create a new MR note.
        data = {"body": self.analysis_output}
        print(f" [*] Creating new merge request note with POST URL: {url} ...")
        response = requests.post(url, data=data, headers=headers, timeout=REQ_TIMEOUT)
        response.raise_for_status()
