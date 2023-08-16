import pathlib
from typing import List, Union

from ladybug_geometry.geometry3d import Face3D, Polyface3D, Point3D
from honeybee.model import Model, Shade, Room, AirBoundary, RoofCeiling, Floor

from .templates import SPACE_TEMPLATE, SHADE_TEMPLATE, ADJ_BLDG_TEMPLATE
from .reader import Z_AXIS, ROOF_ANGLE_TOLERANCE


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
    elif parent_geo.plane.n.angle(Z_AXIS) < ROOF_ANGLE_TOLERANCE:
        origin, flip = parent_geo.lower_left_corner, True
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


def _vertices_to_ies(vertices: List[Point3D]) -> str:
    """Get a string for vertices in GEM format."""
    vertices = '\n'.join(
        '   {:.6f}    {:.6f}    {:.6f}'.format(v.x, v.y, v.z)
        for v in vertices
    )
    return vertices


def _shade_geometry_to_ies(
    geometry: Union[Face3D, Polyface3D], name: str, is_detached=True
        ):

    open_count = 0
    faces = []

    if isinstance(geometry, Polyface3D):
        unique_vertices = geometry.vertices
        vertices = _vertices_to_ies(unique_vertices)
        for face_i, face in zip(geometry.face_indices, geometry.faces):
            index = [str(v + 1) for v in face_i[0]]
            face_str = '%d %s \n' % (len(index), ' '.join(index))
            open_count, openings = 0, []
            if face.has_holes:
                sub_faces = [Face3D(hole, face.plane) for hole in face.holes]
                openings.append(_opening_to_ies(face, sub_faces, 2))
                open_count += len(sub_faces)

            open_str = '\n' + '\n'.join(openings) if len(openings) != 0 else ''
            faces.append('%s%d%s' % (face_str, open_count, open_str))
        face_count = len(geometry.faces)
    else:
        # Face 3D
        unique_vertices = geometry.lower_left_counter_clockwise_vertices
        vertices = _vertices_to_ies(unique_vertices)
        index = [str(v + 1) for v in range(len(unique_vertices))]
        face_str = '%d %s \n' % (len(index), ' '.join(index))
        open_count, openings = 0, []
        if geometry.has_holes:
            sub_faces = [Face3D(hole, face.plane) for hole in face.holes]
            openings.append(_opening_to_ies(face, sub_faces, 2))
            open_count += len(sub_faces)
        open_str = '\n' + '\n'.join(openings) if len(openings) != 0 else ''
        faces.append('%s%d%s' % (face_str, open_count, open_str))
        face_count = 1

    template = ADJ_BLDG_TEMPLATE if is_detached else SHADE_TEMPLATE

    if len(unique_vertices) < 3:
        # a check for line-like mesh faces
        print('Invalid line-like shade object found and removed.')
        return ''

    return template.format(
        name=name,
        vertices_count=len(unique_vertices),
        vertices=vertices,
        faces='\n'.join(faces),
        face_count=face_count
    )


def _shade_group_to_ies(shades: List[Shade]) -> str:
    """Convert a group of shades into a GEM string.

    The files in the shade group should create a closed volume. The translator uses
    the name of the first shade as the name of the group.
    """
    group_geometry = Polyface3D.from_faces(
        [shade.geometry for shade in shades], tolerance=0.001
    )
    first_shade = shades[0]
    # remove new lines from the name
    shade_name = ' '.join(first_shade.display_name.split())
    return _shade_geometry_to_ies(
        group_geometry, shade_name, first_shade.is_detached
    )


def _shade_to_ies(shade: Shade, thickness: float = 0.01) -> str:
    """Convert a single Honeybee Shade to a GEM string.

    Args:
        shade: A Shade face.
        thickness:The thickness of the shade face in meters. IES doesn't consider the
            effect of shades with no thickness in SunCalc. This function extrudes the
            geometry to create a closed volume for the shade. Default: 0.01

    Returns:
        A formatted string that represents this shade in GEM format.

    """
    if thickness == 0:
        # don't add the thickness
        shade_geo = shade.geometry
    else:
        geometry = shade.geometry
        move_vector = geometry.normal.reverse().normalize() * thickness / 2
        base_geo = geometry.move(move_vector)
        shade_geo = Polyface3D.from_offset_face(base_geo, thickness)

    # remove new lines from the name
    shade_name = ' '.join(shade.display_name.split())
    return _shade_geometry_to_ies(
        shade_geo, shade_name, is_detached=shade.is_detached
    )


