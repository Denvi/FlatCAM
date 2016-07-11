import numpy as np
from PyQt4.QtGui import QPalette
import vispy.scene as scene
from VisPyVisuals import LinesCollection, PolygonCollection, ShapeCollection


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

        # -------------------------- Tests ----------------------------------------

        data1 = np.empty((5, 2))
        data2 = np.empty((4, 2))

        data1[0] = 0, -0.0
        data1[1] = 1, -0.
        data1[2] = 1, 1
        data1[3] = 0, 1

        print "test", data1[:1]
        print "test", np.any(data1[0] != data1[-1])

        data2[0] = 2, -0.0
        data2[1] = 3, -0.
        data2[2] = 3, 1
        data2[3] = 2, 1

        # lines = LinesCollection(width=2)
        #
        # print "add1", lines.add(data1, color='blue')
        # print "add2", lines.add(data2, color='green')
        #
        # lines.remove(0)
        # # lines.remove(1)
        #
        # # view.add(lines)
        #
        # polys = PolygonCollection(border_width=2)
        # polys.add(data1, color='yellow', border_color='red')
        # polys.add(data2, color='green', border_color='blue')
        #
        # view.add(polys)

        # polys.remove(0)
        # polys.remove(1)

        # ----------------------- End of tests ----------------------------

        test = {'Poly': []}

        test['Poly'].append(3)
        test['Poly'].append(5)
        # test['Poly'] = np.append(test['Poly'], 1)
        # test['Poly'] = np.append(test['Poly'], 4)

        print "test", test

        self.primitives = {}
        self.primitives['Line'] = LinesCollection(parent=view.scene)
        self.primitives['Poly'] = PolygonCollection(parent=view.scene)

        self.shapes = ShapeCollection(parent=view.scene)

        grid1 = scene.GridLines(parent=view.scene, color='gray')
        grid1.set_gl_state(depth_test=False)

        xaxis.link_view(view)
        yaxis.link_view(view)

        self.view = view
        self.freeze()
