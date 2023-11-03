"""Define an implementation for manifests.

A manifest contains project dependencies in their loose, unresolved form.
"""

from functools import cached_property
import json
from pathlib import Path
import shlex
import subprocess
import tempfile
import textwrap

from phylum.ci.common import PackageDescriptor, Packages
from phylum.ci.depfile import Depfile, parse_current_depfile
from phylum.exceptions import PhylumCalledProcessError, pprint_subprocess_error
from phylum.logger import LOG, MARKUP


class Manifest(Depfile):
    """Provide methods for operating on a manifest."""

    @cached_property
    def current_deps(self) -> Packages:
        """Get the current manifest packages and return them in sorted order."""
        try:
            curr_manifest_packages = parse_current_depfile(self.cli_path, self.type, self.path)
        except subprocess.CalledProcessError as err:
            msg = f"""\
                Consider supplying lockfile type explicitly in the `.phylum_project` file.
                  For more info, see: https://docs.phylum.io/docs/lockfile_generation
                  Please report this as a bug if you believe [code]{self!r}[/]
                  is a valid [code]{self.type}[/] manifest file."""
            raise PhylumCalledProcessError(err, textwrap.dedent(msg)) from err
        return sorted(set(curr_manifest_packages))

    @cached_property
    def base_deps(self) -> Packages:
        """Get the dependencies from the base iteration of the manifest and return them in sorted order.

        The base iteration is determined by the common ancestor commit.
        """
        if not self.common_ancestor_commit:
            LOG.info("No common ancestor commit for `%r`. Assuming no base dependencies.", self)
            return []

        with tempfile.TemporaryDirectory(prefix="phylum_") as temp_dir:
            cmd = ["git", "worktree", "add", "--detach", temp_dir, self.common_ancestor_commit]
            LOG.debug("Adding a git worktree for the base iteration in a temporary directory ...")
            LOG.debug("Using command: %s", shlex.join(cmd))
            try:
                subprocess.run(cmd, check=True, capture_output=True, text=True)  # noqa: S603
            except subprocess.CalledProcessError as err:
                pprint_subprocess_error(err)
                LOG.error("Due to error, assuming no base dependencies. Please report this as a bug.")
                return []

            temp_dir_path = Path(temp_dir).resolve()
            prev_manifest_path = temp_dir_path / self.path.relative_to(Path.cwd())
            cmd = [str(self.cli_path), "parse", "--lockfile-type", self.type, str(prev_manifest_path)]
            LOG.info(
                "Attempting to parse [code]%s[/] as previous [code]%s[/] manifest. This may take a while.",
                self.path,
                self.type,
                extra=MARKUP,
            )
            LOG.debug("Using parse command: %s", shlex.join(cmd))
            try:
                parse_result = subprocess.run(
                    cmd,  # noqa: S603
                    cwd=temp_dir_path,
                    check=True,
                    capture_output=True,
                    text=True,
                ).stdout.strip()
            except subprocess.CalledProcessError as err:
                pprint_subprocess_error(err)
                msg = f"""\
                    Due to error, assuming no previous manifest packages.
                      Consider supplying lockfile type explicitly in `.phylum_project` file.
                      For more info, see: https://docs.phylum.io/docs/lockfile_generation
                      Please report this as a bug if you believe [code]{self!r}[/]
                      is a valid [code]{self.type}[/] manifest file at revision
                      [code]{self.common_ancestor_commit}[/]."""
                LOG.warning(textwrap.dedent(msg), extra=MARKUP)
                remove_git_worktree(temp_dir_path)
                return []

            remove_git_worktree(temp_dir_path)

        parsed_pkgs = json.loads(parse_result)
        prev_manifest_packages = [PackageDescriptor(**pkg) for pkg in parsed_pkgs]
        return sorted(set(prev_manifest_packages))


def remove_git_worktree(worktree: Path) -> None:
    """Remove a given git worktree.

    If a working tree is deleted without using `git worktree remove`, then its associated administrative files, which
    reside in the repository, will eventually be removed automatically.
    Ref: https://git-scm.com/docs/git-worktree

    Use this function to remove the worktree now since the default for the `gc.worktreePruneExpire` setting is 3 months.
    """
    cmd = ["git", "worktree", "remove", "--force", str(worktree)]
    LOG.debug("Removing the git worktree for the base iteration ...")
    LOG.debug("Using command: %s", shlex.join(cmd))
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)  # noqa: S603
    except subprocess.CalledProcessError as err:
        pprint_subprocess_error(err)
        LOG.warning("Unable to remove the git worktree. Try running `git worktree prune` manually.")
