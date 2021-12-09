import os

from click.testing import CliRunner

from ladybug.futil import nukedir

from honeybee_ies.cli.translate import model_to_gem


def test_model_to_rad_folder():
    runner = CliRunner()
    input_hb_model = './tests/assets/sample_model_45.hbjson'
    folder = './tests/assets/temp'
    name = 'cli_test_45'

    result = runner.invoke(
        model_to_gem, [input_hb_model, '--folder', folder, '--name', name]
    )
    assert result.exit_code == 0
    assert os.path.isfile(os.path.join(folder, f'{name}.gem'))
    nukedir(folder, True)
