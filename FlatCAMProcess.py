from FlatCAMGUI import FlatCAMActivityView
from PyQt4 import QtCore
import weakref


class FCProcess(object):

    def __init__(self, descr):
        self.callbacks = {
            "done": []
        }
        self.descr = descr

    def __del__(self):
        self.done()

    def done(self):
        print "FCProcess.done()"
        for fcn in self.callbacks["done"]:
            fcn(self)

    def connect(self, callback, event="done"):
        if callback not in self.callbacks[event]:
            self.callbacks[event].append(callback)

    def disconnect(self, callback, event="done"):
        try:
            self.callbacks[event].remove(callback)
        except ValueError:
            pass

    def status_msg(self):
        return self.descr


class FCProcessContainer(object):
    """
    This is the process container, or controller (as in MVC)
    of the Process/Activity tracking.

    FCProcessContainer keeps weak references to the FCProcess'es
    such that their __del__ method is called when the user
    looses track of their reference.
    """

    def __init__(self):

        self.procs = []

    def add(self, proc):

        self.procs.append(weakref.ref(proc))

    def new(self, descr):
        proc = FCProcess(descr)

        proc.connect(self.on_done, event="done")

        self.add(proc)

        self.on_change(proc)

        return proc

    def on_change(self, proc):
        pass

    def on_done(self, proc):
        self.remove(proc)

    def remove(self, proc):

        to_be_removed = []

        for pref in self.procs:
            if pref() == proc or pref() is None:
                to_be_removed.append(pref)

        for pref in to_be_removed:
            self.procs.remove(pref)


class FCVisibleProcessContainer(QtCore.QObject, FCProcessContainer):
    something_changed = QtCore.pyqtSignal()

    def __init__(self, view):
        assert isinstance(view, FlatCAMActivityView)

        FCProcessContainer.__init__(self)
        QtCore.QObject.__init__(self)

        self.view = view

        self.something_changed.connect(self.update_view)

    def on_done(self, proc):
        print "FCVisibleProcessContainer.on_done()"
        super(FCVisibleProcessContainer, self).on_done(proc)

        #self.update_view()
        self.something_changed.emit()

    def on_change(self, proc):
        print "FCVisibleProcessContainer.on_change()"
        super(FCVisibleProcessContainer, self).on_change(proc)

        #self.update_view()
        self.something_changed.emit()

    def update_view(self):
        print "FCVisibleProcessContainer.update_view()"
        if len(self.procs) == 0:
            self.view.set_idle()

        elif len(self.procs) == 1:
            self.view.set_busy(self.procs[0]().status_msg())

        else:
            self.view.set_busy("%d processes running." % len(self.procs))