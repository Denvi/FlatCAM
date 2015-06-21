from PyQt4 import QtCore
from ObjectUI import *
import FlatCAMApp
import inspect  # TODO: For debugging only.
from camlib import *
from FlatCAMCommon import LoudDict
from FlatCAMDraw import FlatCAMDraw


########################################
##            FlatCAMObj              ##
########################################
class FlatCAMObj(QtCore.QObject):
    """
    Base type of objects handled in FlatCAM. These become interactive
    in the GUI, can be plotted, and their options can be modified
    by the user in their respective forms.
    """

    # Instance of the application to which these are related.
    # The app should set this value.
    app = None

    def __init__(self, name):
        """

        :param name: Name of the object given by the user.
        :return: FlatCAMObj
        """
        QtCore.QObject.__init__(self)

        # View
        self.ui = None

        self.options = LoudDict(name=name)
        self.options.set_change_callback(self.on_options_change)

        self.form_fields = {}

        self.axes = None  # Matplotlib axes
        self.kind = None  # Override with proper name

        self.muted_ui = False

        # assert isinstance(self.ui, ObjectUI)
        # self.ui.name_entry.returnPressed.connect(self.on_name_activate)
        # self.ui.offset_button.clicked.connect(self.on_offset_button_click)
        # self.ui.scale_button.clicked.connect(self.on_scale_button_click)

    def on_options_change(self, key):
        self.emit(QtCore.SIGNAL("optionChanged"), key)

    def set_ui(self, ui):
        self.ui = ui

        self.form_fields = {"name": self.ui.name_entry}

        assert isinstance(self.ui, ObjectUI)
        self.ui.name_entry.returnPressed.connect(self.on_name_activate)
        self.ui.offset_button.clicked.connect(self.on_offset_button_click)
        self.ui.scale_button.clicked.connect(self.on_scale_button_click)

    def __str__(self):
        return "<FlatCAMObj({:12s}): {:20s}>".format(self.kind, self.options["name"])

    def on_name_activate(self):
        old_name = copy(self.options["name"])
        new_name = self.ui.name_entry.get_value()
        self.options["name"] = self.ui.name_entry.get_value()
        self.app.info("Name changed from %s to %s" % (old_name, new_name))

    def on_offset_button_click(self):
        self.app.report_usage("obj_on_offset_button")

        self.read_form()
        vect = self.ui.offsetvector_entry.get_value()
        self.offset(vect)
        self.plot()

    def on_scale_button_click(self):
        self.app.report_usage("obj_on_scale_button")
        self.read_form()
        factor = self.ui.scale_entry.get_value()
        self.scale(factor)
        self.plot()

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

        # Remove anything else in the box
        # box_children = self.app.ui.notebook.selected_contents.get_children()
        # for child in box_children:
        #     self.app.ui.notebook.selected_contents.remove(child)
        # while self.app.ui.selected_layout.count():
        #     self.app.ui.selected_layout.takeAt(0)

        # Put in the UI
        # box_selected.pack_start(sw, True, True, 0)
        # self.app.ui.notebook.selected_contents.add(self.ui)
        # self.app.ui.selected_layout.addWidget(self.ui)
        try:
            self.app.ui.selected_scroll_area.takeWidget()
        except:
            self.app.log.debug("Nothing to remove")
        self.app.ui.selected_scroll_area.setWidget(self.ui)
        self.to_form()

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
        FlatCAMApp.App.log.debug(str(inspect.stack()[1][3]) + " --> FlatCAMObj.plot()")

        # Axes must exist and be attached to canvas.
        if self.axes is None or self.axes not in self.app.plotcanvas.figure.axes:
            self.axes = self.app.plotcanvas.new_axes(self.options['name'])

        if not self.options["plot"]:
            self.axes.cla()
            self.app.plotcanvas.auto_adjust_axes()
            return False

        # Clear axes or we will plot on top of them.
        self.axes.cla()  # TODO: Thread safe?
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

    ui_type = GerberObjectUI

    def __init__(self, name):
        Gerber.__init__(self)
        FlatCAMObj.__init__(self, name)

        self.kind = "gerber"

        # The 'name' is already in self.options from FlatCAMObj
        # Automatically updates the UI
        self.options.update({
            "plot": True,
            "multicolored": False,
            "solid": False,
            "isotooldia": 0.016,
            "isopasses": 1,
            "isooverlap": 0.15,
            "combine_passes": True,
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

        # assert isinstance(self.ui, GerberObjectUI)
        # self.ui.plot_cb.stateChanged.connect(self.on_plot_cb_click)
        # self.ui.solid_cb.stateChanged.connect(self.on_solid_cb_click)
        # self.ui.multicolored_cb.stateChanged.connect(self.on_multicolored_cb_click)
        # self.ui.generate_iso_button.clicked.connect(self.on_iso_button_click)
        # self.ui.generate_cutout_button.clicked.connect(self.on_generatecutout_button_click)
        # self.ui.generate_bb_button.clicked.connect(self.on_generatebb_button_click)
        # self.ui.generate_noncopper_button.clicked.connect(self.on_generatenoncopper_button_click)

    def set_ui(self, ui):
        FlatCAMObj.set_ui(self, ui)

        FlatCAMApp.App.log.debug("FlatCAMGerber.set_ui()")

        self.form_fields.update({
            "plot": self.ui.plot_cb,
            "multicolored": self.ui.multicolored_cb,
            "solid": self.ui.solid_cb,
            "isotooldia": self.ui.iso_tool_dia_entry,
            "isopasses": self.ui.iso_width_entry,
            "isooverlap": self.ui.iso_overlap_entry,
            "combine_passes":self.ui.combine_passes_cb,
            "cutouttooldia": self.ui.cutout_tooldia_entry,
            "cutoutmargin": self.ui.cutout_margin_entry,
            "cutoutgapsize": self.ui.cutout_gap_entry,
            "gaps": self.ui.gaps_radio,
            "noncoppermargin": self.ui.noncopper_margin_entry,
            "noncopperrounded": self.ui.noncopper_rounded_cb,
            "bboxmargin": self.ui.bbmargin_entry,
            "bboxrounded": self.ui.bbrounded_cb
        })

        assert isinstance(self.ui, GerberObjectUI)
        self.ui.plot_cb.stateChanged.connect(self.on_plot_cb_click)
        self.ui.solid_cb.stateChanged.connect(self.on_solid_cb_click)
        self.ui.multicolored_cb.stateChanged.connect(self.on_multicolored_cb_click)
        self.ui.generate_iso_button.clicked.connect(self.on_iso_button_click)
        self.ui.generate_cutout_button.clicked.connect(self.on_generatecutout_button_click)
        self.ui.generate_bb_button.clicked.connect(self.on_generatebb_button_click)
        self.ui.generate_noncopper_button.clicked.connect(self.on_generatenoncopper_button_click)

    def on_generatenoncopper_button_click(self, *args):
        self.app.report_usage("gerber_on_generatenoncopper_button")

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
        self.app.report_usage("gerber_on_generatebb_button")
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
        self.app.report_usage("gerber_on_generatecutout_button")
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
        self.app.report_usage("gerber_on_iso_button")
        self.read_form()
        self.isolate()

    def follow(self, outname=None):
        """
        Creates a geometry object "following" the gerber paths.

        :return: None
        """

        default_name = self.options["name"] + "_follow"
        follow_name = outname or default_name

        def follow_init(follow_obj, app_obj):
            # Propagate options
            follow_obj.options["cnctooldia"] = self.options["isotooldia"]
            follow_obj.solid_geometry = self.solid_geometry
            app_obj.info("Follow geometry created: %s" % follow_obj.options["name"])

        # TODO: Do something if this is None. Offer changing name?
        self.app.new_object("geometry", follow_name, follow_init)

    def isolate(self, dia=None, passes=None, overlap=None, outname=None, combine=None):
        """
        Creates an isolation routing geometry object in the project.

        :param dia: Tool diameter
        :param passes: Number of tool widths to cut
        :param overlap: Overlap between passes in fraction of tool diameter
        :param outname: Base name of the output object
        :return: None
        """
        if dia is None:
            dia = self.options["isotooldia"]
        if passes is None:
            passes = int(self.options["isopasses"])
        if overlap is None:
            overlap = self.options["isooverlap"]
        if combine is None:
            combine = self.options["combine_passes"]
        else:
            combine = bool(combine)

        base_name = self.options["name"] + "_iso"
        base_name = outname or base_name

        def generate_envelope (offset, invert):
            # isolation_geometry produces an envelope that is going on the left of the geometry
            # (the copper features). To leave the least amount of burrs on the features
            # the tool needs to travel on the right side of the features (this is called conventional milling)
            # the first pass is the one cutting all of the features, so it needs to be reversed
            # the other passes overlap preceding ones and cut the left over copper. It is better for them
            # to cut on the right side of the left over copper i.e on the left side of the features. 
            geom = self.isolation_geometry(offset)
            if invert:
                if type(geom) is MultiPolygon:
                    pl = []
                    for p in geom:
                        pl.append(Polygon (p.exterior.coords[::-1], p.interiors))
                    geom = MultiPolygon(pl)
                elif type(geom) is Polygon:
                    geom = Polygon (geom.exterior.coords[::-1], geom.interiors);
                else:
                    raise "Unexpected Geometry"
            return geom

        if (combine):
            iso_name = base_name

            # TODO: This is ugly. Create way to pass data into init function.
            def iso_init(geo_obj, app_obj):
                # Propagate options
                geo_obj.options["cnctooldia"] = self.options["isotooldia"]
                geo_obj.solid_geometry = []
                for i in range(passes):
                    offset = (2 * i + 1) / 2.0 * dia - i * overlap * dia
                    geom = generate_envelope (offset, i == 0)
                    geo_obj.solid_geometry.append(geom)
                app_obj.info("Isolation geometry created: %s" % geo_obj.options["name"])

            # TODO: Do something if this is None. Offer changing name?
            self.app.new_object("geometry", iso_name, iso_init)

        else:
            for i in range(passes):

                offset = (2 * i + 1) / 2.0 * dia - i * overlap  * dia
                if passes > 1:
                    iso_name = base_name + str(i + 1)
                else:
                    iso_name = base_name

                # TODO: This is ugly. Create way to pass data into init function.
                def iso_init(geo_obj, app_obj):
                    # Propagate options
                    geo_obj.options["cnctooldia"] = self.options["isotooldia"]
                    geo_obj.solid_geometry = generate_envelope (offset, i == 0)
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

        FlatCAMApp.App.log.debug(str(inspect.stack()[1][3]) + " --> FlatCAMGerber.plot()")

        # Does all the required setup and returns False
        # if the 'ptint' option is set to False.
        if not FlatCAMObj.plot(self):
            return

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

        self.app.plotcanvas.auto_adjust_axes()

    def serialize(self):
        return {
            "options": self.options,
            "kind": self.kind
        }


class FlatCAMExcellon(FlatCAMObj, Excellon):
    """
    Represents Excellon/Drill code.
    """

    ui_type = ExcellonObjectUI

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
            # "toolselection": ""
            "tooldia": 0.1,
            "toolchange": False,
            "toolchangez": 1.0
        })

        # TODO: Document this.
        self.tool_cbs = {}

        # Attributes to be included in serialization
        # Always append to it because it carries contents
        # from predecessors.
        self.ser_attrs += ['options', 'kind']

    def build_ui(self):
        FlatCAMObj.build_ui(self)

        # Populate tool list
        n = len(self.tools)
        self.ui.tools_table.setColumnCount(2)
        self.ui.tools_table.setHorizontalHeaderLabels(['#', 'Diameter'])
        self.ui.tools_table.setRowCount(n)
        self.ui.tools_table.setSortingEnabled(False)
        i = 0
        for tool in self.tools:
            id = QtGui.QTableWidgetItem(tool)
            id.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
            self.ui.tools_table.setItem(i, 0, id)  # Tool name/id
            dia = QtGui.QTableWidgetItem(str(self.tools[tool]['C']))
            dia.setFlags(QtCore.Qt.ItemIsEnabled)
            self.ui.tools_table.setItem(i, 1, dia)  # Diameter
            i += 1
        self.ui.tools_table.resizeColumnsToContents()
        self.ui.tools_table.resizeRowsToContents()
        self.ui.tools_table.horizontalHeader().setStretchLastSection(True)
        self.ui.tools_table.verticalHeader().hide()
        self.ui.tools_table.setSortingEnabled(True)

    def set_ui(self, ui):
        """
        Configures the user interface for this object.
        Connects options to form fields.

        :param ui: User interface object.
        :type ui: ExcellonObjectUI
        :return: None
        """
        FlatCAMObj.set_ui(self, ui)

        FlatCAMApp.App.log.debug("FlatCAMExcellon.set_ui()")

        self.form_fields.update({
            "plot": self.ui.plot_cb,
            "solid": self.ui.solid_cb,
            "drillz": self.ui.cutz_entry,
            "travelz": self.ui.travelz_entry,
            "feedrate": self.ui.feedrate_entry,
            "tooldia": self.ui.tooldia_entry,
            "toolchange": self.ui.toolchange_cb,
            "toolchangez": self.ui.toolchangez_entry
        })

        assert isinstance(self.ui, ExcellonObjectUI)
        self.ui.plot_cb.stateChanged.connect(self.on_plot_cb_click)
        self.ui.solid_cb.stateChanged.connect(self.on_solid_cb_click)
        self.ui.generate_cnc_button.clicked.connect(self.on_create_cncjob_button_click)
        self.ui.generate_milling_button.clicked.connect(self.on_generate_milling_button_click)

    def get_selected_tools_list(self):
        """
        Returns the keys to the self.tools dictionary corresponding
        to the selections on the tool list in the GUI.
        """
        return [str(x.text()) for x in self.ui.tools_table.selectedItems()]

    def on_generate_milling_button_click(self, *args):
        self.app.report_usage("excellon_on_create_milling_button")
        self.read_form()

        # Get the tools from the list. These are keys
        # to self.tools
        tools = self.get_selected_tools_list()

        if len(tools) == 0:
            self.app.inform.emit("Please select one or more tools from the list and try again.")
            return

        for tool in tools:
            if self.tools[tool]["C"] < self.options["tooldia"]:
                self.app.inform.emit("[warning] Milling tool is larger than hole size. Cancelled.")
                return

        geo_name = self.options["name"] + "_mill"

        def geo_init(geo_obj, app_obj):
            assert isinstance(geo_obj, FlatCAMGeometry)
            app_obj.progress.emit(20)

            geo_obj.solid_geometry = []

            for hole in self.drills:
                if hole['tool'] in tools:
                    geo_obj.solid_geometry.append(
                        Point(hole['point']).buffer(self.tools[hole['tool']]["C"] / 2 -
                                                    self.options["tooldia"] / 2).exterior
                    )

        def geo_thread(app_obj):
            app_obj.new_object("geometry", geo_name, geo_init)
            app_obj.progress.emit(100)

        # Send to worker
        self.app.worker_task.emit({'fcn': geo_thread, 'params': [self.app]})

    def on_create_cncjob_button_click(self, *args):
        self.app.report_usage("excellon_on_create_cncjob_button")
        self.read_form()

        # Get the tools from the list
        tools = self.get_selected_tools_list()

        if len(tools) == 0:
            self.app.inform.emit("Please select one or more tools from the list and try again.")
            return

        job_name = self.options["name"] + "_cnc"

        # Object initialization function for app.new_object()
        def job_init(job_obj, app_obj):
            assert isinstance(job_obj, FlatCAMCNCjob)

            app_obj.progress.emit(20)
            job_obj.z_cut = self.options["drillz"]
            job_obj.z_move = self.options["travelz"]
            job_obj.feedrate = self.options["feedrate"]
            # There could be more than one drill size...
            # job_obj.tooldia =   # TODO: duplicate variable!
            # job_obj.options["tooldia"] =

            tools_csv = ','.join(tools)
            job_obj.generate_from_excellon_by_tool(self, tools_csv,
                                                   toolchange=self.options["toolchange"],
                                                   toolchangez=self.options["toolchangez"])

            app_obj.progress.emit(50)
            job_obj.gcode_parse()

            app_obj.progress.emit(60)
            job_obj.create_geometry()

            app_obj.progress.emit(80)

        # To be run in separate thread
        def job_thread(app_obj):
            app_obj.new_object("cncjob", job_name, job_init)
            app_obj.progress.emit(100)

        # Send to worker
        # self.app.worker.add_task(job_thread, [self.app])
        self.app.worker_task.emit({'fcn': job_thread, 'params': [self.app]})

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

        self.app.plotcanvas.auto_adjust_axes()


