############################################################
# FlatCAM: 2D Post-processing for Manufacturing            #
# http://caram.cl/software/flatcam                         #
# Author: Juan Pablo Caram (c)                             #
# Date: 2/5/2014                                           #
# MIT Licence                                              #
############################################################

import threading
import sys
import urllib
import random

from gi.repository import Gtk, GdkPixbuf, GObject, Gdk, GLib






# from shapely import speedups
# Importing shapely speedups was causing the following errors:
# 'C:\WinPython-32\python-2.7.6\Lib\site-packages\gnome\lib/gio/modules\
# libgiognutls.dll': The specified module could not be found.
# Failed to load module: C:\WinPython-32\python-2.7.6\Lib\site-packages\gnome\lib/gio/modules\libgiognutls.dll
# 'C:\WinPython-32\python-2.7.6\Lib\site-packages\gnome\lib/gio/modules\
# libgiolibproxy.dll': The specified module could not be found.
# Failed to load module: C:\WinPython-32\python-2.7.6\Lib\site-packages\gnome\lib/gio/modules\libgiolibproxy.dll


########################################
##      Imports part of FlatCAM       ##
########################################
from FlatCAM_GTK.FlatCAMWorker import Worker
from FlatCAM_GTK.ObjectCollection import *
from FlatCAM_GTK.FlatCAMObj import *
from FlatCAM_GTK.PlotCanvas import *
from FlatCAM_GTK.FlatCAMGUI import *


class GerberOptionsGroupUI(Gtk.VBox):
    def __init__(self):
        Gtk.VBox.__init__(self, spacing=3, margin=5, vexpand=False)

        ## Plot options
        self.plot_options_label = Gtk.Label(justify=Gtk.Justification.LEFT, xalign=0, margin_top=5)
        self.plot_options_label.set_markup("<b>Plot Options:</b>")
        self.pack_start(self.plot_options_label, expand=False, fill=True, padding=2)

        grid0 = Gtk.Grid(column_spacing=3, row_spacing=2)
        self.pack_start(grid0, expand=True, fill=False, padding=2)

        # Plot CB
        self.plot_cb = FCCheckBox(label='Plot')
        grid0.attach(self.plot_cb, 0, 0, 1, 1)

        # Solid CB
        self.solid_cb = FCCheckBox(label='Solid')
        grid0.attach(self.solid_cb, 1, 0, 1, 1)

        # Multicolored CB
        self.multicolored_cb = FCCheckBox(label='Multicolored')
        grid0.attach(self.multicolored_cb, 2, 0, 1, 1)

        ## Isolation Routing
        self.isolation_routing_label = Gtk.Label(justify=Gtk.Justification.LEFT, xalign=0, margin_top=5)
        self.isolation_routing_label.set_markup("<b>Isolation Routing:</b>")
        self.pack_start(self.isolation_routing_label, expand=True, fill=False, padding=2)

        grid = Gtk.Grid(column_spacing=3, row_spacing=2)
        self.pack_start(grid, expand=True, fill=False, padding=2)

        l1 = Gtk.Label('Tool diam:', xalign=1)
        grid.attach(l1, 0, 0, 1, 1)
        self.iso_tool_dia_entry = LengthEntry()
        grid.attach(self.iso_tool_dia_entry, 1, 0, 1, 1)

        l2 = Gtk.Label('Width (# passes):', xalign=1)
        grid.attach(l2, 0, 1, 1, 1)
        self.iso_width_entry = IntEntry()
        grid.attach(self.iso_width_entry, 1, 1, 1, 1)

        l3 = Gtk.Label('Pass overlap:', xalign=1)
        grid.attach(l3, 0, 2, 1, 1)
        self.iso_overlap_entry = FloatEntry()
        grid.attach(self.iso_overlap_entry, 1, 2, 1, 1)

        ## Board cuttout
        self.isolation_routing_label = Gtk.Label(justify=Gtk.Justification.LEFT, xalign=0, margin_top=5)
        self.isolation_routing_label.set_markup("<b>Board cutout:</b>")
        self.pack_start(self.isolation_routing_label, expand=True, fill=False, padding=2)

        grid2 = Gtk.Grid(column_spacing=3, row_spacing=2)
        self.pack_start(grid2, expand=True, fill=False, padding=2)

        l4 = Gtk.Label('Tool dia:', xalign=1)
        grid2.attach(l4, 0, 0, 1, 1)
        self.cutout_tooldia_entry = LengthEntry()
        grid2.attach(self.cutout_tooldia_entry, 1, 0, 1, 1)

        l5 = Gtk.Label('Margin:', xalign=1)
        grid2.attach(l5, 0, 1, 1, 1)
        self.cutout_margin_entry = LengthEntry()
        grid2.attach(self.cutout_margin_entry, 1, 1, 1, 1)

        l6 = Gtk.Label('Gap size:', xalign=1)
        grid2.attach(l6, 0, 2, 1, 1)
        self.cutout_gap_entry = LengthEntry()
        grid2.attach(self.cutout_gap_entry, 1, 2, 1, 1)

        l7 = Gtk.Label('Gaps:', xalign=1)
        grid2.attach(l7, 0, 3, 1, 1)
        self.gaps_radio = RadioSet([{'label': '2 (T/B)', 'value': 'tb'},
                                    {'label': '2 (L/R)', 'value': 'lr'},
                                    {'label': '4', 'value': '4'}])
        grid2.attach(self.gaps_radio, 1, 3, 1, 1)

        ## Non-copper regions
        self.noncopper_label = Gtk.Label(justify=Gtk.Justification.LEFT, xalign=0, margin_top=5)
        self.noncopper_label.set_markup("<b>Non-copper regions:</b>")
        self.pack_start(self.noncopper_label, expand=True, fill=False, padding=2)

        grid3 = Gtk.Grid(column_spacing=3, row_spacing=2)
        self.pack_start(grid3, expand=True, fill=False, padding=2)

        l8 = Gtk.Label('Boundary margin:', xalign=1)
        grid3.attach(l8, 0, 0, 1, 1)
        self.noncopper_margin_entry = LengthEntry()
        grid3.attach(self.noncopper_margin_entry, 1, 0, 1, 1)

        self.noncopper_rounded_cb = FCCheckBox(label="Rounded corners")
        grid3.attach(self.noncopper_rounded_cb, 0, 1, 2, 1)

        ## Bounding box
        self.boundingbox_label = Gtk.Label(justify=Gtk.Justification.LEFT, xalign=0, margin_top=5)
        self.boundingbox_label.set_markup('<b>Bounding Box:</b>')
        self.pack_start(self.boundingbox_label, expand=True, fill=False, padding=2)

        grid4 = Gtk.Grid(column_spacing=3, row_spacing=2)
        self.pack_start(grid4, expand=True, fill=False, padding=2)

        l9 = Gtk.Label('Boundary Margin:', xalign=1)
        grid4.attach(l9, 0, 0, 1, 1)
        self.bbmargin_entry = LengthEntry()
        grid4.attach(self.bbmargin_entry, 1, 0, 1, 1)

        self.bbrounded_cb = FCCheckBox(label="Rounded corners")
        grid4.attach(self.bbrounded_cb, 0, 1, 2, 1)


class ExcellonOptionsGroupUI(Gtk.VBox):
    def __init__(self):
        Gtk.VBox.__init__(self, spacing=3, margin=5, vexpand=False)

        ## Plot options
        self.plot_options_label = Gtk.Label(justify=Gtk.Justification.LEFT, xalign=0, margin_top=5)
        self.plot_options_label.set_markup("<b>Plot Options:</b>")
        self.pack_start(self.plot_options_label, expand=False, fill=True, padding=2)

        grid0 = Gtk.Grid(column_spacing=3, row_spacing=2)
        self.pack_start(grid0, expand=True, fill=False, padding=2)

        self.plot_cb = FCCheckBox(label='Plot')
        grid0.attach(self.plot_cb, 0, 0, 1, 1)

        self.solid_cb = FCCheckBox(label='Solid')
        grid0.attach(self.solid_cb, 1, 0, 1, 1)

        ## Create CNC Job
        self.cncjob_label = Gtk.Label(justify=Gtk.Justification.LEFT, xalign=0, margin_top=5)
        self.cncjob_label.set_markup('<b>Create CNC Job</b>')
        self.pack_start(self.cncjob_label, expand=True, fill=False, padding=2)

        grid1 = Gtk.Grid(column_spacing=3, row_spacing=2)
        self.pack_start(grid1, expand=True, fill=False, padding=2)

        l1 = Gtk.Label('Cut Z:', xalign=1)
        grid1.attach(l1, 0, 0, 1, 1)
        self.cutz_entry = LengthEntry()
        grid1.attach(self.cutz_entry, 1, 0, 1, 1)

        l2 = Gtk.Label('Travel Z:', xalign=1)
        grid1.attach(l2, 0, 1, 1, 1)
        self.travelz_entry = LengthEntry()
        grid1.attach(self.travelz_entry, 1, 1, 1, 1)

        l3 = Gtk.Label('Feed rate:', xalign=1)
        grid1.attach(l3, 0, 2, 1, 1)
        self.feedrate_entry = LengthEntry()
        grid1.attach(self.feedrate_entry, 1, 2, 1, 1)


