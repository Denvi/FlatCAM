from PyQt4 import QtCore
from multiprocessing import Pool
import dill

def run_dill_encoded(what):
    fun, args = dill.loads(what)
    print "load", fun, args
    return fun(*args)

def apply_async(pool, fun, args):
    print "...", fun, args
    print "dumps", dill.dumps((fun, args))
    return pool.map_async(run_dill_encoded, (dill.dumps((fun, args)),))

def func1():
    print "func"

class WorkerPool(QtCore.QObject):

    def __init__(self):
        super(WorkerPool, self).__init__()
        self.pool = Pool(2)

    def add_task(self, task):
        print "adding task", task
        # task['fcn'](*task['params'])
        # print self.pool.map(task['fcn'], task['params'])
        apply_async(self.pool, func1, ())
