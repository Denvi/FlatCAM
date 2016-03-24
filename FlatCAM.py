import sys
from PyQt4 import QtGui
from PyQt4 import QtCore
from FlatCAMApp import App

def debug_trace():
    '''Set a tracepoint in the Python debugger that works with Qt'''
    from PyQt4.QtCore import pyqtRemoveInputHook
    #from pdb import set_trace
    pyqtRemoveInputHook()
    #set_trace()

debug_trace()

# all X11 calling should  be thread safe  otherwise we have  strenght issues
QtCore.QCoreApplication.setAttribute(QtCore.Qt.AA_X11InitThreads)

app = QtGui.QApplication(sys.argv)
fc = App()
sys.exit(app.exec_())