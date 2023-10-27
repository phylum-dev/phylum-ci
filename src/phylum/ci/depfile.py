"""Define a dependency file implementation.

A Phylum project can consist of multiple dependency files.
Dependency files can be either lockfiles or manifests.
This module/class represents a single dependency file.
"""
from functools import cache, cached_property, lru_cache
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import tempfile
import textwrap
from typing import Optional, TypeVar

from phylum.ci.common import LockfileEntry, PackageDescriptor, Packages
from phylum.exceptions import PhylumCalledProcessError, pprint_subprocess_error
from phylum.logger import LOG

# Starting with Python 3.11, the `typing.Self` type was introduced to do this same thing.
# Reference: https://peps.python.org/pep-0673/
Self = TypeVar("Self", bound="Depfile")


class Depfile:
    """Provide methods for an instance of a dependency file."""

    def __init__(self, provided_depfile: LockfileEntry, cli_path: Path, common_ancestor_commit: Optional[str]) -> None:
        """Initialize a `Depfile` object."""
        self._path = provided_depfile.path.resolve()
        self._type = provided_depfile.type
        self.cli_path = cli_path
        self._common_ancestor_commit = common_ancestor_commit
        self._is_depfile_changed: Optional[bool] = None

        if not shutil.which("git"):
            msg = "`git` is required to be installed and available on the PATH"
            raise SystemExit(msg)

    def __repr__(self) -> str:
        """Return a debug printable string representation of the `Depfile` object."""
        # `PurePath.relative_to()` requires `self` to be the subpath of the argument, but `os.path.relpath()` does not.
        # NOTE: Any change from this format should be made carefully as caller's
        #       may be relying on `repr(depfile)` to provide the relative path.
        # Example: print(f"Relative path to dependency file: `{depfile!r}`")    # noqa: ERA001 ; commented code intended
        return os.path.relpath(self.path)

    def __str__(self) -> str:
        """Return the nicely printable string representation of the `Depfile` object."""
        # NOTE: Any change from this format should be made carefully as caller's
        #       may be relying on `str(depfile)` to provide the path.
        # Example: print(f"Path to dependency file: `{depfile}`")   # noqa: ERA001 ; commented code intended
        return str(self.path)

    def __lt__(self: Self, other: Self) -> bool:
        """Provide a less than "rich comparison" method to enable sorting class objects."""
        return self.path < other.path

    @property
    def path(self) -> Path:
        """Get the dependency file path."""
        return self._path

    @property
    def type(self) -> str:  # noqa: A003 ; shadowing built-in `type` is okay since renaming here would be more confusing
        """Get the dependency file type."""
        return self._type

    @property
    def is_depfile_changed(self) -> Optional[bool]:
        """Predicate for detecting if the dependency file has changed."""
        return self._is_depfile_changed

    @is_depfile_changed.setter
    def is_depfile_changed(self, value: bool) -> None:
        """Set the value for whether the dependency file has changed."""
        self._is_depfile_changed = value

    @property
    def common_ancestor_commit(self) -> Optional[str]:
        """Get the common ancestor commit.

        It will be returned as a string of the SHA1 sum representing the commit.
        When it isn't provided, `None` will be returned.
        """
        return self._common_ancestor_commit

    @cached_property
    def base_deps(self) -> Packages:
        """Get the dependencies from the base iteration of the dependency file and return them in sorted order.

        The base iteration is determined by the common ancestor commit.
        """
        prev_depfile_object = self.previous_depfile_object()
        if not prev_depfile_object:
            LOG.info("No previous dependency file object found for `%r`. Assuming no base dependencies.", self)
            return []
        prev_depfile_packages = sorted(set(self.get_previous_depfile_packages(prev_depfile_object)))
        return prev_depfile_packages

    @cached_property
    def new_deps(self) -> Packages:
        """Get the new dependencies added to the dependency file and return them in sorted order."""
        # Only consider newly added dependencies
        if self.is_depfile_changed is None:
            LOG.warning("The `is_depfile_changed` property has not been set yet")
        if not self.is_depfile_changed:
            return []

        curr_depfile_packages = self.current_depfile_packages()

        prev_depfile_object = self.previous_depfile_object()
        if not prev_depfile_object:
            LOG.debug("No previous dependency file object found for `%r`. Assuming all current packages are new.", self)
            return curr_depfile_packages

        prev_depfile_packages = self.get_previous_depfile_packages(prev_depfile_object)

        prev_pkg_set = set(prev_depfile_packages)
        curr_pkg_set = set(curr_depfile_packages)

        # TODO(maxrake): Consider using these new dependencies to track the output findings...as mapped to a depfile.
        #                https://github.com/phylum-dev/roadmap/issues/263
        new_deps_set = curr_pkg_set.difference(prev_pkg_set)
        new_deps_list = sorted(new_deps_set)
        LOG.debug("New dependencies in `%r`: %s", self, new_deps_list)
        return new_deps_list

    @lru_cache(maxsize=1)
    def current_depfile_packages(self) -> Packages:
        """Get the current dependency file packages."""
        try:
            curr_depfile_packages = parse_current_depfile(self.cli_path, self.type, self.path)
        except subprocess.CalledProcessError as err:
            msg = f"""\
                If this is a manifest, consider supplying lockfile type explicitly in the `.phylum_project` file.
                For more info, see: https://docs.phylum.io/docs/lockfile_generation
                Please report this as a bug if you believe [code]{self!r}[/] is a
                valid [code]{self.type}[/] dependency file."""
            raise PhylumCalledProcessError(err, textwrap.dedent(msg)) from err
        return curr_depfile_packages

    @lru_cache(maxsize=1)
    def previous_depfile_object(self) -> Optional[str]:
        """Get the previous git object for the dependency file.

        Return None when no previous dependency file object can be found.
        """
        if not self.common_ancestor_commit:
            return None
        try:
            # Use the `repr` form to get the relative path to the dependency file
            cmd = ["git", "rev-parse", "--verify", f"{self.common_ancestor_commit}:{self!r}"]
            prev_depfile_object = subprocess.run(cmd, check=True, capture_output=True, text=True).stdout  # noqa: S603
            prev_depfile_object = prev_depfile_object.strip()
        except subprocess.CalledProcessError as err:
            # There could be a true error, but the working assumption when here is a previous version does not exist
            msg = """\
                There [italic]may[/] be an issue with the attempt to get the previous dependency file object.
                Continuing with the assumption a previous dependency file version does not exist ..."""
            pprint_subprocess_error(err)
            LOG.warning(textwrap.dedent(msg), extra={"markup": True})
            prev_depfile_object = None
        return prev_depfile_object

    @lru_cache(maxsize=1)
    def get_previous_depfile_packages(self, prev_depfile_object: str) -> Packages:
        """Get the previous dependency file packages from the corresponding git object and return them."""
        with tempfile.TemporaryDirectory(prefix="phylum_") as temp_dir:
            prev_depfile_path = Path(temp_dir) / self.path.name
            cmd = ["git", "cat-file", "blob", prev_depfile_object]
            try:
                prev_depfile_contents = subprocess.run(
                    cmd,  # noqa: S603
                    check=True,
                    capture_output=True,
                    text=True,
                ).stdout
                prev_depfile_path.write_text(prev_depfile_contents, encoding="utf-8")
            except subprocess.CalledProcessError as err:
                pprint_subprocess_error(err)
                LOG.error("Due to error, assuming no previous dependency file packages. Please report this as a bug.")
                return []
            cmd = [str(self.cli_path), "parse", "--lockfile-type", self.type, str(prev_depfile_path)]
            LOG.info(
                "Attempting to parse [code]%s[/] as previous [code]%s[/] dependency file. Manifests may take a while.",
                self.path,
                self.type,
                extra={"markup": True},
            )
            LOG.debug("Using parse command: %s", shlex.join(cmd))
            try:
                parse_result = subprocess.run(
                    cmd,  # noqa: S603
                    check=True,
                    capture_output=True,
                    text=True,
                ).stdout.strip()
            except subprocess.CalledProcessError as err:
                pprint_subprocess_error(err)
                msg = f"""\
                    Due to error, assuming no previous dependency file packages.
                    If this is a manifest, consider supplying lockfile type explicitly in the `.phylum_project` file.
                    For more info, see: https://docs.phylum.io/docs/lockfile_generation
                    Please report this as a bug if you believe [code]{self!r}[/] is a
                    valid [code]{self.type}[/] dependency file at revision [code]{self.common_ancestor_commit}[/]."""
                LOG.warning(textwrap.dedent(msg), extra={"markup": True})
                return []

        parsed_pkgs = json.loads(parse_result)
        prev_depfile_packages = [PackageDescriptor(**pkg) for pkg in parsed_pkgs]
        return prev_depfile_packages


# Type alias
Depfiles = list[Depfile]


@cache
def parse_current_depfile(cli_path: Path, lockfile_type: str, depfile_path: Path) -> Packages:
    """Parse a current dependency file and return its packages.

    Callers of this function must catch `subprocess.CalledProcessError` exceptions and handle them.
    """
    LOG.info(
        "Attempting to parse [code]%s[/] as a [code]%s[/] dependency file. Manifests may take a while.",
        os.path.relpath(depfile_path),
        lockfile_type,
        extra={"markup": True},
    )
    cmd = [str(cli_path), "parse", "--lockfile-type", lockfile_type, str(depfile_path)]
    LOG.debug("Using parse command: %s", shlex.join(cmd))
    parse_result = subprocess.run(cmd, check=True, capture_output=True, text=True).stdout.strip()  # noqa: S603
    parsed_pkgs = json.loads(parse_result)
    curr_depfile_packages = [PackageDescriptor(**pkg) for pkg in parsed_pkgs]
    return curr_depfile_packages
