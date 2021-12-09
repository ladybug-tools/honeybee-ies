import pathlib
from honeybee.model import Model


def test_model():
    in_file = './tests/assets/sample_model_45.hbjson'
    out_folder = pathlib.Path('./tests/assets/temp')
    out_folder.mkdir(parents=True, exist_ok=True) 
    model = Model.from_hbjson(in_file)
    outf = model.to_gem(out_folder.as_posix(), name='sample_model_45')
    assert outf.exists()
