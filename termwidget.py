"""
Terminal emulator widget.
Shows intput and output text. Allows to enter commands. Supports history.
"""

import cgi

from PyQt4.QtCore import pyqtSignal
from PyQt4.QtGui import QColor, QKeySequence, QLineEdit, QPalette, \
                        QSizePolicy, QTextCursor, QTextEdit, \
                        QVBoxLayout, QWidget


class _ExpandableTextEdit(QTextEdit):
    """
    Class implements edit line, which expands themselves automatically
    """

    historyNext = pyqtSignal()
    historyPrev = pyqtSignal()

    def __init__(self, termWidget, *args):
        QTextEdit.__init__(self, *args)
        self.setStyleSheet("font: 9pt \"Courier\";")
        self._fittedHeight = 1
        self.textChanged.connect(self._fit_to_document)
        self._fit_to_document()
        self._termWidget = termWidget

    def sizeHint(self):
        """
        QWidget sizeHint impelemtation
        """
        hint = QTextEdit.sizeHint(self)
        hint.setHeight(self._fittedHeight)
        return hint

    def _fit_to_document(self):
        """
        Update widget height to fit all text
        """
        documentSize = self.document().size().toSize()
        self._fittedHeight = documentSize.height() + (self.height() - self.viewport().height())
        self.setMaximumHeight(self._fittedHeight)
        self.updateGeometry();

    def keyPressEvent(self, event):
        """
        Catch keyboard events. Process Enter, Up, Down
        """
        if event.matches(QKeySequence.InsertParagraphSeparator):
            text = self.toPlainText()
            if self._termWidget.is_command_complete(text):
                self._termWidget.exec_current_command()
                return
        elif event.matches(QKeySequence.MoveToNextLine):
            text = self.toPlainText()
            cursorPos = self.textCursor().position()
            textBeforeEnd = text[cursorPos:]
            # if len(textBeforeEnd.splitlines()) <= 1:
            if len(textBeforeEnd.split('\n')) <= 1:
                self.historyNext.emit()
                return
        elif event.matches(QKeySequence.MoveToPreviousLine):
            text = self.toPlainText()
            cursorPos = self.textCursor().position()
            textBeforeStart = text[:cursorPos]
            # lineCount = len(textBeforeStart.splitlines())
            lineCount = len(textBeforeStart.split('\n'))
            if len(textBeforeStart) > 0 and \
                    (textBeforeStart[-1] == '\n' or textBeforeStart[-1] == '\r'):
                lineCount += 1
            if lineCount <= 1:
                self.historyPrev.emit()
                return
        elif event.matches(QKeySequence.MoveToNextPage) or \
             event.matches(QKeySequence.MoveToPreviousPage):
            return self._termWidget.browser().keyPressEvent(event)

        QTextEdit.keyPressEvent(self, event)


class TermWidget(QWidget):
    """
    Widget wich represents terminal. It only displays text and allows to enter text.
    All highlevel logic should be implemented by client classes

    User pressed Enter. Client class should decide, if command must be executed or user may continue edit it
    """

    def __init__(self, *args):
        QWidget.__init__(self, *args)

        self._browser = QTextEdit(self)
        self._browser.setStyleSheet("font: 9pt \"Courier\";")
        self._browser.setReadOnly(True)
        self._browser.document().setDefaultStyleSheet(self._browser.document().defaultStyleSheet() +
                                                      "span {white-space:pre;}")

        self._edit = _ExpandableTextEdit(self, self)
        self._edit.historyNext.connect(self._on_history_next)
        self._edit.historyPrev.connect(self._on_history_prev)
        self.setFocusProxy(self._edit)

        layout = QVBoxLayout(self)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._browser)
        layout.addWidget(self._edit)

        self._history = ['']  # current empty line
        self._historyIndex = 0

        self._edit.setFocus()

    def _append_to_browser(self, style, text):
        """
        Convert text to HTML for inserting it to browser
        """
        assert style in ('in', 'out', 'err')

        text = cgi.escape(text)

        text = text.replace('\n', '<br/>')

        if style != 'out':
            def_bg = self._browser.palette().color(QPalette.Base)
            h, s, v, a = def_bg.getHsvF()

            if style == 'in':
                if v > 0.5:  # white background
                    v = v - (v / 8)  # make darker
                else:
                    v = v + ((1 - v) / 4)  # make ligher
            else:  # err
                if v < 0.5:
                    v = v + ((1 - v) / 4)  # make ligher

                if h == -1:  # make red
                    h = 0
                    s = .4
                else:
                    h = h + ((1 - h) * 0.5)  # make more red

            bg = QColor.fromHsvF(h, s, v).name()
            text = '<span style="background-color: %s; font-weight: bold;">%s</span>' % (str(bg), text)
        else:
            text = '<span>%s</span>' % text  # without span <br/> is ignored!!!

        scrollbar = self._browser.verticalScrollBar()
        old_value = scrollbar.value()
        scrollattheend = old_value == scrollbar.maximum()

        self._browser.moveCursor(QTextCursor.End)
        self._browser.insertHtml(text)

        """TODO When user enters second line to the input, and input is resized, scrollbar changes its positon
        and stops moving. As quick fix of this problem, now we always scroll down when add new text.
        To fix it correctly, srcoll to the bottom, if before intput has been resized,
        scrollbar was in the bottom, and remove next lien
        """
        scrollattheend = True

        if scrollattheend:
            scrollbar.setValue(scrollbar.maximum())
        else:
            scrollbar.setValue(old_value)

    def exec_current_command(self):
        """
        Save current command in the history. Append it to the log. Clear edit line
        Reimplement in the child classes to actually execute command
        """
        text = str(self._edit.toPlainText())
        self._append_to_browser('in', '> ' + text + '\n')

        if len(self._history) < 2 or\
           self._history[-2] != text:  # don't insert duplicating items
            if text[-1] == '\n':
                self._history.insert(-1, text[:-1])
            else:
                self._history.insert(-1, text)

        self._historyIndex = len(self._history) - 1

        self._history[-1] = ''
        self._edit.clear()

        if not text[-1] == '\n':
            text += '\n'

        self.child_exec_command(text)

    def child_exec_command(self, text):
        """
        Reimplement in the child classes
        """
        pass

    def add_line_break_to_input(self):
        self._edit.textCursor().insertText('\n')

    def append_output(self, text):
        """Appent text to output widget
        """
        self._append_to_browser('out', text)

    def append_error(self, text):
        """Appent error text to output widget. Text is drawn with red background
        """
        self._append_to_browser('err', text)

    def is_command_complete(self, text):
        """
        Executed by _ExpandableTextEdit. Reimplement this function in the child classes.
        """
        return True

    def browser(self):
        return self._browser

    def _on_history_next(self):
        """
        Down pressed, show next item from the history
        """
        if (self._historyIndex + 1) < len(self._history):
            self._historyIndex += 1
            self._edit.setPlainText(self._history[self._historyIndex])
            self._edit.moveCursor(QTextCursor.End)

    def _on_history_prev(self):
        """
        Up pressed, show previous item from the history
        """
        if self._historyIndex > 0:
            if self._historyIndex == (len(self._history) - 1):
                self._history[-1] = self._edit.toPlainText()
            self._historyIndex -= 1
            self._edit.setPlainText(self._history[self._historyIndex])
            self._edit.moveCursor(QTextCursor.End)

