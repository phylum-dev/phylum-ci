"""Define an implementation for the Azure Pipelines CI platform.

Azure References:
  * https://learn.microsoft.com/azure/devops/pipelines
  * https://learn.microsoft.com/azure/devops/pipelines/repos
  * https://learn.microsoft.com/azure/devops/pipelines/repos/azure-repos-git
  * https://learn.microsoft.com/azure/devops/pipelines/repos/github
  * https://learn.microsoft.com/azure/devops/pipelines/process/access-tokens
  * https://learn.microsoft.com/azure/devops/organizations/accounts/use-personal-access-tokens-to-authenticate
  * https://learn.microsoft.com/azure/devops/pipelines/build/variables
  * https://learn.microsoft.com/azure/devops/pipelines/process/set-secret-variables
  * https://learn.microsoft.com/azure/devops/pipelines/yaml-schema
  * https://learn.microsoft.com/azure/devops/pipelines/yaml-schema/steps-checkout
  * https://learn.microsoft.com/rest/api/azure/devops
  * https://learn.microsoft.com/rest/api/azure/devops/git/pull-request-threads/list
  * https://learn.microsoft.com/rest/api/azure/devops/git/pull-request-threads/create
"""

from argparse import Namespace
import base64
from functools import cached_property, lru_cache
from inspect import cleandoc
import os
import re
import shlex
import subprocess
from typing import Optional
import urllib.parse

import requests

from phylum.ci.ci_base import CIBase
from phylum.ci.ci_github import get_most_recent_phylum_comment_github, post_github_comment
from phylum.ci.git import git_default_branch_name, git_remote
from phylum.constants import PHYLUM_HEADER, PHYLUM_USER_AGENT, REQ_TIMEOUT
from phylum.exceptions import pprint_subprocess_error
from phylum.logger import LOG

AZURE_PAT_ERR_MSG = """
An Azure DevOps token with API access is required to use the API
(e.g., to post comments). This can be the default `System.AccessToken`
provided automatically at the start of each build for the scoped
build identity or a personal access token (PAT).

A PAT needs at least the `Pull Request Threads` scope (read & write).

See Azure DevOps documentation for using personal access tokens:
  * https://learn.microsoft.com/azure/devops/organizations/accounts/use-personal-access-tokens-to-authenticate

The `System.AccessToken` scoped build identity needs
at least the `Contribute to pull requests` permission.

See Azure DevOps documentation for using the `System.AccessToken`:
  * https://learn.microsoft.com/azure/devops/pipelines/build/variables#systemaccesstoken
  * https://learn.microsoft.com/azure/devops/pipelines/process/access-tokens#job-authorization-scope
"""

GITHUB_PAT_ERR_MSG = """
A GitHub token with API access is required to use the
API (e.g., to post comments). This can be either a
classic or fine-grained personal access token (PAT).

A classic PAT needs the `repo` scope or minimally the
`public_repo` scope if private repositories are not used.

A fine-grained PAT needs read access to `metadata` and
read/write access to `pull requests`.

See GitHub Token Documentation for more info:
  * https://docs.github.com/authentication/keeping-your-account-and-data-secure/creating-a-personal-access-token
  * https://docs.github.com/rest/overview/permissions-required-for-fine-grained-personal-access-tokens
  * https://docs.github.com/developers/apps/building-oauth-apps/scopes-for-oauth-apps#available-scopes
"""


@lru_cache(maxsize=1)
def is_in_pr() -> bool:
    """Indicate if the integration is operating in the context of a pull request pipeline.

    Azure Pipelines allows for triggering pipelines to run in different contexts:
      * On every push, for the last commit in the push (e.g., CI triggers)
      * For pull requests (e.g., PR triggers)

    There are other types of triggers but the one we really care about is PR triggers.
    Those will mean running in a context that allows for full output in the form of
    comments. All other triggers will mean running in a context that only provides for
    log based output and a simple fail/succeed result.
    Reference: https://learn.microsoft.com/azure/devops/pipelines/build/triggers

    Knowing when the context is within a pull request helps to ensure the logic used
    to determine the dependency file changes is correct. It also helps to ensure output
    is not attempted to be posted when NOT in the context of a review.
    """
    # References:
    # https://github.com/watson/ci-info/blob/master/vendors.json
    # https://learn.microsoft.com/azure/devops/pipelines/build/variables
    return bool(os.getenv("SYSTEM_PULLREQUEST_PULLREQUESTID"))


