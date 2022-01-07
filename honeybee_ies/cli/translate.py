"""honeybee ies translation commands."""
import click
import sys
import pathlib
import logging

from honeybee.model import Model as HBModel
from dragonfly.model import Model as DFModel

_logger = logging.getLogger(__name__)


@click.group(help='Commands for translating Honeybee JSON files to IES files.')
def translate():
    pass


@translate.command('model-to-gem')
@click.argument('model-json', type=click.Path(
    exists=True, file_okay=True, dir_okay=False, resolve_path=True))
@click.option(
    '--name', '-n', help='Name of the output file.', default="model", show_default=True
)
@click.option(
    '--folder', '-f', help='Path to target folder.',
    type=click.Path(exists=False, file_okay=False, resolve_path=True,
                    dir_okay=True), default='.', show_default=True
)
@click.option(
    '--honeybee/--dragonfly', is_flag=True, help='A flag to indicate if the input '
    'file is a honeybee or a dragonfly file. Default is a Honeybee file.',
    default=True
)
def model_to_gem(model_json, name, folder, honeybee):
    """Translate a Model JSON file to an IES GEM file.
    \b

    Args:
        model_json: Full path to a Model JSON file (HBJSON/DFJSON) or a Model pkl
            (HBpkl/DFpkl) file.

    """
    try:
        if honeybee:
            model = HBModel.from_file(model_json)
        else:
            model = DFModel.from_file(model_json)

        folder = pathlib.Path(folder)
        folder.mkdir(parents=True, exist_ok=True)
        model.to_gem(folder.as_posix(), name=name)
    except Exception as e:
        _logger.exception('Model translation failed.\n{}'.format(e))
        sys.exit(1)
    else:
        sys.exit(0)
