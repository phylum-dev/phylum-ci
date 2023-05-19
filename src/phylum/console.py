"""Provide a console object that can be used throughout the application.

The `rich` library is used here for excellent control over the console.
Reference: https://rich.readthedocs.io/en/latest/index.html
"""
from typing import Mapping, Union

from rich.console import Console
from rich.style import Style
from rich.theme import Theme

# Create a custom Phylum theme by setting unique style values for a subset of the markdown styles that `rich` supports.
# The full list of markdown styles, as of the time of this writing, is included here to make it easier to understand
# what can be modified. The default styles are also included so any future changes will not cause unexpected output.
# The colors chosen are from the standard 8-bit colors supported in terminals and are close to the range of blue colors
# that make up the Phylum logo. These colors are also able to be represented by a name instead of a hex or RGB value.
# References:
#   * https://rich.readthedocs.io/en/latest/style.html
#   * https://rich.readthedocs.io/en/latest/appendix/colors.html
PHYLUM_STYLES: Mapping[str, Union[str, Style]] = {
    # Styles that have been added to the default:
    "logging.level.trace": Style(dim=True),
    # Styles that have been modified from the default:
    "logging.level.debug": Style.null(),
    "logging.level.info": Style(color="green"),
    "logging.level.warning": Style(color="yellow"),
    "markdown.code": "bold reverse",
    "markdown.h1.border": "dodger_blue2",
    "markdown.h1": "dodger_blue2",
    "markdown.h2": "deep_sky_blue3",
    "markdown.h3": "underline cornflower_blue",
    "markdown.h4": "steel_blue1",
    "markdown.h5": "turquoise2",
    "markdown.h6": "cyan1",
    "markdown.h7": "bright_cyan",
    "markdown.item.bullet": "bold blue",
    "markdown.item.number": "bold blue",
    # The `rich` default styles:
    "code": "bold reverse",
    "repr.number": "bold not italic cyan",
    "traceback.border": "red",
    "progress.description": "none",
    "markdown.strong": "bold",
    "markdown.emph": "italic",
    "markdown.paragraph": "none",
    "markdown.text": "none",
    "markdown.code_block": "dim cyan on black",
    "markdown.block_quote": "magenta",
    "markdown.list": "cyan",
    "markdown.item": "none",
    "markdown.hr": "yellow",
    "markdown.link": "bright_blue",
    "markdown.link_url": "blue",
}

phylum_theme = Theme(styles=PHYLUM_STYLES)
console = Console(theme=phylum_theme, soft_wrap=True)