class GeometryOptionsGroupUI(Gtk.VBox):
    def __init__(self):
        Gtk.VBox.__init__(self, spacing=3, margin=5, vexpand=False)

        ## Plot options
        self.plot_options_label = Gtk.Label(justify=Gtk.Justification.LEFT, xalign=0, margin_top=5)
        self.plot_options_label.set_markup("<b>Plot Options:</b>")
        self.pack_start(self.plot_options_label, expand=False, fill=True, padding=2)

        grid0 = Gtk.Grid(column_spacing=3, row_spacing=2)
        self.pack_start(grid0, expand=True, fill=False, padding=2)

        # Plot CB
        self.plot_cb = FCCheckBox(label='Plot')
        grid0.attach(self.plot_cb, 0, 0, 1, 1)

        ## Create CNC Job
        self.cncjob_label = Gtk.Label(justify=Gtk.Justification.LEFT, xalign=0, margin_top=5)
        self.cncjob_label.set_markup('<b>Create CNC Job:</b>')
        self.pack_start(self.cncjob_label, expand=True, fill=False, padding=2)

        grid1 = Gtk.Grid(column_spacing=3, row_spacing=2)
        self.pack_start(grid1, expand=True, fill=False, padding=2)

        # Cut Z
        l1 = Gtk.Label('Cut Z:', xalign=1)
        grid1.attach(l1, 0, 0, 1, 1)
        self.cutz_entry = LengthEntry()
        grid1.attach(self.cutz_entry, 1, 0, 1, 1)

        # Travel Z
        l2 = Gtk.Label('Travel Z:', xalign=1)
        grid1.attach(l2, 0, 1, 1, 1)
        self.travelz_entry = LengthEntry()
        grid1.attach(self.travelz_entry, 1, 1, 1, 1)

        l3 = Gtk.Label('Feed rate:', xalign=1)
        grid1.attach(l3, 0, 2, 1, 1)
        self.cncfeedrate_entry = LengthEntry()
        grid1.attach(self.cncfeedrate_entry, 1, 2, 1, 1)

        l4 = Gtk.Label('Tool dia:', xalign=1)
        grid1.attach(l4, 0, 3, 1, 1)
        self.cnctooldia_entry = LengthEntry()
        grid1.attach(self.cnctooldia_entry, 1, 3, 1, 1)

        ## Paint Area
        self.paint_label = Gtk.Label(justify=Gtk.Justification.LEFT, xalign=0, margin_top=5)
        self.paint_label.set_markup('<b>Paint Area:</b>')
        self.pack_start(self.paint_label, expand=True, fill=False, padding=2)

        grid2 = Gtk.Grid(column_spacing=3, row_spacing=2)
        self.pack_start(grid2, expand=True, fill=False, padding=2)

        # Tool dia
        l5 = Gtk.Label('Tool dia:', xalign=1)
        grid2.attach(l5, 0, 0, 1, 1)
        self.painttooldia_entry = LengthEntry()
        grid2.attach(self.painttooldia_entry, 1, 0, 1, 1)

        # Overlap
        l6 = Gtk.Label('Overlap:', xalign=1)
        grid2.attach(l6, 0, 1, 1, 1)
        self.paintoverlap_entry = LengthEntry()
        grid2.attach(self.paintoverlap_entry, 1, 1, 1, 1)

        # Margin
        l7 = Gtk.Label('Margin:', xalign=1)
        grid2.attach(l7, 0, 2, 1, 1)
        self.paintmargin_entry = LengthEntry()
        grid2.attach(self.paintmargin_entry, 1, 2, 1, 1)


class CNCJobOptionsGroupUI(Gtk.VBox):
    def __init__(self):
        Gtk.VBox.__init__(self, spacing=3, margin=5, vexpand=False)

        ## Plot options
        self.plot_options_label = Gtk.Label(justify=Gtk.Justification.LEFT, xalign=0, margin_top=5)
        self.plot_options_label.set_markup("<b>Plot Options:</b>")
        self.pack_start(self.plot_options_label, expand=False, fill=True, padding=2)

        grid0 = Gtk.Grid(column_spacing=3, row_spacing=2)
        self.pack_start(grid0, expand=True, fill=False, padding=2)

        # Plot CB
        self.plot_cb = FCCheckBox(label='Plot')
        grid0.attach(self.plot_cb, 0, 0, 2, 1)

        # Tool dia for plot
        l1 = Gtk.Label('Tool dia:', xalign=1)
        grid0.attach(l1, 0, 1, 1, 1)
        self.tooldia_entry = LengthEntry()
        grid0.attach(self.tooldia_entry, 1, 1, 1, 1)


class GlobalOptionsUI(Gtk.VBox):
    def __init__(self):
        Gtk.VBox.__init__(self, spacing=3, margin=5, vexpand=False)

        box1 = Gtk.Box()
        self.pack_start(box1, expand=False, fill=False, padding=2)
        l1 = Gtk.Label('Units:')
        box1.pack_start(l1, expand=False, fill=False, padding=2)
        self.units_radio = RadioSet([{'label': 'inch', 'value': 'IN'},
                                     {'label': 'mm', 'value': 'MM'}])
        box1.pack_start(self.units_radio, expand=False, fill=False, padding=2)

        ####### Gerber #######
        l2 = Gtk.Label(margin=5)
        l2.set_markup('<b>Gerber Options</b>')
        frame1 = Gtk.Frame(label_widget=l2)
        self.pack_start(frame1, expand=False, fill=False, padding=2)
        self.gerber_group = GerberOptionsGroupUI()
        frame1.add(self.gerber_group)

        ######## Excellon #########
        l3 = Gtk.Label(margin=5)
        l3.set_markup('<b>Excellon Options</b>')
        frame2 = Gtk.Frame(label_widget=l3)
        self.pack_start(frame2, expand=False, fill=False, padding=2)
        self.excellon_group = ExcellonOptionsGroupUI()
        frame2.add(self.excellon_group)

        ########## Geometry ##########
        l4 = Gtk.Label(margin=5)
        l4.set_markup('<b>Geometry Options</b>')
        frame3 = Gtk.Frame(label_widget=l4)
        self.pack_start(frame3, expand=False, fill=False, padding=2)
        self.geometry_group = GeometryOptionsGroupUI()
        frame3.add(self.geometry_group)

        ########## CNC ############
        l5 = Gtk.Label(margin=5)
        l5.set_markup('<b>CNC Job Options</b>')
        frame4 = Gtk.Frame(label_widget=l5)
        self.pack_start(frame4, expand=False, fill=False, padding=2)
        self.cncjob_group = CNCJobOptionsGroupUI()
        frame4.add(self.cncjob_group)


