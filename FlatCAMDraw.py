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


class FlatCAMDraw:
    def __init__(self, app, disabled=False):
        assert isinstance(app, FlatCAMApp.App)
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
                     "constructor": FCPath}
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

    def clear(self):
        self.active_tool = None
        self.shape_buffer = []
        self.replot()

    def on_tool_select(self, tool):
        """

        :rtype : None
        """
        self.app.log.debug("on_tool_select('%s')" % tool)

        # This is to make the group behave as radio group
        if tool in self.tools:
            if self.tools[tool]["button"].isChecked():
                self.app.log.debug("%s is checked.")
                for t in self.tools:
                    if t != tool:
                        self.tools[t]["button"].setChecked(False)

                self.active_tool = self.tools[tool]["constructor"](self)
                self.app.info(self.active_tool.start_msg)
            else:
                self.app.log.debug("%s is NOT checked.")
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
            msg = self.active_tool.click((event.xdata, event.ydata))
            self.app.info(msg)

            # If it is a shape generating tool
            if isinstance(self.active_tool, FCShapeTool) and self.active_tool.complete:
                self.on_shape_complete()
                return

            if isinstance(self.active_tool, FCSelect):
                self.app.log.debug("Replotting after click.")
                self.replot()

    def on_canvas_move(self, event):
        """
        event.x .y have canvas coordinates
        event.xdaya .ydata have plot coordinates

        :param event:
        :return:
        """
        self.on_canvas_move_effective(event)
        return

        self.move_timer.stop()

        if self.active_tool is None:
            return

        # Make a function to avoid late evaluation
        def make_callback():
            def f():
                self.on_canvas_move_effective(event)
            return f
        callback = make_callback()

        self.move_timer.timeout.connect(callback)
        self.move_timer.start(500)  # Stops if aready running

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

        geo = self.active_tool.utility_geometry(data=(x, y))

        if geo is not None:

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
            elements = self.plot_shape(geometry=geo, linespec="b--", animated=True)
            self.canvas.canvas.restore_region(self.canvas.background)
            for el in elements:
                self.axes.draw_artist(el)
            self.canvas.canvas.blit(self.axes.bbox)

            #self.replot()

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
                self.active_tool.click((event.xdata, event.ydata))
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
            return

        ### Delete selected object
        if event.key == '-':
            self.delete_selected()
            self.replot()

    def on_canvas_key_release(self, event):
        self.key = None

    def delete_selected(self):
        for_deletion = [shape for shape in self.shape_buffer if shape["selected"]]

        for shape in for_deletion:
            self.shape_buffer.remove(shape)
            self.app.info("Shape deleted.")

    def plot_shape(self, geometry=None, linespec='b-', linewidth=1, animated=False):
        self.app.log.debug("plot_shape()")
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
            if shape['utility']:
                self.plot_shape(geometry=shape['geometry'], linespec='k--', linewidth=1)
                continue

            if shape['selected']:
                self.plot_shape(geometry=shape['geometry'], linespec='k-', linewidth=2)
                continue

            self.plot_shape(geometry=shape['geometry'])

        self.canvas.auto_adjust_axes()

    def on_shape_complete(self):
        self.app.log.debug("on_shape_complete()")

        # For some reason plotting just the last created figure does not
        # work. The figure is not shown. Calling replot does the trick
        # which generates a new axes object.
        #self.plot_shape()
        #self.canvas.auto_adjust_axes()

        self.shape_buffer.append({'geometry': self.active_tool.geometry,
                                  'selected': False,
                                  'utility': False})

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

    def edit_fcgeometry(self, fcgeometry):
        """
        Imports the geometry from the given FlatCAM Geometry object
        into the editor.

        :param fcgeometry: FlatCAMGeometry
        :return: None
        """
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