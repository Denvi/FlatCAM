import sys
from PyQt4 import QtGui, QtCore
from FlatCAMApp import App
from multiprocessing import freeze_support
from vispy.visuals import markers, LineVisual, InfiniteLineVisual
import vispy.app
from vispy.scene.widgets import Grid
import OpenGL.platform.win32

def debug_trace():
    """
    Set a tracepoint in the Python debugger that works with Qt
    :return: None
    """
    from PyQt4.QtCore import pyqtRemoveInputHook
    #from pdb import set_trace
    pyqtRemoveInputHook()
    #set_trace()

# All X11 calling should be thread safe otherwise we have strange issues
# QtCore.QCoreApplication.setAttribute(QtCore.Qt.AA_X11InitThreads)
# NOTE: Never talk to the GUI from threads! This is why I commented the above.


def apply_patches():
    # Patch MarkersVisual
    cross_lines = """
    float cross(vec2 pointcoord, float size)
    {
        //vbar
        float r1 = abs(pointcoord.x - 0.5)*size;
        float r2 = abs(pointcoord.y - 0.5)*size - $v_size/2;
        float vbar = max(r1,r2);
        //hbar
        float r3 = abs(pointcoord.y - 0.5)*size;
        float r4 = abs(pointcoord.x - 0.5)*size - $v_size/2;
        float hbar = max(r3,r4);
        return min(vbar, hbar);
    }
    """

    markers._marker_dict['++'] = cross_lines
    markers.marker_types = tuple(sorted(list(markers._marker_dict.keys())))

    # Add clear_data method to LineVisual
    def clear_data(self):
        self._bounds = None
        self._pos = None
        self._changed['pos'] = True
        self.update()

    LineVisual.clear_data = clear_data

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

    # Patch InfiniteLine visual
    def _prepare_draw(self, view=None):
        """This method is called immediately before each draw.
        The *view* argument indicates which view is about to be drawn.
        """
        GL = None
        from vispy.app._default_app import default_app

        if default_app is not None and \
                default_app.backend_name != 'ipynb_webgl':
            try:
                import OpenGL.GL as GL
            except Exception:  # can be other than ImportError sometimes
                pass

        if GL:
            GL.glDisable(GL.GL_LINE_SMOOTH)
            GL.glLineWidth(1.0)

        if self._changed['pos']:
            self.pos_buf.set_data(self._pos)
            self._changed['pos'] = False

        if self._changed['color']:
            self._program.vert['color'] = self._color
            self._changed['color'] = False

    InfiniteLineVisual._prepare_draw = _prepare_draw


if __name__ == '__main__':
    freeze_support()

    debug_trace()
    apply_patches()

    app = QtGui.QApplication(sys.argv)
    fc = App()
    sys.exit(app.exec_())

