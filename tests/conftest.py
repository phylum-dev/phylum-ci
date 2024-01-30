"""Aggregate the pytest fixtures in one location."""

from collections.abc import Generator

import pytest

from phylum.logger import LOG


@pytest.fixture()
def _log() -> Generator:
    """Ensure the LOG level is restored to orginal value."""
    original_log_level = LOG.getEffectiveLevel()
    yield
    LOG.setLevel(original_log_level)
