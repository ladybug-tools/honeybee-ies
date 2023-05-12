"""honeybee ies translation commands."""
import click
import sys
import pathlib
import logging

from honeybee.model import Model
from honeybee_ies.reader import model_from_ies

_logger = logging.getLogger(__name__)


@click.group(help='Commands for translating Honeybee JSON files to and from IES files.')
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
    '--shade-thickness', '-st', help='Optional value for shade thickness in meters. '
    'This value will be used to extrude shades with no group id. IES doesn\'t consider '
    'the effect of shades with no thickness in SunCalc. This function extrudes the '
    'geometry to create a closed volume for the shade.',
    type=click.FLOAT, default=0, show_default=True
)
def model_to_gem(model_json, name, folder, shade_thickness):
    """Translate a Model JSON file to an IES GEM file.
    \b

    Args:
        model_json: Full path to a Model JSON file (HBJSON) or a Model pkl (HBpkl) file.

    """
    try:
        model = Model.from_file(model_json)
        folder = pathlib.Path(folder)
        folder.mkdir(parents=True, exist_ok=True)
        model.to_gem(folder.as_posix(), name=name, shade_thickness=shade_thickness)
    except Exception as e:
        _logger.exception('Model translation failed.\n{}'.format(e))
        sys.exit(1)
    else:
        sys.exit(0)


@translate.command('gem-to-model')
@click.argument('gem-file', type=click.Path(
    exists=True, file_okay=True, dir_okay=False, resolve_path=True))
@click.option(
    '--name', '-n', help='Name of the output file.', default="model", show_default=True
)
@click.option(
    '--folder', '-f', help='Path to target folder.',
    type=click.Path(exists=False, file_okay=False, resolve_path=True,
                    dir_okay=True), default='.', show_default=True
)
def gem_to_model(gem_file, name, folder):
    """Translate an IES GEM file to a HBJSON model.
    \b

    Args:
        gem-file: Full path to an IES VE GEM file.

    """
    try:
        model = model_from_ies(gem_file)
        folder = pathlib.Path(folder)
        folder.mkdir(parents=True, exist_ok=True)
        model.to_hbjson(name=name, folder=folder.as_posix())
    except Exception as e:
        _logger.exception('Model translation failed.\n{}'.format(e))
        sys.exit(1)
    else:
        sys.exit(0)
