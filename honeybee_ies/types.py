import enum
from typing import Dict


class GEM_TYPES(enum.Enum):
    """Enumeration for different object types in GEM.

    There is no public documentation for GEM files but here is our understanding based
    on the sample files.

    -----------------------------------------------------------------------------------
    |     object     | CATEGORY | TYPE | SUBTYPE | LAYER | COLOR | COL-RGB  | KEYWORD |
    -----------------------------------------------------------------------------------
    |  Rooms/Spaces  |    1     |  1   |   2001  |   1   |   0   | 16711680 |   IES   |
    |  UnCond Space  |    1     |  1   |   2002  |   1   |   0   | 16711680 |   IES   |
    |  Trans Shades  |    1     |  1   |   2102  |  64   |   0   |    0     |   IES   |
    |   Nghbr Bldg   |    1     |  2   |    0    |  62   |   0   | 16711935 |   IES   |
    |       PV       |    3     | 202  |    0    |   1   |   0   |  32767   |   PVP   |
    |      Tree      |    1     |  3   |    0    |  65   |   0   | 2399294  |   LAN   |
    |   Topography   |    1     |  3   |    0    |  63   |   0   |  38400   |   IES   |
    |  Local Shades  |    1     |  4   |    0    |  64   |  62   |  65280   |   IES   |
    |  Local Shades  |    1     |  4   |   2101  |  66   |   1   |  65280   |   IES   |
    """
    # '{CATEGORY}-{TYPE}-{SUBTYPE}-{LAYER}-{COLOR}-{COLORRGB}-{KEYWORD}'
    Space = '1-001-2001-01-00-16711680-IES'
    UnconditionedSpace = '1-001-2002-01-00-16711680-IES'
    TranslucentShade = '1-001-2102-64-00-0-IES'
    ContextBuilding = '1-002-0000-62-00-16711935-IES'
    PV = '3-202-0000-01-00-32767-PVP'
    Tree = '1-003-0000-65-00-2399294-LAN'
    Topography = '1-003-0000-63-00-38400-IES'
    Shade = '1-004-0000-64-62-65280-IES'
    Shade_2 = '1-004-2101-66-01-65280-IES'  #  shade in VE 2023

    @classmethod
    def from_info(cls, category: str, type_: int, subtype: int, keyword: str):
        if category == 1 and subtype == 2001 and type_ == 1 and keyword == 'IES':
            return cls.Space
        if category == 1 and subtype == 2002 and type_ == 1 and keyword == 'IES':
            # unconditioned space
            return cls.UnconditionedSpace
        elif category == 1 and subtype == 2102 and type_ == 1 and keyword == 'IES':
            return cls.TranslucentShade
        elif category == 1 and subtype == 0 and type_ == 2 and keyword == 'IES':
            return cls.ContextBuilding
        elif category == 3 and subtype == 0 and type_ == 202 and keyword == 'PVP':
            return cls.PV
        elif category == 1 and subtype == 0 and type_ == 3 and keyword == 'IES':
            return cls.Topography
        elif category == 1 and subtype == 0 and type_ == 3 and keyword == 'LAN':
            return cls.Tree
        elif category == 1 and subtype == 0 and type_ == 4 and keyword == 'IES':
            return cls.Shade
        elif category == 1 and subtype == 2101 and type_ == 4 and keyword == 'IES':
            return cls.Shade_2
        else:
            print(
                'Unknown combination of inputs in the input GEM file. Reach out to '
                'us with a copy of the GEM file and the information below:\n'
                f'{category}-{type_}-{subtype}-{keyword}'
            )
            return cls.Shade

    @classmethod
    def from_user_data(cls, user_data: Dict):
        """Get type from user_data."""
        if not user_data:
            return
        gem_type = user_data.get('__gem_type__', None)
        if not gem_type:
            # support old versions of HBJSON files
            gem_type = user_data.get('__ies_type__', None)
        if gem_type == 'topography':
            return cls.Topography
        elif gem_type == 'translucent_shade':
            return cls.TranslucentShade
        elif gem_type == 'pv':
            return cls.PV
        elif gem_type == 'tree':
            return cls.Tree

    def _get_numeric_values(self, index):
        return int(self.value.split('-')[index])

    def category(self):
        return self._get_numeric_values(0)

    def type(self):
        return self._get_numeric_values(1)

    def subtype(self):
        return self._get_numeric_values(2)

    def layer(self):
        return self._get_numeric_values(3)

    def color(self, rgb=False):
        return self._get_numeric_values(5) \
            if rgb else self._get_numeric_values(4)

    def keyword(self):
        return self.value.split('-')[-1]

    def to_gem(
            self, name: str, identifier: str, vertices: str, faces: str = '',
            vertices_count: int = 0, face_count: int = 0):
        """Get a formatted GEM string."""
        full_name = name if not identifier else f'{name} [{identifier}]'

        gem_header = f'LAYER\n{self.layer()}\n' + \
            f'COLOUR\n{self.color()}\n' + \
            f'CATEGORY\n{self.category()}\n' + \
            f'TYPE\n{self.type()}\n' + \
            f'SUBTYPE\n{self.subtype()}\n' + \
            f'COLOURRGB\n{self.color(True)}\n' + \
            f'{self.keyword()} {full_name}\n'

        if self.name in ('Tree', 'PV'):
            gem_str = gem_header + f'{vertices}'
            return gem_str
        else:
            gem_str = gem_header + f'{vertices_count} {face_count}\n' \
                f'{vertices}\n' \
                f'{faces}'
        if self.name == 'TranslucentShade':
            gem_str = '\n'.join(gem_str.split('\n')[:-1])
            gem_str += f'\n1\n{vertices_count} 0\n{vertices}'

        return gem_str