########################################
##                App                 ##
########################################
class App:
    """
    The main application class. The constructor starts the GUI.
    """

    log = logging.getLogger('base')
    log.setLevel(logging.DEBUG)
    #log.setLevel(logging.WARNING)
    formatter = logging.Formatter('[%(levelname)s] %(message)s')
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    log.addHandler(handler)

    version_url = "http://caram.cl/flatcam/VERSION"

    def __init__(self):
        """
        Starts the application. Takes no parameters.

        :return: app
        :rtype: App
        """

        App.log.info("FlatCAM Starting...")

        # if speedups.available:
        #     App.log.info("Enabling geometry speedups...")
        #     speedups.enable()

        # Needed to interact with the GUI from other threads.
        App.log.debug("GObject.threads_init()...")
        GObject.threads_init()

        #### GUI ####
        # Glade init
        # App.log.debug("Building GUI from Glade file...")
        # self.gladefile = "FlatCAM.ui"
        # self.builder = Gtk.Builder()
        # self.builder.add_from_file(self.gladefile)
        #
        # # References to UI widgets
        # self.window = self.builder.get_object("window1")
        # self.position_label = self.builder.get_object("label3")
        # self.grid = self.builder.get_object("grid1")
        # self.notebook = self.builder.get_object("notebook1")
        # self.info_label = self.builder.get_object("label_status")
        # self.progress_bar = self.builder.get_object("progressbar")
        # self.progress_bar.set_show_text(True)
        # self.units_label = self.builder.get_object("label_units")
        # self.toolbar = self.builder.get_object("toolbar_main")
        #
        # # White (transparent) background on the "Options" tab.
        # self.builder.get_object("vp_options").override_background_color(Gtk.StateType.NORMAL,
        #                                                                 Gdk.RGBA(1, 1, 1, 1))
        # # Combo box to choose between project and application options.
        # self.combo_options = self.builder.get_object("combo_options")
        # self.combo_options.set_active(1)
        self.ui = FlatCAMGUI()

        #self.setup_project_list()  # The "Project" tab
        self.setup_component_editor()  # The "Selected" tab

        ## Setup the toolbar. Adds buttons.
        self.setup_toolbar()

        # App.log.debug("Connecting signals from builder...")
        #### Event handling ####
        # self.builder.connect_signals(self)
        self.ui.menufileopengerber.connect('activate', self.on_fileopengerber)

        #### Make plot area ####
        self.plotcanvas = PlotCanvas(self.ui.plotarea)
        self.plotcanvas.mpl_connect('button_press_event', self.on_click_over_plot)
        self.plotcanvas.mpl_connect('motion_notify_event', self.on_mouse_move_over_plot)
        self.plotcanvas.mpl_connect('key_press_event', self.on_key_over_plot)

        #### DATA ####
        self.clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        self.setup_obj_classes()
        self.mouse = None  # Mouse coordinates over plot
        self.recent = []
        self.collection = ObjectCollection()
        # self.builder.get_object("box_project").pack_start(self.collection.view, False, False, 1)
        self.ui.notebook.project_contents.pack_start(self.collection.view, False, False, 1)
        # TODO: Do this different
        self.collection.view.connect("row_activated", self.on_row_activated)

        # Used to inhibit the on_options_update callback when
        # the options are being changed by the program and not the user.
        self.options_update_ignore = False

        self.toggle_units_ignore = False

        # self.options_box = self.builder.get_object('options_box')
        ## Application defaults ##
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
            "cncjob_tooldia": self.defaults_form.cncjob_group.tooldia_entry
        }

        self.defaults = {
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
            "cncjob_tooldia": 0.016
        }
        self.load_defaults()
        self.defaults_write_form()

        ## Current Project ##
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
            "cncjob_tooldia": self.options_form.cncjob_group.tooldia_entry
        }

        # Project options
        self.options = {
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
            "cncjob_tooldia": 0.016
        }
        self.options.update(self.defaults)  # Copy app defaults to project options
        self.options_write_form()

        self.project_filename = None

        # Where we draw the options/defaults forms.
        self.on_options_combo_change(None)
        #self.options_box.pack_start(self.defaults_form, False, False, 1)

        self.options_form.units_radio.group_toggle_fn = lambda x, y: self.on_toggle_units(x)

        ## Event subscriptions ##

        ## Tools ##
        # self.measure = Measurement(self.builder.get_object("box39"), self.plotcanvas)
        self.measure = Measurement(self.ui.plotarea_super, self.plotcanvas)
        # Toolbar icon
        # TODO: Where should I put this? Tool should have a method to add to toolbar?
        meas_ico = Gtk.Image.new_from_file('share/measure32.png')
        measure = Gtk.ToolButton.new(meas_ico, "")
        measure.connect("clicked", self.measure.toggle_active)
        measure.set_tooltip_markup("<b>Measure Tool:</b> Enable/disable tool.\n" +
                                   "Click on point to set reference.\n" +
                                   "(Click on plot and hit <b>m</b>)")
        # self.toolbar.insert(measure, -1)
        self.ui.toolbar.insert(measure, -1)

        #### Initialization ####
        # self.units_label.set_text("[" + self.options["units"] + "]")
        self.ui.units_label.set_text("[" + self.options["units"] + "]")
        self.setup_recent_items()

        App.log.info("Starting Worker...")
        self.worker = Worker()
        self.worker.daemon = True
        self.worker.start()

        #### Check for updates ####
        # Separate thread (Not worker)
        self.version = 5
        App.log.info("Checking for updates in backgroud (this is version %s)." % str(self.version))
        t1 = threading.Thread(target=self.version_check)
        t1.daemon = True
        t1.start()

        #### For debugging only ###
        def somethreadfunc(app_obj):
            App.log.info("Hello World!")

        t = threading.Thread(target=somethreadfunc, args=(self,))
        t.daemon = True
        t.start()

        ########################################
        ##              START                 ##
        ########################################
        self.icon256 = GdkPixbuf.Pixbuf.new_from_file('share/flatcam_icon256.png')
        self.icon48 = GdkPixbuf.Pixbuf.new_from_file('share/flatcam_icon48.png')
        self.icon16 = GdkPixbuf.Pixbuf.new_from_file('share/flatcam_icon16.png')
        Gtk.Window.set_default_icon_list([self.icon16, self.icon48, self.icon256])
        # self.window.set_title("FlatCAM - Alpha 5")
        # self.window.set_default_size(900, 600)
        # self.window.show_all()
        self.ui.show_all()

        App.log.info("END of constructor. Releasing control.")

    def message_dialog(self, title, message, kind="info"):
        types = {"info": Gtk.MessageType.INFO,
                 "warn": Gtk.MessageType.WARNING,
                 "error": Gtk.MessageType.ERROR}
        dlg = Gtk.MessageDialog(self.ui, 0, types[kind], Gtk.ButtonsType.OK, title)
        dlg.format_secondary_text(message)

        def lifecycle():
            dlg.run()
            dlg.destroy()

        GLib.idle_add(lifecycle)

    def question_dialog(self, title, message):
        label = Gtk.Label(message)
        dialog = Gtk.Dialog(title, self.window, 0,
                            (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                             Gtk.STOCK_OK, Gtk.ResponseType.OK))
        dialog.set_default_size(150, 100)
        dialog.set_modal(True)
        box = dialog.get_content_area()
        box.set_border_width(10)
        box.add(label)
        dialog.show_all()
        response = dialog.run()
        dialog.destroy()
        return response

    def setup_toolbar(self):

        # Zoom fit
        # zf_ico = Gtk.Image.new_from_file('share/zoom_fit32.png')
        # zoom_fit = Gtk.ToolButton.new(zf_ico, "")
        # zoom_fit.connect("clicked", self.on_zoom_fit)
        # zoom_fit.set_tooltip_markup("Zoom Fit.\n(Click on plot and hit <b>1</b>)")
        # self.toolbar.insert(zoom_fit, -1)
        self.ui.zoom_fit_btn.connect("clicked", self.on_zoom_fit)

        # Zoom out
        # zo_ico = Gtk.Image.new_from_file('share/zoom_out32.png')
        # zoom_out = Gtk.ToolButton.new(zo_ico, "")
        # zoom_out.connect("clicked", self.on_zoom_out)
        # zoom_out.set_tooltip_markup("Zoom Out.\n(Click on plot and hit <b>2</b>)")
        # self.toolbar.insert(zoom_out, -1)
        self.ui.zoom_out_btn.connect("clicked", self.on_zoom_out)

        # Zoom in
        # zi_ico = Gtk.Image.new_from_file('share/zoom_in32.png')
        # zoom_in = Gtk.ToolButton.new(zi_ico, "")
        # zoom_in.connect("clicked", self.on_zoom_in)
        # zoom_in.set_tooltip_markup("Zoom In.\n(Click on plot and hit <b>3</b>)")
        # self.toolbar.insert(zoom_in, -1)
        self.ui.zoom_in_btn.connect("clicked", self.on_zoom_in)

        # Clear plot
        # cp_ico = Gtk.Image.new_from_file('share/clear_plot32.png')
        # clear_plot = Gtk.ToolButton.new(cp_ico, "")
        # clear_plot.connect("clicked", self.on_clear_plots)
        # clear_plot.set_tooltip_markup("Clear Plot")
        # self.toolbar.insert(clear_plot, -1)
        self.ui.clear_plot_btn.connect("clicked", self.on_clear_plots)

        # Replot
        # rp_ico = Gtk.Image.new_from_file('share/replot32.png')
        # replot = Gtk.ToolButton.new(rp_ico, "")
        # replot.connect("clicked", self.on_toolbar_replot)
        # replot.set_tooltip_markup("Re-plot all")
        # self.toolbar.insert(replot, -1)
        self.ui.replot_btn.connect("clicked", self.on_toolbar_replot)

        # Delete item
        # del_ico = Gtk.Image.new_from_file('share/delete32.png')
        # delete = Gtk.ToolButton.new(del_ico, "")
        # delete.connect("clicked", self.on_delete)
        # delete.set_tooltip_markup("Delete selected\nobject.")
        # self.toolbar.insert(delete, -1)
        self.ui.delete_btn.connect("clicked", self.on_delete)

    def setup_obj_classes(self):
        """
        Sets up application specifics on the FlatCAMObj class.

        :return: None
        """
        FlatCAMObj.app = self

    def setup_component_editor(self):
        """
        Initial configuration of the component editor. Creates
        a page titled "Selection" on the notebook on the left
        side of the main window.

        :return: None
        """

        # box_selected = self.builder.get_object("vp_selected")

        # White background
        # box_selected.override_background_color(Gtk.StateType.NORMAL,
        #                                        Gdk.RGBA(1, 1, 1, 1))
        self.ui.notebook.selected_contents.override_background_color(Gtk.StateType.NORMAL,
                                                                     Gdk.RGBA(1, 1, 1, 1))

        # Remove anything else in the box
        box_children = self.ui.notebook.selected_contents.get_children()
        for child in box_children:
            self.ui.notebook.selected_contents.remove(child)

        box1 = Gtk.Box(Gtk.Orientation.VERTICAL)
        label1 = Gtk.Label("Choose an item from Project")
        box1.pack_start(label1, True, False, 1)
        self.ui.notebook.selected_contents.add(box1)
        box1.show()
        label1.show()

    def setup_recent_items(self):

        # TODO: Move this to constructor
        icons = {
            "gerber": "share/flatcam_icon16.png",
            "excellon": "share/drill16.png",
            "cncjob": "share/cnc16.png",
            "project": "share/project16.png"
        }

        openers = {
            'gerber': self.open_gerber,
            'excellon': self.open_excellon,
            'cncjob': self.open_gcode,
            'project': self.open_project
        }

        # Closure needed to create callbacks in a loop.
        # Otherwise late binding occurs.
        def make_callback(func, fname):
            def opener(*args):
                self.worker.add_task(func, [fname])
            return opener

        try:
            f = open('recent.json')
        except IOError:
            App.log.error("Failed to load recent item list.")
            self.info("ERROR: Failed to load recent item list.")
            return

        try:
            self.recent = json.load(f)
        except:
            App.log.error("Failed to parse recent item list.")
            self.info("ERROR: Failed to parse recent item list.")
            f.close()
            return
        f.close()

        recent_menu = Gtk.Menu()
        for recent in self.recent:
            filename = recent['filename'].split('/')[-1].split('\\')[-1]
            item = Gtk.ImageMenuItem.new_with_label(filename)
            im = Gtk.Image.new_from_file(icons[recent["kind"]])
            item.set_image(im)

            o = make_callback(openers[recent["kind"]], recent['filename'])

            item.connect('activate', o)
            recent_menu.append(item)

        # self.builder.get_object('open_recent').set_submenu(recent_menu)
        self.ui.menufilerecent.set_submenu(recent_menu)
        recent_menu.show_all()

    def info(self, text):
        """
        Show text on the status bar. This method is thread safe.

        :param text: Text to display.
        :type text: str
        :return: None
        """
        GLib.idle_add(lambda: self.ui.info_label.set_text(text))

    def get_radio_value(self, radio_set):
        """
        Returns the radio_set[key] of the radiobutton
        whose name is key is active.

        :param radio_set: A dictionary containing widget_name: value pairs.
        :type radio_set: dict
        :return: radio_set[key]
        """

        for name in radio_set:
            if self.builder.get_object(name).get_active():
                return radio_set[name]

    def plot_all(self):
        """
        Re-generates all plots from all objects.

        :return: None
        """
        self.plotcanvas.clear()
        self.set_progress_bar(0.1, "Re-plotting...")

        def worker_task(app_obj):
            percentage = 0.1
            try:
                delta = 0.9 / len(self.collection.get_list())
            except ZeroDivisionError:
                GLib.timeout_add(300, lambda: app_obj.set_progress_bar(0.0, ""))
                return
            for obj in self.collection.get_list():
                obj.plot()
                percentage += delta
                GLib.idle_add(lambda: app_obj.set_progress_bar(percentage, "Re-plotting..."))

            GLib.idle_add(app_obj.plotcanvas.auto_adjust_axes)
            GLib.idle_add(lambda: self.on_zoom_fit(None))
            GLib.timeout_add(300, lambda: app_obj.set_progress_bar(0.0, "Idle"))

        # Send to worker
        self.worker.add_task(worker_task, [self])

    def get_eval(self, widget_name):
        """
        Runs eval() on the on the text entry of name 'widget_name'
        and returns the results.

        :param widget_name: Name of Gtk.Entry
        :type widget_name: str
        :return: Depends on contents of the entry text.
        """

        value = self.builder.get_object(widget_name).get_text()
        if value == "":
            value = "None"
        try:
            evald = eval(value)
            return evald
        except:
            self.info("Could not evaluate: " + value)
            return None

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

        # This is ok here... NO.
        # t = Gtk.TextView()
        # print t

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

        # App dies here!
        # t = Gtk.TextView()
        # print t

        # Create object
        classdict = {
            "gerber": FlatCAMGerber,
            "excellon": FlatCAMExcellon,
            "cncjob": FlatCAMCNCjob,
            "geometry": FlatCAMGeometry
        }
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
            GLib.idle_add(lambda: self.info("Converting units to " + self.options["units"] + "."))
            obj.convert_units(self.options["units"])

        # Add to our records
        self.collection.append(obj, active=active)

        # Show object details now.
        # GLib.idle_add(lambda: self.notebook.set_current_page(1))
        GLib.idle_add(lambda: self.ui.notebook.set_current_page(1))

        # Plot
        # TODO: (Thread-safe?)
        if plot:
            obj.plot()

        if fit:
            GLib.idle_add(lambda: self.on_zoom_fit(None))

        return obj

    def set_progress_bar(self, percentage, text=""):
        """
        Sets the application's progress bar to a given frac_digits and text.

        :param percentage: The frac_digits (0.0-1.0) of the progress.
        :type percentage: float
        :param text: Text to display on the progress bar.
        :type text: str
        :return: None
        """
        # self.progress_bar.set_text(text)
        # self.progress_bar.set_fraction(percentage)
        self.ui.progress_bar.set_text(text)
        self.ui.progress_bar.set_fraction(percentage)
        return False

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
            App.log.error("Could not load defaults file.")
            self.info("ERROR: Could not load defaults file.")
            return

        try:
            defaults = json.loads(options)
        except:
            e = sys.exc_info()[0]
            App.log.error(str(e))
            self.info("ERROR: Failed to parse defaults file.")
            return
        self.defaults.update(defaults)

    def defaults_read_form(self):
        for option in self.defaults_form_fields:
            self.defaults[option] = self.defaults_form_fields[option].get_value()

    def options_read_form(self):
        for option in self.options_form_fields:
            self.options[option] = self.options_form_fields[option].get_value()

    def defaults_write_form(self):
        for option in self.defaults_form_fields:
            self.defaults_form_fields[option].set_value(self.defaults[option])

    def options_write_form(self):
        for option in self.options_form_fields:
            self.options_form_fields[option].set_value(self.options[option])

    def save_project(self, filename):
        """
        Saves the current project to the specified file.

        :param filename: Name of the file in which to save.
        :type filename: str
        :return: None
        """

        # Capture the latest changes
        try:
            self.collection.get_active().read_form()
        except:
            pass

        # Serialize the whole project
        d = {"objs": [obj.to_dict() for obj in self.collection.get_list()],
             "options": self.options}

        try:
            f = open(filename, 'w')
        except IOError:
            App.log.error("ERROR: Failed to open file for saving:", filename)
            return

        try:
            json.dump(d, f, default=to_dict)
        except:
            App.log.error("ERROR: File open but failed to write:", filename)
            f.close()
            return

        f.close()

    def open_project(self, filename):
        """
        Loads a project from the specified file.

        :param filename:  Name of the file from which to load.
        :type filename: str
        :return: None
        """
        App.log.debug("Opening project: " + filename)

        try:
            f = open(filename, 'r')
        except IOError:
            App.log.error("Failed to open project file: %s" % filename)
            self.info("ERROR: Failed to open project file: %s" % filename)
            return

        try:
            d = json.load(f, object_hook=dict2obj)
        except:
            App.log.error("Failed to parse project file: %s" % filename)
            self.info("ERROR: Failed to parse project file: %s" % filename)
            f.close()
            return

        self.register_recent("project", filename)

        # Clear the current project
        self.on_file_new(None)

        # Project options
        self.options.update(d['options'])
        self.project_filename = filename
        GLib.idle_add(lambda: self.units_label.set_text(self.options["units"]))

        # Re create objects
        App.log.debug("Re-creating objects...")
        for obj in d['objs']:
            def obj_init(obj_inst, app_inst):
                obj_inst.from_dict(obj)
            App.log.debug(obj['kind'] + ":  " + obj['options']['name'])
            self.new_object(obj['kind'], obj['options']['name'], obj_init, active=False, fit=False, plot=False)

        self.plot_all()
        self.info("Project loaded from: " + filename)
        App.log.debug("Project loaded")

    def populate_objects_combo(self, combo):
        """
        Populates a Gtk.Comboboxtext with the list of the object in the project.

        :param combo: Name or instance of the comboboxtext.
        :type combo: str or Gtk.ComboBoxText
        :return: None
        """
        App.log.debug("Populating combo!")
        if type(combo) == str:
            combo = self.builder.get_object(combo)

        combo.remove_all()
        for name in self.collection.get_names():
            combo.append_text(name)

    def version_check(self, *args):
        """
        Checks for the latest version of the program. Alerts the
        user if theirs is outdated. This method is meant to be run
        in a saeparate thread.

        :return: None
        """

        try:
            f = urllib.urlopen(App.version_url)
        except:
            App.log.warning("Failed checking for latest version. Could not connect.")
            GLib.idle_add(lambda: self.info("ERROR trying to check for latest version."))
            return

        try:
            data = json.load(f)
        except:
            App.log.error("Could nor parse information about latest version.")
            GLib.idle_add(lambda: self.info("ERROR trying to check for latest version."))
            f.close()
            return

        f.close()

        if self.version >= data["version"]:
            GLib.idle_add(lambda: self.info("FlatCAM is up to date!"))
            return

        label = Gtk.Label("There is a newer version of FlatCAM\n" +
                          "available for download:\n\n" +
                          data["name"] + "\n\n" + data["message"])
        dialog = Gtk.Dialog("Newer Version Available", self.window, 0,
                            (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                             Gtk.STOCK_OK, Gtk.ResponseType.OK))
        dialog.set_default_size(150, 100)
        dialog.set_modal(True)
        box = dialog.get_content_area()
        box.set_border_width(10)
        box.add(label)

        def do_dialog():
            dialog.show_all()
            response = dialog.run()
            dialog.destroy()

        GLib.idle_add(lambda: do_dialog())

        return

    def do_nothing(self, param):
        return

    def disable_plots(self, except_current=False):
        """
        Disables all plots with exception of the current object if specified.

        :param except_current: Wether to skip the current object.
        :rtype except_current: boolean
        :return: None
        """
        # TODO: This method is very similar to replot_all. Try to merge.

        self.set_progress_bar(0.1, "Re-plotting...")

        def worker_task(app_obj):
            percentage = 0.1
            try:
                delta = 0.9 / len(self.collection.get_list())
            except ZeroDivisionError:
                GLib.timeout_add(300, lambda: app_obj.set_progress_bar(0.0, ""))
                return
            for obj in self.collection.get_list():
                if obj != self.collection.get_active() or not except_current:
                    obj.options['plot'] = False
                    obj.plot()
                percentage += delta
                GLib.idle_add(lambda: app_obj.set_progress_bar(percentage, "Re-plotting..."))

            GLib.idle_add(app_obj.plotcanvas.auto_adjust_axes)
            GLib.timeout_add(300, lambda: app_obj.set_progress_bar(0.0, ""))

        # Send to worker
        self.worker.add_task(worker_task, [self])

    def enable_all_plots(self, *args):
        self.plotcanvas.clear()
        self.set_progress_bar(0.1, "Re-plotting...")

        def worker_task(app_obj):
            percentage = 0.1
            try:
                delta = 0.9 / len(self.collection.get_list())
            except ZeroDivisionError:
                GLib.timeout_add(300, lambda: app_obj.set_progress_bar(0.0, ""))
                return
            for obj in self.collection.get_list():
                obj.options['plot'] = True
                obj.plot()
                percentage += delta
                GLib.idle_add(lambda: app_obj.set_progress_bar(percentage, "Re-plotting..."))

            GLib.idle_add(app_obj.plotcanvas.auto_adjust_axes)
            GLib.timeout_add(300, lambda: app_obj.set_progress_bar(0.0, ""))

        # Send to worker
        self.worker.add_task(worker_task, [self])

    def register_recent(self, kind, filename):
        record = {'kind': kind, 'filename': filename}

        if record in self.recent:
            return

        self.recent.insert(0, record)

        if len(self.recent) > 10:  # Limit reached
            self.recent.pop()

        try:
            f = open('recent.json', 'w')
        except IOError:
            App.log.error("Failed to open recent items file for writing.")
            self.info('Failed to open recent files file for writing.')
            return

        try:
            json.dump(self.recent, f)
        except:
            App.log.error("Failed to write to recent items file.")
            self.info('ERROR: Failed to write to recent items file.')
            f.close()

        f.close()

    def open_gerber(self, filename):
        """
        Opens a Gerber file, parses it and creates a new object for
        it in the program. Thread-safe.

        :param filename: Gerber file filename
        :type filename: str
        :return: None
        """

        # Fails here
        # t = Gtk.TextView()
        # print t

        GLib.idle_add(lambda: self.set_progress_bar(0.1, "Opening Gerber ..."))

        # How the object should be initialized
        def obj_init(gerber_obj, app_obj):
            assert isinstance(gerber_obj, FlatCAMGerber)

            # Opening the file happens here
            GLib.idle_add(lambda: app_obj.set_progress_bar(0.2, "Parsing ..."))
            gerber_obj.parse_file(filename)

            # Further parsing
            GLib.idle_add(lambda: app_obj.set_progress_bar(0.5, "Creating Geometry ..."))
            GLib.idle_add(lambda: app_obj.set_progress_bar(0.6, "Plotting ..."))

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
        self.register_recent("gerber", filename)

        # GUI feedback
        self.info("Opened: " + filename)
        GLib.idle_add(lambda: self.set_progress_bar(1.0, "Done!"))
        GLib.timeout_add_seconds(1, lambda: self.set_progress_bar(0.0, "Idle"))

    def open_excellon(self, filename):
        """
        Opens an Excellon file, parses it and creates a new object for
        it in the program. Thread-safe.

        :param filename: Excellon file filename
        :type filename: str
        :return: None
        """
        GLib.idle_add(lambda: self.set_progress_bar(0.1, "Opening Excellon ..."))

        # How the object should be initialized
        def obj_init(excellon_obj, app_obj):
            GLib.idle_add(lambda: app_obj.set_progress_bar(0.2, "Parsing ..."))
            excellon_obj.parse_file(filename)
            excellon_obj.create_geometry()
            GLib.idle_add(lambda: app_obj.set_progress_bar(0.6, "Plotting ..."))

        # Object name
        name = filename.split('/')[-1].split('\\')[-1]

        # New object creation and file processing
        try:
            self.new_object("excellon", name, obj_init)
        except:
            e = sys.exc_info()
            App.log.error(str(e))
            self.message_dialog("Failed to create Excellon Object",
                                "Attempting to create a FlatCAM Excellon Object from " +
                                "Excellon file failed during processing:\n" +
                                str(e[0]) + " " + str(e[1]), kind="error")
            GLib.timeout_add_seconds(1, lambda: self.set_progress_bar(0.0, "Idle"))
            self.collection.delete_active()
            return

        # Register recent file
        self.register_recent("excellon", filename)

        # GUI feedback
        self.info("Opened: " + filename)
        GLib.idle_add(lambda: self.set_progress_bar(1.0, "Done!"))
        GLib.timeout_add_seconds(1, lambda: self.set_progress_bar(0.0, ""))

    def open_gcode(self, filename):
        """
        Opens a G-gcode file, parses it and creates a new object for
        it in the program. Thread-safe.

        :param filename: G-code file filename
        :type filename: str
        :return: None
        """

        # How the object should be initialized
        def obj_init(job_obj, app_obj_):
            """

            :type app_obj_: App
            """
            assert isinstance(app_obj_, App)
            GLib.idle_add(lambda: app_obj_.set_progress_bar(0.1, "Opening G-Code ..."))

            f = open(filename)
            gcode = f.read()
            f.close()

            job_obj.gcode = gcode

            GLib.idle_add(lambda: app_obj_.set_progress_bar(0.2, "Parsing ..."))
            job_obj.gcode_parse()

            GLib.idle_add(lambda: app_obj_.set_progress_bar(0.6, "Creating geometry ..."))
            job_obj.create_geometry()

            GLib.idle_add(lambda: app_obj_.set_progress_bar(0.6, "Plotting ..."))

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
            GLib.timeout_add_seconds(1, lambda: self.set_progress_bar(0.0, "Idle"))
            self.collection.delete_active()
            return

        # Register recent file
        self.register_recent("cncjob", filename)

        # GUI feedback
        self.info("Opened: " + filename)
        GLib.idle_add(lambda: self.set_progress_bar(1.0, "Done!"))
        GLib.timeout_add_seconds(1, lambda: self.set_progress_bar(0.0, ""))

    ########################################
    ##         EVENT HANDLERS             ##
    ########################################
    def on_debug_printlist(self, *args):
        self.collection.print_list()

    def on_disable_all_plots(self, widget):
        self.disable_plots()

    def on_disable_all_plots_not_current(self, widget):
        self.disable_plots(except_current=True)

    def on_about(self, widget):
        """
        Opens the 'About' dialog box.

        :param widget: Ignored.
        :return: None
        """

        about = self.builder.get_object("aboutdialog")
        about.run()
        about.hide()

    def on_create_mirror(self, widget):
        """
        Creates a mirror image of an object to be used as a bottom layer.

        :param widget: Ignored.
        :return: None
        """
        # TODO: Move (some of) this to camlib!

        # Object to mirror
        obj_name = self.builder.get_object("comboboxtext_bottomlayer").get_active_text()
        fcobj = self.collection.get_by_name(obj_name)

        # For now, lets limit to Gerbers and Excellons.
        # assert isinstance(gerb, FlatCAMGerber)
        if not isinstance(fcobj, FlatCAMGerber) and not isinstance(fcobj, FlatCAMExcellon):
            self.info("ERROR: Only Gerber and Excellon objects can be mirrored.")
            return

        # Mirror axis "X" or "Y
        axis = self.get_radio_value({"rb_mirror_x": "X",
                                     "rb_mirror_y": "Y"})
        mode = self.get_radio_value({"rb_mirror_box": "box",
                                     "rb_mirror_point": "point"})
        if mode == "point":  # A single point defines the mirror axis
            # TODO: Error handling
            px, py = eval(self.point_entry.get_text())
        else:  # The axis is the line dividing the box in the middle
            name = self.box_combo.get_active_text()
            bb_obj = self.collection.get_by_name(name)
            xmin, ymin, xmax, ymax = bb_obj.bounds()
            px = 0.5*(xmin+xmax)
            py = 0.5*(ymin+ymax)

        fcobj.mirror(axis, [px, py])
        fcobj.plot()

    def on_create_aligndrill(self, widget):
        """
        Creates alignment holes Excellon object. Creates mirror duplicates
        of the specified holes around the specified axis.

        :param widget: Ignored.
        :return: None
        """

        # Mirror axis. Same as in on_create_mirror.
        axis = self.get_radio_value({"rb_mirror_x": "X",
                                     "rb_mirror_y": "Y"})
        # TODO: Error handling
        mode = self.get_radio_value({"rb_mirror_box": "box",
                                     "rb_mirror_point": "point"})
        if mode == "point":
            px, py = eval(self.point_entry.get_text())
        else:
            name = self.box_combo.get_active_text()
            bb_obj = self.collection.get_by_name(name)
            xmin, ymin, xmax, ymax = bb_obj.bounds()
            px = 0.5*(xmin+xmax)
            py = 0.5*(ymin+ymax)
        xscale, yscale = {"X": (1.0, -1.0), "Y": (-1.0, 1.0)}[axis]

        # Tools
        dia = self.get_eval("entry_dblsided_alignholediam")
        tools = {"1": {"C": dia}}

        # Parse hole list
        # TODO: Better parsing
        holes = self.builder.get_object("entry_dblsided_alignholes").get_text()
        holes = eval("[" + holes + "]")
        drills = []
        for hole in holes:
            point = Point(hole)
            point_mirror = affinity.scale(point, xscale, yscale, origin=(px, py))
            drills.append({"point": point, "tool": "1"})
            drills.append({"point": point_mirror, "tool": "1"})

        def obj_init(obj_inst, app_inst):
            obj_inst.tools = tools
            obj_inst.drills = drills
            obj_inst.create_geometry()

        self.new_object("excellon", "Alignment Drills", obj_init)

    def on_toggle_pointbox(self, widget):
        """
        Callback for radio selection change between point and box in the
        Double-sided PCB tool. Updates the UI accordingly.

        :param widget: Ignored.
        :return: None
        """

        # Where the entry or combo go
        box = self.builder.get_object("box_pointbox")

        # Clear contents
        children = box.get_children()
        for child in children:
            box.remove(child)

        choice = self.get_radio_value({"rb_mirror_point": "point",
                                       "rb_mirror_box": "box"})

        if choice == "point":
            self.point_entry = Gtk.Entry()
            self.builder.get_object("box_pointbox").pack_start(self.point_entry,
                                                               False, False, 1)
            self.point_entry.show()
        else:
            self.box_combo = Gtk.ComboBoxText()
            self.builder.get_object("box_pointbox").pack_start(self.box_combo,
                                                               False, False, 1)
            self.populate_objects_combo(self.box_combo)
            self.box_combo.show()

    def on_tools_doublesided(self, param):
        """
        Callback for menu item Tools->Double Sided PCB Tool. Launches the
        tool placing its UI in the "Tool" tab in the notebook.

        :param param: Ignored.
        :return: None
        """

        # Were are we drawing the UI
        box_tool = self.builder.get_object("box_tool")

        # Remove anything else in the box
        box_children = box_tool.get_children()
        for child in box_children:
            box_tool.remove(child)

        # Get the UI
        osw = self.builder.get_object("offscreenwindow_dblsided")
        sw = self.builder.get_object("sw_dblsided")
        osw.remove(sw)
        vp = self.builder.get_object("vp_dblsided")
        vp.override_background_color(Gtk.StateType.NORMAL, Gdk.RGBA(1, 1, 1, 1))

        # Put in the UI
        box_tool.pack_start(sw, True, True, 0)

        # INITIALIZATION
        # Populate combo box
        self.populate_objects_combo("comboboxtext_bottomlayer")

        # Point entry
        self.point_entry = Gtk.Entry()
        box = self.builder.get_object("box_pointbox")
        for child in box.get_children():
            box.remove(child)
        box.pack_start(self.point_entry, False, False, 1)

        # Show the "Tool" tab
        # self.notebook.set_current_page(3)
        self.ui.notebook.set_current_page(3)
        sw.show_all()

    def on_toggle_units(self, widget):
        """
        Callback for the Units radio-button change in the Options tab.
        Changes the application's default units or the current project's units.
        If changing the project's units, the change propagates to all of
        the objects in the project.

        :param widget: Ignored.
        :return: None
        """

        if self.toggle_units_ignore:
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
        label = Gtk.Label("Changing the units of the project causes all geometrical \n" +
                          "properties of all objects to be scaled accordingly. Continue?")
        dialog = Gtk.Dialog("Changing Project Units", self.window, 0,
                            (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                             Gtk.STOCK_OK, Gtk.ResponseType.OK))
        dialog.set_default_size(150, 100)
        dialog.set_modal(True)
        box = dialog.get_content_area()
        box.set_border_width(10)
        box.add(label)
        dialog.show_all()
        response = dialog.run()
        dialog.destroy()

        if response == Gtk.ResponseType.OK:
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
        self.info("Converted units to %s" % self.options["units"])
        self.units_label.set_text("[" + self.options["units"] + "]")

    def on_file_openproject(self, param):
        """
        Callback for menu item File->Open Project. Opens a file chooser and calls
        ``self.open_project()`` after successful selection of a filename.

        :param param: Ignored.
        :return: None
        """

        def on_success(app_obj, filename):
            app_obj.open_project(filename)

        # Runs on_success on worker
        self.file_chooser_action(on_success)

    def on_file_saveproject(self, param):
        """
        Callback for menu item File->Save Project. Saves the project to
        ``self.project_filename`` or calls ``self.on_file_saveprojectas()``
        if set to None. The project is saved by calling ``self.save_project()``.

        :param param: Ignored.
        :return: None
        """

        if self.project_filename is None:
            self.on_file_saveprojectas(None)
        else:
            self.save_project(self.project_filename)
            self.register_recent("project", self.project_filename)
            self.info("Project saved to: " + self.project_filename)

    def on_file_saveprojectas(self, param):
        """
        Callback for menu item File->Save Project As... Opens a file
        chooser and saves the project to the given file via
        ``self.save_project()``.

        :param param: Ignored.
        :return: None
        """

        def on_success(app_obj, filename):
            assert isinstance(app_obj, App)

            try:
                f = open(filename, 'r')
                f.close()
                exists = True
            except IOError:
                exists = False

            msg = "File exists. Overwrite?"
            if exists and self.question_dialog("File exists", msg) == Gtk.ResponseType.CANCEL:
                return

            app_obj.save_project(filename)
            self.project_filename = filename
            self.register_recent("project", filename)
            app_obj.info("Project saved to: " + filename)

        self.file_chooser_save_action(on_success)

    def on_file_saveprojectcopy(self, param):
        """
        Callback for menu item File->Save Project Copy... Opens a file
        chooser and saves the project to the given file via
        ``self.save_project``. It does not update ``self.project_filename`` so
        subsequent save requests are done on the previous known filename.

        :param param: Ignore.
        :return: None
        """

        def on_success(app_obj, filename):
            assert isinstance(app_obj, App)

            try:
                f = open(filename, 'r')
                f.close()
                exists = True
            except IOError:
                exists = False

            msg = "File exists. Overwrite?"
            if exists and self.question_dialog("File exists", msg) == Gtk.ResponseType.CANCEL:
                return

            app_obj.save_project(filename)
            self.register_recent("project", filename)
            app_obj.info("Project copy saved to: " + filename)

        self.file_chooser_save_action(on_success)

    def on_options_app2project(self, param):
        """
        Callback for Options->Transfer Options->App=>Project. Copies options
        from application defaults to project defaults.

        :param param: Ignored.
        :return: None
        """

        self.defaults_read_form()
        self.options.update(self.defaults)
        self.options_write_form()

    def on_options_project2app(self, param):
        """
        Callback for Options->Transfer Options->Project=>App. Copies options
        from project defaults to application defaults.

        :param param: Ignored.
        :return: None
        """

        self.options_read_form()
        self.defaults.update(self.options)
        self.defaults_write_form()

    def on_options_project2object(self, param):
        """
        Callback for Options->Transfer Options->Project=>Object. Copies options
        from project defaults to the currently selected object.

        :param param: Ignored.
        :return: None
        """

        self.options_read_form()
        obj = self.collection.get_active()
        if obj is None:
            self.info("WARNING: No object selected.")
            return
        for option in self.options:
            if option.find(obj.kind + "_") == 0:
                oname = option[len(obj.kind)+1:]
                obj.options[oname] = self.options[option]
        obj.to_form()  # Update UI

    def on_options_object2project(self, param):
        """
        Callback for Options->Transfer Options->Object=>Project. Copies options
        from the currently selected object to project defaults.

        :param param: Ignored.
        :return: None
        """

        obj = self.collection.get_active()
        if obj is None:
            self.info("WARNING: No object selected.")
            return
        obj.read_form()
        for option in obj.options:
            if option in ['name']:  # TODO: Handle this better...
                continue
            self.options[obj.kind + "_" + option] = obj.options[option]
        self.options_write_form()

    def on_options_object2app(self, param):
        """
        Callback for Options->Transfer Options->Object=>App. Copies options
        from the currently selected object to application defaults.

        :param param: Ignored.
        :return: None
        """
        obj = self.collection.get_active()
        if obj is None:
            self.info("WARNING: No object selected.")
            return
        obj.read_form()
        for option in obj.options:
            if option in ['name']:  # TODO: Handle this better...
                continue
            self.defaults[obj.kind + "_" + option] = obj.options[option]
        self.defaults_write_form()

    def on_options_app2object(self, param):
        """
        Callback for Options->Transfer Options->App=>Object. Copies options
        from application defaults to the currently selected object.

        :param param: Ignored.
        :return: None
        """

        self.defaults_read_form()
        obj = self.collection.get_active()
        if obj is None:
            self.info("WARNING: No object selected.")
            return
        for option in self.defaults:
            if option.find(obj.kind + "_") == 0:
                oname = option[len(obj.kind)+1:]
                obj.options[oname] = self.defaults[option]
        obj.to_form()  # Update UI

    def on_file_savedefaults(self, param):
        """
        Callback for menu item File->Save Defaults. Saves application default options
        ``self.defaults`` to defaults.json.

        :param param: Ignored.
        :return: None
        """

        # Read options from file
        try:
            f = open("defaults.json")
            options = f.read()
            f.close()
        except:
            App.log.error("Could not load defaults file.")
            self.info("ERROR: Could not load defaults file.")
            return

        try:
            defaults = json.loads(options)
        except:
            e = sys.exc_info()[0]
            App.log.error("Failed to parse defaults file.")
            App.log.error(str(e))
            self.info("ERROR: Failed to parse defaults file.")
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
            self.info("ERROR: Failed to write defaults to file.")
            return

        self.info("Defaults saved.")

    def on_options_combo_change(self, widget):
        """
        Called when the combo box to choose between application defaults and
        project option changes value. The corresponding variables are
        copied to the UI.

        :param widget: The widget from which this was called. Ignore.
        :return: None
        """

        combo_sel = self.ui.notebook.combo_options.get_active()
        App.log.debug("Options --> %s" % combo_sel)

        # Remove anything else in the box
        # box_children = self.options_box.get_children()
        box_children = self.ui.notebook.options_contents.get_children()
        for child in box_children:
            self.ui.notebook.options_contents.remove(child)

        form = [self.options_form, self.defaults_form][combo_sel]
        self.ui.notebook.options_contents.pack_start(form, False, False, 1)
        form.show_all()

        # self.options2form()

    def on_canvas_configure(self, widget, event):
        """
        Called whenever the canvas changes size. The axes are updated such
        as to use the whole canvas.

        :param widget: Ignored.
        :param event: Ignored.
        :return: None
        """

        self.plotcanvas.auto_adjust_axes()

    def on_row_activated(self, widget, path, col):
        """
        Callback for selection activation (Enter or double-click) on the Project list.
        Switches the notebook page to the object properties form. Calls
        ``self.notebook.set_current_page(1)``.

        :param widget: Ignored.
        :param path: Ignored.
        :param col: Ignored.
        :return: None
        """
        # self.notebook.set_current_page(1)
        self.ui.notebook.set_current_page(1)

    def on_update_plot(self, widget):
        """
        Callback for button on form for all kinds of objects.
        Re-plots the current object only.

        :param widget: The widget from which this was called. Ignored.
        :return: None
        """

        obj = self.collection.get_active()
        obj.read_form()

        self.set_progress_bar(0.5, "Plotting...")

        def thread_func(app_obj):
            assert isinstance(app_obj, App)
            obj.plot()
            GLib.timeout_add(300, lambda: app_obj.set_progress_bar(0.0, "Idle"))

        # Send to worker
        self.worker.add_task(thread_func, [self])

    def on_excellon_tool_choose(self, widget):
        """
        Callback for button on Excellon form to open up a window for
        selecting tools.

        :param widget: The widget from which this was called.
        :return: None
        """
        excellon = self.collection.get_active()
        assert isinstance(excellon, FlatCAMExcellon)
        excellon.show_tool_chooser()

    def on_entry_eval_activate(self, widget):
        """
        Called when an entry is activated (eg. by hitting enter) if
        set to do so. Its text is eval()'d and set to the returned value.
        The current object is updated.

        :param widget:
        :return:
        """
        self.on_eval_update(widget)
        obj = self.collection.get_active()
        assert isinstance(obj, FlatCAMObj)
        obj.read_form()

    def on_eval_update(self, widget):
        """
        Modifies the content of a Gtk.Entry by running
        eval() on its contents and puting it back as a
        string.

        :param widget: The widget from which this was called.
        :return: None
        """
        # TODO: error handling here
        widget.set_text(str(eval(widget.get_text())))

    # def on_cncjob_exportgcode(self, widget):
    #     """
    #     Called from button on CNCjob form to save the G-Code from the object.
    #
    #     :param widget: The widget from which this was called.
    #     :return: None
    #     """
    #     def on_success(app_obj, filename):
    #         cncjob = app_obj.collection.get_active()
    #         f = open(filename, 'w')
    #         f.write(cncjob.gcode)
    #         f.close()
    #         app_obj.info("Saved to: " + filename)
    #
    #     self.file_chooser_save_action(on_success)

    def on_delete(self, widget):
        """
        Delete the currently selected FlatCAMObj.

        :param widget: The widget from which this was called. Ignored.
        :return: None
        """

        # Keep this for later
        name = copy(self.collection.get_active().options["name"])

        # Remove plot
        self.plotcanvas.figure.delaxes(self.collection.get_active().axes)
        self.plotcanvas.auto_adjust_axes()

        # Clear form
        self.setup_component_editor()

        # Remove from dictionary
        self.collection.delete_active()

        self.info("Object deleted: %s" % name)

    def on_toolbar_replot(self, widget):
        """
        Callback for toolbar button. Re-plots all objects.

        :param widget: The widget from which this was called.
        :return: None
        """

        try:
            self.collection.get_active().read_form()
        except AttributeError:
            pass

        self.plot_all()

    def on_clear_plots(self, widget):
        """
        Callback for toolbar button. Clears all plots.

        :param widget: The widget from which this was called.
        :return: None
        """
        self.plotcanvas.clear()

    def on_file_new(self, *param):
        """
        Callback for menu item File->New. Returns the application to its
        startup state. This method is thread-safe.

        :param param: Whatever is passed by the event. Ignore.
        :return: None
        """
        # Remove everything from memory
        App.log.debug("on_file_bew()")

        # GUI things
        def task():
            # Clear plot
            App.log.debug("   self.plotcanvas.clear()")
            self.plotcanvas.clear()

            # Delete data
            App.log.debug("   self.collection.delete_all()")
            self.collection.delete_all()

            # Clear object editor
            App.log.debug("   self.setup_component_editor()")
            self.setup_component_editor()

        GLib.idle_add(task)

        # Clear project filename
        self.project_filename = None

        # Re-fresh project options
        self.on_options_app2project(None)

    def on_filequit(self, param):
        """
        Callback for menu item File->Quit. Closes the application.

        :param param: Whatever is passed by the event. Ignore.
        :return: None
        """

        self.window.destroy()
        Gtk.main_quit()

    def on_closewindow(self, param):
        """
        Callback for closing the main window.

        :param param: Whatever is passed by the event. Ignore.
        :return: None
        """

        self.window.destroy()
        Gtk.main_quit()

    def file_chooser_action(self, on_success):
        """
        Opens the file chooser and runs on_success on a separate thread
        upon completion of valid file choice.

        :param on_success: A function to run upon completion of a valid file
            selection. Takes 2 parameters: The app instance and the filename.
            Note that it is run on a separate thread, therefore it must take the
            appropriate precautions  when accessing shared resources.
        :type on_success: func
        :return: None
        """
        dialog = Gtk.FileChooserDialog("Please choose a file", self.ui,
                                       Gtk.FileChooserAction.OPEN,
                                       (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                                        Gtk.STOCK_OPEN, Gtk.ResponseType.OK))
        response = dialog.run()

        # Works here
        # t = Gtk.TextView()
        # print t

        if response == Gtk.ResponseType.OK:
            filename = dialog.get_filename()
            dialog.destroy()
            # Send to worker.
            self.worker.add_task(on_success, [self, filename])
        elif response == Gtk.ResponseType.CANCEL:
            self.info("Open cancelled.")
            dialog.destroy()

        # Works here
        # t = Gtk.TextView()
        # print t

    def file_chooser_save_action(self, on_success):
        """
        Opens the file chooser and runs on_success upon completion of valid file choice.

        :param on_success: A function to run upon selection of a filename. Takes 2
            parameters: The instance of the application (App) and the chosen filename. This
            gets run immediately in the same thread.
        :return: None
        """
        dialog = Gtk.FileChooserDialog("Save file", self.window,
                                       Gtk.FileChooserAction.SAVE,
                                       (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                                        Gtk.STOCK_SAVE, Gtk.ResponseType.OK))
        dialog.set_current_name("Untitled")
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            filename = dialog.get_filename()
            dialog.destroy()
            on_success(self, filename)
        elif response == Gtk.ResponseType.CANCEL:
            self.info("Save cancelled.")  # print("Cancel clicked")
            dialog.destroy()

    def on_fileopengerber(self, param):
        """
        Callback for menu item File->Open Gerber. Defines a function that is then passed
        to ``self.file_chooser_action()``. It requests the creation of a FlatCAMGerber object
        and updates the progress bar throughout the process.

        :param param: Ignore
        :return: None
        """

        # This works here.
        # t = Gtk.TextView()
        # print t

        self.file_chooser_action(lambda ao, filename: self.open_gerber(filename))

    def on_fileopenexcellon(self, param):
        """
        Callback for menu item File->Open Excellon. Defines a function that is then passed
        to ``self.file_chooser_action()``. It requests the creation of a FlatCAMExcellon object
        and updates the progress bar throughout the process.

        :param param: Ignore
        :return: None
        """

        self.file_chooser_action(lambda ao, filename: self.open_excellon(filename))

    def on_fileopengcode(self, param):
        """
        Callback for menu item File->Open G-Code. Defines a function that is then passed
        to ``self.file_chooser_action()``. It requests the creation of a FlatCAMCNCjob object
        and updates the progress bar throughout the process.

        :param param: Ignore
        :return: None
        """

        self.file_chooser_action(lambda ao, filename: self.open_gcode(filename))

    def on_mouse_move_over_plot(self, event):
        """
        Callback for the mouse motion event over the plot. This event is generated
        by the Matplotlib backend and has been registered in ``self.__init__()``.
        For details, see: http://matplotlib.org/users/event_handling.html

        :param event: Contains information about the event.
        :return: None
        """

        try:  # May fail in case mouse not within axes
            self.ui.position_label.set_label("X: %.4f   Y: %.4f" % (
                event.xdata, event.ydata))
            self.mouse = [event.xdata, event.ydata]

            # for subscriber in self.plot_mousemove_subscribers:
            #     self.plot_mousemove_subscribers[subscriber](event)

        except:
            self.ui.position_label.set_label("")
            self.mouse = None

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
        self.plotcanvas.canvas.grab_focus()

        try:
            App.log.debug('button=%d, x=%d, y=%d, xdata=%f, ydata=%f' % (
                event.button, event.x, event.y, event.xdata, event.ydata))

            self.clipboard.set_text("(%.4f, %.4f)" % (event.xdata, event.ydata), -1)

        except Exception, e:
            App.log.debug("Outside plot?")
            App.log.debug(str(e))

    def on_zoom_in(self, event):
        """
        Callback for zoom-in request. This can be either from the corresponding
        toolbar button or the '3' key when the canvas is focused. Calls ``self.zoom()``.

        :param event: Ignored.
        :return: None
        """
        self.plotcanvas.zoom(1.5)
        return

    def on_zoom_out(self, event):
        """
        Callback for zoom-out request. This can be either from the corresponding
        toolbar button or the '2' key when the canvas is focused. Calls ``self.zoom()``.

        :param event: Ignored.
        :return: None
        """
        self.plotcanvas.zoom(1 / 1.5)

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

        if event.key == 'm':
            if self.measure.toggle_active():
                self.info("Measuring tool ON")
            else:
                self.info("Measuring tool OFF")
            return


