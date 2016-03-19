from ObjectCollection import *
import TclCommand


class TclCommandExteriors(TclCommand.TclCommand):
    """
    Tcl shell command to get exteriors of polygons
    """

    # array of all command aliases, to be able use  old names for backward compatibility (add_poly, add_polygon)
    aliases = ['exteriors', 'ext']

    # dictionary of types from Tcl command, needs to be ordered
    arg_names = collections.OrderedDict([
        ('name', str)
    ])

    # dictionary of types from Tcl command, needs to be ordered , this  is  for options  like -optionname value
    option_types = collections.OrderedDict([
        ('outname', str)
    ])

    # array of mandatory options for current Tcl command: required = {'name','outname'}
    required = ['name']

    # structured help for current command, args needs to be ordered
    help = {
        'main': "Get exteriors of polygons.",
        'args':  collections.OrderedDict([
            ('name', 'Name of the source Geometry object.'),
            ('outname', 'Name of the resulting Geometry object.')
        ]),
        'examples': []
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

        if 'outname' in args:
            outname = args['outname']
        else:
            outname = name + "_exteriors"

        obj = self.app.collection.get_by_name(name)
        if obj is None:
            self.raise_tcl_error("Object not found: %s" % name)

        if not isinstance(obj, Geometry):
            self.raise_tcl_error('Expected Geometry, got %s %s.' % (name, type(obj)))

        def geo_init(geo_obj):
            geo_obj.solid_geometry = obj_exteriors

        obj_exteriors = obj.get_exteriors()
        self.app.new_object('geometry', outname, geo_init)
