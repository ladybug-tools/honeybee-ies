import math
import pathlib
import re
from typing import Iterator, List, Tuple, Union, Dict
import uuid

from ladybug_geometry.geometry3d import Face3D, Point3D, Vector3D, \
    Plane, Mesh3D
from ladybug_geometry.geometry2d import Polygon2D, Point2D, Vector2D
from ladybug_geometry.geometry2d.polygon import closest_point2d_on_line2d
from honeybee.model import Model, Shade, Room, Face, Aperture, Door, \
    AirBoundary, ShadeMesh
from honeybee.boundarycondition import Outdoors, Ground
from honeybee.typing import clean_string, clean_and_id_ep_string

from .types import GEM_TYPES


PI = math.pi
Z_AXIS = Vector3D(0, 0, 1)
ROOF_ANGLE_TOLERANCE = math.radians(10)
MODEL_TOLERANCE = 0.001


def _gem_object_type(info: str, keyword: str = 'IES') -> GEM_TYPES:
    """Get GEM object type from info."""
    type_ = int(re.findall(r'^TYPE\n(\d*)', info, re.MULTILINE)[0])
    subtype = int(re.findall(r'^SUBTYPE\n(\d*)', info, re.MULTILINE)[0])
    category = int(re.findall(r'^CATEGORY\n(\d*)', info, re.MULTILINE)[0])
    return GEM_TYPES.from_info(
        category=category, type_=type_, subtype=subtype, keyword=keyword
    )


def _add_user_date(face: Union[Face, Shade], user_data: Dict):
    """Add user data to a face or a shade object."""
    if not user_data:
        return
    if face.user_data:
        # the dictionary exists
        face.user_data.update(user_data)
    else:
        face.user_data = user_data


def _get_id(display_name):
    """Extract the id from display name.

    In version 2023 the ID is included in the GEM file as inside [] at the end of the
    name.
    """
    id_ = re.findall(r'\s\[(.*)\]$', display_name, re.MULTILINE)
    if id_:
        return id_[0]
    else:
        return None


def _update_name(obj: Union[Shade, Room], display_name: str, count: int = None):
    """Add group id and display name to objects."""
    if not isinstance(obj, Room):
        identifier = \
            clean_string(display_name) if count \
            else clean_string(f'{display_name}-{count}')
        _add_user_date(
            face=obj, user_data={'__group_id__': identifier}
        )

    id_ = _get_id(display_name)
    if id_:
        obj.identifier = f'{id_}-{count}' if count else id_
        obj.display_name = display_name.replace(f' [{id_}]', '')
    else:
        obj.display_name = display_name


def _create_shade(
        boundary: List[Point3D], holes: List[Point3D] = None,
        is_detached: bool = True, user_data: Dict = None):
    """Create a Honeybee Shade object"""
    geometry = Face3D(boundary, holes=holes)
    face = Shade(
        str(uuid.uuid4()), geometry=geometry,
        is_detached=is_detached
    )
    _add_user_date(face, user_data)
    return face


