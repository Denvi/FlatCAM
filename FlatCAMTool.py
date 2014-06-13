from PyQt4 import QtGui, QtCore
from shapely.geometry import Point
from shapely import affinity
from math import sqrt

import FlatCAMApp
from GUIElements import *
from FlatCAMObj import FlatCAMGerber, FlatCAMExcellon


class FlatCAMTool(QtGui.QWidget):

    toolName = "FlatCAM Generic Tool"

    def __init__(self, app, parent=None):
        """

        :param app: The application this tool will run in.
        :type app: App
        :param parent: Qt Parent
        :return: FlatCAMTool
        """
        QtGui.QWidget.__init__(self, parent)

        # self.setSizePolicy(QtGui.QSizePolicy.Maximum, QtGui.QSizePolicy.Maximum)

        self.layout = QtGui.QVBoxLayout()
        self.setLayout(self.layout)

        self.app = app

        self.menuAction = None

    def install(self):
        self.menuAction = self.app.ui.menutool.addAction(self.toolName)
        self.menuAction.triggered.connect(self.run)

    def run(self):
        # Remove anything else in the GUI
        self.app.ui.tool_scroll_area.takeWidget()

        # Put ourself in the GUI
        self.app.ui.tool_scroll_area.setWidget(self)

        # Switch notebook to tool page
        self.app.ui.notebook.setCurrentWidget(self.app.ui.tool_tab)

        self.show()


class DblSidedTool(FlatCAMTool):

    toolName = "Double-Sided PCB Tool"

    def __init__(self, app):
        FlatCAMTool.__init__(self, app)

        ## Title
        title_label = QtGui.QLabel("<font size=4><b>%s</b></font>" % self.toolName)
        self.layout.addWidget(title_label)

        ## Form Layout
        form_layout = QtGui.QFormLayout()
        self.layout.addLayout(form_layout)

        ## Layer to mirror
        self.object_combo = QtGui.QComboBox()
        self.object_combo.setModel(self.app.collection)
        form_layout.addRow("Bottom Layer:", self.object_combo)

        ## Axis
        self.mirror_axis = RadioSet([{'label': 'X', 'value': 'X'},
                                     {'label': 'Y', 'value': 'Y'}])
        form_layout.addRow("Mirror Axis:", self.mirror_axis)

        ## Axis Location
        self.axis_location = RadioSet([{'label': 'Point', 'value': 'point'},
                                       {'label': 'Box', 'value': 'box'}])
        form_layout.addRow("Axis Location:", self.axis_location)

        ## Point/Box
        self.point_box_container = QtGui.QVBoxLayout()
        form_layout.addRow("Point/Box:", self.point_box_container)
        self.point = EvalEntry()
        self.point_box_container.addWidget(self.point)
        self.box_combo = QtGui.QComboBox()
        self.box_combo.setModel(self.app.collection)
        self.point_box_container.addWidget(self.box_combo)
        self.box_combo.hide()

        ## Alignment holes
        self.alignment_holes = EvalEntry()
        form_layout.addRow("Alignment Holes:", self.alignment_holes)

        ## Drill diameter for alignment holes
        self.drill_dia = LengthEntry()
        form_layout.addRow("Drill diam.:", self.drill_dia)

        ## Buttons
        hlay = QtGui.QHBoxLayout()
        self.layout.addLayout(hlay)
        hlay.addStretch()
        self.create_alignment_hole_button = QtGui.QPushButton("Create Alignment Drill")
        self.mirror_object_button = QtGui.QPushButton("Mirror Object")
        hlay.addWidget(self.create_alignment_hole_button)
        hlay.addWidget(self.mirror_object_button)

        self.layout.addStretch()

        ## Signals
        self.create_alignment_hole_button.clicked.connect(self.on_create_alignment_holes)
        self.mirror_object_button.clicked.connect(self.on_mirror)

        self.axis_location.group_toggle_fn = self.on_toggle_pointbox

        ## Initialize form
        self.mirror_axis.set_value('X')
        self.axis_location.set_value('point')

    def on_create_alignment_holes(self):
        axis = self.mirror_axis.get_value()
        mode = self.axis_location.get_value()

        if mode == "point":
            px, py = self.point.get_value()
        else:
            selection_index = self.box_combo.currentIndex()
            bb_obj = self.app.collection.object_list[selection_index]  # TODO: Direct access??
            xmin, ymin, xmax, ymax = bb_obj.bounds()
            px = 0.5*(xmin+xmax)
            py = 0.5*(ymin+ymax)

        xscale, yscale = {"X": (1.0, -1.0), "Y": (-1.0, 1.0)}[axis]

        dia = self.drill_dia.get_value()
        tools = {"1": {"C": dia}}

        holes = self.alignment_holes.get_value()
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

        self.app.new_object("excellon", "Alignment Drills", obj_init)

    def on_mirror(self):
        selection_index = self.object_combo.currentIndex()
        fcobj = self.app.collection.object_list[selection_index]

        # For now, lets limit to Gerbers and Excellons.
        # assert isinstance(gerb, FlatCAMGerber)
        if not isinstance(fcobj, FlatCAMGerber) and not isinstance(fcobj, FlatCAMExcellon):
            self.info("ERROR: Only Gerber and Excellon objects can be mirrored.")
            return

        axis = self.mirror_axis.get_value()
        mode = self.axis_location.get_value()

        if mode == "point":
            px, py = self.point.get_value()
        else:
            selection_index = self.box_combo.currentIndex()
            bb_obj = self.app.collection.object_list[selection_index]  # TODO: Direct access??
            xmin, ymin, xmax, ymax = bb_obj.bounds()
            px = 0.5*(xmin+xmax)
            py = 0.5*(ymin+ymax)

        fcobj.mirror(axis, [px, py])
        fcobj.plot()

    def on_toggle_pointbox(self):
        if self.axis_location.get_value() == "point":
            self.point.show()
            self.box_combo.hide()
        else:
            self.point.hide()
            self.box_combo.show()


