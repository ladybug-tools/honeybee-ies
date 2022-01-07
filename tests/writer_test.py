import pathlib
from honeybee.model import Model as HBModel
from honeybee_ies.writer import hb_model_to_ies, df_model_to_ies
from dragonfly.model import Model as DFModel


def test_model():
    in_file = './tests/assets/revit_sample_model.hbjson'
    out_folder = pathlib.Path('./tests/assets/temp')
    out_folder.mkdir(parents=True, exist_ok=True) 
    model = HBModel.from_hbjson(in_file)
    outf = hb_model_to_ies(model, out_folder.as_posix(), name='revit_sample_model')
    assert outf.exists()


def test_room_shades():
    in_file = './tests/assets/lab_building.hbjson'
    out_folder = pathlib.Path('./tests/assets/temp')
    out_folder.mkdir(parents=True, exist_ok=True) 
    model = HBModel.from_hbjson(in_file)
    outf = hb_model_to_ies(model, out_folder.as_posix(), name='lab_building')
    assert outf.exists()
    assert 'TYPE\n4' in outf.read_text()


def test_df_model():
    in_file = './tests/assets/university_campus.dfjson'
    out_folder = pathlib.Path('./tests/assets/temp')
    out_folder.mkdir(parents=True, exist_ok=True) 
    model = DFModel.from_file(in_file)
    outf = df_model_to_ies(model, out_folder.as_posix(), name='uni_model')
    assert outf.exists()
