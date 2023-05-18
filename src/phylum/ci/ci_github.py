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
from argparse import Namespace
from functools import cached_property
import json
import os
from pathlib import Path
import re
import subprocess
import textwrap
from typing import Optional

import requests

from phylum.ci.ci_base import CIBase
from phylum.constants import PHYLUM_HEADER, REQ_TIMEOUT
from phylum.exceptions import PhylumCalledProcessError
from phylum.github import get_headers, github_request
from phylum.logger import LOG

PAT_ERR_MSG = """
A GitHub token with API access is required to use the API (e.g., to post comments).
This can be the default `GITHUB_TOKEN` provided automatically at the start of each workflow run.
It can also be either a classic or fine-grained personal access token (PAT).
A `GITHUB_TOKEN` needs at least write access for `pull-requests` scope (even though the `issues` API is used).
A classic PAT needs the `repo` scope or minimally the `public_repo` scope if private repositories are not used.
A fine-grained PAT needs read access to `metadata` and read/write access to `pull requests`.
See the GitHub Token Documentation for more info:
  * https://docs.github.com/actions/security-guides/automatic-token-authentication
  * https://docs.github.com/authentication/keeping-your-account-and-data-secure/creating-a-personal-access-token
  * https://docs.github.com/rest/overview/permissions-required-for-fine-grained-personal-access-tokens
  * https://docs.github.com/developers/apps/building-oauth-apps/scopes-for-oauth-apps#available-scopes
"""


class CIGitHub(CIBase):
    """Provide methods for a GitHub Actions environment."""

    def __init__(self, args: Namespace) -> None:  # noqa: D107 ; the base __init__ docstring is better here
        # This is the recommended workaround for container actions, to avoid the `unsafe repository` error.
        # It is added before super().__init__(args) so that lockfile change detection will be set properly.
        # See https://github.com/actions/checkout/issues/766 (git CVE-2022-24765) for more detail.
        github_workspace = os.getenv("GITHUB_WORKSPACE", "/github/workspace")
        cmd = ["git", "config", "--global", "--add", "safe.directory", github_workspace]
        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True)  # noqa: S603
        except subprocess.CalledProcessError as err:
            msg = f"""\
                Adding the GitHub workspace `{github_workspace}` as a safe directory in the git config failed.
                This is the recommended workaround for container actions, to avoid the `unsafe repository` error.
                See https://github.com/actions/checkout/issues/766 (git CVE-2022-24765) for more detail."""
            raise PhylumCalledProcessError(err, textwrap.dedent(msg)) from err

        super().__init__(args)
        self.ci_platform_name = "GitHub Actions"

    def _check_prerequisites(self) -> None:
        """Ensure the necessary pre-requisites are met and bail when they aren't.

        These are the current pre-requisites for operating within a GitHub Actions Environment:
          * The environment must actually be within GitHub Actions
          * A GitHub token providing `issues` API access is available
          * `pull_request` webhook event payload is available
        """
        super()._check_prerequisites()

        if os.getenv("GITHUB_ACTIONS") != "true":
            msg = "Must be working within the GitHub Actions environment"
            raise SystemExit(msg)

        github_token = os.getenv("GITHUB_TOKEN")
        if not github_token:
            msg = f"A GitHub token with API access must be set at `GITHUB_TOKEN`: {PAT_ERR_MSG}"
            raise SystemExit(msg)
        self._github_token = github_token

        # Unfortunately, there's not always a simple default environment variable that contains the desired information.
        # Instead, the full event webhook payload can be used to obtain the information. Reference:
        # https://docs.github.com/en/developers/webhooks-and-events/webhooks/webhook-events-and-payloads#pull_request
        if os.getenv("GITHUB_EVENT_NAME") != "pull_request":
            msg = "The workflow event must be `pull_request`"
            raise SystemExit(msg)
        github_event_path_envvar = os.getenv("GITHUB_EVENT_PATH")
        if github_event_path_envvar is None:
            msg = "Could not read the `GITHUB_EVENT_PATH` environment variable"
            raise SystemExit(msg)
        github_event_path = Path(github_event_path_envvar)
        with github_event_path.open(encoding="utf-8") as f:
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
        label = re.sub(r"\s+", "-", label)
        return label

    @cached_property
    def common_ancestor_commit(self) -> Optional[str]:
        """Find the common ancestor commit."""
        return self.pr_event.get("pull_request", {}).get("base", {}).get("sha")

    @property
    def is_any_lockfile_changed(self) -> bool:
        """Predicate for detecting if any lockfile has changed."""
        pr_src_branch = os.getenv("GITHUB_HEAD_REF")
        pr_tgt_branch = os.getenv("GITHUB_BASE_REF")
        pr_base_sha = self.common_ancestor_commit
        LOG.debug("GITHUB_HEAD_REF: %s", pr_src_branch)
        LOG.debug("GITHUB_BASE_REF: %s", pr_tgt_branch)
        LOG.debug("PR base SHA: %s", pr_base_sha)

        # Assume no change when there isn't enough information to tell
        if pr_base_sha is None:
            return False

        err_msg = """\
            Consider changing the `fetch-depth` input during checkout to fetch more branch history.
            Reference: https://github.com/actions/checkout"""
        self.update_lockfiles_change_status(pr_base_sha, err_msg)

        return any(lockfile.is_lockfile_changed for lockfile in self.lockfiles)

    def post_output(self) -> None:
        """Post the output of the analysis.

        Post output directly in the logs regardless of the context.
        Post output as a comment on the GitHub Pull Request (PR).
        """
        super().post_output()

        comments_url = self.pr_event.get("pull_request", {}).get("comments_url")
        if comments_url is None:
            msg = "The API for posting a GitHub comment was not found."
            raise SystemExit(msg)

        post_github_comment(comments_url, self.github_token, self.analysis_report)


