from vispy.visuals import LineVisual, PolygonVisual, CompoundVisual, MeshVisual
from vispy.scene.visuals import create_visual_node
from vispy.geometry import PolygonData
from vispy.gloo import set_state
from vispy.geometry.triangulation import Triangulation
from matplotlib.colors import ColorConverter
from shapely.geometry import Polygon, LineString, LinearRing
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


class ShapeCollectionVisual(CompoundVisual):
    def __init__(self, line_width=1, **kwargs):
        self.shapes = {}
        self.colors = {}
        self.face_colors = {}
        self.last_key = -1

        self._mesh = MeshVisual()
        self._lines = LineVisual()
        self._line_width = line_width

        CompoundVisual.__init__(self, [self._mesh, self._lines], **kwargs)
        self._mesh.set_gl_state(polygon_offset_fill=True, polygon_offset=(1, 1), cull_face=False)
        self.freeze()

    def add(self, shape, color=None, face_color=None, redraw=False):
        self.last_key += 1
        self.shapes[self.last_key] = shape
        self.colors[self.last_key] = color
        self.face_colors[self.last_key] = face_color
        if redraw:
            self._update()
        return self.last_key

    def remove(self, key, redraw=False):
        del self.shapes[key]
        del self.colors[key]
        del self.face_colors[key]
        if redraw:
            self._update()

    def _update(self):

        pts_m = np.empty((0, 2))  # Vertices of triangles
        tris_m = np.empty((0, 3))  # Indexes of vertices of faces

        for shape in self.shapes.values():
            if type(shape) == LineString:
                pass
            elif type(shape) == LinearRing:
                pass
            elif type(shape) == Polygon:
                simple = shape.simplify(0.01)
                verts_m = self._open_ring(np.array(simple.exterior))
                edges_m = self._generate_edges(len(verts_m))

                for ints in simple.interiors:
                    verts = self._open_ring(np.array(ints))
                    edges_m = np.append(edges_m, self._generate_edges(len(verts)) + len(verts_m), 0)
                    verts_m = np.append(verts_m, verts, 0)

                tri = Triangulation(verts_m, edges_m)
                tri.triangulate()

                tris_m = np.append(tris_m, tri.tris + len(pts_m), 0)
                pts_m = np.append(pts_m, tri.pts, 0)

        if len(pts_m) > 0:
            self._mesh.set_data(pts_m, tris_m.astype(np.uint32), color='red')

    def _open_ring(self, vertices):
        return vertices[:-1] if not np.any(vertices[0] != vertices[-1]) else vertices

    def _generate_edges(self, count):
        edges = np.empty((count, 2), dtype=np.uint32)
        edges[:, 0] = np.arange(count)
        edges[:, 1] = edges[:, 0] + 1
        edges[-1, 1] = 0
        return edges

    def redraw(self):
        self._update()


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
    if np.any(arr[0] != arr[-1]):
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
ShapeCollection = create_visual_node(ShapeCollectionVisual)
