"""Define an implementation for the Jenkinks platform.

Jenkins References:
  * https://www.jenkins.io
  * https://www.jenkins.io/doc/
  * https://www.jenkins.io/doc/book/pipeline/syntax/
  * https://www.jenkins.io/doc/book/using/using-credentials/
  * https://www.jenkins.io/doc/book/pipeline/docker/
  * https://www.jenkins.io/doc/pipeline/steps/
  * https://www.jenkins.io/doc/book/pipeline/multibranch/#supporting-pull-requests
  * https://www.jenkins.io/doc/book/pipeline/jenkinsfile/#using-environment-variables
  * https://www.jenkins.io/doc/book/pipeline/getting-started/#global-variable-reference
"""

from argparse import Namespace
from functools import cached_property, lru_cache
import os
import re
import shlex
import subprocess
from typing import Optional

from phylum.ci.ci_base import CIBase
from phylum.ci.git import git_remote, git_set_remote_head
from phylum.exceptions import pprint_subprocess_error
from phylum.logger import LOG


@lru_cache(maxsize=1)
def is_in_pr() -> bool:
    """Indicate if the integration is operating in the context of a pull request pipeline.

    Jenkins allows for the possibility of running multibranch pipelines in different contexts:
      * On every push, for the last commit in the push (e.g., branch pipelines)
      * For pull requests (e.g., pull request pipelines)

    Knowing when the context is within a pull request helps to ensure the logic used
    to determine the dependency file changes is correct.
    """
    # References:
    # https://github.com/watson/ci-info/blob/master/vendors.json
    # https://www.jenkins.io/doc/book/pipeline/multibranch/#supporting-pull-requests
    return any(map(os.getenv, ["CHANGE_ID", "ghprbPullId"]))


class CIJenkins(CIBase):
    """Provide methods for a Jenkins environment."""

    def __init__(self, args: Namespace) -> None:  # noqa: D107 ; the base __init__ docstring is better here
        super().__init__(args)
        self.ci_platform_name = "Jenkins"
        if is_in_pr():
            LOG.debug("Pipeline context: pull request pipeline")
        else:
            LOG.debug("Pipeline context: branch pipeline")

    def _check_prerequisites(self) -> None:
        """Ensure the necessary prerequisites are met and bail when they aren't.

        These are the current prerequisites for operating within a Jenkins environment:
          * The environment must actually be within Jenkins
        """
        super()._check_prerequisites()

        # References:
        # https://github.com/watson/ci-info/blob/master/vendors.json
        if os.getenv("JENKINS_URL") is None or os.getenv("BUILD_ID") is None:
            msg = "Must be working within a Jenkins environment"
            raise SystemExit(msg)

    @cached_property
    def phylum_label(self) -> str:
        """Get a custom label for use when submitting jobs for analysis."""
        if is_in_pr():
            pr_id = os.getenv("CHANGE_ID", "unknown-ID")
            pr_src_branch = os.getenv("CHANGE_BRANCH", "unknown-branch")
            label = f"{self.ci_platform_name}_PR#{pr_id}_{pr_src_branch}"
        else:
            current_branch = os.getenv("BRANCH_NAME", "unknown-branch")
            label = f"{self.ci_platform_name}_{current_branch}_{self.depfile_hash_object}"

        label = re.sub(r"\s+", "-", label)
        return label

    @cached_property
    def common_ancestor_commit(self) -> Optional[str]:
        """Find the common ancestor commit.

        Some pre-defined variables are used:
        https://www.jenkins.io/doc/book/pipeline/jenkinsfile/#using-environment-variables
        """
        remote = git_remote()

        if not is_in_pr() and os.getenv("BRANCH_IS_PRIMARY"):
            # If the current commit is on the default branch, then the merge base will be the same
            # as the current commit and it won't be possible to provide a useful common ancestor
            # commit. In this case, it is better to force analysis of the dependency file(s) and
            # consider *all* dependencies in analysis results instead of just the newly added ones.
            LOG.warning("On primary branch. Proceeding with analysis of all dependencies ...")
            self._force_analysis = True
            self._all_deps = True

        cmd = ["git", "merge-base", "HEAD", f"refs/remotes/{remote}/HEAD"]
        LOG.debug("Finding common ancestor commit with command: %s", shlex.join(cmd))
        try:
            commit = subprocess.run(cmd, check=True, capture_output=True, text=True).stdout.strip()  # noqa: S603
        except subprocess.CalledProcessError as outer_err:
            # The most likely problem is that the remote HEAD ref is not set. The attempt to set it here, inside
            # the except block, is due to wanting to minimize calling commands that require git credentials.
            pprint_subprocess_error(outer_err)
            LOG.warning("Failed to get commit. Remote HEAD ref likely not set. Attempting to set it and try again ...")
            git_set_remote_head(remote)
            try:
                commit = subprocess.run(cmd, check=True, capture_output=True, text=True).stdout.strip()  # noqa: S603
            except subprocess.CalledProcessError as inner_err:
                pprint_subprocess_error(inner_err)
                LOG.warning("The common ancestor commit could not be found")
                commit = None
        return commit

    @property
    def is_any_depfile_changed(self) -> bool:
        """Predicate for detecting if any dependency file has changed."""
        diff_base_sha = self.common_ancestor_commit
        LOG.debug("The common ancestor commit: %s", diff_base_sha)

        # Assume no change when there isn't enough information to tell
        if diff_base_sha is None:
            return False

        err_msg = """
            Ensure a full checkout is configured, to provide history and proper
            diffs. A `checkout scm` step is not enough here. The `phylum-ci`
            command must also be contained within a `withCredentials` block,
            where the `credentialsId` is the same as used for the checkout.
            For more info, reference:
            * https://plugins.jenkins.io/workflow-scm-step/
            * https://www.jenkins.io/doc/pipeline/steps/credentials-binding/"""
        self.update_depfiles_change_status(diff_base_sha, err_msg)

        return any(depfile.is_depfile_changed for depfile in self.depfiles)

    @property
    def phylum_comment_exists(self) -> bool:
        """Predicate for detecting whether a Phylum-generated comment exists."""
        # There are no historical comments in this implementation
        return False

    @property
    def repo_url(self) -> Optional[str]:
        """Get the repository URL for reference in Phylum project metadata."""
        # This is the "Remote URL of the first git repository in the workspace."
        # It comes from the git plugin and may not be set depending on the context.
        # Ref: https://plugins.jenkins.io/git/#plugin-content-environment-variables
        git_url = os.getenv("GIT_URL")
        if git_url is None:
            LOG.warning("Repository URL not found at `GIT_URL`")
            return None
        return git_url
