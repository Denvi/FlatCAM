import sys
from PyQt4 import QtGui
from FlatCAMApp import App

def debug_trace():
    '''Set a tracepoint in the Python debugger that works with Qt'''
    from PyQt4.QtCore import pyqtRemoveInputHook
    #from pdb import set_trace
    pyqtRemoveInputHook()
    #set_trace()

debug_trace()
app = QtGui.QApplication(sys.argv)
fc = App()
sys.exit(app.exec_())