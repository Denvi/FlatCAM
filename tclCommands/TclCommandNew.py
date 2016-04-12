from ObjectCollection import *
from PyQt4 import QtCore
import TclCommand


class TclCommandNew(TclCommand.TclCommand):
    """
    Tcl shell command to starts a new project. Clears objects from memory
    """

    # array of all command aliases, to be able use  old names for backward compatibility (add_poly, add_polygon)
    aliases = ['new']

    # dictionary of types from Tcl command, needs to be ordered
    arg_names = collections.OrderedDict()

    # dictionary of types from Tcl command, needs to be ordered , this  is  for options  like -optionname value
    option_types = collections.OrderedDict()

    # array of mandatory options for current Tcl command: required = {'name','outname'}
    required = []

    # structured help for current command, args needs to be ordered
    help = {
        'main': "Starts a new project. Clears objects from memory.",
        'args':  collections.OrderedDict(),
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

        self.app.on_file_new()
