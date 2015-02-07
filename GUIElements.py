from PyQt4 import QtGui, QtCore
from copy import copy
import FlatCAMApp
import re


class RadioSet(QtGui.QWidget):
    def __init__(self, choices, orientation='horizontal', parent=None):
        """
        The choices are specified as a list of dictionaries containing:

        * 'label': Shown in the UI
        * 'value': The value returned is selected

        :param choices: List of choices. See description.
        :type choices: list
        """
        super(RadioSet, self).__init__(parent)
        self.choices = copy(choices)

        if orientation == 'horizontal':
            layout = QtGui.QHBoxLayout()
        else:
            layout = QtGui.QVBoxLayout()

        group = QtGui.QButtonGroup(self)

        for choice in self.choices:
            choice['radio'] = QtGui.QRadioButton(choice['label'])
            group.addButton(choice['radio'])
            layout.addWidget(choice['radio'], stretch=0)
            choice['radio'].toggled.connect(self.on_toggle)

        layout.addStretch()
        self.setLayout(layout)

        self.group_toggle_fn = lambda: None

    def on_toggle(self):
        FlatCAMApp.App.log.debug("Radio toggled")
        radio = self.sender()
        if radio.isChecked():
            self.group_toggle_fn()
        return

    def get_value(self):
        for choice in self.choices:
            if choice['radio'].isChecked():
                return choice['value']
        FlatCAMApp.App.log.error("No button was toggled in RadioSet.")
        return None

    def set_value(self, val):
        for choice in self.choices:
            if choice['value'] == val:
                choice['radio'].setChecked(True)
                return
        FlatCAMApp.App.log.error("Value given is not part of this RadioSet: %s" % str(val))


class LengthEntry(QtGui.QLineEdit):
    def __init__(self, output_units='IN', parent=None):
        super(LengthEntry, self).__init__(parent)

        self.output_units = output_units
        self.format_re = re.compile(r"^([^\s]+)(?:\s([a-zA-Z]+))?$")

        # Unit conversion table OUTPUT-INPUT
        self.scales = {
            'IN': {'IN': 1.0,
                   'MM': 1/25.4},
            'MM': {'IN': 25.4,
                   'MM': 1.0}
        }

    def returnPressed(self, *args, **kwargs):
        val = self.get_value()
        if val is not None:
            self.set_text(QtCore.QString(str(val)))
        else:
            FlatCAMApp.App.log.warning("Could not interpret entry: %s" % self.get_text())

    def get_value(self):
        raw = str(self.text()).strip(' ')
        match = self.format_re.search(raw)

        if not match:
            return None
        try:
            if match.group(2) is not None and match.group(2).upper() in self.scales:
                return float(eval(match.group(1)))*float(self.scales[self.output_units][match.group(2).upper()])
            else:
                return float(eval(match.group(1)))
        except:
            FlatCAMApp.App.log.warning("Could not parse value in entry: %s" % str(raw))
            return None

    def set_value(self, val):
        self.setText(QtCore.QString(str(val)))


class FloatEntry(QtGui.QLineEdit):
    def __init__(self, parent=None):
        super(FloatEntry, self).__init__(parent)

    def returnPressed(self, *args, **kwargs):
        val = self.get_value()
        if val is not None:
            self.set_text(QtCore.QString(str(val)))
        else:
            FlatCAMApp.App.log.warning("Could not interpret entry: %s" % self.text())

    def get_value(self):
        raw = str(self.text()).strip(' ')
        try:
            evaled = eval(raw)
        except:
            FlatCAMApp.App.log.error("Could not evaluate: %s" % str(raw))
            return None

        return float(evaled)

    def set_value(self, val):
        self.setText("%.6f"%val)


class IntEntry(QtGui.QLineEdit):
    def __init__(self, parent=None):
        super(IntEntry, self).__init__(parent)

    def get_value(self):
        return int(self.text())

    def set_value(self, val):
        self.setText(QtCore.QString(str(val)))


class FCEntry(QtGui.QLineEdit):
    def __init__(self, parent=None):
        super(FCEntry, self).__init__(parent)

    def get_value(self):
        return str(self.text())

    def set_value(self, val):
        self.setText(QtCore.QString(str(val)))


class EvalEntry(QtGui.QLineEdit):
    def __init__(self, parent=None):
        super(EvalEntry, self).__init__(parent)

    def returnPressed(self, *args, **kwargs):
        val = self.get_value()
        if val is not None:
            self.setText(QtCore.QString(str(val)))
        else:
            FlatCAMApp.App.log.warning("Could not interpret entry: %s" % self.get_text())

    def get_value(self):
        raw = str(self.text()).strip(' ')
        try:
            return eval(raw)
        except:
            FlatCAMApp.App.log.error("Could not evaluate: %s" % str(raw))
            return None

    def set_value(self, val):
        self.setText(QtCore.QString(str(val)))


class FCCheckBox(QtGui.QCheckBox):
    def __init__(self, label='', parent=None):
        super(FCCheckBox, self).__init__(QtCore.QString(label), parent)

    def get_value(self):
        return self.isChecked()

    def set_value(self, val):
        self.setChecked(val)


class FCTextArea(QtGui.QPlainTextEdit):
    def __init__(self, parent=None):
        super(FCTextArea, self).__init__(parent)

    def set_value(self, val):
        self.setPlainText(val)

    def get_value(self):
        return str(self.toPlainText())


class VerticalScrollArea(QtGui.QScrollArea):
    """
    This widget extends QtGui.QScrollArea to make a vertical-only
    scroll area that also expands horizontally to accomodate
    its contents.
    """
    def __init__(self, parent=None):
        QtGui.QScrollArea.__init__(self, parent=parent)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)

    def eventFilter(self, source, event):
        """
        The event filter gets automatically installed when setWidget()
        is called.

        :param source:
        :param event:
        :return:
        """
        if event.type() == QtCore.QEvent.Resize and source == self.widget():
            # FlatCAMApp.App.log.debug("VerticalScrollArea: Widget resized:")
            # FlatCAMApp.App.log.debug(" minimumSizeHint().width() = %d" % self.widget().minimumSizeHint().width())
            # FlatCAMApp.App.log.debug(" verticalScrollBar().width() = %d" % self.verticalScrollBar().width())

            self.setMinimumWidth(self.widget().sizeHint().width() +
                                 self.verticalScrollBar().sizeHint().width())

            # if self.verticalScrollBar().isVisible():
            #     FlatCAMApp.App.log.debug(" Scroll bar visible")
            #     self.setMinimumWidth(self.widget().minimumSizeHint().width() +
            #                          self.verticalScrollBar().width())
            # else:
            #     FlatCAMApp.App.log.debug(" Scroll bar hidden")
            #     self.setMinimumWidth(self.widget().minimumSizeHint().width())
        return QtGui.QWidget.eventFilter(self, source, event)


class OptionalInputSection():

    def __init__(self, cb, optinputs):
        assert isinstance(cb, FCCheckBox)

        self.cb = cb
        self.optinputs = optinputs

        self.on_cb_change()
        self.cb.stateChanged.connect(self.on_cb_change)

    def on_cb_change(self):

        if self.cb.checkState():

            for widget in self.optinputs:
                widget.setEnabled(True)

        else:

            for widget in self.optinputs:
                widget.setEnabled(False)

