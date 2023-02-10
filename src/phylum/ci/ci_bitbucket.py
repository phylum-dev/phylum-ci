"""Define an implementation for the Bitbucket Pipelines platform.

Bitbucket References:
  * https://support.atlassian.com/bitbucket-cloud/
  * https://support.atlassian.com/bitbucket-cloud/resources/
  * https://support.atlassian.com/bitbucket-cloud/docs/using-access-tokens/
  * https://support.atlassian.com/bitbucket-cloud/docs/bitbucket-pipelines-configuration-reference/
  * https://support.atlassian.com/bitbucket-cloud/docs/pipeline-start-conditions/
  * https://support.atlassian.com/bitbucket-cloud/docs/use-docker-images-as-build-environments/
  * https://support.atlassian.com/bitbucket-cloud/docs/variables-and-secrets/
  * https://support.atlassian.com/bitbucket-cloud/docs/git-clone-behavior/
  * https://developer.atlassian.com/cloud/bitbucket/rest/intro/
  * https://developer.atlassian.com/cloud/bitbucket/rest/intro/#access-tokens
  * https://developer.atlassian.com/cloud/bitbucket/rest/intro/#repository-object-and-uuid
  * https://developer.atlassian.com/cloud/bitbucket/rest/intro/#filtering
  * https://developer.atlassian.com/cloud/bitbucket/rest/api-group-pullrequests/
  * https://developer.atlassian.com/cloud/bitbucket/rest/intro/#pullrequest
"""
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
from phylum.ci.constants import PHYLUM_HEADER
from phylum.ci.git import git_default_branch_name, git_hash_object, git_remote
from phylum.constants import PHYLUM_USER_AGENT, REQ_TIMEOUT

BITBUCKET_TOK_ERR_MSG = """
A Bitbucket access token with API access is required to use the API (e.g., to post comments).
This can be a repository, project, or workspace token with at least the `pullrequest` scope.
See the Bitbucket documentation for using access tokens:
  * https://developer.atlassian.com/cloud/bitbucket/rest/intro/#access-tokens
"""


@lru_cache(maxsize=1)
def is_in_pr() -> bool:
    """Indicate if the integration is operating in the context of a pull request pipeline.

    Bitbucket allows for the possibility of running pipelines in different contexts:
        * On every push, for the last commit in the push (e.g., branch and default pipelines)
        * For pull requests (e.g., pull request pipelines)

    Knowing when the context is within a pull request helps to ensure the logic used
    to determine the lockfile changes is correct. It also helps to ensure output is not
    attempted to be posted when NOT in the context of a review.
    """
    # References:
    # https://github.com/watson/ci-info/blob/master/vendors.json
    # https://support.atlassian.com/bitbucket-cloud/docs/pipeline-start-conditions/
    # https://support.atlassian.com/bitbucket-cloud/docs/variables-and-secrets/
    return bool(os.getenv("BITBUCKET_PR_ID"))


