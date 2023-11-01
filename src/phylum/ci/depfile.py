"""Define a dependency file implementation.

A Phylum project can consist of multiple dependency files.
Dependency files can be either lockfiles or manifests.
This module/class represents a single dependency file.

Common functionality is provided where possible and unique functionality is designated
as abstract methods to be defined in either the `Lockfile` or `Manifest` classes.
"""
from abc import ABC, abstractmethod
from functools import cache, cached_property
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
from typing import Optional, TypeVar

from phylum.ci.common import LockfileEntry, PackageDescriptor, Packages
from phylum.logger import LOG, MARKUP

# Starting with Python 3.11, the `typing.Self` type was introduced to do this same thing.
# Reference: https://peps.python.org/pep-0673/
Self = TypeVar("Self", bound="Depfile")


class Depfile(ABC):
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
    @abstractmethod
    def current_deps(self) -> Packages:
        """Get the dependencies from the current iteration of the dependency file and return them in sorted order."""
        raise NotImplementedError

    @cached_property
    @abstractmethod
    def base_deps(self) -> Packages:
        """Get the dependencies from the base iteration of the dependency file and return them in sorted order.

        The base iteration is determined by the common ancestor commit.
        """
        raise NotImplementedError

    @cached_property
    @abstractmethod
    def new_deps(self) -> Packages:
        """Get the new dependencies added to the dependency file and return them in sorted order."""
        raise NotImplementedError


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
        extra=MARKUP,
    )
    cmd = [str(cli_path), "parse", "--lockfile-type", lockfile_type, str(depfile_path)]
    LOG.debug("Using parse command: %s", shlex.join(cmd))
    parse_result = subprocess.run(cmd, check=True, capture_output=True, text=True).stdout.strip()  # noqa: S603
    parsed_pkgs = json.loads(parse_result)
    curr_depfile_packages = [PackageDescriptor(**pkg) for pkg in parsed_pkgs]
    return curr_depfile_packages
