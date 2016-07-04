import sys
import unittest
from PyQt4 import QtGui
from FlatCAMApp import App
from FlatCAMObj import FlatCAMGeometry, FlatCAMCNCjob
from ObjectUI import GerberObjectUI, GeometryObjectUI
from time import sleep
import os
import tempfile


class SVGFlowTestCase(unittest.TestCase):

    def setUp(self):
        self.app = QtGui.QApplication(sys.argv)

        # Create App, keep app defaults (do not load
        # user-defined defaults).
        self.fc = App(user_defaults=False)

        self.filename = 'drawing.svg'

    def tearDown(self):
        del self.fc
        del self.app

    def test_flow(self):

        self.fc.import_svg('tests/svg/' + self.filename)

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
        geo_name = names[0]
        geo_obj = self.fc.collection.get_by_name(geo_name)
        self.assertTrue(isinstance(geo_obj, FlatCAMGeometry),
                        "Expected FlatCAMGeometry, instead, %s is %s" %
                        (geo_name, type(geo_obj)))

        #----------------------------------------
        # Object's GUI matches Object's options
        #----------------------------------------
        # TODO: Open GUI with double-click on object.
        # Opens the Object's GUI, populates it.
        geo_obj.build_ui()
        for option, value in geo_obj.options.iteritems():
            try:
                form_field = geo_obj.form_fields[option]
            except KeyError:
                print ("**********************************************************\n"
                       "* WARNING: Option '{}' has no form field\n"
                       "**********************************************************"
                       "".format(option))
                continue
            self.assertEqual(value, form_field.get_value(),
                             "Option '{}' == {} but form has {}".format(
                                 option, value, form_field.get_value()
                             ))

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
        self.assertEqual(len(names), 2,
                         "Expected 2 objects, found %d" % len(names))

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
        with tempfile.NamedTemporaryFile(prefix='unittest.',
                                         suffix="." + cnc_name + '.gcode',
                                         delete=True) as tmp_file:
            output_filename = tmp_file.name
        cnc_obj.export_gcode(output_filename)
        self.assertTrue(os.path.isfile(output_filename))
        os.remove(output_filename)

        print names
