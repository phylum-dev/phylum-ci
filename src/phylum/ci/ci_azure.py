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
import base64
import os
import subprocess
import sys
import urllib.parse
from argparse import Namespace
from pathlib import Path
from typing import Optional

import requests

from phylum.ci.ci_base import CIBase, git_remote
from phylum.ci.ci_github import post_github_comment
from phylum.ci.constants import PHYLUM_HEADER
from phylum.constants import REQ_TIMEOUT

AZURE_PAT_ERR_MSG = """
An Azure DevOps token with API access is required to use the API (e.g., to post comments).
This can be the default `System.AccessToken` provided automatically at the start
of each build for the scoped build identity or a personal access token (PAT).
A PAT needs at least the `Pull Request Threads` scope (read & write).
See the Azure DevOps documentation for using personal access tokens:
  * https://learn.microsoft.com/azure/devops/organizations/accounts/use-personal-access-tokens-to-authenticate
The `System.AccessToken` scoped build identity needs at least the `Contribute to pull requests` permission.
See the Azure DevOps documentation for using the `System.AccessToken`:
  * https://learn.microsoft.com/azure/devops/pipelines/build/variables#systemaccesstoken
  * https://learn.microsoft.com/azure/devops/pipelines/process/access-tokens#job-authorization-scope
"""

GITHUB_PAT_ERR_MSG = """
A GitHub token with API access is required to use the API (e.g., to post comments).
This can be either a classic or fine-grained personal access token (PAT).
A classic PAT needs the `repo` scope or minimally the `public_repo` scope if private repositories are not used.
A fine-grained PAT needs read access to `metadata` and read/write access to `pull requests`.
See the GitHub Token Documentation for more info:
  * https://docs.github.com/authentication/keeping-your-account-and-data-secure/creating-a-personal-access-token
  * https://docs.github.com/rest/overview/permissions-required-for-fine-grained-personal-access-tokens
  * https://docs.github.com/developers/apps/building-oauth-apps/scopes-for-oauth-apps#available-scopes
"""