class BaseDraw:
    def __init__(self, plotcanvas, name=None):
        """

        :param plotcanvas: The PlotCanvas where the drawing tool will operate.
        :type plotcanvas: PlotCanvas
        """

        self.plotcanvas = plotcanvas

        # Must have unique axes
        charset = "qwertyuiopasdfghjklzxcvbnmQWERTYUIOPASDFGHJKLZXCVBNM1234567890"
        self.name = name or [random.choice(charset) for i in range(20)]
        self.axes = self.plotcanvas.new_axes(self.name)


class DrawingObject(BaseDraw):
    def __init__(self, plotcanvas, name=None):
        """
        Possible objects are:

        * Point
        * Line
        * Rectangle
        * Circle
        * Polygon
        """

        BaseDraw.__init__(self, plotcanvas)
        self.properties = {}

    def plot(self):
        return

    def update_plot(self):
        self.axes.cla()
        self.plot()
        self.plotcanvas.auto_adjust_axes()


class DrawingPoint(DrawingObject):
    def __init__(self, plotcanvas, name=None, coord=None):
        DrawingObject.__init__(self, plotcanvas)

        self.properties.update({
            "coordinate": coord
        })

    def plot(self):
        x, y = self.properties["coordinate"]
        self.axes.plot(x, y, 'o')


