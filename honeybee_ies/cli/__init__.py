"""honeybee-ies commands which will be added to honeybee command line interface."""
import click
from honeybee.cli import main

from .translate import translate


# command group for all ies extension commands.
@click.group(help='honeybee ies commands.')
@click.version_option()
def ies():
    pass

ies.add_command(translate)

# add ies sub-commands to honeybee CLI
main.add_command(ies)