class CIAzure(CIBase):
    """Provide methods for an Azure Pipelines CI environment."""

    def __init__(self, args: Namespace) -> None:  # noqa: D107 ; the base __init__ docstring is better here
        super().__init__(args)
        self.ci_platform_name = "Azure Pipelines"
        if is_in_pr():
            LOG.debug("Pipeline context: PR trigger")
        else:
            # There are other types of events that trigger pipelines, but only PR and CI triggers are supported.
            # Reference: https://learn.microsoft.com/azure/devops/pipelines/build/triggers
            LOG.debug("Pipeline context: CI trigger")

    def _check_prerequisites(self) -> None:
        """Ensure the necessary prerequisites are met and bail when they aren't.

        These are the current prerequisites for operating within an Azure Pipelines Environment:
          * The environment must actually be within Azure Pipelines
          * A token providing API access is available to match the triggering repo when operating in a PR pipeline
            * Unless comment generation is skipped
            * An Azure token for Azure Repos Git
            * A GitHub token for GitHub hosted repos
        """
        super()._check_prerequisites()

        # References:
        # https://github.com/watson/ci-info/blob/master/vendors.json
        # https://learn.microsoft.com/azure/devops/pipelines/build/variables
        if os.getenv("SYSTEM_TEAMFOUNDATIONCOLLECTIONURI") is None:
            msg = "Must be working within the Azure Pipelines environment"
            raise SystemExit(msg)

        self.triggering_repo = os.getenv("BUILD_REPOSITORY_PROVIDER", "unknown")
        LOG.debug("Triggering repository: %s", self.triggering_repo)
        # "TfsGit" is the legacy name for "Azure Repos Git"
        if self.triggering_repo not in {"TfsGit", "GitHub"}:
            msg = f"Triggering repository `{self.triggering_repo}` not supported"
            raise SystemExit(msg)

        azure_token = os.getenv("AZURE_TOKEN", "")
        if not azure_token and self.triggering_repo == "TfsGit" and is_in_pr() and not self.skip_comments:
            msg = f"An Azure token with API access must be set at `AZURE_TOKEN`: {AZURE_PAT_ERR_MSG}"
            raise SystemExit(msg)
        self._azure_token = azure_token

        github_token = os.getenv("GITHUB_TOKEN", "")
        if not github_token and self.triggering_repo == "GitHub" and is_in_pr() and not self.skip_comments:
            msg = f"A GitHub token with API access must be set at `GITHUB_TOKEN`: {GITHUB_PAT_ERR_MSG}"
            raise SystemExit(msg)
        self._github_token = github_token

    @property
    def azure_token(self) -> str:
        """Get the default `System.AccessToken` or custom Personal Access Token (PAT) in use."""
        return self._azure_token

    @property
    def github_token(self) -> str:
        """Get the custom Personal Access Token (PAT) in use."""
        return self._github_token

    @cached_property
    def phylum_label(self) -> str:
        """Get a custom label for use when submitting jobs for analysis."""
        if is_in_pr():
            # This variable is only populated for PRs from GitHub which have a different PR ID and PR number
            pr_number = os.getenv("SYSTEM_PULLREQUEST_PULLREQUESTNUMBER")
            if pr_number is None:
                pr_number = os.getenv("SYSTEM_PULLREQUEST_PULLREQUESTID", "unknown-number")
            pr_src_branch = os.getenv("SYSTEM_PULLREQUEST_SOURCEBRANCH", "unknown-ref").removeprefix("refs/heads/")
            label = f"{self.ci_platform_name}_PR#{pr_number}_{pr_src_branch}"
        else:
            current_branch = os.getenv("BUILD_SOURCEBRANCHNAME", "unknown-branch")
            label = f"{self.ci_platform_name}_{current_branch}_{self.depfile_hash_object}"

        label = re.sub(r"\s+", "-", label)
        return label

    @cached_property
    def common_ancestor_commit(self) -> Optional[str]:
        """Find the common ancestor commit."""
        remote = git_remote()

        if is_in_pr():
            src_branch, tgt_branch = get_pr_branches()
        else:
            # Assume the working context is within a CI triggered build environment when not in a PR.

            src_branch = os.getenv("BUILD_SOURCEBRANCHNAME", "")
            if not src_branch:
                msg = "The BUILD_SOURCEBRANCHNAME environment variable must exist and be set"
                raise SystemExit(msg)
            LOG.debug("BUILD_SOURCEBRANCHNAME: %s", src_branch)

            # This is a best effort attempt since it is finding the merge base between the current commit
            # and the default branch instead of finding the exact commit from which the branch was created.
            tgt_branch = f"refs/remotes/{remote}/HEAD"

            # If the current commit is on the default branch, then the merge base will be the same
            # as the current commit and it won't be possible to provide a useful common ancestor
            # commit. In this case, it is better to force analysis of the dependency file(s) and
            # consider *all* dependencies in analysis results instead of just the newly added ones.
            if src_branch == git_default_branch_name(remote):
                LOG.warning("Source branch is same as default branch. Proceeding with analysis of all dependencies ...")
                self._force_analysis = True
                self._all_deps = True

        # Because the checkout step only fetches the bare minimum needed for the pipeline, and
        # because the PR merge commit is checked out in a "detached HEAD" state, it is necessary
        # to be explicit about the refs so that they can be found in this limited git repository.
        old_ref_prefix = "refs/heads/"
        new_ref_prefix = f"refs/remotes/{remote}/"
        if self.triggering_repo == "TfsGit":
            if src_branch.startswith(old_ref_prefix):
                # This prefix should be present for PR triggers
                src_branch = src_branch.replace(old_ref_prefix, new_ref_prefix, 1)
            else:
                # CI triggers provide the branch name, without any prefix
                src_branch = f"{new_ref_prefix}{src_branch}"
            if tgt_branch.startswith(old_ref_prefix):
                tgt_branch = tgt_branch.replace(old_ref_prefix, new_ref_prefix, 1)
        if self.triggering_repo == "GitHub":
            # The source branch from GitHub triggered repositories are simply the branch
            # name, without any prefix (e.g., `mybranch` instead of `refs/heads/mybranch`).
            src_branch = f"{new_ref_prefix}{src_branch}"
            if is_in_pr():
                # The target branch is the same, but only when in a PR context
                tgt_branch = f"{new_ref_prefix}{tgt_branch}"

        cmd = ["git", "merge-base", src_branch, tgt_branch]
        LOG.debug("Finding common ancestor commit with command: %s", shlex.join(cmd))
        try:
            common_commit = subprocess.run(cmd, check=True, capture_output=True, text=True).stdout.strip()  # noqa: S603
        except subprocess.CalledProcessError as err:
            msg = """
                The common ancestor commit could not be found.
                Ensure shallow fetch is disabled for repo checkouts:
                https://learn.microsoft.com/azure/devops/pipelines/yaml-schema/steps-checkout#shallow-fetch"""
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
            Consider changing the `fetchDepth` property in CI settings to
            clone/fetch more branch history. For more info, reference:
            https://learn.microsoft.com/azure/devops/pipelines/yaml-schema/steps-checkout"""
        self.update_depfiles_change_status(diff_base_sha, err_msg)

        return any(depfile.is_depfile_changed for depfile in self.depfiles)

    @property
    def phylum_comment_exists(self) -> bool:
        """Predicate for detecting whether a Phylum-generated comment exists."""
        if not is_in_pr():
            # Comments only exist in the context of a PR
            return False

        if self.triggering_repo == "TfsGit":
            if self.skip_comments:
                LOG.debug("Posting analysis output as comments on the pull request was disabled.")
                if not self.azure_token:
                    LOG.debug("Azure API token not available. Unable to look for comments.")
                    return False
                LOG.debug("Azure API token available but possibly invalid. Attempting use ...")
            return bool(get_most_recent_phylum_comment_azure(self.azure_token))

        if self.triggering_repo == "GitHub":
            if self.skip_comments:
                LOG.debug("Posting analysis output as comments on the pull request was disabled.")
                if not self.github_token:
                    LOG.debug("GitHub API token not available. Unable to look for comments.")
                    return False
                LOG.debug("GitHub API token available but possibly invalid. Attempting use ...")
            comments_url = get_github_comments_url()
            return bool(get_most_recent_phylum_comment_github(comments_url, self.github_token))

        return False

    @property
    def repo_url(self) -> Optional[str]:
        """Get the repository URL for reference in Phylum project metadata."""
        # Ref: https://learn.microsoft.com/azure/devops/pipelines/build/variables
        if self.triggering_repo == "TfsGit":
            # SYSTEM_TEAMPROJECT provides the name that corresponds to SYSTEM_TEAMPROJECTID.
            # Even though the ID will never change while the name might, the name is used for better human consumption.
            team_project_id = os.getenv("SYSTEM_TEAMPROJECT")
            if team_project_id is None:
                LOG.debug("`SYSTEM_TEAMPROJECT` missing. Can't get repository URL.")
            instance = os.getenv("SYSTEM_TEAMFOUNDATIONCOLLECTIONURI")
            if instance is None:
                LOG.debug("`SYSTEM_TEAMFOUNDATIONCOLLECTIONURI` missing. Can't get repository URL.")
            if team_project_id is None or instance is None:
                return None
            # This format is correct regardless of the pipeline context
            return f"{instance}{team_project_id}"
        if self.triggering_repo == "GitHub":
            # BUILD_REPOSITORY_URI will have the correct format regardless of the pipeline context
            build_repo_uri = os.getenv("BUILD_REPOSITORY_URI")
            if build_repo_uri is None:
                LOG.debug("`BUILD_REPOSITORY_URI` missing. Can't get repository URL.")
            return build_repo_uri
        return None

    def post_output(self) -> None:
        """Post the output of the analysis.

        Post output directly in the logs regardless of the trigger type.
        Optionally post output as a comment on the Azure Repos Pull Request (PR)
        for PR triggers and Azure Repos hosted repos.
        Optionally post output as a comment on the GitHub PR for PR triggers and GitHub hosted repos.
        """
        super().post_output()

        if not is_in_pr():
            # Can't post the output to the PR when there is no PR
            return

        if self.skip_comments:
            LOG.debug("Posting analysis output as comments on the pull request was disabled.")
            return

        if self.triggering_repo == "TfsGit":
            post_azure_comment(self.azure_token, self.analysis_report)
        elif self.triggering_repo == "GitHub":
            comments_url = get_github_comments_url()
            post_github_comment(comments_url, self.github_token, self.analysis_report)


