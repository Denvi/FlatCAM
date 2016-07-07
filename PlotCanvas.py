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

import FlatCAMApp
import numpy as np
import copy
from math import ceil, floor
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureOffscreenCanvas

class PlotCanvas(QtCore.QObject):
    """
    Class handling the plotting area in the application.
    """

    app = None
    updates_queue = 0

    def __init__(self, container):
        """
        The constructor configures the Matplotlib figure that
        will contain all plots, creates the base axes and connects
        events to the plotting area.

        :param container: The parent container in which to draw plots.
        :rtype: PlotCanvas
        """

        super(PlotCanvas, self).__init__()

        # Options
        self.x_margin = 15  # pixels
        self.y_margin = 25  # Pixels

        # Parent container
        self.container = container

        # Plots go onto a single matplotlib.figure
        self.figure = Figure(dpi=50)  # TODO: dpi needed?
        self.figure.patch.set_visible(False)

        # Offscreen figure
        self.offscreen_figure = Figure(dpi=50)
        self.offscreen_figure.patch.set_visible(False)

        # These axes show the ticks and grid. No plotting done here.
        # New axes must have a label, otherwise mpl returns an existing one.
        self.axes = self.figure.add_axes([0.05, 0.05, 0.9, 0.9], label="base", alpha=0.0)
        self.axes.set_aspect(1)
        self.axes.grid(True)

        # The canvas is the top level container (Gtk.DrawingArea)
        self.canvas = FigureCanvas(self.figure)
        # self.canvas.setFocusPolicy(QtCore.Qt.ClickFocus)
        # self.canvas.setFocus()

        # Image
        self.image = None

        #self.canvas.set_hexpand(1)
        #self.canvas.set_vexpand(1)
        #self.canvas.set_can_focus(True)  # For key press

        # Attach to parent
        #self.container.attach(self.canvas, 0, 0, 600, 400)  # TODO: Height and width are num. columns??
        self.container.addWidget(self.canvas)  # Qt

        # Copy a bitmap of the canvas for quick animation.
        # Update every time the canvas is re-drawn.
        self.background = self.canvas.copy_from_bbox(self.axes.bbox)

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

        # self.plots_updated.connect(self.on_plots_updated)

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
        Attach an event handler to the canvas through the native GTK interface.

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
            self.offscreen_figure.clf()
        except KeyError:
            FlatCAMApp.App.log.warning("KeyError in MPL figure.clf()")

        # Re-build
        self.figure.add_axes(self.axes)
        self.axes.set_aspect(1)
        self.axes.grid(True)

        # Prepare offscreen base axes
        ax = self.offscreen_figure.add_axes([0.0, 0.0, 1.0, 1.0], label='base')
        ax.set_frame_on(True)
        ax.patch.set_color("white")
        # Hide frame edge
        for spine in ax.spines:
            ax.spines[spine].set_visible(False)
        ax.set_aspect(1)

        # Re-draw
        self.canvas.draw()

    def auto_adjust_axes(self, *args):
        """
        Calls ``adjust_axes()`` using the extents of the base axes.

        :rtype : None
        :return: None
        """

        xmin, xmax = self.axes.get_xlim()
        ymin, ymax = self.axes.get_ylim()
        self.adjust_axes(xmin, ymin, xmax, ymax)

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
        self.update()

    def update(self):

        # Get bounds
        margin = 2
        x1, y1, x2, y2 = self.app.collection.get_bounds()
        x1, y1, x2, y2 = x1 - margin, y1 - margin, x2 + margin, y2 + margin

        # Calculate bounds in screen space
        points = self.axes.transData.transform([(x1, y1), (x2, y2)])

        # Round bounds to integers
        rounded_points = [(floor(points[0][0]), floor(points[0][1])), (ceil(points[1][0]), ceil(points[1][1]))]

        # Calculate width/height of image
        w, h = (rounded_points[1][0] - rounded_points[0][0]), (rounded_points[1][1] - rounded_points[0][1])

        # Get bounds back in axes units
        inverted_transform = self.axes.transData.inverted()
        bounds = inverted_transform.transform(rounded_points)

        # print "image bounds", x1, x2, y1, y2, points, rounded_points, bounds, w, h, self.axes.transData.transform(bounds)

        x1, x2, y1, y2 = bounds[0][0], bounds[1][0], bounds[0][1], bounds[1][1]

        # print "new image bounds", x1, x2, y1, y2

        pixel = inverted_transform.transform([(0, 0), (1, 1)])
        pixel_size = pixel[1][0] - pixel[0][0]

        # print "pixel size", pixel, pixel_size

        def update_image(figure):

            # Abort update if next update in queue
            if self.updates_queue > 1:
                self.updates_queue -= 1
                return

            # Rescale axes
            for ax in figure.get_axes():
                ax.set_xlim(x1 + pixel_size, x2 + pixel_size)
                ax.set_ylim(y1, y2)
                ax.set_xticks([])
                ax.set_yticks([])

            # Resize figure
            dpi = figure.dpi
            figure.set_size_inches(w / dpi, h / dpi)

            try:
                # Draw to buffer
                self.updates_queue -= 1
                offscreen_canvas = FigureOffscreenCanvas(figure)
                offscreen_canvas.draw()

                # Abort drawing if next update in queue
                if self.updates_queue > 0:
                    del offscreen_canvas
                    return

                buf = offscreen_canvas.buffer_rgba()
                ncols, nrows = offscreen_canvas.get_width_height()
                image = np.frombuffer(buf, dtype=np.uint8).reshape(nrows, ncols, 4)
                del offscreen_canvas

                # Updating canvas
                # Remove previous image if exists
                try:
                    self.image.remove()
                except:
                    pass

                # Set new image
                self.image = self.axes.imshow(image, extent=(x1, x2, y1, y2), interpolation="Nearest")
                del image

            except Exception as e:
                self.app.log.debug(e.message)

            finally:
                # Redraw window
                self.canvas.draw()

        # Do job in background
        proc = self.app.proc_container.new("Updating view")

        def job_thread(app_obj, figure):
            try:
                update_image(figure)
            except Exception as e:
                proc.done()
                raise e
            proc.done()

        # self.app.inform.emit("View update starting ...")
        self.updates_queue += 1
        self.app.worker_task.emit({'fcn': job_thread, 'params': [self.app, self.offscreen_figure]})

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
        # self.canvas.draw_idle()

        self.update()

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

    def new_axes(self, name):
        """
        Creates and returns an Axes object attached to this object's Figure.

        :param name: Unique label for the axes.
        :return: Axes attached to the figure.
        :rtype: Axes
        """

        ax = self.offscreen_figure.add_axes([0.0, 0.0, 1.0, 1.0], label=name)

        ax.set_frame_on(False)  # No frame
        ax.patch.set_visible(False)  # No background
        ax.set_aspect(1)

        return ax

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
            if len(self.pan_axes) > 0:
                self.panning = True;

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

    def on_draw(self, renderer):

        # Store background on canvas redraw
        self.background = self.canvas.copy_from_bbox(self.axes.bbox)
