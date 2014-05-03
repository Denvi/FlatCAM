############################################################
# FlatCAM: 2D Post-processing for Manufacturing            #
# http://caram.cl/software/flatcam                         #
# Author: Juan Pablo Caram (c)                             #
# Date: 4/20/2014                                           #
# MIT Licence                                              #
############################################################

from FlatCAMObj import *
from gi.repository import Gtk, GdkPixbuf
import inspect  # TODO: Remove
import FlatCAMApp


class ObjectCollection:

    classdict = {
        "gerber": FlatCAMGerber,
        "excellon": FlatCAMExcellon,
        "cncjob": FlatCAMCNCjob,
        "geometry": FlatCAMGeometry
    }

    icon_files = {
        "gerber": "share/flatcam_icon16.png",
        "excellon": "share/drill16.png",
        "cncjob": "share/cnc16.png",
        "geometry": "share/geometry16.png"
    }

    def __init__(self):

        ### Icons for the list view
        self.icons = {}
        for kind in ObjectCollection.icon_files:
            self.icons[kind] = GdkPixbuf.Pixbuf.new_from_file(ObjectCollection.icon_files[kind])

        ### GUI List components
        ## Model
        self.store = Gtk.ListStore(FlatCAMObj)

        ## View
        self.view = Gtk.TreeView(model=self.store)
        #self.view.connect("row_activated", self.on_row_activated)
        self.tree_selection = self.view.get_selection()
        self.change_subscription = self.tree_selection.connect("changed", self.on_list_selection_change)

        ## Renderers
        # Icon
        renderer_pixbuf = Gtk.CellRendererPixbuf()
        column_pixbuf = Gtk.TreeViewColumn("Type", renderer_pixbuf)

        def _set_cell_icon(column, cell, model, it, data):
            obj = model.get_value(it, 0)
            cell.set_property('pixbuf', self.icons[obj.kind])

        column_pixbuf.set_cell_data_func(renderer_pixbuf, _set_cell_icon)
        self.view.append_column(column_pixbuf)

        # Name
        renderer_text = Gtk.CellRendererText()
        column_text = Gtk.TreeViewColumn("Name", renderer_text)

        def _set_cell_text(column, cell, model, it, data):
            obj = model.get_value(it, 0)
            cell.set_property('text', obj.options["name"])

        column_text.set_cell_data_func(renderer_text, _set_cell_text)
        self.view.append_column(column_text)

    def print_list(self):
        iterat = self.store.get_iter_first()
        while iterat is not None:
            obj = self.store[iterat][0]
            print obj
            iterat = self.store.iter_next(iterat)

    def delete_all(self):
        FlatCAMApp.App.log.debug(str(inspect.stack()[1][3]) + "--> OC.delete_all()")
        self.store.clear()

    def delete_active(self):
        FlatCAMApp.App.log.debug(str(inspect.stack()[1][3]) + "--> OC.delete_active()")
        try:
            model, treeiter = self.tree_selection.get_selected()
            self.store.remove(treeiter)
        except:
            pass

    def on_list_selection_change(self, selection):
        """
        Callback for change in selection on the objects' list.
        Instructs the new selection to build the UI for its options.

        :param selection: Ignored.
        :return: None
        """
        FlatCAMApp.App.log.debug(str(inspect.stack()[1][3]) + "--> OC.on_list_selection_change()")
        try:
            self.get_active().build_ui()
        except AttributeError:  # For None being active
            pass

    def set_active(self, name):
        """
        Sets an object as the active object in the program. Same
        as `set_list_selection()`.

        :param name: Name of the object.
        :type name: str
        :return: None
        """
        FlatCAMApp.App.log.debug(str(inspect.stack()[1][3]) + "--> OC.set_active()")
        self.set_list_selection(name)

    def get_active(self):
        FlatCAMApp.App.log.debug(str(inspect.stack()[1][3]) + "--> OC.get_active()")
        try:
            model, treeiter = self.tree_selection.get_selected()
            return model[treeiter][0]
        except (TypeError, ValueError):
            return None

    def set_list_selection(self, name):
        """
        Sets which object should be selected in the list.

        :param name: Name of the object.
        :rtype name: str
        :return: None
        """
        FlatCAMApp.App.log.debug(str(inspect.stack()[1][3]) + "--> OC.set_list_selection()")
        iterat = self.store.get_iter_first()
        while iterat is not None and self.store[iterat][0].options["name"] != name:
            iterat = self.store.iter_next(iterat)
        self.tree_selection.select_iter(iterat)

    def append(self, obj, active=False):
        """
        Add a FlatCAMObj the the collection. This method is thread-safe.

        :param obj: FlatCAMObj to append
        :type obj: FlatCAMObj
        :param active: If it is to become the active object after appending
        :type active: bool
        :return: None
        """
        FlatCAMApp.App.log.debug(str(inspect.stack()[1][3]) + "--> OC.append()")

        def guitask():
            self.store.append([obj])
            if active:
                self.set_list_selection(obj.options["name"])
        GLib.idle_add(guitask)

    def get_names(self):
        """
        Gets a list of the names of all objects in the collection.

        :return: List of names.
        :rtype: list
        """
        FlatCAMApp.App.log.debug(str(inspect.stack()[1][3]) + "--> OC.get_names()")
        names = []
        iterat = self.store.get_iter_first()
        while iterat is not None:
            obj = self.store[iterat][0]
            names.append(obj.options["name"])
            iterat = self.store.iter_next(iterat)
        return names

    def get_bounds(self):
        """
        Finds coordinates bounding all objects in the collection.

        :return: [xmin, ymin, xmax, ymax]
        :rtype: list
        """
        FlatCAMApp.App.log.debug(str(inspect.stack()[1][3]) + "--> OC.get_bounds()")

        # TODO: Move the operation out of here.

        xmin = Inf
        ymin = Inf
        xmax = -Inf
        ymax = -Inf

        iterat = self.store.get_iter_first()
        while iterat is not None:
            obj = self.store[iterat][0]
            try:
                gxmin, gymin, gxmax, gymax = obj.bounds()
                xmin = min([xmin, gxmin])
                ymin = min([ymin, gymin])
                xmax = max([xmax, gxmax])
                ymax = max([ymax, gymax])
            except:
                FlatCAMApp.App.log.waring("DEV WARNING: Tried to get bounds of empty geometry.")
            iterat = self.store.iter_next(iterat)
        return [xmin, ymin, xmax, ymax]

    def get_list(self):
        """
        Returns a list with all FlatCAMObj.

        :return: List with all FlatCAMObj.
        :rtype: list
        """
        FlatCAMApp.App.log.debug(str(inspect.stack()[1][3]) + "--> OC.get_list()")
        collection_list = []
        iterat = self.store.get_iter_first()
        while iterat is not None:
            obj = self.store[iterat][0]
            collection_list.append(obj)
            iterat = self.store.iter_next(iterat)
        return collection_list

    def get_by_name(self, name):
        """
        Fetches the FlatCAMObj with the given `name`.

        :param name: The name of the object.
        :type name: str
        :return: The requested object or None if no such object.
        :rtype: FlatCAMObj or None
        """
        FlatCAMApp.App.log.debug(str(inspect.stack()[1][3]) + "--> OC.get_by_name()")

        iterat = self.store.get_iter_first()
        while iterat is not None:
            obj = self.store[iterat][0]
            if obj.options["name"] == name:
                return obj
            iterat = self.store.iter_next(iterat)
        return None

    # def change_name(self, old_name, new_name):
    #     """
    #     Changes the name of `FlatCAMObj` named `old_name` to `new_name`.
    #
    #     :param old_name: Name of the object to change.
    #     :type old_name: str
    #     :param new_name: New name.
    #     :type new_name: str
    #     :return: True if name change succeeded, False otherwise. Will fail
    #        if no object with `old_name` is found.
    #     :rtype: bool
    #     """
    #     print inspect.stack()[1][3], "--> OC.change_name()"
    #     iterat = self.store.get_iter_first()
    #     while iterat is not None:
    #         obj = self.store[iterat][0]
    #         if obj.options["name"] == old_name:
    #             obj.options["name"] = new_name
    #             self.store.row_changed(0, iterat)
    #             return True
    #         iterat = self.store.iter_next(iterat)
    #     return False