class FlatCAMCNCjob(FlatCAMObj, CNCjob):
    """
    Represents G-Code.
    """

    ui_type = CNCObjectUI

    def __init__(self, name, units="in", kind="generic", z_move=0.1,
                 feedrate=3.0, z_cut=-0.002, tooldia=0.0):

        FlatCAMApp.App.log.debug("Creating CNCJob object...")

        CNCjob.__init__(self, units=units, kind=kind, z_move=z_move,
                        feedrate=feedrate, z_cut=z_cut, tooldia=tooldia)

        FlatCAMObj.__init__(self, name)

        self.kind = "cncjob"

        self.options.update({
            "plot": True,
            "tooldia": 0.4 / 25.4,  # 0.4mm in inches
            "append": "",
            "prepend": ""
        })

        # Attributes to be included in serialization
        # Always append to it because it carries contents
        # from predecessors.
        self.ser_attrs += ['options', 'kind']

    def set_ui(self, ui):
        FlatCAMObj.set_ui(self, ui)

        FlatCAMApp.App.log.debug("FlatCAMCNCJob.set_ui()")

        assert isinstance(self.ui, CNCObjectUI)

        self.form_fields.update({
            "plot": self.ui.plot_cb,
            "tooldia": self.ui.tooldia_entry,
            "append": self.ui.append_text,
            "prepend": self.ui.prepend_text
        })

        self.ui.plot_cb.stateChanged.connect(self.on_plot_cb_click)
        self.ui.updateplot_button.clicked.connect(self.on_updateplot_button_click)
        self.ui.export_gcode_button.clicked.connect(self.on_exportgcode_button_click)

    def on_updateplot_button_click(self, *args):
        """
        Callback for the "Updata Plot" button. Reads the form for updates
        and plots the object.
        """
        self.read_form()
        self.plot()

    def on_exportgcode_button_click(self, *args):
        self.app.report_usage("cncjob_on_exportgcode_button")

        try:
            filename = QtGui.QFileDialog.getSaveFileName(caption="Export G-Code ...",
                                                         directory=self.app.defaults["last_folder"])
        except TypeError:
            filename = QtGui.QFileDialog.getSaveFileName(caption="Export G-Code ...")

        preamble = str(self.ui.prepend_text.get_value())
        postamble = str(self.ui.append_text.get_value())

        self.export_gcode(filename, preamble=preamble, postamble=postamble)

    def export_gcode(self, filename, preamble='', postamble=''):
        f = open(filename, 'w')
        f.write(preamble + '\n' + self.gcode + "\n" + postamble)
        f.close()

        self.app.file_opened.emit("cncjob", filename)
        self.app.inform.emit("Saved to: " + filename)

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

        self.app.plotcanvas.auto_adjust_axes()

    def convert_units(self, units):
        factor = CNCjob.convert_units(self, units)
        FlatCAMApp.App.log.debug("FlatCAMCNCjob.convert_units()")
        self.options["tooldia"] *= factor


