import pathlib
from typing import List

from ladybug_geometry.geometry3d import Face3D
from honeybee.model import Model, Shade, Room

from .templates import SPACE_TEMPLATE, SHADE_TEMPLATE


def _opening_to_ies(
        parent_geo: Face3D, opening_geos: List[Face3D], opening_type: int = 0) -> str:
    """Translate an opening to gem format.
    
    Args:
        parent_geo: Geometry of the parent object.
        opening_geos: A list of Face3D geometries for openings.
        opening_type: An integer between 0-2. 0 for apertures, 1 for doors and 2 for
            holes.
    
    Returns:
        A formatted string for the opening.

    """
    if parent_geo.plane.n.z in (1, -1):
        origin, flip = parent_geo.upper_right_corner, True
    else:
        origin, flip = parent_geo.lower_left_corner, False
    openings = []
    for opening in opening_geos:
        verts_2d = parent_geo.polygon_in_face(opening, origin, flip)
        openings.append('{} {}'.format(len(verts_2d), opening_type))
        openings.append(
            '\n'.join('   {:.6f}    {:.6f}'.format(v.x, v.y) for v in verts_2d)
        )
    return '\n'.join(openings)


def shade_to_ies(shade: Shade) -> str:
    """Convert a Honeybee Shade to a GEM string.

    Args:
        shade: A Shade face.

    Returns:
        A formatted string that represents this shade in GEM format.

    """
    unique_vertices = shade.geometry.vertices
    vertices = '\n'.join(
        '   {:.6f}    {:.6f}    {:.6f}'.format(v.x, v.y, v.z)
        for v in unique_vertices
    )
    index = [str(i + 1) for i in range(len(unique_vertices))]
    shade_str = '%d %s \n0\n' % (len(index), ' '.join(index)) + \
        '%d %s \n0' % (len(index), ' '.join(reversed(index)))
    return SHADE_TEMPLATE.format(
        name=shade.display_name, vertices_count=len(unique_vertices),
        vertices=vertices, faces=shade_str
    )


def room_to_ies(room: Room) -> str:
    """Convert a Honeybee Shade to a GEM string.

    Args:
        room: A Honeybee Room.

    Returns:
        A formatted string that represents this room in GEM format.

    """
    unique_vertices = room.geometry.vertices
    vertices = '\n'.join(
        '   {:.6f}    {:.6f}    {:.6f}'.format(v.x, v.y, v.z)
        for v in unique_vertices
    )

    faces = []
    for face_i, face in zip(room.geometry.face_indices, room.faces):
        index = [str(v + 1) for v in face_i[0]]
        face_str = '%d %s \n' % (len(index), ' '.join(index))
        open_count, openings, fg = 0, [], face.geometry
        if fg.has_holes:
            sub_faces = [Face3D(hole, fg.plane) for hole in fg.holes]
            openings.append(_opening_to_ies(fg, sub_faces, 2))
            open_count += len(sub_faces)
        if len(face.apertures) != 0:
            sub_faces = [ap.geometry for ap in face.apertures]
            openings.append(_opening_to_ies(fg, sub_faces, 0))
            open_count += len(sub_faces)
        if len(face.doors) != 0:
            sub_faces = [dr.geometry for dr in face.doors]
            openings.append(_opening_to_ies(fg, sub_faces, 1))
            open_count += len(sub_faces)
        open_str = '\n' + '\n'.join(openings) if len(openings) != 0 else ''
        faces.append('%s%d%s' % (face_str, open_count, open_str))

    return SPACE_TEMPLATE.format(
        space_name=room.display_name, vertices_count=len(unique_vertices),
        face_count=len(room.faces), vertices=vertices, faces='\n'.join(faces)
    )


def model_to_ies(
        model: Model, folder: str = '.', name: str = None) -> pathlib.Path:
    """Export a honeybee model to an IES GEM file.

    Args:
        model: A honeybee model.
        folder: Path to target folder to export the file. Default is current folder.
        name: An optional name for exported file. By default the name of the model will
            be used.

    Returns:
        Path to exported GEM file.
    """
    header = 'COM GEM data file exported by Pollination Rhino\n' \
        'ANT\n'
    rooms_data = [room_to_ies(room) for room in model.rooms]
    # export context shade - we should probably also support exporting other types of
    # shades but I will wait for someone to ask for it!
    shades = [shade_to_ies(shade) for shade in model.shades]

    # write to GEM
    name = name or model.display_name
    if not name.lower().endswith('.gem'):
        name = f'{name}.gem'
    out_folder = pathlib.Path(folder)
    out_folder.mkdir(parents=True, exist_ok=True)
    out_file = out_folder.joinpath(name)
    with out_file.open('w') as outf:
        outf.write(header)
        outf.write('\n'.join(rooms_data) + '\n')
        outf.write('\n'.join(shades) + '\n')

    return out_file
