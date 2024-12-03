# coding=utf-8
# import all of the modules for writing geometry to IES
from honeybee.properties import ModelProperties

from .properties.model import ModelIESProperties

# set a hidden ies attribute on each core geometry Property class to None
# define methods to produce ies property instances on each Property instance
ModelProperties._ies = None


def model_ies_properties(self):
    if self._ies is None:
        self._ies = ModelIESProperties(self.host)
    return self._ies


# add ies property methods to the Properties classes
ModelProperties.ies = property(model_ies_properties)
