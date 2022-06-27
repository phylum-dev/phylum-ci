"""Define an implementation for the GitHub Actions platform.

GitHub References:
  * https://docs.github.com/en/actions/learn-github-actions/environment-variables#default-environment-variables
  * https://docs.github.com/en/actions/security-guides/automatic-token-authentication
  * https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/creating-a-personal-access-token
  * https://docs.github.com/en/developers/apps/building-oauth-apps/scopes-for-oauth-apps#available-scopes
  * https://docs.github.com/en/developers/webhooks-and-events/webhooks/webhook-events-and-payloads#pull_request
  * https://docs.github.com/en/rest/overview/resources-in-the-rest-api
  * https://docs.github.com/en/rest/pulls/comments
  * https://docs.github.com/en/rest/guides/working-with-comments#pull-request-comments
"""
import json
import os
import subprocess
from argparse import Namespace
from pathlib import Path
from typing import Optional

import requests
from phylum.ci.ci_base import CIBase
from phylum.ci.constants import PHYLUM_HEADER
from phylum.constants import REQ_TIMEOUT


class CIGitHub(CIBase):
    """Provide methods for a GitHub Actions environment."""

    def __init__(self, args: Namespace) -> None:
        super().__init__(args)
        self.ci_platform_name = "GitHub Actions"

        # This is the recommended workaround for container actions, to avoid the `unsafe repository` error.
        # See https://github.com/actions/checkout/issues/766 (git CVE-2022-24765) for more detail.
        github_workspace = os.getenv("GITHUB_WORKSPACE", "/github/workspace")
        cmd = f"git config --global --add safe.directory {github_workspace}"
        subprocess.run(cmd.split(), check=True)

    def _check_prerequisites(self) -> None:
        """Ensure the necessary pre-requisites are met and bail when they aren't.

        These are the current pre-requisites for operating within a GitHub Actions Environment:
          * The environment must actually be within GitHub Actions
          * A GitHub token providing `issues` API access is available
          * `pull_request` webhook event payload is available
        """
        super()._check_prerequisites()

        if os.getenv("GITHUB_ACTIONS") != "true":
            raise SystemExit(" [!] Must be working within the GitHub Actions environment")

        # A GitHub token with API access is required to use the API (e.g., to post comments). This can be the default
        # `GITHUB_TOKEN` provided automatically at the start of each workflow run or a personal access token (PAT).
        # A `GITHUB_TOKEN` needs at least write access for `pull-requests` scope (even though the `issues` API is used).
        # A PAT needs the `repo` scope or minimally the `public_repo` scope if private repositories are not used.
        # See the GitHub Token Documentation for more info:
        # https://docs.github.com/en/actions/security-guides/automatic-token-authentication
        # https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/creating-a-personal-access-token
        # https://docs.github.com/en/developers/apps/building-oauth-apps/scopes-for-oauth-apps#available-scopes
        github_token = os.getenv("GITHUB_TOKEN")
        if not github_token:
            raise SystemExit(" [!] A GitHub token with API access must be set at `GITHUB_TOKEN` environment variable")
        self._github_token = github_token

        # Unfortunately, there's not always a simple default environment variable that contains the desired information.
        # Instead, the full event webhook payload can be used to obtain the information. Reference:
        # https://docs.github.com/en/developers/webhooks-and-events/webhooks/webhook-events-and-payloads#pull_request
        if os.getenv("GITHUB_EVENT_NAME") != "pull_request":
            raise SystemExit(" [!] The workflow event must be `pull_request`")
        github_event_path = os.getenv("GITHUB_EVENT_PATH")
        if github_event_path is None:
            raise SystemExit(" [!] Could not read the `GITHUB_EVENT_PATH` environment variable")
        with open(github_event_path, encoding="utf-8") as f:
            pr_event = json.load(f)
        self._pr_event = pr_event

    @property
    def github_token(self) -> str:
        """Get the default `GITHUB_TOKEN` or custom Personal Access Token (PAT) in use."""
        return self._github_token

    @property
    def pr_event(self) -> dict:
        """Get the `pull_request` webhook event payload."""
        return self._pr_event

    @property
    def phylum_label(self) -> str:
        """Get a custom label for use when submitting jobs with `phylum analyze`."""
        pr_number = self.pr_event.get("pull_request", {}).get("number", "unknown-number")
        pr_src_branch = os.getenv("GITHUB_HEAD_REF", "unknown-ref")
        label = f"{self.ci_platform_name}_PR#{pr_number}_{pr_src_branch}"
        label = label.replace(" ", "-")
        return label

    @property
    def common_lockfile_ancestor_commit(self) -> Optional[str]:
        """Find the common lockfile ancestor commit."""
        return self.pr_event.get("pull_request", {}).get("base", {}).get("sha")

    def _is_lockfile_changed(self, lockfile: Path) -> bool:
        """Predicate for detecting if the given lockfile has changed."""
        pr_src_branch = os.getenv("GITHUB_HEAD_REF")
        pr_tgt_branch = os.getenv("GITHUB_BASE_REF")
        pr_base_sha = self.common_lockfile_ancestor_commit
        print(f" [+] GITHUB_HEAD_REF: {pr_src_branch}")
        print(f" [+] GITHUB_BASE_REF: {pr_tgt_branch}")
        print(f" [+] PR base SHA: {pr_base_sha}")

        # Assume no change when there isn't enough information to tell
        if pr_base_sha is None:
            return False

        try:
            # `--exit-code` will make git exit with 1 if there were differences while 0 means no differences.
            # Any other exit code is an error and a reason to re-raise.
            cmd = f"git diff --exit-code --quiet {pr_base_sha} -- {lockfile.resolve()}"
            subprocess.run(cmd.split(), check=True)
            return False
        except subprocess.CalledProcessError as err:
            if err.returncode == 1:
                return True
            print(" [!] Consider changing the `fetch_depth` input during checkout to fetch more branch history")
            raise

    def post_output(self) -> None:
        """Post the output of the analysis as a comment on the GitHub Pull Request (PR)."""
        # API Reference: https://docs.github.com/en/rest/issues/comments
        # This is the same endpoint for listing all PR comments (GET) and creating new ones (POST)
        comments_url = self.pr_event.get("pull_request", {}).get("comments_url")

        headers = {
            "Accept": "application/vnd.github.v3+json",
            "Authorization": f"token {self.github_token}",
        }

        query_params = {"per_page": 100}
        print(f" [*] Getting all current pull request comments with GET URL: {comments_url} ...")
        req = requests.get(comments_url, headers=headers, params=query_params, timeout=REQ_TIMEOUT)
        req.raise_for_status()
        pr_comments = req.json()

        print(" [*] Checking pull request comments for existing content to avoid duplication ...")
        if not pr_comments:
            print(" [+] No existing pull request comments found.")
        # NOTE: The API call returns the comments in ascending order by ID...thus the need to reverse the list.
        #       Detecting Phylum comments is done simply by looking for those that start with a known string value.
        #       We only care about the most recent Phylum comment.
        for pr_comment in reversed(pr_comments):
            if pr_comment.get("body", "").lstrip().startswith(PHYLUM_HEADER.strip()):
                print(" [+] The most recently posted Phylum pull request comment was found.")
                if pr_comment.get("body", "") == self.analysis_output:
                    print(" [+] It contains the same content as the current analysis. Nothing to do.")
                    return
                print(" [+] It does not contain the same content as the current analysis.")
                break

        # If we got here, then the most recent Phylum PR comment does not match the current analysis output or
        # there were no Phylum PR comments. Either way, create a new PR comment.
        body_params = {"body": self.analysis_output}
        print(f" [*] Creating new pull request comment with POST URL: {comments_url} ...")
        response = requests.post(comments_url, headers=headers, json=body_params, timeout=REQ_TIMEOUT)
        response.raise_for_status()