class Measurement(FlatCAMTool):

    toolName = "Measurement Tool"

    def __init__(self, app):
        FlatCAMTool.__init__(self, app)

        # self.setContentsMargins(0, 0, 0, 0)
        self.layout.setMargin(0)
        self.layout.setContentsMargins(0, 0, 3, 0)

        self.setSizePolicy(QtGui.QSizePolicy.Ignored, QtGui.QSizePolicy.Maximum)

        self.point1 = None
        self.point2 = None
        self.label = QtGui.QLabel("Click on a reference point ...")
        self.label.setFrameStyle(QtGui.QFrame.StyledPanel | QtGui.QFrame.Plain)
        self.label.setMargin(3)
        self.layout.addWidget(self.label)
        # self.layout.setMargin(0)
        self.setVisible(False)

        self.click_subscription = None
        self.move_subscription = None

    def install(self):
        FlatCAMTool.install(self)
        self.app.ui.right_layout.addWidget(self)
        self.app.plotcanvas.mpl_connect('key_press_event', self.on_key_press)

    def run(self):
        self.toggle()

    def on_click(self, event):
        if self.point1 is None:
            self.point1 = (event.xdata, event.ydata)
        else:
            self.point2 = copy(self.point1)
            self.point1 = (event.xdata, event.ydata)
        self.on_move(event)

    def on_key_press(self, event):
        if event.key == 'm':
            self.toggle()

    def toggle(self):
        if self.isVisible():
            self.setVisible(False)
            self.app.plotcanvas.mpl_disconnect(self.move_subscription)
            self.app.plotcanvas.mpl_disconnect(self.click_subscription)
        else:
            self.setVisible(True)
            self.move_subscription = self.app.plotcanvas.mpl_connect('motion_notify_event', self.on_move)
            self.click_subscription = self.app.plotcanvas.mpl_connect('button_press_event', self.on_click)

    def on_move(self, event):
        if self.point1 is None:
            self.label.setText("Click on a reference point...")
        else:
            try:
                dx = event.xdata - self.point1[0]
                dy = event.ydata - self.point1[1]
                d = sqrt(dx**2 + dy**2)
                self.label.setText("D = %.4f  D(x) = %.4f  D(y) = %.4f" % (d, dx, dy))
            except TypeError:
                pass
        if self.update is not None:
            self.update()



