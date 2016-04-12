import pkgutil
import sys

# allowed command modules (please append them alphabetically ordered)
import tclCommands.TclCommandAddPolygon
import tclCommands.TclCommandAddPolyline
import tclCommands.TclCommandCncjob
import tclCommands.TclCommandDrillcncjob
import tclCommands.TclCommandExportGcode
import tclCommands.TclCommandExteriors
import tclCommands.TclCommandInteriors
import tclCommands.TclCommandIsolate
import tclCommands.TclCommandNew
import tclCommands.TclCommandOpenGerber


__all__ = []

for loader, name, is_pkg in pkgutil.walk_packages(__path__):
    module = loader.find_module(name).load_module(name)
    __all__.append(name)

def register_all_commands(app, commands):
    """
    Static method which register all known commands.

    Command should  be for now in directory tclCommands and module should start with TCLCommand
    Class  have to follow same  name as module.

    we need import all  modules  in top section:
    import tclCommands.TclCommandExteriors
    at this stage we can include only wanted  commands  with this, auto loading may be implemented in future
    I have no enough knowledge about python's anatomy. Would be nice to include all classes which are descendant etc.

    :param app: FlatCAMApp
    :param commands: array of commands  which should be modified
    :return: None
    """

    tcl_modules = {k: v for k, v in sys.modules.items() if k.startswith('tclCommands.TclCommand')}

    for key, mod in tcl_modules.items():
        if key != 'tclCommands.TclCommand':
            class_name = key.split('.')[1]
            class_type = getattr(mod, class_name)
            command_instance = class_type(app)

            for alias in command_instance.aliases:
                commands[alias] = {
                    'fcn': command_instance.execute_wrapper,
                    'help': command_instance.get_decorated_help()
                }
