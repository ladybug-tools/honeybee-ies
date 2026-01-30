import re
import json
import pathlib
import math
from typing import List, Union, Dict

from ladybug_geometry.geometry3d import Face3D, Polyface3D, Point3D
from honeybee.model import Model, Shade, Room, AirBoundary, \
    RoofCeiling, Floor, ShadeMesh

from .reader import Z_AXIS, ROOF_ANGLE_TOLERANCE
from .types import GEM_TYPES


def _gen_ve_id(display_name: str) -> str:
    """Generate the VE identifier based on the name of the room.

    VE takes the first two alphanumerical values except for vowels from the display name.
    Then it adds an integer. For instance Room will be translated to RM000000. 1st floor
    will be translated to 1S000000. If there is already another room with the same 2
    characters then it adds to the number. RM000001, RM000002, and so on.

    This method only returns the 2 characters.
    """
    # Match any vowel character (case-insensitive), any whitespace, or any \
    # non-alphanumeric character
    pattern = r"[aeiouAEIOU\s\W]+"
    # Replace matched characters with an empty string
    identifier = re.sub(pattern, '', display_name).upper()
    if len(identifier) < 2:
        print(
            f'Unable to generate a valid GEM identifier from this name "{display_name}". '
            'Room display names must retain at least two characters after removing '
            'vowels.'
        )
        return 'ZZ'
    return identifier[:2]


