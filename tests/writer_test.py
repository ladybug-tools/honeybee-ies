import pathlib
from honeybee.model import Model
from honeybee_ies.writer import model_to_ies


def test_model():
    in_file = './tests/assets/revit_sample_model.hbjson'
    out_folder = pathlib.Path('./tests/assets/temp')
    out_folder.mkdir(parents=True, exist_ok=True) 
    model = Model.from_hbjson(in_file)
    outf = model_to_ies(model, out_folder.as_posix(), name='revit_sample_model')
    assert outf.exists()


def test_room_shades():
    in_file = './tests/assets/lab_building.hbjson'
    out_folder = pathlib.Path('./tests/assets/temp')
    out_folder.mkdir(parents=True, exist_ok=True) 
    model = Model.from_hbjson(in_file)
    outf = model_to_ies(model, out_folder.as_posix(), name='lab_building')
    assert outf.exists()
    assert 'TYPE\n4' in outf.read_text()


def test_air_boundary():
    in_file = './tests/assets/room_with_air_boundary.hbjson'
    out_folder = pathlib.Path('./tests/assets/temp')
    out_folder.mkdir(parents=True, exist_ok=True) 
    model = Model.from_hbjson(in_file)
    outf = model_to_ies(model, out_folder.as_posix(), name='room_with_air_boundary')
    assert outf.exists()
    ab_str = '4 2\n' \
        '   0.000000    0.000000\n' \
        '   11.000000    0.000000\n' \
        '   11.000000    3.000000\n' \
        '   0.000000    3.000000\n'

    assert ab_str in outf.read_text()
