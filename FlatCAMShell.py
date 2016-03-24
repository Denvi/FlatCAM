import termwidget


class FCShell(termwidget.TermWidget):
    def __init__(self, sysShell, *args):
        termwidget.TermWidget.__init__(self, *args)
        self._sysShell = sysShell

    def is_command_complete(self, text):
        def skipQuotes(text):
            quote = text[0]
            text = text[1:]
            endIndex = str(text).index(quote)
            return text[endIndex:]
        while text:
            if text[0] in ('"', "'"):
                try:
                    text = skipQuotes(text)
                except ValueError:
                    return False
            text = text[1:]
        return True

    def child_exec_command(self, text):
        self._sysShell.exec_command(text)