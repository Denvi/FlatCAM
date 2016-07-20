from PyQt4 import QtCore
from FlatCAMWorker import Worker
import multiprocessing


class WorkerStack(QtCore.QObject):

    worker_task = QtCore.pyqtSignal(dict)               # 'worker_name', 'func', 'params'
    thread_exception = QtCore.pyqtSignal(object)

    def __init__(self):
        super(WorkerStack, self).__init__()

        self.workers = []
        self.threads = []
        self.load = {}                                  # {'worker_name': tasks_count}

        # Create workers crew
        for i in range(0, 2):
            worker = Worker(self, 'Slogger-' + str(i))
            thread = QtCore.QThread()

            worker.moveToThread(thread)
            worker.connect(thread, QtCore.SIGNAL("started()"), worker.run)
            worker.task_completed.connect(self.on_task_completed)

            thread.start()

            self.workers.append(worker)
            self.threads.append(thread)
            self.load[worker.name] = 0

    def __del__(self):
        for thread in self.threads:
            thread.terminate()

    def add_task(self, task):
        worker_name = min(self.load, key=self.load.get)
        self.load[worker_name] += 1
        self.worker_task.emit({'worker_name': worker_name, 'fcn': task['fcn'], 'params': task['params']})

    def on_task_completed(self, worker_name):
        self.load[str(worker_name)] -= 1