def get_pr_branches() -> tuple[str, str]:
    """Get the source and destination branches when in a PR context and return them as a tuple."""
    # There is no single predefined variable available to provide the PR base SHA.
    # Instead, it can be determined with a `git merge-base` command, like is done for the CINone implementation.
    # Reference: https://learn.microsoft.com/azure/devops/pipelines/build/variables
    src_branch = os.getenv("SYSTEM_PULLREQUEST_SOURCEBRANCH", "")
    tgt_branch = os.getenv("SYSTEM_PULLREQUEST_TARGETBRANCH", "")
    if not src_branch:
        msg = "The SYSTEM_PULLREQUEST_SOURCEBRANCH environment variable must exist and be set"
        raise SystemExit(msg)
    if not tgt_branch:
        msg = "The SYSTEM_PULLREQUEST_TARGETBRANCH environment variable must exist and be set"
        raise SystemExit(msg)
    LOG.debug("SYSTEM_PULLREQUEST_SOURCEBRANCH: %s", src_branch)
    LOG.debug("SYSTEM_PULLREQUEST_TARGETBRANCH: %s", tgt_branch)
    return src_branch, tgt_branch


# This is a cached function due to the desire to limit API calls.
# The function is meant to be used internally, where it is known that the comments on the PR at the time
# of first execution will suffice for the duration of the rest of the lifetime of the running integration.
@lru_cache(maxsize=1)
def get_most_recent_phylum_comment_azure(azure_token: str) -> Optional[str]:
    """Get the raw text of the most recently posted Phylum-generated comment for Azure Repos PRs.

    Return `None` when one does not exist.
    """
    if not is_in_pr():
        # It only makes sense to reference this property in the context of a PR
        return None

    # SYSTEM_TEAMPROJECT provides the name that corresponds to SYSTEM_TEAMPROJECTID.
    # SYSTEM_TEAMPROJECTID is used in the API calls since it should never change.
    team_project_id = os.getenv("SYSTEM_TEAMPROJECTID")
    team_project_name = os.getenv("SYSTEM_TEAMPROJECT")
    pr_threads_url = get_azure_pr_threads_url()
    headers = get_headers(azure_token)
    query_params, query_params_encoded = get_query_params()

    LOG.info("Getting all current PR threads with GET URL: %s?%s ...", pr_threads_url, query_params_encoded)
    LOG.debug("The team project ID %s maps to name: %s", team_project_id, team_project_name)
    resp = requests.get(pr_threads_url, params=query_params, headers=headers, timeout=REQ_TIMEOUT)
    resp.raise_for_status()
    if resp.status_code != requests.codes.OK:
        msg = f"Are the permissions on the Azure token `AZURE_TOKEN` correct? {AZURE_PAT_ERR_MSG}"
        raise SystemExit(msg)
    pr_threads_resp: dict = resp.json()

    pr_threads_count = pr_threads_resp.get("count", 0)
    LOG.debug("PR threads found: %s", pr_threads_count)
    if not pr_threads_count:
        LOG.debug("No existing pull request comments found.")
        return None

    LOG.info("Checking pull request threads for existing Phylum-generated comments ...")
    pr_threads: list = pr_threads_resp.get("value", [])
    # NOTE: The API call returns the comments in ascending order by ID...thus the need to reverse the list.
    #       Detecting Phylum comments is done simply by looking for those that start with a known string value.
    #       We only care about the most recent Phylum comment.
    pr_thread: dict
    for pr_thread in reversed(pr_threads):
        thread_comments = pr_thread.get("comments", [])
        thread_comment: dict
        for thread_comment in thread_comments:
            # All Phylum generated comments will be the first in their own thread
            if thread_comment.get("id", 0) != 1:
                continue
            thread_comment_content: str = thread_comment.get("content", "")
            if thread_comment_content.lstrip().startswith(PHYLUM_HEADER.strip()):
                # The most recently posted Phylum pull request comment was found
                return thread_comment_content

    # No existing Phylum pull request comments found
    return None


