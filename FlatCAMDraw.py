from PyQt4 import QtGui, QtCore, Qt
import FlatCAMApp

from shapely.geometry import Polygon, LineString, Point, LinearRing
from shapely.geometry import MultiPoint, MultiPolygon
from shapely.geometry import box as shply_box
from shapely.ops import cascaded_union, unary_union
import shapely.affinity as affinity
from shapely.wkt import loads as sloads
from shapely.wkt import dumps as sdumps
from shapely.geometry.base import BaseGeometry

from numpy import arctan2, Inf, array, sqrt, pi, ceil, sin, cos

from mpl_toolkits.axes_grid.anchored_artists import AnchoredDrawingArea

from rtree import index as rtindex

class DrawTool(object):
    def __init__(self, draw_app):
        self.draw_app = draw_app
        self.complete = False
        self.start_msg = "Click on 1st point..."
        self.points = []
        self.geometry = None

    def click(self, point):
        return ""

    def utility_geometry(self, data=None):
        return None


class FCShapeTool(DrawTool):
    def __init__(self, draw_app):
        DrawTool.__init__(self, draw_app)

    def make(self):
        pass


class FCCircle(FCShapeTool):
    def __init__(self, draw_app):
        DrawTool.__init__(self, draw_app)
        self.start_msg = "Click on CENTER ..."

    def click(self, point):
        self.points.append(point)

        if len(self.points) == 1:
            return "Click on perimeter to complete ..."

        if len(self.points) == 2:
            self.make()
            return "Done."

        return ""

    def utility_geometry(self, data=None):
        if len(self.points) == 1:
            p1 = self.points[0]
            p2 = data
            radius = sqrt((p1[0]-p2[0])**2 + (p1[1]-p2[1])**2)
            return Point(p1).buffer(radius)

        return None

    def make(self):
        p1 = self.points[0]
        p2 = self.points[1]
        radius = sqrt((p1[0]-p2[0])**2 + (p1[1]-p2[1])**2)
        self.geometry = Point(p1).buffer(radius)
        self.complete = True


class FCRectangle(FCShapeTool):
    def __init__(self, draw_app):
        DrawTool.__init__(self, draw_app)
        self.start_msg = "Click on 1st corner ..."

    def click(self, point):
        self.points.append(point)

        if len(self.points) == 1:
            return "Click on opposite corner to complete ..."

        if len(self.points) == 2:
            self.make()
            return "Done."

        return ""

    def utility_geometry(self, data=None):
        if len(self.points) == 1:
            p1 = self.points[0]
            p2 = data
            return LinearRing([p1, (p2[0], p1[1]), p2, (p1[0], p2[1])])

        return None

    def make(self):
        p1 = self.points[0]
        p2 = self.points[1]
        #self.geometry = LinearRing([p1, (p2[0], p1[1]), p2, (p1[0], p2[1])])
        self.geometry = Polygon([p1, (p2[0], p1[1]), p2, (p1[0], p2[1])])
        self.complete = True


class FCPolygon(FCShapeTool):
    def __init__(self, draw_app):
        DrawTool.__init__(self, draw_app)
        self.start_msg = "Click on 1st point ..."

    def click(self, point):
        self.points.append(point)

        if len(self.points) > 0:
            return "Click on next point or hit SPACE to complete ..."

        return ""

    def utility_geometry(self, data=None):
        if len(self.points) == 1:
            temp_points = [x for x in self.points]
            temp_points.append(data)
            return LineString(temp_points)

        if len(self.points) > 1:
            temp_points = [x for x in self.points]
            temp_points.append(data)
            return LinearRing(temp_points)

        return None

    def make(self):
        # self.geometry = LinearRing(self.points)
        self.geometry = Polygon(self.points)
        self.complete = True


class FCPath(FCPolygon):
    def make(self):
        self.geometry = LineString(self.points)
        self.complete = True

    def utility_geometry(self, data=None):
        if len(self.points) > 1:
            temp_points = [x for x in self.points]
            temp_points.append(data)
            return LineString(temp_points)

        return None


