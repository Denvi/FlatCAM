from vispy.visuals import CompoundVisual, LineVisual, MeshVisual
from vispy.scene.visuals import create_visual_node
from vispy.gloo import set_state
from vispy.geometry.triangulation import Triangulation
from vispy.color import Color
from shapely.geometry import Polygon, LineString, LinearRing
import numpy as np

try:
    from shapely.ops import triangulate
    import Polygon as gpc
except:
    pass

class ShapeCollectionVisual(CompoundVisual):

    total_segments = 0
    total_tris = 0

    def __init__(self, line_width=1, triangulation='gpc', **kwargs):
        self.data = {}
        self.last_key = -1

        self._mesh = MeshVisual()
        self._line = LineVisual(antialias=True)
        self._line_width = line_width
        self._triangulation = triangulation

        CompoundVisual.__init__(self, [self._mesh, self._line], **kwargs)
        self._mesh.set_gl_state(polygon_offset_fill=True, polygon_offset=(1, 1), cull_face=False)
        self._line.set_gl_state(blend=True)
        self.freeze()

    def __del__(self):
        print "ShapeCollection destructed"

    def add(self, shape, color=None, face_color=None, update=False):
        """Adds geometry object to collection

        Args:
            shape: shapely.geometry
                Shapely geometry object
            color: tuple
                Line (polygon edge) color
            face_color: tuple
                Polygon fill color
            update: bool
                Set to redraw collection

        Returns: int

        """
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
            if shape is None or shape.is_empty:
                continue

            simple = shape.simplify(0.01)   # Simplified shape
            pts = np.empty((0, 2))          # Shape line points
            tri_pts = np.empty((0, 2))      # Mesh vertices
            tri_tris = np.empty((0, 3))     # Mesh faces

            if type(shape) == LineString:
                # Prepare lines
                pts = self._linestring_to_segments(np.asarray(simple))

            elif type(shape) == LinearRing:
                # Prepare lines
                pts = self._linearring_to_segments(np.asarray(simple))

            elif type(shape) == Polygon:
                # Prepare polygon faces
                if face_color is not None:

                    if self._triangulation == 'vispy':
                        # VisPy triangulation
                        # Concatenated arrays of external & internal line rings
                        vertices = self._open_ring(np.array(simple.exterior))
                        edges = self._generate_edges(len(vertices))

                        print "poly exterior pts:", len(vertices)

                        for ints in simple.interiors:
                            v = self._open_ring(np.array(ints))
                            edges = np.append(edges, self._generate_edges(len(v)) + len(vertices), 0)
                            vertices = np.append(vertices, v, 0)

                            print "poly interior pts:", len(v)

                        tri = Triangulation(vertices, edges)
                        tri.triangulate()
                        tri_pts, tri_tris = tri.pts, tri.tris
                    elif self._triangulation == 'gpc':

                        # GPC triangulation
                        p = gpc.Polygon(np.asarray(simple.exterior))

                        for ints in simple.interiors:
                            q = gpc.Polygon(np.asarray(ints))
                            p -= q

                        tri_pts = np.empty((0, 2))
                        tri_tris = np.empty((0, 3))

                        for strip in p.triStrip():
                            # Generate tris indexes for triangle strips
                            a = np.repeat(np.arange(0, len(strip) - 2), 3).reshape((-1, 3))
                            a[:, 1] += 1
                            a[:, 2] += 2

                            # Append vertices & tris
                            tri_tris = np.append(tri_tris, a + len(tri_pts), 0)
                            tri_pts = np.append(tri_pts, np.asarray(strip), 0)

                    # Shapely triangulation
                    # tri_pts = np.array(map(lambda x: np.array(x.exterior)[:-1], triangulate(shape))).reshape(-1, 2)
                    # tri_tris = np.arange(0, len(tri_pts), dtype=np.uint32).reshape((-1, 3))

                # Prepare polygon edges
                if color is not None:
                    pts = self._linearring_to_segments(np.asarray(simple.exterior))
                    for ints in simple.interiors:
                        pts = np.append(pts, self._linearring_to_segments(np.asarray(ints)), 0)

            # Appending data for mesh
            if len(tri_pts) > 0 and len(tri_tris) > 0:
                mesh_tris = np.append(mesh_tris, tri_tris + len(mesh_vertices), 0)
                mesh_vertices = np.append(mesh_vertices, tri_pts, 0)
                mesh_colors = np.append(mesh_colors, np.full((len(tri_tris), 4), Color(face_color).rgba), 0)

                # Random face colors
                # rc = np.random.rand(len(tri_tris), 4)
                # rc[:, 3] = 1.0
                # mesh_colors = np.append(mesh_colors, rc, 0)

            # Appending data for line
            if len(pts) > 0:
                line_pts = np.append(line_pts, pts, 0)
                line_colors = np.append(line_colors, np.full((len(pts), 4), Color(color).rgba), 0)

        # Updating mesh
        if len(mesh_vertices) > 0:
            set_state(polygon_offset_fill=False)
            self._mesh.set_data(mesh_vertices, mesh_tris.astype(np.uint32), face_colors=mesh_colors)

            self.total_tris += len(mesh_tris)

        else:
            self._mesh.set_data()

        # Updating line
        if len(line_pts) > 0:
            set_state(blend=True, blend_func=('src_alpha', 'one_minus_src_alpha'))
            self._line.set_data(line_pts, line_colors, self._line_width, 'segments')

            self.total_segments += len(line_pts) / 2

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
        return np.asarray(np.repeat(arr, 2, axis=0)[1:-1])

    def _compute_bounds(self, axis, view):
        return self._line._compute_bounds(axis, view)

    def redraw(self):
        self._update()
        print "total:", self.total_segments, self.total_tris


ShapeCollection = create_visual_node(ShapeCollectionVisual)
