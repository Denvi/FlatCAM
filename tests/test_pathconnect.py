import unittest

from shapely.geometry import LineString, Polygon
from shapely.ops import cascaded_union, unary_union
from matplotlib.pyplot import plot, subplot, show, cla, clf, xlim, ylim, title
from camlib import *
from random import random


class PathConnectTest1(unittest.TestCase):

    def setUp(self):
        pass

    def test_simple_connect(self):
        paths = [
            LineString([[0, 0], [1, 1]]),
            LineString([[1, 1], [2, 1]])
        ]

        result = Geometry.path_connect(paths)

        self.assertEqual(len(result), 1)
        self.assertTrue(result[0].equals(LineString([[0, 0], [1, 1], [2, 1]])))

    def test_interfere_connect(self):
        paths = [
            LineString([[0, 0], [1, 1]]),
            LineString([[1, 1], [2, 1]]),
            LineString([[-0.5, 0.5], [0.5, 0]])
        ]

        result = Geometry.path_connect(paths)

        self.assertEqual(len(result), 2)
        matches = [p for p in result if p.equals(LineString([[0, 0], [1, 1], [2, 1]]))]
        self.assertEqual(len(matches), 1)

    def test_simple_connect_offset1(self):
        for i in range(20):
            offset_x = random()
            offset_y = random()

            paths = [
                LineString([[0 + offset_x, 0 + offset_y], [1 + offset_x, 1 + offset_y]]),
                LineString([[1 + offset_x, 1 + offset_y], [2 + offset_x, 1 + offset_y]])
            ]

            result = Geometry.path_connect(paths)

            self.assertEqual(len(result), 1)
            self.assertTrue(result[0].equals(LineString([[0 + offset_x, 0 + offset_y],
                                                         [1 + offset_x, 1 + offset_y],
                                                         [2 + offset_x, 1 + offset_y]])))

    def test_ring_interfere_connect(self):
        print
        print "TEST STARTING ..."

        paths = [
            LineString([[0, 0], [1, 1]]),
            LineString([[1, 1], [2, 1]]),
            LinearRing([[1, 1], [2, 2], [1, 3], [0, 2]])
        ]

        result = Geometry.path_connect(paths)

        self.assertEqual(len(result), 2)
        matches = [p for p in result if p.equals(LineString([[0, 0], [1, 1], [2, 1]]))]
        self.assertEqual(len(matches), 1)

if __name__ == "__main__":
    unittest.main()