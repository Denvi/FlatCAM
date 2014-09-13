import traceback
import sys
import urllib
from copy import copy
import random
import logging
import simplejson as json
import re
import webbrowser
import os
import Tkinter

from PyQt4 import QtCore

########################################
##      Imports part of FlatCAM       ##
########################################
from FlatCAMWorker import Worker
from ObjectCollection import *
from FlatCAMObj import *
from PlotCanvas import *
from FlatCAMGUI import *
from FlatCAMCommon import LoudDict
from FlatCAMTool import *

from FlatCAMShell import FCShell


########################################
##                App                 ##
########################################
class App(QtCore.QObject):
    """
    The main application class. The constructor starts the GUI.
    """

    ## Logging ##
    log = logging.getLogger('base')
    log.setLevel(logging.DEBUG)
    #log.setLevel(logging.WARNING)
    formatter = logging.Formatter('[%(levelname)s][%(threadName)s] %(message)s')
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    log.addHandler(handler)

    ## URL for update checks
    version_url = "http://caram.cl/flatcam/VERSION"

    ## App URL
    app_url = "http://caram.cl/software/flatcam"

    ## Signals
    inform = QtCore.pyqtSignal(str)  # Message
    worker_task = QtCore.pyqtSignal(dict)  # Worker task
    file_opened = QtCore.pyqtSignal(str, str)  # File type and filename
    progress = QtCore.pyqtSignal(int)  # Percentage of progress
    plots_updated = QtCore.pyqtSignal()
    object_created = QtCore.pyqtSignal(object)
    message = QtCore.pyqtSignal(str, str, str)

    def __init__(self):
        """
        Starts the application. Takes no parameters.

        :return: app
        :rtype: App
        """

        App.log.info("FlatCAM Starting...")

        QtCore.QObject.__init__(self)

        self.ui = FlatCAMGUI()

        #### Plot Area ####
        # self.plotcanvas = PlotCanvas(self.ui.splitter)
        self.plotcanvas = PlotCanvas(self.ui.right_layout)
        self.plotcanvas.mpl_connect('button_press_event', self.on_click_over_plot)
        self.plotcanvas.mpl_connect('motion_notify_event', self.on_mouse_move_over_plot)
        self.plotcanvas.mpl_connect('key_press_event', self.on_key_over_plot)

        self.ui.splitter.setStretchFactor(1, 2)

        ##############
        #### Data ####
        ##############
        self.recent = []

        self.clipboard = QtGui.QApplication.clipboard()

        self.project_filename = None

        self.last_folder = None

        self.toggle_units_ignore = False

        self.defaults_form = GlobalOptionsUI()
        self.defaults_form_fields = {
            "units": self.defaults_form.units_radio,
            "gerber_plot": self.defaults_form.gerber_group.plot_cb,
            "gerber_solid": self.defaults_form.gerber_group.solid_cb,
            "gerber_multicolored": self.defaults_form.gerber_group.multicolored_cb,
            "gerber_isotooldia": self.defaults_form.gerber_group.iso_tool_dia_entry,
            "gerber_isopasses": self.defaults_form.gerber_group.iso_width_entry,
            "gerber_isooverlap": self.defaults_form.gerber_group.iso_overlap_entry,
            "gerber_cutouttooldia": self.defaults_form.gerber_group.cutout_tooldia_entry,
            "gerber_cutoutmargin": self.defaults_form.gerber_group.cutout_margin_entry,
            "gerber_cutoutgapsize": self.defaults_form.gerber_group.cutout_gap_entry,
            "gerber_gaps": self.defaults_form.gerber_group.gaps_radio,
            "gerber_noncoppermargin": self.defaults_form.gerber_group.noncopper_margin_entry,
            "gerber_noncopperrounded": self.defaults_form.gerber_group.noncopper_rounded_cb,
            "gerber_bboxmargin": self.defaults_form.gerber_group.bbmargin_entry,
            "gerber_bboxrounded": self.defaults_form.gerber_group.bbrounded_cb,
            "excellon_plot": self.defaults_form.excellon_group.plot_cb,
            "excellon_solid": self.defaults_form.excellon_group.solid_cb,
            "excellon_drillz": self.defaults_form.excellon_group.cutz_entry,
            "excellon_travelz": self.defaults_form.excellon_group.travelz_entry,
            "excellon_feedrate": self.defaults_form.excellon_group.feedrate_entry,
            "geometry_plot": self.defaults_form.geometry_group.plot_cb,
            "geometry_cutz": self.defaults_form.geometry_group.cutz_entry,
            "geometry_travelz": self.defaults_form.geometry_group.travelz_entry,
            "geometry_feedrate": self.defaults_form.geometry_group.cncfeedrate_entry,
            "geometry_cnctooldia": self.defaults_form.geometry_group.cnctooldia_entry,
            "geometry_painttooldia": self.defaults_form.geometry_group.painttooldia_entry,
            "geometry_paintoverlap": self.defaults_form.geometry_group.paintoverlap_entry,
            "geometry_paintmargin": self.defaults_form.geometry_group.paintmargin_entry,
            "cncjob_plot": self.defaults_form.cncjob_group.plot_cb,
            "cncjob_tooldia": self.defaults_form.cncjob_group.tooldia_entry,
            "cncjob_append": self.defaults_form.cncjob_group.append_text
        }

        self.defaults = LoudDict()
        self.defaults.set_change_callback(lambda key: self.defaults_write_form())  # When the dictionary changes.
        self.defaults.update({
            "units": "IN",
            "gerber_plot": True,
            "gerber_solid": True,
            "gerber_multicolored": False,
            "gerber_isotooldia": 0.016,
            "gerber_isopasses": 1,
            "gerber_isooverlap": 0.15,
            "gerber_cutouttooldia": 0.07,
            "gerber_cutoutmargin": 0.1,
            "gerber_cutoutgapsize": 0.15,
            "gerber_gaps": "4",
            "gerber_noncoppermargin": 0.0,
            "gerber_noncopperrounded": False,
            "gerber_bboxmargin": 0.0,
            "gerber_bboxrounded": False,
            "excellon_plot": True,
            "excellon_solid": False,
            "excellon_drillz": -0.1,
            "excellon_travelz": 0.1,
            "excellon_feedrate": 3.0,
            "geometry_plot": True,
            "geometry_cutz": -0.002,
            "geometry_travelz": 0.1,
            "geometry_feedrate": 3.0,
            "geometry_cnctooldia": 0.016,
            "geometry_painttooldia": 0.07,
            "geometry_paintoverlap": 0.15,
            "geometry_paintmargin": 0.0,
            "cncjob_plot": True,
            "cncjob_tooldia": 0.016,
            "cncjob_append": ""
        })
        self.load_defaults()

        self.options_form = GlobalOptionsUI()
        self.options_form_fields = {
            "units": self.options_form.units_radio,
            "gerber_plot": self.options_form.gerber_group.plot_cb,
            "gerber_solid": self.options_form.gerber_group.solid_cb,
            "gerber_multicolored": self.options_form.gerber_group.multicolored_cb,
            "gerber_isotooldia": self.options_form.gerber_group.iso_tool_dia_entry,
            "gerber_isopasses": self.options_form.gerber_group.iso_width_entry,
            "gerber_isooverlap": self.options_form.gerber_group.iso_overlap_entry,
            "gerber_cutouttooldia": self.options_form.gerber_group.cutout_tooldia_entry,
            "gerber_cutoutmargin": self.options_form.gerber_group.cutout_margin_entry,
            "gerber_cutoutgapsize": self.options_form.gerber_group.cutout_gap_entry,
            "gerber_gaps": self.options_form.gerber_group.gaps_radio,
            "gerber_noncoppermargin": self.options_form.gerber_group.noncopper_margin_entry,
            "gerber_noncopperrounded": self.options_form.gerber_group.noncopper_rounded_cb,
            "gerber_bboxmargin": self.options_form.gerber_group.bbmargin_entry,
            "gerber_bboxrounded": self.options_form.gerber_group.bbrounded_cb,
            "excellon_plot": self.options_form.excellon_group.plot_cb,
            "excellon_solid": self.options_form.excellon_group.solid_cb,
            "excellon_drillz": self.options_form.excellon_group.cutz_entry,
            "excellon_travelz": self.options_form.excellon_group.travelz_entry,
            "excellon_feedrate": self.options_form.excellon_group.feedrate_entry,
            "geometry_plot": self.options_form.geometry_group.plot_cb,
            "geometry_cutz": self.options_form.geometry_group.cutz_entry,
            "geometry_travelz": self.options_form.geometry_group.travelz_entry,
            "geometry_feedrate": self.options_form.geometry_group.cncfeedrate_entry,
            "geometry_cnctooldia": self.options_form.geometry_group.cnctooldia_entry,
            "geometry_painttooldia": self.options_form.geometry_group.painttooldia_entry,
            "geometry_paintoverlap": self.options_form.geometry_group.paintoverlap_entry,
            "geometry_paintmargin": self.options_form.geometry_group.paintmargin_entry,
            "cncjob_plot": self.options_form.cncjob_group.plot_cb,
            "cncjob_tooldia": self.options_form.cncjob_group.tooldia_entry,
            "cncjob_append": self.options_form.cncjob_group.append_text
        }

        self.options = LoudDict()
        self.options.set_change_callback(lambda key: self.options_write_form())
        self.options.update({
            "units": "IN",
            "gerber_plot": True,
            "gerber_solid": True,
            "gerber_multicolored": False,
            "gerber_isotooldia": 0.016,
            "gerber_isopasses": 1,
            "gerber_isooverlap": 0.15,
            "gerber_cutouttooldia": 0.07,
            "gerber_cutoutmargin": 0.1,
            "gerber_cutoutgapsize": 0.15,
            "gerber_gaps": "4",
            "gerber_noncoppermargin": 0.0,
            "gerber_noncopperrounded": False,
            "gerber_bboxmargin": 0.0,
            "gerber_bboxrounded": False,
            "excellon_plot": True,
            "excellon_solid": False,
            "excellon_drillz": -0.1,
            "excellon_travelz": 0.1,
            "excellon_feedrate": 3.0,
            "geometry_plot": True,
            "geometry_cutz": -0.002,
            "geometry_travelz": 0.1,
            "geometry_feedrate": 3.0,
            "geometry_cnctooldia": 0.016,
            "geometry_painttooldia": 0.07,
            "geometry_paintoverlap": 0.15,
            "geometry_paintmargin": 0.0,
            "cncjob_plot": True,
            "cncjob_tooldia": 0.016,
            "cncjob_append": ""
        })
        self.options.update(self.defaults)  # Copy app defaults to project options
        #self.options_write_form()
        self.on_options_combo_change(0)  # Will show the initial form

        self.collection = ObjectCollection()
        self.ui.project_tab_layout.addWidget(self.collection.view)
        #### End of Data ####

        #### Worker ####
        App.log.info("Starting Worker...")
        self.worker = Worker(self)
        self.thr1 = QtCore.QThread()
        self.worker.moveToThread(self.thr1)
        self.connect(self.thr1, QtCore.SIGNAL("started()"), self.worker.run)
        self.thr1.start()

        #### Check for updates ####
        # Separate thread (Not worker)
        self.version = 7
        App.log.info("Checking for updates in backgroud (this is version %s)." % str(self.version))

        self.worker2 = Worker(self, name="worker2")
        self.thr2 = QtCore.QThread()
        self.worker2.moveToThread(self.thr2)
        self.connect(self.thr2, QtCore.SIGNAL("started()"), self.worker2.run)
        self.connect(self.thr2, QtCore.SIGNAL("started()"), lambda: self.worker_task.emit({'fcn': self.version_check,
                                                                                           'params': [],
                                                                                           'worker_name': "worker2"}))
        self.thr2.start()

        ### Signal handling ###
        ## Custom signals
        self.inform.connect(self.info)
        self.message.connect(self.message_dialog)
        self.progress.connect(self.set_progress_bar)
        self.object_created.connect(self.on_object_created)
        self.plots_updated.connect(self.on_plots_updated)
        self.file_opened.connect(self.register_recent)
        self.file_opened.connect(lambda kind, filename: self.register_folder(filename))
        ## Standard signals
        # Menu
        self.ui.menufilenew.triggered.connect(self.on_file_new)
        self.ui.menufileopengerber.triggered.connect(self.on_fileopengerber)
        self.ui.menufileopenexcellon.triggered.connect(self.on_fileopenexcellon)
        self.ui.menufileopengcode.triggered.connect(self.on_fileopengcode)
        self.ui.menufileopenproject.triggered.connect(self.on_file_openproject)
        self.ui.menufilesaveproject.triggered.connect(self.on_file_saveproject)
        self.ui.menufilesaveprojectas.triggered.connect(self.on_file_saveprojectas)
        self.ui.menufilesaveprojectcopy.triggered.connect(lambda: self.on_file_saveprojectas(make_copy=True))
        self.ui.menufilesavedefaults.triggered.connect(self.on_file_savedefaults)
        self.ui.menueditdelete.triggered.connect(self.on_delete)
        self.ui.menuoptions_transfer_a2o.triggered.connect(self.on_options_app2object)
        self.ui.menuoptions_transfer_a2p.triggered.connect(self.on_options_app2project)
        self.ui.menuoptions_transfer_o2a.triggered.connect(self.on_options_object2app)
        self.ui.menuoptions_transfer_p2a.triggered.connect(self.on_options_project2app)
        self.ui.menuoptions_transfer_o2p.triggered.connect(self.on_options_object2project)
        self.ui.menuoptions_transfer_p2o.triggered.connect(self.on_options_project2object)
        self.ui.menuviewdisableall.triggered.connect(self.disable_plots)
        self.ui.menuviewdisableother.triggered.connect(lambda: self.disable_plots(except_current=True))
        self.ui.menuviewenable.triggered.connect(self.enable_all_plots)
        self.ui.menutoolshell.triggered.connect(lambda: self.shell.show())
        self.ui.menuhelp_about.triggered.connect(self.on_about)
        self.ui.menuhelp_manual.triggered.connect(lambda: webbrowser.open(self.app_url))
        # Toolbar
        self.ui.zoom_fit_btn.triggered.connect(self.on_zoom_fit)
        self.ui.zoom_in_btn.triggered.connect(lambda: self.plotcanvas.zoom(1.5))
        self.ui.zoom_out_btn.triggered.connect(lambda: self.plotcanvas.zoom(1/1.5))
        self.ui.clear_plot_btn.triggered.connect(self.plotcanvas.clear)
        self.ui.replot_btn.triggered.connect(self.on_toolbar_replot)
        self.ui.delete_btn.triggered.connect(self.on_delete)
        self.ui.shell_btn.triggered.connect(lambda: self.shell.show())
        # Object list
        self.collection.view.activated.connect(self.on_row_activated)
        # Options
        self.ui.options_combo.activated.connect(self.on_options_combo_change)
        self.options_form.units_radio.group_toggle_fn = self.on_toggle_units

        ####################
        ### Other setups ###
        ####################
        self.setup_obj_classes()
        self.setup_recent_items()
        self.setup_component_editor()

        #########################
        ### Tools and Plugins ###
        #########################
        self.dblsidedtool = DblSidedTool(self)
        self.dblsidedtool.install()

        self.measeurement_tool = Measurement(self)
        self.measeurement_tool.install()

        #############
        ### Shell ###
        #############
        # TODO: Move this to its own class
        self.shell = FCShell(self)
        self.shell.setWindowIcon(self.ui.app_icon)
        self.shell.setWindowTitle("FlatCAM Shell")
        self.shell.show()
        self.shell.resize(550, 300)
        self.shell.append_output("FlatCAM Alpha 7\n(c) 2014 Juan Pablo Caram\n\n")
        self.shell.append_output("Type help to get started.\n\n")
        self.tcl = Tkinter.Tcl()
        self.setup_shell()

        App.log.debug("END of constructor. Releasing control.")

    def defaults_read_form(self):
        for option in self.defaults_form_fields:
            self.defaults[option] = self.defaults_form_fields[option].get_value()

    def defaults_write_form(self):
        for option in self.defaults:
            try:
                self.defaults_form_fields[option].set_value(self.defaults[option])
            except KeyError:
                self.log.error("defaults_write_form(): No field for: %s" % option)

    def disable_plots(self, except_current=False):
        """
        Disables all plots with exception of the current object if specified.

        :param except_current: Wether to skip the current object.
        :rtype except_current: boolean
        :return: None
        """
        # TODO: This method is very similar to replot_all. Try to merge.
        self.progress.emit(10)

        def worker_task(app_obj):
            percentage = 0.1
            try:
                delta = 0.9 / len(self.collection.get_list())
            except ZeroDivisionError:
                self.progress.emit(0)
                return
            for obj in self.collection.get_list():
                if obj != self.collection.get_active() or not except_current:
                    obj.options['plot'] = False
                    obj.plot()
                percentage += delta
                self.progress.emit(int(percentage*100))

            self.progress.emit(0)
            self.plots_updated.emit()

        # Send to worker
        self.worker_task.emit({'fcn': worker_task, 'params': [self]})

    def execCommand(self, text):
        """
        Hadles input from the shell.

        :param text: Input command
        :return: None
        """
        text = str(text)

        try:
            result = self.tcl.eval(str(text))
            self.shell.append_output(result + '\n')
        except Tkinter.TclError, e:
            self.shell.append_error('ERROR: ' + str(e) + '\n')
            raise
        return

        def shhelp(p=None):
            if not p:
                return "Available commands:\n" + '\n'.join(['  ' + cmd for cmd in commands])

            if p not in commands:
                return "Unknown command: %s" % p

            return commands[p]["help"]


        commands = {
            "open_gerber": {
                "fcn": self.open_gerber,
                "params": 1,
                "converters": [lambda x: x],
                "retfcn": lambda x: None,
                "help": "Opens a Gerber file.\n> open_gerber <filename>\n   filename: Path to file to open."
            },
            "open_excellon": {
                "fcn": self.open_excellon,
                "params": 1,
                "converters": [lambda x: x],
                "retfcn": lambda x: None,
                "help": "Opens an Excellon file.\n> open_excellon <filename>\n   filename: Path to file to open."
            },
            "open_gcode": {
                "fcn": self.open_gcode,
                "params": 1,
                "converters": [lambda x: x],
                "retfcn": lambda x: None,
                "help": "Opens an G-Code file.\n> open_gcode <filename>\n   filename: Path to file to open."
            },
            "open_project": {
                "fcn": self.open_project,
                "params": 1,
                "converters": [lambda x: x],
                "retfcn": lambda x: None,
                "help": "Opens a FlatCAM project.\n> open_project <filename>\n   filename: Path to file to open."
            },
            "save_project": {
                "fcn": self.save_project,
                "params": 1,
                "converters": [lambda x: x],
                "retfcn": lambda x: None,
                "help": "Saves the FlatCAM project to file.\n> save_project <filename>\n   filename: Path to file to save."
            },
            "help": {
                "fcn": shhelp,
                "params": [0, 1],
                "converters": [lambda x: x],
                "retfcn": lambda x: x,
                "help": "Shows list of commands."
            }
        }

        parts = re.findall(r'([\w\\:\.]+|".*?")+', text)
        parts = [p.replace('\n', '').replace('"', '') for p in parts]
        self.log.debug(parts)
        try:
            if parts[0] not in commands:
                self.shell.append_error("Unknown command\n")
                return

            #import inspect
            #inspect.getargspec(someMethod)
            if (type(commands[parts[0]]["params"]) is not list and len(parts)-1 != commands[parts[0]]["params"]) or \
                    (type(commands[parts[0]]["params"]) is list and len(parts)-1 not in commands[parts[0]]["params"]):
                self.shell.append_error(
                    "Command %s takes %d arguments. %d given.\n" %
                    (parts[0], commands[parts[0]]["params"], len(parts)-1)
                )
                return

            cmdfcn = commands[parts[0]]["fcn"]
            cmdconv = commands[parts[0]]["converters"]
            if len(parts)-1 > 0:
                retval = cmdfcn(*[cmdconv[i](parts[i+1]) for i in range(len(parts)-1)])
            else:
                retval = cmdfcn()
            retfcn = commands[parts[0]]["retfcn"]
            if retval and retfcn(retval):
                self.shell.append_output(retfcn(retval) + "\n")

        except:
            self.shell.append_error(''.join(traceback.format_exc()))
            #self.shell.append_error("?\n")

    def info(self, text):
        self.ui.info_label.setText(QtCore.QString(text))

    def load_defaults(self):
        """
        Loads the aplication's default settings from defaults.json into
        ``self.defaults``.

        :return: None
        """
        try:
            f = open("defaults.json")
            options = f.read()
            f.close()
        except IOError:
            self.log.error("Could not load defaults file.")
            self.inform.emit("ERROR: Could not load defaults file.")
            return

        try:
            defaults = json.loads(options)
        except:
            e = sys.exc_info()[0]
            App.log.error(str(e))
            self.inform.emit("ERROR: Failed to parse defaults file.")
            return
        self.defaults.update(defaults)

    def message_dialog(self, title, message, kind="info"):
        icon = {"info": QtGui.QMessageBox.Information,
                "warning": QtGui.QMessageBox.Warning,
                "error": QtGui.QMessageBox.Critical}[str(kind)]
        dlg = QtGui.QMessageBox(icon, title, message, parent=self.ui)
        dlg.setText(message)
        dlg.exec_()

    def register_recent(self, kind, filename):

        self.log.debug("register_recent()")
        self.log.debug("   %s" % kind)
        self.log.debug("   %s" % filename)

        record = {'kind': str(kind), 'filename': str(filename)}
        if record in self.recent:
            return

        self.recent.insert(0, record)

        if len(self.recent) > 10:  # Limit reached
            self.recent.pop()

        try:
            f = open('recent.json', 'w')
        except IOError:
            App.log.error("Failed to open recent items file for writing.")
            self.inform.emit('Failed to open recent files file for writing.')
            return

        #try:
        json.dump(self.recent, f)
        # except:
        #     App.log.error("Failed to write to recent items file.")
        #     self.inform.emit('ERROR: Failed to write to recent items file.')
        #     f.close()

        f.close()

        # Re-buid the recent items menu
        self.setup_recent_items()

    def new_object(self, kind, name, initialize, active=True, fit=True, plot=True):
        """
        Creates a new specalized FlatCAMObj and attaches it to the application,
        this is, updates the GUI accordingly, any other records and plots it.
        This method is thread-safe.

        :param kind: The kind of object to create. One of 'gerber',
         'excellon', 'cncjob' and 'geometry'.
        :type kind: str
        :param name: Name for the object.
        :type name: str
        :param initialize: Function to run after creation of the object
         but before it is attached to the application. The function is
         called with 2 parameters: the new object and the App instance.
        :type initialize: function
        :return: None
        :rtype: None
        """

        App.log.debug("new_object()")

        ### Check for existing name
        if name in self.collection.get_names():
            ## Create a new name
            # Ends with number?
            App.log.debug("new_object(): Object name exists, changing.")
            match = re.search(r'(.*[^\d])?(\d+)$', name)
            if match:  # Yes: Increment the number!
                base = match.group(1) or ''
                num = int(match.group(2))
                name = base + str(num + 1)
            else:  # No: add a number!
                name += "_1"

        # Create object
        classdict = {
            "gerber": FlatCAMGerber,
            "excellon": FlatCAMExcellon,
            "cncjob": FlatCAMCNCjob,
            "geometry": FlatCAMGeometry
        }

        App.log.debug("Calling object constructor...")
        obj = classdict[kind](name)
        obj.units = self.options["units"]  # TODO: The constructor should look at defaults.

        # Set default options from self.options
        for option in self.options:
            if option.find(kind + "_") == 0:
                oname = option[len(kind)+1:]
                obj.options[oname] = self.options[option]

        # Initialize as per user request
        # User must take care to implement initialize
        # in a thread-safe way as is is likely that we
        # have been invoked in a separate thread.
        initialize(obj, self)

        # Check units and convert if necessary
        if self.options["units"].upper() != obj.units.upper():
            self.inform.emit("Converting units to " + self.options["units"] + ".")
            obj.convert_units(self.options["units"])

        FlatCAMApp.App.log.debug("Moving new object back to main thread.")

        # Move the object to the main thread and let the app know that it is available.
        obj.moveToThread(QtGui.QApplication.instance().thread())
        self.object_created.emit(obj)

        return obj

    def options_read_form(self):
        for option in self.options_form_fields:
            self.options[option] = self.options_form_fields[option].get_value()

    def options_write_form(self):
        for option in self.options:
            try:
                self.options_form_fields[option].set_value(self.options[option])
            except KeyError:
                self.log.error("options_write_form(): No field for: %s" % option)

    def on_about(self):

        class AboutDialog(QtGui.QDialog):
            def __init__(self, parent=None):
                QtGui.QDialog.__init__(self, parent)

                self.setWindowIcon(parent.app_icon)

                layout1 = QtGui.QVBoxLayout()
                self.setLayout(layout1)

                layout2 = QtGui.QHBoxLayout()
                layout1.addLayout(layout2)

                logo = QtGui.QLabel()
                logo.setPixmap(QtGui.QPixmap('share/flatcam_icon256.png'))
                layout2.addWidget(logo, stretch=0)

                title = QtGui.QLabel(
                    "<font size=8><B>FlatCAM</B></font><BR>"
                    "Version Alpha 7 (2014/10)<BR>"
                    "<BR>"
                    "2D Post-processing for Manufacturing specialized in<BR>"
                    "Printed Circuit Boards<BR>"
                    "<BR>"
                    "(c) 2014 Juan Pablo Caram"
                )
                layout2.addWidget(title, stretch=1)

                layout3 = QtGui.QHBoxLayout()
                layout1.addLayout(layout3)
                layout3.addStretch()
                okbtn = QtGui.QPushButton("Close")
                layout3.addWidget(okbtn)

                okbtn.clicked.connect(self.accept)

        AboutDialog(self.ui).exec_()

    def on_file_savedefaults(self):
        """
        Callback for menu item File->Save Defaults. Saves application default options
        ``self.defaults`` to defaults.json.

        :return: None
        """

        # Read options from file
        try:
            f = open("defaults.json")
            options = f.read()
            f.close()
        except:
            App.log.error("Could not load defaults file.")
            self.inform.emit("ERROR: Could not load defaults file.")
            return

        try:
            defaults = json.loads(options)
        except:
            e = sys.exc_info()[0]
            App.log.error("Failed to parse defaults file.")
            App.log.error(str(e))
            self.inform.emit("ERROR: Failed to parse defaults file.")
            return

        # Update options
        self.defaults_read_form()
        defaults.update(self.defaults)

        # Save update options
        try:
            f = open("defaults.json", "w")
            json.dump(defaults, f)
            f.close()
        except:
            self.inform.emit("ERROR: Failed to write defaults to file.")
            return

        self.inform.emit("Defaults saved.")

    def on_options_app2project(self):
        """
        Callback for Options->Transfer Options->App=>Project. Copies options
        from application defaults to project defaults.

        :return: None
        """

        self.defaults_read_form()
        self.options.update(self.defaults)
        self.options_write_form()

    def on_options_project2app(self):
        """
        Callback for Options->Transfer Options->Project=>App. Copies options
        from project defaults to application defaults.

        :return: None
        """

        self.options_read_form()
        self.defaults.update(self.options)
        self.defaults_write_form()

    def on_options_project2object(self):
        """
        Callback for Options->Transfer Options->Project=>Object. Copies options
        from project defaults to the currently selected object.

        :return: None
        """

        self.options_read_form()
        obj = self.collection.get_active()
        if obj is None:
            self.inform.emit("WARNING: No object selected.")
            return
        for option in self.options:
            if option.find(obj.kind + "_") == 0:
                oname = option[len(obj.kind)+1:]
                obj.options[oname] = self.options[option]
        obj.to_form()  # Update UI

    def on_options_object2project(self):
        """
        Callback for Options->Transfer Options->Object=>Project. Copies options
        from the currently selected object to project defaults.

        :return: None
        """

        obj = self.collection.get_active()
        if obj is None:
            self.inform.emit("WARNING: No object selected.")
            return
        obj.read_form()
        for option in obj.options:
            if option in ['name']:  # TODO: Handle this better...
                continue
            self.options[obj.kind + "_" + option] = obj.options[option]
        self.options_write_form()

    def on_options_object2app(self):
        """
        Callback for Options->Transfer Options->Object=>App. Copies options
        from the currently selected object to application defaults.

        :return: None
        """
        obj = self.collection.get_active()
        if obj is None:
            self.inform.emit("WARNING: No object selected.")
            return
        obj.read_form()
        for option in obj.options:
            if option in ['name']:  # TODO: Handle this better...
                continue
            self.defaults[obj.kind + "_" + option] = obj.options[option]
        self.defaults_write_form()

    def on_options_app2object(self):
        """
        Callback for Options->Transfer Options->App=>Object. Copies options
        from application defaults to the currently selected object.

        :return: None
        """

        self.defaults_read_form()
        obj = self.collection.get_active()
        if obj is None:
            self.inform.emit("WARNING: No object selected.")
            return
        for option in self.defaults:
            if option.find(obj.kind + "_") == 0:
                oname = option[len(obj.kind)+1:]
                obj.options[oname] = self.defaults[option]
        obj.to_form()  # Update UI

    def on_toggle_units(self):
        """
        Callback for the Units radio-button change in the Options tab.
        Changes the application's default units or the current project's units.
        If changing the project's units, the change propagates to all of
        the objects in the project.

        :return: None
        """

        if self.toggle_units_ignore:
            return

        # If option is the same, then ignore
        if self.options_form.units_radio.get_value().upper() == self.options['units'].upper():
            self.log.debug("on_toggle_units(): Same as options, so ignoring.")
            return

        # Options to scale
        dimensions = ['gerber_isotooldia', 'gerber_cutoutmargin', 'gerber_cutoutgapsize',
                      'gerber_noncoppermargin', 'gerber_bboxmargin', 'excellon_drillz',
                      'excellon_travelz', 'excellon_feedrate', 'cncjob_tooldia',
                      'geometry_cutz', 'geometry_travelz', 'geometry_feedrate',
                      'geometry_cnctooldia', 'geometry_painttooldia', 'geometry_paintoverlap',
                      'geometry_paintmargin']

        def scale_options(sfactor):
            for dim in dimensions:
                self.options[dim] *= sfactor

        # The scaling factor depending on choice of units.
        factor = 1/25.4
        if self.options_form.units_radio.get_value().upper() == 'MM':
            factor = 25.4

        # Changing project units. Warn user.
        msgbox = QtGui.QMessageBox()
        msgbox.setText("<B>Change project units ...</B>")
        msgbox.setInformativeText("Changing the units of the project causes all geometrical "
                                  "properties of all objects to be scaled accordingly. Continue?")
        msgbox.setStandardButtons(QtGui.QMessageBox.Cancel | QtGui.QMessageBox.Ok)
        msgbox.setDefaultButton(QtGui.QMessageBox.Ok)

        response = msgbox.exec_()

        if response == QtGui.QMessageBox.Ok:
            self.options_read_form()
            scale_options(factor)
            self.options_write_form()
            for obj in self.collection.get_list():
                units = self.options_form.units_radio.get_value().upper()
                obj.convert_units(units)
            current = self.collection.get_active()
            if current is not None:
                current.to_form()
            self.plot_all()
        else:
            # Undo toggling
            self.toggle_units_ignore = True
            if self.options_form.units_radio.get_value().upper() == 'MM':
                self.options_form.units_radio.set_value('IN')
            else:
                self.options_form.units_radio.set_value('MM')
            self.toggle_units_ignore = False

        self.options_read_form()
        self.inform.emit("Converted units to %s" % self.options["units"])
        self.ui.units_label.setText("[" + self.options["units"] + "]")

    def on_options_combo_change(self, sel):
        """
        Called when the combo box to choose between application defaults and
        project option changes value. The corresponding variables are
        copied to the UI.

        :param sel: The option index that was chosen.
        :return: None
        """

        # combo_sel = self.ui.notebook.combo_options.get_active()
        App.log.debug("Options --> %s" % sel)

        # Remove anything else in the box
        # box_children = self.options_box.get_children()
        # box_children = self.ui.notebook.options_contents.get_children()
        # for child in box_children:
        #     self.ui.notebook.options_contents.remove(child)

        # try:
        #     self.ui.options_area.removeWidget(self.defaults_form)
        # except:
        #     pass
        #
        # try:
        #     self.ui.options_area.removeWidget(self.options_form)
        # except:
        #     pass

        form = [self.defaults_form, self.options_form][sel]
        # self.ui.notebook.options_contents.pack_start(form, False, False, 1)
        try:
            self.ui.options_scroll_area.takeWidget()
        except:
            self.log.debug("Nothing to remove")
        self.ui.options_scroll_area.setWidget(form)
        form.show()

        # self.options2form()

    def on_delete(self):
        """
        Delete the currently selected FlatCAMObj.

        :return: None
        """

        # Keep this for later
        try:
            name = copy(self.collection.get_active().options["name"])
        except AttributeError:
            self.log.debug("Nothing selected for deletion")
            return

        # Remove plot
        self.plotcanvas.figure.delaxes(self.collection.get_active().axes)
        self.plotcanvas.auto_adjust_axes()

        # Clear form
        self.setup_component_editor()

        # Remove from dictionary
        self.collection.delete_active()

        self.inform.emit("Object deleted: %s" % name)

    def on_plots_updated(self):
        self.plotcanvas.auto_adjust_axes()
        self.on_zoom_fit(None)

    def on_toolbar_replot(self):
        """
        Callback for toolbar button. Re-plots all objects.

        :return: None
        """
        self.log.debug("on_toolbar_replot()")

        try:
            self.collection.get_active().read_form()
        except AttributeError:
            self.log.debug("on_toolbar_replot(): AttributeError")
            pass

        self.plot_all()

    def on_row_activated(self, index):
        self.ui.notebook.setCurrentWidget(self.ui.selected_tab)

    def on_object_created(self, obj):
        self.log.debug("on_object_created()")
        self.inform.emit("Object (%s) created: %s" % (obj.kind, obj.options['name']))
        self.collection.append(obj)
        obj.plot()
        self.on_zoom_fit(None)

    def on_zoom_fit(self, event):
        """
        Callback for zoom-out request. This can be either from the corresponding
        toolbar button or the '1' key when the canvas is focused. Calls ``self.adjust_axes()``
        with axes limits from the geometry bounds of all objects.

        :param event: Ignored.
        :return: None
        """
        xmin, ymin, xmax, ymax = self.collection.get_bounds()
        width = xmax - xmin
        height = ymax - ymin
        xmin -= 0.05 * width
        xmax += 0.05 * width
        ymin -= 0.05 * height
        ymax += 0.05 * height
        self.plotcanvas.adjust_axes(xmin, ymin, xmax, ymax)

    def on_key_over_plot(self, event):
        """
        Callback for the key pressed event when the canvas is focused. Keyboard
        shortcuts are handled here. So far, these are the shortcuts:

        ==========  ============================================
        Key         Action
        ==========  ============================================
        '1'         Zoom-fit. Fits the axes limits to the data.
        '2'         Zoom-out.
        '3'         Zoom-in.
        'm'         Toggle on-off the measuring tool.
        ==========  ============================================

        :param event: Ignored.
        :return: None
        """

        if event.key == '1':  # 1
            self.on_zoom_fit(None)
            return

        if event.key == '2':  # 2
            self.plotcanvas.zoom(1 / 1.5, self.mouse)
            return

        if event.key == '3':  # 3
            self.plotcanvas.zoom(1.5, self.mouse)
            return

        # if event.key == 'm':
        #     if self.measure.toggle_active():
        #         self.inform.emit("Measuring tool ON")
        #     else:
        #         self.inform.emit("Measuring tool OFF")
        #     return

    def on_click_over_plot(self, event):
        """
        Callback for the mouse click event over the plot. This event is generated
        by the Matplotlib backend and has been registered in ``self.__init__()``.
        For details, see: http://matplotlib.org/users/event_handling.html

        Default actions are:

        * Copy coordinates to clipboard. Ex.: (65.5473, -13.2679)

        :param event: Contains information about the event, like which button
            was clicked, the pixel coordinates and the axes coordinates.
        :return: None
        """

        # So it can receive key presses
        self.plotcanvas.canvas.setFocus()

        try:
            App.log.debug('button=%d, x=%d, y=%d, xdata=%f, ydata=%f' % (
                event.button, event.x, event.y, event.xdata, event.ydata))

            self.clipboard.setText("(%.4f, %.4f)" % (event.xdata, event.ydata))

        except Exception, e:
            App.log.debug("Outside plot?")
            App.log.debug(str(e))

    def on_mouse_move_over_plot(self, event):
        """
        Callback for the mouse motion event over the plot. This event is generated
        by the Matplotlib backend and has been registered in ``self.__init__()``.
        For details, see: http://matplotlib.org/users/event_handling.html

        :param event: Contains information about the event.
        :return: None
        """

        try:  # May fail in case mouse not within axes
            self.ui.position_label.setText("X: %.4f   Y: %.4f" % (
                event.xdata, event.ydata))
            self.mouse = [event.xdata, event.ydata]

        except:
            self.ui.position_label.setText("")
            self.mouse = None

    def on_file_new(self):
        """
        Callback for menu item File->New. Returns the application to its
        startup state. This method is thread-safe.

        :return: None
        """
        # Remove everything from memory
        App.log.debug("on_file_new()")

        self.plotcanvas.clear()

        self.collection.delete_all()

        self.setup_component_editor()

        # Clear project filename
        self.project_filename = None

        # Re-fresh project options
        self.on_options_app2project()

    def on_options_app2project(self):
        """
        Callback for Options->Transfer Options->App=>Project. Copies options
        from application defaults to project defaults.

        :return: None
        """

        self.options.update(self.defaults)

    def on_fileopengerber(self):
        App.log.debug("on_fileopengerber()")
        try:
            filename = QtGui.QFileDialog.getOpenFileName(caption="Open Gerber",
                                                         directory=self.last_folder)
        except TypeError:
            filename = QtGui.QFileDialog.getOpenFileName(caption="Open Gerber")

        # The Qt methods above will return a QString which can cause problems later.
        # So far json.dump() will fail to serialize it.
        # TODO: Improve the serialization methods and remove this fix.
        filename = str(filename)

        if str(filename) == "":
            self.inform.emit("Open cancelled.")
        else:
            self.worker_task.emit({'fcn': self.open_gerber,
                                   'params': [filename]})

    def on_fileopenexcellon(self):
        App.log.debug("on_fileopenexcellon()")
        try:
            filename = QtGui.QFileDialog.getOpenFileName(caption="Open Excellon",
                                                         directory=self.last_folder)
        except TypeError:
            filename = QtGui.QFileDialog.getOpenFileName(caption="Open Excellon")

        # The Qt methods above will return a QString which can cause problems later.
        # So far json.dump() will fail to serialize it.
        # TODO: Improve the serialization methods and remove this fix.
        filename = str(filename)

        if str(filename) == "":
            self.inform.emit("Open cancelled.")
        else:
            self.worker_task.emit({'fcn': self.open_excellon,
                                   'params': [filename]})

    def on_fileopengcode(self):
        App.log.debug("on_fileopengcode()")

        try:
            filename = QtGui.QFileDialog.getOpenFileName(caption="Open G-Code",
                                                         directory=self.last_folder)
        except TypeError:
            filename = QtGui.QFileDialog.getOpenFileName(caption="Open G-Code")

        # The Qt methods above will return a QString which can cause problems later.
        # So far json.dump() will fail to serialize it.
        # TODO: Improve the serialization methods and remove this fix.
        filename = str(filename)

        if str(filename) == "":
            self.inform.emit("Open cancelled.")
        else:
            self.worker_task.emit({'fcn': self.open_gcode,
                                   'params': [filename]})

    def on_file_openproject(self):
        App.log.debug("on_file_openproject()")

        try:
            filename = QtGui.QFileDialog.getOpenFileName(caption="Open Project",
                                                         directory=self.last_folder)
        except TypeError:
            filename = QtGui.QFileDialog.getOpenFileName(caption="Open Project")

        # The Qt methods above will return a QString which can cause problems later.
        # So far json.dump() will fail to serialize it.
        # TODO: Improve the serialization methods and remove this fix.
        filename = str(filename)

        if str(filename) == "":
            self.inform.emit("Open cancelled.")
        else:
            self.worker_task.emit({'fcn': self.open_project,
                                   'params': [filename]})

    def on_file_saveproject(self):
        """
        Callback for menu item File->Save Project. Saves the project to
        ``self.project_filename`` or calls ``self.on_file_saveprojectas()``
        if set to None. The project is saved by calling ``self.save_project()``.

        :return: None
        """

        if self.project_filename is None:
            self.on_file_saveprojectas()
        else:
            self.save_project(self.project_filename)
            self.file_opened.emit("project", self.project_filename)
            self.inform.emit("Project saved to: " + self.project_filename)

    def on_file_saveprojectas(self, make_copy=False):
        """
        Callback for menu item File->Save Project As... Opens a file
        chooser and saves the project to the given file via
        ``self.save_project()``.

        :return: None
        """

        try:
            filename = QtGui.QFileDialog.getSaveFileName(caption="Save Project As ...",
                                                         directory=self.last_folder)
        except TypeError:
            filename = QtGui.QFileDialog.getSaveFileName(caption="Save Project As ...")

        try:
            f = open(filename, 'r')
            f.close()
            exists = True
        except IOError:
            exists = False

        msg = "File exists. Overwrite?"
        if exists:
            msgbox = QtGui.QMessageBox()
            msgbox.setInformativeText(msg)
            msgbox.setStandardButtons(QtGui.QMessageBox.Cancel | QtGui.QMessageBox.Ok)
            msgbox.setDefaultButton(QtGui.QMessageBox.Cancel)
            result = msgbox.exec_()
            if result == QtGui.QMessageBox.Cancel:
                return

        self.save_project(filename)
        self.file_opened.emit("project", filename)

        if not make_copy:
            self.project_filename = filename
            self.inform.emit("Project saved to: " + self.project_filename)
        else:
            self.inform.emit("Project copy saved to: " + self.project_filename)

    def open_gerber(self, filename):
        """
        Opens a Gerber file, parses it and creates a new object for
        it in the program. Thread-safe.

        :param filename: Gerber file filename
        :type filename: str
        :return: None
        """

        App.log.debug("open_gerber()")

        self.progress.emit(10)

        # How the object should be initialized
        def obj_init(gerber_obj, app_obj):
            assert isinstance(gerber_obj, FlatCAMGerber)

            # Opening the file happens here
            self.progress.emit(30)
            gerber_obj.parse_file(filename)

            # Further parsing
            self.progress.emit(70)

        # Object name
        name = filename.split('/')[-1].split('\\')[-1]

        self.new_object("gerber", name, obj_init)

        # New object creation and file processing
        # try:
        #     self.new_object("gerber", name, obj_init)
        # except:
        #     e = sys.exc_info()
        #     print "ERROR:", e[0]
        #     traceback.print_exc()
        #     self.message_dialog("Failed to create Gerber Object",
        #                         "Attempting to create a FlatCAM Gerber Object from " +
        #                         "Gerber file failed during processing:\n" +
        #                         str(e[0]) + " " + str(e[1]), kind="error")
        #     GLib.timeout_add_seconds(1, lambda: self.set_progress_bar(0.0, "Idle"))
        #     self.collection.delete_active()
        #     return

        # Register recent file
        self.file_opened.emit("gerber", filename)

        self.progress.emit(100)

        # GUI feedback
        self.inform.emit("Opened: " + filename)

    def open_excellon(self, filename):
        """
        Opens an Excellon file, parses it and creates a new object for
        it in the program. Thread-safe.

        :param filename: Excellon file filename
        :type filename: str
        :return: None
        """

        App.log.debug("open_excellon()")

        self.progress.emit(10)

        # How the object should be initialized
        def obj_init(excellon_obj, app_obj):
            self.progress.emit(20)
            excellon_obj.parse_file(filename)
            excellon_obj.create_geometry()
            self.progress.emit(70)

        # Object name
        name = filename.split('/')[-1].split('\\')[-1]

        self.new_object("excellon", name, obj_init)
        # New object creation and file processing
        # try:
        #     self.new_object("excellon", name, obj_init)
        # except:
        #     e = sys.exc_info()
        #     App.log.error(str(e))
        #     self.message_dialog("Failed to create Excellon Object",
        #                         "Attempting to create a FlatCAM Excellon Object from " +
        #                         "Excellon file failed during processing:\n" +
        #                         str(e[0]) + " " + str(e[1]), kind="error")
        #     self.progress.emit(0)
        #     self.collection.delete_active()
        #     return

        # Register recent file
        self.file_opened.emit("excellon", filename)

        # GUI feedback
        self.inform.emit("Opened: " + filename)
        self.progress.emit(100)

    def open_gcode(self, filename):
        """
        Opens a G-gcode file, parses it and creates a new object for
        it in the program. Thread-safe.

        :param filename: G-code file filename
        :type filename: str
        :return: None
        """
        App.log.debug("open_gcode()")

        # How the object should be initialized
        def obj_init(job_obj, app_obj_):
            """

            :type app_obj_: App
            """
            assert isinstance(app_obj_, App)
            self.progress.emit(10)

            f = open(filename)
            gcode = f.read()
            f.close()

            job_obj.gcode = gcode

            self.progress.emit(20)
            job_obj.gcode_parse()

            self.progress.emit(60)
            job_obj.create_geometry()

        # Object name
        name = filename.split('/')[-1].split('\\')[-1]

        # New object creation and file processing
        try:
            self.new_object("cncjob", name, obj_init)
        except:
            e = sys.exc_info()
            App.log.error(str(e))
            self.message_dialog("Failed to create CNCJob Object",
                                "Attempting to create a FlatCAM CNCJob Object from " +
                                "G-Code file failed during processing:\n" +
                                str(e[0]) + " " + str(e[1]), kind="error")
            self.progress.emit(0)
            self.collection.delete_active()
            return

        # Register recent file
        self.file_opened.emit("cncjob", filename)

        # GUI feedback
        self.inform.emit("Opened: " + filename)
        self.progress.emit(100)

    def open_project(self, filename):
        """
        Loads a project from the specified file.

        1) Loads and parses file
        2) Registers the file as recently opened.
        3) Calls on_file_new()
        4) Updates options
        5) Calls new_object() with the object's from_dict() as init method.
        6) Calls plot_all()

        :param filename:  Name of the file from which to load.
        :type filename: str
        :return: None
        """
        App.log.debug("Opening project: " + filename)

        try:
            f = open(filename, 'r')
        except IOError:
            App.log.error("Failed to open project file: %s" % filename)
            self.inform.emit("ERROR: Failed to open project file: %s" % filename)
            return

        try:
            d = json.load(f, object_hook=dict2obj)
        except:
            App.log.error("Failed to parse project file: %s" % filename)
            self.inform.emit("ERROR: Failed to parse project file: %s" % filename)
            f.close()
            return

        self.file_opened.emit("project", filename)

        # Clear the current project
        self.on_file_new()

        # Project options
        self.options.update(d['options'])
        self.project_filename = filename
        self.ui.units_label.setText("[" + self.options["units"] + "]")

        # Re create objects
        App.log.debug("Re-creating objects...")
        for obj in d['objs']:
            def obj_init(obj_inst, app_inst):
                obj_inst.from_dict(obj)
            App.log.debug(obj['kind'] + ":  " + obj['options']['name'])
            self.new_object(obj['kind'], obj['options']['name'], obj_init, active=False, fit=False, plot=False)

        self.plot_all()
        self.inform.emit("Project loaded from: " + filename)
        App.log.debug("Project loaded")

    def plot_all(self):
        """
        Re-generates all plots from all objects.

        :return: None
        """
        self.log.debug("plot_all()")

        self.plotcanvas.clear()
        self.progress.emit(10)

        def worker_task(app_obj):
            percentage = 0.1
            try:
                delta = 0.9 / len(self.collection.get_list())
            except ZeroDivisionError:
                self.progress.emit(0)
                return
            for obj in self.collection.get_list():
                obj.plot()
                percentage += delta
                self.progress.emit(int(percentage*100))

            self.progress.emit(0)
            self.plots_updated.emit()

        # Send to worker
        #self.worker.add_task(worker_task, [self])
        self.worker_task.emit({'fcn': worker_task, 'params': [self]})

    def register_folder(self, filename):
        self.last_folder = os.path.split(str(filename))[0]

    def set_progress_bar(self, percentage, text=""):
        self.ui.progress_bar.setValue(int(percentage))

    def setup_shell(self):
        self.log.debug("setup_shell()")

        def shelp(p=None):
            if not p:
                return "Available commands:\n" + '\n'.join(['  ' + cmd for cmd in commands]) + \
                "\n\nType help <command_name> for usage.\n Example: help open_gerber"

            if p not in commands:
                return "Unknown command: %s" % p

            return commands[p]["help"]

        def options(name):
            ops = self.collection.get_by_name(str(name)).options
            return '\n'.join(["%s: %s" % (o, ops[o]) for o in ops])

        def isolate(name, dia=None, passes=None, overlap=None):
            dia = float(dia) if dia is not None else None
            passes = int(passes) if passes is not None else None
            overlap = float(overlap) if overlap is not None else None
            self.collection.get_by_name(str(name)).isolate(dia, passes, overlap)

        commands = {
            'help': {
                'fcn': shelp,
                'help': "Shows list of commands."
            },
            'open_gerber': {
                'fcn': self.open_gerber,
                'help': "Opens a Gerber file.\n> open_gerber <filename>\n   filename: Path to file to open."
            },
            'open_excellon': {
                'fcn': self.open_excellon,
                'help': "Opens an Excellon file.\n> open_excellon <filename>\n   filename: Path to file to open."
            },
            'open_gcode': {
                'fcn': self.open_gcode,
                'help': "Opens an G-Code file.\n> open_gcode <filename>\n   filename: Path to file to open."
            },
            'open_project': {
                'fcn': self.open_project,
                "help": "Opens a FlatCAM project.\n> open_project <filename>\n   filename: Path to file to open."
            },
            'save_project': {
                'fcn': self.save_project,
                'help': "Saves the FlatCAM project to file.\n> save_project <filename>\n   filename: Path to file to save."
            },
            'set_active': {
                'fcn': self.collection.set_active,
                'help': "Sets a FlatCAM object as active.\n > set_active <name>\n   name: Name of the object."
            },
            'get_names': {
                'fcn': lambda: '\n'.join(self.collection.get_names()),
                'help': "Lists the names of objects in the project.\n > get_names"
            },
            'new': {
                'fcn': self.on_file_new,
                'help': "Starts a new project. Clears objects from memory.\n > new"
            },
            'options': {
                'fcn': options,
                'help': "Shows the settings for an object.\n > options <name>\n   name: Object name."
            },
            'isolate': {
                'fcn': isolate,
                'help': "Creates isolation routing geometry for the given Gerber.\n" +
                        "> isolate <name> [dia [passes [overlap]]]\n" +
                        "   name: Name if the object\n"
                        "   dia: Tool diameter\n   passes: # of tool width\n" +
                        "   overlap: Fraction of tool diameter to overlap passes"
            },
            'scale': {
                'fcn': lambda name, factor: self.collection.get_by_name(str(name)).scale(float(factor)),
                'help': "Resizes the object by a factor.\n" +
                        "> scale <name> <factor>\n" +
                        "   name: Name of the object\n   factor: Fraction by which to scale"
            },
            'offset': {
                'fcn': lambda name, x, y: self.collection.get_by_name(str(name)).offset([float(x), float(y)]),
                'help': "Changes the position of the object.\n" +
                        "> offset <name> <x> <y>\n" +
                        "   name: Name of the object\n" +
                        "   x: X-axis distance\n" +
                        "   y: Y-axis distance"
            },
            'plot': {
                'fcn': self.plot_all,
                'help': 'Updates the plot on the user interface'
            }
        }

        for cmd in commands:
            self.tcl.createcommand(cmd, commands[cmd]['fcn'])

        self.tcl.eval('''
            rename puts original_puts
            proc puts {args} {
                if {[llength $args] == 1} {
                    return "[lindex $args 0]"
                } else {
                    eval original_puts $args
                }
            }
            ''')



    def setup_recent_items(self):
        self.log.debug("setup_recent_items()")

        # TODO: Move this to constructor
        icons = {
            "gerber": "share/flatcam_icon16.png",
            "excellon": "share/drill16.png",
            "cncjob": "share/cnc16.png",
            "project": "share/project16.png"
        }

        openers = {
            'gerber': lambda fname: self.worker_task.emit({'fcn': self.open_gerber, 'params': [fname]}),
            'excellon': lambda fname: self.worker_task.emit({'fcn': self.open_excellon, 'params': [fname]}),
            'cncjob': lambda fname: self.worker_task.emit({'fcn': self.open_gcode, 'params': [fname]}),
            'project': self.open_project
        }

        # Open file
        try:
            f = open('recent.json')
        except IOError:
            App.log.error("Failed to load recent item list.")
            self.inform.emit("ERROR: Failed to load recent item list.")
            return

        try:
            self.recent = json.load(f)
        except json.scanner.JSONDecodeError:
            App.log.error("Failed to parse recent item list.")
            self.inform.emit("ERROR: Failed to parse recent item list.")
            f.close()
            return
        f.close()

        # Closure needed to create callbacks in a loop.
        # Otherwise late binding occurs.
        def make_callback(func, fname):
            def opener():
                func(fname)
            return opener

        # Reset menu
        self.ui.recent.clear()

        # Create menu items
        for recent in self.recent:
            filename = recent['filename'].split('/')[-1].split('\\')[-1]
            action = QtGui.QAction(QtGui.QIcon(icons[recent["kind"]]), filename, self)

            o = make_callback(openers[recent["kind"]], recent['filename'])

            action.triggered.connect(o)
            self.ui.recent.addAction(action)

        # self.builder.get_object('open_recent').set_submenu(recent_menu)
        # self.ui.menufilerecent.set_submenu(recent_menu)
        # recent_menu.show_all()
        # self.ui.recent.show()

    def setup_component_editor(self):
        label = QtGui.QLabel("Choose an item from Project")
        label.setAlignment(QtCore.Qt.AlignHCenter | QtCore.Qt.AlignVCenter)
        self.ui.selected_scroll_area.setWidget(label)

    def setup_obj_classes(self):
        """
        Sets up application specifics on the FlatCAMObj class.

        :return: None
        """
        FlatCAMObj.app = self

    def version_check(self):
        """
        Checks for the latest version of the program. Alerts the
        user if theirs is outdated. This method is meant to be run
        in a saeparate thread.

        :return: None
        """

        self.log.debug("version_check()")

        try:
            f = urllib.urlopen(App.version_url)
        except:
            App.log.warning("Failed checking for latest version. Could not connect.")
            self.inform.emit("Failed checking for latest version. Could not connect.")
            return

        try:
            data = json.load(f)
        except:
            App.log.error("Could not parse information about latest version.")
            self.inform.emit("Could not parse information about latest version.")
            f.close()
            return

        f.close()

        if self.version >= data["version"]:
            App.log.debug("FlatCAM is up to date!")
            self.inform.emit("FlatCAM is up to date!")
            return

        App.log.debug("Newer version available.")
        self.message.emit(
            "Newer Version Available",
            "There is a newer version of FlatCAM\n" +
            "available for download:\n\n" +
            data["name"] + "\n\n" + data["message"],
            "info"
        )

    def enable_all_plots(self, *args):
        self.plotcanvas.clear()

        def worker_task(app_obj):
            percentage = 0.1
            try:
                delta = 0.9 / len(self.collection.get_list())
            except ZeroDivisionError:
                self.progress.emit(0)
                return
            for obj in self.collection.get_list():
                obj.options['plot'] = True
                obj.plot()
                percentage += delta
                self.progress.emit(int(percentage*100))

            self.progress.emit(0)
            self.plots_updated.emit()

        # Send to worker
        # self.worker.add_task(worker_task, [self])
        self.worker_task.emit({'fcn': worker_task, 'params': [self]})

    def save_project(self, filename):
        """
        Saves the current project to the specified file.

        :param filename: Name of the file in which to save.
        :type filename: str
        :return: None
        """
        self.log.debug("save_project()")

        ## Capture the latest changes
        # Current object
        try:
            self.collection.get_active().read_form()
        except:
            self.log.debug("There was no active object")
            pass
        # Project options
        self.options_read_form()

        # Serialize the whole project
        d = {"objs": [obj.to_dict() for obj in self.collection.get_list()],
             "options": self.options,
             "version": self.version}

        # Open file
        try:
            f = open(filename, 'w')
        except IOError:
            App.log.error("ERROR: Failed to open file for saving:", filename)
            return

        # Write
        try:
            json.dump(d, f, default=to_dict)
        except:
            App.log.error("ERROR: File open but failed to write:", filename)
            f.close()
            return

        f.close()

        self.inform.emit("Project saved to: %s" % filename)

# def main():
#
#     app = QtGui.QApplication(sys.argv)
#     fc = App()
#     sys.exit(app.exec_())
#
#
# if __name__ == '__main__':
#     main()