import math
import pathlib
import re
from typing import Iterator, List, Tuple
import uuid

from ladybug_geometry.geometry3d import Face3D, Point3D, Vector3D
from honeybee.model import Model, Shade, Room, Face, Aperture, Door, AirBoundary
from honeybee.boundarycondition import Outdoors, Ground
from honeybee.typing import clean_string, clean_and_id_ep_string

Z_AXIS = Vector3D(0, 0, 1)
ROOF_ANGLE_TOLERANCE = math.radians(10)


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
        vertices = geometry.upper_right_counter_clockwise_vertices
        x = geometry.plane.x.reverse()
        y = geometry.plane.y.reverse()
    elif geometry.plane.n.angle(Z_AXIS) < ROOF_ANGLE_TOLERANCE:
        # almost horizontal faces
        vertices = geometry.lower_left_counter_clockwise_vertices
        origin = geometry.lower_left_corner
        x = geometry.plane.x.reverse()
        y = geometry.plane.y.reverse()
    else:
        vertices = geometry.lower_left_counter_clockwise_vertices
        origin = vertices[0]
        # not sure if this is the best approach but using the plane x and y from the
        # base geometry could result in a flipped plane is some cases.
        x = (vertices[1] - origin).normalize()
        y = (vertices[-1] - origin).normalize()

    # This is how the next line looks
    # 5 2
    ver_count, opening_type = [int(v) for v in next(content).split()]

    # calculate the vertices from X, Y values
    # 0.000000     0.906100
    # 0.000000     0.000000
    # 10.373100     0.000000
    boundary_2d = geometry.boundary_polygon2d

    def _move_vertex(xx_m, yy_m):
        vertex = origin.move(x * xx_m)  # move in x direction
        vertex = vertex.move(y * yy_m) # move in y direction
        vertex_2d = geometry._plane.xyz_to_xy(vertex)
        return vertex, vertex_2d

    opening_vertices = []
    push_dist = 0.02

    for _ in range(ver_count):
        x_m, y_m = [float(v) for v in next(content).split()]
        # change 0 value to a cm - this will move the point inwards
        x_m = x_m or push_dist
        y_m = y_m or push_dist
        # try finding the correct vertices that doesn't touch the edge
        # this is not a problem in IES but it is in the Rhino plugin and EP
        moves = [
            (x_m, y_m),
            (x_m + push_dist, y_m), (x_m, y_m + push_dist),
            (x_m - push_dist, y_m), (x_m, y_m - push_dist),
            (x_m + push_dist, y_m + push_dist), (x_m - push_dist, y_m - push_dist),
            (x_m - push_dist, y_m + push_dist), (x_m + push_dist, y_m - push_dist),
        ]
        for (xx, yy) in moves:
            vertex, vertex_2d = _move_vertex(xx, yy)
            dist = min(seg.distance_to_point(vertex_2d) for seg in boundary_2d.segments)
            if boundary_2d.is_point_inside_check(vertex_2d) and dist > push_dist * 0.5:
                opening_vertices.append(vertex)
                break
        else:
            # using the initial option - technically we should never get here
            vertex, vertex_2d = _move_vertex(*moves[0])
            opening_vertices.append(vertex)

    return opening_vertices, opening_type


def _parse_gem_segment(segment: str):
    """Parse a segment of the GEM file.

    Each segment has the information for a room or a shade object.
    """
    info, segments = re.split('\nIES ', segment)
    type_ = int(re.findall(r'^TYPE\n(\d)', info, re.MULTILINE)[0])
    assert type_ in (1, 2, 4), \
        f'Only types 1, 2 and 4 for rooms and shades are valid. Invalid type: {type_}.' \
        'Contact the developers for adding support for a new type'

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
        boundary = [vertices[int(i) - 1] for i in next(content).split()[1:]]
        boundary_geometry = Face3D(boundary, enforce_right_hand=False)
        opening_count = int(next(content))
        for _ in range(opening_count):
            opening_vertices, opening_type = _opening_from_ies(boundary_geometry, content)
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
                holes.append(opening_vertices)
            else:
                # create 
                raise ValueError(f'Unsupported opening type: {opening_type}')

        if type_ == 1:
            geometry = Face3D(boundary, holes=holes)
            face = Face(str(uuid.uuid4()), geometry=geometry)
            if apertures or doors:
                # change the boundary condition if it is set to ground
                if isinstance(face.boundary_condition, Ground):
                    print(
                        'Changing boundary condition from Ground to Outdoors for ' \
                        f'{face.display_name} in {display_name} [{identifier}].'
                    )
                    face.boundary_condition = Outdoors()
            face.add_apertures(apertures)
            face.add_doors(doors)
            if holes:
                # add an AirBoundary to cover the hole
                for hole in holes:
                    hole_geo = Face3D(hole)
                    hole_face = Face(
                        str(uuid.uuid4()), geometry=hole_geo, type=AirBoundary()
                    )
                    hole_face.user_data = {'__ies_import__': True}
                    faces.append(hole_face)
        elif type_ == 4 or type_ == 2:
            # local and context shades
            # 4 is for local shades attached to the building and 2 is for neighbor
            # buildings
            is_detached = True if type_ == 2 else False
            geometry = Face3D(boundary)
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
        tolerance=0.01
    )
    model.display_name = gem_file.stem
    return model
