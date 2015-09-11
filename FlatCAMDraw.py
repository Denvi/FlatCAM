from PyQt4 import QtGui, QtCore, Qt
import FlatCAMApp
from camlib import *
from FlatCAMTool import FlatCAMTool
from ObjectUI import LengthEntry

from shapely.geometry import Polygon, LineString, Point, LinearRing
from shapely.geometry import MultiPoint, MultiPolygon
from shapely.geometry import box as shply_box
from shapely.ops import cascaded_union, unary_union
import shapely.affinity as affinity
from shapely.wkt import loads as sloads
from shapely.wkt import dumps as sdumps
from shapely.geometry.base import BaseGeometry

from numpy import arctan2, Inf, array, sqrt, pi, ceil, sin, cos, sign, dot
from numpy.linalg import solve

#from mpl_toolkits.axes_grid.anchored_artists import AnchoredDrawingArea

from rtree import index as rtindex


class BufferSelectionTool(FlatCAMTool):
    """
    Simple input for buffer distance.
    """

    toolName = "Buffer Selection"

    def __init__(self, app, fcdraw):
        FlatCAMTool.__init__(self, app)

        self.fcdraw = fcdraw

        ## Title
        title_label = QtGui.QLabel("<font size=4><b>%s</b></font>" % self.toolName)
        self.layout.addWidget(title_label)

        ## Form Layout
        form_layout = QtGui.QFormLayout()
        self.layout.addLayout(form_layout)

        ## Buffer distance
        self.buffer_distance_entry = LengthEntry()
        form_layout.addRow("Buffer distance:", self.buffer_distance_entry)

        ## Buttons
        hlay = QtGui.QHBoxLayout()
        self.layout.addLayout(hlay)
        hlay.addStretch()
        self.buffer_button = QtGui.QPushButton("Buffer")
        hlay.addWidget(self.buffer_button)

        self.layout.addStretch()

        ## Signals
        self.buffer_button.clicked.connect(self.on_buffer)

    def on_buffer(self):
        buffer_distance = self.buffer_distance_entry.get_value()
        self.fcdraw.buffer(buffer_distance)


class DrawToolShape(object):
    """
    Encapsulates "shapes" under a common class.
    """

    @staticmethod
    def get_pts(o):
        """
        Returns a list of all points in the object, where
        the object can be a Polygon, Not a polygon, or a list
        of such. Search is done recursively.

        :param: geometric object
        :return: List of points
        :rtype: list
        """
        pts = []

        ## Iterable: descend into each item.
        try:
            for subo in o:
                pts += DrawToolShape.get_pts(subo)

        ## Non-iterable
        except TypeError:

            ## DrawToolShape: descend into .geo.
            if isinstance(o, DrawToolShape):
                pts += DrawToolShape.get_pts(o.geo)

            ## Descend into .exerior and .interiors
            elif type(o) == Polygon:
                pts += DrawToolShape.get_pts(o.exterior)
                for i in o.interiors:
                    pts += DrawToolShape.get_pts(i)

            ## Has .coords: list them.
            else:
                pts += list(o.coords)

        return pts

    def __init__(self, geo=[]):

        # Shapely type or list of such
        self.geo = geo
        self.utility = False

    def get_all_points(self):
        return DrawToolShape.get_pts(self)


class DrawToolUtilityShape(DrawToolShape):
    """
    Utility shapes are temporary geometry in the editor
    to assist in the creation of shapes. For example it
    will show the outline of a rectangle from the first
    point to the current mouse pointer before the second
    point is clicked and the final geometry is created.
    """

    def __init__(self, geo=[]):
        super(DrawToolUtilityShape, self).__init__(geo=geo)
        self.utility = True


class DrawTool(object):
    """
    Abstract Class representing a tool in the drawing
    program. Can generate geometry, including temporary
    utility geometry that is updated on user clicks
    and mouse motion.
    """
    def __init__(self, draw_app):
        self.draw_app = draw_app
        self.complete = False
        self.start_msg = "Click on 1st point..."
        self.points = []
        self.geometry = None  # DrawToolShape or None

    def click(self, point):
        """
        :param point: [x, y] Coordinate pair.
        """
        return ""

    def on_key(self, key):
        return None

    def utility_geometry(self, data=None):
        return None


