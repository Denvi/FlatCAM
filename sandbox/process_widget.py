import sys
from PyQt4.QtGui import *

app = QApplication(sys.argv)

top = QWidget()
halign = QHBoxLayout()
top.setLayout(halign)
busy_anim = QMovie("../share/busy16.gif")
busy_anim.start()
busy_anim_label = QLabel()
busy_anim_label.setMovie(busy_anim)
halign.addWidget(busy_anim_label)

message_label = QLabel("Processing...")
halign.addWidget(message_label)

top.show()

sys.exit(app.exec_())