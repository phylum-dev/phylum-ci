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
import shlex
import subprocess
import urllib.parse
from argparse import Namespace
from functools import lru_cache
from pathlib import Path
from typing import Optional

import requests
from backports.cached_property import cached_property

from phylum.ci.ci_base import CIBase
from phylum.ci.ci_github import post_github_comment
from phylum.ci.constants import PHYLUM_HEADER
from phylum.ci.git import git_default_branch_name, git_hash_object, git_remote
from phylum.constants import PHYLUM_USER_AGENT, REQ_TIMEOUT

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
    to determine the lockfile changes is correct. It also helps to ensure output is not
    attempted to be posted when NOT in the context of a review.
    """
    # References:
    # https://github.com/watson/ci-info/blob/master/vendors.json
    # https://learn.microsoft.com/azure/devops/pipelines/build/variables
    return bool(os.getenv("SYSTEM_PULLREQUEST_PULLREQUESTID"))


class CIAzure(CIBase):
    """Provide methods for an Azure Pipelines CI environment."""

    def __init__(self, args: Namespace) -> None:
        super().__init__(args)
        self.ci_platform_name = "Azure Pipelines"
        if is_in_pr():
            print(" [-] Pipeline context: PR trigger")
        else:
            # There are other types of events that trigger pipelines, but only PR and CI triggers are supported.
            # Reference: https://learn.microsoft.com/azure/devops/pipelines/build/triggers
            print(" [-] Pipeline context: CI trigger")

    def _check_prerequisites(self) -> None:
        """Ensure the necessary pre-requisites are met and bail when they aren't.

        These are the current pre-requisites for operating within an Azure Pipelines Environment:
          * The environment must actually be within Azure Pipelines
          * A token providing API access is available to match the triggering repo when operating in a PR pipeline
            * An Azure token for Azure Repos Git
            * A GitHub token for GitHub hosted repos
        """
        super()._check_prerequisites()

        # References:
        # https://github.com/watson/ci-info/blob/master/vendors.json
        # https://learn.microsoft.com/azure/devops/pipelines/build/variables
        if os.getenv("SYSTEM_TEAMFOUNDATIONCOLLECTIONURI") is None:
            raise SystemExit(" [!] Must be working within the Azure Pipelines environment")

        self.triggering_repo = os.getenv("BUILD_REPOSITORY_PROVIDER", "unknown")
        print(f" [+] Triggering repository: {self.triggering_repo}")
        # "TfsGit" is the legacy name for "Azure Repos Git"
        if self.triggering_repo not in ["TfsGit", "GitHub"]:
            raise SystemExit(f" [!] Triggering repository `{self.triggering_repo}` not supported")

        azure_token = os.getenv("AZURE_TOKEN", "")
        if not azure_token and self.triggering_repo == "TfsGit" and is_in_pr():
            raise SystemExit(f" [!] An Azure token with API access must be set at `AZURE_TOKEN`: {AZURE_PAT_ERR_MSG}")
        self._azure_token = azure_token

        github_token = os.getenv("GITHUB_TOKEN", "")
        if not github_token and self.triggering_repo == "GitHub" and is_in_pr():
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
        if is_in_pr():
            pr_number = os.getenv("SYSTEM_PULLREQUEST_PULLREQUESTID", "unknown-number")
            pr_src_branch = os.getenv("SYSTEM_PULLREQUEST_SOURCEBRANCH", "unknown-ref")
            ref_prefix = "refs/heads/"
            # Starting with Python 3.9, the str.removeprefix() method was introduced to do this same thing
            if pr_src_branch.startswith(ref_prefix):
                pr_src_branch = pr_src_branch.replace(ref_prefix, "", 1)
            label = f"{self.ci_platform_name}_PR#{pr_number}_{pr_src_branch}"
        else:
            current_branch = os.getenv("BUILD_SOURCEBRANCHNAME", "unknown-branch")
            lockfile_hash_object = git_hash_object(self.lockfile)
            label = f"{self.ci_platform_name}_{current_branch}_{lockfile_hash_object[:7]}"

        label = label.replace(" ", "-")
        return label

    @cached_property
    def common_lockfile_ancestor_commit(self) -> Optional[str]:
        """Find the common lockfile ancestor commit."""
        remote = git_remote()

        if is_in_pr():
            # There is no single predefined variable available to provide the PR base SHA.
            # Instead, it can be determined with a `git merge-base` command, like is done for the CINone implementation.
            # Reference: https://learn.microsoft.com/azure/devops/pipelines/build/variables
            src_branch = os.getenv("SYSTEM_PULLREQUEST_SOURCEBRANCH", "")
            tgt_branch = os.getenv("SYSTEM_PULLREQUEST_TARGETBRANCH", "")
            if not src_branch:
                raise SystemExit(" [!] The SYSTEM_PULLREQUEST_SOURCEBRANCH environment variable must exist and be set")
            if not tgt_branch:
                raise SystemExit(" [!] The SYSTEM_PULLREQUEST_TARGETBRANCH environment variable must exist and be set")
            print(f" [+] SYSTEM_PULLREQUEST_SOURCEBRANCH: {src_branch}")
            print(f" [+] SYSTEM_PULLREQUEST_TARGETBRANCH: {tgt_branch}")
        else:
            # Assume the working context is within a CI triggered build environment when not in a PR.

            src_branch = os.getenv("BUILD_SOURCEBRANCHNAME", "")
            if not src_branch:
                raise SystemExit(" [!] The BUILD_SOURCEBRANCHNAME environment variable must exist and be set")
            print(f" [+] BUILD_SOURCEBRANCHNAME: {src_branch}")

            # This is a best effort attempt since it is finding the merge base between the current commit
            # and the default branch instead of finding the exact commit from which the branch was created.
            tgt_branch = f"refs/remotes/{remote}/HEAD"

            # If the current commit is on the default branch, then the merge base will be the same
            # as the current commit and it won't be possible to provide a useful common lockfile
            # ancestor commit. In this case, it is better to force analysis of the lockfile and
            # consider *all* dependencies in analysis results instead of just the newly added ones.
            if src_branch == git_default_branch_name(remote):
                print(" [+] Source branch is same as default branch. Proceeding with analysis of all dependencies ...")
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
        shell_escaped_cmd = " ".join(shlex.quote(arg) for arg in cmd)
        print(f" [*] Finding common lockfile ancestor commit with command: {shell_escaped_cmd}")
        try:
            common_ancestor_commit = subprocess.run(cmd, check=True, capture_output=True, text=True).stdout.strip()
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

        if not is_in_pr():
            # Can't post the output to the PR when there is no PR
            return

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
    headers = {
        "User-Agent": PHYLUM_USER_AGENT,
        "Authorization": f"Basic {b64_ado_pat}",
    }

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
