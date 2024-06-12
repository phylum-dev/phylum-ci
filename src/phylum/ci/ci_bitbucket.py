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

from argparse import Namespace
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
from phylum.ci.git import git_default_branch_name, git_remote
from phylum.constants import PHYLUM_HEADER, PHYLUM_USER_AGENT, REQ_TIMEOUT
from phylum.exceptions import pprint_subprocess_error
from phylum.logger import LOG

BITBUCKET_TOK_ERR_MSG = """
A Bitbucket access token with API access is required to use the
API (e.g., to post comments). This can be a repository, project,
or workspace token with at least the `pullrequest` scope.

See Bitbucket documentation for using access tokens:
  * https://developer.atlassian.com/cloud/bitbucket/rest/intro/#access-tokens
"""


@lru_cache(maxsize=1)
def is_in_pr() -> bool:
    """Indicate if the integration is operating in the context of a pull request pipeline.

    Bitbucket allows for the possibility of running pipelines in different contexts:
      * On every push, for the last commit in the push (e.g., branch and default pipelines)
      * For pull requests (e.g., pull request pipelines)

    Knowing when the context is within a pull request helps to ensure the logic used
    to determine the dependency file changes is correct. It also helps to ensure output
    is not attempted to be posted when NOT in the context of a review.
    """
    # References:
    # https://github.com/watson/ci-info/blob/master/vendors.json
    # https://support.atlassian.com/bitbucket-cloud/docs/pipeline-start-conditions/
    # https://support.atlassian.com/bitbucket-cloud/docs/variables-and-secrets/
    return bool(os.getenv("BITBUCKET_PR_ID"))