def _opening_from_ies(geometry: Face3D, content: Iterator) -> Tuple[List[Point3D], int]:
    """Translate an opening from gem format.

    Args:
        parent_geo: Geometry of the parent object.
        content: A GEM string

    Returns:
        opening_geos: A list of Face3D geometries for openings.
        opening_type: An integer between 0-2. 0 for apertures, 1 for doors and 2 for
            holes.
    """

    if geometry.plane.n.z in (1, -1):
        # horizontal faces
        origin = geometry.upper_right_corner
    else:
        origin = geometry.lower_left_corner

    # This is how the next line looks
    # 5 2
    ver_count, opening_type = [int(float(v)) for v in next(content).split()]

    # calculate the vertices from X, Y values
    # 0.000000     0.906100
    # 0.000000     0.000000
    # 10.373100     0.000000
    tolerance = MODEL_TOLERANCE * 5
    boundary_2d: Polygon2D = geometry.boundary_polygon2d
    offset_boundary_2d = boundary_2d.offset(tolerance)
    origin_2d = geometry.plane.xyz_to_xy(origin)

    # create vertices in 2D
    opening_vertices = []
    opening_vertices_2d = []
    for _ in range(ver_count):
        cnt = next(content).split()
        if len(cnt) == 2:
            x_m, y_m = [float(v) for v in cnt]
        elif len(cnt) == 3:
            # Translucent shade
            x_m, y_m, opacity = [float(v) for v in cnt]
        vertex_2d = Point2D(origin_2d.x - x_m, origin_2d.y - y_m)
        vertex = geometry.plane.xy_to_xyz(vertex_2d)
        on_segments = []
        for segment in boundary_2d.segments:
            close_pt = closest_point2d_on_line2d(vertex_2d, segment)
            if vertex_2d.distance_to_point(close_pt) <= tolerance:
                on_segments.append((segment, close_pt))

        if not on_segments or opening_type == 2:
            # for holes don't move the vertex
            pass
        elif len(on_segments) == 1:
            # it is an edge
            vector: Vector2D = on_segments[0][0].v
            v1 = vector.rotate(PI / 2).normalize() * tolerance
            v2 = vector.rotate(-PI / 2).normalize() * tolerance
            v = vertex_2d.move(v1)
            if boundary_2d.is_point_inside_check(v):
                vertex_2d = v
            else:
                v = vertex_2d.move(v2)
                if boundary_2d.is_point_inside_check:
                    vertex_2d = v
        elif len(on_segments) == 2:
            # The point is adjacent to a corner. Find the closest point to the offset boundary
            dist_col = []
            for seg in offset_boundary_2d.segments:
                cp = seg.closest_point(vertex_2d)
                dist = cp.distance_to_point(vertex_2d)
                dist_col.append([dist, cp])

            points_sorted = sorted(dist_col, key=lambda x: x[0])
            vertex_2d = points_sorted[0][1]
        else:
            # this should not happen!
            print(f'{vertex} is adjacent to more than 2 edges of the same polygon.')

        vertex = geometry.plane.xy_to_xyz(vertex_2d)
        opening_vertices.append(vertex)
        opening_vertices_2d.append(vertex_2d)

    org_pl = Polygon2D(opening_vertices_2d)
    opening_area = org_pl.area

    return opening_type, opening_vertices, opening_vertices_2d, opening_area


def _create_tree(info: str, tree_type=1) -> Shade:
    """Create a Tree from an IES Tree."""
    values = [float(v) for v in info.strip().split()]
    assert len(values) == 8, 'Length of data for tree is not 8 segments.'
    # calculate tree geometry
    x, y, z, x_scale, y_scale, z_scale, xy_rotation, yz_rotation = values
    x_scale *= 3
    y_scale *= 3
    z_scale *= 8
    base = Point3D(x, y, z)
    # move the base plane for half the x_scale
    x_base = Plane(o=base, n=Vector3D(0, -1, 0), x=Vector3D(1, 0, 0))
    x_base = x_base.move(Vector3D(-x_scale / 2, 0, 0))
    y_base = Plane(o=base, n=Vector3D(1, 0, 0), x=Vector3D(0, 1, 0))
    y_base = y_base.move(Vector3D(0, -y_scale / 2, 0))
    geometries = [
        Face3D.from_rectangle(x_scale, z_scale, x_base),
        Face3D.from_rectangle(y_scale, z_scale, y_base)
    ]
    geos = []
    for geometry in geometries:
        if yz_rotation:
            axis = Vector3D(-1, 0, 0)
            geometry = geometry.rotate(axis, math.radians(yz_rotation), base)
        if xy_rotation:
            geometry = geometry.rotate_xy(math.radians(xy_rotation), base)
        geos.append(geometry)

    tree_0 = _create_shade(
        geos[0].lower_left_counter_clockwise_vertices,
        user_data={
            '__gem_type__': 'tree',
            '__gem_tree_type__': tree_type,
            '__ies_import__': True
        }
    )

    tree_1 = _create_shade(
        geos[1].lower_left_counter_clockwise_vertices,
        user_data={
            '__gem_type__': 'tree',
            '__gem_tree_type__': tree_type
        }
    )

    return tree_0, tree_1


