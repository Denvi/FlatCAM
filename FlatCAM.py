############################################################
# FlatCAM: 2D Post-processing for Manufacturing            #
# http://caram.cl/software/flatcam                         #
# Author: Juan Pablo Caram (c)                             #
# Date: 2/5/2014                                           #
# MIT Licence                                              #
############################################################

import threading

# TODO: Bundle together. This is just for debugging.
from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GdkPixbuf
from gi.repository import GLib
from gi.repository import GObject
import simplejson as json

from matplotlib.figure import Figure
from numpy import arange, sin, pi
from matplotlib.backends.backend_gtk3agg import FigureCanvasGTK3Agg as FigureCanvas
from mpl_toolkits.axes_grid.anchored_artists import AnchoredText

from camlib import *
import sys
import urllib
import copy


########################################
##            FlatCAMObj              ##
########################################
class FlatCAMObj:
    """
    Base type of objects handled in FlatCAM. These become interactive
    in the GUI, can be plotted, and their options can be modified
    by the user in their respective forms.
    """

    # Instance of the application to which these are related.
    # The app should set this value.
    app = None

    def __init__(self, name):
        self.options = {"name": name}
        self.form_kinds = {"name": "entry_text"}  # Kind of form element for each option
        self.radios = {}  # Name value pairs for radio sets
        self.radios_inv = {}  # Inverse of self.radios
        self.axes = None  # Matplotlib axes
        self.kind = None  # Override with proper name

    def setup_axes(self, figure):
        """
        1) Creates axes if they don't exist. 2) Clears axes. 3) Attaches
        them to figure if not part of the figure. 4) Sets transparent
        background. 5) Sets 1:1 scale aspect ratio.

        :param figure: A Matplotlib.Figure on which to add/configure axes.
        :type figure: matplotlib.figure.Figure
        :return: None
        :rtype: None
        """
        if self.axes is None:
            print "New axes"
            self.axes = figure.add_axes([0.05, 0.05, 0.9, 0.9],
                                        label=self.options["name"])
        elif self.axes not in figure.axes:
            print "Clearing and attaching axes"
            self.axes.cla()
            figure.add_axes(self.axes)
        else:
            print "Clearing Axes"
            self.axes.cla()

        # Remove all decoration. The app's axes will have
        # the ticks and grid.
        self.axes.set_frame_on(False)  # No frame
        self.axes.set_xticks([])  # No tick
        self.axes.set_yticks([])  # No ticks
        self.axes.patch.set_visible(False)  # No background
        self.axes.set_aspect(1)

    def to_form(self):
        """
        Copies options to the UI form.

        :return: None
        """
        for option in self.options:
            self.set_form_item(option)

    def read_form(self):
        """
        Reads form into ``self.options``.

        :return: None
        :rtype: None
        """
        for option in self.options:
            self.read_form_item(option)

    def build_ui(self):
        """
        Sets up the UI/form for this object.

        :return: None
        :rtype: None
        """

        # Where the UI for this object is drawn
        box_selected = self.app.builder.get_object("box_selected")

        # Remove anything else in the box
        box_children = box_selected.get_children()
        for child in box_children:
            box_selected.remove(child)

        osw = self.app.builder.get_object("offscrwindow_" + self.kind)  # offscreenwindow
        sw = self.app.builder.get_object("sw_" + self.kind)  # scrollwindows
        osw.remove(sw)  # TODO: Is this needed ?
        vp = self.app.builder.get_object("vp_" + self.kind)  # Viewport
        vp.override_background_color(Gtk.StateType.NORMAL, Gdk.RGBA(1, 1, 1, 1))

        # Put in the UI
        box_selected.pack_start(sw, True, True, 0)

        entry_name = self.app.builder.get_object("entry_text_" + self.kind + "_name")
        entry_name.connect("activate", self.app.on_activate_name)
        self.to_form()
        sw.show()

    def set_form_item(self, option):
        """
        Copies the specified option to the UI form.

        :param option: Name of the option (Key in ``self.options``).
        :type option: str
        :return: None
        """
        fkind = self.form_kinds[option]
        fname = fkind + "_" + self.kind + "_" + option

        if fkind == 'entry_eval' or fkind == 'entry_text':
            self.app.builder.get_object(fname).set_text(str(self.options[option]))
            return
        if fkind == 'cb':
            self.app.builder.get_object(fname).set_active(self.options[option])
            return
        if fkind == 'radio':
            self.app.builder.get_object(self.radios_inv[option][self.options[option]]).set_active(True)
            return
        print "Unknown kind of form item:", fkind

    def read_form_item(self, option):
        """
        Reads the specified option from the UI form into ``self.options``.

        :param option: Name of the option.
        :type option: str
        :return: None
        """
        fkind = self.form_kinds[option]
        fname = fkind + "_" + self.kind + "_" + option

        if fkind == 'entry_text':
            self.options[option] = self.app.builder.get_object(fname).get_text()
            return
        if fkind == 'entry_eval':
            self.options[option] = self.app.get_eval(fname)
            return
        if fkind == 'cb':
            self.options[option] = self.app.builder.get_object(fname).get_active()
            return
        if fkind == 'radio':
            self.options[option] = self.app.get_radio_value(self.radios[option])
            return
        print "Unknown kind of form item:", fkind

    def plot(self, figure):
        """
        Extend this method! Sets up axes if needed and
        clears them. Descendants must do the actual plotting.
        """
        # Creates the axes if necessary and sets them up.
        self.setup_axes(figure)

    def serialize(self):
        """
        Returns a representation of the object as a dictionary so
        it can be later exported as JSON. Override this method.

        :return: Dictionary representing the object
        :rtype: dict
        """
        return

    def deserialize(self, obj_dict):
        """
        Re-builds an object from its serialized version.

        :param obj_dict: Dictionary representing a FlatCAMObj
        :type obj_dict: dict
        :return None
        """
        return


class FlatCAMGerber(FlatCAMObj, Gerber):
    """
    Represents Gerber code.
    """

    def __init__(self, name):
        Gerber.__init__(self)
        FlatCAMObj.__init__(self, name)

        self.kind = "gerber"

        # The 'name' is already in self.options from FlatCAMObj
        self.options.update({
            "plot": True,
            "mergepolys": True,
            "multicolored": False,
            "solid": False,
            "isotooldia": 0.4 / 25.4,
            "cutoutmargin": 0.2,
            "cutoutgapsize": 0.15,
            "gaps": "tb",
            "noncoppermargin": 0.0,
            "bboxmargin": 0.0,
            "bboxrounded": False
        })

        # The 'name' is already in self.form_kinds from FlatCAMObj
        self.form_kinds.update({
            "plot": "cb",
            "mergepolys": "cb",
            "multicolored": "cb",
            "solid": "cb",
            "isotooldia": "entry_eval",
            "cutoutmargin": "entry_eval",
            "cutoutgapsize": "entry_eval",
            "gaps": "radio",
            "noncoppermargin": "entry_eval",
            "bboxmargin": "entry_eval",
            "bboxrounded": "cb"
        })

        self.radios = {"gaps": {"rb_2tb": "tb", "rb_2lr": "lr", "rb_4": "4"}}
        self.radios_inv = {"gaps": {"tb": "rb_2tb", "lr": "rb_2lr", "4": "rb_4"}}

        # Attributes to be included in serialization
        # Always append to it because it carries contents
        # from predecessors.
        self.ser_attrs += ['options', 'kind']

    def convert_units(self, units):
        """
        Converts the units of the object by scaling dimensions in all geometry
        and options.

        :param units: Units to which to convert the object: "IN" or "MM".
        :type units: str
        :return: None
        :rtype: None
        """

        factor = Gerber.convert_units(self, units)

        self.options['isotooldia'] *= factor
        self.options['cutoutmargin'] *= factor
        self.options['cutoutgapsize'] *= factor
        self.options['noncoppermargin'] *= factor
        self.options['bboxmargin'] *= factor

    def plot(self, figure):
        """
        Plots the object on to the specified figure.

        :param figure: Matplotlib figure on which to plot.
        """

        FlatCAMObj.plot(self, figure)

        if not self.options["plot"]:
            return

        if self.options["mergepolys"]:
            geometry = self.solid_geometry
        else:
            geometry = self.buffered_paths + \
                       [poly['polygon'] for poly in self.regions] + \
                       self.flash_geometry

        if self.options["multicolored"]:
            linespec = '-'
        else:
            linespec = 'k-'

        if self.options["solid"]:
            for poly in geometry:
                # TODO: Too many things hardcoded.
                patch = PolygonPatch(poly,
                                     facecolor="#BBF268",
                                     edgecolor="#006E20",
                                     alpha=0.75,
                                     zorder=2)
                self.axes.add_patch(patch)
        else:
            for poly in geometry:
                x, y = poly.exterior.xy
                self.axes.plot(x, y, linespec)
                for ints in poly.interiors:
                    x, y = ints.coords.xy
                    self.axes.plot(x, y, linespec)

        self.app.canvas.queue_draw()

    def serialize(self):
        return {
            "options": self.options,
            "kind": self.kind
        }


