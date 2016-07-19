from OpenGL import GLU


class GLUTess:
    def __init__(self):
        """
        OpenGL GLU triangulation class
        """
        self.tris = []
        self.pts = []
        self.vertex_index = 0

    def _on_begin_primitive(self, type):
        pass

    def _on_new_vertex(self, vertex):
        self.tris.append(vertex)

    # Force GLU to return separate triangles (GLU_TRIANGLES)
    def _on_edge_flag(self, flag):
        pass

    def _on_combine(self, coords, data, weight):
        return (coords[0], coords[1], coords[2])

    def _on_error(self, errno):
        print "GLUTess error:", errno

    def _on_end_primitive(self):
        pass

    def triangulate(self, polygon):
        # Create tessellation object
        """
        Triangulates polygon
        :param polygon: shapely.geometry.polygon
            Polygon to tessellate
        :return: list, list
            Array of triangle vertex indices [t0i0, t0i1, t0i2, t1i0, t1i1, ... ]
            Array of polygon points [(x0, y0), (x1, y1), ... ]
        """
        tess = GLU.gluNewTess()

        # Setup callbacks
        GLU.gluTessCallback(tess, GLU.GLU_TESS_BEGIN, self._on_begin_primitive)
        GLU.gluTessCallback(tess, GLU.GLU_TESS_VERTEX, self._on_new_vertex)
        GLU.gluTessCallback(tess, GLU.GLU_TESS_EDGE_FLAG, self._on_edge_flag)
        GLU.gluTessCallback(tess, GLU.GLU_TESS_COMBINE, self._on_combine)
        GLU.gluTessCallback(tess, GLU.GLU_TESS_ERROR, self._on_error)
        GLU.gluTessCallback(tess, GLU.GLU_TESS_END, self._on_end_primitive)

        # Reset data
        del self.tris[:]
        del self.pts[:]
        self.vertex_index = 0

        # Define polygon
        GLU.gluTessBeginPolygon(tess, None)

        def define_contour(contour):
            vertices = list(contour.coords)             # Get vertices coordinates
            if vertices[0] == vertices[-1]:             # Open ring
                vertices = vertices[:-1]

            self.pts += vertices

            GLU.gluTessBeginContour(tess)               # Start contour

            # Set vertices
            for vertex in vertices:
                point = (vertex[0], vertex[1], 0)
                GLU.gluTessVertex(tess, point, self.vertex_index)
                self.vertex_index += 1

            GLU.gluTessEndContour(tess)                 # End contour

        # Polygon exterior
        define_contour(polygon.exterior)

        # Interiors
        for interior in polygon.interiors:
            define_contour(interior)

        # Start tessellation
        GLU.gluTessEndPolygon(tess)

        # Free resources
        GLU.gluDeleteTess(tess)

        return self.tris, self.pts