def _convert_room_ids(model: Model) -> Dict:
    """Convert room identifiers to a valid VE identifier.

    This method updates the model directly, and returns a dictionary that maps the
    original identifier to the new VE identifier. The mapper is useful to find the
    rooms by ID from inside IES VE python editor.
    """
    id_mapper = {}
    id_counter = {}
    for room in model.rooms:
        room: Room
        identifier = room.identifier
        ve_identifier = _gen_ve_id(room.display_name)
        if ve_identifier not in id_counter:
            id_counter[ve_identifier] = -1
        id_counter[ve_identifier] += 1
        full_ve_id = f'{ve_identifier}{id_counter[ve_identifier]:06d}'
        id_mapper[identifier] = full_ve_id
        try:
            room.identifier = full_ve_id
        except AssertionError:
            room.identifier = f'RM{id_counter[ve_identifier]:06d}'
    return id_mapper


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
    geometry: Union[Face3D, Polyface3D, ShadeMesh], name: str,
    is_detached: bool = True, identifier: str = None,
    user_data: Dict = None
        ):

    open_count = 0
    faces = []

    gem_type = GEM_TYPES.from_user_data(user_data)
    if not gem_type:
        # it is a shade or a context building
        gem_type = GEM_TYPES.ContextBuilding if is_detached \
            else GEM_TYPES.Shade

    if gem_type == GEM_TYPES.PV:
        # calculate the bounds of the geometry based and translate it back to
        # GEM format
        w, h = geometry.boundary_polygon2d.max - geometry.boundary_polygon2d.min
        base = geometry.lower_right_corner
        yz_rotation = abs(90 - round(math.degrees(geometry.plane.altitude), 6))
        xy_rotation = abs(360 - round(math.degrees(geometry.plane.azimuth), 6))
        pv_info = f'{round(base.x, 4)} {round(base.y, 4)} {round(base.z, 4)} ' \
            f'{round(w, 4)} {round(h, 4)} ' \
            f'{round(xy_rotation, 4)} {round(yz_rotation, 4)}'
        return gem_type.to_gem(
                name=name, identifier=identifier, vertices=pv_info
            )

    if gem_type == GEM_TYPES.Tree:
        # TODO: create objects for every IES object to remove duplicate values
        # like the scales here
        x_scale = 3
        y_scale = 3
        z_scale = 8
        tree_type = user_data.get('__gem_tree_type__', 1)
        w, h = geometry.boundary_polygon2d.max - geometry.boundary_polygon2d.min
        base = (geometry.lower_right_corner + geometry.lower_left_corner) / 2
        # this logic won't work for values larger than 180 but that's for later
        xy_rotation = abs(90 - round(math.degrees(geometry.plane.azimuth), 6))
        yz_rotation = round(math.degrees(geometry.plane.altitude), 6)
        tree_info = f'2D Tree {tree_type}\n' \
            f'{round(base.x, 4)} {round(base.y, 4)} {round(base.z, 4)} ' \
            f'{round(w / x_scale, 4)} {round(w / y_scale, 4)} {round(h / z_scale, 4)} ' \
            f'{round(xy_rotation, 4)} {round(yz_rotation, 4)}'
        return gem_type.to_gem(
                name=name, identifier=identifier, vertices=tree_info
            )

    if isinstance(geometry, Polyface3D):
        unique_vertices = geometry.vertices
        vertices = _vertices_to_ies(unique_vertices)
        for face_i, face in zip(geometry.face_indices, geometry.faces):
            index = [str(v + 1) for v in face_i[0]]
            face_str = '%d %s\n' % (len(index), ' '.join(index))
            open_count, openings = 0, []
            if face.has_holes:
                sub_faces = [Face3D(hole, face.plane) for hole in face.holes]
                openings.append(_opening_to_ies(face, sub_faces, 2))
                open_count += len(sub_faces)

            open_str = '\n' + '\n'.join(openings) if len(openings) != 0 else ''
            faces.append('%s%d%s' % (face_str, open_count, open_str))
        face_count = len(geometry.faces)
    elif isinstance(geometry, ShadeMesh):
        # ShadeMesh
        unique_vertices = geometry.vertices
        vertices = _vertices_to_ies(unique_vertices)
        for face in geometry.faces:
            index = [str(v + 1) for v in face]
            face_str = '%d %s\n' % (len(index), ' '.join(index))
            faces.append(f'{face_str}0')
        face_count = len(geometry.faces)
    else:
        # Face 3D
        unique_vertices = geometry.lower_left_counter_clockwise_vertices
        vertices = _vertices_to_ies(unique_vertices)
        index = [str(v + 1) for v in range(len(unique_vertices))]
        face_str = '%d %s\n' % (len(index), ' '.join(index))
        open_count, openings = 0, []
        if geometry.has_holes:
            sub_faces = [Face3D(hole, geometry.plane) for hole in geometry.holes]
            openings.append(_opening_to_ies(geometry, sub_faces, 2))
            open_count += len(sub_faces)
        open_str = '\n' + '\n'.join(openings) if len(openings) != 0 else ''
        faces.append('%s%d%s' % (face_str, open_count, open_str))
        face_count = 1

    if len(unique_vertices) < 3:
        # a check for line-like mesh faces
        print('Invalid line-like shade object found and removed.')
        return ''

    return gem_type.to_gem(
        name=name, identifier=identifier,
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
        group_geometry, shade_name, first_shade.is_detached,
        first_shade.identifier, first_shade.user_data
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
        shade_geo, shade_name, is_detached=shade.is_detached,
        identifier=shade.identifier, user_data=shade.user_data
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
        user_data = shade.user_data
        if user_data and '__ies_import__' in user_data \
                and user_data['__ies_import__']:
            # ignore the shade face with __ies_import__ key
            continue
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

    single_keys = [key for key, value in shade_groups.items() if len(value) == 1]
    for key in single_keys:
        v = shade_groups.pop(key)
        no_groups.append(v[0])

    single_shades = '\n'.join([_shade_to_ies(shade, thickness) for shade in no_groups])
    group_shades = '\n'.join(
        [_shade_group_to_ies(shades) for shades in shade_groups.values()]
        )

    return '\n'.join((single_shades, group_shades))


def shade_meshes_to_ies(shades: List[ShadeMesh]) -> str:
    """Convert a list of ShadeMeshes to a GEM string.

    Args:
        shades: A list of ShadeMeshes.

    Returns:
        A formatted string that represents this shade in GEM format.

    """
    return '' if not shades else \
        '\n'.join(
            _shade_geometry_to_ies(
                geometry=shade, name=shade.display_name, is_detached=shade.is_detached,
                identifier=shade.identifier, user_data=shade.user_data
            ) for shade in shades
        )


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

    # remove new lines from the name
    room.display_name = ' '.join(room.display_name.split())

    unique_vertices = room.geometry.vertices
    vertices = _vertices_to_ies(unique_vertices)
    face_count = len(room.faces)
    faces = []
    air_boundary_count = 0
    _key = '__ies_import__'
    for face_i, face in zip(room.geometry.face_indices, room.faces):
        # ensure that the face_i are aligned with the face vertices
        boundary = tuple(unique_vertices[i] for i in face_i[0])
        rebuilt_face = Face3D(boundary)
        if not face.geometry.plane.n.angle(rebuilt_face.plane.n) <= math.radians(1):
            # face indices are reversed from Face3D objects
            face_i = [list(reversed(pt_i)) for pt_i in face_i]
        if isinstance(face.type, AirBoundary) and face.user_data \
                and _key in face.user_data:
            # This air boundary was created during the process of importing holes
            # from an IES GEM file. We don't write these air boundaries back to GEM.
            air_boundary_count += 1
            continue
        if isinstance(face.type, (RoofCeiling, Floor)) and face.geometry.has_holes:
            # IES doesn't like rooms with holes in them. We need to break the face
            # into smaller faces
            try:
                fgs = face.geometry.split_through_holes()
            except AssertionError as e:
                if 'There must be at least 3 vertices for a Polygon2D' not in str(e):
                    raise AssertionError(e)
                # ignore the hole
                print(
                    f'Failed to resolve the holes for {room.display_name}. Check the '
                    'input model to ensure the holes are not outside the parent face.'
                )
                fgs = [face.geometry]
                indexes = [[str(v + 1) for v in face_i[0]]]
            else:
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
            face_str = '%d %s\n' % (len(index), ' '.join(index))
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
                opaque_doors, glass_doors = [], []
                for dr in face.doors:
                    if dr.is_glass:
                        glass_doors.append(dr.geometry)
                    else:
                        opaque_doors.append(dr.geometry)
                if len(glass_doors) != 0:
                    openings.append(_opening_to_ies(fg, glass_doors, 0))
                    open_count += len(glass_doors)
                if len(opaque_doors) != 0:
                    openings.append(_opening_to_ies(fg, opaque_doors, 1))
                    open_count += len(opaque_doors)
            open_str = '\n' + '\n'.join(openings) if len(openings) != 0 else ''
            faces.append('%s%d%s' % (face_str, open_count, open_str))

    is_void = room.exclude_floor_area
    if is_void:
        space = GEM_TYPES.UnconditionedSpace.to_gem(
            name=room.display_name, identifier=room.identifier,
            vertices_count=len(unique_vertices),
            face_count=face_count - air_boundary_count,
            vertices=vertices, faces='\n'.join(faces)
        )
    else:
        space = GEM_TYPES.Space.to_gem(
            name=room.display_name, identifier=room.identifier,
            vertices_count=len(unique_vertices),
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


def model_to_gem(model: Model, shade_thickness: float = 0.0):
    """Generate an IES GEM string representation of a Model.

    Args:
        model: A honeybee model.
        shade_thickness:The thickness of the shade face in meters. This value will be
            used to extrude shades with no group id. IES doesn't consider the effect of
            shades with no thickness in SunCalc. This function extrudes the geometry to
            create a closed volume for the shade. (Default: 0.0).

    Returns:
        Text string representation of the contents of a GEM file derived from
        the input model.
    """
    # duplicate model to avoid mutating it as we edit it for GEM export
    original_model = model
    model = model.duplicate()
    # scale the model if the units are not meters
    if model.units != 'Meters':
        model.convert_to_units('Meters')
    # remove degenerate geometry within native IESVE tolerance of 0.001 meters
    try:
        model.remove_degenerate_geometry(0.001)
    except ValueError:
        error = 'Failed to remove degenerate Rooms.\nYour Model units system is: {}. ' \
            'Is this correct?'.format(original_model.units)
        raise ValueError(error)
    # split all room faces through their holes as they are not allowed in IES-VE
    model.split_rooms_through_holes()
    # ensure model has identifiers that are acceptable for GEM
    _convert_room_ids(model)
    # create and return the GEM file string
    header = 'COM GEM data file exported by Pollination\\nANT'
    rooms_data = [room_to_ies(room, shade_thickness=shade_thickness)
                  for room in model.rooms]
    context_shades = shades_to_ies(model.shades, thickness=shade_thickness)
    mesh_shades = shade_meshes_to_ies(model.shade_meshes)
    gem_data = [header] + rooms_data + [context_shades, mesh_shades]
    return '\n'.join(gem_data)


def model_to_ies(
    model: Model, folder: str = '.', name: str = None, shade_thickness: float = 0.0,
    write_id_mapper=True
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
        write_id_mapper: A boolean to indicate if the id mapper file should be written
            next to the gem file. It is a JSON file that maps the original identifier
            of the rooms in the honeybee model to the new identifier in GEM file.

    Returns:
        Path to exported GEM file.
    """
    # ensure model is in metric and has identifiers that are acceptable for GEM
    model = model.duplicate()
    model.convert_to_units(units='Meters')
    id_mapper = _convert_room_ids(model)

    # get the text for the GEM file contents
    header = 'COM GEM data file exported by Pollination\nANT\n'
    rooms_data = [room_to_ies(room, shade_thickness=shade_thickness)
                  for room in model.rooms]
    context_shades = shades_to_ies(model.shades, thickness=shade_thickness)
    mesh_shades = shade_meshes_to_ies(model.shade_meshes)

    # write to GEM
    name = name or model.display_name
    if not name.lower().endswith('.gem'):
        name = f'{name}.gem'
    out_folder = pathlib.Path(folder)
    out_folder.mkdir(parents=True, exist_ok=True)
    out_file = out_folder.joinpath(name)
    with out_file.open('w', encoding='utf-8') as outf:
        outf.write(header)
        outf.write('\n'.join(rooms_data) + '\n')
        outf.write(context_shades)
        outf.write(mesh_shades)

    if write_id_mapper:
        mapper_name = f'{name[:-4]}.im.json'
        mapper_out_file = out_folder.joinpath(mapper_name)
        mapper_out_file.write_text(json.dumps(id_mapper))

    return out_file
