from vispy.visuals import markers, LineVisual, InfiniteLineVisual
from vispy.visuals.axis import Ticker, _get_ticks_talbot
from vispy.scene.widgets import Grid
import numpy as np


def apply_patches():
    # Patch MarkersVisual to have crossed lines marker
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

    # Add clear_data method to LineVisual to have possibility of clearing data
    def clear_data(self):
        self._bounds = None
        self._pos = None
        self._changed['pos'] = True
        self.update()

    LineVisual.clear_data = clear_data

    # Patch VisPy Grid to prevent updating layout on PaintGL, which cause low fps
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

    # Patch InfiniteLine visual to 1px width
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

    # Patch AxisVisual to have less axis labels
    def _get_tick_frac_labels(self):
        """Get the major ticks, minor ticks, and major labels"""
        minor_num = 4  # number of minor ticks per major division
        if (self.axis.scale_type == 'linear'):
            domain = self.axis.domain
            if domain[1] < domain[0]:
                flip = True
                domain = domain[::-1]
            else:
                flip = False
            offset = domain[0]
            scale = domain[1] - domain[0]

            transforms = self.axis.transforms
            length = self.axis.pos[1] - self.axis.pos[0]  # in logical coords
            n_inches = np.sqrt(np.sum(length ** 2)) / transforms.dpi

            # major = np.linspace(domain[0], domain[1], num=11)
            # major = MaxNLocator(10).tick_values(*domain)
            major = _get_ticks_talbot(domain[0], domain[1], n_inches, 1)

            labels = ['%g' % x for x in major]
            majstep = major[1] - major[0]
            minor = []
            minstep = majstep / (minor_num + 1)
            minstart = 0 if self.axis._stop_at_major[0] else -1
            minstop = -1 if self.axis._stop_at_major[1] else 0
            for i in range(minstart, len(major) + minstop):
                maj = major[0] + i * majstep
                minor.extend(np.linspace(maj + minstep,
                                         maj + majstep - minstep,
                                         minor_num))
            major_frac = (major - offset) / scale
            minor_frac = (np.array(minor) - offset) / scale
            major_frac = major_frac[::-1] if flip else major_frac
            use_mask = (major_frac > -0.0001) & (major_frac < 1.0001)
            major_frac = major_frac[use_mask]
            labels = [l for li, l in enumerate(labels) if use_mask[li]]
            minor_frac = minor_frac[(minor_frac > -0.0001) &
                                    (minor_frac < 1.0001)]
        elif self.axis.scale_type == 'logarithmic':
            return NotImplementedError
        elif self.axis.scale_type == 'power':
            return NotImplementedError
        return major_frac, minor_frac, labels

    Ticker._get_tick_frac_labels = _get_tick_frac_labels