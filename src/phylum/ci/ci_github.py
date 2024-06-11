"""Define an implementation for the GitHub Actions platform.

GitHub References:
  * https://docs.github.com/en/actions/learn-github-actions/variables#default-environment-variables
  * https://docs.github.com/en/actions/security-guides/automatic-token-authentication
  * https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/creating-a-personal-access-token
  * https://docs.github.com/en/developers/apps/building-oauth-apps/scopes-for-oauth-apps#available-scopes
  * https://docs.github.com/en/developers/webhooks-and-events/webhooks/webhook-events-and-payloads#pull_request
  * https://docs.github.com/en/rest/overview/resources-in-the-rest-api
  * https://docs.github.com/en/rest/pulls/comments
  * https://docs.github.com/en/rest/guides/working-with-comments#pull-request-comments
"""

from argparse import Namespace
from functools import cached_property, lru_cache
from inspect import cleandoc
import json
import os
from pathlib import Path
import re
import subprocess
from typing import Optional

import requests

from phylum.ci.ci_base import CIBase
from phylum.constants import PHYLUM_HEADER, REQ_TIMEOUT
from phylum.exceptions import PhylumCalledProcessError
from phylum.github import get_headers, github_request
from phylum.logger import LOG

PAT_ERR_MSG = """
A GitHub token with API access is required to use the API
(e.g., to post comments). This can be the default `GITHUB_TOKEN`
provided automatically at the start of each workflow run. It can also
be either a classic or fine-grained personal access token (PAT).

A `GITHUB_TOKEN` needs at least write access for `pull-requests`
scope (even though the `issues` API is used).

A classic PAT needs the `repo` scope or minimally the `public_repo`
scope if private repositories are not used.

A fine-grained PAT needs read access to `metadata` and read/write
access to `pull requests`.

See GitHub Token Documentation for more info:
  * https://docs.github.com/actions/security-guides/automatic-token-authentication
  * https://docs.github.com/authentication/keeping-your-account-and-data-secure/creating-a-personal-access-token
  * https://docs.github.com/rest/overview/permissions-required-for-fine-grained-personal-access-tokens
  * https://docs.github.com/developers/apps/building-oauth-apps/scopes-for-oauth-apps#available-scopes
"""