class FlatCAMExcellon(FlatCAMObj, Excellon):
    """
    Represents Excellon/Drill code.
    """

    def __init__(self, name):
        Excellon.__init__(self)
        FlatCAMObj.__init__(self, name)

        self.kind = "excellon"

        self.options.update({
            "plot": True,
            "solid": False,
            "multicolored": False,
            "drillz": -0.1,
            "travelz": 0.1,
            "feedrate": 5.0,
            "toolselection": ""
        })

        self.form_kinds.update({
            "plot": "cb",
            "solid": "cb",
            "multicolored": "cb",
            "drillz": "entry_eval",
            "travelz": "entry_eval",
            "feedrate": "entry_eval",
            "toolselection": "entry_text"
        })

        # TODO: Document this.
        self.tool_cbs = {}

        # Attributes to be included in serialization
        # Always append to it because it carries contents
        # from predecessors.
        self.ser_attrs += ['options', 'kind']

    def convert_units(self, units):
        factor = Excellon.convert_units(self, units)

        self.options['drillz'] *= factor
        self.options['travelz'] *= factor
        self.options['feedrate'] *= factor

    def plot(self, figure):
        FlatCAMObj.plot(self, figure)

        if not self.options["plot"]:
            return

        try:
            _ = iter(self.solid_geometry)
        except TypeError:
            self.solid_geometry = [self.solid_geometry]

        # Plot excellon (All polygons?)
        for geo in self.solid_geometry:
            x, y = geo.exterior.coords.xy
            self.axes.plot(x, y, 'r-')
            for ints in geo.interiors:
                x, y = ints.coords.xy
                self.axes.plot(x, y, 'g-')

        self.app.on_zoom_fit(None)
        self.app.canvas.queue_draw()

    def show_tool_chooser(self):
        win = Gtk.Window()
        box = Gtk.Box(spacing=2)
        box.set_orientation(Gtk.Orientation(1))
        win.add(box)
        for tool in self.tools:
            self.tool_cbs[tool] = Gtk.CheckButton(label=tool + ": " + str(self.tools[tool]))
            box.pack_start(self.tool_cbs[tool], False, False, 1)
        button = Gtk.Button(label="Accept")
        box.pack_start(button, False, False, 1)
        win.show_all()

        def on_accept(widget):
            win.destroy()
            tool_list = []
            for tool in self.tool_cbs:
                if self.tool_cbs[tool].get_active():
                    tool_list.append(tool)
            self.options["toolselection"] = ", ".join(tool_list)
            self.to_form()

        button.connect("activate", on_accept)
        button.connect("clicked", on_accept)


class FlatCAMCNCjob(FlatCAMObj, CNCjob):
    """
    Represents G-Code.
    """

    def __init__(self, name, units="in", kind="generic", z_move=0.1,
                 feedrate=3.0, z_cut=-0.002, tooldia=0.0):
        CNCjob.__init__(self, units=units, kind=kind, z_move=z_move,
                        feedrate=feedrate, z_cut=z_cut, tooldia=tooldia)
        FlatCAMObj.__init__(self, name)

        self.kind = "cncjob"

        self.options.update({
            "plot": True,
            "tooldia": 0.4 / 25.4  # 0.4mm in inches
        })

        self.form_kinds.update({
            "plot": "cb",
            "tooldia": "entry_eval"
        })

        # Attributes to be included in serialization
        # Always append to it because it carries contents
        # from predecessors.
        self.ser_attrs += ['options', 'kind']

    def plot(self, figure):
        FlatCAMObj.plot(self, figure)  # Only sets up axes

        if not self.options["plot"]:
            return

        self.plot2(self.axes, tooldia=self.options["tooldia"])
        self.app.on_zoom_fit(None)
        self.app.canvas.queue_draw()

    def convert_units(self, units):
        factor = CNCjob.convert_units(self, units)
        print "FlatCAMCNCjob.convert_units()"
        self.options["tooldia"] *= factor


class FlatCAMGeometry(FlatCAMObj, Geometry):
    """
    Geometric object not associated with a specific
    format.
    """

    def __init__(self, name):
        FlatCAMObj.__init__(self, name)
        Geometry.__init__(self)

        self.kind = "geometry"

        self.options.update({
            "plot": True,
            "solid": False,
            "multicolored": False,
            "cutz": -0.002,
            "travelz": 0.1,
            "feedrate": 5.0,
            "cnctooldia": 0.4 / 25.4,
            "painttooldia": 0.0625,
            "paintoverlap": 0.15,
            "paintmargin": 0.01
        })

        self.form_kinds.update({
            "plot": "cb",
            "solid": "cb",
            "multicolored": "cb",
            "cutz": "entry_eval",
            "travelz": "entry_eval",
            "feedrate": "entry_eval",
            "cnctooldia": "entry_eval",
            "painttooldia": "entry_eval",
            "paintoverlap": "entry_eval",
            "paintmargin": "entry_eval"
        })

        # Attributes to be included in serialization
        # Always append to it because it carries contents
        # from predecessors.
        self.ser_attrs += ['options', 'kind']

    def scale(self, factor):
        """
        Scales all geometry by a given factor.

        :param factor: Factor by which to scale the object's geometry/
        :type factor: float
        :return: None
        :rtype: None
        """

        if type(self.solid_geometry) == list:
            self.solid_geometry = [affinity.scale(g, factor, factor, origin=(0, 0))
                                   for g in self.solid_geometry]
        else:
            self.solid_geometry = affinity.scale(self.solid_geometry, factor, factor,
                                                 origin=(0, 0))

    def offset(self, vect):
        """
        Offsets all geometry by a given vector/

        :param vect: (x, y) vector by which to offset the object's geometry.
        :type vect: tuple
        :return: None
        :rtype: None
        """

        dx, dy = vect

        if type(self.solid_geometry) == list:
            self.solid_geometry = [affinity.translate(g, xoff=dx, yoff=dy)
                                   for g in self.solid_geometry]
        else:
            self.solid_geometry = affinity.translate(self.solid_geometry, xoff=dx, yoff=dy)

    def convert_units(self, units):
        factor = Geometry.convert_units(self, units)

        self.options['cutz'] *= factor
        self.options['travelz'] *= factor
        self.options['feedrate'] *= factor
        self.options['cnctooldia'] *= factor
        self.options['painttooldia'] *= factor
        self.options['paintmargin'] *= factor

        return factor

    def plot(self, figure):
        """
        Plots the object onto the give figure. Updates the canvas
        when done.

        :param figure: Matplotlib figure on which to plot.
        :type figure: Matplotlib.Figure
        :return: None
        """
        # Sets up and clears self.axes.
        # Attaches axes to the figure... Maybe we want to do that
        # when plotting is complete?
        FlatCAMObj.plot(self, figure)

        if not self.options["plot"]:
            return

        # Make sure solid_geometry is iterable.
        try:
            _ = iter(self.solid_geometry)
        except TypeError:
            self.solid_geometry = [self.solid_geometry]

        for geo in self.solid_geometry:

            if type(geo) == Polygon:
                x, y = geo.exterior.coords.xy
                self.axes.plot(x, y, 'r-')
                for ints in geo.interiors:
                    x, y = ints.coords.xy
                    self.axes.plot(x, y, 'r-')
                continue

            if type(geo) == LineString or type(geo) == LinearRing:
                x, y = geo.coords.xy
                self.axes.plot(x, y, 'r-')
                continue

            if type(geo) == MultiPolygon:
                for poly in geo:
                    x, y = poly.exterior.coords.xy
                    self.axes.plot(x, y, 'r-')
                    for ints in poly.interiors:
                        x, y = ints.coords.xy
                        self.axes.plot(x, y, 'r-')
                continue

            print "WARNING: Did not plot:", str(type(geo))

        self.app.on_zoom_fit(None)
        self.app.canvas.queue_draw()


