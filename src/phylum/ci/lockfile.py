"""Define an implementation for lockfiles.

A lockfile contains the completely resolved collection of the project dependencies,
often from abstract declarations in one or more manifest files.
"""

from functools import cached_property, lru_cache
import json
from pathlib import Path
import shlex
import subprocess
import tempfile
import textwrap
from typing import Optional

from phylum.ci.common import PackageDescriptor, Packages
from phylum.ci.depfile import Depfile, parse_current_depfile
from phylum.exceptions import PhylumCalledProcessError, pprint_subprocess_error
from phylum.logger import LOG, MARKUP


class Lockfile(Depfile):
    """Provide methods for operating on a lockfile."""

    @cached_property
    def current_deps(self) -> Packages:
        """Get the current lockfile packages and return them in sorted order."""
        try:
            curr_lockfile_packages = parse_current_depfile(self.cli_path, self.type, self.path)
        except subprocess.CalledProcessError as err:
            msg = f"""\
                Please report this as a bug if you believe [code]{self!r}[/]
                  is a valid [code]{self.type}[/] lockfile."""
            raise PhylumCalledProcessError(err, textwrap.dedent(msg)) from err
        return sorted(set(curr_lockfile_packages))

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

    @lru_cache(maxsize=1)
    def previous_lockfile_object(self) -> Optional[str]:
        """Get the previous git object for the lockfile.

        Return None when no previous lockfile object can be found.
        """
        if not self.common_ancestor_commit:
            return None
        # Use the `repr` form to get the relative path to the lockfile
        cmd = ["git", "rev-parse", "--verify", f"{self.common_ancestor_commit}:{self!r}"]
        try:
            prev_lockfile_object = subprocess.run(cmd, check=True, capture_output=True, text=True).stdout  # noqa: S603
            prev_lockfile_object = prev_lockfile_object.strip()
        except subprocess.CalledProcessError as err:
            # There could be a true error, but the working assumption when here is a previous version does not exist
            msg = """\
                There [italic]may[/] be an issue with the attempt to get the previous lockfile object.
                  Continuing with the assumption a previous lockfile version does not exist ..."""
            pprint_subprocess_error(err)
            LOG.warning(textwrap.dedent(msg), extra=MARKUP)
            prev_lockfile_object = None
        return prev_lockfile_object

    @lru_cache(maxsize=1)
    def get_previous_lockfile_packages(self, prev_lockfile_object: str) -> Packages:
        """Get the previous lockfile packages from the corresponding git object and return them."""
        with tempfile.TemporaryDirectory(prefix="phylum_") as temp_dir:
            prev_lockfile_path = Path(temp_dir) / self.path.name
            cmd = ["git", "cat-file", "blob", prev_lockfile_object]
            try:
                prev_lockfile_contents = subprocess.run(
                    cmd,  # noqa: S603
                    check=True,
                    capture_output=True,
                    text=True,
                ).stdout
                prev_lockfile_path.write_text(prev_lockfile_contents, encoding="utf-8")
            except subprocess.CalledProcessError as err:
                pprint_subprocess_error(err)
                LOG.error("Due to error, assuming no previous lockfile packages. Please report this as a bug.")
                return []
            cmd = [str(self.cli_path), "parse", "--lockfile-type", self.type, str(prev_lockfile_path)]
            LOG.info(
                "Attempting to parse [code]%s[/] as previous [code]%s[/] lockfile ...",
                self.path,
                self.type,
                extra=MARKUP,
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
                    Due to error, assuming no previous lockfile packages.
                      Please report this as a bug if you believe [code]{self!r}[/]
                      is a valid [code]{self.type}[/] lockfile at revision
                      [code]{self.common_ancestor_commit}[/]."""
                LOG.warning(textwrap.dedent(msg), extra=MARKUP)
                return []

        parsed_pkgs = json.loads(parse_result)
        prev_lockfile_packages = [PackageDescriptor(**pkg) for pkg in parsed_pkgs]
        return prev_lockfile_packages
