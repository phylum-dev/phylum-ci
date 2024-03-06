"""Define a dependency file implementation.

A Phylum project can consist of multiple dependency files.
Dependency files can be either lockfiles or manifests.
This module/class represents a single dependency file.
"""

from enum import Enum
from functools import cache, cached_property
from inspect import cleandoc
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
from typing import Optional

from phylum.ci.common import CLIExitCode, DepfileEntry, Package, Packages
from phylum.exceptions import PhylumCalledProcessError
from phylum.logger import LOG, MARKUP


class DepfileType(Enum):
    """Enumeration to track dependency file types.

    A lockfile contains the completely resolved collection of the project dependencies,
    often from abstract declarations in one or more manifest files.

    A manifest contains project dependencies in their loose, unresolved form.

    Lockifests are manifests that, for historical reasons, can also be used as lockfiles.
    """

    LOCKFILE = "lockfile"
    MANIFEST = "manifest"
    LOCKIFEST = "lockifest"
    UNKNOWN = "unknown"


class Depfile:
    """Provide methods for an instance of a dependency file."""

    def __init__(
        self,
        provided_depfile: DepfileEntry,
        cli_path: Path,
        depfile_type: DepfileType,
        *,
        disable_lockfile_generation: bool = False,
    ) -> None:
        """Initialize a `Depfile` object."""
        self._path = provided_depfile.path.resolve()
        self._type = provided_depfile.type
        self.cli_path = cli_path
        self.disable_lockfile_generation = disable_lockfile_generation
        self._depfile_type = depfile_type
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

    def __lt__(self, other: object) -> bool:
        """Provide a less than "rich comparison" method to enable sorting class objects."""
        if not isinstance(other, Depfile):
            return NotImplemented
        return self.path < other.path

    @property
    def path(self) -> Path:
        """Get the dependency file path."""
        return self._path

    @property
    def type(self) -> str:
        """Get the dependency file ecosystem type."""
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
    def depfile_type(self) -> DepfileType:
        """Get the dependency file type."""
        return self._depfile_type

    @property
    def is_lockfile(self) -> bool:
        """Predicate to specify if the dependency file is a lockfile."""
        return self.depfile_type == DepfileType.LOCKFILE

    @property
    def is_manifest(self) -> bool:
        """Predicate to specify if the dependency file is a manifest.

        Lockifests and unknown types are also treated as manifests.
        """
        return self.depfile_type in {DepfileType.MANIFEST, DepfileType.LOCKIFEST, DepfileType.UNKNOWN}

    @cached_property
    def deps(self) -> Packages:
        """Get the dependencies from the current iteration of the dependency file and return them in sorted order."""
        try:
            curr_depfile_packages = parse_depfile(
                self.cli_path,
                self.type,
                self.path,
                disable_lockfile_generation=self.disable_lockfile_generation,
            )
        except subprocess.CalledProcessError as err:
            if err.returncode == CLIExitCode.MANIFEST_WITHOUT_GENERATION.value:
                msg = f"""
                    Provided manifest [code]{self!r}[/] requires lockfile
                    generation to parse but it was disabled to prevent running arbitrary
                    code in untrusted contexts, like PRs from forks. Consider adding a
                    lockfile instead of or along with the manifest, even for libraries."""
                LOG.warning(cleandoc(msg), extra=MARKUP)
                return []
            if self.is_lockfile:
                msg = f"""
                    Please report this as a bug if you believe [code]{self!r}[/]
                    is a valid [code]{self.type}[/] lockfile."""
            else:
                msg = f"""
                    Consider supplying dependency file type explicitly in `.phylum_project`
                    file. For more info: https://docs.phylum.io/cli/lockfile_generation
                    Please report this as a bug if you believe [code]{self!r}[/]
                    is a valid [code]{self.type}[/] manifest file."""
            raise PhylumCalledProcessError(err, cleandoc(msg)) from err
        return sorted(set(curr_depfile_packages))


# Type alias
Depfiles = list[Depfile]


@cache
def parse_depfile(
    cli_path: Path,
    depfile_type: str,
    depfile_path: Path,
    *,
    start: Optional[Path] = None,
    disable_lockfile_generation: bool = False,
) -> Packages:
    """Parse a dependency file and return its packages.

    `start` is an optional `Path` where the parsing command should be executed.
    When not specified, it will default to the current working directory.

    Specify `disable_lockfile_generation` as True to disable lockfile generation and False to allow it.

    Callers of this function *MUST* catch `subprocess.CalledProcessError` exceptions and handle them.
    Of note, an exit code of 20 indicates lockfile generation is required but was disabled.
    """
    if start is None:
        start = Path.cwd()
    depfile_relpath = os.path.relpath(depfile_path, start=start)
    LOG.info(
        "Parsing [code]%s[/] as [code]%s[/] dependency file. Manifests take longer.",
        depfile_relpath,
        depfile_type,
        extra=MARKUP,
    )
    cmd = [str(cli_path), "parse", "--type", depfile_type]
    if not _is_sandbox_possible(cli_path):
        cmd.append("--skip-sandbox")
    if disable_lockfile_generation:
        cmd.append("--no-generation")
    cmd.append(str(depfile_path))
    LOG.debug("Using parse command: %s", shlex.join(cmd))
    LOG.debug("Running command from: %s", start)
    result = subprocess.run(cmd, cwd=start, check=True, capture_output=True, text=True).stdout.strip()  # noqa: S603
    parsed_pkgs: list[dict[str, str]] = json.loads(result)
    depfile_pkgs = [Package(**pkg) for pkg in parsed_pkgs]
    return depfile_pkgs


@cache
def _is_sandbox_possible(cli_path: Path) -> bool:
    """Predicate to determine if the Phylum sandbox will work in the current running environment."""
    # See https://github.com/phylum-dev/cli/issues/1294 for more detail
    LOG.debug("Determining viability of the Phylum sandbox in this environment ...")
    cmd = [str(cli_path), "sandbox", "--allow-run", "/", "true"]
    LOG.debug("Executing command: %s", shlex.join(cmd))
    # We want the return code here and don't want to raise when non-zero.
    if bool(subprocess.run(cmd, check=False, capture_output=True).returncode):  # noqa: S603
        msg = """
            Phylum sandbox does not work in this environment and will be disabled.
            This is common and expected for container environments, such as Docker.
            Carefully scrutinize other environments where sandboxing is expected."""
        LOG.warning(cleandoc(msg))
        return False
    LOG.info("The Phylum sandbox works in this environment and will be enabled")
    return True
