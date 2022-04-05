"""Top-level package for phylum-ci."""
# TODO: Use only the standard library form (importlib.metadata) only after Python 3.7 support is dropped
#       https://github.com/phylum-dev/phylum-ci/issues/18
try:
    import importlib.metadata as importlib_metadata
except ModuleNotFoundError:
    import importlib_metadata


# TODO: Bump this version to at least 0.1.0 once there is more product centered functionality provided by this package
__version__ = importlib_metadata.version(__name__)
__author__ = importlib_metadata.metadata(__name__).get("Author")
__email__ = importlib_metadata.metadata(__name__).get("Author-email")