########################################
##                App                 ##
########################################
class App:
    """
    The main application class. The constructor starts the GUI.
    """

    def __init__(self):
        """
        Starts the application. Takes no parameters.

        :return: app
        :rtype: App
        """

        # Needed to interact with the GUI from other threads.
        GObject.threads_init()

        # GLib.log_set_handler()

        #### GUI ####
        self.gladefile = "FlatCAM.ui"
        self.builder = Gtk.Builder()
        self.builder.add_from_file(self.gladefile)
        self.window = self.builder.get_object("window1")
        self.position_label = self.builder.get_object("label3")
        self.grid = self.builder.get_object("grid1")
        self.notebook = self.builder.get_object("notebook1")
        self.info_label = self.builder.get_object("label_status")
        self.progress_bar = self.builder.get_object("progressbar")
        self.progress_bar.set_show_text(True)
        self.units_label = self.builder.get_object("label_units")

        # White (transparent) background on the "Options" tab.
        self.builder.get_object("vp_options").override_background_color(Gtk.StateType.NORMAL,
                                                                        Gdk.RGBA(1, 1, 1, 1))
        # Combo box to choose between project and application options.
        self.combo_options = self.builder.get_object("combo_options")
        self.combo_options.set_active(1)

        self.setup_project_list()  # The "Project" tab
        self.setup_component_editor()  # The "Selected" tab

        self.setup_toolbar()

        #### Event handling ####
        self.builder.connect_signals(self)

        #### Make plot area ####
        self.figure = None
        self.axes = None
        self.canvas = None
        self.setup_plot()

        self.setup_tooltips()

        #### DATA ####
        self.clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        self.setup_obj_classes()
        self.stuff = {}    # FlatCAMObj's by name
        self.mouse = None  # Mouse coordinates over plot

        # What is selected by the user. It is
        # a key if self.stuff
        self.selected_item_name = None

        # Used to inhibit the on_options_update callback when
        # the options are being changed by the program and not the user.
        self.options_update_ignore = False

        self.toggle_units_ignore = False

        self.defaults = {
            "units": "in"
        }  # Application defaults

        ## Current Project ##
        self.options = {}  # Project options
        self.project_filename = None

        self.form_kinds = {
            "units": "radio"
        }

        self.radios = {"units": {"rb_inch": "IN", "rb_mm": "MM"},
                       "gerber_gaps": {"rb_app_2tb": "tb", "rb_app_2lr": "lr", "rb_app_4": "4"}}
        self.radios_inv = {"units": {"IN": "rb_inch", "MM": "rb_mm"},
                           "gerber_gaps": {"tb": "rb_app_2tb", "lr": "rb_app_2lr", "4": "rb_app_4"}}

        # Options for each kind of FlatCAMObj.
        # Example: 'gerber_plot': 'cb'. The widget name would be: 'cb_app_gerber_plot'
        for FlatCAMClass in [FlatCAMExcellon, FlatCAMGeometry, FlatCAMGerber, FlatCAMCNCjob]:
            obj = FlatCAMClass("no_name")
            for option in obj.form_kinds:
                self.form_kinds[obj.kind + "_" + option] = obj.form_kinds[option]
                # if obj.form_kinds[option] == "radio":
                #     self.radios.update({obj.kind + "_" + option: obj.radios[option]})
                #     self.radios_inv.update({obj.kind + "_" + option: obj.radios_inv[option]})

        ## Event subscriptions ##
        self.plot_click_subscribers = {}
        self.plot_mousemove_subscribers = {}

        ## Tools ##
        self.measure = Measurement(self.axes, self.plot_click_subscribers,
                                   self.plot_mousemove_subscribers,
                                   lambda: self.canvas.queue_draw())

        #### Initialization ####
        self.load_defaults()
        self.options.update(self.defaults)  # Copy app defaults to project options
        self.options2form()  # Populate the app defaults form
        self.units_label.set_text("[" + self.options["units"] + "]")

        #### Check for updates ####
        self.version = 2
        t1 = threading.Thread(target=self.versionCheck)
        t1.daemon = True
        t1.start()

        #### For debugging only ###
        def someThreadFunc(app_obj):
            print "Hello World!"

        t = threading.Thread(target=someThreadFunc, args=(self,))
        t.daemon = True
        t.start()

        ########################################
        ##              START                 ##
        ########################################
        self.icon256 = GdkPixbuf.Pixbuf.new_from_file('share/flatcam_icon256.png')
        self.icon48 = GdkPixbuf.Pixbuf.new_from_file('share/flatcam_icon48.png')
        self.icon16 = GdkPixbuf.Pixbuf.new_from_file('share/flatcam_icon16.png')
        Gtk.Window.set_default_icon_list([self.icon16, self.icon48, self.icon256])
        self.window.set_title("FlatCAM - Alpha 3 UNSTABLE - Check for updates!")
        self.window.set_default_size(900, 600)
        self.window.show_all()

    def setup_toolbar(self):
        toolbar = self.builder.get_object("toolbar_main")

        # Zoom fit
        zf_ico = Gtk.Image.new_from_file('share/zoom_fit32.png')
        zoom_fit = Gtk.ToolButton.new(zf_ico, "")
        zoom_fit.connect("clicked", self.on_zoom_fit)
        zoom_fit.set_tooltip_markup("Zoom Fit.\n(Click on plot and hit <b>1</b>)")
        toolbar.insert(zoom_fit, -1)

        # Zoom out
        zo_ico = Gtk.Image.new_from_file('share/zoom_out32.png')
        zoom_out = Gtk.ToolButton.new(zo_ico, "")
        zoom_out.connect("clicked", self.on_zoom_out)
        zoom_out.set_tooltip_markup("Zoom Out.\n(Click on plot and hit <b>2</b>)")
        toolbar.insert(zoom_out, -1)

        # Zoom in
        zi_ico = Gtk.Image.new_from_file('share/zoom_in32.png')
        zoom_in = Gtk.ToolButton.new(zi_ico, "")
        zoom_in.connect("clicked", self.on_zoom_in)
        zoom_in.set_tooltip_markup("Zoom In.\n(Click on plot and hit <b>3</b>)")
        toolbar.insert(zoom_in, -1)

        # Clear plot
        cp_ico = Gtk.Image.new_from_file('share/clear_plot32.png')
        clear_plot = Gtk.ToolButton.new(cp_ico, "")
        clear_plot.connect("clicked", self.on_clear_plots)
        clear_plot.set_tooltip_markup("Clear Plot")
        toolbar.insert(clear_plot, -1)

        # Replot
        rp_ico = Gtk.Image.new_from_file('share/replot32.png')
        replot = Gtk.ToolButton.new(rp_ico, "")
        replot.connect("clicked", self.on_toolbar_replot)
        replot.set_tooltip_markup("Re-plot all")
        toolbar.insert(replot, -1)

        # Delete item
        del_ico = Gtk.Image.new_from_file('share/delete32.png')
        delete = Gtk.ToolButton.new(del_ico, "")
        delete.connect("clicked", self.on_delete)
        delete.set_tooltip_markup("Delete selected\nobject.")
        toolbar.insert(delete, -1)

    def setup_plot(self):
        """
        Sets up the main plotting area by creating a Matplotlib
        figure in self.canvas, adding axes and configuring them.
        These axes should not be ploted on and are just there to
        display the axes ticks and grid.

        :return: None
        :rtype: None
        """

        self.figure = Figure(dpi=50)
        self.axes = self.figure.add_axes([0.05, 0.05, 0.9, 0.9], label="base", alpha=0.0)
        self.axes.set_aspect(1)
        #t = arange(0.0,5.0,0.01)
        #s = sin(2*pi*t)
        #self.axes.plot(t,s)
        self.axes.grid(True)
        self.figure.patch.set_visible(False)

        self.canvas = FigureCanvas(self.figure)  # a Gtk.DrawingArea
        self.canvas.set_hexpand(1)
        self.canvas.set_vexpand(1)

        # Events
        self.canvas.mpl_connect('button_press_event', self.on_click_over_plot)
        self.canvas.mpl_connect('motion_notify_event', self.on_mouse_move_over_plot)
        self.canvas.set_can_focus(True)  # For key press
        self.canvas.mpl_connect('key_press_event', self.on_key_over_plot)
        #self.canvas.mpl_connect('scroll_event', self.on_scroll_over_plot)
        self.canvas.connect("configure-event", self.on_canvas_configure)

        self.grid.attach(self.canvas, 0, 0, 600, 400)

    def setup_obj_classes(self):
        """
        Sets up application specifics on the FlatCAMObj class.

        :return: None
        """
        FlatCAMObj.app = self

    def setup_project_list(self):
        """
        Sets up list or Tree where whatever has been loaded or created is
        displayed.

        :return: None
        """

        self.store = Gtk.ListStore(str)
        self.tree = Gtk.TreeView(self.store)
        #self.list = Gtk.ListBox()
        self.tree.connect("row_activated", self.on_row_activated)
        self.tree_select = self.tree.get_selection()
        self.signal_id = self.tree_select.connect("changed", self.on_tree_selection_changed)
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Title", renderer, text=0)
        self.tree.append_column(column)
        self.builder.get_object("box_project").pack_start(self.tree, False, False, 1)

    def setup_component_editor(self):
        """
        Initial configuration of the component editor. Creates
        a page titled "Selection" on the notebook on the left
        side of the main window.

        :return: None
        """

        box_selected = self.builder.get_object("box_selected")

        # Remove anything else in the box
        box_children = box_selected.get_children()
        for child in box_children:
            box_selected.remove(child)

        box1 = Gtk.Box(Gtk.Orientation.VERTICAL)
        label1 = Gtk.Label("Choose an item from Project")
        box1.pack_start(label1, True, False, 1)
        box_selected.pack_start(box1, True, True, 0)
        #box_selected.show()
        box1.show()
        label1.show()

    def info(self, text):
        """
        Show text on the status bar.

        :param text: Text to display.
        :type text: str
        :return: None
        """
        self.info_label.set_text(text)

    def zoom(self, factor, center=None):
        """
        Zooms the plot by factor around a given
        center point. Takes care of re-drawing.

        :param factor: Number by which to scale the plot.
        :type factor: float
        :param center: Coordinates [x, y] of the point around which to scale the plot.
        :type center: list
        :return: None
        """
        xmin, xmax = self.axes.get_xlim()
        ymin, ymax = self.axes.get_ylim()
        width = xmax - xmin
        height = ymax - ymin

        if center is None:
            center = [(xmin + xmax) / 2.0, (ymin + ymax) / 2.0]

        # For keeping the point at the pointer location
        relx = (xmax - center[0]) / width
        rely = (ymax - center[1]) / height

        new_width = width / factor
        new_height = height / factor

        xmin = center[0] - new_width * (1 - relx)
        xmax = center[0] + new_width * relx
        ymin = center[1] - new_height * (1 - rely)
        ymax = center[1] + new_height * rely

        for name in self.stuff:
            self.stuff[name].axes.set_xlim((xmin, xmax))
            self.stuff[name].axes.set_ylim((ymin, ymax))
        self.axes.set_xlim((xmin, xmax))
        self.axes.set_ylim((ymin, ymax))

        self.canvas.queue_draw()

    def build_list(self):
        """
        Clears and re-populates the list of objects in currently
        in the project.

        :return: None
        """
        print "build_list(): clearing"
        self.tree_select.unselect_all()
        self.store.clear()
        print "repopulating...",
        for key in self.stuff:
            print key,
            self.store.append([key])
        print

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
        self.clear_plots()
        self.set_progress_bar(0.1, "Re-plotting...")

        def thread_func(app_obj):
            percentage = 0.1
            try:
                delta = 0.9 / len(self.stuff)
            except ZeroDivisionError:
                GLib.timeout_add(300, lambda: app_obj.set_progress_bar(0.0, ""))
                return
            for i in self.stuff:
                self.stuff[i].plot(self.figure)
                percentage += delta
                GLib.idle_add(lambda: app_obj.set_progress_bar(percentage, "Re-plotting..."))

            self.on_zoom_fit(None)
            self.axes.grid(True)
            self.canvas.queue_draw()
            GLib.timeout_add(300, lambda: app_obj.set_progress_bar(0.0, ""))

        t = threading.Thread(target=thread_func, args=(self,))
        t.daemon = True
        t.start()

    def clear_plots(self):
        """
        Clears self.axes and self.figure.

        :return: None
        """

        # TODO: Create a setup_axes method that gets called here and in setup_plot?
        self.axes.cla()
        self.figure.clf()
        self.figure.add_axes(self.axes)
        self.axes.set_aspect(1)
        self.axes.grid(True)
        self.canvas.queue_draw()

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

    def set_list_selection(self, name):
        """
        Marks a given object as selected in the list ob objects
        in the GUI. This selection will in turn trigger
        ``self.on_tree_selection_changed()``.

        :param name: Name of the object.
        :type name: str
        :return: None
        """

        iter = self.store.get_iter_first()
        while iter is not None and self.store[iter][0] != name:
            iter = self.store.iter_next(iter)
        self.tree_select.unselect_all()
        self.tree_select.select_iter(iter)

        # Need to return False such that GLib.idle_add
        # or .timeout_add do not repear.
        return False

    def new_object(self, kind, name, initialize):
        """
        Creates a new specalized FlatCAMObj and attaches it to the application,
        this is, updates the GUI accordingly, any other records and plots it.

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

        # Check for existing name
        if name in self.stuff:
            self.info("Rename " + name + " in project first.")
            return None

        # Create object
        classdict = {
            "gerber": FlatCAMGerber,
            "excellon": FlatCAMExcellon,
            "cncjob": FlatCAMCNCjob,
            "geometry": FlatCAMGeometry
        }
        obj = classdict[kind](name)
        obj.units = self.options["units"]  # TODO: The constructor should look at defaults.

        # Initialize as per user request
        # User must take care to implement initialize
        # in a thread-safe way as is is likely that we
        # have been invoked in a separate thread.
        #initialize(obj, self)

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
        self.stuff[name] = obj

        # Update GUI list and select it (Thread-safe?)
        self.store.append([name])
        #self.build_list()
        GLib.idle_add(lambda: self.set_list_selection(name))
        # TODO: Gtk.notebook.set_current_page is not known to
        # TODO: return False. Fix this??
        GLib.timeout_add(100, lambda: self.notebook.set_current_page(1))

        # Plot
        # TODO: (Thread-safe?)
        obj.plot(self.figure)
        obj.axes.set_alpha(0.0)
        self.on_zoom_fit(None)

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
        self.progress_bar.set_text(text)
        self.progress_bar.set_fraction(percentage)
        return False

    def get_current(self):
        """
        Returns the currently selected FlatCAMObj in the application.

        :return: Currently selected FlatCAMObj in the application.
        :rtype: FlatCAMObj or None
        """

        # TODO: Could possibly read the form into the object here.
        # But there are some cases when the form for the object
        # is not up yet. See on_tree_selection_changed.

        try:
            return self.stuff[self.selected_item_name]
        except:
            return None

    def adjust_axes(self, xmin, ymin, xmax, ymax):
        """
        Adjusts axes of all plots while maintaining the use of the whole canvas
        and an aspect ratio to 1:1 between x and y axes. The parameters are an original
        request that will be modified to fit these restrictions.

        :param xmin: Requested minimum value for the X axis.
        :type xmin: float
        :param ymin: Requested minimum value for the Y axis.
        :type ymin: float
        :param xmax: Requested maximum value for the X axis.
        :type xmax: float
        :param ymax: Requested maximum value for the Y axis.
        :type ymax: float
        :return: None
        """
        m_x = 15  # pixels
        m_y = 25  # pixels
        width = xmax - xmin
        height = ymax - ymin
        try:
            r = width / height
        except:
            print "ERROR: Height is", height
            return
        Fw, Fh = self.canvas.get_width_height()
        Fr = float(Fw) / Fh
        x_ratio = float(m_x) / Fw
        y_ratio = float(m_y) / Fh

        if r > Fr:
            ycenter = (ymin + ymax) / 2.0
            newheight = height * r / Fr
            ymin = ycenter - newheight / 2.0
            ymax = ycenter + newheight / 2.0
        else:
            xcenter = (xmax + ymin) / 2.0
            newwidth = width * Fr / r
            xmin = xcenter - newwidth / 2.0
            xmax = xcenter + newwidth / 2.0

        for name in self.stuff:
            if self.stuff[name].axes is None:
                continue
            self.stuff[name].axes.set_xlim((xmin, xmax))
            self.stuff[name].axes.set_ylim((ymin, ymax))
            self.stuff[name].axes.set_position([x_ratio, y_ratio,
                                                1 - 2 * x_ratio, 1 - 2 * y_ratio])
        self.axes.set_xlim((xmin, xmax))
        self.axes.set_ylim((ymin, ymax))
        self.axes.set_position([x_ratio, y_ratio,
                                1 - 2 * x_ratio, 1 - 2 * y_ratio])

        self.canvas.queue_draw()

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
        except:
            self.info("ERROR: Could not load defaults file.")
            return

        try:
            defaults = json.loads(options)
        except:
            e = sys.exc_info()[0]
            print e
            self.info("ERROR: Failed to parse defaults file.")
            return
        self.defaults.update(defaults)

    def read_form(self):
        """
        Reads the options form into self.defaults/self.options.

        :return: None
        :rtype: None
        """
        combo_sel = self.combo_options.get_active()
        options_set = [self.options, self.defaults][combo_sel]
        for option in options_set:
            self.read_form_item(option, options_set)

    def read_form_item(self, name, dest):
        """
        Reads the value of a form item in the defaults/options form and
        saves it to the corresponding dictionary.

        :param name: Name of the form item. A key in ``self.defaults`` or
            ``self.options``.
        :type name: str
        :param dest: Dictionary to which to save the value.
        :type dest: dict
        :return: None
        """
        fkind = self.form_kinds[name]
        fname = fkind + "_" + "app" + "_" + name

        if fkind == 'entry_text':
            dest[name] = self.builder.get_object(fname).get_text()
            return
        if fkind == 'entry_eval':
            dest[name] = self.get_eval(fname)
            return
        if fkind == 'cb':
            dest[name] = self.builder.get_object(fname).get_active()
            return
        if fkind == 'radio':
            dest[name] = self.get_radio_value(self.radios[name])
            return
        print "Unknown kind of form item:", fkind

    def options2form(self):
        """
        Sets the 'Project Options' or 'Application Defaults' form with values from
        ``self.options`` or ``self.defaults``.

        :return: None
        :rtype: None
        """

        # Set the on-change callback to do nothing while we do the changes.
        self.options_update_ignore = True
        self.toggle_units_ignore = True

        combo_sel = self.combo_options.get_active()
        options_set = [self.options, self.defaults][combo_sel]
        for option in options_set:
            self.set_form_item(option, options_set[option])

        self.options_update_ignore = False
        self.toggle_units_ignore = False

    def set_form_item(self, name, value):
        """
        Sets a form item 'name' in the GUI with the given 'value'. The syntax of
        form names in the GUI is <kind>_app_<name>, where kind is one of: rb (radio button),
        cb (check button), entry_eval or entry_text (entry), combo (combo box). name is
        whatever name it's been given. For self.defaults, name is a key in the dictionary.

        :param name: Name of the form field.
        :type name: str
        :param value: The value to set the form field to.
        :type value: Depends on field kind.
        :return: None
        """
        if name not in self.form_kinds:
            print "WARNING: Tried to set unknown option/form item:", name
            return
        fkind = self.form_kinds[name]
        fname = fkind + "_" + "app" + "_" + name
        if fkind == 'entry_eval' or fkind == 'entry_text':
            try:
                self.builder.get_object(fname).set_text(str(value))
            except:
                print "ERROR: Failed to set value of %s to %s" % (fname, str(value))
            return
        if fkind == 'cb':
            try:
                self.builder.get_object(fname).set_active(value)
            except:
                print "ERROR: Failed to set value of %s to %s" % (fname, str(value))
            return
        if fkind == 'radio':
            try:
                self.builder.get_object(self.radios_inv[name][value]).set_active(True)
            except:
                print "ERROR: Failed to set value of %s to %s" % (fname, str(value))
            return
        print "Unknown kind of form item:", fkind

    def save_project(self, filename):
        """
        Saves the current project to the specified file.

        :param filename: Name of the file in which to save.
        :type filename: str
        :return: None
        """

        # Capture the latest changes
        try:
            self.get_current().read_form()
        except:
            pass

        d = {"objs": [self.stuff[o].to_dict() for o in self.stuff],
             "options": self.options}

        try:
            f = open(filename, 'w')
        except:
            print "ERROR: Failed to open file for saving:", filename
            return

        try:
            json.dump(d, f, default=to_dict)
        except:
            print "ERROR: File open but failed to write:", filename
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

        try:
            f = open(filename, 'r')
        except:
            print "WARNING: Failed to open project file:", filename
            return

        try:
            d = json.load(f, object_hook=dict2obj)
        except:
            print "WARNING: Failed to parse project file:", filename
            f.close()
            return

        # Clear the current project
        self.on_file_new(None)

        # Project options
        self.options.update(d['options'])
        self.project_filename = filename
        self.units_label.set_text(self.options["units"])

        # Re create objects
        for obj in d['objs']:
            def obj_init(obj_inst, app_inst):
                obj_inst.from_dict(obj)
            self.new_object(obj['kind'], obj['options']['name'], obj_init)

        self.info("Project loaded from: " + filename)

    def populate_objects_combo(self, combo):
        """
        Populates a Gtk.Comboboxtext with the list of the object in the project.

        :param combo: Name or instance of the comboboxtext.
        :type combo: str or Gtk.ComboBoxText
        :return: None
        """
        print "Populating combo!"
        if type(combo) == str:
            combo = self.builder.get_object(combo)

        combo.remove_all()
        for obj in self.stuff:
            combo.append_text(obj)

    def versionCheck(self):
        """
        Checks for the latest version of the program. Alerts the
        user if theirs is outdated. This method is meant to be run
        in a saeparate thread.

        :return: None
        """

        try:
            f = urllib.urlopen("http://caram.cl/flatcam/VERSION")  # TODO: Hardcoded.
        except:
            GLib.idle_add(lambda: self.info("ERROR trying to check for latest version."))
            return

        try:
            data = json.load(f)
        except:
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

    def setup_tooltips(self):
        tooltips = {
            "cb_gerber_plot": "Plot this object on the main window.",
            "cb_gerber_mergepolys": "Show overlapping polygons as single.",
            "cb_gerber_solid": "Paint inside polygons.",
            "cb_gerber_multicolored": "Draw polygons with different polygons."
        }

        for widget in tooltips:
            self.builder.get_object(widget).set_tooltip_markup(tooltips[widget])

    def do_nothing(self, param):
        return

    ########################################
    ##         EVENT HANDLERS             ##
    ########################################
    def on_offset_object(self, widget):
        """
        Offsets the object's geometry by the vector specified
        in the form. Re-plots.

        :param widget: Ignored
        :return: None
        """

        obj = self.get_current()
        obj.read_form()
        assert isinstance(obj, FlatCAMObj)
        try:
            vect = self.get_eval("entry_eval_" + obj.kind + "_offset")
        except:
            self.info("ERROR: Vector is not in (x, y) format.")
            return
        assert isinstance(obj, Geometry)
        obj.offset(vect)
        obj.plot(self.figure)
        self.on_zoom_fit(None)  # TODO: Change this. Just done to aline all axes.
        return

    def on_cb_plot_toggled(self, widget):
        """
        Callback for toggling the "Plot" checkbox. Re-plots.

        :param widget: Ignored.
        :return: None
        """

        self.get_current().read_form()
        self.get_current().plot(self.figure)
        self.on_zoom_fit(None)  # TODO: Does not update correctly otherwise.

    def on_about(self, widget):
        """
        Opens the 'About' dialog box.

        :param widget: Ignored.
        :return: None
        """

        about = self.builder.get_object("aboutdialog")
        response = about.run()
        #about.destroy()
        about.hide()

    def on_create_mirror(self, widget):
        """
        Creates a mirror image of a Gerber object to be used as a bottom
        copper layer.

        :param widget: Ignored.
        :return: None
        """

        # Layer to mirror
        gerb_name = self.builder.get_object("comboboxtext_bottomlayer").get_active_text()
        gerb = self.stuff[gerb_name]

        # For now, lets limit to Gerbers.
        assert isinstance(gerb, FlatCAMGerber)

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
            bb_obj = self.stuff[name]
            xmin, ymin, xmax, ymax = bb_obj.bounds()
            px = 0.5*(xmin+xmax)
            py = 0.5*(ymin+ymax)

        # Do the mirroring
        xscale, yscale = {"X": (1.0, -1.0), "Y": (-1.0, 1.0)}[axis]
        mirrored = affinity.scale(gerb.solid_geometry, xscale, yscale, origin=(px, py))

        def obj_init(obj_inst, app_inst):
            obj_inst.solid_geometry = mirrored

        self.new_object("gerber", gerb.options["name"] + "_mirror", obj_init)

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
            bb_obj = self.stuff[name]
            xmin, ymin, xmax, ymax = bb_obj.bounds()
            px = 0.5*(xmin+xmax)
            py = 0.5*(ymin+ymax)
        xscale, yscale = {"X": (1.0, -1.0), "Y": (-1.0, 1.0)}[axis]

        # Tools
        tools = {"1": self.get_eval("entry_dblsided_alignholediam")}

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
        self.notebook.set_current_page(3)
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

        combo_sel = self.combo_options.get_active()
        options_set = [self.options, self.defaults][combo_sel]

        # Options to scale
        dimensions = ['gerber_isotooldia', 'gerber_cutoutmargin', 'gerber_cutoutgapsize',
                      'gerber_noncoppermargin', 'gerber_bboxmargin', 'excellon_drillz',
                      'excellon_travelz', 'excellon_feedrate', 'cncjob_tooldia',
                      'geometry_cutz', 'geometry_travelz', 'geometry_feedrate',
                      'geometry_cnctooldia', 'geometry_painttooldia', 'geometry_paintoverlap',
                      'geometry_paintmargin']

        def scale_options(factor):
            for dim in dimensions:
                options_set[dim] *= factor

        # The scaling factor depending on choice of units.
        factor = 1/25.4
        if self.builder.get_object('rb_mm').get_active():
            factor = 25.4

        # App units. Convert without warning.
        if combo_sel == 1:
            self.read_form()
            scale_options(factor)
            self.options2form()
            return

        # Changing project units. Warn user.
        label = Gtk.Label("Changing the units of the project causes all geometrical \n" + \
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
            #print "Converting units..."
            #print "Converting options..."
            self.read_form()
            scale_options(factor)
            self.options2form()
            for obj in self.stuff:
                units = self.get_radio_value({"rb_mm": "MM", "rb_inch": "IN"})
                #print "Converting ", obj, " to ", units
                self.stuff[obj].convert_units(units)
            current = self.get_current()
            if current is not None:
                current.to_form()
            self.plot_all()
        else:
            # Undo toggling
            self.toggle_units_ignore = True
            if self.builder.get_object('rb_mm').get_active():
                self.builder.get_object('rb_inch').set_active(True)
            else:
                self.builder.get_object('rb_mm').set_active(True)
            self.toggle_units_ignore = False

        self.read_form()
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
            app_obj.save_project(filename)
            self.project_filename = filename
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
            app_obj.save_project(filename)
            app_obj.info("Project copy saved to: " + filename)

        self.file_chooser_save_action(on_success)

    def on_options_app2project(self, param):
        """
        Callback for Options->Transfer Options->App=>Project. Copies options
        from application defaults to project defaults.

        :param param: Ignored.
        :return: None
        """

        self.options.update(self.defaults)
        self.options2form()  # Update UI

    def on_options_project2app(self, param):
        """
        Callback for Options->Transfer Options->Project=>App. Copies options
        from project defaults to application defaults.

        :param param: Ignored.
        :return: None
        """

        self.defaults.update(self.options)
        self.options2form()  # Update UI

    def on_options_project2object(self, param):
        """
        Callback for Options->Transfer Options->Project=>Object. Copies options
        from project defaults to the currently selected object.

        :param param: Ignored.
        :return: None
        """

        obj = self.get_current()
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

        obj = self.get_current()
        if obj is None:
            self.info("WARNING: No object selected.")
            return
        obj.read_form()
        for option in obj.options:
            if option in ['name']:  # TODO: Handle this better...
                continue
            self.options[obj.kind + "_" + option] = obj.options[option]
        self.options2form()  # Update UI

    def on_options_object2app(self, param):
        """
        Callback for Options->Transfer Options->Object=>App. Copies options
        from the currently selected object to application defaults.

        :param param: Ignored.
        :return: None
        """
        obj = self.get_current()
        if obj is None:
            self.info("WARNING: No object selected.")
            return
        obj.read_form()
        for option in obj.options:
            if option in ['name']:  # TODO: Handle this better...
                continue
            self.defaults[obj.kind + "_" + option] = obj.options[option]
        self.options2form()  # Update UI

    def on_options_app2object(self, param):
        """
        Callback for Options->Transfer Options->App=>Object. Copies options
        from application defaults to the currently selected object.

        :param param: Ignored.
        :return: None
        """

        obj = self.get_current()
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

        try:
            f = open("defaults.json")
            options = f.read()
            f.close()
        except:
            self.info("ERROR: Could not load defaults file.")
            return

        try:
            defaults = json.loads(options)
        except:
            e = sys.exc_info()[0]
            print e
            self.info("ERROR: Failed to parse defaults file.")
            return

        assert isinstance(defaults, dict)
        defaults.update(self.defaults)

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

        #combo_sel = self.combo_options.get_active()
        #print "Options --> ", combo_sel
        self.options2form()

    def on_options_update(self, widget):
        """
        Called whenever a value in the options/defaults form changes.
        All values are updated. Can be inhibited by setting ``self.options_update_ignore = True``,
        which may be necessary when updating the UI from code and not by the user.

        :param widget: The widget from which this was called. Ignore.
        :return: None
        """

        if self.options_update_ignore:
            return
        self.read_form()

    def on_scale_object(self, widget):
        """
        Callback for request to change an objects geometry scale. The object
        is re-scaled and replotted.

        :param widget: Ignored.
        :return: None
        """

        obj = self.get_current()
        factor = self.get_eval("entry_eval_" + obj.kind + "_scalefactor")
        obj.scale(factor)
        obj.to_form()
        self.on_update_plot(None)

    def on_canvas_configure(self, widget, event):
        """
        Called whenever the canvas changes size. The axes are updated such
        as to use the whole canvas.

        :param widget: Ignored.
        :param event: Ignored.
        :return: None
        """

        xmin, xmax = self.axes.get_xlim()
        ymin, ymax = self.axes.get_ylim()
        self.adjust_axes(xmin, ymin, xmax, ymax)

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
        self.notebook.set_current_page(1)

    def on_generate_gerber_bounding_box(self, widget):
        """
        Callback for request from the Gerber form to generate a bounding box for the
        geometry in the object. Creates a FlatCAMGeometry with the bounding box.
        The box can have rounded corners if specified in the form.

        :param widget: Ignored.
        :return: None
        """
        # TODO: Use Gerber.get_bounding_box(...)
        gerber = self.get_current()
        gerber.read_form()
        name = gerber.options["name"] + "_bbox"

        def geo_init(geo_obj, app_obj):
            assert isinstance(geo_obj, FlatCAMGeometry)
            # Bounding box with rounded corners
            bounding_box = gerber.solid_geometry.envelope.buffer(gerber.options["bboxmargin"])
            if not gerber.options["bboxrounded"]:  # Remove rounded corners
                bounding_box = bounding_box.envelope
            geo_obj.solid_geometry = bounding_box

        self.new_object("geometry", name, geo_init)

    def on_update_plot(self, widget):
        """
        Callback for button on form for all kinds of objects.
        Re-plots the current object only.

        :param widget: The widget from which this was called.
        :return: None
        """

        obj = self.get_current()
        obj.read_form()

        self.set_progress_bar(0.5, "Plotting...")

        def thread_func(app_obj):
            assert isinstance(app_obj, App)
            #GLib.idle_add(lambda: app_obj.set_progress_bar(0.5, "Plotting..."))
            #GLib.idle_add(lambda: app_obj.get_current().plot(app_obj.figure))
            obj.plot(app_obj.figure)
            GLib.idle_add(lambda: app_obj.on_zoom_fit(None))
            GLib.timeout_add(300, lambda: app_obj.set_progress_bar(0.0, "Idle"))

        t = threading.Thread(target=thread_func, args=(self,))
        t.daemon = True
        t.start()

    def on_generate_excellon_cncjob(self, widget):
        """
        Callback for button active/click on Excellon form to
        create a CNC Job for the Excellon file.

        :param widget: Ignored
        :return: None
        """

        excellon = self.get_current()
        excellon.read_form()
        job_name = excellon.options["name"] + "_cnc"

        # Object initialization function for app.new_object()
        def job_init(job_obj, app_obj):
            # excellon_ = self.get_current()
            # assert isinstance(excellon_, FlatCAMExcellon)
            assert isinstance(job_obj, FlatCAMCNCjob)

            GLib.idle_add(lambda: app_obj.set_progress_bar(0.2, "Creating CNC Job..."))
            job_obj.z_cut = excellon.options["drillz"]
            job_obj.z_move = excellon.options["travelz"]
            job_obj.feedrate = excellon.options["feedrate"]
            # There could be more than one drill size...
            # job_obj.tooldia =   # TODO: duplicate variable!
            # job_obj.options["tooldia"] =
            job_obj.generate_from_excellon_by_tool(excellon, excellon.options["toolselection"])

            GLib.idle_add(lambda: app_obj.set_progress_bar(0.5, "Parsing G-Code..."))
            job_obj.gcode_parse()

            GLib.idle_add(lambda: app_obj.set_progress_bar(0.6, "Creating New Geometry..."))
            job_obj.create_geometry()

            GLib.idle_add(lambda: app_obj.set_progress_bar(0.8, "Plotting..."))

        # To be run in separate thread
        def job_thread(app_obj):
            app_obj.new_object("cncjob", job_name, job_init)
            GLib.idle_add(lambda: app_obj.set_progress_bar(1.0, "Done!"))
            GLib.timeout_add_seconds(1, lambda: app_obj.set_progress_bar(0.0, ""))

        # Start the thread
        t = threading.Thread(target=job_thread, args=(self,))
        t.daemon = True
        t.start()

    def on_excellon_tool_choose(self, widget):
        """
        Callback for button on Excellon form to open up a window for
        selecting tools.

        :param widget: The widget from which this was called.
        :return: None
        """
        excellon = self.get_current()
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
        obj = self.get_current()
        assert isinstance(obj, FlatCAMObj)
        obj.read_form()

    def on_gerber_generate_noncopper(self, widget):
        """
        Callback for button on Gerber form to create a geometry object
        with polygons covering the area without copper or negative of the
        Gerber.

        :param widget: The widget from which this was called.
        :return: None
        """

        gerb = self.get_current()
        gerb.read_form()
        name = gerb.options["name"] + "_noncopper"

        def geo_init(geo_obj, app_obj):
            assert isinstance(geo_obj, FlatCAMGeometry)
            bounding_box = gerb.solid_geometry.envelope.buffer(gerb.options["noncoppermargin"])
            non_copper = bounding_box.difference(gerb.solid_geometry)
            geo_obj.solid_geometry = non_copper

        # TODO: Check for None
        self.new_object("geometry", name, geo_init)

    def on_gerber_generate_cutout(self, widget):
        """
        Callback for button on Gerber form to create geometry with lines
        for cutting off the board.

        :param widget: The widget from which this was called.
        :return: None
        """

        gerb = self.get_current()
        gerb.read_form()
        name = gerb.options["name"] + "_cutout"

        def geo_init(geo_obj, app_obj):
            margin = gerb.options["cutoutmargin"]
            gap_size = gerb.options["cutoutgapsize"]
            minx, miny, maxx, maxy = gerb.bounds()
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
            cuts = cases[app.get_radio_value({"rb_2tb": "tb", "rb_2lr": "lr", "rb_4": "4"})]
            geo_obj.solid_geometry = cascaded_union([LineString(segment) for segment in cuts])

        # TODO: Check for None
        self.new_object("geometry", name, geo_init)

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

    def on_generate_isolation(self, widget):
        """
        Callback for button on Gerber form to create isolation routing geometry.

        :param widget: The widget from which this was called.
        :return: None
        """

        gerb = self.get_current()
        gerb.read_form()
        iso_name = gerb.options["name"] + "_iso"

        def iso_init(geo_obj, app_obj):
            # Propagate options
            geo_obj.options["cnctooldia"] = gerb.options["isotooldia"]

            geo_obj.solid_geometry = gerb.isolation_geometry(gerb.options["isotooldia"] / 2.0)
            app_obj.info("Isolation geometry created: %s" % geo_obj.options["name"])

        # TODO: Do something if this is None. Offer changing name?
        self.new_object("geometry", iso_name, iso_init)

    def on_generate_cncjob(self, widget):
        """
        Callback for button on geometry form to generate CNC job.

        :param widget: The widget from which this was called.
        :return: None
        """

        source_geo = self.get_current()
        source_geo.read_form()
        job_name = source_geo.options["name"] + "_cnc"

        # Object initialization function for app.new_object()
        # RUNNING ON SEPARATE THREAD!
        def job_init(job_obj, app_obj):
            assert isinstance(job_obj, FlatCAMCNCjob)
            # Propagate options
            job_obj.options["tooldia"] = source_geo.options["cnctooldia"]

            GLib.idle_add(lambda: app_obj.set_progress_bar(0.2, "Creating CNC Job..."))
            job_obj.z_cut = source_geo.options["cutz"]
            job_obj.z_move = source_geo.options["travelz"]
            job_obj.feedrate = source_geo.options["feedrate"]

            GLib.idle_add(lambda: app_obj.set_progress_bar(0.4, "Analyzing Geometry..."))
            # TODO: The tolerance should not be hard coded. Just for testing.
            job_obj.generate_from_geometry(source_geo, tolerance=0.0005)

            GLib.idle_add(lambda: app_obj.set_progress_bar(0.5, "Parsing G-Code..."))
            job_obj.gcode_parse()

            # TODO: job_obj.create_geometry creates stuff that is not used.
            #GLib.idle_add(lambda: app_obj.set_progress_bar(0.6, "Creating New Geometry..."))
            #job_obj.create_geometry()

            GLib.idle_add(lambda: app_obj.set_progress_bar(0.8, "Plotting..."))

        # To be run in separate thread
        def job_thread(app_obj):
            app_obj.new_object("cncjob", job_name, job_init)
            GLib.idle_add(lambda: app_obj.info("CNCjob created: %s" % job_name))
            GLib.idle_add(lambda: app_obj.set_progress_bar(1.0, "Done!"))
            GLib.timeout_add_seconds(1, lambda: app_obj.set_progress_bar(0.0, ""))

        # Start the thread
        t = threading.Thread(target=job_thread, args=(self,))
        t.daemon = True
        t.start()

    def on_generate_paintarea(self, widget):
        """
        Callback for button on geometry form.
        Subscribes to the "Click on plot" event and continues
        after the click. Finds the polygon containing
        the clicked point and runs clear_poly() on it, resulting
        in a new FlatCAMGeometry object.

        :param widget: The  widget from which this was called.
        :return: None
        """

        self.info("Click inside the desired polygon.")
        geo = self.get_current()
        geo.read_form()
        assert isinstance(geo, FlatCAMGeometry)
        tooldia = geo.options["painttooldia"]
        overlap = geo.options["paintoverlap"]

        # To be called after clicking on the plot.
        def doit(event):
            self.plot_click_subscribers.pop("generate_paintarea")
            self.info("")
            point = [event.xdata, event.ydata]
            poly = find_polygon(geo.solid_geometry, point)

            # Initializes the new geometry object
            def gen_paintarea(geo_obj, app_obj):
                assert isinstance(geo_obj, FlatCAMGeometry)
                assert isinstance(app_obj, App)
                cp = clear_poly(poly.buffer(-geo.options["paintmargin"]), tooldia, overlap)
                geo_obj.solid_geometry = cp
                geo_obj.options["cnctooldia"] = tooldia

            name = self.selected_item_name + "_paint"
            self.new_object("geometry", name, gen_paintarea)

        self.plot_click_subscribers["generate_paintarea"] = doit

    def on_cncjob_exportgcode(self, widget):
        """
        Called from button on CNCjob form to save the G-Code from the object.

        :param widget: The widget from which this was called.
        :return: None
        """
        def on_success(app_obj, filename):
            cncjob = app_obj.get_current()
            f = open(filename, 'w')
            f.write(cncjob.gcode)
            f.close()
            app_obj.info("Saved to: " + filename)

        self.file_chooser_save_action(on_success)

    def on_delete(self, widget):
        """
        Delete the currently selected FlatCAMObj.

        :param widget: The widget from which this was called.
        :return: None
        """

        # Keep this for later
        name = copy.copy(self.selected_item_name)

        # Remove plot
        self.figure.delaxes(self.get_current().axes)
        self.canvas.queue_draw()

        # Remove from dictionary
        self.stuff.pop(self.selected_item_name)

        # Update UI
        self.build_list()  # Update the items list

        self.info("Object deleted: %s" % name)

    def on_toolbar_replot(self, widget):
        """
        Callback for toolbar button. Re-plots all objects.

        :param widget: The widget from which this was called.
        :return: None
        """

        self.get_current().read_form()

        self.plot_all()

    def on_clear_plots(self, widget):
        """
        Callback for toolbar button. Clears all plots.

        :param widget: The widget from which this was called.
        :return: None
        """
        self.clear_plots()

    def on_activate_name(self, entry):
        """
        Hitting 'Enter' after changing the name of an item
        updates the item dictionary and re-builds the item list.

        :param entry: The widget from which this was called.
        :return: None
        """

        # Disconnect event listener
        self.tree.get_selection().disconnect(self.signal_id)

        new_name = entry.get_text()  # Get from form
        self.stuff[new_name] = self.stuff.pop(self.selected_item_name)  # Update dictionary
        self.stuff[new_name].options["name"] = new_name  # update object
        self.info('Name change: ' + self.selected_item_name + " to " + new_name)

        self.selected_item_name = new_name  # Update selection name

        self.build_list()  # Update the items list

        # Reconnect event listener
        self.signal_id = self.tree.get_selection().connect(
            "changed", self.on_tree_selection_changed)

    def on_tree_selection_changed(self, selection):
        """
        Callback for selection change in the project list. This changes
        the currently selected FlatCAMObj.

        :param selection: Selection associated to the project tree or list
        :type selection: Gtk.TreeSelection
        :return: None
        """
        print "DEBUG: on_tree_selection_change(): ",
        model, treeiter = selection.get_selected()

        if treeiter is not None:
            # Save data for previous selection
            obj = self.get_current()
            if obj is not None:
                obj.read_form()

            print "DEBUG: You selected", model[treeiter][0]
            self.selected_item_name = model[treeiter][0]
            obj_new = self.get_current()
            if obj_new is not None:
                GLib.idle_add(lambda: obj_new.build_ui())
        else:
            print "DEBUG: Nothing selected"
            self.selected_item_name = None
            self.setup_component_editor()

    def on_file_new(self, param):
        """
        Callback for menu item File->New. Returns the application to its
        startup state.

        :param param: Whatever is passed by the event. Ignore.
        :return: None
        """
        # Remove everythong from memory
        # Clear plot
        self.clear_plots()

        # Clear object editor
        #self.setup_component_editor()

        # Clear data
        self.stuff = {}

        # Clear list
        #self.tree_select.unselect_all()
        self.build_list()

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
        dialog = Gtk.FileChooserDialog("Please choose a file", self.window,
                                       Gtk.FileChooserAction.OPEN,
                                       (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                                        Gtk.STOCK_OPEN, Gtk.ResponseType.OK))
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            filename = dialog.get_filename()
            dialog.destroy()
            t = threading.Thread(target=on_success, args=(self, filename))
            t.daemon = True
            t.start()
            #on_success(self, filename)
        elif response == Gtk.ResponseType.CANCEL:
            self.info("Open cancelled.")  # print("Cancel clicked")
            dialog.destroy()

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
        # IMPORTANT: on_success will run on a separate thread. Use
        # GLib.idle_add(function, **kwargs) to launch actions that will
        # updata the GUI.
        def on_success(app_obj, filename):
            assert isinstance(app_obj, App)
            GLib.idle_add(lambda: app_obj.set_progress_bar(0.1, "Opening Gerber ..."))

            def obj_init(gerber_obj, app_obj):
                assert isinstance(gerber_obj, FlatCAMGerber)
                GLib.idle_add(lambda: app_obj.set_progress_bar(0.2, "Parsing ..."))
                gerber_obj.parse_file(filename)
                GLib.idle_add(lambda: app_obj.set_progress_bar(0.5, "Creating Geometry ..."))
                gerber_obj.create_geometry()
                GLib.idle_add(lambda: app_obj.set_progress_bar(0.6, "Plotting ..."))

            name = filename.split('/')[-1].split('\\')[-1]
            app_obj.new_object("gerber", name, obj_init)

            GLib.idle_add(lambda: app_obj.set_progress_bar(1.0, "Done!"))
            GLib.timeout_add_seconds(1, lambda: app_obj.set_progress_bar(0.0, ""))

        # on_success gets run on a separate thread
        self.file_chooser_action(on_success)

    def on_fileopenexcellon(self, param):
        """
        Callback for menu item File->Open Excellon. Defines a function that is then passed
        to ``self.file_chooser_action()``. It requests the creation of a FlatCAMExcellon object
        and updates the progress bar throughout the process.

        :param param: Ignore
        :return: None
        """
        # IMPORTANT: on_success will run on a separate thread. Use
        # GLib.idle_add(function, **kwargs) to launch actions that will
        # updata the GUI.
        def on_success(app_obj, filename):
            assert isinstance(app_obj, App)
            GLib.idle_add(lambda: app_obj.set_progress_bar(0.1, "Opening Excellon ..."))

            def obj_init(excellon_obj, app_obj):
                GLib.idle_add(lambda: app_obj.set_progress_bar(0.2, "Parsing ..."))
                excellon_obj.parse_file(filename)
                excellon_obj.create_geometry()
                GLib.idle_add(lambda: app_obj.set_progress_bar(0.6, "Plotting ..."))

            name = filename.split('/')[-1].split('\\')[-1]
            app_obj.new_object("excellon", name, obj_init)

            GLib.idle_add(lambda: app_obj.set_progress_bar(1.0, "Done!"))
            GLib.timeout_add_seconds(1, lambda: app_obj.set_progress_bar(0.0, ""))

        # on_success gets run on a separate thread
        self.file_chooser_action(on_success)

    def on_fileopengcode(self, param):
        """
        Callback for menu item File->Open G-Code. Defines a function that is then passed
        to ``self.file_chooser_action()``. It requests the creation of a FlatCAMCNCjob object
        and updates the progress bar throughout the process.

        :param param: Ignore
        :return: None
        """
        # IMPORTANT: on_success will run on a separate thread. Use
        # GLib.idle_add(function, **kwargs) to launch actions that will
        # updata the GUI.
        def on_success(app_obj, filename):
            assert isinstance(app_obj, App)

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

            name = filename.split('/')[-1].split('\\')[-1]
            app_obj.new_object("cncjob", name, obj_init)

            GLib.idle_add(lambda: app_obj.set_progress_bar(1.0, "Done!"))
            GLib.timeout_add_seconds(1, lambda: app_obj.set_progress_bar(0.0, ""))

        # on_success gets run on a separate thread
        self.file_chooser_action(on_success)

    def on_mouse_move_over_plot(self, event):
        """
        Callback for the mouse motion event over the plot. This event is generated
        by the Matplotlib backend and has been registered in ``self.__init__()``.
        For details, see: http://matplotlib.org/users/event_handling.html

        :param event: Contains information about the event.
        :return: None
        """

        try:  # May fail in case mouse not within axes
            self.position_label.set_label("X: %.4f   Y: %.4f" % (
                event.xdata, event.ydata))
            self.mouse = [event.xdata, event.ydata]

            for subscriber in self.plot_mousemove_subscribers:
                self.plot_mousemove_subscribers[subscriber](event)

        except:
            self.position_label.set_label("")
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

        # For key presses
        self.canvas.grab_focus()

        try:
            print 'button=%d, x=%d, y=%d, xdata=%f, ydata=%f' % (
                event.button, event.x, event.y, event.xdata, event.ydata)

            # TODO: This custom subscription mechanism is probably not necessary.
            for subscriber in self.plot_click_subscribers:
                self.plot_click_subscribers[subscriber](event)

            self.clipboard.set_text("(%.4f, %.4f)" % (event.xdata, event.ydata), -1)

        except Exception, e:
            print "Outside plot!"

    def on_zoom_in(self, event):
        """
        Callback for zoom-in request. This can be either from the corresponding
        toolbar button or the '3' key when the canvas is focused. Calls ``self.zoom()``.

        :param event: Ignored.
        :return: None
        """
        self.zoom(1.5)
        return

    def on_zoom_out(self, event):
        """
        Callback for zoom-out request. This can be either from the corresponding
        toolbar button or the '2' key when the canvas is focused. Calls ``self.zoom()``.

        :param event: Ignored.
        :return: None
        """
        self.zoom(1 / 1.5)

    def on_zoom_fit(self, event):
        """
        Callback for zoom-out request. This can be either from the corresponding
        toolbar button or the '1' key when the canvas is focused. Calls ``self.adjust_axes()``
        with axes limits from the geometry bounds of all objects.

        :param event: Ignored.
        :return: None
        """
        xmin, ymin, xmax, ymax = get_bounds(self.stuff)
        width = xmax - xmin
        height = ymax - ymin
        xmin -= 0.05 * width
        xmax += 0.05 * width
        ymin -= 0.05 * height
        ymax += 0.05 * height
        self.adjust_axes(xmin, ymin, xmax, ymax)

    # def on_scroll_over_plot(self, event):
    #     print "Scroll"
    #     center = [event.xdata, event.ydata]
    #     if sign(event.step):
    #         self.zoom(1.5, center=center)
    #     else:
    #         self.zoom(1/1.5, center=center)
    #
    # def on_window_scroll(self, event):
    #     print "Scroll"

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
        ==========  ============================================

        :param event: Ignored.
        :return: None
        """
        #print 'you pressed', event.key, event.xdata, event.ydata

        if event.key == '1':  # 1
            self.on_zoom_fit(None)
            return

        if event.key == '2':  # 2
            self.zoom(1 / 1.5, self.mouse)
            return

        if event.key == '3':  # 3
            self.zoom(1.5, self.mouse)
            return

        if event.key == 'm':
            if self.measure.toggle_active():
                self.info("Measuring tool ON")
            else:
                self.info("Measuring tool OFF")
            return


