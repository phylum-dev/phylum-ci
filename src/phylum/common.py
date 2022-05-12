"""Provide common data structures for the package."""
import argparse


class CustomFormatter(argparse.ArgumentDefaultsHelpFormatter, argparse.RawDescriptionHelpFormatter):
    """Custom argparse formatter to get both default arguments and help text line wrapping."""
