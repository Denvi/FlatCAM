import numpy as np
from PyQt4.QtGui import QPalette
import vispy.scene as scene
from vispy.scene.cameras.base_camera import BaseCamera
import time


class VisPyCanvas(scene.SceneCanvas):

    def __init__(self, config=None):

        scene.SceneCanvas.__init__(self, keys=None, config=config)
        self.unfreeze()

        back_color = str(QPalette().color(QPalette.Window).name())

        self.central_widget.bgcolor = back_color
        self.central_widget.border_color = back_color

        grid = self.central_widget.add_grid(margin=10)
        grid.spacing = 0

        top_padding = grid.add_widget(row=0, col=0, col_span=2)
        top_padding.height_max = 24

        yaxis = scene.AxisWidget(orientation='left', axis_color='black', text_color='black', font_size=8)
        yaxis.width_max = 80
        grid.add_widget(yaxis, row=1, col=0)

        xaxis = scene.AxisWidget(orientation='bottom', axis_color='black', text_color='black', font_size=8)
        xaxis.height_max = 40
        grid.add_widget(xaxis, row=2, col=1)

        right_padding = grid.add_widget(row=0, col=2, row_span=2)
        right_padding.width_max = 24

        view = grid.add_view(row=1, col=1, border_color='black', bgcolor='white')
        view.camera = Camera(aspect=1)

        # Following function was removed from 'prepare_draw()' of 'Grid' class by patch,
        # it is necessary to call manually
        grid._update_child_widget_dim()

        grid1 = scene.GridLines(parent=view.scene, color='gray')
        grid1.set_gl_state(depth_test=False)

        xaxis.link_view(view)
        yaxis.link_view(view)

        self.grid = grid1
        self.view = view
        self.freeze()

        self.measure_fps()

    def translate_coords(self, pos):
        tr = self.grid.get_transform('canvas', 'visual')
        return tr.map(pos)


class Camera(scene.PanZoomCamera):

    def __init__(self, **kwargs):
        super(Camera, self).__init__(**kwargs)

        self.minimum_scene_size = 0.01
        self.maximum_scene_size = 10000

        self.last_event = None
        self.last_time = 0

    def zoom(self, factor, center=None):
        center = center if (center is not None) else self.center
        super(Camera, self).zoom(factor, center)

    def viewbox_mouse_event(self, event):
        """
        The SubScene received a mouse event; update transform
        accordingly.

        Parameters
        ----------
        event : instance of Event
            The event.
        """
        if event.handled or not self.interactive:
            return

        # Limit mouse move events
        last_event = event.last_event
        t = time.time()
        if t - self.last_time > 0.015:
            self.last_time = t
            if self.last_event:
                last_event = self.last_event
                self.last_event = None
        else:
            if not self.last_event:
                self.last_event = last_event
            event.handled = True
            return

        # Scrolling
        BaseCamera.viewbox_mouse_event(self, event)

        if event.type == 'mouse_wheel':
            center = self._scene_transform.imap(event.pos)
            scale = (1 + self.zoom_factor) ** (-event.delta[1] * 30)
            self.limited_zoom(scale, center)
            event.handled = True

        elif event.type == 'mouse_move':
            if event.press_event is None:
                return

            modifiers = event.mouse_event.modifiers

            if event.button in [2, 3] and not modifiers:
                # Translate
                p1 = np.array(last_event.pos)[:2]
                p2 = np.array(event.pos)[:2]
                p1s = self._transform.imap(p1)
                p2s = self._transform.imap(p2)
                self.pan(p1s-p2s)
                event.handled = True
            elif event.button in [2, 3] and 'Shift' in modifiers:
                # Zoom
                p1c = np.array(last_event.pos)[:2]
                p2c = np.array(event.pos)[:2]
                scale = ((1 + self.zoom_factor) **
                         ((p1c-p2c) * np.array([1, -1])))
                center = self._transform.imap(event.press_event.pos[:2])
                self.limited_zoom(scale, center)
                event.handled = True
            else:
                event.handled = False
        elif event.type == 'mouse_press':
            # accept the event if it is button 1 or 2.
            # This is required in order to receive future events
            event.handled = event.button in [1, 2, 3]
        else:
            event.handled = False

    def limited_zoom(self, scale, center):

        try:
            zoom_in = scale[1] < 1
        except IndexError:
            zoom_in = scale < 1

        if (not zoom_in and self.rect.width < self.maximum_scene_size) \
                or (zoom_in and self.rect.width > self.minimum_scene_size):
            self.zoom(scale, center)
