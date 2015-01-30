from FlatCAMGUI import FlatCAMActivityView

class FCProcess(object):

    def __init__(self, descr):
        self.callbacks = {
            "done": []
        }
        self.descr = descr

    def done(self):
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

    def __init__(self):

        self.procs = []

    def add(self, proc):

        self.procs.append(proc)

    def new(self, descr):
        proc = FCProcess(descr)
        proc.connect(self.on_done, event="done")

    def on_done(self, proc):
        pass

    def remove(self, proc):

        if proc in self.procs:
            self.procs.remove(proc)


class FCVisibleProcessContainer(FCProcessContainer):

    def __init__(self, view):
        assert isinstance(view, FlatCAMActivityView)

        super(FCVisibleProcessContainer, self).__init__()

        self.view = view

    def on_done(self, proc):
        super(FCVisibleProcessContainer, self).on_done(proc)

        self.update_view()

    def update_view(self):

        if len(self.procs) == 0:
            self.view.set_idle()
        elif len(self.procs) == 1:
            self.view.set_busy(self.procs[0].status_msg())
        else:
            self.view.set_busy("%d processes running." % len(self.procs))