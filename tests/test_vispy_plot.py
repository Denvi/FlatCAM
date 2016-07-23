import sys
import unittest
from PyQt4 import QtGui, QtCore
from FlatCAMApp import App
from VisPyPatches import apply_patches
import random
import logging


class VisPyPlotCase(unittest.TestCase):
    """
    This is a top-level test covering the Gerber-to-GCode
    generation workflow.

    THIS IS A REQUIRED TEST FOR ANY UPDATES.

    """

    filenames = ['test', 'test1', 'test2', 'test3', 'test4']

    def setUp(self):
        self.app = QtGui.QApplication(sys.argv)
        apply_patches()
        # Create App, keep app defaults (do not load
        # user-defined defaults).
        self.fc = App()
        self.fc.log.setLevel(logging.ERROR)

    def tearDown(self):
        del self.fc
        del self.app

    def test_flow(self):
        for i in range(100):
            print "Test #", i + 1

            # Open test project
            self.fc.open_project('tests/project_files/' + self.filenames[random.randint(0, len(self.filenames) - 1)])

            print "Project", self.fc.project_filename

            # Wait for project loaded and plotted
            while True:
                self.sleep(500)
                if self.fc.proc_container.view.text.text() == 'Idle.' or self.fc.ui.isHidden():
                    break

            # Interrupt on window close
            if self.fc.ui.isHidden():
                break

            # Create new project and wait for a random time
            self.fc.on_file_new()
            self.sleep(random.randint(100, 1000))

    def sleep(self, time):
        timer = QtCore.QTimer()
        el = QtCore.QEventLoop()

        timer.singleShot(time, el, QtCore.SLOT("quit()"))
        el.exec_()
