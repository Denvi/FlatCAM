from ObjectCollection import *
import TclCommand


class TclCommandIsolate(TclCommand.TclCommandSignaled):
    """
    Tcl shell command to Creates isolation routing geometry for the given Gerber.

    example:
        set_sys units MM
        new
        open_gerber tests/gerber_files/simple1.gbr -outname margin
        isolate margin -dia 3
        cncjob margin_iso
    """

    # array of all command aliases, to be able use  old names for backward compatibility (add_poly, add_polygon)
    aliases = ['isolate']

    # dictionary of types from Tcl command, needs to be ordered
    arg_names = collections.OrderedDict([
        ('name', str)
    ])

    # dictionary of types from Tcl command, needs to be ordered , this  is  for options  like -optionname value
    option_types = collections.OrderedDict([
        ('dia',float),
        ('passes',int),
        ('overlap',float),
        ('combine',int),
        ('outname',str)
    ])

    # array of mandatory options for current Tcl command: required = {'name','outname'}
    required = ['name']

    # structured help for current command, args needs to be ordered
    help = {
        'main': "Creates isolation routing geometry for the given Gerber.",
        'args': collections.OrderedDict([
            ('name', 'Name of the source object.'),
            ('dia', 'Tool diameter.'),
            ('passes', 'Passes of tool width.'),
            ('overlap', 'Fraction of tool diameter to overlap passes.'),
            ('combine', 'Combine all passes into one geometry.'),
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
            args['outname'] = name + "_iso"

        if 'timeout' in args:
            timeout = args['timeout']
        else:
            timeout = 10000

        obj = self.app.collection.get_by_name(name)
        if obj is None:
            self.raise_tcl_error("Object not found: %s" % name)

        if not isinstance(obj, FlatCAMGerber):
            self.raise_tcl_error('Expected FlatCAMGerber, got %s %s.' % (name, type(obj)))

        del args['name']
        obj.isolate(**args)