class CIGitHub(CIBase):
    """Provide methods for a GitHub Actions environment."""

    def __init__(self, args: Namespace) -> None:  # noqa: D107 ; the base __init__ docstring is better here
        # This is the recommended workaround for container actions, to avoid the `unsafe repository` error.
        # It is added before super().__init__(args) so that dependency file change detection will be set properly.
        # See https://github.com/actions/checkout/issues/766 (git CVE-2022-24765) for more detail.
        github_workspace = os.getenv("GITHUB_WORKSPACE", "/github/workspace")
        cmd = ["git", "config", "--global", "--add", "safe.directory", github_workspace]
        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True)  # noqa: S603
        except subprocess.CalledProcessError as err:
            msg = f"""
                Adding the GitHub workspace `{github_workspace}` as a safe
                directory in the git config failed. This is the recommended workaround
                for container actions, to avoid the `unsafe repository` error.
                See https://github.com/actions/checkout/issues/766 (git CVE-2022-24765)
                for more detail."""
            raise PhylumCalledProcessError(err, cleandoc(msg)) from err

        super().__init__(args)
        self.ci_platform_name = "GitHub Actions"

        if os.getenv("GITHUB_EVENT_NAME") == "pull_request_target":
            msg = """
                Using `pull_request_target` events for forked repositories has security
                implications if done improperly. Lockfile generation has been disabled
                to prevent arbitrary code execution in an untrusted context.
                See https://docs.phylum.io/phylum-ci/github_actions for more detail."""
            LOG.warning(cleandoc(msg))
            self.disable_lockfile_generation = True

    def _check_prerequisites(self) -> None:
        """Ensure the necessary prerequisites are met and bail when they aren't.

        These are the current prerequisites for operating within a GitHub Actions Environment:
          * The environment must actually be within GitHub Actions
          * A GitHub token providing `issues` API access is available
            * Unless comment generation is skipped
          * `pull_request` or `pull_request_target` is the triggering event
          * `pull_request` webhook event payload is available
        """
        super()._check_prerequisites()

        if os.getenv("GITHUB_ACTIONS") != "true":
            msg = "Must be working within the GitHub Actions environment"
            raise SystemExit(msg)

        github_token = os.getenv("GITHUB_TOKEN", "")
        if not github_token and not self.skip_comments:
            msg = f"A GitHub token with API access must be set at `GITHUB_TOKEN`: {PAT_ERR_MSG}"
            raise SystemExit(msg)
        self._github_token = github_token

        # Unfortunately, there's not always a simple default environment variable that contains the desired information.
        # Instead, the full event webhook payload can be used to obtain the information. The webhook payload for both
        # `pull_request` and `pull_request_target` events is the same - `pull_request`.
        # Ref: https://docs.github.com/developers/webhooks-and-events/webhooks/webhook-events-and-payloads#pull_request
        if os.getenv("GITHUB_EVENT_NAME") not in {"pull_request", "pull_request_target"}:
            msg = "The workflow event must be `pull_request` or `pull_request_target`"
            raise SystemExit(msg)
        github_event_path_envvar = os.getenv("GITHUB_EVENT_PATH")
        if github_event_path_envvar is None:
            msg = "Could not read the `GITHUB_EVENT_PATH` environment variable"
            raise SystemExit(msg)
        github_event_path = Path(github_event_path_envvar)
        with github_event_path.open(encoding="utf-8") as f:
            self._pr_event = json.load(f)

    @property
    def github_token(self) -> str:
        """Get the default `GITHUB_TOKEN` or custom Personal Access Token (PAT) in use."""
        return self._github_token

    @property
    def pr_event(self) -> dict:
        """Get the `pull_request` webhook event payload."""
        return self._pr_event

    @property
    def comments_url(self) -> str:
        """Get the API endpoint for working with comments."""
        # The `comments_url` is the full API endpoint for this particular GitHub issue/PR.
        # API Reference: https://docs.github.com/en/rest/issues/comments
        # This is the same endpoint for listing all PR comments (GET) and creating new ones (POST).
        comments_url = self.pr_event.get("pull_request", {}).get("comments_url")
        if comments_url is None:
            msg = "The API for posting a GitHub comment was not found."
            raise SystemExit(msg)
        return comments_url

    @cached_property
    def phylum_label(self) -> str:
        """Get a custom label for use when submitting jobs for analysis."""
        pr_number = self.pr_event.get("pull_request", {}).get("number", "unknown-number")
        if os.getenv("GITHUB_EVENT_NAME") == "pull_request_target":
            # Use the `OWNER:BRANCH` form when the PR comes from a forked repo
            pr_src_branch = self.pr_event.get("pull_request", {}).get("head", {}).get("label", "unknown-ref")
        else:
            pr_src_branch = os.getenv("GITHUB_HEAD_REF", "unknown-ref")
        label = f"{self.ci_platform_name}_PR#{pr_number}_{pr_src_branch}"
        label = re.sub(r"\s+", "-", label)
        return label

    @cached_property
    def common_ancestor_commit(self) -> Optional[str]:
        """Find the common ancestor commit."""
        return self.pr_event.get("pull_request", {}).get("base", {}).get("sha")

    @property
    def is_any_depfile_changed(self) -> bool:
        """Predicate for detecting if any dependency file has changed."""
        pr_src_branch = os.getenv("GITHUB_HEAD_REF")
        pr_tgt_branch = os.getenv("GITHUB_BASE_REF")
        pr_base_sha = self.common_ancestor_commit
        LOG.debug("GITHUB_HEAD_REF: %s", pr_src_branch)
        LOG.debug("GITHUB_BASE_REF: %s", pr_tgt_branch)
        LOG.debug("PR base SHA: %s", pr_base_sha)

        # Assume no change when there isn't enough information to tell
        if pr_base_sha is None:
            return False

        err_msg = """
            Consider changing the `fetch-depth` input during checkout to fetch more
            branch history. For more info: https://github.com/actions/checkout"""
        self.update_depfiles_change_status(pr_base_sha, err_msg)

        return any(depfile.is_depfile_changed for depfile in self.depfiles)

    @property
    def phylum_comment_exists(self) -> bool:
        """Predicate for detecting whether a Phylum-generated comment exists."""
        if self.skip_comments:
            LOG.debug("Posting analysis output as comments on the pull request was disabled.")
            if not self.github_token:
                LOG.debug("GitHub API token not available. Unable to look for comments.")
                return False
            LOG.debug("GitHub API token available but possibly invalid. Attempting use ...")
        return bool(get_most_recent_phylum_comment_github(self.comments_url, self.github_token))

    @property
    def repo_url(self) -> Optional[str]:
        """Get the repository URL for reference in Phylum project metadata."""
        # Ref: https://docs.github.com/actions/learn-github-actions/variables#default-environment-variables
        server_url = os.getenv("GITHUB_SERVER_URL")
        if server_url is None:
            LOG.debug("`GITHUB_SERVER_URL` missing. Can't get repository URL.")
        repo = os.getenv("GITHUB_REPOSITORY")
        if repo is None:
            LOG.debug("`GITHUB_REPOSITORY` missing. Can't get repository URL.")
        if server_url is None or repo is None:
            return None
        return f"{server_url}/{repo}"

    def post_output(self) -> None:
        """Post the output of the analysis.

        Post output directly in the logs regardless of the context.
        Optionally post output as a comment on the GitHub Pull Request (PR).
        """
        super().post_output()

        if self.skip_comments:
            LOG.debug("Posting analysis output as comments on the pull request was disabled.")
            return

        post_github_comment(self.comments_url, self.github_token, self.analysis_report)


