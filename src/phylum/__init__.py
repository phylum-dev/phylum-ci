"""Top-level package for phylum."""
# TODO: Use only the standard library form (importlib.metadata) only after Python 3.7 support is dropped
#       https://github.com/phylum-dev/phylum-ci/issues/18
try:
    import importlib.metadata as importlib_metadata
except ModuleNotFoundError:
    import importlib_metadata


PKG_METADATA = importlib_metadata.metadata(__name__)

__version__ = importlib_metadata.version(__name__)
__author__ = PKG_METADATA.get("Author")
__email__ = PKG_METADATA.get("Author-email")

PKG_NAME = PKG_METADATA.get("Name")
PKG_SUMMARY = PKG_METADATA.get("Summary")
