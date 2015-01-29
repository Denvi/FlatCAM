import unittest

from shapely.geometry import LineString, Polygon
from shapely.ops import cascaded_union, unary_union
from matplotlib.pyplot import plot, subplot, show, cla, clf, xlim, ylim, title
from camlib import *
from copy import deepcopy

def mkstorage(paths):
    def get_pts(o):
        return [o.coords[0], o.coords[-1]]
    storage = FlatCAMRTreeStorage()
    storage.get_points = get_pts
    for p in paths:
        storage.insert(p)
    return storage


def plotg2(geo, solid_poly=False, color="black", linestyle='solid'):

    try:
        for sub_geo in geo:
            plotg2(sub_geo, solid_poly=solid_poly, color=color, linestyle=linestyle)
    except TypeError:
        if type(geo) == Polygon:
            if solid_poly:
                patch = PolygonPatch(geo,
                                     #facecolor="#BBF268",
                                     facecolor=color,
                                     edgecolor="#006E20",
                                     alpha=0.5,
                                     zorder=2)
                ax = subplot(111)
                ax.add_patch(patch)
            else:
                x, y = geo.exterior.coords.xy
                plot(x, y, color=color, linestyle=linestyle)
                for ints in geo.interiors:
                    x, y = ints.coords.xy
                    plot(x, y, color=color, linestyle=linestyle)

        if type(geo) == LineString or type(geo) == LinearRing:
            x, y = geo.coords.xy
            plot(x, y, color=color, linestyle=linestyle)

        if type(geo) == Point:
            x, y = geo.coords.xy
            plot(x, y, 'o')


class PaintTestCase(unittest.TestCase):
    # def __init__(self):
    #     super(PaintTestCase, self).__init__()
    #     self.boundary = None
    #     self.descr = None

    def plot_summary_A(self, paths, tooldia, result, msg):
        plotg2(self.boundary, solid_poly=True, color="green")
        plotg2(paths, color="red")
        plotg2([r.buffer(tooldia / 2) for r in result], solid_poly=True, color="blue")
        plotg2(result, color="black", linestyle='dashed')
        title(msg)
        xlim(0, 5)
        ylim(0, 5)
        show()


class PaintConnectTest(PaintTestCase):
    """
    Simple rectangular boundary and paths inside.
    """

    def setUp(self):
        self.boundary = Polygon([[0, 0], [0, 5], [5, 5], [5, 0]])

    def test_jump(self):
        print "Test: WALK Expected"
        paths = [
            LineString([[0.5, 2], [2, 4.5]]),
            LineString([[2, 0.5], [4.5, 2]])
        ]
        for p in paths:
            print p

        tooldia = 1.0

        print "--"
        result = Geometry.paint_connect(mkstorage(deepcopy(paths)), self.boundary, tooldia)

        result = list(result.get_objects())
        for r in result:
            print r

        self.assertEqual(len(result), 1)

        self.plot_summary_A(paths, tooldia, result, "WALK expected.")

    def test_no_jump1(self):
        print "Test: FLY Expected"
        paths = [
            LineString([[0, 2], [2, 5]]),
            LineString([[2, 0], [5, 2]])
        ]
        for p in paths:
            print p

        tooldia = 1.0

        print "--"
        result = Geometry.paint_connect(mkstorage(deepcopy(paths)), self.boundary, tooldia)

        result = list(result.get_objects())
        for r in result:
            print r

        self.assertEqual(len(result), len(paths))

        self.plot_summary_A(paths, tooldia, result, "FLY Expected")

    def test_no_jump2(self):
        print "Test: FLY Expected"
        paths = [
            LineString([[0.5, 2], [2, 4.5]]),
            LineString([[2, 0.5], [4.5, 2]])
        ]
        for p in paths:
            print p

        tooldia = 1.1

        print "--"
        result = Geometry.paint_connect(mkstorage(deepcopy(paths)), self.boundary, tooldia)

        result = list(result.get_objects())
        for r in result:
            print r

        self.assertEqual(len(result), len(paths))

        self.plot_summary_A(paths, tooldia, result, "FLY Expected")


class PaintConnectTest2(PaintTestCase):
    """
    Boundary with an internal cutout.
    """

    def setUp(self):
        self.boundary = Polygon([[0, 0], [0, 5], [5, 5], [5, 0]])
        self.boundary = self.boundary.difference(
            Polygon([[2, 1], [3, 1], [3, 4], [2, 4]])
        )

    def test_no_jump3(self):
        print "TEST: No jump expected"
        paths = [
            LineString([[0.5, 1], [1.5, 3]]),
            LineString([[4, 1], [4, 4]])
        ]
        for p in paths:
            print p

        tooldia = 1.0

        print "--"
        result = Geometry.paint_connect(mkstorage(deepcopy(paths)), self.boundary, tooldia)

        result = list(result.get_objects())
        for r in result:
            print r

        self.assertEqual(len(result), len(paths))

        self.plot_summary_A(paths, tooldia, result, "FLY Expected")


class PaintConnectTest3(PaintTestCase):
    """
    Tests with linerings among elements.
    """

    def setUp(self):
        self.boundary = Polygon([[0, 0], [0, 5], [5, 5], [5, 0]])
        print "TEST w/ LinearRings"

    def test_jump2(self):
        print "Test: WALK Expected"
        paths = [
            LineString([[0.5, 2], [2, 4.5]]),
            LineString([[2, 0.5], [4.5, 2]]),
            self.boundary.buffer(-0.5).exterior
        ]
        for p in paths:
            print p

        tooldia = 1.0

        print "--"
        result = Geometry.paint_connect(mkstorage(deepcopy(paths)), self.boundary, tooldia)

        result = list(result.get_objects())
        for r in result:
            print r

        self.assertEqual(len(result), 1)

        self.plot_summary_A(paths, tooldia, result, "WALK Expected")


if __name__ == '__main__':
    unittest.main()