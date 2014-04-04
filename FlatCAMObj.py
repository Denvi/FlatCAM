############################################################
# FlatCAM: 2D Post-processing for Manufacturing            #
# http://caram.cl/software/flatcam                         #
# Author: Juan Pablo Caram (c)                             #
# Date: 2/5/2014                                           #
# MIT Licence                                              #
############################################################

from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GLib
from gi.repository import GObject

from camlib import *


########################################
##            FlatCAMObj              ##
########################################
class FlatCAMObj(GObject.GObject, object):
    """
    Base type of objects handled in FlatCAM. These become interactive
    in the GUI, can be plotted, and their options can be modified
    by the user in their respective forms.
    """

    # Instance of the application to which these are related.
    # The app should set this value.
    app = None

    def __init__(self, name):
        GObject.GObject.__init__(self)

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

        # entry_name = self.app.builder.get_object("entry_text_" + self.kind + "_name")
        # entry_name.connect("activate", self.app.on_activate_name)
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

    def plot(self):
        """
        Plot this object (Extend this method to implement the actual plotting).
        Axes get created, appended to canvas and cleared before plotting.
        Call this in descendants before doing the plotting.

        :return: Whether to continue plotting or not depending on the "plot" option.
        :rtype: bool
        """

        # Axes must exist and be attached to canvas.
        if self.axes is None or self.axes not in self.app.plotcanvas.figure.axes:
            self.axes = self.app.plotcanvas.new_axes(self.options['name'])

        if not self.options["plot"]:
            self.axes.cla()
            self.app.plotcanvas.auto_adjust_axes()
            return False

        # Clear axes or we will plot on top of them.
        self.axes.cla()
        # GLib.idle_add(self.axes.cla)
        return True

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
        :return: None
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
            "isotooldia": 0.016,
            "isopasses": 1,
            "isooverlap": 0.15,
            "cutouttooldia": 0.07,
            "cutoutmargin": 0.2,
            "cutoutgapsize": 0.15,
            "gaps": "tb",
            "noncoppermargin": 0.0,
            "noncopperrounded": False,
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
            "isopasses": "entry_eval",
            "isooverlap": "entry_eval",
            "cutouttooldia": "entry_eval",
            "cutoutmargin": "entry_eval",
            "cutoutgapsize": "entry_eval",
            "gaps": "radio",
            "noncoppermargin": "entry_eval",
            "noncopperrounded": "cb",
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

    def plot(self):

        # Does all the required setup and returns False
        # if the 'ptint' option is set to False.
        if not FlatCAMObj.plot(self):
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

        # self.app.plotcanvas.auto_adjust_axes()
        GLib.idle_add(self.app.plotcanvas.auto_adjust_axes)

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
            "drillz": -0.1,
            "travelz": 0.1,
            "feedrate": 5.0,
            "toolselection": ""
        })

        self.form_kinds.update({
            "plot": "cb",
            "solid": "cb",
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

    def plot(self):

        # Does all the required setup and returns False
        # if the 'ptint' option is set to False.
        if not FlatCAMObj.plot(self):
            return

        try:
            _ = iter(self.solid_geometry)
        except TypeError:
            self.solid_geometry = [self.solid_geometry]

        # Plot excellon (All polygons?)
        if self.options["solid"]:
            for geo in self.solid_geometry:
                patch = PolygonPatch(geo,
                                     facecolor="#C40000",
                                     edgecolor="#750000",
                                     alpha=0.75,
                                     zorder=3)
                self.axes.add_patch(patch)
        else:
            for geo in self.solid_geometry:
                x, y = geo.exterior.coords.xy
                self.axes.plot(x, y, 'r-')
                for ints in geo.interiors:
                    x, y = ints.coords.xy
                    self.axes.plot(x, y, 'g-')

        #self.app.plotcanvas.auto_adjust_axes()
        GLib.idle_add(self.app.plotcanvas.auto_adjust_axes)

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
            for toolx in self.tool_cbs:
                if self.tool_cbs[toolx].get_active():
                    tool_list.append(toolx)
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

    def plot(self):

        # Does all the required setup and returns False
        # if the 'ptint' option is set to False.
        if not FlatCAMObj.plot(self):
            return

        self.plot2(self.axes, tooldia=self.options["tooldia"])

        #self.app.plotcanvas.auto_adjust_axes()
        GLib.idle_add(self.app.plotcanvas.auto_adjust_axes)

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

    def plot(self):
        """
        Plots the object into its axes. If None, of if the axes
        are not part of the app's figure, it fetches new ones.

        :return: None
        """

        # Does all the required setup and returns False
        # if the 'ptint' option is set to False.
        if not FlatCAMObj.plot(self):
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

        #self.app.plotcanvas.auto_adjust_axes()
        GLib.idle_add(self.app.plotcanvas.auto_adjust_axes)