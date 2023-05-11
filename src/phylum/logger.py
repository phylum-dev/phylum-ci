"""Configure the logging features for the package."""
import logging

from rich.logging import RichHandler

from phylum import PKG_NAME
from phylum.console import console

LOG = logging.getLogger(PKG_NAME)

rich_handler = RichHandler(
    console=console,
    show_time=False,
    # TODO: show path, links, and level only for `trace` level?
    show_path=False,
)
LOG.addHandler(rich_handler)


def set_logger_level(level: int) -> None:
    """Initialize the default logger instance with a level.

    The intended usage is to pass the count of `--verbose` and `--quiet` arguments, as parsed from `args`:

    >>> set_logger_level(args.verbose - args.quiet)

    This assumes that those arguments are mutually exclusive and make use of the "count" action.
    """
    min_level = -2
    max_level = 2
    level_map = {
        -2: logging.CRITICAL,
        -1: logging.ERROR,
        0: logging.WARNING,
        1: logging.INFO,
        2: logging.DEBUG,
    }
    level = min(max(level, min_level), max_level)
    LOG.setLevel(level_map.get(level, 0))