def post_github_comment(comments_url: str, github_token: str, comment: str) -> None:
    """Post a comment on a GitHub Pull Request (PR).

    The `comments_url` should be the full API endpoint for a particular GitHub issue/PR.
    API Reference: https://docs.github.com/en/rest/issues/comments
    This is the same endpoint for listing all PR comments (GET) and creating new ones (POST).

    The comment will only be created if there isn't already a Phylum comment
    or if the most recently posted Phylum comment does not contain the same content.
    """
    query_params = {"per_page": 100}
    LOG.info("Getting all current pull request comments with GET URL: %s ...", comments_url)
    pr_comments = github_request(comments_url, params=query_params, github_token=github_token)

    LOG.info("Checking pull request comments for existing content to avoid duplication ...")
    if not pr_comments:
        LOG.debug("No existing pull request comments found.")
    # NOTE: The API call returns the comments in ascending order by ID...thus the need to reverse the list.
    #       Detecting Phylum comments is done simply by looking for those that start with a known string value.
    #       We only care about the most recent Phylum comment.
    for pr_comment in reversed(pr_comments):
        if pr_comment.get("body", "").lstrip().startswith(PHYLUM_HEADER.strip()):
            LOG.debug("The most recently posted Phylum pull request comment was found.")
            if pr_comment.get("body", "") == comment:
                LOG.debug("It contains the same content as the current analysis. Nothing to do.")
                return
            LOG.debug("It does not contain the same content as the current analysis.")
            break

    # If we got here, then the most recent Phylum PR comment does not match the current analysis output or
    # there were no Phylum PR comments. Either way, create a new PR comment.
    headers = get_headers(github_token=github_token)
    body_params = {"body": comment}
    LOG.info("Creating new pull request comment with POST URL: %s ...", comments_url)
    response = requests.post(comments_url, headers=headers, json=body_params, timeout=REQ_TIMEOUT)
    response.raise_for_status()
