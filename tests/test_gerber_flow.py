import sys
import unittest
from PyQt4 import QtGui
from FlatCAMApp import App
from FlatCAMObj import FlatCAMGerber, FlatCAMGeometry, FlatCAMCNCjob
from ObjectUI import GerberObjectUI, GeometryObjectUI
from time import sleep
import os
import tempfile

class GerberFlowTestCase(unittest.TestCase):

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

    def test_flow(self):
        # Names of available objects.
        names = self.fc.collection.get_names()
        print names

        #--------------------------------------
        # Total of 1 objects.
        #--------------------------------------
        self.assertEquals(len(names), 1,
                          "Expected 1 object, found %d" % len(names))

        #--------------------------------------
        # Object's name matches the file name.
        #--------------------------------------
        self.assertEquals(names[0], self.filename,
                          "Expected name == %s, got %s" % (self.filename, names[0]))

        #---------------------------------------
        # Get object by that name, make sure it's a FlatCAMGerber.
        #---------------------------------------
        gerber_name = names[0]
        gerber_obj = self.fc.collection.get_by_name(gerber_name)
        self.assertTrue(isinstance(gerber_obj, FlatCAMGerber),
                        "Expected FlatCAMGerber, instead, %s is %s" %
                        (gerber_name, type(gerber_obj)))

        #--------------------------------------------------
        # Create isolation routing using default values
        # and by clicking on the button.
        #--------------------------------------------------
        # Get the object's GUI and click on "Generate Geometry" under
        # "Isolation Routing"
        assert isinstance(gerber_obj, FlatCAMGerber)  # Just for the IDE
        gerber_obj.build_ui()  # Open the object's UI.
        ui = gerber_obj.ui
        assert isinstance(ui, GerberObjectUI)
        ui.generate_iso_button.click()  # Click

        #---------------------------------------------
        # Check that only 1 object has been created.
        #---------------------------------------------
        names = self.fc.collection.get_names()
        self.assertEqual(len(names), 2,
                         "Expected 2 objects, found %d" % len(names))

        #-------------------------------------------------------
        # Make sure the Geometry Object has the correct name
        #-------------------------------------------------------
        geo_name = gerber_name + "_iso"
        self.assertTrue(geo_name in names,
                        "Object named %s not found." % geo_name)

        #-------------------------------------------------------
        # Get the object make sure it's a geometry object
        #-------------------------------------------------------
        geo_obj = self.fc.collection.get_by_name(geo_name)
        self.assertTrue(isinstance(geo_obj, FlatCAMGeometry),
                        "Expected a FlatCAMGeometry, got %s" % type(geo_obj))

        #------------------------------------
        # Open the UI, make CNCObject
        #------------------------------------
        geo_obj.build_ui()
        ui = geo_obj.ui
        assert isinstance(ui, GeometryObjectUI)  # Just for the IDE
        ui.generate_cnc_button.click()  # Click

        # Work is done in a separate thread and results are
        # passed via events to the main event loop which is
        # not running. Run only for pending events.
        #
        # I'm not sure why, but running it only once does
        # not catch the new object. Might be a timing issue.
        # http://pyqt.sourceforge.net/Docs/PyQt4/qeventloop.html#details
        for _ in range(2):
            sleep(0.1)
            self.app.processEvents()

        #---------------------------------------------
        # Check that only 1 object has been created.
        #---------------------------------------------
        names = self.fc.collection.get_names()
        self.assertEqual(len(names), 3,
                         "Expected 3 objects, found %d" % len(names))

        #-------------------------------------------------------
        # Make sure the CNC Job Object has the correct name
        #-------------------------------------------------------
        cnc_name = geo_name + "_cnc"
        self.assertTrue(cnc_name in names,
                        "Object named %s not found." % geo_name)

        #-------------------------------------------------------
        # Get the object make sure it's a CNC Job object
        #-------------------------------------------------------
        cnc_obj = self.fc.collection.get_by_name(cnc_name)
        self.assertTrue(isinstance(cnc_obj, FlatCAMCNCjob),
                        "Expected a FlatCAMCNCJob, got %s" % type(geo_obj))

        #-----------------------------------------
        # Export G-Code, check output
        #-----------------------------------------
        assert isinstance(cnc_obj, FlatCAMCNCjob)
        output_filename = ""
        # get system temporary file(try create it and  delete also)
        with tempfile.NamedTemporaryFile(prefix='unittest.', suffix="." + cnc_name + '.gcode', delete=True) as tmp_file:
            output_filename = tmp_file.name
        cnc_obj.export_gcode(output_filename)
        self.assertTrue(os.path.isfile(output_filename))
        os.remove(output_filename)

        print names