class FCShapeTool(DrawTool):
    """
    Abstarct class for tools that create a shape.
    """
    def __init__(self, draw_app):
        DrawTool.__init__(self, draw_app)

    def make(self):
        pass


class FCCircle(FCShapeTool):
    """
    Resulting type: Polygon
    """

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
            radius = sqrt((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2)
            return DrawToolUtilityShape(Point(p1).buffer(radius))

        return None

    def make(self):
        p1 = self.points[0]
        p2 = self.points[1]
        radius = distance(p1, p2)
        self.geometry = DrawToolShape(Point(p1).buffer(radius))
        self.complete = True


class FCArc(FCShapeTool):
    def __init__(self, draw_app):
        DrawTool.__init__(self, draw_app)
        self.start_msg = "Click on CENTER ..."

        # Direction of rotation between point 1 and 2.
        # 'cw' or 'ccw'. Switch direction by hitting the
        # 'o' key.
        self.direction = "cw"

        # Mode
        # C12 = Center, p1, p2
        # 12C = p1, p2, Center
        # 132 = p1, p3, p2
        self.mode = "c12"  # Center, p1, p2

        self.steps_per_circ = 55

    def click(self, point):
        self.points.append(point)

        if len(self.points) == 1:
            return "Click on 1st point ..."

        if len(self.points) == 2:
            return "Click on 2nd point to complete ..."

        if len(self.points) == 3:
            self.make()
            return "Done."

        return ""

    def on_key(self, key):
        if key == 'o':
            self.direction = 'cw' if self.direction == 'ccw' else 'ccw'
            return 'Direction: ' + self.direction.upper()

        if key == 'p':
            if self.mode == 'c12':
                self.mode = '12c'
            elif self.mode == '12c':
                self.mode = '132'
            else:
                self.mode = 'c12'
            return 'Mode: ' + self.mode

    def utility_geometry(self, data=None):
        if len(self.points) == 1:  # Show the radius
            center = self.points[0]
            p1 = data

            return DrawToolUtilityShape(LineString([center, p1]))

        if len(self.points) == 2:  # Show the arc

            if self.mode == 'c12':
                center = self.points[0]
                p1 = self.points[1]
                p2 = data

                radius = sqrt((center[0] - p1[0]) ** 2 + (center[1] - p1[1]) ** 2)
                startangle = arctan2(p1[1] - center[1], p1[0] - center[0])
                stopangle = arctan2(p2[1] - center[1], p2[0] - center[0])

                return DrawToolUtilityShape([LineString(arc(center, radius, startangle, stopangle,
                                       self.direction, self.steps_per_circ)),
                        Point(center)])

            elif self.mode == '132':
                p1 = array(self.points[0])
                p3 = array(self.points[1])
                p2 = array(data)

                center, radius, t = three_point_circle(p1, p2, p3)
                direction = 'cw' if sign(t) > 0 else 'ccw'

                startangle = arctan2(p1[1] - center[1], p1[0] - center[0])
                stopangle = arctan2(p3[1] - center[1], p3[0] - center[0])

                return DrawToolUtilityShape([LineString(arc(center, radius, startangle, stopangle,
                                   direction, self.steps_per_circ)),
                        Point(center), Point(p1), Point(p3)])

            else:  # '12c'
                p1 = array(self.points[0])
                p2 = array(self.points[1])

                # Midpoint
                a = (p1 + p2) / 2.0

                # Parallel vector
                c = p2 - p1

                # Perpendicular vector
                b = dot(c, array([[0, -1], [1, 0]], dtype=float32))
                b /= norm(b)

                # Distance
                t = distance(data, a)

                # Which side? Cross product with c.
                # cross(M-A, B-A), where line is AB and M is test point.
                side = (data[0] - p1[0]) * c[1] - (data[1] - p1[1]) * c[0]
                t *= sign(side)

                # Center = a + bt
                center = a + b * t

                radius = norm(center - p1)
                startangle = arctan2(p1[1] - center[1], p1[0] - center[0])
                stopangle = arctan2(p2[1] - center[1], p2[0] - center[0])

                return DrawToolUtilityShape([LineString(arc(center, radius, startangle, stopangle,
                                       self.direction, self.steps_per_circ)),
                        Point(center)])

        return None

    def make(self):

        if self.mode == 'c12':
            center = self.points[0]
            p1 = self.points[1]
            p2 = self.points[2]

            radius = distance(center, p1)
            startangle = arctan2(p1[1] - center[1], p1[0] - center[0])
            stopangle = arctan2(p2[1] - center[1], p2[0] - center[0])
            self.geometry = DrawToolShape(LineString(arc(center, radius, startangle, stopangle,
                                          self.direction, self.steps_per_circ)))

        elif self.mode == '132':
            p1 = array(self.points[0])
            p3 = array(self.points[1])
            p2 = array(self.points[2])

            center, radius, t = three_point_circle(p1, p2, p3)
            direction = 'cw' if sign(t) > 0 else 'ccw'

            startangle = arctan2(p1[1] - center[1], p1[0] - center[0])
            stopangle = arctan2(p3[1] - center[1], p3[0] - center[0])

            self.geometry = DrawToolShape(LineString(arc(center, radius, startangle, stopangle,
                                          direction, self.steps_per_circ)))

        else:  # self.mode == '12c'
            p1 = array(self.points[0])
            p2 = array(self.points[1])
            pc = array(self.points[2])

            # Midpoint
            a = (p1 + p2) / 2.0

            # Parallel vector
            c = p2 - p1

            # Perpendicular vector
            b = dot(c, array([[0, -1], [1, 0]], dtype=float32))
            b /= norm(b)

            # Distance
            t = distance(pc, a)

            # Which side? Cross product with c.
            # cross(M-A, B-A), where line is AB and M is test point.
            side = (pc[0] - p1[0]) * c[1] - (pc[1] - p1[1]) * c[0]
            t *= sign(side)

            # Center = a + bt
            center = a + b * t

            radius = norm(center - p1)
            startangle = arctan2(p1[1] - center[1], p1[0] - center[0])
            stopangle = arctan2(p2[1] - center[1], p2[0] - center[0])

            self.geometry = DrawToolShape(LineString(arc(center, radius, startangle, stopangle,
                                           self.direction, self.steps_per_circ)))
        self.complete = True


class FCRectangle(FCShapeTool):
    """
    Resulting type: Polygon
    """

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
            return DrawToolUtilityShape(LinearRing([p1, (p2[0], p1[1]), p2, (p1[0], p2[1])]))

        return None

    def make(self):
        p1 = self.points[0]
        p2 = self.points[1]
        #self.geometry = LinearRing([p1, (p2[0], p1[1]), p2, (p1[0], p2[1])])
        self.geometry = DrawToolShape(Polygon([p1, (p2[0], p1[1]), p2, (p1[0], p2[1])]))
        self.complete = True


class FCPolygon(FCShapeTool):
    """
    Resulting type: Polygon
    """

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
            return DrawToolUtilityShape(LineString(temp_points))

        if len(self.points) > 1:
            temp_points = [x for x in self.points]
            temp_points.append(data)
            return DrawToolUtilityShape(LinearRing(temp_points))

        return None

    def make(self):
        # self.geometry = LinearRing(self.points)
        self.geometry = DrawToolShape(Polygon(self.points))
        self.complete = True


class FCPath(FCPolygon):
    """
    Resulting type: LineString
    """

    def make(self):
        self.geometry = DrawToolShape(LineString(self.points))
        self.complete = True

    def utility_geometry(self, data=None):
        if len(self.points) > 1:
            temp_points = [x for x in self.points]
            temp_points.append(data)
            return DrawToolUtilityShape(LineString(temp_points))

        return None


class FCSelect(DrawTool):
    def __init__(self, draw_app):
        DrawTool.__init__(self, draw_app)
        self.storage = self.draw_app.storage
        #self.shape_buffer = self.draw_app.shape_buffer
        self.selected = self.draw_app.selected
        self.start_msg = "Click on geometry to select"

    def click(self, point):
        try:
            _, closest_shape = self.storage.nearest(point)
        except StopIteration:
            return ""

        if self.draw_app.key != 'control':
            self.draw_app.selected = []

        self.draw_app.set_selected(closest_shape)
        self.draw_app.app.log.debug("Selected shape containing: " + str(closest_shape.geo))

        return ""


class FCMove(FCShapeTool):
    def __init__(self, draw_app):
        FCShapeTool.__init__(self, draw_app)
        #self.shape_buffer = self.draw_app.shape_buffer
        self.origin = None
        self.destination = None
        self.start_msg = "Click on reference point."

    def set_origin(self, origin):
        self.origin = origin

    def click(self, point):
        if len(self.draw_app.get_selected()) == 0:
            return "Nothing to move."

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
        self.geometry = [DrawToolShape(affinity.translate(geom.geo, xoff=dx, yoff=dy))
                         for geom in self.draw_app.get_selected()]

        # Delete old
        self.draw_app.delete_selected()

        # # Select the new
        # for g in self.geometry:
        #     # Note that g is not in the app's buffer yet!
        #     self.draw_app.set_selected(g)

        self.complete = True

    def utility_geometry(self, data=None):
        """
        Temporary geometry on screen while using this tool.

        :param data:
        :return:
        """
        if self.origin is None:
            return None

        if len(self.draw_app.get_selected()) == 0:
            return None

        dx = data[0] - self.origin[0]
        dy = data[1] - self.origin[1]

        return DrawToolUtilityShape([affinity.translate(geom.geo, xoff=dx, yoff=dy)
                                     for geom in self.draw_app.get_selected()])


class FCCopy(FCMove):
    def make(self):
        # Create new geometry
        dx = self.destination[0] - self.origin[0]
        dy = self.destination[1] - self.origin[1]
        self.geometry = [DrawToolShape(affinity.translate(geom.geo, xoff=dx, yoff=dy))
                         for geom in self.draw_app.get_selected()]
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
        self.select_btn = self.drawing_toolbar.addAction(QtGui.QIcon('share/pointer32.png'), "Select 'Esc'")
        self.add_circle_btn = self.drawing_toolbar.addAction(QtGui.QIcon('share/circle32.png'), 'Add Circle')
        self.add_arc_btn = self.drawing_toolbar.addAction(QtGui.QIcon('share/arc32.png'), 'Add Arc')
        self.add_rectangle_btn = self.drawing_toolbar.addAction(QtGui.QIcon('share/rectangle32.png'), 'Add Rectangle')
        self.add_polygon_btn = self.drawing_toolbar.addAction(QtGui.QIcon('share/polygon32.png'), 'Add Polygon')
        self.add_path_btn = self.drawing_toolbar.addAction(QtGui.QIcon('share/path32.png'), 'Add Path')
        self.union_btn = self.drawing_toolbar.addAction(QtGui.QIcon('share/union32.png'), 'Polygon Union')
        self.intersection_btn = self.drawing_toolbar.addAction(QtGui.QIcon('share/intersection32.png'), 'Polygon Intersection')
        self.subtract_btn = self.drawing_toolbar.addAction(QtGui.QIcon('share/subtract32.png'), 'Polygon Subtraction')
        self.cutpath_btn = self.drawing_toolbar.addAction(QtGui.QIcon('share/cutpath32.png'), 'Cut Path')
        self.move_btn = self.drawing_toolbar.addAction(QtGui.QIcon('share/move32.png'), "Move Objects 'm'")
        self.copy_btn = self.drawing_toolbar.addAction(QtGui.QIcon('share/copy32.png'), "Copy Objects 'c'")
        self.delete_btn = self.drawing_toolbar.addAction(QtGui.QIcon('share/deleteshape32.png'), "Delete Shape '-'")

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

        ### Application menu ###
        self.menu = QtGui.QMenu("Drawing")
        self.app.ui.menu.insertMenu(self.app.ui.menutoolaction, self.menu)
        # self.select_menuitem = self.menu.addAction(QtGui.QIcon('share/pointer16.png'), "Select 'Esc'")
        # self.add_circle_menuitem = self.menu.addAction(QtGui.QIcon('share/circle16.png'), 'Add Circle')
        # self.add_arc_menuitem = self.menu.addAction(QtGui.QIcon('share/arc16.png'), 'Add Arc')
        # self.add_rectangle_menuitem = self.menu.addAction(QtGui.QIcon('share/rectangle16.png'), 'Add Rectangle')
        # self.add_polygon_menuitem = self.menu.addAction(QtGui.QIcon('share/polygon16.png'), 'Add Polygon')
        # self.add_path_menuitem = self.menu.addAction(QtGui.QIcon('share/path16.png'), 'Add Path')
        self.union_menuitem = self.menu.addAction(QtGui.QIcon('share/union16.png'), 'Polygon Union')
        self.intersection_menuitem = self.menu.addAction(QtGui.QIcon('share/intersection16.png'), 'Polygon Intersection')
        # self.subtract_menuitem = self.menu.addAction(QtGui.QIcon('share/subtract16.png'), 'Polygon Subtraction')
        self.cutpath_menuitem = self.menu.addAction(QtGui.QIcon('share/cutpath16.png'), 'Cut Path')
        # self.move_menuitem = self.menu.addAction(QtGui.QIcon('share/move16.png'), "Move Objects 'm'")
        # self.copy_menuitem = self.menu.addAction(QtGui.QIcon('share/copy16.png'), "Copy Objects 'c'")
        self.delete_menuitem = self.menu.addAction(QtGui.QIcon('share/deleteshape16.png'), "Delete Shape '-'")
        self.buffer_menuitem = self.menu.addAction(QtGui.QIcon('share/buffer16.png'), "Buffer selection 'b'")
        self.menu.addSeparator()

        self.buffer_menuitem.triggered.connect(self.on_buffer_tool)
        self.delete_menuitem.triggered.connect(self.on_delete_btn)
        self.union_menuitem.triggered.connect(self.union)
        self.intersection_menuitem.triggered.connect(self.intersection)
        self.cutpath_menuitem.triggered.connect(self.cutpath)

        ### Event handlers ###
        # Connection ids for Matplotlib
        self.cid_canvas_click = None
        self.cid_canvas_move = None
        self.cid_canvas_key = None
        self.cid_canvas_key_release = None

        # Connect the canvas
        #self.connect_canvas_event_handlers()

        self.union_btn.triggered.connect(self.union)
        self.intersection_btn.triggered.connect(self.intersection)
        self.subtract_btn.triggered.connect(self.subtract)
        self.cutpath_btn.triggered.connect(self.cutpath)
        self.delete_btn.triggered.connect(self.on_delete_btn)

        ## Toolbar events and properties
        self.tools = {
            "select": {"button": self.select_btn,
                       "constructor": FCSelect},
            "circle": {"button": self.add_circle_btn,
                       "constructor": FCCircle},
            "arc": {"button": self.add_arc_btn,
                    "constructor": FCArc},
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

        ### Data
        self.active_tool = None

        self.storage = FlatCAMDraw.make_storage()
        self.utility = []

        ## List of selected shapes.
        self.selected = []

        self.move_timer = QtCore.QTimer()
        self.move_timer.setSingleShot(True)

        self.key = None  # Currently pressed key

        def make_callback(thetool):
            def f():
                self.on_tool_select(thetool)
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

    def connect_canvas_event_handlers(self):
        ## Canvas events
        self.cid_canvas_click = self.canvas.mpl_connect('button_press_event', self.on_canvas_click)
        self.cid_canvas_move = self.canvas.mpl_connect('motion_notify_event', self.on_canvas_move)
        self.cid_canvas_key = self.canvas.mpl_connect('key_press_event', self.on_canvas_key)
        self.cid_canvas_key_release = self.canvas.mpl_connect('key_release_event', self.on_canvas_key_release)

    def disconnect_canvas_event_handlers(self):
        self.canvas.mpl_disconnect(self.cid_canvas_click)
        self.canvas.mpl_disconnect(self.cid_canvas_move)
        self.canvas.mpl_disconnect(self.cid_canvas_key)
        self.canvas.mpl_disconnect(self.cid_canvas_key_release)

    def add_shape(self, shape):
        """
        Adds a shape to the shape storage.

        :param shape: Shape to be added.
        :type shape: DrawToolShape
        :return: None
        """

        # List of DrawToolShape?
        if isinstance(shape, list):
            for subshape in shape:
                self.add_shape(subshape)
            return

        assert isinstance(shape, DrawToolShape)
        assert shape.geo is not None
        assert (isinstance(shape.geo, list) and len(shape.geo) > 0) or not isinstance(shape.geo, list)

        if isinstance(shape, DrawToolUtilityShape):
            self.utility.append(shape)
        else:
            self.storage.insert(shape)

    def deactivate(self):
        self.disconnect_canvas_event_handlers()
        self.clear()
        self.drawing_toolbar.setDisabled(True)
        self.snap_toolbar.setDisabled(True)  # TODO: Combine and move into tool

    def delete_utility_geometry(self):
        #for_deletion = [shape for shape in self.shape_buffer if shape.utility]
        #for_deletion = [shape for shape in self.storage.get_objects() if shape.utility]
        for_deletion = [shape for shape in self.utility]
        for shape in for_deletion:
            self.delete_shape(shape)

    def cutpath(self):
        selected = self.get_selected()
        tools = selected[1:]
        toolgeo = cascaded_union([shp.geo for shp in tools])

        target = selected[0]
        if type(target.geo) == Polygon:
            for ring in poly2rings(target.geo):
                self.add_shape(DrawToolShape(ring.difference(toolgeo)))
            self.delete_shape(target)
        elif type(target.geo) == LineString or type(target.geo) == LinearRing:
            self.add_shape(DrawToolShape(target.geo.difference(toolgeo)))
            self.delete_shape(target)
        else:
            self.app.log.warning("Not implemented.")

        self.replot()

    def toolbar_tool_toggle(self, key):
        self.options[key] = self.sender().isChecked()

    def clear(self):
        self.active_tool = None
        #self.shape_buffer = []
        self.selected = []
        self.storage = FlatCAMDraw.make_storage()
        self.replot()

    def edit_fcgeometry(self, fcgeometry):
        """
        Imports the geometry from the given FlatCAM Geometry object
        into the editor.

        :param fcgeometry: FlatCAMGeometry
        :return: None
        """
        assert isinstance(fcgeometry, Geometry)

        self.deactivate()

        self.connect_canvas_event_handlers()
        self.select_tool("select")

        # Link shapes into editor.
        for shape in fcgeometry.flatten():
            if shape is not None:  # TODO: Make flatten never create a None
                self.add_shape(DrawToolShape(shape))

        self.replot()
        self.drawing_toolbar.setDisabled(False)
        self.snap_toolbar.setDisabled(False)

    def on_buffer_tool(self):
        buff_tool = BufferSelectionTool(self.app, self)
        buff_tool.run()

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
        event.x and .y have canvas coordinates
        event.xdaya and .ydata have plot coordinates

        :param event: Event object dispatched by Matplotlib
        :return: None
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
        event.x and .y have canvas coordinates
        event.xdaya and .ydata have plot coordinates

        :param event: Event object dispatched by Matplotlib
        :return:
        """
        self.on_canvas_move_effective(event)
        return None

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

        event.x and .y have canvas coordinates
        event.xdaya and .ydata have plot coordinates

        :param event: Event object dispatched by Matplotlib
        :return: None
        """

        try:
            x = float(event.xdata)
            y = float(event.ydata)
        except TypeError:
            return

        if self.active_tool is None:
            return

        ### Snap coordinates
        x, y = self.snap(x, y)

        ### Utility geometry (animated)
        self.canvas.canvas.restore_region(self.canvas.background)
        geo = self.active_tool.utility_geometry(data=(x, y))

        if isinstance(geo, DrawToolShape) and geo.geo is not None:

            # Remove any previous utility shape
            self.delete_utility_geometry()

            # Add the new utility shape
            self.add_shape(geo)

            # Efficient plotting for fast animation

            #self.canvas.canvas.restore_region(self.canvas.background)
            elements = self.plot_shape(geometry=geo.geo,
                                       linespec="b--",
                                       linewidth=1,
                                       animated=True)
            for el in elements:
                self.axes.draw_artist(el)
            #self.canvas.canvas.blit(self.axes.bbox)

        # Pointer (snapped)
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
            #self.on_tool_select("select")
            self.app.info("Cancelled.")

            self.delete_utility_geometry()

            self.replot()
            # self.select_btn.setChecked(True)
            # self.on_tool_select('select')
            self.select_tool('select')
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

        ### Buffer
        if event.key == 'b':
            self.on_buffer_tool()

        ### Propagate to tool
        response = None
        if self.active_tool is not None:
            response = self.active_tool.on_key(event.key)
        if response is not None:
            self.app.info(response)

    def on_canvas_key_release(self, event):
        self.key = None

    def on_delete_btn(self):
        self.delete_selected()
        self.replot()

    def get_selected(self):
        """
        Returns list of shapes that are selected in the editor.

        :return: List of shapes.
        """
        #return [shape for shape in self.shape_buffer if shape["selected"]]
        return self.selected

    def delete_selected(self):
        tempref = [s for s in self.selected]
        for shape in tempref:
            self.delete_shape(shape)

        self.selected = []

    def plot_shape(self, geometry=None, linespec='b-', linewidth=1, animated=False):
        """
        Plots a geometric object or list of objects without rendering. Plotted objects
        are returned as a list. This allows for efficient/animated rendering.

        :param geometry: Geometry to be plotted (Any Shapely.geom kind or list of such)
        :param linespec: Matplotlib linespec string.
        :param linewidth: Width of lines in # of pixels.
        :param animated: If geometry is to be animated. (See MPL plot())
        :return: List of plotted elements.
        """
        plot_elements = []

        if geometry is None:
            geometry = self.active_tool.geometry

        try:
            for geo in geometry:
                plot_elements += self.plot_shape(geometry=geo,
                                                 linespec=linespec,
                                                 linewidth=linewidth,
                                                 animated=animated)

        ## Non-iterable
        except TypeError:

            ## DrawToolShape
            if isinstance(geometry, DrawToolShape):
                plot_elements += self.plot_shape(geometry=geometry.geo,
                                                 linespec=linespec,
                                                 linewidth=linewidth,
                                                 animated=animated)

            ## Polygon: Dscend into exterior and each interior.
            if type(geometry) == Polygon:
                plot_elements += self.plot_shape(geometry=geometry.exterior,
                                                 linespec=linespec,
                                                 linewidth=linewidth,
                                                 animated=animated)
                plot_elements += self.plot_shape(geometry=geometry.interiors,
                                                 linespec=linespec,
                                                 linewidth=linewidth,
                                                 animated=animated)

            if type(geometry) == LineString or type(geometry) == LinearRing:
                x, y = geometry.coords.xy
                element, = self.axes.plot(x, y, linespec, linewidth=linewidth, animated=animated)
                plot_elements.append(element)

            if type(geometry) == Point:
                x, y = geometry.coords.xy
                element, = self.axes.plot(x, y, 'bo', linewidth=linewidth, animated=animated)
                plot_elements.append(element)

        return plot_elements

    def plot_all(self):
        """
        Plots all shapes in the editor.
        Clears the axes, plots, and call self.canvas.auto_adjust_axes.

        :return: None
        :rtype: None
        """
        self.app.log.debug("plot_all()")
        self.axes.cla()

        for shape in self.storage.get_objects():
            if shape.geo is None:  # TODO: This shouldn't have happened
                continue

            if shape in self.selected:
                self.plot_shape(geometry=shape.geo, linespec='k-', linewidth=2)
                continue

            self.plot_shape(geometry=shape.geo)

        for shape in self.utility:
            self.plot_shape(geometry=shape.geo, linespec='k--', linewidth=1)
            continue

        self.canvas.auto_adjust_axes()

    def on_shape_complete(self):
        self.app.log.debug("on_shape_complete()")

        # Add shape
        self.add_shape(self.active_tool.geometry)

        # Remove any utility shapes
        self.delete_utility_geometry()

        # Replot and reset tool.
        self.replot()
        self.active_tool = type(self.active_tool)(self)

    def delete_shape(self, shape):

        if shape in self.utility:
            self.utility.remove(shape)
            return

        self.storage.remove(shape)

        if shape in self.selected:
            self.selected.remove(shape)

    def replot(self):
        self.axes = self.canvas.new_axes("draw")
        self.plot_all()

    @staticmethod
    def make_storage():

        ## Shape storage.
        storage = FlatCAMRTreeStorage()
        storage.get_points = DrawToolShape.get_pts

        return storage

    def select_tool(self, toolname):
        """
        Selects a drawing tool. Impacts the object and GUI.

        :param toolname: Name of the tool.
        :return: None
        """
        self.tools[toolname]["button"].setChecked(True)
        self.on_tool_select(toolname)

    def set_selected(self, shape):

        # Remove and add to the end.
        if shape in self.selected:
            self.selected.remove(shape)

        self.selected.append(shape)

    def set_unselected(self, shape):
        if shape in self.selected:
            self.selected.remove(shape)

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
        ### No need for the objects, just the coordinates
        ### in the index.
        if self.options["corner_snap"]:
            try:
                nearest_pt, shape = self.storage.nearest((x, y))

                nearest_pt_distance = distance((x, y), nearest_pt)
                if nearest_pt_distance <= self.options["snap_max"]:
                    snap_distance = nearest_pt_distance
                    snap_x, snap_y = nearest_pt
            except (StopIteration, AssertionError):
                pass

        ### Grid snap
        if self.options["grid_snap"]:
            if self.options["snap-x"] != 0:
                snap_x_ = round(x / self.options["snap-x"]) * self.options['snap-x']
            else:
                snap_x_ = x

            if self.options["snap-y"] != 0:
                snap_y_ = round(y / self.options["snap-y"]) * self.options['snap-y']
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
        #for shape in self.shape_buffer:
        for shape in self.storage.get_objects():
            fcgeometry.solid_geometry.append(shape.geo)

    def union(self):
        """
        Makes union of selected polygons. Original polygons
        are deleted.

        :return: None.
        """

        results = cascaded_union([t.geo for t in self.get_selected()])

        # Delete originals.
        for_deletion = [s for s in self.get_selected()]
        for shape in for_deletion:
            self.delete_shape(shape)

        # Selected geometry is now gone!
        self.selected = []

        self.add_shape(DrawToolShape(results))

        self.replot()

    def intersection(self):
        """
        Makes intersectino of selected polygons. Original polygons are deleted.

        :return: None
        """

        shapes = self.get_selected()

        results = shapes[0].geo

        for shape in shapes[1:]:
            results = results.intersection(shape.geo)

        # Delete originals.
        for_deletion = [s for s in self.get_selected()]
        for shape in for_deletion:
            self.delete_shape(shape)

        # Selected geometry is now gone!
        self.selected = []

        self.add_shape(DrawToolShape(results))

        self.replot()

    def subtract(self):
        selected = self.get_selected()
        tools = selected[1:]
        toolgeo = cascaded_union([shp.geo for shp in tools])
        result = selected[0].geo.difference(toolgeo)

        self.delete_shape(selected[0])
        self.add_shape(DrawToolShape(result))

        self.replot()

    def buffer(self, buf_distance):
        selected = self.get_selected()

        if len(selected) == 0:
            self.app.inform.emit("[warning] Nothing selected for buffering.")
            return

        if not isinstance(buf_distance, float):
            self.app.inform.emit("[warning] Invalid distance for buffering.")
            return

        pre_buffer = cascaded_union([t.geo for t in selected])
        results = pre_buffer.buffer(buf_distance)
        self.add_shape(DrawToolShape(results))

        self.replot()


def distance(pt1, pt2):
    return sqrt((pt1[0] - pt2[0]) ** 2 + (pt1[1] - pt2[1]) ** 2)


def mag(vec):
    return sqrt(vec[0] ** 2 + vec[1] ** 2)


def poly2rings(poly):
    return [poly.exterior] + [interior for interior in poly.interiors]