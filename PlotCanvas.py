############################################################
# FlatCAM: 2D Post-processing for Manufacturing            #
# http://caram.cl/software/flatcam                         #
# Author: Juan Pablo Caram (c)                             #
# Date: 2/5/2014                                           #
# MIT Licence                                              #
############################################################

from PyQt4 import QtGui, QtCore

# Prevent conflict with Qt5 and above.
from matplotlib import use as mpl_use
mpl_use("Qt4Agg")

from matplotlib.figure import Figure
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_agg import FigureCanvasAgg
import FlatCAMApp
import logging
from VisPyCanvas import VisPyCanvas

log = logging.getLogger('base')


class CanvasCache(QtCore.QObject):
    """

    Case story #1:

    1) No objects in the project.
    2) Object is created (new_object() emits object_created(obj)).
       on_object_created() adds (i) object to collection and emits
       (ii) new_object_available() then calls (iii) object.plot()
    3) object.plot() creates axes if necessary on
       app.collection.figure. Then plots on it.
    4) Plots on a cache-size canvas (in background).
    5) Plot completes. Bitmap is generated.
    6) Visible canvas is painted.

    """

    # Signals:
    # A bitmap is ready to be displayed.
    new_screen = QtCore.pyqtSignal()

    def __init__(self, plotcanvas, app, dpi=50):

        super(CanvasCache, self).__init__()

        self.app = app

        self.plotcanvas = plotcanvas
        self.dpi = dpi

        self.figure = Figure(dpi=dpi)

        self.axes = self.figure.add_axes([0.0, 0.0, 1.0, 1.0], alpha=1.0)
        self.axes.set_frame_on(False)
        self.axes.set_xticks([])
        self.axes.set_yticks([])

        self.canvas = FigureCanvasAgg(self.figure)

        self.cache = None

    def run(self):

        log.debug("CanvasCache Thread Started!")

        self.plotcanvas.update_screen_request.connect(self.on_update_req)

        self.app.new_object_available.connect(self.on_new_object_available)

    def on_update_req(self, extents):
        """
        Event handler for an updated display request.

        :param extents: [xmin, xmax, ymin, ymax, zoom(optional)]
        """

        log.debug("Canvas update requested: %s" % str(extents))

        # Note: This information below might be out of date. Establish
        # a protocol regarding when to change the canvas in the main
        # thread and when to check these values here in the background,
        # or pass this data in the signal (safer).
        log.debug("Size: %s [px]" % str(self.plotcanvas.get_axes_pixelsize()))
        log.debug("Density: %s [units/px]" % str(self.plotcanvas.get_density()))

        # Move the requested screen portion to the main thread
        # and inform about the update:

        self.new_screen.emit()

        # Continue to update the cache.

    def on_new_object_available(self):

        log.debug("A new object is available. Should plot it!")


