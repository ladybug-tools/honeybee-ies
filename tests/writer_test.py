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
    ab_str = 'IES first line second line [FR000000]\n'

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
    ab_str = 'IES Shade 13c9e [Shade_13c9e001]\n' \
        '4 1\n' \
        '   -1.500000    -3.000000    2.500000\n' \
        '   2.500000    -3.000000    2.500000\n' \
        '   2.500000    0.000000    2.500000\n' \
        '   -1.500000    0.000000    2.500000\n' \
        '4 1 2 3 4\n' \
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

    room_str = 'IES Room w holes [RM000001]\n28 18'

    assert room_str in outf.read_text()


def test_model_with_pv():
    in_file = './tests/assets/pv.hbjson'
    out_folder = pathlib.Path('./tests/assets/temp')
    out_folder.mkdir(parents=True, exist_ok=True)
    model = Model.from_hbjson(in_file)
    outf = model_to_ies(model, out_folder.as_posix(), name='pv')
    assert outf.exists()

    pv_str = 'LAYER\n1\nCOLOUR\n0\nCATEGORY\n3\nTYPE\n202\nSUBTYPE\n0\n' \
        'COLOURRGB\n32767\n' \
        'PVP PV Panel [PV000000]\n' \
        '0.0315 -25.9269 8.54 4.0 1.0 225.0 120.0'

    assert pv_str in outf.read_text()


def test_model_with_tree():
    in_file = './tests/assets/tree.hbjson'
    out_folder = pathlib.Path('./tests/assets/temp')
    out_folder.mkdir(parents=True, exist_ok=True)
    model = Model.from_hbjson(in_file)
    outf = model_to_ies(model, out_folder.as_posix(), name='tree')
    assert outf.exists()

    tree_str = 'LAN Tree [TR000001]\n' \
        '2D Tree 2\n' \
        '0.0315 -30.9269 -0.0 1.0 1.0 1.0 60.0 0.0'

    assert tree_str in outf.read_text()


def test_model_with_topo():
    in_file = './tests/assets/topographical_shade.hbjson'
    out_folder = pathlib.Path('./tests/assets/temp')
    out_folder.mkdir(parents=True, exist_ok=True)
    model = Model.from_hbjson(in_file)
    outf = model_to_ies(model, out_folder.as_posix(), name='topographical_shade')
    assert outf.exists()

    topo_str = 'IES Missing Space [MS000000]\n' \
        '8 6\n' \
        '   9.303000    18.016400    -0.017700\n' \
        '   3.972000    13.144500    -0.017700\n' \
        '   -3.425000    16.664500    -0.017700\n' \
        '   -0.721300    20.133500    -0.017700\n' \
        '   -0.721300    20.133500    3.682300\n' \
        '   -3.425000    16.664500    3.682300\n' \
        '   3.972000    13.144500    3.682300\n' \
        '   9.303000    18.016400    3.682300\n' \
        '4 1 2 3 4\n' \
        '0\n' \
        '4 5 6 7 8\n' \
        '0\n' \
        '4 6 3 2 7\n' \
        '0\n' \
        '4 7 2 1 8\n' \
        '0\n' \
        '4 8 1 4 5\n' \
        '0\n' \
        '4 5 4 3 6\n' \
        '0'

    assert topo_str in outf.read_text()


def test_model_with_translucent_shade():
    in_file = './tests/assets/translucent_shade.hbjson'
    out_folder = pathlib.Path('./tests/assets/temp')
    out_folder.mkdir(parents=True, exist_ok=True)
    model = Model.from_hbjson(in_file)
    outf = model_to_ies(model, out_folder.as_posix(), name='translucent_shade')
    assert outf.exists()

    topo_str = 'IES Ground Floor [GR000000]\n' \
        '4 1\n' \
        '   9.175500    -0.018900    8.540000\n' \
        '   0.031500    -0.018900    8.540000\n' \
        '   0.031500    3.007600    8.540000\n' \
        '   9.175500    3.007600    8.540000\n' \
        '4 1 2 3 4\n' \
        '1\n' \
        '4 0\n' \
        '   9.175500    -0.018900    8.540000\n' \
        '   0.031500    -0.018900    8.540000\n' \
        '   0.031500    3.007600    8.540000\n' \
        '   9.175500    3.007600    8.540000'

    assert topo_str in outf.read_text()


def test_model_with_shade_mesh():
    in_file = './tests/assets/shade_mesh_example.hbjson'
    out_folder = pathlib.Path('./tests/assets/temp')
    out_folder.mkdir(parents=True, exist_ok=True)
    model = Model.from_hbjson(in_file)
    outf = model_to_ies(model, out_folder.as_posix(), name='shades_mesh')
    assert outf.exists()

    content = outf.read_text()
    assert 'IES Tree_1' in content
    assert 'IES Tree_2' in content
    assert 'IES Tree_3' in content
    assert '182 200' in content


def test_model_non_ascii():
    in_file = './tests/assets/room_non_ascii.hbjson'
    out_folder = pathlib.Path('./tests/assets/temp')
    out_folder.mkdir(parents=True, exist_ok=True)
    model = Model.from_hbjson(in_file)
    outf = model_to_ies(model, out_folder.as_posix(), name='room_non_ascii')
    assert outf.exists()

    content = outf.read_text(encoding='utf-8')
    assert 'IES اتاق خواب [' in content


def test_room_with_plenum():
    in_file = './tests/assets/room_with_plenum.hbjson'
    out_folder = pathlib.Path('./tests/assets/temp')
    out_folder.mkdir(parents=True, exist_ok=True)
    model = Model.from_hbjson(in_file)
    outf = model_to_ies(model, out_folder.as_posix(), name='room_with_plenum')
    assert outf.exists()

    floor_plenum_str = 'SUBTYPE\n' \
        '2002\n' \
        'COLOURRGB\n' \
        '16711680\n' \
        'IES 131-Corridor Floor Plenum [13000000]'

    room_str = 'SUBTYPE\n' \
        '2001\n' \
        'COLOURRGB\n' \
        '16711680\n' \
        'IES 131-Corridor [13000001]'

    ceiling_plenum_str = 'SUBTYPE\n' \
        '2002\n' \
        'COLOURRGB\n' \
        '16711680\n' \
        'IES 131-Corridor Ceiling Plenum [13000002]'

    content = outf.read_text()

    assert floor_plenum_str in content
    assert room_str in content
    assert ceiling_plenum_str in content
