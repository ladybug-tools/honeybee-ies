import os

from click.testing import CliRunner

from ladybug.futil import nukedir

from honeybee_ies.cli.translate import model_to_gem_cli


def test_model_to_gem():
    runner = CliRunner()
    input_hb_model = './tests/assets/sample_model_45.hbjson'
    folder = './tests/assets/temp'
    name = 'cli_test_45'

    result = runner.invoke(
        model_to_gem_cli, [input_hb_model, '--folder', folder, '--name', name]
    )
    print(result.output)
    assert result.exit_code == 0
    assert os.path.isfile(os.path.join(folder, f'{name}.gem'))
    nukedir(folder, True)
