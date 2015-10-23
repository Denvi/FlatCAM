import sys
import urllib
import getopt
import random
import logging
import simplejson as json
import re
import webbrowser
import os
import Tkinter
from PyQt4 import QtCore
import time  # Just used for debugging. Double check before removing.

########################################
##      Imports part of FlatCAM       ##
########################################
from FlatCAMWorker import Worker
from ObjectCollection import *
from FlatCAMObj import *
from PlotCanvas import *
from FlatCAMGUI import *
from FlatCAMCommon import LoudDict
from FlatCAMShell import FCShell
from FlatCAMDraw import FlatCAMDraw
from FlatCAMProcess import *
from MeasurementTool import Measurement
from DblSidedTool import DblSidedTool


########################################
##                App                 ##
########################################
class App(QtCore.QObject):
    """
    The main application class. The constructor starts the GUI.
    """

    ## Get Cmd Line Options
    cmd_line_shellfile = ''
    cmd_line_help = "FlatCam.py --shellfile=<cmd_line_shellfile>"
    try:
        cmd_line_options, args = getopt.getopt(sys.argv[1:], "h:", "shellfile=")
    except getopt.GetoptError:
        print cmd_line_help
        sys.exit(2)
    for opt, arg in cmd_line_options:
        if opt == '-h':
            print cmd_line_help
            sys.exit()
        elif opt == '--shellfile':
            cmd_line_shellfile = arg

    ## Logging ##
    log = logging.getLogger('base')
    log.setLevel(logging.DEBUG)
    # log.setLevel(logging.WARNING)
    formatter = logging.Formatter('[%(levelname)s][%(threadName)s] %(message)s')
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    log.addHandler(handler)

    ## Version
    version = 8.4
    version_date = "2015/10"

    ## URL for update checks and statistics
    version_url = "http://flatcam.org/version"

    ## App URL
    app_url = "http://flatcam.org"

    ## Manual URL
    manual_url = "http://flatcam.org/manual/index.html"

    ## Signals
    inform = QtCore.pyqtSignal(str)  # Message
    worker_task = QtCore.pyqtSignal(dict)  # Worker task
    file_opened = QtCore.pyqtSignal(str, str)  # File type and filename
    progress = QtCore.pyqtSignal(int)  # Percentage of progress
    plots_updated = QtCore.pyqtSignal()

    # Emitted by new_object() and passes the new object as argument.
    # on_object_created() adds the object to the collection,
    # and emits new_object_available.
    object_created = QtCore.pyqtSignal(object)

    # Emitted when a new object has been added to the collection
    # and is ready to be used.
    new_object_available = QtCore.pyqtSignal(object)
    message = QtCore.pyqtSignal(str, str, str)

    def __init__(self):
        """
        Starts the application. Takes no parameters.

        :return: app
        :rtype: App
        """

        App.log.info("FlatCAM Starting...")

        ###################
        ### OS-specific ###
        ###################

        if sys.platform == 'win32':
            from win32com.shell import shell, shellcon
            App.log.debug("Win32!")
            self.data_path = shell.SHGetFolderPath(0, shellcon.CSIDL_APPDATA, None, 0) + \
                '/FlatCAM'
            self.os = 'windows'
        else:  # Linux/Unix/MacOS
            self.data_path = os.path.expanduser('~') + \
                '/.FlatCAM'
            self.os = 'unix'

        ###############################
        ### Setup folders and files ###
        ###############################

        if not os.path.exists(self.data_path):
            os.makedirs(self.data_path)
            App.log.debug('Created data folder: ' + self.data_path)

        try:
            f = open(self.data_path + '/defaults.json')
            f.close()
        except IOError:
            App.log.debug('Creating empty defaults.json')
            f = open(self.data_path + '/defaults.json', 'w')
            json.dump({}, f)
            f.close()

        try:
            f = open(self.data_path + '/recent.json')
            f.close()
        except IOError:
            App.log.debug('Creating empty recent.json')
            f = open(self.data_path + '/recent.json', 'w')
            json.dump([], f)
            f.close()

        # Application directory. Chdir to it. Otherwise, trying to load
        # GUI icons will fail as thir path is relative.
        # This will fail under cx_freeze ...
        self.app_home = os.path.dirname(os.path.realpath(__file__))
        App.log.debug("Application path is " + self.app_home)
        App.log.debug("Started in " + os.getcwd())
        os.chdir(self.app_home)

        ####################
        ## Initialize GUI ##
        ####################

        QtCore.QObject.__init__(self)

        self.ui = FlatCAMGUI(self.version)
        self.connect(self.ui,
                     QtCore.SIGNAL("geomUpdate(int, int, int, int)"),
                     self.save_geometry)

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

        self.proc_container = FCVisibleProcessContainer(self.ui.activity_view)

        self.project_filename = None

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
            "gerber_combine_passes": self.defaults_form.gerber_group.combine_passes_cb,
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
            "excellon_spindlespeed": self.defaults_form.excellon_group.spindlespeed_entry,
            "geometry_plot": self.defaults_form.geometry_group.plot_cb,
            "geometry_cutz": self.defaults_form.geometry_group.cutz_entry,
            "geometry_travelz": self.defaults_form.geometry_group.travelz_entry,
            "geometry_feedrate": self.defaults_form.geometry_group.cncfeedrate_entry,
            "geometry_cnctooldia": self.defaults_form.geometry_group.cnctooldia_entry,
            "geometry_painttooldia": self.defaults_form.geometry_group.painttooldia_entry,
            "geometry_spindlespeed": self.defaults_form.geometry_group.cncspindlespeed_entry,
            "geometry_paintoverlap": self.defaults_form.geometry_group.paintoverlap_entry,
            "geometry_paintmargin": self.defaults_form.geometry_group.paintmargin_entry,
            "cncjob_plot": self.defaults_form.cncjob_group.plot_cb,
            "cncjob_tooldia": self.defaults_form.cncjob_group.tooldia_entry,
            "cncjob_prepend": self.defaults_form.cncjob_group.prepend_text,
            "cncjob_append": self.defaults_form.cncjob_group.append_text
        }

        self.defaults = LoudDict()
        self.defaults.set_change_callback(self.on_defaults_dict_change)  # When the dictionary changes.
        self.defaults.update({
            "serial": 0,
            "stats": {},
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
            "excellon_spindlespeed": None,
            "geometry_plot": True,
            "geometry_cutz": -0.002,
            "geometry_travelz": 0.1,
            "geometry_feedrate": 3.0,
            "geometry_cnctooldia": 0.016,
            "geometry_spindlespeed": None,
            "geometry_painttooldia": 0.07,
            "geometry_paintoverlap": 0.15,
            "geometry_paintmargin": 0.0,
            "cncjob_plot": True,
            "cncjob_tooldia": 0.016,
            "cncjob_prepend": "",
            "cncjob_append": "",

            # Persistence
            "last_folder": None,
            # Default window geometry
            "def_win_x": 100,
            "def_win_y": 100,
            "def_win_w": 1024,
            "def_win_h": 650,

            # Constants...
            "defaults_save_period_ms": 20000,   # Time between default saves.
            "shell_shape": [500, 300],          # Shape of the shell in pixels.
            "shell_at_startup": False,          # Show the shell at startup.
            "recent_limit": 10,                 # Max. items in recent list.
            "fit_key": '1',
            "zoom_out_key": '2',
            "zoom_in_key": '3',
            "zoom_ratio": 1.5,
            "point_clipboard_format": "(%.4f, %.4f)",
            "zdownrate": None,
            "excellon_zeros": "L",
            "gerber_use_buffer_for_union": True,
            "cncjob_coordinate_format": "X%.4fY%.4f"
        })

        ###############################
        ### Load defaults from file ###
        self.load_defaults()

        chars = 'abcdefghijklmnopqrstuvwxyz0123456789'
        if self.defaults['serial'] == 0 or len(str(self.defaults['serial'])) < 10:
            self.defaults['serial'] = ''.join([random.choice(chars) for i in range(20)])
            self.save_defaults(silent=True)

        self.propagate_defaults()
        self.restore_main_win_geom()

        def auto_save_defaults():
            try:
                self.save_defaults(silent=True)
            finally:
                QtCore.QTimer.singleShot(self.defaults["defaults_save_period_ms"], auto_save_defaults)

        QtCore.QTimer.singleShot(self.defaults["defaults_save_period_ms"], auto_save_defaults)

        self.options_form = GlobalOptionsUI()
        self.options_form_fields = {
            "units": self.options_form.units_radio,
            "gerber_plot": self.options_form.gerber_group.plot_cb,
            "gerber_solid": self.options_form.gerber_group.solid_cb,
            "gerber_multicolored": self.options_form.gerber_group.multicolored_cb,
            "gerber_isotooldia": self.options_form.gerber_group.iso_tool_dia_entry,
            "gerber_isopasses": self.options_form.gerber_group.iso_width_entry,
            "gerber_isooverlap": self.options_form.gerber_group.iso_overlap_entry,
            "gerber_combine_passes": self.options_form.gerber_group.combine_passes_cb,
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
            "excellon_spindlespeed": self.options_form.excellon_group.spindlespeed_entry,
            "geometry_plot": self.options_form.geometry_group.plot_cb,
            "geometry_cutz": self.options_form.geometry_group.cutz_entry,
            "geometry_travelz": self.options_form.geometry_group.travelz_entry,
            "geometry_feedrate": self.options_form.geometry_group.cncfeedrate_entry,
            "geometry_spindlespeed": self.options_form.geometry_group.cncspindlespeed_entry,
            "geometry_cnctooldia": self.options_form.geometry_group.cnctooldia_entry,
            "geometry_painttooldia": self.options_form.geometry_group.painttooldia_entry,
            "geometry_paintoverlap": self.options_form.geometry_group.paintoverlap_entry,
            "geometry_paintmargin": self.options_form.geometry_group.paintmargin_entry,
            "cncjob_plot": self.options_form.cncjob_group.plot_cb,
            "cncjob_tooldia": self.options_form.cncjob_group.tooldia_entry,
            "cncjob_prepend": self.options_form.cncjob_group.prepend_text,
            "cncjob_append": self.options_form.cncjob_group.append_text
        }

        self.options = LoudDict()
        self.options.set_change_callback(self.on_options_dict_change)
        self.options.update({
            "units": "IN",
            "gerber_plot": True,
            "gerber_solid": True,
            "gerber_multicolored": False,
            "gerber_isotooldia": 0.016,
            "gerber_isopasses": 1,
            "gerber_isooverlap": 0.15,
            "gerber_combine_passes": True,
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
            "excellon_spindlespeed": None,
            "geometry_plot": True,
            "geometry_cutz": -0.002,
            "geometry_travelz": 0.1,
            "geometry_feedrate": 3.0,
            "geometry_spindlespeed": None,
            "geometry_cnctooldia": 0.016,
            "geometry_painttooldia": 0.07,
            "geometry_paintoverlap": 0.15,
            "geometry_paintmargin": 0.0,
            "cncjob_plot": True,
            "cncjob_tooldia": 0.016,
            "cncjob_prepend": "",
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
        App.log.info("Checking for updates in backgroud (this is version %s)." % str(self.version))

        self.worker2 = Worker(self, name="worker2")
        self.thr2 = QtCore.QThread()
        self.worker2.moveToThread(self.thr2)
        self.connect(self.thr2, QtCore.SIGNAL("started()"), self.worker2.run)
        self.connect(self.thr2, QtCore.SIGNAL("started()"),
                     lambda: self.worker_task.emit({'fcn': self.version_check,
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
        self.ui.menueditnew.triggered.connect(lambda: self.new_object('geometry', 'New Geometry', lambda x, y: None))
        self.ui.menueditedit.triggered.connect(self.edit_geometry)
        self.ui.menueditok.triggered.connect(self.editor2geometry)
        self.ui.menueditjoin.triggered.connect(self.on_edit_join)
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
        self.ui.menuhelp_home.triggered.connect(lambda: webbrowser.open(self.app_url))
        self.ui.menuhelp_manual.triggered.connect(lambda: webbrowser.open(self.manual_url))
        # Toolbar
        self.ui.zoom_fit_btn.triggered.connect(self.on_zoom_fit)
        self.ui.zoom_in_btn.triggered.connect(lambda: self.plotcanvas.zoom(1.5))
        self.ui.zoom_out_btn.triggered.connect(lambda: self.plotcanvas.zoom(1 / 1.5))
        self.ui.clear_plot_btn.triggered.connect(self.plotcanvas.clear)
        self.ui.replot_btn.triggered.connect(self.on_toolbar_replot)
        self.ui.newgeo_btn.triggered.connect(lambda: self.new_object('geometry', 'New Geometry', lambda x, y: None))
        self.ui.editgeo_btn.triggered.connect(self.edit_geometry)
        self.ui.updategeo_btn.triggered.connect(self.editor2geometry)
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
        # Sets up FlatCAMObj, FCProcess and FCProcessContainer.
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

        self.draw = FlatCAMDraw(self, disabled=True)

        #############
        ### Shell ###
        #############
        # TODO: Move this to its own class

        self.shell = FCShell(self)
        self.shell.setWindowIcon(self.ui.app_icon)
        self.shell.setWindowTitle("FlatCAM Shell")
        if self.defaults["shell_at_startup"]:
            self.shell.show()
        self.shell.resize(*self.defaults["shell_shape"])
        self.shell.append_output("FlatCAM %s\n(c) 2014-2015 Juan Pablo Caram\n\n" % self.version)
        self.shell.append_output("Type help to get started.\n\n")
        self.tcl = Tkinter.Tcl()
        self.setup_shell()

        if self.cmd_line_shellfile:
            try:
                with open(self.cmd_line_shellfile, "r") as myfile:
                    cmd_line_shellfile_text = myfile.read()
                    self.shell._sysShell.exec_command(cmd_line_shellfile_text)
            except Exception as ext:
                print "ERROR: ", ext
                sys.exit(2)

        App.log.debug("END of constructor. Releasing control.")

    def defaults_read_form(self):
        for option in self.defaults_form_fields:
            self.defaults[option] = self.defaults_form_fields[option].get_value()

    def defaults_write_form(self):
        for option in self.defaults:
            self.defaults_write_form_field(option)
            # try:
            #     self.defaults_form_fields[option].set_value(self.defaults[option])
            # except KeyError:
            #     #self.log.debug("defaults_write_form(): No field for: %s" % option)
            #     # TODO: Rethink this?
            #     pass

    def defaults_write_form_field(self, field):
        try:
            self.defaults_form_fields[field].set_value(self.defaults[field])
        except KeyError:
            #self.log.debug("defaults_write_form(): No field for: %s" % option)
            # TODO: Rethink this?
            pass

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

    def edit_geometry(self):
        """
        Send the current geometry object (if any) into the editor.

        :return: None
        """
        if not isinstance(self.collection.get_active(), FlatCAMGeometry):
            self.info("Select a Geometry Object to edit.")
            return

        self.ui.updategeo_btn.setEnabled(True)

        self.draw.edit_fcgeometry(self.collection.get_active())

    def editor2geometry(self):
        """
        Transfers the geometry in the editor to the current geometry object.

        :return: None
        """
        geo = self.collection.get_active()
        if not isinstance(geo, FlatCAMGeometry):
            self.info("Select a Geometry Object to update.")
            return

        self.draw.update_fcgeometry(geo)
        self.draw.deactivate()

        self.ui.updategeo_btn.setEnabled(False)

        geo.plot()

    def get_last_folder(self):
        return self.defaults["last_folder"]

    def report_usage(self, resource):
        """
        Increments usage counter for the given resource
        in self.defaults['stats'].

        :param resource: Name of the resource.
        :return: None
        """

        if resource in self.defaults['stats']:
            self.defaults['stats'][resource] += 1
        else:
            self.defaults['stats'][resource] = 1

    def exec_command(self, text):
        """
        Handles input from the shell. See FlatCAMApp.setup_shell for shell commands.

        :param text: Input command
        :return: None
        """
        self.report_usage('exec_command')

        text = str(text)

        try:
            result = self.tcl.eval(str(text))
            self.shell.append_output(result + '\n')
        except Tkinter.TclError, e:
            self.shell.append_error('ERROR: ' + str(e) + '\n')
        return

        """
        Code below is unsused. Saved for later.
        """

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
            if len(parts) - 1 > 0:
                retval = cmdfcn(*[cmdconv[i](parts[i + 1]) for i in range(len(parts)-1)])
            else:
                retval = cmdfcn()
            retfcn = commands[parts[0]]["retfcn"]
            if retval and retfcn(retval):
                self.shell.append_output(retfcn(retval) + "\n")

        except Exception, e:
            #self.shell.append_error(''.join(traceback.format_exc()))
            #self.shell.append_error("?\n")
            self.shell.append_error(str(e) + "\n")

    def info(self, msg):
        """
        Writes on the status bar.

        :param msg: Text to write.
        :return: None
        """
        match = re.search("\[([^\]]+)\](.*)", msg)
        if match:
            self.ui.fcinfo.set_status(QtCore.QString(match.group(2)), level=match.group(1))
        else:
            self.ui.fcinfo.set_status(QtCore.QString(msg), level="info")

    def load_defaults(self):
        """
        Loads the aplication's default settings from defaults.json into
        ``self.defaults``.

        :return: None
        """
        try:
            f = open(self.data_path + "/defaults.json")
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

    def save_geometry(self, x, y, width, height):
        self.defaults["def_win_x"] = x
        self.defaults["def_win_y"] = y
        self.defaults["def_win_w"] = width
        self.defaults["def_win_h"] = height
        self.save_defaults()

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

        if len(self.recent) > self.defaults['recent_limit']:  # Limit reached
            self.recent.pop()

        try:
            f = open(self.data_path + '/recent.json', 'w')
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

        t0 = time.time()  # Debug

        ### Check for existing name
        # while name in self.collection.get_names():
        #     ## Create a new name
        #     # Ends with number?
        #     App.log.debug("new_object(): Object name (%s) exists, changing." % name)
        #     match = re.search(r'(.*[^\d])?(\d+)$', name)
        #     if match:  # Yes: Increment the number!
        #         base = match.group(1) or ''
        #         num = int(match.group(2))
        #         name = base + str(num + 1)
        #     else:  # No: add a number!
        #         name += "_1"

        ## Create object
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
                oname = option[len(kind) + 1:]
                obj.options[oname] = self.options[option]

        # Initialize as per user request
        # User must take care to implement initialize
        # in a thread-safe way as is is likely that we
        # have been invoked in a separate thread.
        t1 = time.time()
        self.log.debug("%f seconds before initialize()." % (t1 - t0))
        initialize(obj, self)
        t2 = time.time()
        self.log.debug("%f seconds executing initialize()." % (t2 - t1))

        # Check units and convert if necessary
        # This condition CAN be true because initialize() can change obj.units
        if self.options["units"].upper() != obj.units.upper():
            self.inform.emit("Converting units to " + self.options["units"] + ".")
            obj.convert_units(self.options["units"])
            t3 = time.time()
            self.log.debug("%f seconds converting units." % (t3 - t2))

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
            self.options_write_form_field(option)

    def options_write_form_field(self, field):
        try:
            self.options_form_fields[field].set_value(self.options[field])
        except KeyError:
            # Changed from error to debug. This allows to have data stored
            # which is not user-editable.
            self.log.debug("options_write_form_field(): No field for: %s" % field)

    def on_about(self):
        """
        Displays the "about" dialog.

        :return: None
        """
        self.report_usage("on_about")

        version = self.version
        version_date = self.version_date

        class AboutDialog(QtGui.QDialog):
            def __init__(self, parent=None):
                QtGui.QDialog.__init__(self, parent)

                # Icon and title
                self.setWindowIcon(parent.app_icon)
                self.setWindowTitle("FlatCAM")

                layout1 = QtGui.QVBoxLayout()
                self.setLayout(layout1)

                layout2 = QtGui.QHBoxLayout()
                layout1.addLayout(layout2)

                logo = QtGui.QLabel()
                logo.setPixmap(QtGui.QPixmap('share/flatcam_icon256.png'))
                layout2.addWidget(logo, stretch=0)

                title = QtGui.QLabel(
                    "<font size=8><B>FlatCAM</B></font><BR>"
                    "Version %s (%s)<BR>"
                    "<BR>"
                    "2D Computer-Aided Printed Circuit Board<BR>"
                    "Manufacturing.<BR>"
                    "<BR>"
                    "(c) 2014-2015 Juan Pablo Caram" % (version, version_date)
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

        self.save_defaults()

    def save_defaults(self, silent=False):
        """
        Saves application default options
        ``self.defaults`` to defaults.json.

        :return: None
        """

        self.report_usage("save_defaults")

        ## Read options from file ##
        try:
            f = open(self.data_path + "/defaults.json")
            options = f.read()
            f.close()
        except:
            e = sys.exc_info()[0]
            App.log.error("Could not load defaults file.")
            App.log.error(str(e))
            self.inform.emit("[error] Could not load defaults file.")
            return

        try:
            defaults = json.loads(options)
        except:
            e = sys.exc_info()[0]
            App.log.error("Failed to parse defaults file.")
            App.log.error(str(e))
            self.inform.emit("[error] Failed to parse defaults file.")
            return

        # Update options
        self.defaults_read_form()
        defaults.update(self.defaults)

        # Save update options
        try:
            f = open(self.data_path + "/defaults.json", "w")
            json.dump(defaults, f)
            f.close()
        except:
            self.inform.emit("[error] Failed to write defaults to file.")
            return

        if not silent:
            self.inform.emit("Defaults saved.")

    def on_edit_join(self):
        """
        Callback for Edit->Join. Joins the selected geometry objects into
        a new one.

        :return: None
        """
        objs = self.collection.get_selected()

        def initialize(obj, app):
            FlatCAMGeometry.merge(objs, obj)

        self.new_object("geometry", "Combo", initialize)

    def on_options_app2project(self):
        """
        Callback for Options->Transfer Options->App=>Project. Copies options
        from application defaults to project defaults.

        :return: None
        """

        self.report_usage("on_options_app2project")

        self.defaults_read_form()
        self.options.update(self.defaults)
        self.options_write_form()

    def on_options_project2app(self):
        """
        Callback for Options->Transfer Options->Project=>App. Copies options
        from project defaults to application defaults.

        :return: None
        """

        self.report_usage("on_options_project2app")

        self.options_read_form()
        self.defaults.update(self.options)
        self.defaults_write_form()

    def on_options_project2object(self):
        """
        Callback for Options->Transfer Options->Project=>Object. Copies options
        from project defaults to the currently selected object.

        :return: None
        """

        self.report_usage("on_options_project2object")

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

        self.report_usage("on_options_object2project")

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

        self.report_usage("on_options_object2app")

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

        self.report_usage("on_options_app2object")

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

    def on_options_dict_change(self, field):
        self.options_write_form_field(field)

        if field == "units":
            self.set_screen_units(self.options['units'])

    def on_defaults_dict_change(self, field):
        self.defaults_write_form_field(field)

    def set_screen_units(self, units):
        self.ui.units_label.setText("[" + self.options["units"].lower() + "]")

    def on_toggle_units(self):
        """
        Callback for the Units radio-button change in the Options tab.
        Changes the application's default units or the current project's units.
        If changing the project's units, the change propagates to all of
        the objects in the project.

        :return: None
        """

        self.report_usage("on_toggle_units")

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
        #self.ui.units_label.setText("[" + self.options["units"] + "]")
        self.set_screen_units(self.options["units"])

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
        Delete the currently selected FlatCAMObjs.

        :return: None
        """

        self.log.debug("on_delete()")
        self.report_usage("on_delete")

        while (self.collection.get_active()):
            self.delete_first_selected()
 

    def delete_first_selected(self):
        # Keep this for later
        try:
            name = self.collection.get_active().options["name"]
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
        """
        Callback used to report when the plots have changed.
        Adjust axes and zooms to fit.

        :return: None
        """
        self.plotcanvas.auto_adjust_axes()
        self.on_zoom_fit(None)

    def on_toolbar_replot(self):
        """
        Callback for toolbar button. Re-plots all objects.

        :return: None
        """

        self.report_usage("on_toolbar_replot")
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
        """
        Event callback for object creation.

        :param obj: The newly created FlatCAM object.
        :return: None
        """
        t0 = time.time()  # DEBUG
        self.log.debug("on_object_created()")

        # The Collection might change the name if there is a collision
        self.collection.append(obj)

        self.inform.emit("Object (%s) created: %s" % (obj.kind, obj.options['name']))
        self.new_object_available.emit(obj)
        obj.plot()
        self.on_zoom_fit(None)
        t1 = time.time()  # DEBUG
        self.log.debug("%f seconds adding object and plotting." % (t1 - t0))

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

        if event.key == self.defaults['fit_key']:  # 1
            self.on_zoom_fit(None)
            return

        if event.key == self.defaults['zoom_out_key']:  # 2
            self.plotcanvas.zoom(1 / self.defaults['zoom_ratio'], self.mouse)
            return

        if event.key == self.defaults['zoom_in_key']:  # 3
            self.plotcanvas.zoom(self.defaults['zoom_ratio'], self.mouse)
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

            self.clipboard.setText(self.defaults["point_clipboard_format"] % (event.xdata, event.ydata))

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

        self.report_usage("on_file_new")

        # Remove everything from memory
        App.log.debug("on_file_new()")

        self.plotcanvas.clear()

        self.collection.delete_all()

        self.setup_component_editor()

        # Clear project filename
        self.project_filename = None

        # Re-fresh project options
        self.on_options_app2project()

    def on_fileopengerber(self):
        """
        File menu callback for opening a Gerber.

        :return: None
        """

        self.report_usage("on_fileopengerber")
        App.log.debug("on_fileopengerber()")

        try:
            filename = QtGui.QFileDialog.getOpenFileName(caption="Open Gerber",
                                                         directory=self.get_last_folder())
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
        """
        File menu callback for opening an Excellon file.

        :return: None
        """

        self.report_usage("on_fileopenexcellon")
        App.log.debug("on_fileopenexcellon()")

        try:
            filename = QtGui.QFileDialog.getOpenFileName(caption="Open Excellon",
                                                         directory=self.get_last_folder())
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
        """
        File menu call back for opening gcode.

        :return: None
        """

        self.report_usage("on_fileopengcode")
        App.log.debug("on_fileopengcode()")

        try:
            filename = QtGui.QFileDialog.getOpenFileName(caption="Open G-Code",
                                                         directory=self.get_last_folder())
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
        """
        File menu callback for opening a project.

        :return: None
        """

        self.report_usage("on_file_openproject")
        App.log.debug("on_file_openproject()")

        try:
            filename = QtGui.QFileDialog.getOpenFileName(caption="Open Project",
                                                         directory=self.get_last_folder())
        except TypeError:
            filename = QtGui.QFileDialog.getOpenFileName(caption="Open Project")

        # The Qt methods above will return a QString which can cause problems later.
        # So far json.dump() will fail to serialize it.
        # TODO: Improve the serialization methods and remove this fix.
        filename = str(filename)

        if str(filename) == "":
            self.inform.emit("Open cancelled.")
        else:
            # self.worker_task.emit({'fcn': self.open_project,
            #                        'params': [filename]})
            # The above was failing because open_project() is not
            # thread safe. The new_project()
            self.open_project(filename)

    def on_file_saveproject(self):
        """
        Callback for menu item File->Save Project. Saves the project to
        ``self.project_filename`` or calls ``self.on_file_saveprojectas()``
        if set to None. The project is saved by calling ``self.save_project()``.

        :return: None
        """

        self.report_usage("on_file_saveproject")

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

        self.report_usage("on_file_saveprojectas")

        try:
            filename = QtGui.QFileDialog.getSaveFileName(caption="Save Project As ...",
                                                         directory=self.get_last_folder())
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

    def open_gerber(self, filename, follow=False, outname=None):
        """
        Opens a Gerber file, parses it and creates a new object for
        it in the program. Thread-safe.

        :param filename: Gerber file filename
        :type filename: str
        :param follow: If true, the parser will not create polygons, just lines
            following the gerber path.
        :type follow: bool
        :return: None
        """

        # How the object should be initialized
        def obj_init(gerber_obj, app_obj):
            assert isinstance(gerber_obj, FlatCAMGerber)
            #log.debug("sys.getrefcount(proc) == %d" % sys.getrefcount(proc))

            # Opening the file happens here
            self.progress.emit(30)
            try:
                gerber_obj.parse_file(filename, follow=follow)
            except IOError:
                app_obj.inform.emit("[error] Failed to open file: " + filename)
                app_obj.progress.emit(0)
                raise IOError('Failed to open file: ' + filename)
            except ParseError, e:
                app_obj.inform.emit("[error] Failed to parse file: " + filename)
                app_obj.progress.emit(0)
                self.log.error(str(e))
                raise
                #return

            # Further parsing
            self.progress.emit(70)  # TODO: Note the mixture of self and app_obj used here

        App.log.debug("open_gerber()")

        with self.proc_container.new("Opening Gerber") as proc:

            self.progress.emit(10)

            # Object name
            name = outname or filename.split('/')[-1].split('\\')[-1]

            ### Object creation ###
            self.new_object("gerber", name, obj_init)

            # Register recent file
            self.file_opened.emit("gerber", filename)

            self.progress.emit(100)
            #proc.done()

            # GUI feedback
            self.inform.emit("Opened: " + filename)

    def open_excellon(self, filename, outname=None):
        """
        Opens an Excellon file, parses it and creates a new object for
        it in the program. Thread-safe.

        :param filename: Excellon file filename
        :type filename: str
        :return: None
        """

        App.log.debug("open_excellon()")

        #self.progress.emit(10)

        # How the object should be initialized
        def obj_init(excellon_obj, app_obj):
            #self.progress.emit(20)

            try:
                excellon_obj.parse_file(filename)
            except IOError:
                app_obj.inform.emit("[error] Cannot open file: " + filename)
                self.progress.emit(0)  # TODO: self and app_bjj mixed
                raise IOError("Cannot open file: " + filename)

            try:
                excellon_obj.create_geometry()
            except Exception as e:
                app_obj.inform.emit("[error] Failed to create geometry after parsing: " + filename)
                self.progress.emit(0)
                raise e

            #self.progress.emit(70)

        with self.proc_container.new("Opening Excellon."):

            # Object name
            name = outname or filename.split('/')[-1].split('\\')[-1]

            self.new_object("excellon", name, obj_init)

            # Register recent file
            self.file_opened.emit("excellon", filename)

            # GUI feedback
            self.inform.emit("Opened: " + filename)
            #self.progress.emit(100)

    def open_gcode(self, filename, outname=None):
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

            try:
                f = open(filename)
                gcode = f.read()
                f.close()
            except IOError:
                app_obj_.inform.emit("[error] Failed to open " + filename)
                self.progress.emit(0)
                raise IOError("Failed to open " + filename)

            job_obj.gcode = gcode

            self.progress.emit(20)
            job_obj.gcode_parse()

            self.progress.emit(60)
            job_obj.create_geometry()

        with self.proc_container.new("Opening G-Code."):

            # Object name
            name = outname or filename.split('/')[-1].split('\\')[-1]

            # New object creation and file processing
            try:
                self.new_object("cncjob", name, obj_init)
            except Exception as e:
                # e = sys.exc_info()
                App.log.error(str(e))
                self.message_dialog("Failed to create CNCJob Object",
                                    "Attempting to create a FlatCAM CNCJob Object from " +
                                    "G-Code file failed during processing:\n" +
                                    str(e[0]) + " " + str(e[1]), kind="error")
                self.progress.emit(0)
                self.collection.delete_active()
                raise e

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

        ## Open and parse
        try:
            f = open(filename, 'r')
        except IOError:
            App.log.error("Failed to open project file: %s" % filename)
            self.inform.emit("[error] Failed to open project file: %s" % filename)
            return

        try:
            d = json.load(f, object_hook=dict2obj)
        except:
            App.log.error("Failed to parse project file: %s" % filename)
            self.inform.emit("[error] Failed to parse project file: %s" % filename)
            f.close()
            return

        self.file_opened.emit("project", filename)

        ## Clear the current project
        ## NOT THREAD SAFE ##
        self.on_file_new()

        ##Project options
        self.options.update(d['options'])
        self.project_filename = filename
        #self.ui.units_label.setText("[" + self.options["units"] + "]")
        self.set_screen_units(self.options["units"])

        ## Re create objects
        App.log.debug("Re-creating objects...")
        for obj in d['objs']:
            def obj_init(obj_inst, app_inst):
                obj_inst.from_dict(obj)
            App.log.debug(obj['kind'] + ":  " + obj['options']['name'])
            self.new_object(obj['kind'], obj['options']['name'], obj_init, active=False, fit=False, plot=False)

        self.plot_all()
        self.inform.emit("Project loaded from: " + filename)
        App.log.debug("Project loaded")

    def propagate_defaults(self):
        """
        This method is used to set default values in classes. It's
        an alternative to project options but allows the use
        of values invisible to the user.

        :return: None
        """

        self.log.debug("propagate_defaults()")

        # Which objects to update the given parameters.
        routes = {
            "zdownrate": CNCjob,
            "excellon_zeros": Excellon,
            "gerber_use_buffer_for_union": Gerber,
            "cncjob_coordinate_format": CNCjob
            # "spindlespeed": CNCjob
        }

        for param in routes:
            if param in routes[param].defaults:
                try:
                    routes[param].defaults[param] = self.defaults[param]
                    self.log.debug("  " + param + " OK")
                except KeyError:
                    self.log.debug("  ERROR: " + param + " not in defaults.")
            else:
                # Try extracting the name:
                # classname_param here is param in the object
                if param.find(routes[param].__name__.lower() + "_") == 0:
                    p = param[len(routes[param].__name__) + 1:]
                    if p in routes[param].defaults:
                        routes[param].defaults[p] = self.defaults[param]
                        self.log.debug("  " + param + " OK!")

    def restore_main_win_geom(self):
        self.ui.setGeometry(self.defaults["def_win_x"],
                            self.defaults["def_win_y"],
                            self.defaults["def_win_w"],
                            self.defaults["def_win_h"])

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
        self.defaults["last_folder"] = os.path.split(str(filename))[0]

    def set_progress_bar(self, percentage, text=""):
        self.ui.progress_bar.setValue(int(percentage))

    def setup_shell(self):
        """
        Creates shell functions. Runs once at startup.

        :return: None
        """

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

        def h(*args):
            """
            Pre-processes arguments to detect '-keyword value' pairs into dictionary
            and standalone parameters into list.
            """

            kwa = {}
            a = []
            n = len(args)
            name = None
            for i in range(n):
                match = re.search(r'^-([a-zA-Z].*)', args[i])
                if match:
                    assert name is None
                    name = match.group(1)
                    continue

                if name is None:
                    a.append(args[i])
                else:
                    kwa[name] = args[i]
                    name = None

            return a, kwa

        def open_gerber(filename, *args):
            a, kwa = h(*args)
            types = {'follow': bool,
                     'outname': str}

            for key in kwa:
                if key not in types:
                    return 'Unknown parameter: %s' % key
                kwa[key] = types[key](kwa[key])

            self.open_gerber(str(filename), **kwa)

        def open_excellon(filename, *args):
            a, kwa = h(*args)
            types = {'outname': str}

            for key in kwa:
                if key not in types:
                    return 'Unknown parameter: %s' % key
                kwa[key] = types[key](kwa[key])

            self.open_excellon(str(filename), **kwa)

        def open_gcode(filename, *args):
            a, kwa = h(*args)
            types = {'outname': str}

            for key in kwa:
                if key not in types:
                    return 'Unknown parameter: %s' % key
                kwa[key] = types[key](kwa[key])

            self.open_gcode(str(filename), **kwa)

        def cutout(name, *args):
            a, kwa = h(*args)
            types = {'dia': float,
                     'margin': float,
                     'gapsize': float,
                     'gaps': str}

            for key in kwa:
                if key not in types:
                    return 'Unknown parameter: %s' % key
                kwa[key] = types[key](kwa[key])

            try:
                obj = self.collection.get_by_name(str(name))
            except:
                return "Could not retrieve object: %s" % name

            def geo_init_me(geo_obj, app_obj):
                margin = kwa['margin']+kwa['dia']/2
                gap_size = kwa['dia']+kwa['gapsize']
                minx, miny, maxx, maxy = obj.bounds()
                minx -= margin
                maxx += margin
                miny -= margin
                maxy += margin
                midx = 0.5 * (minx + maxx)
                midy = 0.5 * (miny + maxy)
                hgap = 0.5 * gap_size
                pts = [[midx - hgap, maxy],
                       [minx, maxy],
                       [minx, midy + hgap],
                       [minx, midy - hgap],
                       [minx, miny],
                       [midx - hgap, miny],
                       [midx + hgap, miny],
                       [maxx, miny],
                       [maxx, midy - hgap],
                       [maxx, midy + hgap],
                       [maxx, maxy],
                       [midx + hgap, maxy]]
                cases = {"tb": [[pts[0], pts[1], pts[4], pts[5]],
                                [pts[6], pts[7], pts[10], pts[11]]],
                         "lr": [[pts[9], pts[10], pts[1], pts[2]],
                                [pts[3], pts[4], pts[7], pts[8]]],
                         "4": [[pts[0], pts[1], pts[2]],
                               [pts[3], pts[4], pts[5]],
                               [pts[6], pts[7], pts[8]],
                               [pts[9], pts[10], pts[11]]]}
                cuts = cases[kwa['gaps']]
                geo_obj.solid_geometry = cascaded_union([LineString(segment) for segment in cuts])

            try:
                obj.app.new_object("geometry", name + "_cutout", geo_init_me)
            except Exception, e:
                return "Operation failed: %s" % str(e)

            return 'Ok'

        def mirror(name, *args):
            a, kwa = h(*args)
            types = {'box': str,
                     'axis': str,
                     'dist': float}

            for key in kwa:
                if key not in types:
                    return 'Unknown parameter: %s' % key
                kwa[key] = types[key](kwa[key])

            # Get source object.
            try:
                obj = self.collection.get_by_name(str(name))
            except:
                return "Could not retrieve object: %s" % name

            if obj is None:
                return "Object not found: %s" % name

            if not isinstance(obj, FlatCAMGerber) and not isinstance(obj, FlatCAMExcellon):
                return "ERROR: Only Gerber and Excellon objects can be mirrored."


            # Axis
            try:
                axis = kwa['axis'].upper()
            except KeyError:
                return "ERROR: Specify -axis X or -axis Y"


            # Box
            if 'box' in kwa:
                try:
                    box = self.collection.get_by_name(kwa['box'])
                except:
                    return "Could not retrieve object box: %s" % kwa['box']

                if box is None:
                    return "Object box not found: %s" % kwa['box']

                try:
                    xmin, ymin, xmax, ymax = box.bounds()
                    px = 0.5 * (xmin + xmax)
                    py = 0.5 * (ymin + ymax)

                    obj.mirror(axis, [px, py])
                    obj.plot()

                except Exception, e:
                    return "Operation failed: %s" % str(e)

            else:
                try:
                    dist = float(kwa['dist'])
                except KeyError:
                    dist = 0.0
                except ValueError:
                    return "Invalid distance: %s" % kwa['dist']

                try:
                    obj.mirror(axis, [dist, dist])
                    obj.plot()
                except Exception, e:
                    return "Operation failed: %s" % str(e)

            return 'Ok'

        def drillcncjob(name, *args):
            a, kwa = h(*args)
            types = {'tools': str,
                     'outname': str,
                     'drillz': float,
                     'travelz': float,
                     'feedrate': float,
                     'spindlespeed': int,
                     'toolchange': int
                     }

            for key in kwa:
                if key not in types:
                    return 'Unknown parameter: %s' % key
                kwa[key] = types[key](kwa[key])

            try:
                obj = self.collection.get_by_name(str(name))
            except:
                return "Could not retrieve object: %s" % name

            if obj is None:
                return "Object not found: %s" % name

            if not isinstance(obj, FlatCAMExcellon):
                return "ERROR: Only Excellon objects can be drilled."

            try:
              
                # Get the tools from the list
                job_name = kwa["outname"]
        
                # Object initialization function for app.new_object()
                def job_init(job_obj, app_obj):
                    assert isinstance(job_obj, FlatCAMCNCjob)
                    
                    job_obj.z_cut = kwa["drillz"]
                    job_obj.z_move = kwa["travelz"]
                    job_obj.feedrate = kwa["feedrate"]
                    job_obj.spindlespeed = kwa["spindlespeed"] if "spindlespeed" in kwa else None
                    toolchange = True if "toolchange" in kwa and kwa["toolchange"] == 1 else False
                    job_obj.generate_from_excellon_by_tool(obj, kwa["tools"], toolchange)
                    
                    job_obj.gcode_parse()
                    
                    job_obj.create_geometry()
        
                obj.app.new_object("cncjob", job_name, job_init)

            except Exception, e:
                return "Operation failed: %s" % str(e)

            return 'Ok'

        def drillmillgeometry(name, *args):
            a, kwa = h(*args)
            types = {'tooldia': float,
                     'tools': str,
                     'outname': str}

            for key in kwa:
                if key not in types:
                    return 'Unknown parameter: %s' % key
                kwa[key] = types[key](kwa[key])

            try:
                if 'tools' in kwa:
                    kwa['tools'] = [x.strip() for x in kwa['tools'].split(",")]
            except Exception as e:
                return "Bad tools: %s" % str(e)

            try:
                obj = self.collection.get_by_name(str(name))
            except:
                return "Could not retrieve object: %s" % name

            if obj is None:
                return "Object not found: %s" % name

            assert isinstance(obj, FlatCAMExcellon)

            try:
                success, msg = obj.generate_milling(**kwa)
            except Exception as e:
                return "Operation failed: %s" % str(e)

            if not success:
                return msg

            return 'Ok'

        def exteriors(obj_name, *args):
            a, kwa = h(*args)
            types = {'outname': str}

            for key in kwa:
                if key not in types:
                    return 'Unknown parameter: %s' % key
                kwa[key] = types[key](kwa[key])

            try:
                obj = self.collection.get_by_name(str(obj_name))
            except:
                return "Could not retrieve object: %s" % obj_name

            if obj is None:
                return "Object not found: %s" % obj_name

            assert isinstance(obj, Geometry)

            obj_exteriors = obj.get_exteriors()

            def geo_init(geo_obj, app_obj):
                geo_obj.solid_geometry = obj_exteriors

            if 'outname' in kwa:
                outname = kwa['outname']
            else:
                outname = obj_name + ".exteriors"

            try:
                self.new_object('geometry', outname, geo_init)
            except Exception as e:
                return "Failed: %s" % str(e)

            return 'Ok'

        def interiors(obj_name, *args):
            a, kwa = h(*args)
            types = {}

            for key in kwa:
                if key not in types:
                    return 'Unknown parameter: %s' % key
                kwa[key] = types[key](kwa[key])

            try:
                obj = self.collection.get_by_name(str(obj_name))
            except:
                return "Could not retrieve object: %s" % obj_name

            if obj is None:
                return "Object not found: %s" % obj_name

            assert isinstance(obj, Geometry)

            obj_interiors = obj.get_interiors()

            def geo_init(geo_obj, app_obj):
                geo_obj.solid_geometry = obj_interiors

            if 'outname' in kwa:
                outname = kwa['outname']
            else:
                outname = obj_name + ".interiors"

            try:
                self.new_object('geometry', outname, geo_init)
            except Exception as e:
                return "Failed: %s" % str(e)

            return 'Ok'

        def isolate(name, *args):
            a, kwa = h(*args)
            types = {'dia': float,
                     'passes': int,
                     'overlap': float,
                     'outname': str, 
                     'combine': int}

            for key in kwa:
                if key not in types:
                    return 'Unknown parameter: %s' % key
                kwa[key] = types[key](kwa[key])

            try:
                obj = self.collection.get_by_name(str(name))
            except:
                return "Could not retrieve object: %s" % name

            if obj is None:
                return "Object not found: %s" % name

            assert isinstance(obj, FlatCAMGerber)

            try:
                obj.isolate(**kwa)
            except Exception, e:
                return "Operation failed: %s" % str(e)

            return 'Ok'

        def cncjob(obj_name, *args):
            a, kwa = h(*args)

            types = {'z_cut': float,
                     'z_move': float,
                     'feedrate': float,
                     'tooldia': float,
                     'outname': str,
                     'spindlespeed': int
                     }

            for key in kwa:
                if key not in types:
                    return 'Unknown parameter: %s' % key
                kwa[key] = types[key](kwa[key])

            try:
                obj = self.collection.get_by_name(str(obj_name))
            except:
                return "Could not retrieve object: %s" % obj_name
            if obj is None:
                return "Object not found: %s" % obj_name

            try:
                obj.generatecncjob(**kwa)
            except Exception, e:
                return "Operation failed: %s" % str(e)

            return 'Ok'

        def write_gcode(obj_name, filename, preamble='', postamble=''):
            """
            Requires obj_name to be available. It might still be in the
            making at the time this function is called, so check for
            promises and send to background if there are promises.
            """

            # If there are promised objects, wait until all promises have been fulfilled.
            if self.collection.has_promises():

                def write_gcode_on_object(new_object):
                    self.log.debug("write_gcode_on_object(): Disconnecting %s" % write_gcode_on_object)
                    self.new_object_available.disconnect(write_gcode_on_object)
                    write_gcode(obj_name, filename, preamble, postamble)

                # Try again when a new object becomes available.
                self.log.debug("write_gcode(): Collection has promises. Queued for %s." % obj_name)
                self.log.debug("write_gcode(): Queued function: %s" % write_gcode_on_object)
                self.new_object_available.connect(write_gcode_on_object)

                return

            self.log.debug("write_gcode(): No promises. Continuing for %s." % obj_name)

            try:
                obj = self.collection.get_by_name(str(obj_name))
            except:
                return "Could not retrieve object: %s" % obj_name

            try:
                obj.export_gcode(str(filename), str(preamble), str(postamble))
            except Exception, e:
                return "Operation failed: %s" % str(e)

        def paint_poly(obj_name, inside_pt_x, inside_pt_y, tooldia, overlap):
            try:
                obj = self.collection.get_by_name(str(obj_name))
            except:
                return "Could not retrieve object: %s" % obj_name
            if obj is None:
                return "Object not found: %s" % obj_name
            obj.paint_poly([float(inside_pt_x), float(inside_pt_y)], float(tooldia), float(overlap))

        def add_poly(obj_name, *args):
            if len(args) % 2 != 0:
                return "Incomplete coordinate."

            points = [[float(args[2*i]), float(args[2*i+1])] for i in range(len(args)/2)]

            try:
                obj = self.collection.get_by_name(str(obj_name))
            except:
                return "Could not retrieve object: %s" % obj_name
            if obj is None:
                return "Object not found: %s" % obj_name

            obj.add_polygon(points)

        def add_rectangle(obj_name, botleft_x, botleft_y, topright_x, topright_y):
            return add_poly(obj_name, botleft_x, botleft_y, botleft_x, topright_y,
                            topright_x, topright_y, topright_x, botleft_y)

        def add_circle(obj_name, center_x, center_y, radius):
            try:
                obj = self.collection.get_by_name(str(obj_name))
            except:
                return "Could not retrieve object: %s" % obj_name
            if obj is None:
                return "Object not found: %s" % obj_name

            obj.add_circle([float(center_x), float(center_y)], float(radius))

        def set_active(obj_name):
            try:
                self.collection.set_active(str(obj_name))
            except Exception, e:
                return "Command failed: %s" % str(e)

        def delete(obj_name):
            try:
                self.collection.set_active(str(obj_name))
                self.on_delete()
            except Exception, e:
                return "Command failed: %s" % str(e)

        def geo_union(obj_name):

            try:
                obj = self.collection.get_by_name(str(obj_name))
            except:
                return "Could not retrieve object: %s" % obj_name
            if obj is None:
                return "Object not found: %s" % obj_name

            obj.union()

        def join_geometries(obj_name, *obj_names):
            objs = []
            for obj_n in obj_names:
                obj = self.collection.get_by_name(str(obj_n))
                if obj is None:
                    return "Object not found: %s" % obj_n
                else:
                    objs.append(obj)

            def initialize(obj, app):
                FlatCAMGeometry.merge(objs, obj)

            if objs is not None:
                self.new_object("geometry", obj_name, initialize)

        def make_docs():
            output = ''
            import collections
            od = collections.OrderedDict(sorted(commands.items()))
            for cmd, val in od.iteritems():
                #print cmd, '\n', ''.join(['~']*len(cmd))
                output += cmd + ' \n' + ''.join(['~'] * len(cmd)) + '\n'

                t = val['help']
                usage_i = t.find('>')
                if usage_i < 0:
                    expl = t
                    #print expl + '\n'
                    output += expl + '\n\n'
                    continue

                expl = t[:usage_i - 1]
                #print expl + '\n'
                output += expl + '\n\n'

                end_usage_i = t[usage_i:].find('\n')

                if end_usage_i < 0:
                    end_usage_i = len(t[usage_i:])
                    #print '    ' + t[usage_i:]
                    #print '       No parameters.\n'
                    output += '    ' + t[usage_i:] + '\n       No parameters.\n'
                else:
                    extras = t[usage_i+end_usage_i+1:]
                    parts = [s.strip() for s in extras.split('\n')]


                    #print '    ' + t[usage_i:usage_i+end_usage_i]
                    output += '    ' + t[usage_i:usage_i+end_usage_i] + '\n'
                    for p in parts:
                        #print '       ' + p + '\n'
                        output += '       ' + p + '\n\n'

            return output

        def follow(obj_name, *args):
            a, kwa = h(*args)

            types = {'outname': str}

            for key in kwa:
                if key not in types:
                    return 'Unknown parameter: %s' % key
                kwa[key] = types[key](kwa[key])

            try:
                obj = self.collection.get_by_name(str(obj_name))
            except:
                return "Could not retrieve object: %s" % obj_name
            if obj is None:
                return "Object not found: %s" % obj_name

            try:
                obj.follow(**kwa)
            except Exception, e:
                return "ERROR: %s" % str(e)

        def get_sys(param):
            if param in self.defaults:
                return self.defaults[param]

            return "ERROR: No such system parameter."

        def set_sys(param, value):
            # tcl string to python keywords:
            tcl2py = {
                "None": None,
                "none": None,
                "false": False,
                "False": False,
                "true": True,
                "True": True
            }

            if param in self.defaults:

                try:
                    value = tcl2py[value]
                except KeyError:
                    pass

                self.defaults[param] = value

                self.propagate_defaults()
                return "Ok"

            return "ERROR: No such system parameter."

        commands = {
            'help': {
                'fcn': shelp,
                'help': "Shows list of commands."
            },
            'open_gerber': {
                'fcn': open_gerber,
                'help': "Opens a Gerber file.\n' +"
                        "> open_gerber <filename> [-follow <0|1>] [-outname <o>]\n' +"
                        "   filename: Path to file to open.\n" +
                        "   follow: If 1, does not create polygons, just follows the gerber path.\n" +
                        "   outname: Name of the created gerber object."
            },
            'open_excellon': {
                'fcn': open_excellon,
                'help': "Opens an Excellon file.\n" +
                        "> open_excellon <filename> [-outname <o>]\n" +
                        "   filename: Path to file to open.\n" +
                        "   outname: Name of the created excellon object."
            },
            'open_gcode': {
                'fcn': open_gcode,
                'help': "Opens an G-Code file.\n" +
                        "> open_gcode <filename> [-outname <o>]\n" +
                        "   filename: Path to file to open.\n" +
                        "   outname: Name of the created CNC Job object."
            },
            'open_project': {
                'fcn': self.open_project,
                "help": "Opens a FlatCAM project.\n" +
                        "> open_project <filename>\n" +
                        "   filename: Path to file to open."
            },
            'save_project': {
                'fcn': self.save_project,
                'help': "Saves the FlatCAM project to file.\n" +
                        "> save_project <filename>\n" +
                        "   filename: Path to file to save."
            },
            'set_active': {
                'fcn': set_active,
                'help': "Sets a FlatCAM object as active.\n" +
                        "> set_active <name>\n" +
                        "   name: Name of the object."
            },
            'get_names': {
                'fcn': lambda: '\n'.join(self.collection.get_names()),
                'help': "Lists the names of objects in the project.\n" +
                        "> get_names"
            },
            'new': {
                'fcn': self.on_file_new,
                'help': "Starts a new project. Clears objects from memory.\n" +
                        "> new"
            },
            'options': {
                'fcn': options,
                'help': "Shows the settings for an object.\n" +
                        "> options <name>\n" +
                        "   name: Object name."
            },
            'isolate': {
                'fcn': isolate,
                'help': "Creates isolation routing geometry for the given Gerber.\n" +
                        "> isolate <name> [-dia <d>] [-passes <p>] [-overlap <o>] [-combine 0|1]\n" +
                        "   name: Name of the object\n"
                        "   dia: Tool diameter\n   passes: # of tool width\n" +
                        "   overlap: Fraction of tool diameter to overlap passes" +
                        "   combine: combine all passes into one geometry"
            },
            'cutout': {
                'fcn': cutout,
                'help': "Creates board cutout.\n" +
                        "> cutout <name> [-dia <3.0 (float)>] [-margin <0.0 (float)>] [-gapsize <0.5 (float)>] [-gaps <lr (4|tb|lr)>]\n" +
                        "   name: Name of the object\n" +
                        "   dia: Tool diameter\n" +
                        "   margin: Margin over bounds\n" +
                        "   gapsize: size of gap\n" +
                        "   gaps: type of gaps"
            },
            'mirror': {
                'fcn': mirror,
                'help': "Mirror a layer.\n" +
                        "> mirror <name> -axis <X|Y> [-box <nameOfBox> | -dist <number>]\n" +
                        "   name: Name of the object (Gerber or Excellon) to mirror.\n" +
                        "   box: Name of object which act as box (cutout for example.)\n" +
                        "   axis: Mirror axis parallel to the X or Y axis.\n" +
                        "   dist: Distance of the mirror axis to the X or Y axis."
            },
            'exteriors': {
                'fcn': exteriors,
                'help': "Get exteriors of polygons.\n" +
                        "> exteriors <name> [-outname <outname>]\n" +
                        "   name: Name of the source Geometry object.\n" +
                        "   outname: Name of the resulting Geometry object."
            },
            'interiors': {
                'fcn': interiors,
                'help': "Get interiors of polygons.\n" +
                        "> interiors <name> [-outname <outname>]\n" +
                        "   name: Name of the source Geometry object.\n" +
                        "   outname: Name of the resulting Geometry object."
            },
            'drillcncjob': {
                'fcn': drillcncjob,
                'help': "Drill CNC job.\n" +
                        "> drillcncjob <name> -tools <str> -drillz <float> " +
                        "-travelz <float> -feedrate <float> -outname <str> " +
                        "[-spindlespeed (int)] [-toolchange (int)] \n" +
                        "   name: Name of the object\n" +
                        "   tools: Comma separated indexes of tools (example: 1,3 or 2)\n" +
                        "   drillz: Drill depth into material (example: -2.0)\n" +
                        "   travelz: Travel distance above material (example: 2.0)\n" +
                        "   feedrate: Drilling feed rate\n" +
                        "   outname: Name of object to create\n" +
                        "   spindlespeed: Speed of the spindle in rpm (example: 4000)\n" +
                        "   toolchange: Enable tool changes (example: 1)\n"
            },
            'millholes': {
                'fcn': drillmillgeometry,
                'help': "Create Geometry Object for milling holes from Excellon.\n" +
                        "> millholes <name> -tools <str> -tooldia <float> -outname <str> \n" +
                        "   name: Name of the Excellon Object\n" +
                        "   tools: Comma separated indexes of tools (example: 1,3 or 2)\n" +
                        "   tooldia: Diameter of the milling tool (example: 0.1)\n" +
                        "   outname: Name of object to create\n"
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
            },
            'cncjob': {
                'fcn': cncjob,
                'help': 'Generates a CNC Job from a Geometry Object.\n' +
                        '> cncjob <name> [-z_cut <c>] [-z_move <m>] [-feedrate <f>] [-tooldia <t>] [-spindlespeed (int)] [-outname <n>]\n' +
                        '   name: Name of the source object\n' +
                        '   z_cut: Z-axis cutting position\n' +
                        '   z_move: Z-axis moving position\n' +
                        '   feedrate: Moving speed when cutting\n' +
                        '   tooldia: Tool diameter to show on screen\n' +
                        '   spindlespeed: Speed of the spindle in rpm (example: 4000)\n' +
                        '   outname: Name of the output object'
            },
            'write_gcode': {
                'fcn': write_gcode,
                'help': 'Saves G-code of a CNC Job object to file.\n' +
                        '> write_gcode <name> <filename>\n' +
                        '   name: Source CNC Job object\n' +
                        '   filename: Output filename'
            },
            'paint_poly': {
                'fcn': paint_poly,
                'help': 'Creates a geometry object with toolpath to cover the inside of a polygon.\n' +
                        '> paint_poly <name> <inside_pt_x> <inside_pt_y> <tooldia> <overlap>\n' +
                        '   name: Name of the sourge geometry object.\n' +
                        '   inside_pt_x, inside_pt_y: Coordinates of a point inside the polygon.\n' +
                        '   tooldia: Diameter of the tool to be used.\n' +
                        '   overlap: Fraction of the tool diameter to overlap cuts.'
            },
            'new_geometry': {
                'fcn': lambda name: self.new_object('geometry', str(name), lambda x, y: None),
                'help': 'Creates a new empty geometry object.\n' +
                        '> new_geometry <name>\n' +
                        '   name: New object name'
            },
            'add_poly': {
                'fcn': add_poly,
                'help': 'Creates a polygon in the given Geometry object.\n' +
                        '> create_poly <name> <x0> <y0> <x1> <y1> <x2> <y2> [x3 y3 [...]]\n' +
                        '   name: Name of the geometry object to which to append the polygon.\n' +
                        '   xi, yi: Coordinates of points in the polygon.'
            },
            'delete': {
                'fcn': delete,
                'help': 'Deletes the give object.\n' +
                        '> delete <name>\n' +
                        '   name: Name of the object to delete.'
            },
            'geo_union': {
                'fcn': geo_union,
                'help': 'Runs a union operation (addition) on the components ' +
                        'of the geometry object. For example, if it contains ' +
                        '2 intersecting polygons, this opperation adds them into' +
                        'a single larger polygon.\n' +
                        '> geo_union <name>\n' +
                        '   name: Name of the geometry object.'
            },
            'join_geometries': {
                'fcn': join_geometries,
                'help': 'Runs a merge operation (join) on the geometry ' +
                        'objects.' +
                        '> join_geometries <out_name> <obj_name_0>....\n' +
                        '   out_name: Name of the new geometry object.' +
                        '   obj_name_0... names of the objects to join'
            },
            'add_rect': {
                'fcn': add_rectangle,
                'help': 'Creates a rectange in the given Geometry object.\n' +
                        '> add_rect <name> <botleft_x> <botleft_y> <topright_x> <topright_y>\n' +
                        '   name: Name of the geometry object to which to append the rectangle.\n' +
                        '   botleft_x, botleft_y: Coordinates of the bottom left corner.\n' +
                        '   topright_x, topright_y Coordinates of the top right corner.'
            },
            'add_circle': {
                'fcn': add_circle,
                'help': 'Creates a circle in the given Geometry object.\n' +
                        '> add_circle <name> <center_x> <center_y> <radius>\n' +
                        '   name: Name of the geometry object to which to append the circle.\n' +
                        '   center_x, center_y: Coordinates of the center of the circle.\n' +
                        '   radius: Radius of the circle.'
            },
            'make_docs': {
                'fcn': make_docs,
                'help': 'Prints command rererence in reStructuredText format.'
            },
            'follow': {
                'fcn': follow,
                'help': 'Creates a geometry object following gerber paths.\n' +
                        '> follow <name> [-outname <oname>]\n' +
                        '   name: Name of the gerber object.\n' +
                        '   outname: Name of the output geometry object.'
            },
            'get_sys': {
                'fcn': get_sys,
                'help': 'Get the value of a system parameter (FlatCAM constant)\n' +
                        '> get_sys <sysparam>\n' +
                        '   sysparam: Name of the parameter.'
            },
            'set_sys': {
                'fcn': set_sys,
                'help': 'Set the value of a system parameter (FlatCAM constant)\n' +
                        '> set_sys <sysparam> <paramvalue>\n' +
                        '   sysparam: Name of the parameter.\n' +
                        '   paramvalue: Value to set.'
            }
        }

        # Add commands to the tcl interpreter
        for cmd in commands:
            self.tcl.createcommand(cmd, commands[cmd]['fcn'])

        # Make the tcl puts function return instead of print to stdout
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
            f = open(self.data_path + '/recent.json')
        except IOError:
            App.log.error("Failed to load recent item list.")
            self.inform.emit("[error] Failed to load recent item list.")
            return

        try:
            self.recent = json.load(f)
        except json.scanner.JSONDecodeError:
            App.log.error("Failed to parse recent item list.")
            self.inform.emit("[error] Failed to parse recent item list.")
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

            # Attach callback
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

        FCProcess.app = self
        FCProcessContainer.app = self

    def version_check(self):
        """
        Checks for the latest version of the program. Alerts the
        user if theirs is outdated. This method is meant to be run
        in a separate thread.

        :return: None
        """

        self.log.debug("version_check()")
        full_url = App.version_url + \
            "?s=" + str(self.defaults['serial']) + \
            "&v=" + str(self.version) + \
            "&os=" + str(self.os) + \
            "&" + urllib.urlencode(self.defaults["stats"])
        App.log.debug("Checking for updates @ %s" % full_url)

        ### Get the data
        try:
            f = urllib.urlopen(full_url)
        except:
            App.log.warning("Failed checking for latest version. Could not connect.")
            self.inform.emit("[warning] Failed checking for latest version. Could not connect.")
            return

        try:
            data = json.load(f)
        except Exception, e:
            App.log.error("Could not parse information about latest version.")
            self.inform.emit("[error] Could not parse information about latest version.")
            App.log.debug("json.load(): %s" % str(e))
            f.close()
            return

        f.close()

        ### Latest version?
        if self.version >= data["version"]:
            App.log.debug("FlatCAM is up to date!")
            self.inform.emit("[success] FlatCAM is up to date!")
            return

        App.log.debug("Newer version available.")
        self.message.emit(
            "Newer Version Available",
            QtCore.QString("There is a newer version of FlatCAM " +
                           "available for download:<br><br>" +
                           "<B>" + data["name"] + "</b><br>" +
                           data["message"].replace("\n", "<br>")),
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
            self.log.debug("[warning] There was no active object")
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
            App.log.error("[error] Failed to open file for saving: %s", filename)
            return

        # Write
        json.dump(d, f, default=to_dict)
        # try:
        #     json.dump(d, f, default=to_dict)
        # except Exception, e:
        #     print str(e)
        #     App.log.error("[error] File open but failed to write: %s", filename)
        #     f.close()
        #     return

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
