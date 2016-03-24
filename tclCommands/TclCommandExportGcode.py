from ObjectCollection import *
import TclCommand


class TclCommandExportGcode(TclCommand.TclCommandSignaled):
    """
    Tcl shell command to export gcode as  tcl output for "set X [export_gcode ...]"

    Requires name to be available. It might still be in the
    making at the time this function is called, so check for
    promises and send to background if there are promises.


    this  export   may be  catched   by tcl and past as preable  to another  export_gcode or write_gcode
    this can be used to join GCODES

    example:
        set_sys units MM
        new
        open_gerber tests/gerber_files/simple1.gbr -outname margin
        isolate margin -dia 3
        cncjob margin_iso
        cncjob margin_iso
        set EXPORT [export_gcode margin_iso_cnc]
        write_gcode margin_iso_cnc_1 /tmp/file.gcode ${EXPORT}

    """

    # array of all command aliases, to be able use  old names for backward compatibility (add_poly, add_polygon)
    aliases = ['export_gcode']

    # dictionary of types from Tcl command, needs to be ordered
    arg_names = collections.OrderedDict([
        ('name', str),
        ('preamble', str),
        ('postamble', str)
    ])

    # dictionary of types from Tcl command, needs to be ordered , this  is  for options  like -optionname value
    option_types = collections.OrderedDict()

    # array of mandatory options for current Tcl command: required = {'name','outname'}
    required = ['name']

    # structured help for current command, args needs to be ordered
    help = {
        'main': "Export gcode into console output.",
        'args': collections.OrderedDict([
            ('name', 'Name of the source Geometry object.'),
            ('preamble', 'Prepend GCODE.'),
            ('postamble', 'Append GCODE.')
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

        obj = self.app.collection.get_by_name(name)
        if obj is None:
            self.raise_tcl_error("Object not found: %s" % name)

        if not isinstance(obj, CNCjob):
            self.raise_tcl_error('Expected CNCjob, got %s %s.' % (name, type(obj)))

        if self.app.collection.has_promises():
            self.raise_tcl_error('!!!Promises exists, but should not here!!!')

        del args['name']
        return obj.get_gcode(**args)
