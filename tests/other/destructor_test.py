import sys
from PyQt4 import QtCore, QtGui


class MyObj():

    def __init__(self):
        pass

    def __del__(self):
        print "##### Destroyed ######"


def parse():
    o = MyObj()
    raise Exception("Intentional Exception")


class Example(QtGui.QWidget):

    def __init__(self):
        super(Example, self).__init__()

        qbtn = QtGui.QPushButton('Raise', self)
        qbtn.clicked.connect(parse)

        self.setWindowTitle('Quit button')
        self.show()


if __name__ == '__main__':
    app = QtGui.QApplication(sys.argv)
    ex = Example()
    sys.exit(app.exec_())