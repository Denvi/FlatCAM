from ObjectCollection import *
import TclCommand


class TclCommandDrillcncjob(TclCommand.TclCommandSignaled):
    """
    Tcl shell command to Generates a Drill CNC Job from a Excellon Object.
    """

    # array of all command aliases, to be able use  old names for backward compatibility (add_poly, add_polygon)
    aliases = ['drillcncjob']

    # dictionary of types from Tcl command, needs to be ordered
    arg_names = collections.OrderedDict([
        ('name', str)
    ])

    # dictionary of types from Tcl command, needs to be ordered , this  is  for options  like -optionname value
    option_types = collections.OrderedDict([
        ('tools',str),
        ('drillz',float),
        ('travelz',float),
        ('feedrate',float),
        ('spindlespeed',int),
        ('toolchange',bool),
        ('outname',str)
    ])

    # array of mandatory options for current Tcl command: required = {'name','outname'}
    required = ['name']

    # structured help for current command, args needs to be ordered
    help = {
        'main': "Generates a Drill CNC Job from a Excellon Object.",
        'args': collections.OrderedDict([
            ('name', 'Name of the source object.'),
            ('tools', 'Comma separated indexes of tools (example: 1,3 or 2) or select all if not specified.'),
            ('drillz', 'Drill depth into material (example: -2.0).'),
            ('travelz', 'Travel distance above material (example: 2.0).'),
            ('feedrate', 'Drilling feed rate.'),
            ('spindlespeed', 'Speed of the spindle in rpm (example: 4000).'),
            ('toolchange', 'Enable tool changes (example: True).'),
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

        if not isinstance(obj, FlatCAMExcellon):
            self.raise_tcl_error('Expected FlatCAMExcellon, got %s %s.' % (name, type(obj)))

        def job_init(job_obj, app):
            job_obj.z_cut = args["drillz"]
            job_obj.z_move = args["travelz"]
            job_obj.feedrate = args["feedrate"]
            job_obj.spindlespeed = args["spindlespeed"] if "spindlespeed" in args else None
            toolchange = True if "toolchange" in args and args["toolchange"] == 1 else False
            tools = args["tools"] if "tools" in args else 'all'
            job_obj.generate_from_excellon_by_tool(obj, tools, toolchange)
            job_obj.gcode_parse()
            job_obj.create_geometry()

        self.app.new_object("cncjob", name, job_init)
