import numpy as np
from PyQt4.QtGui import QPalette
import vispy.scene as scene
from vispy.scene.widgets import Grid
from vispy.scene.cameras.base_camera import BaseCamera


# Patch VisPy Grid to prevent updating layout on PaintGL
def _prepare_draw(self, view):
    pass

def _update_clipper(self):
    super(Grid, self)._update_clipper()
    try:
        self._update_child_widget_dim()
    except Exception as e:
        print e

Grid._prepare_draw = _prepare_draw
Grid._update_clipper = _update_clipper


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

        yaxis = scene.AxisWidget(orientation='left', axis_color='black', text_color='black', font_size=12)
        yaxis.width_max = 50
        grid.add_widget(yaxis, row=1, col=0)

        xaxis = scene.AxisWidget(orientation='bottom', axis_color='black', text_color='black', font_size=12)
        xaxis.height_max = 40
        grid.add_widget(xaxis, row=2, col=1)

        right_padding = grid.add_widget(row=0, col=2, row_span=2)
        right_padding.width_max = 24

        view = grid.add_view(row=1, col=1, border_color='black', bgcolor='white')
        view.camera = Camera(aspect=1)

        grid1 = scene.GridLines(parent=view.scene, color='gray')
        grid1.set_gl_state(depth_test=False)

        xaxis.link_view(view)
        yaxis.link_view(view)

        # shapes = scene.Line(parent=view.scene)
        # view.add(shapes)

        self.grid = grid1
        self.view = view
        self.freeze()

        self.measure_fps()

    def translate_coords(self, pos):
        tr = self.grid.get_transform('canvas', 'visual')
        return tr.map(pos)


class Camera(scene.PanZoomCamera):
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

        # Scrolling
        BaseCamera.viewbox_mouse_event(self, event)

        if event.type == 'mouse_wheel':
            center = self._scene_transform.imap(event.pos)
            self.zoom((1 + self.zoom_factor) ** (-event.delta[1] * 30), center)
            event.handled = True

        elif event.type == 'mouse_move':
            if event.press_event is None:
                return

            modifiers = event.mouse_event.modifiers
            p1 = event.mouse_event.press_event.pos
            p2 = event.mouse_event.pos

            if event.button in [2, 3] and not modifiers:
                # Translate
                p1 = np.array(event.last_event.pos)[:2]
                p2 = np.array(event.pos)[:2]
                p1s = self._transform.imap(p1)
                p2s = self._transform.imap(p2)
                self.pan(p1s-p2s)
                event.handled = True
            elif event.button in [2, 3] and 'Shift' in modifiers:
                # Zoom
                p1c = np.array(event.last_event.pos)[:2]
                p2c = np.array(event.pos)[:2]
                scale = ((1 + self.zoom_factor) **
                         ((p1c-p2c) * np.array([1, -1])))
                center = self._transform.imap(event.press_event.pos[:2])
                self.zoom(scale, center)
                event.handled = True
            else:
                event.handled = False
        elif event.type == 'mouse_press':
            # accept the event if it is button 1 or 2.
            # This is required in order to receive future events
            event.handled = event.button in [1, 2, 3]
        else:
            event.handled = False