class FCSelect(DrawTool):
    def __init__(self, draw_app):
        DrawTool.__init__(self, draw_app)
        self.shape_buffer = self.draw_app.shape_buffer
        self.start_msg = "Click on geometry to select"

    def click(self, point):
        min_distance = Inf
        closest_shape = None

        for shape in self.shape_buffer:
            if self.draw_app.key != 'control':
                shape["selected"] = False

            distance = Point(point).distance(shape["geometry"])
            if distance < min_distance:
                closest_shape = shape
                min_distance = distance

        if closest_shape is not None:
            closest_shape["selected"] = True
            return "Shape selected."

        return "Nothing selected."


class FCMove(FCShapeTool):
    def __init__(self, draw_app):
        FCShapeTool.__init__(self, draw_app)
        self.shape_buffer = self.draw_app.shape_buffer
        self.origin = None
        self.destination = None
        self.start_msg = "Click on reference point."

    def set_origin(self, origin):
        self.origin = origin

    def click(self, point):
        if self.origin is None:
            self.set_origin(point)
            return "Click on final location."
        else:
            self.destination = point
            self.make()
            return "Done."

    def make(self):
        # Create new geometry
        dx = self.destination[0] - self.origin[0]
        dy = self.destination[1] - self.origin[1]
        self.geometry = [affinity.translate(geom['geometry'], xoff=dx, yoff=dy) for geom in self.draw_app.get_selected()]

        # Delete old
        for geo in self.draw_app.get_selected():
            self.draw_app.shape_buffer.remove(geo)

        self.complete = True

    def utility_geometry(self, data=None):
        """
        Temporary geometry on screen while using this tool.

        :param data:
        :return:
        """
        if self.origin is None:
            return None

        dx = data[0] - self.origin[0]
        dy = data[1] - self.origin[1]

        return [affinity.translate(geom['geometry'], xoff=dx, yoff=dy) for geom in self.draw_app.get_selected()]


class FCCopy(FCMove):
    def make(self):
        # Create new geometry
        dx = self.destination[0] - self.origin[0]
        dy = self.destination[1] - self.origin[1]
        self.geometry = [affinity.translate(geom['geometry'], xoff=dx, yoff=dy) for geom in self.draw_app.get_selected()]
        self.complete = True


