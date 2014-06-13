############################################################
# FlatCAM: 2D Post-processing for Manufacturing            #
# http://caram.cl/software/flatcam                         #
# Author: Juan Pablo Caram (c)                             #
# Date: 2/5/2014                                           #
# MIT Licence                                              #
############################################################

import inspect  # TODO: Remove

from gi.repository import Gtk
from gi.repository import GLib
from gi.repository import GObject

from camlib import *
from ObjectUI import *


class LoudDict(dict):
    """
    A Dictionary with a callback for
    item changes.
    """

    def __init__(self, *args, **kwargs):
        super(LoudDict, self).__init__(*args, **kwargs)
        self.callback = lambda x: None
        self.silence = False

    def set_change_callback(self, callback):
        """
        Assigns a function as callback on item change. The callback
        will receive the key of the object that was changed.

        :param callback: Function to call on item change.
        :type callback: func
        :return: None
        """

        self.callback = callback

    def __setitem__(self, key, value):
        """
        Overridden __setitem__ method. Will call self.callback
        if the item was changed and self.silence is False.
        """
        super(LoudDict, self).__setitem__(key, value)
        try:
            if self.__getitem__(key) == value:
                return
        except KeyError:
            pass
        if self.silence:
            return
        self.callback(key)


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

    def __init__(self, name, ui):
        """

        :param name: Name of the object given by the user.
        :param ui: User interface to interact with the object.
        :type ui: ObjectUI
        :return: FlatCAMObj
        """
        GObject.GObject.__init__(self)

        # View
        self.ui = ui

        self.options = LoudDict(name=name)
        self.options.set_change_callback(self.on_options_change)

        self.form_fields = {"name": self.ui.name_entry}
        self.radios = {}  # Name value pairs for radio sets
        self.radios_inv = {}  # Inverse of self.radios
        self.axes = None  # Matplotlib axes
        self.kind = None  # Override with proper name

        self.muted_ui = False

        self.ui.name_entry.connect('activate', self.on_name_activate)
        self.ui.offset_button.connect('clicked', self.on_offset_button_click)
        self.ui.offset_button.connect('activate', self.on_offset_button_click)
        self.ui.scale_button.connect('clicked', self.on_scale_button_click)
        self.ui.scale_button.connect('activate', self.on_scale_button_click)

    def __str__(self):
        return "<FlatCAMObj({:12s}): {:20s}>".format(self.kind, self.options["name"])

    def on_name_activate(self, *args):
        old_name = copy(self.options["name"])
        new_name = self.ui.name_entry.get_text()
        self.options["name"] = self.ui.name_entry.get_text()
        self.app.info("Name changed from %s to %s" % (old_name, new_name))

    def on_offset_button_click(self, *args):
        self.read_form()
        vect = self.ui.offsetvector_entry.get_value()
        self.offset(vect)
        self.plot()

    def on_scale_button_click(self, *args):
        self.read_form()
        factor = self.ui.scale_entry.get_value()
        self.scale(factor)
        self.plot()

    def on_options_change(self, key):
        self.form_fields[key].set_value(self.options[key])
        return

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
            FlatCAMApp.App.log.debug("setup_axes(): New axes")
            self.axes = figure.add_axes([0.05, 0.05, 0.9, 0.9],
                                        label=self.options["name"])
        elif self.axes not in figure.axes:
            FlatCAMApp.App.log.debug("setup_axes(): Clearing and attaching axes")
            self.axes.cla()
            figure.add_axes(self.axes)
        else:
            FlatCAMApp.App.log.debug("setup_axes(): Clearing Axes")
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
        FlatCAMApp.App.log.debug(str(inspect.stack()[1][3]) + "--> FlatCAMObj.read_form()")
        for option in self.options:
            self.read_form_item(option)

    def build_ui(self):
        """
        Sets up the UI/form for this object.

        :return: None
        :rtype: None
        """

        self.muted_ui = True
        FlatCAMApp.App.log.debug(str(inspect.stack()[1][3]) + "--> FlatCAMObj.build_ui()")

        # Where the UI for this object is drawn
        # box_selected = self.app.builder.get_object("box_selected")
        # box_selected = self.app.builder.get_object("vp_selected")

        # Remove anything else in the box
        box_children = self.app.ui.notebook.selected_contents.get_children()
        for child in box_children:
            self.app.ui.notebook.selected_contents.remove(child)

        # Put in the UI
        # box_selected.pack_start(sw, True, True, 0)
        self.app.ui.notebook.selected_contents.add(self.ui)
        self.to_form()
        GLib.idle_add(self.app.ui.notebook.selected_contents.show_all)
        GLib.idle_add(self.ui.show_all)
        self.muted_ui = False

    def set_form_item(self, option):
        """
        Copies the specified option to the UI form.

        :param option: Name of the option (Key in ``self.options``).
        :type option: str
        :return: None
        """

        try:
            self.form_fields[option].set_value(self.options[option])
        except KeyError:
            self.app.log.warn("Tried to set an option or field that does not exist: %s" % option)

    def read_form_item(self, option):
        """
        Reads the specified option from the UI form into ``self.options``.

        :param option: Name of the option.
        :type option: str
        :return: None
        """

        try:
            self.options[option] = self.form_fields[option].get_value()
        except KeyError:
            self.app.log.warning("Failed to read option from field: %s" % option)

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
        self.axes.cla()  # TODO: Thread safe?
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
        FlatCAMObj.__init__(self, name, GerberObjectUI())

        self.kind = "gerber"

        self.form_fields.update({
            "plot": self.ui.plot_cb,
            "multicolored": self.ui.multicolored_cb,
            "solid": self.ui.solid_cb,
            "isotooldia": self.ui.iso_tool_dia_entry,
            "isopasses": self.ui.iso_width_entry,
            "isooverlap": self.ui.iso_overlap_entry,
            "cutouttooldia": self.ui.cutout_tooldia_entry,
            "cutoutmargin": self.ui.cutout_margin_entry,
            "cutoutgapsize": self.ui.cutout_gap_entry,
            "gaps": self.ui.gaps_radio,
            "noncoppermargin": self.ui.noncopper_margin_entry,
            "noncopperrounded": self.ui.noncopper_rounded_cb,
            "bboxmargin": self.ui.bbmargin_entry,
            "bboxrounded": self.ui.bbrounded_cb
        })

        # The 'name' is already in self.options from FlatCAMObj
        # Automatically updates the UI
        self.options.update({
            "plot": True,
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

        # Attributes to be included in serialization
        # Always append to it because it carries contents
        # from predecessors.
        self.ser_attrs += ['options', 'kind']

        assert isinstance(self.ui, GerberObjectUI)
        self.ui.plot_cb.connect('clicked', self.on_plot_cb_click)
        self.ui.plot_cb.connect('activate', self.on_plot_cb_click)
        self.ui.solid_cb.connect('clicked', self.on_solid_cb_click)
        self.ui.solid_cb.connect('activate', self.on_solid_cb_click)
        self.ui.multicolored_cb.connect('clicked', self.on_multicolored_cb_click)
        self.ui.multicolored_cb.connect('activate', self.on_multicolored_cb_click)
        self.ui.generate_iso_button.connect('clicked', self.on_iso_button_click)
        self.ui.generate_iso_button.connect('activate', self.on_iso_button_click)
        self.ui.generate_cutout_button.connect('clicked', self.on_generatecutout_button_click)
        self.ui.generate_cutout_button.connect('activate', self.on_generatecutout_button_click)
        self.ui.generate_bb_button.connect('clicked', self.on_generatebb_button_click)
        self.ui.generate_bb_button.connect('activate', self.on_generatebb_button_click)
        self.ui.generate_noncopper_button.connect('clicked', self.on_generatenoncopper_button_click)
        self.ui.generate_noncopper_button.connect('activate', self.on_generatenoncopper_button_click)

    def on_generatenoncopper_button_click(self, *args):
        self.read_form()
        name = self.options["name"] + "_noncopper"

        def geo_init(geo_obj, app_obj):
            assert isinstance(geo_obj, FlatCAMGeometry)
            bounding_box = self.solid_geometry.envelope.buffer(self.options["noncoppermargin"])
            if not self.options["noncopperrounded"]:
                bounding_box = bounding_box.envelope
            non_copper = bounding_box.difference(self.solid_geometry)
            geo_obj.solid_geometry = non_copper

        # TODO: Check for None
        self.app.new_object("geometry", name, geo_init)

    def on_generatebb_button_click(self, *args):
        self.read_form()
        name = self.options["name"] + "_bbox"

        def geo_init(geo_obj, app_obj):
            assert isinstance(geo_obj, FlatCAMGeometry)
            # Bounding box with rounded corners
            bounding_box = self.solid_geometry.envelope.buffer(self.options["bboxmargin"])
            if not self.options["bboxrounded"]:  # Remove rounded corners
                bounding_box = bounding_box.envelope
            geo_obj.solid_geometry = bounding_box

        self.app.new_object("geometry", name, geo_init)

    def on_generatecutout_button_click(self, *args):
        self.read_form()
        name = self.options["name"] + "_cutout"

        def geo_init(geo_obj, app_obj):
            margin = self.options["cutoutmargin"] + self.options["cutouttooldia"]/2
            gap_size = self.options["cutoutgapsize"] + self.options["cutouttooldia"]
            minx, miny, maxx, maxy = self.bounds()
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
            cuts = cases[self.options['gaps']]
            geo_obj.solid_geometry = cascaded_union([LineString(segment) for segment in cuts])

        # TODO: Check for None
        self.app.new_object("geometry", name, geo_init)

    def on_iso_button_click(self, *args):
        self.read_form()
        dia = self.options["isotooldia"]
        passes = int(self.options["isopasses"])
        overlap = self.options["isooverlap"] * dia

        for i in range(passes):

            offset = (2*i + 1)/2.0 * dia - i*overlap
            iso_name = self.options["name"] + "_iso%d" % (i+1)

            # TODO: This is ugly. Create way to pass data into init function.
            def iso_init(geo_obj, app_obj):
                # Propagate options
                geo_obj.options["cnctooldia"] = self.options["isotooldia"]

                geo_obj.solid_geometry = self.isolation_geometry(offset)
                app_obj.info("Isolation geometry created: %s" % geo_obj.options["name"])

            # TODO: Do something if this is None. Offer changing name?
            self.app.new_object("geometry", iso_name, iso_init)

    def on_plot_cb_click(self, *args):
        if self.muted_ui:
            return
        self.read_form_item('plot')
        self.plot()

    def on_solid_cb_click(self, *args):
        if self.muted_ui:
            return
        self.read_form_item('solid')
        self.plot()

    def on_multicolored_cb_click(self, *args):
        if self.muted_ui:
            return
        self.read_form_item('multicolored')
        self.plot()

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

        # if self.options["mergepolys"]:
        #     geometry = self.solid_geometry
        # else:
        #     geometry = self.buffered_paths + \
        #                 [poly['polygon'] for poly in self.regions] + \
        #                 self.flash_geometry
        geometry = self.solid_geometry

        # Make sure geometry is iterable.
        try:
            _ = iter(geometry)
        except TypeError:
            geometry = [geometry]

        if self.options["multicolored"]:
            linespec = '-'
        else:
            linespec = 'k-'

        if self.options["solid"]:
            for poly in geometry:
                # TODO: Too many things hardcoded.
                try:
                    patch = PolygonPatch(poly,
                                         facecolor="#BBF268",
                                         edgecolor="#006E20",
                                         alpha=0.75,
                                         zorder=2)
                    self.axes.add_patch(patch)
                except AssertionError:
                    FlatCAMApp.App.log.warning("A geometry component was not a polygon:")
                    FlatCAMApp.App.log.warning(str(poly))
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
        FlatCAMObj.__init__(self, name, ExcellonObjectUI())

        self.kind = "excellon"

        self.form_fields.update({
            "plot": self.ui.plot_cb,
            "solid": self.ui.solid_cb,
            "drillz": self.ui.cutz_entry,
            "travelz": self.ui.travelz_entry,
            "feedrate": self.ui.feedrate_entry,
            "toolselection": self.ui.tools_entry
        })

        self.options.update({
            "plot": True,
            "solid": False,
            "drillz": -0.1,
            "travelz": 0.1,
            "feedrate": 5.0,
            "toolselection": ""
        })

        # TODO: Document this.
        self.tool_cbs = {}

        # Attributes to be included in serialization
        # Always append to it because it carries contents
        # from predecessors.
        self.ser_attrs += ['options', 'kind']

        assert isinstance(self.ui, ExcellonObjectUI)
        self.ui.plot_cb.connect('clicked', self.on_plot_cb_click)
        self.ui.plot_cb.connect('activate', self.on_plot_cb_click)
        self.ui.solid_cb.connect('clicked', self.on_solid_cb_click)
        self.ui.solid_cb.connect('activate', self.on_solid_cb_click)
        self.ui.choose_tools_button.connect('clicked', lambda args: self.show_tool_chooser())
        self.ui.choose_tools_button.connect('activate', lambda args: self.show_tool_chooser())
        self.ui.generate_cnc_button.connect('clicked', self.on_create_cncjob_button_click)
        self.ui.generate_cnc_button.connect('activate', self.on_create_cncjob_button_click)

    def on_create_cncjob_button_click(self, *args):
        self.read_form()
        job_name = self.options["name"] + "_cnc"

        # Object initialization function for app.new_object()
        def job_init(job_obj, app_obj):
            assert isinstance(job_obj, FlatCAMCNCjob)

            GLib.idle_add(lambda: app_obj.set_progress_bar(0.2, "Creating CNC Job..."))
            job_obj.z_cut = self.options["drillz"]
            job_obj.z_move = self.options["travelz"]
            job_obj.feedrate = self.options["feedrate"]
            # There could be more than one drill size...
            # job_obj.tooldia =   # TODO: duplicate variable!
            # job_obj.options["tooldia"] =
            job_obj.generate_from_excellon_by_tool(self, self.options["toolselection"])

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

        # Send to worker
        self.app.worker.add_task(job_thread, [self.app])

    def on_plot_cb_click(self, *args):
        if self.muted_ui:
            return
        self.read_form_item('plot')
        self.plot()

    def on_solid_cb_click(self, *args):
        if self.muted_ui:
            return
        self.read_form_item('solid')
        self.plot()

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

import time

class FlatCAMCNCjob(FlatCAMObj, CNCjob):
    """
    Represents G-Code.
    """

    def __init__(self, name, units="in", kind="generic", z_move=0.1,
                 feedrate=3.0, z_cut=-0.002, tooldia=0.0):
        FlatCAMApp.App.log.debug("Creating CNCJob object...")
        CNCjob.__init__(self, units=units, kind=kind, z_move=z_move,
                        feedrate=feedrate, z_cut=z_cut, tooldia=tooldia)
        ui = CNCObjectUI()
        FlatCAMApp.App.log.debug("... UI Created")
        time.sleep(2)
        FlatCAMApp.App.log.debug("... 2 seconds later")
        FlatCAMObj.__init__(self, name, ui)
        FlatCAMApp.App.log.debug("... UI Passed to parent")
        self.kind = "cncjob"

        self.options.update({
            "plot": True,
            "tooldia": 0.4 / 25.4,  # 0.4mm in inches
            #"append": ""
        })

        self.form_fields.update({
            "plot": self.ui.plot_cb,
            "tooldia": self.ui.tooldia_entry,
            #"append": self.ui.append_gtext
        })
        FlatCAMApp.App.log.debug("... Options")

        # Attributes to be included in serialization
        # Always append to it because it carries contents
        # from predecessors.
        self.ser_attrs += ['options', 'kind']

        self.ui.plot_cb.connect('clicked', self.on_plot_cb_click)
        self.ui.plot_cb.connect('activate', self.on_plot_cb_click)
        self.ui.updateplot_button.connect('clicked', self.on_updateplot_button_click)
        self.ui.updateplot_button.connect('activate', self.on_updateplot_button_click)
        self.ui.export_gcode_button.connect('clicked', self.on_exportgcode_button_click)
        self.ui.export_gcode_button.connect('activate', self.on_exportgcode_button_click)
        FlatCAMApp.App.log.debug("... Callbacks. DONE")

    def on_updateplot_button_click(self, *args):
        """
        Callback for the "Updata Plot" button. Reads the form for updates
        and plots the object.
        """
        self.read_form()
        self.plot()

    def on_exportgcode_button_click(self, *args):
        def on_success(app_obj, filename):
            f = open(filename, 'w')
            f.write(self.gcode)
            f.close()
            app_obj.info("Saved to: " + filename)

        self.app.file_chooser_save_action(on_success)

    def on_plot_cb_click(self, *args):
        if self.muted_ui:
            return
        self.read_form_item('plot')
        self.plot()

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
        FlatCAMApp.App.log.debug("FlatCAMCNCjob.convert_units()")
        self.options["tooldia"] *= factor


class FlatCAMGeometry(FlatCAMObj, Geometry):
    """
    Geometric object not associated with a specific
    format.
    """

    def __init__(self, name):
        FlatCAMObj.__init__(self, name, GeometryObjectUI())
        Geometry.__init__(self)

        self.kind = "geometry"

        self.form_fields.update({
            "plot": self.ui.plot_cb,
            # "solid": self.ui.sol,
            # "multicolored": self.ui.,
            "cutz": self.ui.cutz_entry,
            "travelz": self.ui.travelz_entry,
            "feedrate": self.ui.cncfeedrate_entry,
            "cnctooldia": self.ui.cnctooldia_entry,
            "painttooldia": self.ui.painttooldia_entry,
            "paintoverlap": self.ui.paintoverlap_entry,
            "paintmargin": self.ui.paintmargin_entry
        })

        self.options.update({
            "plot": True,
            # "solid": False,
            # "multicolored": False,
            "cutz": -0.002,
            "travelz": 0.1,
            "feedrate": 5.0,
            "cnctooldia": 0.4 / 25.4,
            "painttooldia": 0.0625,
            "paintoverlap": 0.15,
            "paintmargin": 0.01
        })

        # self.form_kinds.update({
        #     "plot": "cb",
        #     "solid": "cb",
        #     "multicolored": "cb",
        #     "cutz": "entry_eval",
        #     "travelz": "entry_eval",
        #     "feedrate": "entry_eval",
        #     "cnctooldia": "entry_eval",
        #     "painttooldia": "entry_eval",
        #     "paintoverlap": "entry_eval",
        #     "paintmargin": "entry_eval"
        # })

        # Attributes to be included in serialization
        # Always append to it because it carries contents
        # from predecessors.
        self.ser_attrs += ['options', 'kind']

        assert isinstance(self.ui, GeometryObjectUI)
        self.ui.plot_cb.connect('clicked', self.on_plot_cb_click)
        self.ui.plot_cb.connect('activate', self.on_plot_cb_click)
        self.ui.generate_cnc_button.connect('clicked', self.on_generatecnc_button_click)
        self.ui.generate_cnc_button.connect('activate', self.on_generatecnc_button_click)
        self.ui.generate_paint_button.connect('clicked', self.on_paint_button_click)
        self.ui.generate_paint_button.connect('activate', self.on_paint_button_click)

    def on_paint_button_click(self, *args):
        self.app.info("Click inside the desired polygon.")
        self.read_form()
        tooldia = self.options["painttooldia"]
        overlap = self.options["paintoverlap"]

        # Connection ID for the click event
        subscription = None

        # To be called after clicking on the plot.
        def doit(event):
            self.app.plotcanvas.mpl_disconnect(subscription)
            point = [event.xdata, event.ydata]
            poly = find_polygon(self.solid_geometry, point)

            # Initializes the new geometry object
            def gen_paintarea(geo_obj, app_obj):
                assert isinstance(geo_obj, FlatCAMGeometry)
                #assert isinstance(app_obj, App)
                cp = clear_poly(poly.buffer(-self.options["paintmargin"]), tooldia, overlap)
                geo_obj.solid_geometry = cp
                geo_obj.options["cnctooldia"] = tooldia

            name = self.options["name"] + "_paint"
            self.app.new_object("geometry", name, gen_paintarea)

        subscription = self.app.plotcanvas.mpl_connect('button_press_event', doit)

    def on_generatecnc_button_click(self, *args):
        self.read_form()
        job_name = self.options["name"] + "_cnc"

        # Object initialization function for app.new_object()
        # RUNNING ON SEPARATE THREAD!
        def job_init(job_obj, app_obj):
            assert isinstance(job_obj, FlatCAMCNCjob)
            # Propagate options
            job_obj.options["tooldia"] = self.options["cnctooldia"]

            GLib.idle_add(lambda: app_obj.set_progress_bar(0.2, "Creating CNC Job..."))
            job_obj.z_cut = self.options["cutz"]
            job_obj.z_move = self.options["travelz"]
            job_obj.feedrate = self.options["feedrate"]

            GLib.idle_add(lambda: app_obj.set_progress_bar(0.4, "Analyzing Geometry..."))
            # TODO: The tolerance should not be hard coded. Just for testing.
            job_obj.generate_from_geometry(self, tolerance=0.0005)

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
            GLib.timeout_add_seconds(1, lambda: app_obj.set_progress_bar(0.0, "Idle"))

        # Send to worker
        self.app.worker.add_task(job_thread, [self.app])

    def on_plot_cb_click(self, *args):
        if self.muted_ui:
            return
        self.read_form_item('plot')
        self.plot()

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

            FlatCAMApp.App.log.warning("Did not plot:", str(type(geo)))

        #self.app.plotcanvas.auto_adjust_axes()
        GLib.idle_add(self.app.plotcanvas.auto_adjust_axes)