class CIBitbucket(CIBase):
    """Provide methods for a Bitbucket Pipelines environment."""

    def __init__(self, args: Namespace) -> None:  # noqa: D107 ; the base __init__ docstring is better here
        super().__init__(args)
        self.ci_platform_name = "Bitbucket Pipelines"
        if is_in_pr():
            LOG.debug("Pipeline context: pull request pipeline")
        else:
            LOG.debug("Pipeline context: branch pipeline")

    def _check_prerequisites(self) -> None:
        """Ensure the necessary prerequisites are met and bail when they aren't.

        These are the current prerequisites for operating within a Bitbucket Pipelines Environment:
          * The environment must actually be within Bitbucket Pipelines
          * A Bitbucket token providing API access is available when operating in a PR pipeline
            * Unless comment generation is skipped
        """
        super()._check_prerequisites()

        # References:
        # https://github.com/watson/ci-info/blob/master/vendors.json
        # https://support.atlassian.com/bitbucket-cloud/docs/variables-and-secrets/
        if os.getenv("BITBUCKET_COMMIT") is None:
            msg = "Must be working within the Bitbucket Pipelines environment"
            raise SystemExit(msg)

        # A Bitbucket token with API access is required to use the API (e.g., to post comments).
        # This can be a repository, project, or workspace access token.
        # See the Bitbucket Token Overview Documentation for info:
        # https://developer.atlassian.com/cloud/bitbucket/rest/intro/#access-tokens
        bitbucket_token = os.getenv("BITBUCKET_TOKEN", "")
        if not bitbucket_token and is_in_pr() and not self.skip_comments:
            msg = f"A Bitbucket access token must be set at `BITBUCKET_TOKEN`: {BITBUCKET_TOK_ERR_MSG}"
            raise SystemExit(msg)
        self._bitbucket_token = bitbucket_token

    @property
    def bitbucket_token(self) -> str:
        """Get the Bitbucket token (e.g., repository, project, or workspace access token)."""
        return self._bitbucket_token

    @cached_property
    def phylum_label(self) -> str:
        """Get a custom label for use when submitting jobs for analysis."""
        if is_in_pr():
            pr_id = os.getenv("BITBUCKET_PR_ID", "unknown-ID")
            pr_src_branch = os.getenv("BITBUCKET_BRANCH", "unknown-branch")
            label = f"{self.ci_platform_name}_PR#{pr_id}_{pr_src_branch}"
        else:
            current_branch = os.getenv("BITBUCKET_BRANCH", "unknown-branch")
            label = f"{self.ci_platform_name}_{current_branch}_{self.depfile_hash_object}"

        label = re.sub(r"\s+", "-", label)
        return label

    @cached_property
    def common_ancestor_commit(self) -> Optional[str]:
        """Find the common ancestor commit.

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
                msg = "The BITBUCKET_BRANCH environment variable must exist and be set"
                raise SystemExit(msg)
            if not tgt_branch:
                msg = "The BITBUCKET_PR_DESTINATION_BRANCH environment variable must exist and be set"
                raise SystemExit(msg)
            LOG.debug("BITBUCKET_BRANCH: %s", src_branch)
            LOG.debug("BITBUCKET_PR_DESTINATION_BRANCH: %s", tgt_branch)
        else:
            # Assume the working context is within a branch-based CI triggered
            # build environment when not in a PR (no tag or custom pipelines).
            src_branch = os.getenv("BITBUCKET_BRANCH", "")
            if not src_branch:
                msg = "The BITBUCKET_BRANCH environment variable must exist and be set"
                raise SystemExit(msg)
            LOG.debug("BITBUCKET_BRANCH: %s", src_branch)

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
        new_ref_prefix = f"refs/remotes/{remote}/"
        # The source branch is simply the branch name, without any prefix
        # (e.g., `mybranch` instead of `refs/remotes/origin/mybranch`).
        src_branch = f"{new_ref_prefix}{src_branch}"
        if is_in_pr():
            # The target branch is also simply the branch name, without any prefix, but only when in a PR context.
            tgt_branch = f"{new_ref_prefix}{tgt_branch}"

        cmd = ["git", "merge-base", src_branch, tgt_branch]
        LOG.debug("Finding common ancestor commit with command: %s", shlex.join(cmd))
        try:
            common_commit = subprocess.run(cmd, check=True, capture_output=True, text=True).stdout.strip()  # noqa: S603
        except subprocess.CalledProcessError as err:
            msg = """
                The common ancestor commit could not be found.
                Ensure git strategy is set to `full clone depth` for repo checkouts:
                https://support.atlassian.com/bitbucket-cloud/docs/git-clone-behavior/"""
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
            Consider changing the `clone depth` variable in CI settings to
            clone/fetch more branch history. For more info, reference:
            https://support.atlassian.com/bitbucket-cloud/docs/git-clone-behavior/"""
        self.update_depfiles_change_status(diff_base_sha, err_msg)

        return any(depfile.is_depfile_changed for depfile in self.depfiles)

    @property
    def phylum_comment_exists(self) -> bool:
        """Predicate for detecting whether a Phylum-generated comment exists."""
        return bool(self.most_recent_phylum_comment)

    @property
    def repo_url(self) -> Optional[str]:
        """Get the repository URL for reference in Phylum project metadata."""
        # This is the "URL for the origin", which uses `HTTP:` instead of
        # `HTTPS:`, even though the value redirects to the `HTTPS:` site.
        # Ref: https://support.atlassian.com/bitbucket-cloud/docs/variables-and-secrets/
        origin_url = os.getenv("BITBUCKET_GIT_HTTP_ORIGIN")
        if origin_url is None:
            LOG.warning("Repository URL not found at `BITBUCKET_GIT_HTTP_ORIGIN`")
            return None

        # Ensure the repository URL uses the HTTPS scheme
        parsed_url = urllib.parse.urlparse(origin_url)
        if parsed_url.scheme == "http":
            parsed_url = parsed_url._replace(scheme="https")
        return parsed_url.geturl()

    def post_output(self) -> None:
        """Post the output of the analysis.

        Post output directly in the logs regardless of the pipeline context.
        Optionally post output as a comment on the Bitbucket Pipelines Pull
        Request (PR) when operating in a PR pipeline.
        """
        super().post_output()

        if not is_in_pr():
            # Can't post the output to the PR when there is no PR
            return

        if self.skip_comments:
            LOG.debug("Posting analysis output as comments on the pull request was disabled.")
            return

        LOG.info("Checking pull request comments for existing content to avoid duplication ...")
        if self.most_recent_phylum_comment:
            LOG.debug("The most recently posted Phylum pull request comment was found.")
            if self.most_recent_phylum_comment == self.analysis_report:
                LOG.debug("It contains the same content as the current analysis. Nothing to do.")
                return
            LOG.debug("It does not contain the same content as the current analysis.")
        else:
            LOG.debug("No existing Phylum pull request comments found.")

        # If we got here, then the most recent Phylum PR comment does not match the current analysis output or
        # there were no Phylum PR comments. Either way, create a new PR comment.
        url = get_comments_url()
        data = {"content": {"raw": self.analysis_report}}
        headers = self.headers.copy()
        headers["Content-Type"] = "application/json"
        LOG.info("Creating new pull request comment with POST URL: %s ...", url)
        response = requests.post(url, json=data, headers=headers, timeout=REQ_TIMEOUT)
        response.raise_for_status()

    @property
    def headers(self) -> dict:
        """Provide headers to use when making Bitbucket API calls."""
        headers = {
            "User-Agent": PHYLUM_USER_AGENT,
            "Accept": "application/json",
            "Authorization": f"Bearer {self.bitbucket_token}",
        }
        return headers

    @cached_property
    def most_recent_phylum_comment(self) -> Optional[str]:
        """Get the raw text of the most recently posted Phylum-generated comment.

        Return `None` when one does not exist.
        """
        if not is_in_pr():
            # It only makes sense to reference this property in the context of a PR
            return None

        if self.skip_comments:
            LOG.debug("Posting analysis output as comments on the pull request was disabled.")
            if not self.bitbucket_token:
                LOG.debug("Bitbucket API token not available. Unable to look for comments.")
                return None
            LOG.debug("Bitbucket API token available but possibly invalid. Attempting use ...")

        url = get_comments_url()

        # BITBUCKET_REPO_FULL_NAME provides the workspace and repository name that corresponds to BITBUCKET_REPO_UUID.
        # BITBUCKET_REPO_UUID is used in the API calls since it should never change.
        repo_full_name = os.getenv("BITBUCKET_REPO_FULL_NAME")
        repo_uuid = os.getenv("BITBUCKET_REPO_UUID")

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
        LOG.info("Getting all current pull request comments with GET URL: %s?%s ...", url, query_params_encoded)
        LOG.debug("The repository UUID %s maps to workspace and repository name: %s", repo_uuid, repo_full_name)
        req = requests.get(url, params=query_params, headers=self.headers, timeout=REQ_TIMEOUT)
        req.raise_for_status()
        pr_comments_resp: dict = req.json()
        pr_comments_values: list = pr_comments_resp.get("values", [])
        if pr_comments_values:
            # The most recently posted Phylum pull request comment was found.
            # NOTE: The API call normally returns all the comments in chronological order. Query parameters are used to
            #       only return the most recent Phylum comment, if one exists, since this is the only one we care about.
            most_recent_phylum_comment = pr_comments_values[0].get("content", {}).get("raw", "")
            return most_recent_phylum_comment

        # No existing Phylum pull request comments found
        return None


