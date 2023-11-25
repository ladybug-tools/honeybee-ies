import math
import pathlib
import re
from typing import Iterator, List, Tuple
import uuid

from ladybug_geometry.geometry3d import Face3D, Point3D, Vector3D
from ladybug_geometry.geometry2d import Polygon2D, Point2D, Vector2D
from ladybug_geometry.geometry2d.polygon import closest_point2d_on_line2d
from honeybee.model import Model, Shade, Room, Face, Aperture, Door, AirBoundary
from honeybee.boundarycondition import Outdoors, Ground
from honeybee.typing import clean_string, clean_and_id_ep_string

PI = math.pi
Z_AXIS = Vector3D(0, 0, 1)
ROOF_ANGLE_TOLERANCE = math.radians(10)
MODEL_TOLERANCE = 0.001


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
        x_m, y_m = [float(v) for v in next(content).split()]
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


def _parse_gem_segment(segment: str):
    """Parse a segment of the GEM file.

    Each segment has the information for a room or a shade object.
    """
    info, segments = re.split('\nIES ', segment)
    type_ = int(re.findall(r'^TYPE\n(\d)', info, re.MULTILINE)[0])
    assert type_ in (1, 2, 3, 4), \
        f'Only types 1, 2, 3 and 4 for rooms and shades are valid. Invalid type: {type_}. ' \
        'Contact the developers with your sample file for adding support for a new type.'

    # remove empty lines if any
    content = iter(l for l in segments.split('\n') if l.strip())
    display_name = next(content)
    cleaned_display_name = clean_string(display_name)
    identifier = clean_and_id_ep_string(cleaned_display_name)
    ver_count, face_count = [int(v) for v in next(content).split()]
    vertices = [
        Point3D(*[float(v) for v in next(content).split()])
        for _ in range(ver_count)
    ]

    faces = []
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

        if type_ == 1:
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
                        hole = boundary_geometry_polygon2d.snap_to_polygon(hole, MODEL_TOLERANCE * 5)
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
                # 2. separate holes from side air boundaris
                holes_2d_snapped = [
                    boundary_geometry_polygon2d.snap_to_polygon(hole, MODEL_TOLERANCE * 5)
                    for hole in holes_2d
                ]
                holes_3d_snapped = [
                    Face3D([boundary_geometry.plane.xy_to_xyz(v) for v in hole])
                    for hole in holes_2d_snapped
                ]
                #
                base_faces = boundary_geometry.coplanar_difference(
                    holes_3d_snapped, tolerance=MODEL_TOLERANCE * 5, angle_tolerance=0.01
                )
                base_faces_holes = [[] for _ in base_faces]
                holes_tracker = []
                for hole_count, hole_geo in enumerate(holes_3d_snapped):
                    for count, base_face in enumerate(base_faces):
                        if not base_face.holes:
                            continue
                        for f_hole in base_face.holes:
                            f_hole_geo = Face3D(f_hole)
                            if hole_geo.center.distance_to_point(f_hole_geo.center) <= MODEL_TOLERANCE * 5:
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

        elif 2 <= type_ <= 4:
            # local, context or topography shades
            # 4 is for local shades attached to the building and 2 is for neighbor
            # buildings. 3 if for topography
            is_detached = True if type_ != 4 else False
            geometry = Face3D(boundary, holes=holes)
            face = Shade(str(uuid.uuid4()), geometry=geometry, is_detached=is_detached)
            # use group id to group the shades together.
            try:
                face.user_data['__group_id__'] = cleaned_display_name
            except TypeError:
                face.user_data = {'__group_id__': cleaned_display_name}
            face.display_name = display_name

        faces.append(face)

    if type_ == 1:
        room = Room(identifier, faces=faces)
        room.display_name = display_name
        return room
    else:
        return faces


def model_from_ies(gem: str) -> Model:
    """Create a Honeybee Model from a VE GEM file."""
    gem_file = pathlib.Path(gem)
    # split the gem file into separate segments
    segments = gem_file.read_text().split('\nLAYER')[1:]
    parsed_objects = [_parse_gem_segment(segment) for segment in segments]
    rooms = []
    shades = []
    for r in parsed_objects:
        if isinstance(r, Room):
            rooms.append(r)
        else:
            shades.extend(r)

    model = Model(
        clean_string(gem_file.stem), rooms=rooms, units='Meters', orphaned_shades=shades,
        tolerance=0.0001
    )
    model.display_name = gem_file.stem
    return model
