import sys
from PyQt4 import QtGui, QtCore
from FlatCAMApp import App
from multiprocessing import freeze_support
import VisPyPatches

if sys.platform == "win32":
    # cx_freeze 'module win32' workaround
    import OpenGL.platform.win32

def debug_trace():
    """
    Set a tracepoint in the Python debugger that works with Qt
    :return: None
    """
    from PyQt4.QtCore import pyqtRemoveInputHook
    #from pdb import set_trace
    pyqtRemoveInputHook()
    #set_trace()

# All X11 calling should be thread safe otherwise we have strange issues
# QtCore.QCoreApplication.setAttribute(QtCore.Qt.AA_X11InitThreads)
# NOTE: Never talk to the GUI from threads! This is why I commented the above.

if __name__ == '__main__':
    freeze_support()

    debug_trace()
    VisPyPatches.apply_patches()

    app = QtGui.QApplication(sys.argv)
    fc = App()
    sys.exit(app.exec_())

