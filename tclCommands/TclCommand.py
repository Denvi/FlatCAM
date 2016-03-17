import sys, inspect, pkgutil
import re
import FlatCAMApp
import collections

class TclCommand(object):

    app=None

    # array of all command aliases, to be able use  old names for backward compatibility (add_poly, add_polygon)
    aliases = []

    # dictionary of types from Tcl command, needs to be ordered
    arg_names = collections.OrderedDict([
        ('name', str)
    ])

    # dictionary of types from Tcl command, needs to be ordered , this  is  for options  like -optionname value
    option_types = collections.OrderedDict([])

    # array of mandatory options for current Tcl command: required = {'name','outname'}
    required = ['name']

    # structured help for current command, args needs to be ordered
    help = {
        'main': "undefined help.",
        'args': collections.OrderedDict([
            ('argumentname', 'undefined help.'),
            ('optionname', 'undefined help.')
        ]),
        'examples' : []
    }

    def __init__(self, app):
        self.app=app

    def get_decorated_help(self):
        """
        Decorate help for TCL console output.

        :return: decorated help from structue
        """

        def get_decorated_command(alias):
            command_string = []
            for key, value in self.help['args'].items():
                command_string.append(get_decorated_argument(key, value, True))
            return "> " + alias + " " + " ".join(command_string)

        def get_decorated_argument(key, value, in_command=False):
            option_symbol = ''
            if key in self.arg_names:
                type=self.arg_names[key]
                type_name=str(type.__name__)
                in_command_name = "<" + type_name + ">"
            elif key in self.option_types:
                option_symbol = '-'
                type=self.option_types[key]
                type_name=str(type.__name__)
                in_command_name = option_symbol + key + " <" + type_name + ">"
            else:
                option_symbol = ''
                type_name='?'
                in_command_name = option_symbol + key + " <" + type_name + ">"

            if in_command:
                if key in self.required:
                    return in_command_name
                else:
                    return '[' + in_command_name + "]"
            else:
                if key in self.required:
                    return "\t" + option_symbol + key + " <" + type_name + ">: " + value
                else:
                    return "\t[" + option_symbol + key + " <" + type_name + ">: " + value+"]"

        def get_decorated_example(example):
            return "> "+example

        help_string=[self.help['main']]
        for alias in self.aliases:
            help_string.append(get_decorated_command(alias))

        for key, value in self.help['args'].items():
            help_string.append(get_decorated_argument(key, value))

        for example in self.help['examples']:
            help_string.append(get_decorated_example(example))

        return "\n".join(help_string)

    def parse_arguments(self, args):
            """
            Pre-processes arguments to detect '-keyword value' pairs into dictionary
            and standalone parameters into list.

            This is copy from FlatCAMApp.setup_shell().h() just for accesibility,  original should  be removed  after all commands will be converted
            """

            options = {}
            arguments = []
            n = len(args)
            name = None
            for i in range(n):
                match = re.search(r'^-([a-zA-Z].*)', args[i])
                if match:
                    assert name is None
                    name = match.group(1)
                    continue

                if name is None:
                    arguments.append(args[i])
                else:
                    options[name] = args[i]
                    name = None

            return arguments, options

    def check_args(self, args):
        """
        Check arguments and  options for right types

        :param args: arguments from tcl to check
        :return:
        """

        arguments, options = self.parse_arguments(args)

        named_args={}
        unnamed_args=[]

        # check arguments
        idx=0
        arg_names_items=self.arg_names.items()
        for argument in arguments:
            if len(self.arg_names) > idx:
                key, type = arg_names_items[idx]
                try:
                    named_args[key] = type(argument)
                except Exception, e:
                    self.app.raiseTclError("Cannot cast named argument '%s' to type %s." % (key, type))
            else:
                unnamed_args.append(argument)
            idx += 1

        # check otions
        for key in options:
            if key not in self.option_types:
                self.app.raiseTclError('Unknown parameter: %s' % key)
            try:
                named_args[key] = self.option_types[key](options[key])
            except Exception, e:
                self.app.raiseTclError("Cannot cast argument '-%s' to type %s." % (key, self.option_types[key]))

        # check required arguments
        for key in self.required:
            if key not in named_args:
                self.app.raiseTclError("Missing required argument '%s'." % (key))

        return named_args, unnamed_args

    def execute_wrapper(self, *args):
        """
        Command which is called by tcl console when current commands aliases are hit.
        Main catch(except) is implemented here.
        This method should be reimplemented only when initial checking sequence differs

        :param args: arguments passed from tcl command console
        :return: None, output text or exception
        """
        try:
            args, unnamed_args = self.check_args(args)
            return self.execute(args, unnamed_args)
        except Exception as unknown:
            self.app.raiseTclUnknownError(unknown)

    def execute(self, args, unnamed_args):
        """
        Direct execute of command, this method should be implemented in each descendant.
        No main catch should be implemented here.

        :param args: array of known named arguments and options
        :param unnamed_args: array of other values which were passed into command
            without -somename and  we do not have them in known arg_names
        :return: None, output text or exception
        """

        raise NotImplementedError("Please Implement this method")