class Measurement:
    def __init__(self, container, plotcanvas, update=None):
        self.update = update
        self.container = container
        self.frame = None
        self.label = None
        self.point1 = None
        self.point2 = None
        self.active = False
        self.plotcanvas = plotcanvas
        self.click_subscription = None
        self.move_subscription = None

    def toggle_active(self, *args):
        if self.active:  # Deactivate
            self.active = False
            self.container.remove(self.frame)
            if self.update is not None:
                self.update()
            self.plotcanvas.mpl_disconnect(self.click_subscription)
            self.plotcanvas.mpl_disconnect(self.move_subscription)
            return False
        else:  # Activate
            App.log.debug("DEBUG: Activating Measurement Tool...")
            self.active = True
            self.click_subscription = self.plotcanvas.mpl_connect("button_press_event", self.on_click)
            self.move_subscription = self.plotcanvas.mpl_connect('motion_notify_event', self.on_move)
            self.frame = Gtk.Frame()
            self.frame.set_margin_right(5)
            self.frame.set_margin_top(3)
            align = Gtk.Alignment()
            align.set(0, 0.5, 0, 0)
            align.set_padding(4, 4, 4, 4)
            self.label = Gtk.Label()
            self.label.set_label("Click on a reference point...")
            abox = Gtk.Box.new(Gtk.Orientation.HORIZONTAL, 10)
            abox.pack_start(Gtk.Image.new_from_file('share/measure16.png'), False, False, 0)
            abox.pack_start(self.label, False, False, 0)
            align.add(abox)
            self.frame.add(align)
            self.container.pack_end(self.frame, False, True, 1)
            self.frame.show_all()
            return True

    def on_move(self, event):
        if self.point1 is None:
            self.label.set_label("Click on a reference point...")
        else:
            try:
                dx = event.xdata - self.point1[0]
                dy = event.ydata - self.point1[1]
                d = sqrt(dx**2 + dy**2)
                self.label.set_label("D = %.4f  D(x) = %.4f  D(y) = %.4f" % (d, dx, dy))
            except TypeError:
                pass
        if self.update is not None:
            self.update()

    def on_click(self, event):
            if self.point1 is None:
                self.point1 = (event.xdata, event.ydata)
            else:
                self.point2 = copy(self.point1)
                self.point1 = (event.xdata, event.ydata)
            self.on_move(event)
