from honeybee.model import Model
from honeybee_ies.writer import model_to_gem


def test_model():
    # serialize the model
    in_file = './tests/assets/sample_model_45.hbjson'
    model = Model.from_hbjson(in_file)
    # check that the model can be translated to GEM
    gem_str = model_to_gem(model)
    assert isinstance(gem_str, str)