# This is a cached function due to the desire to limit API calls.
# The function is meant to be used internally, where it is known that the comments on the PR at the time
# of first execution will suffice for the duration of the rest of the lifetime of the running integration.
@lru_cache(maxsize=1)
def get_most_recent_phylum_comment_github(comments_url: str, github_token: str) -> Optional[str]:
    """Get the raw text of the most recently posted Phylum-generated comment for GitHub PRs.

    Return `None` when one does not exist.

    The `comments_url` should be the full API endpoint for a particular GitHub issue/PR.
    API Reference: https://docs.github.com/en/rest/issues/comments
    This is the same endpoint for listing all PR comments (GET) and creating new ones (POST).
    """
    query_params = {"per_page": 100}
    LOG.info("Getting all current pull request comments with GET URL: %s ...", comments_url)
    pr_comments: list = github_request(comments_url, params=query_params, github_token=github_token)

    if not pr_comments:
        LOG.debug("No existing pull request comments found.")
        return None

    # NOTE: The API call returns the comments in ascending order by ID...thus the need to reverse the list.
    #       Detecting Phylum comments is done simply by looking for those that start with a known string value.
    #       We only care about the most recent Phylum comment.
    pr_comment: dict
    for pr_comment in reversed(pr_comments):
        comment_body: str = pr_comment.get("body", "")
        if comment_body.lstrip().startswith(PHYLUM_HEADER.strip()):
            # The most recently posted Phylum pull request comment was found
            return comment_body

    # No existing Phylum pull request comments found
    return None


def post_github_comment(comments_url: str, github_token: str, comment: str) -> None:
    """Post a comment on a GitHub Pull Request (PR).

    The `comments_url` should be the full API endpoint for a particular GitHub issue/PR.
    API Reference: https://docs.github.com/en/rest/issues/comments
    This is the same endpoint for listing all PR comments (GET) and creating new ones (POST).

    The comment will only be created if there isn't already a Phylum comment
    or if the most recently posted Phylum comment does not contain the same content.
    """
    LOG.info("Checking pull request comments for existing content to avoid duplication ...")
    most_recent_phylum_comment = get_most_recent_phylum_comment_github(comments_url, github_token)
    if most_recent_phylum_comment:
        LOG.debug("The most recently posted Phylum pull request comment was found.")
        if most_recent_phylum_comment == comment:
            LOG.debug("It contains the same content as the current analysis. Nothing to do.")
            return
        LOG.debug("It does not contain the same content as the current analysis.")
    else:
        LOG.debug("No existing Phylum pull request comments found.")

    # If we got here, then the most recent Phylum PR comment does not match the current analysis output or
    # there were no Phylum PR comments. Either way, create a new PR comment.
    headers = get_headers(github_token=github_token)
    body_params = {"body": comment}
    LOG.info("Creating new pull request comment with POST URL: %s ...", comments_url)
    response = requests.post(comments_url, headers=headers, json=body_params, timeout=REQ_TIMEOUT)
    response.raise_for_status()
