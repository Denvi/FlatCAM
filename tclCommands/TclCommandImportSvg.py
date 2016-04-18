from ObjectCollection import *
import TclCommand


class TclCommandImportSvg(TclCommand.TclCommandSignaled):
    """
    Tcl shell command to import an SVG file as a Geometry Object.
    """

    # array of all command aliases, to be able use  old names for backward compatibility (add_poly, add_polygon)
    aliases = ['import_svg']

    # dictionary of types from Tcl command, needs to be ordered
    arg_names = collections.OrderedDict([
        ('filename', str)
    ])

    # dictionary of types from Tcl command, needs to be ordered , this  is  for options  like -optionname value
    option_types = collections.OrderedDict([
        ('type', str),
        ('outname', str)
    ])

    # array of mandatory options for current Tcl command: required = {'name','outname'}
    required = ['filename']

    # structured help for current command, args needs to be ordered
    help = {
        'main': "Import an SVG file as a Geometry Object..",
        'args':  collections.OrderedDict([
            ('filename', 'Path to file to open.'),
            ('type', 'Import as gerber or geometry(default).'),
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

        # How the object should be initialized
        def obj_init(geo_obj, app_obj):

            if not isinstance(geo_obj, Geometry):
                self.raise_tcl_error('Expected Geometry or Gerber, got %s %s.' % (outname, type(geo_obj)))

            geo_obj.import_svg(filename)

        filename = args['filename']

        if 'outname' in args:
            outname = args['outname']
        else:
            outname = filename.split('/')[-1].split('\\')[-1]

        if 'type' in args:
            obj_type = args['type']
        else:
            obj_type = 'geometry'

        if obj_type != "geometry" and  obj_type != "gerber":
            self.raise_tcl_error("Option type can be 'geopmetry' or 'gerber' only, got '%s'." % obj_type)

        with self.app.proc_container.new("Import SVG"):

            # Object creation
            self.app.new_object(obj_type, outname, obj_init)

            # Register recent file
            self.app.file_opened.emit("svg", filename)

            # GUI feedback
            self.app.inform.emit("Opened: " + filename)

