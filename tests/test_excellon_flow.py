import unittest
from PyQt4 import QtGui
import sys
from FlatCAMApp import App
from FlatCAMObj import FlatCAMExcellon, FlatCAMCNCjob
from ObjectUI import ExcellonObjectUI
import tempfile
import os
from time import sleep


class ExcellonFlowTestCase(unittest.TestCase):
    """
    This is a top-level test covering the Excellon-to-GCode
    generation workflow.

    THIS IS A REQUIRED TEST FOR ANY UPDATES.

    """

    filename = 'case1.drl'

    def setUp(self):
        self.app = QtGui.QApplication(sys.argv)

        # Create App, keep app defaults (do not load
        # user-defined defaults).
        self.fc = App(user_defaults=False)

        self.fc.open_excellon('tests/excellon_files/' + self.filename)

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
        # Get object by that name, make sure it's a FlatCAMExcellon.
        #---------------------------------------
        excellon_name = names[0]
        excellon_obj = self.fc.collection.get_by_name(excellon_name)
        self.assertTrue(isinstance(excellon_obj, FlatCAMExcellon),
                        "Expected FlatCAMExcellon, instead, %s is %s" %
                        (excellon_name, type(excellon_obj)))

        #----------------------------------------
        # Object's GUI matches Object's options
        #----------------------------------------
        # TODO: Open GUI with double-click on object.
        # Opens the Object's GUI, populates it.
        excellon_obj.build_ui()
        for option, value in excellon_obj.options.iteritems():
            try:
                form_field = excellon_obj.form_fields[option]
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

        #--------------------------------------------------
        # Changes in the GUI should be read in when
        # running any process. Changing something here.
        #--------------------------------------------------

        form_field = excellon_obj.form_fields['feedrate']
        value = form_field.get_value()
        form_field.set_value(value * 1.1)  # Increase by 10%
        print "'feedrate' == {}".format(value)

        #--------------------------------------------------
        # Create GCode using all tools.
        #--------------------------------------------------

        assert isinstance(excellon_obj, FlatCAMExcellon)  # Just for the IDE
        ui = excellon_obj.ui
        assert isinstance(ui, ExcellonObjectUI)
        ui.tools_table.selectAll()  # Select All
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
        # Check that GUI has been read in.
        #---------------------------------------------

        value = excellon_obj.options['feedrate']
        form_value = form_field.get_value()
        self.assertEqual(value, form_value,
                         "Form value for '{}' == {} was not read into options"
                         "which has {}".format('feedrate', form_value, value))
        print "'feedrate' == {}".format(value)

        #---------------------------------------------
        # Check that only 1 object has been created.
        #---------------------------------------------

        names = self.fc.collection.get_names()
        self.assertEqual(len(names), 2,
                         "Expected 2 objects, found %d" % len(names))

        #-------------------------------------------------------
        # Make sure the CNCJob Object has the correct name
        #-------------------------------------------------------

        cncjob_name = excellon_name + "_cnc"
        self.assertTrue(cncjob_name in names,
                        "Object named %s not found." % cncjob_name)

        #-------------------------------------------------------
        # Get the object make sure it's a cncjob object
        #-------------------------------------------------------

        cncjob_obj = self.fc.collection.get_by_name(cncjob_name)
        self.assertTrue(isinstance(cncjob_obj, FlatCAMCNCjob),
                        "Expected a FlatCAMCNCjob, got %s" % type(cncjob_obj))

        #-----------------------------------------
        # Export G-Code, check output
        #-----------------------------------------
        assert isinstance(cncjob_obj, FlatCAMCNCjob)  # For IDE

        # get system temporary file(try create it and delete)
        with tempfile.NamedTemporaryFile(prefix='unittest.',
                                         suffix="." + cncjob_name + '.gcode',
                                         delete=True) as tmp_file:
            output_filename = tmp_file.name

        cncjob_obj.export_gcode(output_filename)
        self.assertTrue(os.path.isfile(output_filename))
        os.remove(output_filename)

        print names
