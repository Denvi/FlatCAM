import sys
import unittest
from PyQt4 import QtGui
from FlatCAMApp import App


class BaseGUITestCase(unittest.TestCase):

    filename = 'simple1.gbr'

    def setUp(self):
        self.app = QtGui.QApplication(sys.argv)

        # Create App, keep app defaults (do not load
        # user-defined defaults).
        self.fc = App(user_defaults=False)

        self.fc.open_gerber('tests/gerber_files/' + self.filename)

    def tearDown(self):
        del self.fc
        del self.app

    def test_available(self):
        names = self.fc.collection.get_names()

        # Total of 1 objects
        self.assertEquals(len(names), 1,
                          "Expected 1 object, found %d" % len(names))

        # Object's name matches the file name.
        self.assertEquals(names[0], self.filename,
                          "Expected name == %s, got %s" % (self.filename, names[0]))
        print names[0]