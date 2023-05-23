"""Top-level package for phylum."""
from importlib.metadata import metadata, version
import logging

PKG_METADATA = metadata(__name__)

__version__ = version(__name__)
__author__ = PKG_METADATA["Author"]
__email__ = PKG_METADATA["Author-email"]

PKG_NAME = PKG_METADATA["Name"]
PKG_SUMMARY = PKG_METADATA["Summary"]

LOG = logging.getLogger(PKG_NAME)
