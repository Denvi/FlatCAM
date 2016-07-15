from PyQt4 import QtGui
from FlatCAMTool import FlatCAMTool
from copy import copy
from math import sqrt


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
        self.app.plotcanvas.vis_connect('key_press', self.on_key_press)

    def run(self):
        self.toggle()

    def on_click(self, event):
        pos = self.app.plotcanvas.vispy_canvas.translate_coords(event.pos)
        if self.point1 is None:
            self.point1 = pos
        else:
            self.point2 = copy(self.point1)
            self.point1 = pos
        self.on_move(event)

    def on_key_press(self, event):
        if event.key == 'R':
            self.toggle()

    def toggle(self):
        if self.isVisible():
            self.setVisible(False)
            self.app.plotcanvas.vis_disconnect('mouse_move', self.on_move)
            self.app.plotcanvas.vis_disconnect('mouse_release', self.on_click)
        else:
            self.setVisible(True)
            self.app.plotcanvas.vis_connect('mouse_move', self.on_move)
            self.app.plotcanvas.vis_connect('mouse_release', self.on_click)

    def on_move(self, event):
        if self.point1 is None:
            self.label.setText("Click on a reference point...")
        else:
            try:
                pos = self.app.plotcanvas.vispy_canvas.translate_coords(event.pos)
                dx = pos[0] - self.point1[0]
                dy = pos[1] - self.point1[1]
                d = sqrt(dx**2 + dy**2)
                self.label.setText("D = %.4f  D(x) = %.4f  D(y) = %.4f" % (d, dx, dy))
            except TypeError:
                pass
        if self.update is not None:
            self.update()
