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
        # TODO: Translate to vis
        # self.app.plotcanvas.mpl_connect('key_press_event', self.on_key_press)

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
        if event.key == 'r':
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
