from PyQt4 import QtCore
import FlatCAMApp


class Worker(QtCore.QObject):
    """
    Implements a queue of tasks to be carried out in order
    in a single independent thread.
    """

    def __init__(self, app, name=None):
        super(Worker, self).__init__()
        self.app = app
        self.name = name

    def run(self):
        FlatCAMApp.App.log.debug("Worker Started!")

        # Tasks are queued in the event listener.
        self.app.worker_task.connect(self.do_worker_task)

    def do_worker_task(self, task):
        FlatCAMApp.App.log.debug("Running task: %s" % str(task))

        # 'worker_name' property of task allows to target
        # specific worker.
        if 'worker_name' in task and task['worker_name'] == self.name:
            task['fcn'](*task['params'])
            return

        if 'worker_name' not in task and self.name is None:
            task['fcn'](*task['params'])
            return

        FlatCAMApp.App.log.debug("Task ignored.")