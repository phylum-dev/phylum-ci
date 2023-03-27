"""Define a lockfile implementation.

A Phylum project can consist of multiple lockfiles.
This class represents a single lockfile.
"""
import json
import shutil
import subprocess
import tempfile
import textwrap
from pathlib import Path
from typing import List, Optional, TypeVar

from phylum.ci.common import PackageDescriptor, Packages

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
            raise SystemExit(" [!] `git` is required to be installed and available on the PATH")

    def __repr__(self) -> str:
        """Return a debug printable string representation of the `Lockfile` object."""
        # NOTE: Any change from this format should be made carefully as caller's
        #       may be relying on `repr(lockfile)` to provide the relative path.
        #       Example: print(f"Relative path to lockfile: `{lockfile!r}`")
        return str(self.path.relative_to(Path.cwd()))

    def __str__(self) -> str:
        """Return the nicely printable string representation of the `Lockfile` object."""
        # NOTE: Any change from this format should be made carefully as caller's
        #       may be relying on `str(lockfile)` to provide the path.
        #       Example: print(f"Path to lockfile: `{lockfile}`")
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

    @property
    def new_deps(self) -> Packages:
        """Get the new dependencies added to the lockfile and return them in sorted order."""
        # Only consider newly added dependencies
        if self.is_lockfile_changed is None:
            print(" [!] The `is_lockfile_changed` property has not been set yet")
        if not self.is_lockfile_changed:
            return []

        curr_lockfile_packages = self.current_lockfile_packages()

        prev_lockfile_object = self.previous_lockfile_object()
        if not prev_lockfile_object:
            print(f" [+] No previous lockfile object found for `{self!r}`. Assuming all current packages are new.")
            return curr_lockfile_packages

        prev_lockfile_packages = self.get_previous_lockfile_packages(prev_lockfile_object)

        prev_pkg_set = set(prev_lockfile_packages)
        curr_pkg_set = set(curr_lockfile_packages)

        # TODO: Consider using these new dependencies to track the output findings...as mapped to a lockfile.
        #       https://github.com/phylum-dev/roadmap/issues/263
        new_deps_set = curr_pkg_set.difference(prev_pkg_set)
        new_deps_list = sorted(new_deps_set)
        print(f" [+] New dependencies in `{self!r}`: {new_deps_list}")
        return new_deps_list

    def current_lockfile_packages(self) -> Packages:
        """Get the current lockfile packages."""
        try:
            cmd = [str(self.cli_path), "parse", str(self.path)]
            parse_result = subprocess.run(cmd, check=True, capture_output=True, text=True).stdout.strip()
        except subprocess.CalledProcessError as err:
            print(f" [!] There was an error running the command: {' '.join(err.cmd)}")
            print(f" [!] stdout:\n{err.stdout}")
            print(f" [!] stderr:\n{err.stderr}")
            raise SystemExit(f" [!] Is `{self!r}` a valid lockfile? If so, please report this as a bug.") from err
        parsed_pkgs = json.loads(parse_result)
        curr_lockfile_packages = [PackageDescriptor(**pkg) for pkg in parsed_pkgs]
        return curr_lockfile_packages

    def previous_lockfile_object(self) -> Optional[str]:
        """Get the previous git object for the lockfile.

        Return None when no previous lockfile object can be found.
        """
        if not self.common_ancestor_commit:
            return None
        try:
            # Use the `repr` form to get the relative path to the lockfile
            cmd = ["git", "rev-parse", "--verify", f"{self.common_ancestor_commit}:{self!r}"]
            prev_lockfile_object = subprocess.run(cmd, check=True, capture_output=True, text=True).stdout.strip()
        except subprocess.CalledProcessError as err:
            # There could be a true error, but the working assumption when here is a previous version does not exist
            print(f" [?] There *may* be an issue with the attempt to get the previous lockfile object: {err}")
            print(f" [?] stdout:\n{err.stdout}")
            print(f" [?] stderr:\n{err.stderr}")
            print(" [+] Assuming a previous lockfile version does not exist ...")
            prev_lockfile_object = None
        return prev_lockfile_object

    def get_previous_lockfile_packages(self, prev_lockfile_object: str) -> Packages:
        """Get the previous lockfile packages from the corresponding git object and return them."""
        with tempfile.NamedTemporaryFile(mode="w+") as prev_lockfile_fd:
            try:
                cmd = ["git", "cat-file", "blob", prev_lockfile_object]
                prev_lockfile_contents = subprocess.run(cmd, check=True, capture_output=True, text=True).stdout
                prev_lockfile_fd.write(prev_lockfile_contents)
                prev_lockfile_fd.flush()
            except subprocess.CalledProcessError as err:
                print(f" [!] There was an error running the command: {' '.join(err.cmd)}")
                print(f" [!] stdout:\n{err.stdout}")
                print(f" [!] stderr:\n{err.stderr}")
                print(" [!] Due to error, assuming no previous lockfile packages. Please report this as a bug.")
                return []
            try:
                cmd = [str(self.cli_path), "parse", prev_lockfile_fd.name]
                parse_result = subprocess.run(cmd, check=True, capture_output=True, text=True).stdout.strip()
            except subprocess.CalledProcessError as err:
                print(f" [!] There was an error running the command: {' '.join(err.cmd)}")
                print(f" [!] stdout:\n{err.stdout}")
                print(f" [!] stderr:\n{err.stderr}")
                msg = textwrap.dedent(
                    f"""\
                    [!] Due to error, assuming no previous lockfile packages.
                        Please report this as a bug if you believe `{self!r}`
                        is a valid lockfile at revision `{self.common_ancestor_commit}`.
                    """
                )
                print(msg)
                return []

        parsed_pkgs = json.loads(parse_result)
        prev_lockfile_packages = [PackageDescriptor(**pkg) for pkg in parsed_pkgs]
        return prev_lockfile_packages


# Type alias
Lockfiles = List[Lockfile]
