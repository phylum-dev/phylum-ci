"""Configure the logging features for the package."""

import inspect
import logging
import sys
from types import FunctionType, MethodType
from typing import Any, Callable, Optional

from rich.logging import RichHandler
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
import rich.traceback

from phylum import PKG_NAME
from phylum.console import console

# Import and use this throughout the `phylum` package to write consistent log entries
LOG = logging.getLogger(PKG_NAME)
# This is a shorter form of specifying the `rich` markup format as an "extra" argument in log calls
MARKUP = {"markup": True}
# This is a shorter form of specifying the `rich` markup format, w/o highlighting, as an "extra" argument in log calls
MARKUP_NO_HI = {"markup": True, "highlighter": None}
# This is a custom logging level, defined relative to existing logging.DEBUG level as suggested in the
# Python `logging` library documentation: https://docs.python.org/3/library/logging.html#logging-levels
LOGGING_TRACE_LEVEL = logging.DEBUG - 5

DEFAULT_RICH_HANDLER = RichHandler(
    console=console,
    show_time=False,
    show_level=True,
    show_path=False,
    rich_tracebacks=True,
    tracebacks_show_locals=False,
)
LOG.addHandler(DEFAULT_RICH_HANDLER)

# Install rich as the default traceback handler so that all uncaught exceptions will be rendered with highlighting
rich.traceback.install(console=console, word_wrap=True, show_locals=True)


# This function was adapted from:
#  * https://stackoverflow.com/a/35804945
#  * https://github.com/python/cpython/issues/75913#issuecomment-1093761548
#  * https://github.com/madphysicist/haggis/blob/master/src/haggis/logs.py
def add_logging_level(level_name: str, level_num: int, method_name: Optional[str] = None) -> None:
    """Add a new logging level to the `logging` module and the currently configured logging class.

    `level_name` becomes an attribute of the `logging` module with the value `level_num`.
    `method_name` becomes a convenience method for both `logging` itself and the class
    returned by `logging.getLoggerClass()` (usually just `logging.Logger`).
    If `method_name` is not specified, `level_name.lower()` is used.

    To avoid accidental clobberings of existing attributes, this method will raise an `AttributeError` if the
    level name is already an attribute of the `logging` module or if the method name is already present.
    """
    if not method_name:
        method_name = level_name.lower()

    if hasattr(logging, level_name):
        msg = f"{level_name} already defined in logging module"
        raise AttributeError(msg)
    if hasattr(logging, method_name):
        msg = f"{method_name} already defined in logging module"
        raise AttributeError(msg)
    if hasattr(logging.getLoggerClass(), method_name):
        msg = f"{method_name} already defined in logger class"
        raise AttributeError(msg)

    def for_logger_class(self, message, *args, **kwargs):
        if self.isEnabledFor(level_num):
            # This private member access is required; it is the name used in the logging class
            self._log(level_num, message, args, **kwargs)

    def for_logging_module(message, *args, **kwargs):
        logging.log(level_num, message, *args, **kwargs)

    logging.addLevelName(level_num, level_name)
    setattr(logging, level_name, level_num)
    setattr(logging.getLoggerClass(), method_name, for_logger_class)
    setattr(logging, method_name, for_logging_module)


def add_trace_level() -> None:
    """Add a new `TRACE` level to the `logging` module."""
    add_logging_level("TRACE", LOGGING_TRACE_LEVEL)


# Call at module level scope so it happens on import
add_trace_level()


def set_logger_level(level: int) -> None:
    """Initialize the default logger instance with a level.

    The intended usage is to pass the count of `--verbose` and `--quiet` arguments, as parsed from `args`:

    >>> set_logger_level(args.verbose - args.quiet)

    This assumes that those arguments are mutually exclusive and make use of the "count" action.
    """
    min_level = -2
    max_level = 3
    level_map = {
        -2: logging.CRITICAL,
        -1: logging.ERROR,
        0: logging.WARNING,
        1: logging.INFO,
        2: logging.DEBUG,
        3: LOGGING_TRACE_LEVEL,
    }
    level = min(max(level, min_level), max_level)
    logging_level = level_map.get(level, logging.NOTSET)
    if logging_level == LOGGING_TRACE_LEVEL:
        # Show level, path, and links only for `trace` level
        trace_rich_handler = RichHandler(
            console=console,
            show_time=False,
            show_level=True,
            show_path=True,
            rich_tracebacks=True,
            tracebacks_show_locals=True,
        )
        LOG.removeHandler(DEFAULT_RICH_HANDLER)
        LOG.addHandler(trace_rich_handler)
        add_trace_logging()

    # Set the level _after_ adding trace logging to avoid tracing the tracing setup
    LOG.setLevel(logging_level)
    LOG.debug("Logging initialized to level %s (%s)", logging_level, logging.getLevelName(logging_level))


