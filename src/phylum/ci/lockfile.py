"""Define a lockfile implementation.

A Phylum project can consist of multiple lockfiles.
This class represents a single lockfile.
"""
from functools import cached_property, lru_cache
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import textwrap
from typing import List, Optional, TypeVar

from phylum.ci.common import PackageDescriptor, Packages
from phylum.exceptions import PhylumCalledProcessError, pprint_subprocess_error
from phylum.logger import LOG

# Starting with Python 3.11, the `typing.Self` type was introduced to do this same thing.
# Reference: https://peps.python.org/pep-0673/
Self = TypeVar("Self", bound="Lockfile")


class Lockfile:
    """Provide methods for an instance of a lockfile."""

    def __init__(self, provided_lockfile: Path, cli_path: Path, common_ancestor_commit: Optional[str]) -> None:
        """Initialize a lockfile object."""
        self._path = provided_lockfile.resolve()
        self.cli_path = cli_path
        self._common_ancestor_commit = common_ancestor_commit
        self._is_lockfile_changed: Optional[bool] = None

        if not shutil.which("git"):
            msg = "`git` is required to be installed and available on the PATH"
            raise SystemExit(msg)

    def __repr__(self) -> str:
        """Return a debug printable string representation of the `Lockfile` object."""
        # NOTE: Any change from this format should be made carefully as caller's
        #       may be relying on `repr(lockfile)` to provide the relative path.
        #       Example: print(f"Relative path to lockfile: `{lockfile!r}`")    # noqa: ERA001 ; commented code intended
        return str(self.path.relative_to(Path.cwd()))

    def __str__(self) -> str:
        """Return the nicely printable string representation of the `Lockfile` object."""
        # NOTE: Any change from this format should be made carefully as caller's
        #       may be relying on `str(lockfile)` to provide the path.
        #       Example: print(f"Path to lockfile: `{lockfile}`")   # noqa: ERA001 ; commented code intended
        return str(self.path)

    def __lt__(self: Self, other: Self) -> bool:
        """Provide a less than "rich comparison" method to enable sorting class objects."""
        return self.path < other.path

    @property
    def path(self) -> Path:
        """Get the lockfile path."""
        return self._path

    @property
    def is_lockfile_changed(self) -> Optional[bool]:
        """Predicate for detecting if the lockfile has changed."""
        return self._is_lockfile_changed

    @is_lockfile_changed.setter
    def is_lockfile_changed(self, value: bool) -> None:
        """Set the value for whether the lockfile has changed."""
        self._is_lockfile_changed = value

    @property
    def common_ancestor_commit(self) -> Optional[str]:
        """Get the common ancestor commit.

        It will be returned as a string of the SHA1 sum representing the commit.
        When it isn't provided, `None` will be returned.
        """
        return self._common_ancestor_commit

    @cached_property
    def base_deps(self) -> Packages:
        """Get the dependencies from the base iteration of the lockfile and return them in sorted order.

        The base iteration is determined by the common ancestor commit.
        """
        prev_lockfile_object = self.previous_lockfile_object()
        if not prev_lockfile_object:
            LOG.info("No previous lockfile object found for `%r`. Assuming no base dependencies.", self)
            return []
        prev_lockfile_packages = sorted(set(self.get_previous_lockfile_packages(prev_lockfile_object)))
        return prev_lockfile_packages

    @cached_property
    def new_deps(self) -> Packages:
        """Get the new dependencies added to the lockfile and return them in sorted order."""
        # Only consider newly added dependencies
        if self.is_lockfile_changed is None:
            LOG.warning("The `is_lockfile_changed` property has not been set yet")
        if not self.is_lockfile_changed:
            return []

        curr_lockfile_packages = self.current_lockfile_packages()

        prev_lockfile_object = self.previous_lockfile_object()
        if not prev_lockfile_object:
            LOG.debug("No previous lockfile object found for `%r`. Assuming all current packages are new.", self)
            return curr_lockfile_packages

        prev_lockfile_packages = self.get_previous_lockfile_packages(prev_lockfile_object)

        prev_pkg_set = set(prev_lockfile_packages)
        curr_pkg_set = set(curr_lockfile_packages)

        # TODO(maxrake): Consider using these new dependencies to track the output findings...as mapped to a lockfile.
        #                https://github.com/phylum-dev/roadmap/issues/263
        new_deps_set = curr_pkg_set.difference(prev_pkg_set)
        new_deps_list = sorted(new_deps_set)
        LOG.debug("New dependencies in `%r`: %s", self, new_deps_list)
        return new_deps_list

    @lru_cache(maxsize=1)
    def current_lockfile_packages(self) -> Packages:
        """Get the current lockfile packages."""
        try:
            cmd = [str(self.cli_path), "parse", str(self.path)]
            parse_result = subprocess.run(cmd, check=True, capture_output=True, text=True).stdout.strip()  # noqa: S603
        except subprocess.CalledProcessError as err:
            msg = f"Is [reverse]{self!r}[/] a valid lockfile? If so, please report this as a bug."
            raise PhylumCalledProcessError(err, msg) from err
        parsed_pkgs = json.loads(parse_result)
        curr_lockfile_packages = [PackageDescriptor(**pkg) for pkg in parsed_pkgs]
        return curr_lockfile_packages

    @lru_cache(maxsize=1)
    def previous_lockfile_object(self) -> Optional[str]:
        """Get the previous git object for the lockfile.

        Return None when no previous lockfile object can be found.
        """
        if not self.common_ancestor_commit:
            return None
        try:
            # Use the `repr` form to get the relative path to the lockfile
            cmd = ["git", "rev-parse", "--verify", f"{self.common_ancestor_commit}:{self!r}"]
            prev_lockfile_object = subprocess.run(cmd, check=True, capture_output=True, text=True).stdout  # noqa: S603
            prev_lockfile_object = prev_lockfile_object.strip()
        except subprocess.CalledProcessError as err:
            # There could be a true error, but the working assumption when here is a previous version does not exist
            msg = """\
                There [italic]may[/] be an issue with the attempt to get the previous lockfile object.
                Continuing with the assumption a previous lockfile version does not exist ..."""
            pprint_subprocess_error(err)
            LOG.warning(textwrap.dedent(msg), extra={"markup": True})
            prev_lockfile_object = None
        return prev_lockfile_object

    @lru_cache(maxsize=1)
    def get_previous_lockfile_packages(self, prev_lockfile_object: str) -> Packages:
        """Get the previous lockfile packages from the corresponding git object and return them."""
        with tempfile.NamedTemporaryFile(mode="w+") as prev_lockfile_fd:
            try:
                cmd = ["git", "cat-file", "blob", prev_lockfile_object]
                prev_lockfile_contents = subprocess.run(
                    cmd,  # noqa: S603
                    check=True,
                    capture_output=True,
                    text=True,
                ).stdout
                prev_lockfile_fd.write(prev_lockfile_contents)
                prev_lockfile_fd.flush()
            except subprocess.CalledProcessError as err:
                pprint_subprocess_error(err)
                LOG.error("Due to error, assuming no previous lockfile packages. Please report this as a bug.")
                return []
            try:
                cmd = [str(self.cli_path), "parse", prev_lockfile_fd.name]
                parse_result = subprocess.run(
                    cmd,  # noqa: S603
                    check=True,
                    capture_output=True,
                    text=True,
                ).stdout.strip()
            except subprocess.CalledProcessError as err:
                pprint_subprocess_error(err)
                msg = f"""\
                    Due to error, assuming no previous lockfile packages.
                    Please report this as a bug if you believe [code]{self!r}[/]
                    is a valid lockfile at revision [code]{self.common_ancestor_commit}[/]."""
                LOG.warning(textwrap.dedent(msg), extra={"markup": True})
                return []

        parsed_pkgs = json.loads(parse_result)
        prev_lockfile_packages = [PackageDescriptor(**pkg) for pkg in parsed_pkgs]
        return prev_lockfile_packages


# Type alias
Lockfiles = List[Lockfile]