def _create_pv(info: str) -> Shade:
    """Create a PV panel from GEM PV panel."""
    values = [float(v) for v in info.strip().split()]
    assert len(values) == 7, 'Length of data for PV is not 7 segments.'
    # calculate PV geometry
    x, y, z, width, height, xy_rotation, yz_rotation = values
    base = Point3D(x, y, z)
    base_plane = Plane(o=base)
    geometry = Face3D.from_rectangle(width, -height, base_plane)
    if yz_rotation:
        axis = Vector3D(-1, 0, 0)
        geometry = geometry.rotate(axis, math.radians(yz_rotation), base)
    if xy_rotation:
        geometry = geometry.rotate_xy(math.radians(xy_rotation), base)

    pv = _create_shade(
        geometry.lower_left_counter_clockwise_vertices,
        user_data={'__gem_type__': 'pv'}
    )

    return pv


def _parse_gem_segment(
        segment: str, ignore_shade_mesh=False) -> Union[Room, ShadeMesh, Shade]:
    """Parse a segment of the GEM file.

    Each segment has the information for a room or a shade object.
    """
    for keyword in ['IES', 'LAN', 'PVP']:
        if keyword in segment:
            info, segments = re.split(f'\n{keyword} ', segment)
            break
    else:
        raise ValueError(
            'There is a segment with an unsupported type in the input GEM file. '
            'Reach out to us with a copy of the GEM file and the information below:\n'
            f'{segment}'
        )

    gem_type = _gem_object_type(info=info, keyword=keyword)

    # remove empty lines if any
    content = iter(lin for lin in segments.split('\n') if lin.strip())
    display_name = next(content)
    cleaned_display_name = clean_string(display_name)
    identifier = clean_and_id_ep_string(cleaned_display_name)
    if gem_type == GEM_TYPES.PV:
        pv_info = next(content)
        face = _create_pv(pv_info)
        _update_name(face, display_name)
        return [face]
    elif gem_type == GEM_TYPES.Tree:
        tree_type = next(content)
        assert tree_type.startswith('2D Tree'), \
            f'{tree_type} is not currently supported.'
        tree_type = int(tree_type.split()[-1])
        tree_info = next(content)
        faces = _create_tree(tree_info, tree_type=tree_type)
        for count, face in enumerate(faces):
            _update_name(face, display_name, count)
        return faces

    faces = []
    # everything else
    ver_count, face_count = [int(v) for v in next(content).split()]
    vertices = [
        Point3D(*[float(v) for v in next(content).split()])
        for _ in range(ver_count)
    ]

    # create a shade mesh for shades with multiple faces
    if not ignore_shade_mesh \
        and gem_type == GEM_TYPES.ContextBuilding \
            and face_count > 1:
        faces = []
        for _ in range(face_count):
            boundary = tuple(int(i) - 1 for i in next(content).split()[1:])
            opening_count = int(next(content))  # pass the line for the opening count
            if opening_count > 0 or len(boundary) > 4:
                # there is a hole in the shade or the face has more than 4 edges
                # use the old method of using faces instead
                return _parse_gem_segment(segment, True)
            faces.append(boundary)
        mesh_geometry = Mesh3D(vertices=vertices, faces=faces)
        mesh = ShadeMesh(identifier=identifier, geometry=mesh_geometry, is_detached=True)
        _update_name(mesh, display_name)
        return mesh

    # create faces
    for _ in range(face_count):
        apertures = []
        doors = []
        holes = []
        holes_2d = []
        boundary = [vertices[int(i) - 1] for i in next(content).split()[1:]]
        boundary_geometry = Face3D(boundary, enforce_right_hand=False)
        boundary_geometry_polygon2d = boundary_geometry.boundary_polygon2d
        boundary_area = boundary_geometry.area
        holes_area = 0
        opening_count = int(next(content))
        for _ in range(opening_count):
            opening_type, opening_vertices, opening_vertices_2d, opening_area = \
                _opening_from_ies(boundary_geometry, content)
            if opening_type == 0:
                # create an aperture
                aperture_geo = Face3D(opening_vertices)
                aperture = Aperture(str(uuid.uuid4()), aperture_geo)
                apertures.append(aperture)
            elif opening_type == 1:
                # create a door
                door_geo = Face3D(opening_vertices)
                door = Door(str(uuid.uuid4()), door_geo)
                doors.append(door)
            elif opening_type == 2:
                # create a hole
                holes_area += opening_area
                holes.append(opening_vertices)
                holes_2d.append(Polygon2D(opening_vertices_2d))
            else:
                raise ValueError(f'Unsupported opening type: {opening_type}')

        if gem_type == GEM_TYPES.Space or gem_type == GEM_TYPES.UnconditionedSpace:
            # A model face
            geometry = Face3D(boundary)
            face = Face(str(uuid.uuid4()), geometry=geometry)
            if apertures or doors:
                # change the boundary condition if it is set to ground
                if isinstance(face.boundary_condition, Ground):
                    print(
                        'Changing boundary condition from Ground to Outdoors for '
                        f'{face.display_name} in {display_name} [{identifier}].'
                    )
                    face.boundary_condition = Outdoors()
            face.add_apertures(apertures)
            face.add_doors(doors)
            if holes:
                # add an AirBoundary to cover the hole
                if holes_area >= 0.98 * boundary_area:
                    # the face is mostly created from holes
                    # replace the parent face with an face from type AirBoundary
                    if len(holes) == 1:
                        # the entire face is created from holes
                        face.type = AirBoundary()
                        faces.append(face)
                        continue
                    # there are multiple air boundaries. create an AirBoundary for each.
                    for hole in holes_2d:
                        hole = boundary_geometry_polygon2d.snap_to_polygon(
                            hole, MODEL_TOLERANCE * 5)
                        # map the hole back to 3D
                        hole = [boundary_geometry.plane.xy_to_xyz(ver) for ver in hole]
                        hole_geo = Face3D(hole)
                        hole_face = Face(
                            str(uuid.uuid4()), geometry=hole_geo, type=AirBoundary()
                        )
                        faces.append(hole_face)
                    continue

                # only part of the face is created from holes.
                # 1. try to snap them to the face
                # 2. separate holes from side air boundaries
                holes_2d_snapped = [
                    boundary_geometry_polygon2d.snap_to_polygon(hole, MODEL_TOLERANCE * 5)
                    for hole in holes_2d
                ]
                holes_3d_snapped = [
                    Face3D([boundary_geometry.plane.xy_to_xyz(v) for v in hole])
                    for hole in holes_2d_snapped
                ]

                base_faces = boundary_geometry.coplanar_difference(
                    holes_3d_snapped, tolerance=MODEL_TOLERANCE, angle_tolerance=0.01
                )
                if isinstance(base_faces, Face3D):
                    # change the base face to a list if the difference is a single face
                    base_faces = [base_faces]
                base_faces_holes = [[] for _ in base_faces]
                holes_tracker = []
                for hole_count, hole_geo in enumerate(holes_3d_snapped):
                    for count, base_face in enumerate(base_faces):
                        if not base_face.holes:
                            continue
                        for f_hole in base_face.holes:
                            f_hole_geo = Face3D(f_hole)
                            if hole_geo.center.distance_to_point(f_hole_geo.center) <= \
                                    MODEL_TOLERANCE * 5:
                                # this hole is inside the face
                                base_faces_holes[count].append(f_hole_geo)
                                holes_tracker.append(hole_count)
                                break
                    else:
                        if hole_count in holes_tracker:
                            continue
                        # the hole is not inside any of the faces
                        hole_face = Face(
                            str(uuid.uuid4()), geometry=hole_geo, type=AirBoundary()
                        )
                        faces.append(hole_face)

                # create holes
                holes_flattened = [h for holes in base_faces_holes for h in holes]
                for hole_geo in holes_flattened:
                    hole_face = Face(
                        str(uuid.uuid4()), geometry=hole_geo, type=AirBoundary()
                    )
                    # add a key to user data to skip the face when translating
                    # back from HBJSON to GEM
                    hole_face.user_data = {'__ies_import__': True}
                    faces.append(hole_face)

                # add base faces
                for base_face in base_faces:
                    face = Face(str(uuid.uuid4()), geometry=base_face)
                    faces.append(face)
                continue

        elif gem_type in (
                GEM_TYPES.ContextBuilding, GEM_TYPES.Shade, GEM_TYPES.Shade_2):
            is_detached = True if gem_type == GEM_TYPES.ContextBuilding else False
            face = _create_shade(boundary, holes, is_detached)
            _update_name(face, display_name)
        elif gem_type == GEM_TYPES.TranslucentShade:
            # ignore the hole. GEM has a strange way of building translucent shades
            face = _create_shade(
                boundary=boundary, is_detached=False,
                user_data={'__gem_type__': 'translucent_shade'}
            )
            _update_name(face, display_name)
        elif gem_type == GEM_TYPES.Topography:
            # Topography
            face = _create_shade(
                boundary=boundary, holes=holes, is_detached=True,
                user_data={'__gem_type__': 'topography'}
            )
            _update_name(face, display_name)

        faces.append(face)

    if gem_type == GEM_TYPES.Space or gem_type == GEM_TYPES.UnconditionedSpace:
        room = Room(identifier, faces=faces)
        _update_name(room, display_name)
        if gem_type == GEM_TYPES.UnconditionedSpace:
            room.exclude_floor_area = True
        return room
    else:
        return faces