class Measurement:
    def __init__(self, axes, click_subscibers, move_subscribers, update=None):
        self.update = update
        self.axes = axes
        self.click_subscribers = click_subscibers
        self.move_subscribers = move_subscribers
        self.point1 = None
        self.point2 = None
        self.active = False
        self.at = None  # AnchoredText object on plot

    def toggle_active(self):
        if self.active:
            self.active = False
            self.move_subscribers.pop("meas")
            self.click_subscribers.pop("meas")
            self.at.remove()
            if self.update is not None:
                self.update()
            return False
        else:
            self.active = True
            self.click_subscribers["meas"] = self.on_click
            self.move_subscribers["meas"] = self.on_move
            return True

    def on_move(self, event):
        try:
            self.at.remove()
        except:
            pass
        if self.point1 is None:
            self.at = AnchoredText("Click on a reference point...")
        else:
            dx = event.xdata - self.point1[0]
            dy = event.ydata - self.point1[1]
            d = sqrt(dx**2 + dy**2)
            self.at = AnchoredText("D = %.4f\nD(x) = %.4f\nD(y) = %.4f" % (d, dx, dy),
                                   loc=2, prop={'size': 14}, frameon=False)
        self.axes.add_artist(self.at)
        if self.update is not None:
            self.update()

    def on_click(self, event):
            if self.point1 is None:
                self.point1 = (event.xdata, event.ydata)
                return
            else:
                self.point2 = copy.copy(self.point1)
                self.point1 = (event.xdata, event.ydata)


