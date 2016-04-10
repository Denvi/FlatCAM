from ObjectCollection import *
import TclCommand


class TclCommandCncjob(TclCommand.TclCommandSignaled):
    """
    Tcl shell command to Generates a CNC Job from a Geometry Object.

    example:
        set_sys units MM
        new
        open_gerber tests/gerber_files/simple1.gbr -outname margin
        isolate margin -dia 3
        cncjob margin_iso
    """

    # array of all command aliases, to be able use  old names for backward compatibility (add_poly, add_polygon)
    aliases = ['cncjob']

    # dictionary of types from Tcl command, needs to be ordered
    arg_names = collections.OrderedDict([
        ('name', str)
    ])

    # dictionary of types from Tcl command, needs to be ordered , this  is  for options  like -optionname value
    option_types = collections.OrderedDict([
        ('z_cut',float),
        ('z_move',float),
        ('feedrate',float),
        ('tooldia',float),
        ('spindlespeed',int),
        ('multidepth',bool),
        ('depthperpass',float),
        ('outname',str)
    ])

    # array of mandatory options for current Tcl command: required = {'name','outname'}
    required = ['name']

    # structured help for current command, args needs to be ordered
    help = {
        'main': "Generates a CNC Job from a Geometry Object.",
        'args': collections.OrderedDict([
            ('name', 'Name of the source object.'),
            ('z_cut', 'Z-axis cutting position.'),
            ('z_move', 'Z-axis moving position.'),
            ('feedrate', 'Moving speed when cutting.'),
            ('tooldia', 'Tool diameter to show on screen.'),
            ('spindlespeed', 'Speed of the spindle in rpm (example: 4000).'),
            ('multidepth', 'Use or not multidepth cnccut.'),
            ('depthperpass', 'Height of one layer for multidepth.'),
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

        if 'outname' not in args:
            args['outname'] = name + "_cnc"

        obj = self.app.collection.get_by_name(name)
        if obj is None:
            self.raise_tcl_error("Object not found: %s" % name)

        if not isinstance(obj, FlatCAMGeometry):
            self.raise_tcl_error('Expected FlatCAMGeometry, got %s %s.' % (name, type(obj)))

        del args['name']
        obj.generatecncjob(use_thread = False, **args)