# coding=utf-8
"""Model IES Properties."""
from honeybee.units import parse_distance_string


class ModelIESProperties(object):
    """IES Properties for Honeybee Model.

    Args:
        host: A honeybee_core Model object that hosts these properties.

    Properties:
        * host
    """

    def __init__(self, host):
        """Initialize ModelIESProperties."""
        self._host = host

    @property
    def host(self):
        """Get the Model object hosting these properties."""
        return self._host

    def check_for_extension(self, raise_exception=True, detailed=False):
        """Check that the Model is valid for IES simulation.

        This process includes all relevant honeybee-core checks as well as checks
        that apply only for IES.

        Args:
            raise_exception: Boolean to note whether a ValueError should be raised
                if any errors are found. If False, this method will simply
                return a text string with all errors that were found. (Default: True).
            detailed: Boolean for whether the returned object is a detailed list of
                dicts with error info or a string with a message. (Default: False).

        Returns:
            A text string with all errors that were found or a list if detailed is True.
            This string (or list) will be empty if no errors were found.
        """
        # set up defaults to ensure the method runs correctly
        detailed = False if raise_exception else detailed
        msgs = []
        tol = self.host.tolerance
        ang_tol = self.host.angle_tolerance
        e_tol = parse_distance_string('1mm', self.host.units)

        # perform checks for duplicate identifiers, which might mess with other checks
        msgs.append(self.host.check_all_duplicate_identifiers(False, detailed))

        # perform several checks for the Honeybee schema geometry rules
        msgs.append(self.host.check_planar(tol, False, detailed))
        msgs.append(self.host.check_self_intersecting(tol, False, detailed))
        msgs.append(self.host.check_degenerate_rooms(e_tol, False, detailed))

        # perform geometry checks related to parent-child relationships
        msgs.append(self.host.check_sub_faces_valid(tol, ang_tol, False, detailed))
        msgs.append(self.host.check_sub_faces_overlapping(tol, False, detailed))
        msgs.append(self.host.check_rooms_solid(tol, ang_tol, False, detailed))

        # perform checks related to adjacency relationships
        msgs.append(self.host.check_room_volume_collisions(tol, False, detailed))
        msgs.append(self.host.check_all_air_boundaries_adjacent(False, detailed))

        # output a final report of errors or raise an exception
        full_msgs = [msg for msg in msgs if msg]
        if detailed:
            return [m for msg in full_msgs for m in msg]
        full_msg = '\n'.join(full_msgs)
        if raise_exception and len(full_msgs) != 0:
            raise ValueError(full_msg)
        return full_msg

    def to_dict(self):
        """Return Model IES properties as a dictionary."""
        return {'ies': {'type': 'ModelIESProperties'}}

    def apply_properties_from_dict(self, data):
        """Apply the energy properties of a dictionary to the host Model of this object.

        Args:
            data: A dictionary representation of an entire honeybee-core Model.
                Note that this dictionary must have ModelIESProperties in order
                for this method to successfully apply the IES properties.
        """
        assert 'ies' in data['properties'], \
            'Dictionary possesses no ModelIESProperties.'

    def ToString(self):
        return self.__repr__()

    def __repr__(self):
        return 'Model IES Properties: [host: {}]'.format(self.host.display_name)