def get_comments_url() -> str:
    """Get the comments API URL and return it."""
    if not is_in_pr():
        msg = "Must be working in the context of a pull request pipeline"
        raise SystemExit(msg)
    # API Reference: https://developer.atlassian.com/cloud/bitbucket/rest/api-group-pullrequests/
    bitbucket_api_root_url = "https://api.bitbucket.org"
    # BITBUCKET_REPO_FULL_NAME provides the workspace and repository name that corresponds to BITBUCKET_REPO_UUID.
    # BITBUCKET_REPO_UUID is used in the API calls since it should never change.
    repo_uuid = os.getenv("BITBUCKET_REPO_UUID")
    pr_id = os.getenv("BITBUCKET_PR_ID")
    # This is the same endpoint for listing all PR comments (GET) and creating new ones (POST)
    # NOTE: It is possible to make calls with the repository UUID and an empty workspace:
    #       https://api.bitbucket.org/2.0/repositories/{}/{repo_uuid}/pullrequests/{pull_request_id}/comments
    #       The braces (even the empty braces) are required in the construction of the endpoint request.
    #       Reference: https://developer.atlassian.com/cloud/bitbucket/rest/intro/#repository-object-and-uuid
    pr_comments_api_endpoint = f"/2.0/repositories/{{}}/{repo_uuid}/pullrequests/{pr_id}/comments"
    url = f"{bitbucket_api_root_url}{pr_comments_api_endpoint}"
    return url