def post_azure_comment(azure_token: str, comment: str) -> None:
    """Post a comment on an Azure Repos Pull Request (PR).

    The comment will only be created if there isn't already a Phylum comment
    or if the most recently posted Phylum comment does not contain the same content.
    """
    if not is_in_pr():
        msg = "Must be working in the context of a pull request pipeline"
        raise SystemExit(msg)

    LOG.info("Checking pull request threads for existing comment content to avoid duplication ...")
    most_recent_phylum_comment = get_most_recent_phylum_comment_azure(azure_token)
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
    pr_threads_url = get_azure_pr_threads_url()
    headers = get_headers(azure_token)
    query_params, query_params_encoded = get_query_params()
    req_body = {
        "comments": [
            {
                "parentCommentId": 0,
                "content": comment,
                "commentType": "text",
            },
        ],
        "status": "active",
    }
    LOG.info("Creating new pull request thread with POST URL: %s?%s ...", pr_threads_url, query_params_encoded)
    resp = requests.post(pr_threads_url, params=query_params, json=req_body, headers=headers, timeout=REQ_TIMEOUT)
    resp.raise_for_status()


def get_headers(azure_token: str) -> dict[str, str]:
    """Provide the headers to use when making Azure Pipelines API calls."""
    # To provide the personal access token through an HTTP header, you must first convert it to a base64 string.
    # NOTE: The colon (`:`) appended to the front of the PAT is intentional as it is expected by the endpoints.
    b64_ado_pat = base64.b64encode(bytes(f":{azure_token}", encoding="ascii")).decode(encoding="ascii")
    headers = {
        "User-Agent": PHYLUM_USER_AGENT,
        "Authorization": f"Basic {b64_ado_pat}",
    }
    return headers


