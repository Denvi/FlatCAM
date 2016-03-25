from PyQt4 import QtCore
#import FlatCAMApp


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

        self.app.log.debug("Worker Started!")

        # Tasks are queued in the event listener.
        self.app.worker_task.connect(self.do_worker_task)

    def do_worker_task(self, task):

        self.app.log.debug("Running task: %s" % str(task))

        # 'worker_name' property of task allows to target
        # specific worker.
        if ('worker_name' in task and task['worker_name'] == self.name) or \
                ('worker_name' not in task and self.name is None):

            try:
                task['fcn'](*task['params'])
            except Exception as e:
                self.app.thread_exception.emit(e)
                raise e

            return

        # FlatCAMApp.App.log.debug("Task ignored.")
        self.app.log.debug("Task ignored.")