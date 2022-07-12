"""Templates for different objects in gem.

Note: This is based on our current understanding of the objects and based on the limited
available information online.
"""

# Type 4 is for shade
SHADE_TEMPLATE = 'LAYER\n64\n' + \
    'COLOUR\n62\n' + \
    'CATEGORY\n1\n' + \
    'TYPE\n4\n' + \
    'SUBTYPE\n0\n' + \
    'COLOURRGB\n65280\n' + \
    'IES {name}\n' \
    '{vertices_count} {face_count}\n' \
    '{vertices}\n' \
    '{faces}'


# Type 2 is for adjacent buildings
ADJ_BLDG_TEMPLATE = 'LAYER\n62\n' + \
    'COLOUR\n0\n' + \
    'CATEGORY\n1\n' + \
    'TYPE\n2\n' + \
    'SUBTYPE\n0\n' + \
    'COLOURRGB\n16711935\n' + \
    'IES {name}\n' \
    '{vertices_count} {face_count}\n' \
    '{vertices}\n' \
    '{faces}'


SPACE_TEMPLATE = 'LAYER\n1\n' + \
    'COLOUR\n0\n' + \
    'CATEGORY\n1\n' + \
    'TYPE\n1\n' + \
    'SUBTYPE\n2001\n' + \
    'COLOURRGB\n16711680\n' + \
    'IES {space_name}\n' \
    '{vertices_count} {face_count}\n' \
    '{vertices}\n' \
    '{faces}'