def model_from_gem(
    gem_str: str, model_id: str = 'Unnamed', model_name: str = None
) -> Model:
    """Create a Honeybee Model from the string contents of a VE GEM file.

    Args:
        gem_str: Text string representation of the contents of a GEM file.
        model_id: Text string to be applied as the Model identifier. Typically,
            this is derived from the GEM file name. (Default: Unnamed).
        model_name: Text string to be applied as the Model identifier. If None,
            this will be the same as the model_id. (Default: None).

    Returns:
        A Honeybee Model derived from the GEM file contents.
    """
    # parse the Rooms, Shades and ShadeMeshes
    segments = gem_str.split('\nLAYER')[1:]
    parsed_objects = [_parse_gem_segment(segment) for segment in segments]
    rooms = []
    shades = []
    shade_meshes = []
    for r in parsed_objects:
        if isinstance(r, Room):
            rooms.append(r)
        elif isinstance(r, ShadeMesh):
            shade_meshes.append(r)
        else:
            shades.extend(r)

    # create the Model
    model = Model(
        clean_string(model_id), rooms=rooms, orphaned_shades=shades,
        shade_meshes=shade_meshes, units='Meters', tolerance=0.0001
    )
    if model_name is not None:
        model.display_name = model_name
    return model


def model_from_ies(gem: str) -> Model:
    """Create a Honeybee Model from a VE GEM file.

    Args:
        gem: String for the path to a VE GEM file.

    Returns:
        A Honeybee Model derived from the GEM file contents.
    """
    # load the contents of the GEM file
    gem_file = pathlib.Path(gem)
    file_contents = gem_file.read_text(encoding='utf-8')
    # return the Honeybee Model
    return model_from_gem(file_contents, clean_string(gem_file.stem), gem_file.stem)
