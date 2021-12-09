from .writer import shade_to_ies, room_to_ies, model_to_ies
from honeybee.model import Shade, Room, Model

Shade.to_gem = shade_to_ies
Room.to_gem = room_to_ies
Model.to_gem = model_to_ies
