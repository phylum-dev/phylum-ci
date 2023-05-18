"""Provide custom exceptions for the package."""
import subprocess
import sys

from rich import print as rich_print
from rich.console import RenderResult, group
from rich.panel import Panel

from phylum.logger import LOG


class PhylumCalledProcessError(Exception):
    """Custom exception for handling subprocess errors."""

    def __init__(self, err: subprocess.CalledProcessError, msg: str) -> None:
        """Format a subprocess error in a consistent way for log entries.

        This exception is meant to be re-raised when catching a `subprocess.CalledProcessError`.
        `err` is the captured variable in the exception context manager.
        `msg` will be displayed in the logs and should provide a best effort explanation about
        what went wrong and what to do about it. Rich console markup is allowed in the string.

        If this exception is raised it means there is no other option and the program should terminate.

        Example:
        ```
        except subprocess.CalledProcessError as err:
            msg = "This is the best explanation of what went wrong and what to do about it."
            raise PhylumCalledProcessError(err, msg) from err
        ```
        """
        # TODO: figure out how to apply a theme to a panel (like how traceback does)
        pprint_subprocess_error(err)
        LOG.critical(msg, extra={"markup": True})
        raise SystemExit(err.returncode)


@group()
def rich_called_process_error(err: subprocess.CalledProcessError) -> RenderResult:
    """Create a group of rich renderables for prettier output of subprocess errors.

    Reference: https://rich.readthedocs.io/en/latest/group.html
    """
    yield f"[bold yellow]COMMAND[/]: [code]{' '.join(err.cmd)}[/]"
    yield f"[bold yellow]RETURN CODE[/]: [repr.number]{err.returncode}"
    stdout = err.stdout.strip() if err.stdout and isinstance(err.stdout, str) else "[dim]NONE"
    yield Panel(stdout, title="[bold yellow]STDOUT", expand=False, border_style="yellow")
    stderr = err.stderr.strip() if err.stderr and isinstance(err.stderr, str) else "[dim]NONE"
    yield Panel(stderr, title="[bold yellow]STDERR", expand=False, border_style="yellow")


def pprint_subprocess_error(err: subprocess.CalledProcessError) -> None:
    """Pretty print a subprocess error using rich."""
    err_panel = Panel(
        rich_called_process_error(err),
        title="Subprocess Error",
        expand=False,
        border_style="traceback.border",
    )
    rich_print(err_panel, file=sys.stderr)
