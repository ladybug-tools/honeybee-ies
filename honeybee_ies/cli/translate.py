"""honeybee ies translation commands."""
import click
import sys
import os
import logging
import json

from ladybug.commandutil import process_content_to_output
from honeybee.model import Model
from honeybee_ies.writer import model_to_gem as model_to_gem_str
from honeybee_ies.reader import model_from_ies

_logger = logging.getLogger(__name__)


@click.group(help='Commands for translating Honeybee JSON files to and from IES files.')
def translate():
    pass


@translate.command('model-to-gem')
@click.argument('model-file', type=click.Path(
    exists=True, file_okay=True, dir_okay=False, resolve_path=True))
@click.option(
    '--shade-thickness', '-st', help='Optional value for shade thickness in meters. '
    'This value will be used to extrude shades with no group id. IES doesn\'t consider '
    'the effect of shades with no thickness in SunCalc. This function extrudes the '
    'geometry to create a closed volume for the shade.',
    type=click.FLOAT, default=0, show_default=True)
@click.option(
    '--name', '-n', help='Deprecated option to set the name of the output file.',
    default=None, show_default=True)
@click.option(
    '--folder', '-f', help='Deprecated option to set the path to target folder.',
    type=click.Path(file_okay=False, resolve_path=True, dir_okay=True), default=None)
@click.option(
    '--output-file', '-o', help='Optional GEM file path to output the GEM string '
    'of the translation. By default this will be printed out to stdout.',
    type=click.File('w'), default='-', show_default=True)
def model_to_gem_cli(model_file, shade_thickness, name, folder, output_file):
    """Translate a Model JSON file to an IES GEM file.
    \b

    Args:
        model_file: Full path to a Model JSON file (HBJSON) or a Model pkl (HBpkl) file.
    """
    try:
        if folder is not None and name is not None:
            if not name.lower().endswith('.gem'):
                name = name + '.gem'
            output_file = os.path.join(folder, name)
        model_to_gem(model_file, shade_thickness, output_file)
    except Exception as e:
        _logger.exception('Model translation failed.\n{}'.format(e))
        sys.exit(1)
    else:
        sys.exit(0)


def model_to_gem(model_file, shade_thickness=0, output_file=None):
    """Translate a Model JSON file to an IES GEM file.

    Args:
        model_file: Full path to a Honeybee Model file (HBJSON or HBpkl).
        shade_thickness: Optional value for shade thickness in meters. This value
            will be used to extrude shades with no group id. IES does not consider
            the effect of shades with no thickness in SunCalc. This function
            extrudes the geometry to create a closed volume for the shade. (Default: 0).
        output_file: Optional GEM file path to output the GEM string of the
            translation. If None, the string will be returned from this function.
    """
    model = Model.from_file(model_file)
    gem_str = model_to_gem_str(model, shade_thickness=shade_thickness)
    return process_content_to_output(gem_str, output_file)


@translate.command('gem-to-model')
@click.argument('gem-file', type=click.Path(
    exists=True, file_okay=True, dir_okay=False, resolve_path=True))
@click.option(
    '--name', '-n', help='Deprecated option to set the name of the output file.',
    default=None, show_default=True)
@click.option(
    '--folder', '-f', help='Deprecated option to set the path to target folder.',
    type=click.Path(file_okay=False, resolve_path=True, dir_okay=True), default=None)
@click.option(
    '--output-file', '-o', help='Optional HBJSON file path to output the HBJSON string '
    'of the translation. By default this will be printed out to stdout.',
    type=click.File('w'), default='-', show_default=True)
def gem_to_model_cli(gem_file, name, folder, output_file):
    """Translate an IES GEM file to a HBJSON model.
    \b

    Args:
        gem-file: Full path to an IES VE GEM file.
    """
    try:
        if folder is not None and name is not None:
            low_name = name.lower()
            if not low_name.endswith('.hbjson') and not low_name.endswith('.json'):
                name = name + '.hbjson'
            output_file = os.path.join(folder, name)
        gem_to_model(gem_file, output_file)
    except Exception as e:
        _logger.exception('Model translation failed.\n{}'.format(e))
        sys.exit(1)
    else:
        sys.exit(0)


def gem_to_model(gem_file, output_file=None):
    """Translate an IES GEM file to a HBJSON model.

    Args:
        gem_file: Full path to an IES VE GEM file.
        output_file: Optional HBJSON file path to output the JSON string of the
            translation. If None, the string will be returned from this function.
    """
    model = model_from_ies(gem_file)
    content_str = json.dumps(model.to_dict())
    return process_content_to_output(content_str, output_file)