def shades_to_ies(shades: List[Shade], thickness: float = 0.01) -> str:
    """Convert a list of Shades to a GEM string.

    Args:
        shades: A list of Shade faces.
        thickness:The thickness of the shade face in meters. This value will be used to
            extrude shades with no group id. IES doesn't consider the effect of shades
            with no thickness in SunCalc. This function extrudes the geometry to create
            a closed volume for the shade. Default: 0.01

    Returns:
        A formatted string that represents this shade in GEM format.

    """
    shade_groups = {}
    no_groups = []
    for shade in shades:
        try:
            group_id = shade.user_data['__group_id__']
        except (TypeError, KeyError):
            no_groups.append(shade)
            continue
        else:
            if group_id not in shade_groups:
                shade_groups[group_id] = [shade]
            else:
                shade_groups[group_id].append(shade)

    single_shades = '\n'.join([_shade_to_ies(shade, thickness) for shade in no_groups])
    group_shades = '\n'.join(
        [_shade_group_to_ies(shades) for shades in shade_groups.values()]
        )

    return '\n'.join((single_shades, group_shades))


def room_to_ies(room: Room, shade_thickness: float = 0.01) -> str:
    """Convert a Honeybee Shade to a GEM string.

    Args:
        room: A Honeybee Room.
        shade_thickness:The thickness of the shade face in meters. This value will be
            used to extrude shades with no group id. IES doesn't consider the effect of
            shades with no thickness in SunCalc. This function extrudes the geometry to
            create a closed volume for the shade. Default: 0.01
    Returns:
        A formatted string that represents this room in GEM format.

    """

    def _find_index(vertex: Point3D, vertices: List[Point3D], tolerance=0.01):
        for c, v in enumerate(vertices):
            if v.distance_to_point(vertex) <= tolerance:
                return str(c + 1)
        else:
            raise ValueError(f'Failed to find {vertex} in the vertices.')

    unique_vertices = room.geometry.vertices
    vertices = _vertices_to_ies(unique_vertices)
    face_count = len(room.faces)
    faces = []
    air_boundary_count = 0
    _key = '__ies_import__'
    for face_i, face in zip(room.geometry.face_indices, room.faces):
        if isinstance(face.type, AirBoundary) and face.user_data \
                and _key in face.user_data:
            # This air boundary was created during the process of importing holes
            # from an IES GEM file. We don't write these air boundaries back to GEM.
            air_boundary_count += 1
            continue
        if isinstance(face.type, (RoofCeiling, Floor)) and face.geometry.has_holes:
            # IES doesn't like rooms with holes in them. We need to break the face
            # into smaller faces
            fgs = face.geometry.split_through_holes()
            face_count += len(fgs) - 1
            indexes = [
                [
                    _find_index(v, unique_vertices)
                    for v in fg.lower_left_counter_clockwise_vertices
                ] for fg in fgs
            ]
        else:
            fgs = [face.geometry]
            indexes = [[str(v + 1) for v in face_i[0]]]

        for index, fg in zip(indexes, fgs):
            face_str = '%d %s \n' % (len(index), ' '.join(index))
            open_count, openings = 0, []
            if isinstance(face.type, AirBoundary):
                # add the face itself as the hole
                sub_faces = [Face3D(fg.vertices, fg.plane)]
                openings.append(_opening_to_ies(fg, sub_faces, 2))
                open_count += 1
            elif fg.has_holes:
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

    # remove new lines from the name
    room_name = ' '.join(room.display_name.split())
    space = SPACE_TEMPLATE.format(
        space_name=room_name, vertices_count=len(unique_vertices),
        face_count=face_count - air_boundary_count,
        vertices=vertices, faces='\n'.join(faces)
    )

    # collect all the shades from room
    shades = [shade for shade in room.shades]
    for face in room.faces:
        for aperture in face.apertures:
            for shade in aperture.shades:
                shades.append(shade)
        for door in face.doors:
            for shade in door.shades:
                shades.append(shade)
    if shades:
        formatted_shades = shades_to_ies(shades=shades, thickness=shade_thickness)
        return '\n'.join((space, formatted_shades))
    else:
        return space


def model_to_ies(
    model: Model, folder: str = '.', name: str = None, shade_thickness: float = 0.0
        ) -> pathlib.Path:
    """Export a honeybee model to an IES GEM file.

    Args:
        model: A honeybee model.
        folder: Path to target folder to export the file. Default is current folder.
        name: An optional name for exported file. By default the name of the model will
            be used.
        shade_thickness:The thickness of the shade face in meters. This value will be
            used to extrude shades with no group id. IES doesn't consider the effect of
            shades with no thickness in SunCalc. This function extrudes the geometry to
            create a closed volume for the shade. Default: 0.0

    Returns:
        Path to exported GEM file.
    """
    # ensure model is in metrics
    model.convert_to_units(units='Meters')

    header = 'COM GEM data file exported by Pollination\n' \
        'ANT\n'
    rooms_data = [
        room_to_ies(room, shade_thickness=shade_thickness) for room in model.rooms
    ]
    context_shades = shades_to_ies(model.shades, thickness=shade_thickness)

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
        outf.write(context_shades)

    return out_file
