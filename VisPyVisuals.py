from vispy.visuals import CompoundVisual, LineVisual, MeshVisual
from vispy.scene.visuals import create_visual_node
from vispy.gloo import set_state
from vispy.geometry.triangulation import Triangulation
from vispy.color import Color
from shapely.geometry import Polygon, LineString, LinearRing
import numpy as np
import time

try:
    from shapely.ops import triangulate
    import Polygon as gpc
except:
    pass


class ShapeGroup(object):
    def __init__(self, collection):
        self._collection = collection
        self._indexes = []
        self._visible = True

    def add(self, shape, color=None, face_color=None, visible=True, update=False):
        self._indexes.append(self._collection.add(shape, color, face_color, visible, update))

    def clear(self, update=False):
        for i in self._indexes:
            self._collection.remove(i, False)

        del self._indexes[:]

        if update:
            self._collection.redraw()

    def redraw(self):
        self._collection.redraw()

    @property
    def visible(self):
        return self._visible

    @visible.setter
    def visible(self, value):
        self._visible = value
        for i in self._indexes:
            self._collection.data[i]['visible'] = value

        self._collection.redraw()


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

    def add(self, shape, color=None, face_color=None, visible=True, update=False):
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

        self.data[self.last_key] = {'geometry': shape, 'color': color, 'face_color': face_color, 'visible': visible}
        self.update_shape_buffers(self.last_key)

        if update:
            self._update()

        return self.last_key

    def update_shape_buffers(self, key):
        mesh_vertices = []                      # Vertices for mesh
        mesh_tris = []                          # Faces for mesh
        mesh_colors = []                        # Face colors
        line_pts = []                           # Vertices for line
        line_colors = []                        # Line color

        geo, color, face_color = self.data[key]['geometry'], self.data[key]['color'], self.data[key]['face_color']

        if geo is not None and not geo.is_empty:
            simple = geo.simplify(0.01)         # Simplified shape
            pts = []                            # Shape line points
            tri_pts = []                        # Mesh vertices
            tri_tris = []                       # Mesh faces

            if type(geo) == LineString:
                # Prepare lines
                pts = self._linestring_to_segments(np.asarray(simple)).tolist()

            elif type(geo) == LinearRing:
                # Prepare lines
                pts = self._linearring_to_segments(np.asarray(simple)).tolist()

            elif type(geo) == Polygon:
                # Prepare polygon faces
                if face_color is not None:

                    if self._triangulation == 'vispy':
                        # VisPy triangulation
                        # Concatenated arrays of external & internal line rings
                        vertices = self._open_ring(np.asarray(simple.exterior))
                        edges = self._generate_edges(len(vertices))

                        for ints in simple.interiors:
                            v = self._open_ring(np.asarray(ints))
                            edges = np.append(edges, self._generate_edges(len(v)) + len(vertices), 0)
                            vertices = np.append(vertices, v, 0)

                        tri = Triangulation(vertices, edges)
                        tri.triangulate()
                        tri_pts, tri_tris = tri.pts.tolist(), tri.tris.tolist()

                    elif self._triangulation == 'gpc':

                        # GPC triangulation
                        p = gpc.Polygon(np.asarray(simple.exterior))

                        for ints in simple.interiors:
                            q = gpc.Polygon(np.asarray(ints))
                            p -= q

                        for strip in p.triStrip():
                            # Generate tris indexes for triangle strips
                            a = [[x + y for x in range(0, 3)] for y in range(0, len(strip) - 2)]

                            # Append vertices & tris
                            tri_tris += [[x + len(tri_pts) for x in y] for y in a]
                            tri_pts += strip

                # Prepare polygon edges
                if color is not None:
                    pts = self._linearring_to_segments(np.asarray(simple.exterior)).tolist()
                    for ints in simple.interiors:
                        pts += self._linearring_to_segments(np.asarray(ints)).tolist()

            # Appending data for mesh
            if len(tri_pts) > 0 and len(tri_tris) > 0:
                mesh_tris += tri_tris
                mesh_vertices += tri_pts
                mesh_colors += [Color(face_color).rgba] * len(tri_tris)

            # Appending data for line
            if len(pts) > 0:
                line_pts += pts
                line_colors += [Color(color).rgba] * len(pts)

        # Store buffers
        self.data[key]['line_pts'] = line_pts
        self.data[key]['line_colors'] = line_colors
        self.data[key]['mesh_vertices'] = mesh_vertices
        self.data[key]['mesh_tris'] = mesh_tris
        self.data[key]['mesh_colors'] = mesh_colors

    def remove(self, key, update=False):
        self.data.pop(key)
        if update:
            self._update()

    def clear(self, update=False):
        self.data.clear()
        if update:
            self._update()

    def _update(self):

        mesh_vertices = []                  # Vertices for mesh
        mesh_tris = []                      # Faces for mesh
        mesh_colors = []                    # Face colors
        line_pts = []                       # Vertices for line
        line_colors = []                    # Line color

        # Merge shapes buffers
        for data in self.data.values():
            if data['visible']:
                try:
                    line_pts += data['line_pts']
                    line_colors += data['line_colors']
                    mesh_tris += [[x + len(mesh_vertices) for x in y] for y in data['mesh_tris']]
                    mesh_vertices += data['mesh_vertices']
                    mesh_colors += data['mesh_colors']
                except Exception as e:
                    print "Data error", e

        # Updating mesh
        if len(mesh_vertices) > 0:
            set_state(polygon_offset_fill=False)
            print "set mesh data", len(mesh_vertices)
            self._mesh.set_data(np.asarray(mesh_vertices), np.asarray(mesh_tris, dtype=np.uint32),
                                face_colors=np.asarray(mesh_colors))

            self.total_tris += len(mesh_tris)

        else:
            self._mesh.set_data()

        # Updating line
        if len(line_pts) > 0:
            self._line.set_data(np.asarray(line_pts), np.asarray(line_colors), self._line_width, 'segments')
        else:
            self._line._bounds = None
            self._line._pos = None
            self._line._changed['pos'] = True
            self._line.update()

        # self._line._bounds_changed()
        self._mesh._bounds_changed()
        self._bounds_changed()

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

    def redraw(self):
        self._update()


ShapeCollection = create_visual_node(ShapeCollectionVisual)
