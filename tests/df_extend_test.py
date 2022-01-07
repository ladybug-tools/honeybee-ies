import pathlib
from dragonfly.model import Model


def test_model():
    in_file = './tests/assets/simple_model.dfjson'
    out_folder = pathlib.Path('./tests/assets/temp')
    out_folder.mkdir(parents=True, exist_ok=True) 
    model = Model.from_file(in_file)
    outf = model.to_gem(out_folder.as_posix(), name='simple_model')
    assert outf.exists()