def function_trace_logger(func: FunctionType) -> Callable:
    """Define a function decorator for trace level logging."""

    def traced_function(*args, **kwargs):
        LOG.log(
            LOGGING_TRACE_LEVEL,
            "[dim]Entering [reverse]%s",
            func.__name__,
            extra=MARKUP_NO_HI,
        )
        result = func(*args, **kwargs)
        LOG.log(
            LOGGING_TRACE_LEVEL,
            "[dim]Exiting [reverse]%s[/] -> %s",
            func.__name__,
            result,
            extra=MARKUP,
        )
        return result

    return traced_function


# This decorator was adapted from: https://bytepawn.com/python-decorator-patterns.html
def class_trace_logger(cls: type):
    """Class decorator for trace level logging.

    This decorator is meant to be applied to a class.
    It will add trace level logging for every method in the class.
    """

    def make_traced(cls: type, method_name: str, method: MethodType):
        def traced_method(*args, **kwargs):
            LOG.log(
                LOGGING_TRACE_LEVEL,
                "[dim]Entering [reverse]%s->%s",
                cls.__name__,
                method_name,
                extra=MARKUP_NO_HI,
            )
            result = method(*args, **kwargs)
            LOG.log(
                LOGGING_TRACE_LEVEL,
                "[dim]Exiting [reverse]%s->%s[/] -> %s",
                cls.__name__,
                method_name,
                result,
                extra=MARKUP,
            )
            return result

        return traced_method

    for name in cls.__dict__:
        cls_name_attr = getattr(cls, name)
        if callable(cls_name_attr) and name != "__class__":
            setattr(cls, name, make_traced(cls, name, cls_name_attr))
    return cls


def add_trace_logging() -> None:
    """Add trace logging to functions and classes in the package namespace."""
    pkg_namespace = f"{PKG_NAME}."
    phylum_modules = (module for module in sys.modules if module.startswith(pkg_namespace))

    phylum_funcs: dict[str, FunctionType] = {}
    phylum_classes: dict[str, type] = {}
    for module in phylum_modules:
        module_functions = inspect.getmembers(sys.modules[module], inspect.isfunction)
        if module_functions:
            phylum_funcs.update(module_functions)
        module_classes = inspect.getmembers(sys.modules[module], inspect.isclass)
        if module_classes:
            phylum_classes.update(module_classes)

    # Dynamically "decorate" the `phylum` functions
    for name, func in phylum_funcs.items():
        module_where_defined: str = func.__module__
        if module_where_defined.startswith(pkg_namespace):
            sys.modules[module_where_defined].__dict__[name] = function_trace_logger(func)

    # Dynamically "decorate" the `phylum` classes
    for name, cls in phylum_classes.items():
        module_where_defined = cls.__module__
        if module_where_defined.startswith(pkg_namespace):
            sys.modules[module_where_defined].__dict__[name] = class_trace_logger(cls)


def progress_spinner(desc: str) -> Callable:
    """Display a spinner for tasks with indeterminate progress.

    This is a function decorator that takes `desc` as a description of the task.
    """

    def make_traced(func: Callable) -> Callable:
        def traced_function(*args, **kwargs) -> Any:
            # Reference: https://rich.readthedocs.io/en/latest/progress.html
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                TimeElapsedColumn(),
                console=console,
                transient=True,
            ) as progress:
                task = progress.add_task(desc, total=None)
                result = func(*args, **kwargs)
                progress.stop_task(task)
            return result

        return traced_function

    return make_traced