class CIAzure(CIBase):
    """Provide methods for an Azure Pipelines CI environment."""

    def __init__(self, args: Namespace) -> None:
        super().__init__(args)
        self.ci_platform_name = "Azure Pipelines"

    def _check_prerequisites(self) -> None:
        """Ensure the necessary pre-requisites are met and bail when they aren't.

        These are the current pre-requisites for operating within an Azure Pipelines Environment:
          * The environment must actually be within Azure Pipelines
          * The environment must be part of a Pull Request (PR) pipeline
          * An token providing API access is available to match the triggering repo
            * An Azure token for Azure Repos Git
            * A GitHub token for GitHub hosted repos
        """
        super()._check_prerequisites()

        # References:
        # https://github.com/watson/ci-info/blob/master/vendors.json
        # https://learn.microsoft.com/azure/devops/pipelines/build/variables
        if os.getenv("SYSTEM_TEAMFOUNDATIONCOLLECTIONURI") is None:
            raise SystemExit(" [!] Must be working within the Azure Pipelines environment")
        if os.getenv("SYSTEM_PULLREQUEST_PULLREQUESTID") is None:
            print(" [+] Not in a Pull Request pipeline. Nothing to do. Exiting ...")
            sys.exit(0)

        self.triggering_repo = os.getenv("BUILD_REPOSITORY_PROVIDER", "unknown")
        print(f" [+] Triggering repository: {self.triggering_repo}")
        # "TfsGit" is the legacy name for "Azure Repos Git"
        if self.triggering_repo not in ["TfsGit", "GitHub"]:
            raise SystemExit(f" [!] Triggering repository `{self.triggering_repo}` not supported")

        azure_token = os.getenv("AZURE_TOKEN", "")
        if not azure_token and self.triggering_repo == "TfsGit":
            raise SystemExit(f" [!] An Azure token with API access must be set at `AZURE_TOKEN`: {AZURE_PAT_ERR_MSG}")
        self._azure_token = azure_token

        github_token = os.getenv("GITHUB_TOKEN", "")
        if not github_token and self.triggering_repo == "GitHub":
            raise SystemExit(f" [!] A GitHub token with API access must be set at `GITHUB_TOKEN`: {GITHUB_PAT_ERR_MSG}")
        self._github_token = github_token

    @property
    def azure_token(self) -> str:
        """Get the default `System.AccessToken` or custom Personal Access Token (PAT) in use."""
        return self._azure_token

    @property
    def github_token(self) -> str:
        """Get the custom Personal Access Token (PAT) in use."""
        return self._github_token

    @property
    def phylum_label(self) -> str:
        """Get a custom label for use when submitting jobs with `phylum analyze`."""
        pr_number = os.getenv("SYSTEM_PULLREQUEST_PULLREQUESTID", "unknown-number")
        pr_src_branch = os.getenv("SYSTEM_PULLREQUEST_SOURCEBRANCH", "unknown-ref")
        ref_prefix = "refs/heads/"
        if pr_src_branch.startswith(ref_prefix):
            pr_src_branch = pr_src_branch.replace(ref_prefix, "", 1)
        label = f"{self.ci_platform_name}_PR#{pr_number}_{pr_src_branch}"
        label = label.replace(" ", "-")
        return label

    # TODO: Use the `@functools.cached_property` decorator, introduced in Python 3.8, to avoid computing more than once.
    #       https://github.com/phylum-dev/phylum-ci/issues/18
    @property
    def common_lockfile_ancestor_commit(self) -> Optional[str]:
        """Find the common lockfile ancestor commit."""
        # There is no single predefined variable available to provide the PR base SHA.
        # Instead, it can be determined with a `git merge-base` command, like is done for the CINone implementation.
        # Reference: https://learn.microsoft.com/azure/devops/pipelines/build/variables
        pr_src_branch = os.getenv("SYSTEM_PULLREQUEST_SOURCEBRANCH", "")
        pr_tgt_branch = os.getenv("SYSTEM_PULLREQUEST_TARGETBRANCH", "")
        if not all([pr_src_branch, pr_tgt_branch]):
            raise SystemExit(" [!] SYSTEM_PULLREQUEST_SOURCEBRANCH and SYSTEM_PULLREQUEST_TARGETBRANCH must both exist")

        # Because the checkout step only fetches the bare minimum needed for the pipeline, and
        # because the PR merge commit is checked out in a "detached HEAD" state, it is necessary
        # to be explicit about the refs so that they can be found in this limited git repository.
        remote = git_remote()
        old_ref_prefix = "refs/heads/"
        new_ref_prefix = f"refs/remotes/{remote}/"
        if self.triggering_repo == "TfsGit":
            if pr_src_branch.startswith(old_ref_prefix):
                pr_src_branch = pr_src_branch.replace(old_ref_prefix, new_ref_prefix, 1)
            if pr_tgt_branch.startswith(old_ref_prefix):
                pr_tgt_branch = pr_tgt_branch.replace(old_ref_prefix, new_ref_prefix, 1)
        if self.triggering_repo == "GitHub":
            # The source and target branches from GitHub triggered repositories are simply the
            # branch name, without any prefix (e.g., `mybranch` instead of `refs/heads/mybranch`).
            pr_src_branch = f"{new_ref_prefix}{pr_src_branch}"
            pr_tgt_branch = f"{new_ref_prefix}{pr_tgt_branch}"

        cmd = ["git", "merge-base", pr_src_branch, pr_tgt_branch]
        try:
            common_ancestor_commit = subprocess.run(cmd, check=True, capture_output=True, text=True).stdout.strip()
            print(f" [+] Common lockfile ancestor commit: {common_ancestor_commit}")
        except subprocess.CalledProcessError as err:
            ref_url = "https://learn.microsoft.com/azure/devops/pipelines/yaml-schema/steps-checkout#shallow-fetch"
            print(f" [!] The common lockfile ancestor commit could not be found: {err}")
            print(f" [!] stdout:\n{err.stdout}")
            print(f" [!] stderr:\n{err.stderr}")
            print(f" [!] Ensure shallow fetch is disabled for repo checkouts: {ref_url}")
            common_ancestor_commit = None

        return common_ancestor_commit

    def _is_lockfile_changed(self, lockfile: Path) -> bool:
        """Predicate for detecting if the given lockfile has changed."""
        pr_src_branch = os.getenv("SYSTEM_PULLREQUEST_SOURCEBRANCH")
        pr_tgt_branch = os.getenv("SYSTEM_PULLREQUEST_TARGETBRANCH")
        pr_base_sha = self.common_lockfile_ancestor_commit
        print(f" [+] SYSTEM_PULLREQUEST_SOURCEBRANCH: {pr_src_branch}")
        print(f" [+] SYSTEM_PULLREQUEST_TARGETBRANCH: {pr_tgt_branch}")
        print(f" [+] PR base SHA: {pr_base_sha}")

        # Assume no change when there isn't enough information to tell
        if pr_base_sha is None:
            return False

        # `--exit-code` will make git exit with 1 if there were differences while 0 means no differences.
        # Any other exit code is an error and a reason to re-raise.
        cmd = ["git", "diff", "--exit-code", "--quiet", pr_base_sha, "--", str(lockfile.resolve())]
        ret = subprocess.run(cmd, check=False)
        if ret.returncode == 0:
            return False
        if ret.returncode == 1:
            return True
        # Reference: https://learn.microsoft.com/azure/devops/pipelines/yaml-schema/steps-checkout
        print(" [!] Consider changing the `fetchDepth` property in CI settings to clone/fetch more branch history")
        ret.check_returncode()
        return False  # unreachable code but this makes mypy happy

    def post_output(self) -> None:
        """Post the output of the analysis.

        Post output directly in the logs regardless of the trigger type.
        Post output as a comment on the Azure Repos Pull Request (PR) for PR triggers and Azure Repos hosted repos.
        Post output as a comment on the GitHub PR for PR triggers and GitHub hosted repos.
        """
        super().post_output()

        if self.triggering_repo == "TfsGit":
            post_azure_comment(self.azure_token, self.analysis_output)
        elif self.triggering_repo == "GitHub":
            github_api_root_url = "https://api.github.com"

            owner_repo = os.getenv("BUILD_REPOSITORY_NAME")
            if not owner_repo:
                raise SystemExit(" [!] The GitHub owner and repository could not be found.")
            pr_number = os.getenv("SYSTEM_PULLREQUEST_PULLREQUESTNUMBER")
            if not pr_number:
                raise SystemExit(" [!] The GitHub PR number could not be found.")

            # API Reference: https://docs.github.com/en/rest/issues/comments
            # This is the same endpoint for listing all PR comments (GET) and creating new ones (POST)
            pr_comments_api_endpoint = f"/repos/{owner_repo}/issues/{pr_number}/comments"
            comments_url = f"{github_api_root_url}{pr_comments_api_endpoint}"

            post_github_comment(comments_url, self.github_token, self.analysis_output)


