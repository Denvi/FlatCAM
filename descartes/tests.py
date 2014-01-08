from shapely.geometry import *
import unittest

from descartes.patch import PolygonPatch

class PolygonTestCase(unittest.TestCase):
    polygon = Point(0, 0).buffer(10.0).difference(
                MultiPoint([(-5, 0), (5, 0)]).buffer(3.0))
    def test_patch(self):
        patch = PolygonPatch(self.polygon)
        self.failUnlessEqual(str(type(patch)), 
            "<class 'matplotlib.patches.PathPatch'>")
        path = patch.get_path()
        self.failUnless(len(path.vertices) == len(path.codes) == 198)

class JSONPolygonTestCase(unittest.TestCase):
    polygon = Point(0, 0).buffer(10.0).difference(
                MultiPoint([(-5, 0), (5, 0)]).buffer(3.0))
    def test_patch(self):
        geo = self.polygon.__geo_interface__
        patch = PolygonPatch(geo)
        self.failUnlessEqual(str(type(patch)), 
            "<class 'matplotlib.patches.PathPatch'>")
        path = patch.get_path()
        self.failUnless(len(path.vertices) == len(path.codes) == 198)

class GeoInterfacePolygonTestCase(unittest.TestCase):
    class GeoThing:
        __geo_interface__ = None
    thing = GeoThing()
    thing.__geo_interface__ = Point(0, 0).buffer(10.0).difference(
                MultiPoint([(-5, 0), (5, 0)]).buffer(3.0)).__geo_interface__
    def test_patch(self):
        patch = PolygonPatch(self.thing)
        self.failUnlessEqual(str(type(patch)), 
            "<class 'matplotlib.patches.PathPatch'>")
        path = patch.get_path()
        self.failUnless(len(path.vertices) == len(path.codes) == 198)