class PlotCanvas:
    """
    Class handling the plotting area in the application.
    """

    def __init__(self, container):
        # Options
        self.x_margin = 15  # pixels
        self.y_margin = 25  # Pixels

        # Parent container
        self.container = container

        # Plots go onto a single matplotlib.figure
        self.figure = Figure(dpi=50)  # TODO: dpi needed?
        self.figure.patch.set_visible(False)

        # These axes show the ticks and grid. No plotting done here.
        # New axes must have a label, otherwise mpl returns an existing one.
        self.axes = self.figure.add_axes([0.05, 0.05, 0.9, 0.9], label="base", alpha=0.0)
        self.axes.set_aspect(1)
        self.axes.grid(True)

        # The canvas is the top level container (Gtk.DrawingArea)
        self.canvas = FigureCanvas(self.figure)
        self.canvas.set_hexpand(1)
        self.canvas.set_vexpand(1)
        self.canvas.set_can_focus(True)  # For key press

        # Attach to parent
        self.container.attach(self.canvas, 0, 0, 600, 400)

    def mpl_connect(self, event_name, callback):
        """
        Attach an event handler to the canvas through the Matplotlib interface.

        :param event_name: Name of the event
        :type event_name: str
        :param callback: Function to call
        :type callback: func
        :return: Nothing
        """
        self.canvas.mpl_connect(event_name, callback)

    def connect(self, event_name, callback):
        """
        Attach an event handler to the canvas through the native GTK interface.

        :param event_name: Name of the event
        :type event_name: str
        :param callback: Function to call
        :type callback: function
        :return: Nothing
        """
        self.canvas.connect(event_name, callback)

    def clear(self):
        """
        Clears axes and figure.

        :return: None
        """

        # Clear
        self.axes.cla()
        self.figure.clf()

        # Re-build
        self.figure.add_axes(self.axes)
        self.axes.set_aspect(1)
        self.axes.grid(True)

        # Re-draw
        self.canvas.queue_draw()

    def adjust_axes(self, xmin, ymin, xmax, ymax):
        """
        Adjusts axes of all plots while maintaining the use of the whole canvas
        and an aspect ratio to 1:1 between x and y axes. The parameters are an original
        request that will be modified to fit these restrictions.

        :param xmin: Requested minimum value for the X axis.
        :type xmin: float
        :param ymin: Requested minimum value for the Y axis.
        :type ymin: float
        :param xmax: Requested maximum value for the X axis.
        :type xmax: float
        :param ymax: Requested maximum value for the Y axis.
        :type ymax: float
        :return: None
        """

        width = xmax - xmin
        height = ymax - ymin
        try:
            r = width / height
        except:
            print "ERROR: Height is", height
            return
        canvas_w, canvas_h = self.canvas.get_width_height()
        canvas_r = float(canvas_w) / canvas_h
        x_ratio = float(self.x_margin) / canvas_w
        y_ratio = float(self.y_margin) / canvas_h

        if r > canvas_r:
            ycenter = (ymin + ymax) / 2.0
            newheight = height * r / canvas_r
            ymin = ycenter - newheight / 2.0
            ymax = ycenter + newheight / 2.0
        else:
            xcenter = (xmax + ymin) / 2.0
            newwidth = width * canvas_r / r
            xmin = xcenter - newwidth / 2.0
            xmax = xcenter + newwidth / 2.0

        # Adjust axes
        for ax in self.figure.get_axes():
            ax.set_xlim((xmin, xmax))
            ax.set_ylim((ymin, ymax))
            ax.set_position([x_ratio, y_ratio, 1 - 2 * x_ratio, 1 - 2 * y_ratio])

        # Re-draw
        self.canvas.queue_draw()

    def auto_adjust_axes(self):
        """
        Calls ``adjust_axes()`` using the extents of the base axes.

        :return: None
        """

        xmin, xmax = self.axes.get_xlim()
        ymin, ymax = self.axes.get_ylim()
        self.adjust_axes(xmin, ymin, xmax, ymax)

    def zoom(self, factor, center=None):
        """
        Zooms the plot by factor around a given
        center point. Takes care of re-drawing.

        :param factor: Number by which to scale the plot.
        :type factor: float
        :param center: Coordinates [x, y] of the point around which to scale the plot.
        :type center: list
        :return: None
        """

        xmin, xmax = self.axes.get_xlim()
        ymin, ymax = self.axes.get_ylim()
        width = xmax - xmin
        height = ymax - ymin

        if center is None:
            center = [(xmin + xmax) / 2.0, (ymin + ymax) / 2.0]

        # For keeping the point at the pointer location
        relx = (xmax - center[0]) / width
        rely = (ymax - center[1]) / height

        new_width = width / factor
        new_height = height / factor

        xmin = center[0] - new_width * (1 - relx)
        xmax = center[0] + new_width * relx
        ymin = center[1] - new_height * (1 - rely)
        ymax = center[1] + new_height * rely

        # Adjust axes
        for ax in self.figure.get_axes():
            ax.set_xlim((xmin, xmax))
            ax.set_ylim((ymin, ymax))

        # Re-draw
        self.canvas.queue_draw()

app = App()
Gtk.main()
