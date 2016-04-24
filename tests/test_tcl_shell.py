import sys
import unittest
from PyQt4 import QtGui
from PyQt4.QtCore import QThread

from FlatCAMApp import App
from os import listdir
from os.path import isfile
from FlatCAMObj import FlatCAMGerber, FlatCAMGeometry, FlatCAMCNCjob, FlatCAMExcellon
from ObjectUI import GerberObjectUI, GeometryObjectUI
from time import sleep
import os
import tempfile

class TclShellTest(unittest.TestCase):

    svg_files = 'tests/svg'
    svg_filename = 'Arduino Nano3_pcb.svg'
    gerber_files = 'tests/gerber_files'
    copper_bottom_filename = 'detector_copper_bottom.gbr'
    copper_top_filename = 'detector_copper_top.gbr'
    cutout_filename = 'detector_contour.gbr'
    excellon_filename = 'detector_drill.txt'
    gerber_name = "gerber"
    geometry_name = "geometry"
    excellon_name = "excellon"
    gerber_top_name = "top"
    gerber_bottom_name = "bottom"
    gerber_cutout_name = "cutout"
    engraver_diameter = 0.3
    cutout_diameter = 3
    drill_diameter = 0.8

    # load test methods to split huge test file into smaller pieces
    # reason for this is reuse one test window only,
    from tests.tclCommands import *

    @classmethod
    def setUpClass(self):

        self.setup=True
        self.app = QtGui.QApplication(sys.argv)
        # Create App, keep app defaults (do not load
        # user-defined defaults).
        self.fc = App(user_defaults=False)
        self.fc.ui.shell_dock.show()

    def setUp(self):
        self.fc.exec_command_test('set_sys units MM')
        self.fc.exec_command_test('new')

    @classmethod
    def tearDownClass(self):
        self.fc.tcl=None
        self.app.closeAllWindows()
        del self.fc
        del self.app
        pass

    def test_set_get_units(self):

        self.fc.exec_command_test('set_sys units MM')
        self.fc.exec_command_test('new')

        self.fc.exec_command_test('set_sys units IN')
        self.fc.exec_command_test('new')
        units=self.fc.exec_command_test('get_sys units')
        self.assertEquals(units, "IN")

        self.fc.exec_command_test('set_sys units MM')
        self.fc.exec_command_test('new')
        units=self.fc.exec_command_test('get_sys units')
        self.assertEquals(units, "MM")


    def test_gerber_flow(self):

        # open  gerber files top, bottom and cutout

        self.fc.exec_command_test('open_gerber %s/%s -outname %s' % (self.gerber_files, self.copper_top_filename, self.gerber_top_name))
        gerber_top_obj = self.fc.collection.get_by_name(self.gerber_top_name)
        self.assertTrue(isinstance(gerber_top_obj, FlatCAMGerber),
                        "Expected FlatCAMGerber, instead, %s is %s" %
                        (self.gerber_top_name, type(gerber_top_obj)))

        self.fc.exec_command_test('open_gerber %s/%s -outname %s' % (self.gerber_files, self.copper_bottom_filename, self.gerber_bottom_name))
        gerber_bottom_obj = self.fc.collection.get_by_name(self.gerber_bottom_name)
        self.assertTrue(isinstance(gerber_bottom_obj, FlatCAMGerber),
                        "Expected FlatCAMGerber, instead, %s is %s" %
                        (self.gerber_bottom_name, type(gerber_bottom_obj)))

        self.fc.exec_command_test('open_gerber %s/%s -outname %s' % (self.gerber_files, self.cutout_filename, self.gerber_cutout_name))
        gerber_cutout_obj = self.fc.collection.get_by_name(self.gerber_cutout_name)
        self.assertTrue(isinstance(gerber_cutout_obj, FlatCAMGerber),
                        "Expected FlatCAMGerber, instead, %s is %s" %
                        (self.gerber_cutout_name, type(gerber_cutout_obj)))

        # exteriors delete and join geometries for top layer
        self.fc.exec_command_test('isolate %s -dia %f' % (self.gerber_cutout_name, self.engraver_diameter))
        self.fc.exec_command_test('exteriors %s -outname %s' % (self.gerber_cutout_name + '_iso', self.gerber_cutout_name + '_iso_exterior'))
        self.fc.exec_command_test('delete %s' % (self.gerber_cutout_name + '_iso'))
        obj = self.fc.collection.get_by_name(self.gerber_cutout_name + '_iso_exterior')
        self.assertTrue(isinstance(obj, FlatCAMGeometry),
                        "Expected FlatCAMGeometry, instead, %s is %s" %
                        (self.gerber_cutout_name + '_iso_exterior', type(obj)))

        # mirror bottom gerbers
        self.fc.exec_command_test('mirror %s -box %s -axis X' % (self.gerber_bottom_name, self.gerber_cutout_name))
        self.fc.exec_command_test('mirror %s -box %s -axis X' % (self.gerber_cutout_name, self.gerber_cutout_name))

        # exteriors delete and join geometries for bottom layer
        self.fc.exec_command_test('isolate %s -dia %f -outname %s' % (self.gerber_cutout_name, self.engraver_diameter, self.gerber_cutout_name + '_bottom_iso'))
        self.fc.exec_command_test('exteriors %s -outname %s' % (self.gerber_cutout_name + '_bottom_iso', self.gerber_cutout_name + '_bottom_iso_exterior'))
        self.fc.exec_command_test('delete %s' % (self.gerber_cutout_name + '_bottom_iso'))
        obj = self.fc.collection.get_by_name(self.gerber_cutout_name + '_bottom_iso_exterior')
        self.assertTrue(isinstance(obj, FlatCAMGeometry),
                        "Expected FlatCAMGeometry, instead, %s is %s" %
                        (self.gerber_cutout_name + '_bottom_iso_exterior', type(obj)))

        # at this stage we should have 5 objects
        names = self.fc.collection.get_names()
        self.assertEqual(len(names), 5,
                         "Expected 5 objects, found %d" % len(names))

        # isolate traces
        self.fc.exec_command_test('isolate %s -dia %f' %  (self.gerber_top_name, self.engraver_diameter))
        self.fc.exec_command_test('isolate %s -dia %f' %  (self.gerber_bottom_name, self.engraver_diameter))

        # join isolated geometries for top and  bottom
        self.fc.exec_command_test('join_geometries %s %s %s' %  (self.gerber_top_name + '_join_iso', self.gerber_top_name + '_iso', self.gerber_cutout_name + '_iso_exterior'))
        self.fc.exec_command_test('join_geometries %s %s %s' %  (self.gerber_bottom_name + '_join_iso', self.gerber_bottom_name + '_iso', self.gerber_cutout_name + '_bottom_iso_exterior'))

        # at this stage we should have 9 objects
        names = self.fc.collection.get_names()
        self.assertEqual(len(names), 9,
                         "Expected 9 objects, found %d" % len(names))

        # clean unused isolations
        self.fc.exec_command_test('delete %s' % (self.gerber_bottom_name + '_iso'))
        self.fc.exec_command_test('delete %s' % (self.gerber_top_name + '_iso'))
        self.fc.exec_command_test('delete %s' % (self.gerber_cutout_name + '_iso_exterior'))
        self.fc.exec_command_test('delete %s' % (self.gerber_cutout_name + '_bottom_iso_exterior'))

        # at this stage we should have 5 objects again
        names = self.fc.collection.get_names()
        self.assertEqual(len(names), 5,
                         "Expected 5 objects, found %d" % len(names))

        # geocutout bottom test (it cuts  to same object)
        self.fc.exec_command_test('isolate %s -dia %f -outname %s' % (self.gerber_cutout_name, self.cutout_diameter, self.gerber_cutout_name + '_bottom_iso'))
        self.fc.exec_command_test('exteriors %s -outname %s' % (self.gerber_cutout_name + '_bottom_iso', self.gerber_cutout_name + '_bottom_iso_exterior'))
        self.fc.exec_command_test('delete %s' % (self.gerber_cutout_name + '_bottom_iso'))
        obj = self.fc.collection.get_by_name(self.gerber_cutout_name + '_bottom_iso_exterior')
        self.assertTrue(isinstance(obj, FlatCAMGeometry),
                        "Expected FlatCAMGeometry, instead, %s is %s" %
                        (self.gerber_cutout_name + '_bottom_iso_exterior', type(obj)))
        self.fc.exec_command_test('geocutout %s -dia %f -gapsize 0.3 -gaps 4' % (self.gerber_cutout_name + '_bottom_iso_exterior', self.cutout_diameter))

        # at this stage we should have 6 objects
        names = self.fc.collection.get_names()
        self.assertEqual(len(names), 6,
                         "Expected 6 objects, found %d" % len(names))

        # TODO: tests for tcl

    def test_open_gerber(self):

        self.fc.exec_command_test('open_gerber %s/%s -outname %s' % (self.gerber_files, self.copper_top_filename, self.gerber_top_name))
        gerber_top_obj = self.fc.collection.get_by_name(self.gerber_top_name)
        self.assertTrue(isinstance(gerber_top_obj, FlatCAMGerber),
                        "Expected FlatCAMGerber, instead, %s is %s" %
                        (self.gerber_top_name, type(gerber_top_obj)))

    def test_excellon_flow(self):

        self.fc.exec_command_test('open_excellon %s/%s -outname %s' % (self.gerber_files, self.excellon_filename, self.excellon_name))
        excellon_obj = self.fc.collection.get_by_name(self.excellon_name)
        self.assertTrue(isinstance(excellon_obj, FlatCAMExcellon),
                        "Expected FlatCAMExcellon, instead, %s is %s" %
                        (self.excellon_name, type(excellon_obj)))

        # mirror bottom excellon
        self.fc.exec_command_test('mirror %s -box %s -axis X' % (self.excellon_name, self.gerber_cutout_name))

        # TODO: tests for tcl
