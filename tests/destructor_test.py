from time import sleep
from PyQt4 import QtCore
from FlatCAMWorker import Worker

class MyObj():

    def __init__(self):
        pass

    def __del__(self):
        print "##### Destroyed ######"


def parse():
    o = MyObj()
    raise Exception("Intentional Exception")


if __name__ == "__main__":
    qo = QtCore.QObject
    worker = Worker(qo)
    thr1 = QtCore.QThread()
    worker.moveToThread(thr1)
    qo.connect(thr1, QtCore.SIGNAL("started()"), worker.run)
    thr1.start()

    while True:
        try:
            parse()
            print "Parse returned."
        except Exception:
            pass
        sleep(5)
        print "Competed successfully."