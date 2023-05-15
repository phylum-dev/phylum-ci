"""Test the package logging capabilities."""
import logging

import pytest

from phylum.logger import LOG, LOGGING_TRACE_LEVEL, set_logger_level


@pytest.mark.parametrize(
    ("input_level", "expected_level"),
    [
        (0, logging.WARNING),
        (1, logging.INFO),
        (2, logging.DEBUG),
        (3, LOGGING_TRACE_LEVEL),
        (4, LOGGING_TRACE_LEVEL),
        (-1, logging.ERROR),
        (-2, logging.CRITICAL),
        (-3, logging.CRITICAL),
    ],
)
@pytest.mark.usefixtures("_log")
def test_set_logger_level(input_level, expected_level):
    """Ensure the log verbosity options are handled correctly."""
    set_logger_level(input_level)
    assert LOG.getEffectiveLevel() == expected_level
