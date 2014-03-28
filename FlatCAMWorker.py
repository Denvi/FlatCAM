############################################################
# FlatCAM: 2D Post-processing for Manufacturing            #
# http://caram.cl/software/flatcam                         #
# Author: Juan Pablo Caram (c)                             #
# Date: 2/5/2014                                           #
# MIT Licence                                              #
############################################################

import threading
import Queue


class Worker(threading.Thread):
    """
    Implements a queue of tasks to be carried out in order
    in a single independent thread.
    """

    def __init__(self):
        super(Worker, self).__init__()
        self.queue = Queue.Queue()
        self.stoprequest = threading.Event()

    def run(self):
        while not self.stoprequest.isSet():
            try:
                task = self.queue.get(True, 0.05)
                self.do_task(task)
            except Queue.Empty:
                continue

    @staticmethod
    def do_task(task):
        task['fcn'](*task['params'])
        return

    def add_task(self, target, params=list()):
        self.queue.put({'fcn': target, 'params': params})
        return

    def join(self, timeout=None):
        self.stoprequest.set()
        super(Worker, self).join()