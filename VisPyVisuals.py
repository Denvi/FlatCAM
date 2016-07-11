from vispy.visuals import LineVisual, PolygonVisual
from vispy.scene.visuals import create_visual_node
from vispy.geometry import PolygonData
from vispy.gloo import set_state
from matplotlib.colors import ColorConverter
import numpy as np
import abc


class Collection:

    def __init__(self):
        self.data = {}
        self.last_key = -1
        self.colors = {}
        self.border_colors = {}

    def add(self, data, form=None, color=None, border_color=None, update=False):
        self.last_key += 1
        self.data[self.last_key] = self._translate_data(data, form)
        self.colors[self.last_key] = color
        self.border_colors[self.last_key] = border_color
        if update:
            self._update_data()

        return self.last_key

    def remove(self, key, update=False):
        del self.data[key]
        del self.colors[key]
        del self.border_colors[key]
        if update:
            self._update_data()

    def redraw(self):
        self._update_data()

    @abc.abstractmethod
    def _update_data(self):
        pass

    def _translate_data(self, data, form):
        return data


class LinesCollectionVisual(LineVisual, Collection):

    def __init__(self, width=1, method='gl', antialias=False):
        self.color_converter = ColorConverter()
        Collection.__init__(self)
        LineVisual.__init__(self, width=width, connect='segments', method=method, antialias=antialias)

    def _update_data(self):
        if len(self.data) > 0:
            # Merge arrays of segments, colors of segments
            pos_m = np.empty((0, 2))    # Line segments
            color_m = np.empty((0, 4))  # Colors of segments

            for key in self.data:
                if self.colors[key] is None:
                    continue
                pos = self.data[key]
                color = np.full((len(pos), 4), self.color_converter.to_rgba(self.colors[key]))
                pos_m = np.append(pos_m, pos, 0)
                color_m = np.append(color_m, color, 0)

            # Update lines
            if len(pos_m) > 0:
                LineVisual.set_data(self, pos_m, color=color_m)

        else:
            self._bounds = None
            self._pos = None
            self._changed['pos'] = True
            self.update()

    def _translate_data(self, data, form):
        if form == 'LineString':
            return linestring_to_segments(data)
        elif form == 'LinearRing':
            return linearring_to_segments(data)
        else:
            return data

    def set_data(self, pos=None, color=None, width=None, connect=None):
        pass


class PolygonCollectionVisual(PolygonVisual, Collection):

    def __init__(self, color='black', border_width=1, **kwargs):
        self.color_converter = ColorConverter()
        Collection.__init__(self)
        PolygonVisual.__init__(self, border_width=border_width, **kwargs)

    def _update_data(self):
        if len(self.data) > 0:
            # Merge arrays of vertices, faces, face colors
            pts_m = np.empty((0, 2))            # Vertices of triangles
            tris_m = np.empty((0, 3))           # Indexes of vertices of faces
            colors_m = np.empty((0, 4))         # Colors of faces

            for key in self.data:
                if self.colors[key] is None:
                    continue
                pos = self.data[key]
                data = PolygonData(vertices=np.array(pos, dtype=np.float32))

                pts, tris = data.triangulate()
                offset = np.full((1, 3), len(pts_m))
                tris = np.add(tris, offset)

                pts_m, tris_m = np.append(pts_m, pts, 0), np.append(tris_m, tris, 0)

                colors = np.full((len(tris), 4), self.color_converter.to_rgba(self.colors[key]))
                colors_m = np.append(colors_m, colors, 0)

            # Update mesh
            if len(pts_m) > 0:
                set_state(polygon_offset_fill=False)
                self._mesh.set_data(vertices=pts_m, faces=tris_m.astype(np.uint32),
                                    face_colors=colors_m)

            # Merge arrays of segments, colors of segments
            pos_m = np.empty((0, 2))            # Line segments of borders
            border_colors_m = np.empty((0, 4))  # Colors of segments

            for key in self.data:
                if self.border_colors[key] is None:
                    continue
                pos = self.data[key]
                pos = linearring_to_segments(pos)
                pos_m = np.append(pos_m, pos, 0)

                border_colors = np.full((len(pos), 4), self.color_converter.to_rgba(self.border_colors[key]))
                border_colors_m = np.append(border_colors_m, border_colors, 0)

            # Update borders
            if len(pos_m) > 0:
                self._border.set_data(pos=pos_m, color=border_colors_m, width=self._border_width,
                                      connect='segments')
                self._border.update()

        else:
            self._mesh.set_data()
            self._border._bounds = None
            self._border._pos = None
            self._border._changed['pos'] = True
            self._border.update()

    def _update(self):
        self._update_data()

    @property
    def pos(self):
        return None

    @pos.setter
    def pos(self, pos):
        pass

    @property
    def color(self):
        return None

    @color.setter
    def color(self, color):
        pass

    @property
    def border_color(self):
        return None

    @border_color.setter
    def border_color(self, border_color):
        pass


def linearring_to_segments(arr):

    # Close linear ring
    if np.any(arr[0] != arr[1]):
        arr = np.concatenate([arr, arr[:1]], axis=0)

    return linestring_to_segments(arr)


def linestring_to_segments(arr):
    lines = []
    for pnt in range(0, len(arr) - 1):
        lines.append(arr[pnt])
        lines.append(arr[pnt + 1])

    return np.array(lines)


LinesCollection = create_visual_node(LinesCollectionVisual)
PolygonCollection = create_visual_node(PolygonCollectionVisual)
