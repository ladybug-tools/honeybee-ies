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


def test_display_name_clean_up():
    in_file = './tests/assets/multiline_name_test.hbjson'
    out_folder = pathlib.Path('./tests/assets/temp')
    out_folder.mkdir(parents=True, exist_ok=True) 
    model = Model.from_hbjson(in_file)
    outf = model_to_ies(model, out_folder.as_posix(), name='multiline_name_test')
    assert outf.exists()
    ab_str = 'IES first line second line\n'

    assert ab_str in outf.read_text()


def test_0_shade_thickness():
    in_file = './tests/assets/single_face_shade.hbjson'
    out_folder = pathlib.Path('./tests/assets/temp')
    out_folder.mkdir(parents=True, exist_ok=True) 
    model = Model.from_hbjson(in_file)
    outf = model_to_ies(
        model, out_folder.as_posix(), name='zero_shade_thickness', shade_thickness=0
    )
    assert outf.exists()
    ab_str = 'IES Shade 13c9e\n' \
        '4 1\n' \
        '   2.500000    0.000000    2.500000\n' \
        '   -1.500000    0.000000    2.500000\n' \
        '   -1.500000    -3.000000    2.500000\n' \
        '   2.500000    -3.000000    2.500000\n' \
        '4 1 2 3 4 \n' \
        '0'

    assert ab_str in outf.read_text()


def test_shade_with_holes():
    in_file = './tests/assets/shade_with_holes.hbjson'
    out_folder = pathlib.Path('./tests/assets/temp')
    out_folder.mkdir(parents=True, exist_ok=True)
    model = Model.from_hbjson(in_file)
    outf = model_to_ies(model, out_folder.as_posix(), name='shade_with_holes')
    assert outf.exists()

    hole_str = '4 2\n' \
        '   8.000000    2.000000\n' \
        '   8.000000    4.000000\n' \
        '   3.000000    4.000000\n' \
        '   3.000000    2.000000\n' \
        '4 2\n' \
        '   9.000000    7.000000\n' \
        '   9.000000    9.000000\n' \
        '   7.000000    9.000000\n' \
        '   7.000000    7.000000\n'

    assert hole_str in outf.read_text()


def test_model_with_holes():
    in_file = './tests/assets/model_with_holes.hbjson'
    out_folder = pathlib.Path('./tests/assets/temp')
    out_folder.mkdir(parents=True, exist_ok=True)
    model = Model.from_hbjson(in_file)
    outf = model_to_ies(model, out_folder.as_posix(), name='model_with_holes')
    assert outf.exists()

    room_str = 'IES Room w holes\n28 18'

    assert room_str in outf.read_text()