class CIBitbucket(CIBase):
    """Provide methods for a Bitbucket Pipelines environment."""

    def __init__(self, args: Namespace) -> None:
        super().__init__(args)
        self.ci_platform_name = "Bitbucket Pipelines"
        if is_in_pr():
            print(" [-] Pipeline context: pull request pipeline")
        else:
            print(" [-] Pipeline context: branch pipeline")

    def _check_prerequisites(self) -> None:
        """Ensure the necessary pre-requisites are met and bail when they aren't.

        These are the current pre-requisites for operating within a Bitbucket Pipelines Environment:
          * The environment must actually be within Bitbucket Pipelines
          * A Bitbucket token providing API access is available when operating in an PR pipeline
        """
        super()._check_prerequisites()

        # References:
        # https://github.com/watson/ci-info/blob/master/vendors.json
        # https://support.atlassian.com/bitbucket-cloud/docs/variables-and-secrets/
        if os.getenv("BITBUCKET_COMMIT") is None:
            raise SystemExit(" [!] Must be working within the Bitbucket Pipelines environment")

        # A Bitbucket token with API access is required to use the API (e.g., to post comments).
        # This can be a repository, project, or workspace access token.
        # See the Bitbucket Token Overview Documentation for info:
        # https://developer.atlassian.com/cloud/bitbucket/rest/intro/#access-tokens
        bitbucket_token = os.getenv("BITBUCKET_TOKEN", "")
        if not bitbucket_token and is_in_pr():
            raise SystemExit(f" [!] A Bitbucket access token must be set at `BITBUCKET_TOKEN`: {BITBUCKET_TOK_ERR_MSG}")
        self._bitbucket_token = bitbucket_token

    @property
    def bitbucket_token(self) -> str:
        """Get the Bitbucket token (e.g., repository, project, or workspace access token)."""
        return self._bitbucket_token

    @property
    def phylum_label(self) -> str:
        """Get a custom label for use when submitting jobs with `phylum analyze`."""
        if is_in_pr():
            pr_id = os.getenv("BITBUCKET_PR_ID", "unknown-ID")
            pr_title = os.getenv("BITBUCKET_BRANCH", "unknown-branch")
            label = f"{self.ci_platform_name}_PR#{pr_id}_{pr_title}"
        else:
            current_branch = os.getenv("BITBUCKET_BRANCH", "unknown-branch")
            lockfile_hash_object = git_hash_object(self.lockfile)
            label = f"{self.ci_platform_name}_{current_branch}_{lockfile_hash_object[:7]}"

        label = label.replace(" ", "-")
        return label

    @cached_property
    def common_lockfile_ancestor_commit(self) -> Optional[str]:
        """Find the common lockfile ancestor commit.

        Some pre-defined variables are used: https://support.atlassian.com/bitbucket-cloud/docs/variables-and-secrets/
        """
        remote = git_remote()

        if is_in_pr():
            # There is no single predefined variable available to provide the PR base SHA.
            # Instead, it can be determined with a `git merge-base` command, like is done for the CINone implementation.
            # Reference: https://support.atlassian.com/bitbucket-cloud/docs/variables-and-secrets/
            src_branch = os.getenv("BITBUCKET_BRANCH", "")
            tgt_branch = os.getenv("BITBUCKET_PR_DESTINATION_BRANCH", "")
            if not src_branch:
                raise SystemExit(" [!] The BITBUCKET_BRANCH environment variable must exist and be set")
            if not tgt_branch:
                raise SystemExit(" [!] The BITBUCKET_PR_DESTINATION_BRANCH environment variable must exist and be set")
            print(f" [+] BITBUCKET_BRANCH: {src_branch}")
            print(f" [+] BITBUCKET_PR_DESTINATION_BRANCH: {tgt_branch}")
        else:
            # Assume the working context is within a branch-based CI triggered
            # build environment when not in a PR (no tag or custom pipelines).
            src_branch = os.getenv("BITBUCKET_BRANCH", "")
            if not src_branch:
                raise SystemExit(" [!] The BITBUCKET_BRANCH environment variable must exist and be set")
            print(f" [+] BITBUCKET_BRANCH: {src_branch}")

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
        new_ref_prefix = f"refs/remotes/{remote}/"
        # The source branch is simply the branch name, without any prefix
        # (e.g., `mybranch` instead of `refs/remotes/origin/mybranch`).
        src_branch = f"{new_ref_prefix}{src_branch}"
        if is_in_pr():
            # The target branch is also simply the branch name, without any prefix, but only when in a PR context.
            tgt_branch = f"{new_ref_prefix}{tgt_branch}"

        cmd = ["git", "merge-base", src_branch, tgt_branch]
        shell_escaped_cmd = " ".join(shlex.quote(arg) for arg in cmd)
        print(f" [*] Finding common lockfile ancestor commit with command: {shell_escaped_cmd}")
        try:
            common_ancestor_commit = subprocess.run(cmd, check=True, capture_output=True, text=True).stdout.strip()
        except subprocess.CalledProcessError as err:
            ref_url = "https://support.atlassian.com/bitbucket-cloud/docs/git-clone-behavior/"
            print(f" [!] The common lockfile ancestor commit could not be found: {err}")
            print(f" [!] stdout:\n{err.stdout}")
            print(f" [!] stderr:\n{err.stderr}")
            print(f" [!] Ensure the git strategy is set to `full clone depth` for repo checkouts: {ref_url}")
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
        # Reference: https://support.atlassian.com/bitbucket-cloud/docs/git-clone-behavior/
        print(" [!] Consider changing the `clone depth` variable in CI settings to clone/fetch more branch history")
        ret.check_returncode()
        return False  # unreachable code but this makes mypy happy

    def post_output(self) -> None:
        """Post the output of the analysis.

        Post output directly in the logs regardless of the pipeline context.
        Post output as a comment on the Bitbucket Pipelines Pull Request (PR)
        when operating in a pull request pipeline.
        """
        super().post_output()

        if not is_in_pr():
            # Can't post the output to the PR when there is no PR
            return

        # API Reference: https://developer.atlassian.com/cloud/bitbucket/rest/api-group-pullrequests/
        bitbucket_api_root_url = "https://api.bitbucket.org"

        # BITBUCKET_REPO_FULL_NAME provides the workspace and repository name that corresponds to BITBUCKET_REPO_UUID.
        # BITBUCKET_REPO_UUID is used in the API calls since it should never change.
        repo_uuid = os.getenv("BITBUCKET_REPO_UUID")
        repo_full_name = os.getenv("BITBUCKET_REPO_FULL_NAME")

        pr_id = os.getenv("BITBUCKET_PR_ID")

        # This is the same endpoint for listing all PR comments (GET) and creating new ones (POST)
        # NOTE: It is possible to make calls with the repository UUID and an empty workspace:
        #       https://api.bitbucket.org/2.0/repositories/{}/{repo_uuid}/pullrequests/{pull_request_id}/comments
        #       The braces (even the empty braces) are required in the construction of the endpoint request.
        #       Reference: https://developer.atlassian.com/cloud/bitbucket/rest/intro/#repository-object-and-uuid
        pr_comments_api_endpoint = f"/2.0/repositories/{{}}/{repo_uuid}/pullrequests/{pr_id}/comments"
        url = f"{bitbucket_api_root_url}{pr_comments_api_endpoint}"

        headers = {
            "User-Agent": PHYLUM_USER_AGENT,
            "Accept": "application/json",
            "Authorization": f"Bearer {self.bitbucket_token}",
        }

        # Comments are returned in chronological order. It is possible to use query parameters to our advantage.
        # Reference: https://developer.atlassian.com/cloud/bitbucket/rest/intro/#filtering
        query_params = {
            # Reverse the order
            "sort": "-updated_on",
            # Filter out any comments that are not produced by this integration
            "q": f'content.raw~"{PHYLUM_HEADER}"',
            # Only return the field containing the raw comment text
            "fields": "values.content.raw",
            # Only return the most recently posted Phylum-generated comment
            "pagelen": "1",
        }

        query_params_encoded = urllib.parse.urlencode(query_params, safe="/", quote_via=urllib.parse.quote)
        print(f" [*] Getting all current pull request comments with GET URL: {url}?{query_params_encoded} ...")
        print(f" [-] The repository UUID {repo_uuid} maps to workspace and repository name: {repo_full_name}")
        req = requests.get(url, params=query_params, headers=headers, timeout=REQ_TIMEOUT)
        req.raise_for_status()
        pr_comments = req.json()

        print(" [*] Checking existing pull request comments for existing content to avoid duplication ...")
        if pr_comments.get("values"):
            # NOTE: The API call normally returns all the comments in chronological order. Query parameters are used to
            #       only return the most recent Phylum comment, if one exists, since this is the only one we care about.
            print(" [+] The most recently posted Phylum pull request comment was found.")
            pr_comment = pr_comments.get("values")[0]
            if pr_comment.get("content", {}).get("raw", "") == self.analysis_output:
                print(" [+] It contains the same content as the current analysis. Nothing to do.")
                return
            print(" [+] It does not contain the same content as the current analysis.")
        else:
            print(" [+] No existing Phylum pull request comments found.")

        # If we got here, then the most recent Phylum PR comment does not match the current analysis output or
        # there were no Phylum PR comments. Either way, create a new PR comment.
        data = {"content": {"raw": self.analysis_output}}
        headers["Content-Type"] = "application/json"
        print(f" [*] Creating new pull request comment with POST URL: {url} ...")
        response = requests.post(url, json=data, headers=headers, timeout=REQ_TIMEOUT)
        response.raise_for_status()