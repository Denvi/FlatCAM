from PyQt4 import QtCore

class Worker(QtCore.QObject):
    """
    Implements a queue of tasks to be carried out in order
    in a single independent thread.
    """

    # avoid multiple tests  for debug availability
    pydevd_failed = False

    def __init__(self, app, name=None):
        super(Worker, self).__init__()
        self.app = app
        self.name = name

    def allow_debug(self):
        """
         allow debuging/breakpoints in this threads
         should work from PyCharm and PyDev
        :return:
        """

        if not self.pydevd_failed:
            try:
                import pydevd
                pydevd.settrace(suspend=False, trace_only_current_thread=True)
            except ImportError:
                self.pydevd_failed=True

    def run(self):

        # allow  debuging/breakpoints in this threads
        #pydevd.settrace(suspend=False, trace_only_current_thread=True)

        # FlatCAMApp.App.log.debug("Worker Started!")
        self.app.log.debug("Worker Started!")

        # Tasks are queued in the event listener.
        self.app.worker_task.connect(self.do_worker_task)

    def do_worker_task(self, task):

        # FlatCAMApp.App.log.debug("Running task: %s" % str(task))
        self.app.log.debug("Running task: %s" % str(task))

        self.allow_debug()

        # 'worker_name' property of task allows to target
        # specific worker.
        if 'worker_name' in task and task['worker_name'] == self.name:
            task['fcn'](*task['params'])
            return

        if 'worker_name' not in task and self.name is None:
            task['fcn'](*task['params'])
            return

        # FlatCAMApp.App.log.debug("Task ignored.")
        self.app.log.debug("Task ignored.")
