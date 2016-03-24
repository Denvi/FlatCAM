from ObjectCollection import *
import TclCommand


class TclCommandAddPolyline(TclCommand.TclCommandSignaled):
    """
    Tcl shell command to create a polyline in the given Geometry object
    """

    # array of all command aliases, to be able use  old names for backward compatibility (add_poly, add_polygon)
    aliases = ['add_polyline']

    # dictionary of types from Tcl command, needs to be ordered
    arg_names = collections.OrderedDict([
        ('name', str)
    ])

    # dictionary of types from Tcl command, needs to be ordered , this  is  for options  like -optionname value
    option_types = collections.OrderedDict()

    # array of mandatory options for current Tcl command: required = {'name','outname'}
    required = ['name']

    # structured help for current command, args needs to be ordered
    help = {
        'main': "Creates a polyline in the given Geometry object.",
        'args': collections.OrderedDict([
            ('name', 'Name of the Geometry object to which to append the polyline.'),
            ('xi, yi', 'Coordinates of points in the polyline.')
        ]),
        'examples': [
            'add_polyline <name> <x0> <y0> <x1> <y1> <x2> <y2> [x3 y3 [...]]'
        ]
    }

    def execute(self, args, unnamed_args):
        """
        execute current TCL shell command

        :param args: array of known named arguments and options
        :param unnamed_args: array of other values which were passed into command
            without -somename and  we do not have them in known arg_names
        :return: None or exception
        """

        name = args['name']

        obj = self.app.collection.get_by_name(name)
        if obj is None:
            self.raise_tcl_error("Object not found: %s" % name)

        if not isinstance(obj, Geometry):
            self.raise_tcl_error('Expected Geometry, got %s %s.' % (name, type(obj)))

        if len(unnamed_args) % 2 != 0:
            self.raise_tcl_error("Incomplete coordinates.")

        points = [[float(unnamed_args[2*i]), float(unnamed_args[2*i+1])] for i in range(len(unnamed_args)/2)]

        obj.add_polyline(points)
        obj.plot()
