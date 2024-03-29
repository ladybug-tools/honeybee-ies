from honeybee_ies.reader import model_from_ies


def test_underground_aperture():
    in_file = './tests/assets/room_underground.gem'
    model = model_from_ies(in_file)
    assert len(model.rooms) == 2


def test_topo_shade():
    in_file = './tests/assets/topographical_shade.gem'
    model = model_from_ies(in_file)
    assert len(model.shades) == 6


def test_translucent_shade():
    in_file = './tests/assets/translucent_shade.gem'
    model = model_from_ies(in_file)
    assert len(model.shades) == 1


def test_tree():
    in_file = './tests/assets/tree.gem'
    model = model_from_ies(in_file)
    assert len(model.shades) == 10


def test_pv():
    in_file = './tests/assets/pv.gem'
    model = model_from_ies(in_file)
    assert len(model.shades) == 1


def test_non_ascii():
    in_file = './tests/assets/room_non_ascii.gem'
    model = model_from_ies(in_file)
    assert model.rooms[0].display_name == 'اتاق خواب'