def get_query_params() -> tuple[dict, str]:
    """Provide the query parameters to use when making Azure Pipelines API calls."""
    # This is the latest available API version a/o SEP 2023. While it is a "preview" version, it was chosen to
    # lean forward in an effort to maintain relevance and recency for a longer period of time going forward.
    # It does appear that the APIs for PR Threads are stable between this version and the previous major version
    # with accessible documentation.
    api_version = "7.2-preview.1"
    query_params = {"api-version": api_version}
    query_params_encoded = urllib.parse.urlencode(query_params, safe="/", quote_via=urllib.parse.quote)
    return query_params, query_params_encoded


def get_azure_pr_threads_url() -> str:
    """Get the Azure Pipelines pull request threads API URL and return it."""
    # API References:
    #   * Basics: https://learn.microsoft.com/rest/api/azure/devops
    #   * PR Threads - List: https://learn.microsoft.com/rest/api/azure/devops/git/pull-request-threads/list
    #   * PR Threads - Create: https://learn.microsoft.com/rest/api/azure/devops/git/pull-request-threads/create

    if not is_in_pr():
        msg = "Must be working in the context of a pull request pipeline"
        raise SystemExit(msg)

    # SYSTEM_TEAMPROJECT provides the name that corresponds to SYSTEM_TEAMPROJECTID.
    # SYSTEM_TEAMPROJECTID is used in the API calls since it should never change.
    team_project_id = os.getenv("SYSTEM_TEAMPROJECTID")
    instance = os.getenv("SYSTEM_TEAMFOUNDATIONCOLLECTIONURI")
    repo_id = os.getenv("BUILD_REPOSITORY_ID")
    pr_id = os.getenv("SYSTEM_PULLREQUEST_PULLREQUESTID")
    resource_path = f"/_apis/git/repositories/{repo_id}/pullRequests/{pr_id}/threads"

    # This is the same endpoint for listing all PR threads (GET) and creating new ones (POST)
    pr_threads_url = f"{instance}{team_project_id}{resource_path}"
    return pr_threads_url


def get_github_comments_url() -> str:
    """Get the GitHub comments API URL and return it."""
    github_api_root_url = "https://api.github.com"

    owner_repo = os.getenv("BUILD_REPOSITORY_NAME")
    if not owner_repo:
        msg = "The GitHub owner and repository could not be found."
        raise SystemExit(msg)
    pr_number = os.getenv("SYSTEM_PULLREQUEST_PULLREQUESTNUMBER")
    if not pr_number:
        msg = "The GitHub PR number could not be found."
        raise SystemExit(msg)

    # API Reference: https://docs.github.com/en/rest/issues/comments
    # This is the same endpoint for listing all PR comments (GET) and creating new ones (POST)
    pr_comments_api_endpoint = f"/repos/{owner_repo}/issues/{pr_number}/comments"
    comments_url = f"{github_api_root_url}{pr_comments_api_endpoint}"
    return comments_url
