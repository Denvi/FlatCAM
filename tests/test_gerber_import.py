import sys
import unittest
from PyQt4 import QtGui
from FlatCAMApp import App


class BaseGUITestCase(unittest.TestCase):

    filename = 'simple1.gbr'

    def setUp(self):
        self.app = QtGui.QApplication(sys.argv)
        self.fc = App()

        self.fc.open_gerber('tests/gerber_files/' + self.filename)

    def tearDown(self):
        del self.fc
        del self.app

    def test_available(self):
        names = self.fc.collection.get_names()
        self.assertEquals(len(names), 1,
                          "Expected 1 object, found %d" % len(names))
        self.assertEquals(names[0], self.filename,
                          "Expected name == %s, got %s" % (self.filename, names[0]))
        print names[0]