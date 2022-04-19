# Default to the phylum-install entry point
from phylum.install.cli import main

# TODO: Add logic here to dynamically show the ways this package can be called as a module.
# Alternate idea: use this as a pass-through to call the true phylum CLI tool. That way, Python can be used to make
#                 the calls - `python -m phylum`
main()
