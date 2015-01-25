import unittest

from shapely.geometry import LineString, Polygon
from shapely.ops import cascaded_union, unary_union
from matplotlib.pyplot import plot, subplot, show, cla, clf, xlim, ylim, title
from camlib import *


class PathConnectTest1(unittest.TestCase):

    def setUp(self):
        pass

    def test_simple_connect(self):
        paths = [
            LineString([[0, 0], [0, 1]]),
            LineString([[0, 1], [0, 2]])
        ]

        result = Geometry.path_connect(paths)

        self.assertEqual(len(result), 1)
        self.assertTrue(result[0].equals(LineString([[0, 0], [0, 2]])))


if __name__ == "__main__":
    unittest.main()