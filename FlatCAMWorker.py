from PyQt4 import QtCore
#import Queue
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
        self.app.worker_task.connect(self.do_worker_task)

    def do_worker_task(self, task):
        FlatCAMApp.App.log.debug("Running task: %s" % str(task))
        if 'worker_name' in task and task['worker_name'] == self.name:
            task['fcn'](*task['params'])
            return

        if 'worker_name' not in task and self.name is None:
            task['fcn'](*task['params'])
            return