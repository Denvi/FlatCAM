from vispy.visuals import CompoundVisual, LineVisual, MeshVisual
from vispy.scene.visuals import create_visual_node
from vispy.gloo import set_state
from vispy.geometry.triangulation import Triangulation
from vispy.color import Color
from shapely.geometry import Polygon, LineString, LinearRing
import numpy as np


class ShapeCollectionVisual(CompoundVisual):
    def __init__(self, line_width=1, **kwargs):
        self.data = {}
        self.last_key = -1

        self._mesh = MeshVisual()
        self._line = LineVisual()
        self._line_width = line_width

        CompoundVisual.__init__(self, [self._mesh, self._line], **kwargs)
        self._mesh.set_gl_state(polygon_offset_fill=True, polygon_offset=(1, 1), cull_face=False)
        self.freeze()

    def add(self, shape, color=None, face_color=None, update=False):
        self.last_key += 1
        self.data[self.last_key] = shape, color, face_color
        if update:
            self._update()
        return self.last_key

    def remove(self, key, update=False):
        del self.data[key]
        if update:
            self._update()

    def clear(self, update=False):
        self.data = {}
        if update:
            self._update()

    def _update(self):
        mesh_vertices = np.empty((0, 2))    # Vertices for mesh
        mesh_tris = np.empty((0, 3))        # Faces for mesh
        mesh_colors = np.empty((0, 4))      # Face colors

        line_pts = np.empty((0, 2))         # Vertices for line
        line_colors = np.empty((0, 4))      # Line color

        # Creating arrays for mesh and line from all shapes
        for shape, color, face_color in self.data.values():

            simple = shape.simplify(0.01)   # Simplified shape
            pts = np.empty((0, 2))          # Shape line points
            tri_pts = np.empty((0, 2))      # Mesh vertices
            tri_tris = np.empty((0, 3))     # Mesh faces

            if type(shape) == LineString:
                # Prepare lines
                pts = self._linestring_to_segments(np.array(simple))

            elif type(shape) == LinearRing:
                # Prepare lines
                pts = self._linearring_to_segments(np.array(simple))

            elif type(shape) == Polygon:
                # Prepare polygon faces
                if face_color is not None:
                    # Concatenated arrays of external & internal line rings
                    vertices = self._open_ring(np.array(simple.exterior))
                    edges = self._generate_edges(len(vertices))

                    for ints in simple.interiors:
                        v = self._open_ring(np.array(ints))
                        edges = np.append(edges, self._generate_edges(len(v)) + len(vertices), 0)
                        vertices = np.append(vertices, v, 0)

                    tri = Triangulation(vertices, edges)
                    tri.triangulate()
                    tri_pts, tri_tris = tri.pts, tri.tris

                # Prepare polygon edges
                if color is not None:
                    pts = self._linearring_to_segments(np.array(simple.exterior))
                    for ints in simple.interiors:
                        pts = np.append(pts, self._linearring_to_segments(np.array(ints)), 0)

            # Appending data for mesh
            if len(tri_pts) > 0 and len(tri_tris) > 0:
                mesh_tris = np.append(mesh_tris, tri_tris + len(mesh_vertices), 0)
                mesh_vertices = np.append(mesh_vertices, tri_pts, 0)
                mesh_colors = np.append(mesh_colors, np.full((len(tri_tris), 4), Color(face_color).rgba), 0)

            # Appending data for line
            if len(pts) > 0:
                line_pts = np.append(line_pts, pts, 0)
                line_colors = np.append(line_colors, np.full((len(pts), 4), Color(color).rgba), 0)

        # Updating mesh
        if len(mesh_vertices) > 0:
            set_state(polygon_offset_fill=False)
            self._mesh.set_data(mesh_vertices, mesh_tris.astype(np.uint32), face_colors=mesh_colors)
        else:
            self._mesh.set_data()

        # Updating line
        if len(line_pts) > 0:
            self._line.set_data(line_pts, line_colors, self._line_width, 'segments')
        else:
            self._line._bounds = None
            self._line._pos = None
            self._line._changed['pos'] = True
            self._line.update()

    def _open_ring(self, vertices):
        return vertices[:-1] if not np.any(vertices[0] != vertices[-1]) else vertices

    def _generate_edges(self, count):
        edges = np.empty((count, 2), dtype=np.uint32)
        edges[:, 0] = np.arange(count)
        edges[:, 1] = edges[:, 0] + 1
        edges[-1, 1] = 0
        return edges

    def _linearring_to_segments(self, arr):

        # Close linear ring
        if np.any(arr[0] != arr[-1]):
            arr = np.concatenate([arr, arr[:1]], axis=0)

        return self._linestring_to_segments(arr)

    def _linestring_to_segments(self, arr):
        lines = []
        for pnt in range(0, len(arr) - 1):
            lines.append(arr[pnt])
            lines.append(arr[pnt + 1])

        return np.array(lines)

    def redraw(self):
        self._update()


ShapeCollection = create_visual_node(ShapeCollectionVisual)
