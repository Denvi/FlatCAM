############################################################
# FlatCAM: 2D Post-processing for Manufacturing            #
# http://caram.cl/software/flatcam                         #
# Author: Juan Pablo Caram (c)                             #
# Date: 2/5/2014                                           #
# MIT Licence                                              #
############################################################

from PyQt4 import QtCore

import logging
from VisPyCanvas import VisPyCanvas
from VisPyVisuals import ShapeGroup, ShapeCollection
from vispy.scene.visuals import Markers, Text
import numpy as np
from vispy.geometry import Rect

log = logging.getLogger('base')


class PlotCanvas(QtCore.QObject):
    """
    Class handling the plotting area in the application.
    """

    def __init__(self, container, app):
        """
        The constructor configures the Matplotlib figure that
        will contain all plots, creates the base axes and connects
        events to the plotting area.

        :param container: The parent container in which to draw plots.
        :rtype: PlotCanvas
        """

        super(PlotCanvas, self).__init__()

        self.app = app

        # Options
        self.x_margin = 15  # pixels
        self.y_margin = 25  # Pixels

        # Parent container
        self.container = container

        # Attach to parent
        self.vispy_canvas = VisPyCanvas()
        self.vispy_canvas.create_native()
        self.vispy_canvas.native.setParent(self.app.ui)
        self.container.addWidget(self.vispy_canvas.native)

        self.shape_collection = self.new_shape_collection()
        self.shape_collection.parent = self.vispy_canvas.view.scene

    def vis_connect(self, event_name, callback):
        return getattr(self.vispy_canvas.events, event_name).connect(callback)

    def vis_disconnect(self, event_name, callback):
        getattr(self.vispy_canvas.events, event_name).disconnect(callback)

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

        self.vispy_canvas.view.camera.zoom(factor, center)

    def new_shape_group(self):
        return ShapeGroup(self.shape_collection)   # TODO: Make local shape collection

    def new_shape_collection(self):
        return ShapeCollection()

    def new_cursor(self):
        return Markers(pos=np.empty((0, 2)))

    def new_annotation(self):
        return Text(parent=self.vispy_canvas.view.scene)

    def fit_view(self, rect=None):
        if not rect:
            rect = Rect(0, 0, 10, 10)
            try:
                rect.left, rect.right = self.shape_collection.bounds(axis=0)
                rect.bottom, rect.top = self.shape_collection.bounds(axis=1)
            except TypeError:
                pass

        self.vispy_canvas.view.camera.rect = rect
        self.vispy_canvas.update()

    def clear(self):
        pass