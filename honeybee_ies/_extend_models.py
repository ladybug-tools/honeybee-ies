from .writer import df_model_to_ies, shade_to_ies, room_to_ies, hb_model_to_ies
from honeybee.model import Shade, Room, Model as HBModel
from dragonfly.model import Model as DFModel

Shade.to_gem = shade_to_ies
Room.to_gem = room_to_ies
HBModel.to_gem = hb_model_to_ies
DFModel.to_gem = df_model_to_ies