def post_azure_comment(azure_token: str, comment: str) -> None:
    """Post a comment on an Azure Repos Pull Request (PR).

    The comment will only be created if there isn't already a Phylum comment
    or if the most recently posted Phylum comment does not contain the same content.
    """
    # API References:
    #   * Basics: https://learn.microsoft.com/rest/api/azure/devops
    #   * PR Threads - List: https://learn.microsoft.com/rest/api/azure/devops/git/pull-request-threads/list
    #   * PR Threads - Create: https://learn.microsoft.com/rest/api/azure/devops/git/pull-request-threads/create

    # This is the latest available API version a/o NOV 2022. While it is a "preview" version, it was chosen to
    # lean forward in an effort to maintain relevance and recency for a longer period of time going forward.
    # It does appear that the APIs for PR Threads are stable between this version and the previous major version
    # with accessible documentation.
    api_version = "7.1-preview.1"

    # SYSTEM_TEAMPROJECT provides the name that corresponds to SYSTEM_TEAMPROJECTID.
    # SYSTEM_TEAMPROJECTID is used in the API calls since it should never change.
    team_project_id = os.getenv("SYSTEM_TEAMPROJECTID")
    team_project_name = os.getenv("SYSTEM_TEAMPROJECT")
    instance = os.getenv("SYSTEM_TEAMFOUNDATIONCOLLECTIONURI")
    repo_id = os.getenv("BUILD_REPOSITORY_ID")
    pr_id = os.getenv("SYSTEM_PULLREQUEST_PULLREQUESTID")
    resource_path = f"/_apis/git/repositories/{repo_id}/pullRequests/{pr_id}/threads"

    # This is the same endpoint for listing all PR threads (GET) and creating new ones (POST)
    pr_threads_url = f"{instance}{team_project_id}{resource_path}"

    # To provide the personal access token through an HTTP header, you must first convert it to a base64 string.
    # NOTE: The colon (`:`) appended to the front of the PAT is intentional as it is expected by the endpoints.
    b64_ado_pat = base64.b64encode(bytes(f":{azure_token}", encoding="ascii")).decode(encoding="ascii")

    query_params = {"api-version": api_version}
    headers = {"Authorization": f"Basic {b64_ado_pat}"}

    query_params_encoded = urllib.parse.urlencode(query_params, safe="/", quote_via=urllib.parse.quote)
    print(f" [*] Getting list of all current PR threads with GET URL: {pr_threads_url}?{query_params_encoded} ...")
    print(f" [-] The team project ID {team_project_id} maps to name: {team_project_name}")
    resp = requests.get(pr_threads_url, params=query_params, headers=headers, timeout=REQ_TIMEOUT)
    resp.raise_for_status()
    if resp.status_code != requests.codes.OK:
        raise SystemExit(f" [!] Are the permissions on the Azure token `AZURE_TOKEN` correct? {AZURE_PAT_ERR_MSG}")
    pr_threads = resp.json()

    print(" [*] Checking pull request threads for existing comment content to avoid duplication ...")
    pr_threads_count = pr_threads.get("count", 0)
    print(f" [+] PR threads found: {pr_threads_count}")
    if pr_threads_count:
        pr_threads = pr_threads.get("value", [])
        is_phylum_comment_found = False
        # NOTE: The API call returns the comments in ascending order by ID...thus the need to reverse the list.
        #       Detecting Phylum comments is done simply by looking for those that start with a known string value.
        #       We only care about the most recent Phylum comment.
        for pr_thread in reversed(pr_threads):
            thread_comments = pr_thread.get("comments", [])
            for thread_comment in thread_comments:
                # All Phylum generated comments will be the first in their own thread
                if thread_comment.get("id", 0) != 1:
                    continue
                if thread_comment.get("content", "").lstrip().startswith(PHYLUM_HEADER.strip()):
                    print(" [+] The most recently posted Phylum pull request comment was found.")
                    is_phylum_comment_found = True
                    if thread_comment.get("content", "") == comment:
                        print(" [+] It contains the same content as the current analysis. Nothing to do.")
                        return
                    print(" [+] It does not contain the same content as the current analysis.")
                    break
            if is_phylum_comment_found:
                break
        if not is_phylum_comment_found:
            print(" [+] No existing Phylum pull request comments found.")

    # If we got here, then the most recent Phylum PR comment does not match the current analysis output or
    # there were no Phylum PR comments. Either way, create a new PR comment.
    req_body = {
        "comments": [
            {
                "parentCommentId": 0,
                "content": comment,
                "commentType": "text",
            }
        ],
        "status": "active",
    }
    print(f" [*] Creating new pull request thread with POST URL: {pr_threads_url}?{query_params_encoded} ...")
    resp = requests.post(pr_threads_url, params=query_params, json=req_body, headers=headers, timeout=REQ_TIMEOUT)
    resp.raise_for_status()
