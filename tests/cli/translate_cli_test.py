import os

from click.testing import CliRunner

from ladybug.futil import nukedir

from honeybee_ies.cli.translate import model_to_gem


def test_hb_model_to_ies():
    runner = CliRunner()
    input_hb_model = './tests/assets/sample_model_45.hbjson'
    folder = './tests/assets/temp'
    name = 'cli_test_45'

    result = runner.invoke(
        model_to_gem, [input_hb_model, '--folder', folder, '--name', name, '--honeybee']
    )
    assert result.exit_code == 0
    assert os.path.isfile(os.path.join(folder, f'{name}.gem'))
    nukedir(folder, True)


def test_df_model_to_ies():
    runner = CliRunner()
    input_df_model = './tests/assets/simple_model.dfjson'
    folder = './tests/assets/temp'
    name = 'cli_df_model'

    result = runner.invoke(
        model_to_gem, [input_df_model, '--folder', folder, '--name', name, '--dragonfly']
    )
    assert result.exit_code == 0
    assert os.path.isfile(os.path.join(folder, f'{name}.gem'))
    nukedir(folder, True)
