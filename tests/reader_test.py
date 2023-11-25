import pathlib
from honeybee.model import Model
from honeybee_ies.reader import model_from_ies

def test_underground_aperture():
    in_file = './tests/assets/room_underground.gem'
    model = model_from_ies(in_file)
    assert len(model.rooms) == 2


def test_topo_shade():
    in_file = './tests/assets/topographical_shade.gem'
    model = model_from_ies(in_file)
    assert len(model.shades) == 6
