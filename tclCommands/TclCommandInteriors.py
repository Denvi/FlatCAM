from ObjectCollection import *
import TclCommand

class TclCommandInteriors(TclCommand.TclCommand):
    """
    Tcl shell command to get interiors of polygons
    """

    # array of all command aliases, to be able use  old names for backward compatibility (add_poly, add_polygon)
    aliases = ['interiors']

    # dictionary of types from Tcl command: args = {'name': str}, this is  for  value without optionname
    arg_names = {'name': str}

    # dictionary of types from Tcl command: types = {'outname': str} , this  is  for options  like -optionname value
    option_types = {'outname': str}

    # array of mandatory options for current Tcl command: required = {'name','outname'}
    required = ['name']

    # structured help for current command
    help = {
        'main': "Get interiors of polygons.",
        'args': {
            'name': 'Name of the source Geometry object.',
            'outname': 'Name of the resulting Geometry object.'
        },
        'examples':[]
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
            outname = name + "_interiors"

        try:
            obj = self.app.collection.get_by_name(name)
        except:
            self.app.raiseTclError("Could not retrieve object: %s" % name)

        if obj is None:
            self.app.raiseTclError("Object not found: %s" % name)

        if not isinstance(obj, Geometry):
            self.app.raiseTclError('Expected Geometry, got %s %s.' % (name, type(obj)))

        def geo_init(geo_obj, app_obj):
            geo_obj.solid_geometry = obj_exteriors

        obj_exteriors = obj.get_interiors()
        self.app.new_object('geometry', outname, geo_init)