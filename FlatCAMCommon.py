class LoudDict(dict):
    """
    A Dictionary with a callback for
    item changes.
    """

    def __init__(self, *args, **kwargs):
        dict.__init__(self, *args, **kwargs)
        self.callback = lambda x: None

    def __setitem__(self, key, value):
        """
        Overridden __setitem__ method. Will emit 'changed(QString)'
        if the item was changed, with key as parameter.
        """
        if key in self and self.__getitem__(key) == value:
            return

        dict.__setitem__(self, key, value)
        self.callback(key)

    def update(self, *args, **kwargs):
        if len(args) > 1:
            raise TypeError("update expected at most 1 arguments, got %d" % len(args))
        other = dict(*args, **kwargs)
        for key in other:
            self[key] = other[key]

    def set_change_callback(self, callback):
        """
        Assigns a function as callback on item change. The callback
        will receive the key of the object that was changed.

        :param callback: Function to call on item change.
        :type callback: func
        :return: None
        """

        self.callback = callback
