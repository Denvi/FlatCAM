import numpy as np
from PyQt4.QtGui import QPalette
import vispy.scene as scene
from vispy.geometry import Rect


class VisPyCanvas(scene.SceneCanvas):

    def __init__(self):
        scene.SceneCanvas.__init__(self, keys=None)
        self.unfreeze()

        back_color = str(QPalette().color(QPalette.Window).name())

        self.central_widget.bgcolor = back_color
        self.central_widget.border_color = back_color

        grid = self.central_widget.add_grid(margin=10)
        grid.spacing = 0

        top_padding = grid.add_widget(row=0, col=0, col_span=2)
        top_padding.height_max = 24

        yaxis = scene.AxisWidget(orientation='left', axis_color='black', text_color='black', font_size=12)
        yaxis.width_max = 60
        grid.add_widget(yaxis, row=1, col=0)

        xaxis = scene.AxisWidget(orientation='bottom', axis_color='black', text_color='black', font_size=12)
        xaxis.height_max = 40
        grid.add_widget(xaxis, row=2, col=1)

        right_padding = grid.add_widget(row=0, col=2, row_span=2)
        right_padding.width_max = 24

        view = grid.add_view(row=1, col=1, border_color='black', bgcolor='white')
        view.camera = scene.PanZoomCamera(aspect=1)

        grid1 = scene.GridLines(parent=view.scene, color='gray')
        grid1.set_gl_state(depth_test=False)

        xaxis.link_view(view)
        yaxis.link_view(view)

        # self.shapes = ShapeCollection(parent=view.scene)
        self.view = view
        self.freeze()

    def fit_view(self):
        rect = Rect()
        rect.left, rect.right = self.view.get_scene_bounds(dim=0)
        rect.bottom, rect.top = self.view.get_scene_bounds(dim=1)
        self.view.camera.rect = rect
