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
from pathlib import Path
from typing import Optional

import requests
from phylum.ci.ci_base import CIBase
from phylum.ci.constants import PHYLUM_HEADER
from phylum.constants import REQ_TIMEOUT


class CIGitLab(CIBase):
    """Provide methods for a GitLab CI environment."""

    def __init__(self, args: Namespace) -> None:
        self.ci_platform_name = "GitLab CI"
        super().__init__(args)

    def _check_prerequisites(self) -> None:
        """Ensure the necessary pre-requisites are met and bail when they aren't.

        These are the current pre-requisites for operating within a GitLab CI Environment:
          * The environment must actually be within GitLab CI
          * A GitLab token providing API access is available
        """
        super()._check_prerequisites()

        if os.getenv("GITLAB_CI") != "true":
            raise SystemExit(" [!] Must be working within the GitLab CI environment")

        # A GitLab token with API access is required to use the API (e.g., to post notes/comments)
        # This can be a personal, project, or group access token...and possibly some other types as well.
        # See the GitLab Token Overview Documentation for info: https://docs.gitlab.com/ee/security/token_overview.html
        gitlab_token = os.getenv("GITLAB_TOKEN")
        if not gitlab_token:
            raise SystemExit(" [!] A GitLab token with API access must be set at `GITLAB_TOKEN`")
        self._gitlab_token = gitlab_token

    @property
    def gitlab_token(self) -> str:
        """Get the GitLab token (e.g., personal, project, group, etc.)."""
        return self._gitlab_token

    @property
    def phylum_label(self) -> str:
        """Get a custom label for use when submitting jobs with `phylum analyze`."""
        mr_iid = os.getenv("CI_MERGE_REQUEST_IID", "unknown-IID")
        mr_title = os.getenv("CI_MERGE_REQUEST_TITLE", "unknown-title")
        label = f"{self.ci_platform_name}_MR#{mr_iid}_{mr_title}"
        label = label.replace(" ", "-")
        return label

    @property
    def common_lockfile_ancestor_commit(self) -> Optional[str]:
        """Find the common lockfile ancestor commit."""
        # Reference: https://docs.gitlab.com/ee/ci/variables/predefined_variables.html
        return os.getenv("CI_MERGE_REQUEST_DIFF_BASE_SHA")

    def _is_lockfile_changed(self, lockfile: Path) -> bool:
        """Predicate for detecting if the given lockfile has changed."""
        mr_src_branch = os.getenv("CI_MERGE_REQUEST_SOURCE_BRANCH_NAME")
        mr_tgt_branch = os.getenv("CI_MERGE_REQUEST_TARGET_BRANCH_NAME")
        mr_diff_base_sha = os.getenv("CI_MERGE_REQUEST_DIFF_BASE_SHA")
        print(f" [+] CI_MERGE_REQUEST_SOURCE_BRANCH_NAME: {mr_src_branch}")
        print(f" [+] CI_MERGE_REQUEST_TARGET_BRANCH_NAME: {mr_tgt_branch}")
        print(f" [+] CI_MERGE_REQUEST_DIFF_BASE_SHA: {mr_diff_base_sha}")

        # Assume no change when there isn't enough information to tell
        if mr_diff_base_sha is None:
            return False

        try:
            cmd = f"git diff --exit-code --quiet {mr_diff_base_sha} -- {lockfile.resolve()}"
            # `--exit-code` will make git exit with with 1 if there were differences while 0 means no differences.
            # Any other exit code is an error and a reason to re-raise.
            subprocess.run(cmd.split(), check=True)
            return False
        except subprocess.CalledProcessError as err:
            if err.returncode == 1:
                return True
            print(" [!] Consider changing the `GIT_DEPTH` variable in CI settings to clone/fetch more branch history")
            raise

    def post_output(self) -> None:
        """Post the output of the analysis as a note (comment) on the GitLab CI Merge Request (MR)."""
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
        # NOTE: The API defaults to returning the notes in descending order by the `created_at` field.
        #       Detecting Phylum notes is done simply by looking for those notes that start with a known string value.
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