########################
### Main Application ###
########################
class FlatCAMDraw(QtCore.QObject):
    def __init__(self, app, disabled=False):
        assert isinstance(app, FlatCAMApp.App)
        super(FlatCAMDraw, self).__init__()

        self.app = app
        self.canvas = app.plotcanvas
        self.axes = self.canvas.new_axes("draw")

        ### Drawing Toolbar ###
        self.drawing_toolbar = QtGui.QToolBar()
        self.drawing_toolbar.setDisabled(disabled)
        self.app.ui.addToolBar(self.drawing_toolbar)
        self.select_btn = self.drawing_toolbar.addAction(QtGui.QIcon('share/pointer32.png'), 'Select')
        self.add_circle_btn = self.drawing_toolbar.addAction(QtGui.QIcon('share/circle32.png'), 'Add Circle')
        self.add_rectangle_btn = self.drawing_toolbar.addAction(QtGui.QIcon('share/rectangle32.png'), 'Add Rectangle')
        self.add_polygon_btn = self.drawing_toolbar.addAction(QtGui.QIcon('share/polygon32.png'), 'Add Polygon')
        self.add_path_btn = self.drawing_toolbar.addAction(QtGui.QIcon('share/path32.png'), 'Add Path')
        self.union_btn = self.drawing_toolbar.addAction(QtGui.QIcon('share/union32.png'), 'Polygon Union')
        self.move_btn = self.drawing_toolbar.addAction(QtGui.QIcon('share/move32.png'), 'Move Objects')
        self.copy_btn = self.drawing_toolbar.addAction(QtGui.QIcon('share/copy32.png'), 'Copy Objects')

        ### Snap Toolbar ###
        self.snap_toolbar = QtGui.QToolBar()
        self.grid_snap_btn = self.snap_toolbar.addAction(QtGui.QIcon('share/grid32.png'), 'Snap to grid')
        self.grid_gap_x_entry = QtGui.QLineEdit()
        self.grid_gap_x_entry.setMaximumWidth(70)
        self.grid_gap_x_entry.setToolTip("Grid X distance")
        self.snap_toolbar.addWidget(self.grid_gap_x_entry)
        self.grid_gap_y_entry = QtGui.QLineEdit()
        self.grid_gap_y_entry.setMaximumWidth(70)
        self.grid_gap_y_entry.setToolTip("Grid Y distante")
        self.snap_toolbar.addWidget(self.grid_gap_y_entry)

        self.corner_snap_btn = self.snap_toolbar.addAction(QtGui.QIcon('share/corner32.png'), 'Snap to corner')
        self.snap_max_dist_entry = QtGui.QLineEdit()
        self.snap_max_dist_entry.setMaximumWidth(70)
        self.snap_max_dist_entry.setToolTip("Max. magnet distance")
        self.snap_toolbar.addWidget(self.snap_max_dist_entry)

        self.snap_toolbar.setDisabled(disabled)
        self.app.ui.addToolBar(self.snap_toolbar)

        ### Event handlers ###
        ## Canvas events
        self.canvas.mpl_connect('button_press_event', self.on_canvas_click)
        self.canvas.mpl_connect('motion_notify_event', self.on_canvas_move)
        self.canvas.mpl_connect('key_press_event', self.on_canvas_key)
        self.canvas.mpl_connect('key_release_event', self.on_canvas_key_release)

        self.union_btn.triggered.connect(self.union)

        ## Toolbar events and properties
        self.tools = {
            "select": {"button": self.select_btn,
                       "constructor": FCSelect},
            "circle": {"button": self.add_circle_btn,
                       "constructor": FCCircle},
            "rectangle": {"button": self.add_rectangle_btn,
                          "constructor": FCRectangle},
            "polygon": {"button": self.add_polygon_btn,
                        "constructor": FCPolygon},
            "path": {"button": self.add_path_btn,
                     "constructor": FCPath},
            "move": {"button": self.move_btn,
                     "constructor": FCMove},
            "copy": {"button": self.copy_btn,
                     "constructor": FCCopy}
        }

        # Data
        self.active_tool = None
        self.shape_buffer = []

        self.move_timer = QtCore.QTimer()
        self.move_timer.setSingleShot(True)

        self.key = None  # Currently pressed key

        def make_callback(tool):
            def f():
                self.on_tool_select(tool)
            return f

        for tool in self.tools:
            self.tools[tool]["button"].triggered.connect(make_callback(tool))  # Events
            self.tools[tool]["button"].setCheckable(True)  # Checkable

        # for snap_tool in [self.grid_snap_btn, self.corner_snap_btn]:
        #     snap_tool.triggered.connect(lambda: self.toolbar_tool_toggle("grid_snap"))
        #     snap_tool.setCheckable(True)
        self.grid_snap_btn.setCheckable(True)
        self.grid_snap_btn.triggered.connect(lambda: self.toolbar_tool_toggle("grid_snap"))
        self.corner_snap_btn.setCheckable(True)
        self.corner_snap_btn.triggered.connect(lambda: self.toolbar_tool_toggle("corner_snap"))

        self.options = {
            "snap-x": 0.1,
            "snap-y": 0.1,
            "snap_max": 0.05,
            "grid_snap": False,
            "corner_snap": False,
        }

        self.grid_gap_x_entry.setText(str(self.options["snap-x"]))
        self.grid_gap_y_entry.setText(str(self.options["snap-y"]))
        self.snap_max_dist_entry.setText(str(self.options["snap_max"]))

        self.rtree_index = rtindex.Index()

        def entry2option(option, entry):
            self.options[option] = float(entry.text())

        self.grid_gap_x_entry.setValidator(QtGui.QDoubleValidator())
        self.grid_gap_x_entry.editingFinished.connect(lambda: entry2option("snap-x", self.grid_gap_x_entry))
        self.grid_gap_y_entry.setValidator(QtGui.QDoubleValidator())
        self.grid_gap_y_entry.editingFinished.connect(lambda: entry2option("snap-y", self.grid_gap_y_entry))
        self.snap_max_dist_entry.setValidator(QtGui.QDoubleValidator())
        self.snap_max_dist_entry.editingFinished.connect(lambda: entry2option("snap_max", self.snap_max_dist_entry))

    def activate(self):
        pass

    def deactivate(self):
        self.clear()
        self.drawing_toolbar.setDisabled(True)
        self.snap_toolbar.setDisabled(True)  # TODO: Combine and move into tool

    def toolbar_tool_toggle(self, key):
        self.options[key] = self.sender().isChecked()
        print "grid_snap", self.options["grid_snap"]

    def clear(self):
        self.active_tool = None
        self.shape_buffer = []
        self.replot()

    def edit_fcgeometry(self, fcgeometry):
        """
        Imports the geometry from the given FlatCAM Geometry object
        into the editor.

        :param fcgeometry: FlatCAMGeometry
        :return: None
        """

        if fcgeometry.solid_geometry is None:
            geometry = []
        else:
            try:
                _ = iter(fcgeometry.solid_geometry)
                geometry = fcgeometry.solid_geometry
            except TypeError:
                geometry = [fcgeometry.solid_geometry]

        # Delete contents of editor.
        self.shape_buffer = []

        # Link shapes into editor.
        for shape in geometry:
            self.shape_buffer.append({'geometry': shape,
                                      'selected': False,
                                      'utility': False})

        self.replot()
        self.drawing_toolbar.setDisabled(False)
        self.snap_toolbar.setDisabled(False)

    def on_tool_select(self, tool):
        """
        Behavior of the toolbar. Tool initialization.

        :rtype : None
        """
        self.app.log.debug("on_tool_select('%s')" % tool)

        # This is to make the group behave as radio group
        if tool in self.tools:
            if self.tools[tool]["button"].isChecked():
                self.app.log.debug("%s is checked." % tool)
                for t in self.tools:
                    if t != tool:
                        self.tools[t]["button"].setChecked(False)

                self.active_tool = self.tools[tool]["constructor"](self)
                self.app.info(self.active_tool.start_msg)
            else:
                self.app.log.debug("%s is NOT checked." % tool)
                for t in self.tools:
                    self.tools[t]["button"].setChecked(False)
                self.active_tool = None

    def on_canvas_click(self, event):
        """
        event.x .y have canvas coordinates
        event.xdaya .ydata have plot coordinates

        :param event:
        :return:
        """
        if self.active_tool is not None:
            # Dispatch event to active_tool
            msg = self.active_tool.click(self.snap(event.xdata, event.ydata))
            self.app.info(msg)

            # If it is a shape generating tool
            if isinstance(self.active_tool, FCShapeTool) and self.active_tool.complete:
                self.on_shape_complete()
                return

            if isinstance(self.active_tool, FCSelect):
                self.app.log.debug("Replotting after click.")
                self.replot()
        else:
            self.app.log.debug("No active tool to respond to click!")

    def on_canvas_move(self, event):
        """
        event.x .y have canvas coordinates
        event.xdaya .ydata have plot coordinates

        :param event:
        :return:
        """
        self.on_canvas_move_effective(event)
        return

        # self.move_timer.stop()
        #
        # if self.active_tool is None:
        #     return
        #
        # # Make a function to avoid late evaluation
        # def make_callback():
        #     def f():
        #         self.on_canvas_move_effective(event)
        #     return f
        # callback = make_callback()
        #
        # self.move_timer.timeout.connect(callback)
        # self.move_timer.start(500)  # Stops if aready running

    def on_canvas_move_effective(self, event):
        """
        Is called after timeout on timer set in on_canvas_move.

        For details on animating on MPL see:
        http://wiki.scipy.org/Cookbook/Matplotlib/Animations

        event.x .y have canvas coordinates
        event.xdaya .ydata have plot coordinates

        :param event:
        :return:
        """

        try:
            x = float(event.xdata)
            y = float(event.ydata)
        except TypeError:
            return

        if self.active_tool is None:
            return

        x, y = self.snap(x, y)

        ### Utility geometry (animated)
        self.canvas.canvas.restore_region(self.canvas.background)
        geo = self.active_tool.utility_geometry(data=(x, y))

        if geo is not None and ((type(geo) == list and len(geo) > 0) or
                                (type(geo) != list and not geo.is_empty)):

            # Remove any previous utility shape
            for shape in self.shape_buffer:
                if shape['utility']:
                    self.shape_buffer.remove(shape)

            # Add the new utility shape
            self.shape_buffer.append({
                'geometry': geo,
                'selected': False,
                'utility': True
            })

            # Efficient plotting for fast animation

            #self.canvas.canvas.restore_region(self.canvas.background)
            elements = self.plot_shape(geometry=geo, linespec="b--", animated=True)
            for el in elements:
                self.axes.draw_artist(el)
            #self.canvas.canvas.blit(self.axes.bbox)

            #self.replot()


        elements = self.axes.plot(x, y, 'bo', animated=True)
        for el in elements:
                self.axes.draw_artist(el)
        self.canvas.canvas.blit(self.axes.bbox)

    def on_canvas_key(self, event):
        """
        event.key has the key.

        :param event:
        :return:
        """
        self.key = event.key

        ### Finish the current action. Use with tools that do not
        ### complete automatically, like a polygon or path.
        if event.key == ' ':
            if isinstance(self.active_tool, FCShapeTool):
                self.active_tool.click(self.snap(event.xdata, event.ydata))
                self.active_tool.make()
                if self.active_tool.complete:
                    self.on_shape_complete()
            return

        ### Abort the current action
        if event.key == 'escape':
            # TODO: ...?
            self.on_tool_select("select")
            self.app.info("Cancelled.")
            for_deletion = [shape for shape in self.shape_buffer if shape['utility']]
            for shape in for_deletion:
                self.shape_buffer.remove(shape)

            self.replot()
            self.select_btn.setChecked(True)
            self.on_tool_select('select')
            return

        ### Delete selected object
        if event.key == '-':
            self.delete_selected()
            self.replot()

        ### Move
        if event.key == 'm':
            self.move_btn.setChecked(True)
            self.on_tool_select('move')
            self.active_tool.set_origin(self.snap(event.xdata, event.ydata))

        ### Copy
        if event.key == 'c':
            self.copy_btn.setChecked(True)
            self.on_tool_select('copy')
            self.active_tool.set_origin(self.snap(event.xdata, event.ydata))

        ### Snap
        if event.key == 'g':
            self.grid_snap_btn.trigger()
        if event.key == 'k':
            self.corner_snap_btn.trigger()

    def on_canvas_key_release(self, event):
        self.key = None

    def get_selected(self):
        return [shape for shape in self.shape_buffer if shape["selected"]]

    def delete_selected(self):
        for shape in self.get_selected():
            self.shape_buffer.remove(shape)
            self.app.info("Shape deleted.")

    def plot_shape(self, geometry=None, linespec='b-', linewidth=1, animated=False):
        plot_elements = []

        if geometry is None:
            geometry = self.active_tool.geometry
        try:
            _ = iter(geometry)
            iterable_geometry = geometry
        except TypeError:
            iterable_geometry = [geometry]

        for geo in iterable_geometry:

            if type(geo) == Polygon:
                x, y = geo.exterior.coords.xy
                element, = self.axes.plot(x, y, linespec, linewidth=linewidth, animated=animated)
                plot_elements.append(element)
                for ints in geo.interiors:
                    x, y = ints.coords.xy
                    element, = self.axes.plot(x, y, linespec, linewidth=linewidth, animated=animated)
                    plot_elements.append(element)
                continue

            if type(geo) == LineString or type(geo) == LinearRing:
                x, y = geo.coords.xy
                element, = self.axes.plot(x, y, linespec, linewidth=linewidth, animated=animated)
                plot_elements.append(element)
                continue

            if type(geo) == MultiPolygon:
                for poly in geo:
                    x, y = poly.exterior.coords.xy
                    element, = self.axes.plot(x, y, linespec, linewidth=linewidth, animated=animated)
                    plot_elements.append(element)
                    for ints in poly.interiors:
                        x, y = ints.coords.xy
                        element, = self.axes.plot(x, y, linespec, linewidth=linewidth, animated=animated)
                        plot_elements.append(element)
                continue

        return plot_elements
        # self.canvas.auto_adjust_axes()

    def plot_all(self):
        self.app.log.debug("plot_all()")
        self.axes.cla()
        for shape in self.shape_buffer:
            if shape['geometry'] is None:  # TODO: This shouldn't have happened
                continue

            if shape['utility']:
                self.plot_shape(geometry=shape['geometry'], linespec='k--', linewidth=1)
                continue

            if shape['selected']:
                self.plot_shape(geometry=shape['geometry'], linespec='k-', linewidth=2)
                continue

            self.plot_shape(geometry=shape['geometry'])

        self.canvas.auto_adjust_axes()

    def add2index(self, id, geo):
        try:
            for pt in geo.coords:
                self.rtree_index.add(id, pt)
        except NotImplementedError:
            # It's a polygon?
            for pt in geo.exterior.coords:
                self.rtree_index.add(id, pt)

    def on_shape_complete(self):
        self.app.log.debug("on_shape_complete()")

        # For some reason plotting just the last created figure does not
        # work. The figure is not shown. Calling replot does the trick
        # which generates a new axes object.
        #self.plot_shape()
        #self.canvas.auto_adjust_axes()

        try:
            for geo in self.active_tool.geometry:
                self.shape_buffer.append({'geometry': geo,
                                          'selected': False,
                                          'utility': False})
                self.add2index(len(self.shape_buffer)-1, geo)
        except TypeError:
            self.shape_buffer.append({'geometry': self.active_tool.geometry,
                                      'selected': False,
                                      'utility': False})
            self.add2index(len(self.shape_buffer)-1, self.active_tool.geometry)

        # Remove any utility shapes
        for shape in self.shape_buffer:
            if shape['utility']:
                self.shape_buffer.remove(shape)

        self.replot()
        self.active_tool = type(self.active_tool)(self)

    def replot(self):
        #self.canvas.clear()
        self.axes = self.canvas.new_axes("draw")
        self.plot_all()

    def snap(self, x, y):
        """
        Adjusts coordinates to snap settings.

        :param x: Input coordinate X
        :param y: Input coordinate Y
        :return: Snapped (x, y)
        """

        snap_x, snap_y = (x, y)
        snap_distance = Inf

        ### Object (corner?) snap
        if self.options["corner_snap"]:
            try:
                bbox = self.rtree_index.nearest((x, y), objects=True).next().bbox
                nearest_pt = (bbox[0], bbox[1])

                nearest_pt_distance = distance((x, y), nearest_pt)
                if nearest_pt_distance <= self.options["snap_max"]:
                    snap_distance = nearest_pt_distance
                    snap_x, snap_y = nearest_pt
            except StopIteration:
                pass

        ### Grid snap
        if self.options["grid_snap"]:
            if self.options["snap-x"] != 0:
                snap_x_ = round(x/self.options["snap-x"])*self.options['snap-x']
            else:
                snap_x_ = x

            if self.options["snap-y"] != 0:
                snap_y_ = round(y/self.options["snap-y"])*self.options['snap-y']
            else:
                snap_y_ = y
            nearest_grid_distance = distance((x, y), (snap_x_, snap_y_))
            if nearest_grid_distance < snap_distance:
                snap_x, snap_y = (snap_x_, snap_y_)

        return snap_x, snap_y

    def update_fcgeometry(self, fcgeometry):
        """
        Transfers the drawing tool shape buffer to the selected geometry
        object. The geometry already in the object are removed.

        :param fcgeometry: FlatCAMGeometry
        :return: None
        """
        fcgeometry.solid_geometry = []
        for shape in self.shape_buffer:
            fcgeometry.solid_geometry.append(shape['geometry'])

    def union(self):
        """
        Makes union of selected polygons. Original polygons
        are deleted.

        :return: None.
        """
        targets = [shape for shape in self.shape_buffer if shape['selected']]

        results = cascaded_union([t['geometry'] for t in targets])

        for shape in targets:
            self.shape_buffer.remove(shape)

        try:
            for geo in results:

                self.shape_buffer.append({
                    'geometry': geo,
                    'selected': True,
                    'utility': False
                })
        except TypeError:
            self.shape_buffer.append({
                'geometry': results,
                'selected': True,
                'utility': False
            })

        self.replot()


def distance(pt1, pt2):
    return sqrt((pt1[0]-pt2[0])**2 + (pt1[1]-pt2[1])**2)