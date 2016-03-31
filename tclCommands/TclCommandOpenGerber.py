from ObjectCollection import *
import TclCommand


class TclCommandOpenGerber(TclCommand.TclCommandSignaled):
    """
    Tcl shell command to opens a Gerber file
    """

    # array of all command aliases, to be able use  old names for backward compatibility (add_poly, add_polygon)
    aliases = ['open_gerber']

    # dictionary of types from Tcl command, needs to be ordered
    arg_names = collections.OrderedDict([
        ('filename', str)
    ])

    # dictionary of types from Tcl command, needs to be ordered , this  is  for options  like -optionname value
    option_types = collections.OrderedDict([
        ('follow', str),
        ('outname', str)
    ])

    # array of mandatory options for current Tcl command: required = {'name','outname'}
    required = ['filename']

    # structured help for current command, args needs to be ordered
    help = {
        'main': "Opens a Gerber file.",
        'args':  collections.OrderedDict([
            ('filename', 'Path to file to open.'),
            ('follow', 'N If 1, does not create polygons, just follows the gerber path.'),
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
        def obj_init(gerber_obj, app_obj):

            if not isinstance(gerber_obj, Geometry):
                self.raise_tcl_error('Expected FlatCAMGerber, got %s %s.' % (outname, type(gerber_obj)))

            # Opening the file happens here
            self.app.progress.emit(30)
            try:
                gerber_obj.parse_file(filename, follow=follow)

            except IOError:
                app_obj.inform.emit("[error] Failed to open file: %s " % filename)
                app_obj.progress.emit(0)
                self.raise_tcl_error('Failed to open file: %s' % filename)

            except ParseError, e:
                app_obj.inform.emit("[error] Failed to parse file: %s, %s " % (filename, str(e)))
                app_obj.progress.emit(0)
                self.log.error(str(e))
                raise

            # Further parsing
            app_obj.progress.emit(70)

        filename = args['filename']

        if 'outname' in args:
            outname = args['outname']
        else:
            outname = filename.split('/')[-1].split('\\')[-1]

        follow = None
        if 'follow' in args:
            follow = args['follow']

        with self.app.proc_container.new("Opening Gerber"):

            # Object creation
            self.app.new_object("gerber", outname, obj_init)

            # Register recent file
            self.app.file_opened.emit("gerber", filename)

            self.app.progress.emit(100)

            # GUI feedback
            self.app.inform.emit("Opened: " + filename)