class PlotCanvas(QtCore.QObject):
    """
    Class handling the plotting area in the application.
    """

    # Signals:
    # Request for new bitmap to display. The parameter
    # is a list with [xmin, xmax, ymin, ymax, zoom(optional)]
    update_screen_request = QtCore.pyqtSignal(list)

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

        # Plots go onto a single matplotlib.figure
        self.figure = Figure(dpi=50)  # TODO: dpi needed?
        self.figure.patch.set_visible(False)

        # These axes show the ticks and grid. No plotting done here.
        # New axes must have a label, otherwise mpl returns an existing one.
        self.axes = self.figure.add_axes([0.05, 0.05, 0.9, 0.9], label="base", alpha=0.0)
        self.axes.set_aspect(1)
        self.axes.grid(True)

        # The canvas is the top level container (FigureCanvasQTAgg)
        self.canvas = FigureCanvas(self.figure)
        # self.canvas.setFocusPolicy(QtCore.Qt.ClickFocus)
        # self.canvas.setFocus()

        #self.canvas.set_hexpand(1)
        #self.canvas.set_vexpand(1)
        #self.canvas.set_can_focus(True)  # For key press

        # Attach to parent
        #self.container.attach(self.canvas, 0, 0, 600, 400)  # TODO: Height and width are num. columns??
        # self.container.addWidget(self.canvas)  # Qt
        conf = {'samples': 8}
        self.vispy_canvas = VisPyCanvas()
        self.vispy_canvas.create_native()
        self.vispy_canvas.native.setParent(self.app.ui)
        self.container.addWidget(self.vispy_canvas.native)

        # Copy a bitmap of the canvas for quick animation.
        # Update every time the canvas is re-drawn.
        self.background = self.canvas.copy_from_bbox(self.axes.bbox)

        ### Bitmap Cache
        self.cache = CanvasCache(self, self.app)
        self.cache_thread = QtCore.QThread()
        self.cache.moveToThread(self.cache_thread)
        super(PlotCanvas, self).connect(self.cache_thread, QtCore.SIGNAL("started()"), self.cache.run)
        # self.connect()
        self.cache_thread.start()
        self.cache.new_screen.connect(self.on_new_screen)

        # Events
        self.canvas.mpl_connect('button_press_event', self.on_mouse_press)
        self.canvas.mpl_connect('button_release_event', self.on_mouse_release)
        self.canvas.mpl_connect('motion_notify_event', self.on_mouse_move)
        #self.canvas.connect('configure-event', self.auto_adjust_axes)
        self.canvas.mpl_connect('resize_event', self.auto_adjust_axes)
        #self.canvas.add_events(Gdk.EventMask.SMOOTH_SCROLL_MASK)
        #self.canvas.connect("scroll-event", self.on_scroll)
        self.canvas.mpl_connect('scroll_event', self.on_scroll)
        self.canvas.mpl_connect('key_press_event', self.on_key_down)
        self.canvas.mpl_connect('key_release_event', self.on_key_up)
        self.canvas.mpl_connect('draw_event', self.on_draw)

        self.mouse = [0, 0]
        self.key = None

        self.pan_axes = []
        self.panning = False

    def on_new_screen(self):

        log.debug("Cache updated the screen!")

    def on_key_down(self, event):
        """

        :param event:
        :return:
        """
        FlatCAMApp.App.log.debug('on_key_down(): ' + str(event.key))
        self.key = event.key

    def on_key_up(self, event):
        """

        :param event:
        :return:
        """
        self.key = None

    def mpl_connect(self, event_name, callback):
        """
        Attach an event handler to the canvas through the Matplotlib interface.

        :param event_name: Name of the event
        :type event_name: str
        :param callback: Function to call
        :type callback: func
        :return: Connection id
        :rtype: int
        """
        return self.canvas.mpl_connect(event_name, callback)

    def mpl_disconnect(self, cid):
        """
        Disconnect callback with the give id.
        :param cid: Callback id.
        :return: None
        """
        self.canvas.mpl_disconnect(cid)

    def connect(self, event_name, callback):
        """
        Attach an event handler to the canvas through the native Qt interface.

        :param event_name: Name of the event
        :type event_name: str
        :param callback: Function to call
        :type callback: function
        :return: Nothing
        """
        self.canvas.connect(event_name, callback)

    def clear(self):
        """
        Clears axes and figure.

        :return: None
        """

        # Clear
        self.axes.cla()
        try:
            self.figure.clf()
        except KeyError:
            FlatCAMApp.App.log.warning("KeyError in MPL figure.clf()")

        # Re-build
        self.figure.add_axes(self.axes)
        self.axes.set_aspect(1)
        self.axes.grid(True)

        # Re-draw
        self.canvas.draw_idle()

    def adjust_axes(self, xmin, ymin, xmax, ymax):
        """
        Adjusts all axes while maintaining the use of the whole canvas
        and an aspect ratio to 1:1 between x and y axes. The parameters are an original
        request that will be modified to fit these restrictions.

        :param xmin: Requested minimum value for the X axis.
        :type xmin: float
        :param ymin: Requested minimum value for the Y axis.
        :type ymin: float
        :param xmax: Requested maximum value for the X axis.
        :type xmax: float
        :param ymax: Requested maximum value for the Y axis.
        :type ymax: float
        :return: None
        """

        # FlatCAMApp.App.log.debug("PC.adjust_axes()")

        width = xmax - xmin
        height = ymax - ymin
        try:
            r = width / height
        except ZeroDivisionError:
            FlatCAMApp.App.log.error("Height is %f" % height)
            return
        canvas_w, canvas_h = self.canvas.get_width_height()
        canvas_r = float(canvas_w) / canvas_h
        x_ratio = float(self.x_margin) / canvas_w
        y_ratio = float(self.y_margin) / canvas_h

        if r > canvas_r:
            ycenter = (ymin + ymax) / 2.0
            newheight = height * r / canvas_r
            ymin = ycenter - newheight / 2.0
            ymax = ycenter + newheight / 2.0
        else:
            xcenter = (xmax + xmin) / 2.0
            newwidth = width * canvas_r / r
            xmin = xcenter - newwidth / 2.0
            xmax = xcenter + newwidth / 2.0

        # Adjust axes
        for ax in self.figure.get_axes():
            if ax._label != 'base':
                ax.set_frame_on(False)  # No frame
                ax.set_xticks([])  # No tick
                ax.set_yticks([])  # No ticks
                ax.patch.set_visible(False)  # No background
                ax.set_aspect(1)
            ax.set_xlim((xmin, xmax))
            ax.set_ylim((ymin, ymax))
            ax.set_position([x_ratio, y_ratio, 1 - 2 * x_ratio, 1 - 2 * y_ratio])

        # Sync re-draw to proper paint on form resize
        self.canvas.draw()

        ##### Temporary place-holder for cached update #####
        self.update_screen_request.emit([0, 0, 0, 0, 0])

    def auto_adjust_axes(self, *args):
        """
        Calls ``adjust_axes()`` using the extents of the base axes.

        :rtype : None
        :return: None
        """

        xmin, xmax = self.axes.get_xlim()
        ymin, ymax = self.axes.get_ylim()
        self.adjust_axes(xmin, ymin, xmax, ymax)

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

        xmin, xmax = self.axes.get_xlim()
        ymin, ymax = self.axes.get_ylim()
        width = xmax - xmin
        height = ymax - ymin

        if center is None or center == [None, None]:
            center = [(xmin + xmax) / 2.0, (ymin + ymax) / 2.0]

        # For keeping the point at the pointer location
        relx = (xmax - center[0]) / width
        rely = (ymax - center[1]) / height

        new_width = width / factor
        new_height = height / factor

        xmin = center[0] - new_width * (1 - relx)
        xmax = center[0] + new_width * relx
        ymin = center[1] - new_height * (1 - rely)
        ymax = center[1] + new_height * rely

        # Adjust axes
        for ax in self.figure.get_axes():
            ax.set_xlim((xmin, xmax))
            ax.set_ylim((ymin, ymax))

        # Async re-draw
        self.canvas.draw_idle()

        ##### Temporary place-holder for cached update #####
        self.update_screen_request.emit([0, 0, 0, 0, 0])

    def pan(self, x, y):
        xmin, xmax = self.axes.get_xlim()
        ymin, ymax = self.axes.get_ylim()
        width = xmax - xmin
        height = ymax - ymin

        # Adjust axes
        for ax in self.figure.get_axes():
            ax.set_xlim((xmin + x * width, xmax + x * width))
            ax.set_ylim((ymin + y * height, ymax + y * height))

        # Re-draw
        self.canvas.draw_idle()

        ##### Temporary place-holder for cached update #####
        self.update_screen_request.emit([0, 0, 0, 0, 0])

    def new_axes(self, name):
        """
        Creates and returns an Axes object attached to this object's Figure.

        :param name: Unique label for the axes.
        :return: Axes attached to the figure.
        :rtype: Axes
        """

        return self.figure.add_axes([0.05, 0.05, 0.9, 0.9], label=name)

    def on_scroll(self, event):
        """
        Scroll event handler.

        :param event: Event object containing the event information.
        :return: None
        """

        # So it can receive key presses
        # self.canvas.grab_focus()
        self.canvas.setFocus()

        # Event info
        # z, direction = event.get_scroll_direction()

        if self.key is None:

            if event.button == 'up':
                self.zoom(1.5, self.mouse)
            else:
                self.zoom(1 / 1.5, self.mouse)
            return

        if self.key == 'shift':

            if event.button == 'up':
                self.pan(0.3, 0)
            else:
                self.pan(-0.3, 0)
            return

        if self.key == 'control':

            if event.button == 'up':
                self.pan(0, 0.3)
            else:
                self.pan(0, -0.3)
            return

    def on_mouse_press(self, event):

        # Check for middle mouse button press
        if event.button == 2:

            # Prepare axes for pan (using 'matplotlib' pan function)
            self.pan_axes = []
            for a in self.figure.get_axes():
                if (event.x is not None and event.y is not None and a.in_axes(event) and
                        a.get_navigate() and a.can_pan()):
                    a.start_pan(event.x, event.y, 1)
                    self.pan_axes.append(a)

            # Set pan view flag
            if len(self.pan_axes) > 0: self.panning = True;

    def on_mouse_release(self, event):

        # Check for middle mouse button release to complete pan procedure
        if event.button == 2:
            for a in self.pan_axes:
                a.end_pan()

            # Clear pan flag
            self.panning = False

    def on_mouse_move(self, event):
        """
        Mouse movement event hadler. Stores the coordinates. Updates view on pan.

        :param event: Contains information about the event.
        :return: None
        """
        self.mouse = [event.xdata, event.ydata]

        # Update pan view on mouse move
        if self.panning is True:
            for a in self.pan_axes:
                a.drag_pan(1, event.key, event.x, event.y)

            # Async re-draw (redraws only on thread idle state, uses timer on backend)
            self.canvas.draw_idle()

            ##### Temporary place-holder for cached update #####
            self.update_screen_request.emit([0, 0, 0, 0, 0])

    def on_draw(self, renderer):

        # Store background on canvas redraw
        self.background = self.canvas.copy_from_bbox(self.axes.bbox)

    def get_axes_pixelsize(self):
        """
        Axes size in pixels.

        :return: Pixel width and height
        :rtype: tuple
        """
        bbox = self.axes.get_window_extent().transformed(self.figure.dpi_scale_trans.inverted())
        width, height = bbox.width, bbox.height
        width *= self.figure.dpi
        height *= self.figure.dpi
        return width, height

    def get_density(self):
        """
        Returns unit length per pixel on horizontal
        and vertical axes.

        :return: X and Y density
        :rtype: tuple
        """
        xpx, ypx = self.get_axes_pixelsize()

        xmin, xmax = self.axes.get_xlim()
        ymin, ymax = self.axes.get_ylim()
        width = xmax - xmin
        height = ymax - ymin

        return width / xpx, height / ypx