class FlatCAMGeometry(FlatCAMObj, Geometry):
    """
    Geometric object not associated with a specific
    format.
    """

    ui_type = GeometryObjectUI

    @staticmethod
    def merge(geo_list, geo_final):
        """
        Merges the geometry of objects in geo_list into
        the geometry of geo_final.

        :param geo_list: List of FlatCAMGeometry Objects to join.
        :param geo_final: Destination FlatCAMGeometry object.
        :return: None
        """

        if geo_final.solid_geometry is None:
            geo_final.solid_geometry = []
        if type(geo_final.solid_geometry) is not list:
            geo_final.solid_geometry = [geo_final.solid_geometry]

        for geo in geo_list:

            # Expand lists
            if type(geo) is list:
                FlatCAMGeometry.merge(geo, geo_final)

            # If not list, just append
            else:
                geo_final.solid_geometry.append(geo.solid_geometry)

            # try:  # Iterable
            #     for shape in geo.solid_geometry:
            #         geo_final.solid_geometry.append(shape)
            #
            # except TypeError:  # Non-iterable
            #     geo_final.solid_geometry.append(geo.solid_geometry)

    def __init__(self, name):
        FlatCAMObj.__init__(self, name)
        Geometry.__init__(self)

        self.kind = "geometry"

        self.options.update({
            "plot": True,
            "cutz": -0.002,
            "travelz": 0.1,
            "feedrate": 5.0,
            "cnctooldia": 0.4 / 25.4,
            "painttooldia": 0.0625,
            "paintoverlap": 0.15,
            "paintmargin": 0.01,
            "paintmethod": "standard"
        })

        # Attributes to be included in serialization
        # Always append to it because it carries contents
        # from predecessors.
        self.ser_attrs += ['options', 'kind']

    def build_ui(self):
        FlatCAMObj.build_ui(self)

    def set_ui(self, ui):
        FlatCAMObj.set_ui(self, ui)

        FlatCAMApp.App.log.debug("FlatCAMGeometry.set_ui()")

        assert isinstance(self.ui, GeometryObjectUI)

        self.form_fields.update({
            "plot": self.ui.plot_cb,
            "cutz": self.ui.cutz_entry,
            "travelz": self.ui.travelz_entry,
            "feedrate": self.ui.cncfeedrate_entry,
            "cnctooldia": self.ui.cnctooldia_entry,
            "painttooldia": self.ui.painttooldia_entry,
            "paintoverlap": self.ui.paintoverlap_entry,
            "paintmargin": self.ui.paintmargin_entry,
            "paintmethod": self.ui.paintmethod_combo
        })

        self.ui.plot_cb.stateChanged.connect(self.on_plot_cb_click)
        self.ui.generate_cnc_button.clicked.connect(self.on_generatecnc_button_click)
        self.ui.generate_paint_button.clicked.connect(self.on_paint_button_click)

    def on_paint_button_click(self, *args):
        self.app.report_usage("geometry_on_paint_button")

        self.app.info("Click inside the desired polygon.")
        self.read_form()
        tooldia = self.options["painttooldia"]
        overlap = self.options["paintoverlap"]

        # Connection ID for the click event
        subscription = None

        # To be called after clicking on the plot.
        def doit(event):
            self.app.info("Painting polygon...")
            self.app.plotcanvas.mpl_disconnect(subscription)
            point = [event.xdata, event.ydata]
            self.paint_poly(point, tooldia, overlap)

        subscription = self.app.plotcanvas.mpl_connect('button_press_event', doit)

    def paint_poly(self, inside_pt, tooldia, overlap):

        # Which polygon.
        #poly = find_polygon(self.solid_geometry, inside_pt)
        poly = self.find_polygon(inside_pt)

        # No polygon?
        if poly is None:
            self.app.log.warning('No polygon found.')
            self.app.inform.emit('[warning] No polygon found.')
            return

        proc = self.app.proc_container.new("Painting polygon.")

        # Initializes the new geometry object
        def gen_paintarea(geo_obj, app_obj):
            assert isinstance(geo_obj, FlatCAMGeometry)
            #assert isinstance(app_obj, App)

            if self.options["paintmethod"] == "seed":
                cp = self.clear_polygon2(poly.buffer(-self.options["paintmargin"]), tooldia, overlap=overlap)

            else:
                cp = self.clear_polygon(poly.buffer(-self.options["paintmargin"]), tooldia, overlap=overlap)

            geo_obj.solid_geometry = list(cp.get_objects())
            geo_obj.options["cnctooldia"] = tooldia
            self.app.inform.emit("Done.")

        def job_thread(app_obj):
            try:
                name = self.options["name"] + "_paint"
                app_obj.new_object("geometry", name, gen_paintarea)
            except Exception as e:
                proc.done()
                raise e
            proc.done()

        self.app.inform.emit("Polygon Paint started ...")
        self.app.worker_task.emit({'fcn': job_thread, 'params': [self.app]})

    def on_generatecnc_button_click(self, *args):
        self.app.report_usage("geometry_on_generatecnc_button")
        self.read_form()
        self.generatecncjob()

    def generatecncjob(self, z_cut=None, z_move=None,
                       feedrate=None, tooldia=None, outname=None):

        outname = outname if outname is not None else self.options["name"] + "_cnc"
        z_cut = z_cut if z_cut is not None else self.options["cutz"]
        z_move = z_move if z_move is not None else self.options["travelz"]
        feedrate = feedrate if feedrate is not None else self.options["feedrate"]
        tooldia = tooldia if tooldia is not None else self.options["cnctooldia"]
        
        # Object initialization function for app.new_object()
        # RUNNING ON SEPARATE THREAD!
        def job_init(job_obj, app_obj):
            assert isinstance(job_obj, FlatCAMCNCjob)
            # Propagate options
            job_obj.options["tooldia"] = tooldia

            app_obj.progress.emit(20)
            job_obj.z_cut = z_cut
            job_obj.z_move = z_move
            job_obj.feedrate = feedrate

            app_obj.progress.emit(40)
            # TODO: The tolerance should not be hard coded. Just for testing.
            job_obj.generate_from_geometry_2(self, tolerance=0.0005)

            app_obj.progress.emit(50)
            job_obj.gcode_parse()

            app_obj.progress.emit(80)

        # To be run in separate thread
        def job_thread(app_obj):
            with self.app.proc_container.new("Generating CNC Job."):
                app_obj.new_object("cncjob", outname, job_init)
                app_obj.inform.emit("CNCjob created: %s" % outname)
                app_obj.progress.emit(100)

        # Send to worker
        self.app.worker_task.emit({'fcn': job_thread, 'params': [self.app]})

    def on_plot_cb_click(self, *args):  # TODO: args not needed
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

    def plot_element(self, element):
        try:
            for sub_el in element:
                self.plot_element(sub_el)

        except TypeError:  # Element is not iterable...

            if type(element) == Polygon:
                x, y = element.exterior.coords.xy
                self.axes.plot(x, y, 'r-')
                for ints in element.interiors:
                    x, y = ints.coords.xy
                    self.axes.plot(x, y, 'r-')
                return

            if type(element) == LineString or type(element) == LinearRing:
                x, y = element.coords.xy
                self.axes.plot(x, y, 'r-')
                return

            FlatCAMApp.App.log.warning("Did not plot:" + str(type(element)))

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
        # TODO: This method should not modify the object !!!
        # try:
        #     _ = iter(self.solid_geometry)
        # except TypeError:
        #     if self.solid_geometry is None:
        #         self.solid_geometry = []
        #     else:
        #         self.solid_geometry = [self.solid_geometry]
        #
        # for geo in self.solid_geometry:
        #
        #     if type(geo) == Polygon:
        #         x, y = geo.exterior.coords.xy
        #         self.axes.plot(x, y, 'r-')
        #         for ints in geo.interiors:
        #             x, y = ints.coords.xy
        #             self.axes.plot(x, y, 'r-')
        #         continue
        #
        #     if type(geo) == LineString or type(geo) == LinearRing:
        #         x, y = geo.coords.xy
        #         self.axes.plot(x, y, 'r-')
        #         continue
        #
        #     if type(geo) == MultiPolygon:
        #         for poly in geo:
        #             x, y = poly.exterior.coords.xy
        #             self.axes.plot(x, y, 'r-')
        #             for ints in poly.interiors:
        #                 x, y = ints.coords.xy
        #                 self.axes.plot(x, y, 'r-')
        #         continue
        #
        #     FlatCAMApp.App.log.warning("Did not plot:", str(type(geo)))

        self.plot_element(self.solid_geometry)

        self.app.plotcanvas.auto_adjust_axes()
