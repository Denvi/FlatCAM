from unittest import TestCase
from FlatCAMWorkerStack import WorkerStack
from PyQt4 import QtCore, QtGui
import random
from multiprocessing import Process, Queue
from shapely.geometry import LineString
import time


def calc(line, q):
    res = q.get()
    res += list(line.coords)

    res = [res for _ in range(3)]

    q.put(res)
    # a = [x ** x for x in range(0, random.randint(5000, 10000))]
    print "process ended"
    return


class TestWorkerStack(TestCase):

    def test_create(self):
        a = QtGui.QApplication([])

        s = WorkerStack()
        time.sleep(1)

        for i in range(0, 4):
            s.add_task({'fcn': self.task, 'params': [i]})

        # self.sleep(1000)
        #
        # for i in range(0, 8):
        #     s.add_task({'fcn': self.task, 'params': [i + 8]})

        time.sleep(2)

    def task(self, id):
        print "Task", id, "started"

        line = LineString([(0, 0), (1, 1), (1, 0), (0, 0)])
        out = [(9, 9)]

        q = Queue()
        q.put(out)

        p = Process(target=calc, args=(line, q))
        p.start()
        p.join()

        out = q.get()
        print "Task", id, "ended", out
