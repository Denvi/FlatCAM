# from PyQt4.QtCore import QModelIndex
from FlatCAMObj import *
import inspect  # TODO: Remove
import FlatCAMApp
from PyQt4 import Qt, QtGui, QtCore


class KeySensitiveListView(QtGui.QTreeView):
    """
    QtGui.QListView extended to emit a signal on key press.
    """

    def __init__(self, parent=None):
        super(KeySensitiveListView, self).__init__(parent)
        self.setHeaderHidden(True)
        self.setEditTriggers(QtGui.QTreeView.SelectedClicked)
        # self.setRootIsDecorated(False)
        # self.setExpandsOnDoubleClick(False)

    keyPressed = QtCore.pyqtSignal(int)

    def keyPressEvent(self, event):
        super(KeySensitiveListView, self).keyPressEvent(event)
        self.keyPressed.emit(event.key())


class TreeItem:
    """
    Item of a tree model
    """

    def __init__(self, data, icon=None, obj=None, parent_item=None):

        self.parent_item = parent_item
        self.item_data = data  # Columns string data
        self.icon = icon  # Decoration
        self.obj = obj  # FlatCAMObj

        self.child_items = []

        if parent_item:
            parent_item.append_child(self)

    def append_child(self, item):
        self.child_items.append(item)
        item.set_parent_item(self)

    def remove_child(self, item):
        child = self.child_items.pop(self.child_items.index(item))
        child.obj.shapes.clear(True)
        del child

    def remove_children(self):
        for child in self.child_items:
            child.obj.shapes.clear()
            del child

        self.child_items = []

    def child(self, row):
        return self.child_items[row]

    def child_count(self):
        return len(self.child_items)

    def column_count(self):
        return len(self.item_data)

    def data(self, column):
        return self.item_data[column]

    def row(self):
        return self.parent_item.child_items.index(self)

    def set_parent_item(self, parent_item):
        self.parent_item = parent_item

    def __del__(self):
        del self.obj
        del self.icon


class ObjectCollection(QtCore.QAbstractItemModel):
    """
    Object storage and management.
    """

    groups = [
        ("gerber", "Gerber"),
        ("excellon", "Excellon"),
        ("geometry", "Geometry"),
        ("cncjob", "CNC Job")
    ]

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

    root_item = None
    app = None

    def __init__(self, parent=None):

        QtCore.QAbstractItemModel.__init__(self)

        ### Icons for the list view
        self.icons = {}
        for kind in ObjectCollection.icon_files:
            self.icons[kind] = QtGui.QPixmap(ObjectCollection.icon_files[kind])

        # Create root tree view item
        self.root_item = TreeItem(["root"])

        # Create group items
        self.group_items = {}
        for kind, title in ObjectCollection.groups:
            item = TreeItem([title], self.icons[kind])
            self.group_items[kind] = item
            self.root_item.append_child(item)

        # Create test sub-items
        # for i in self.root_item.m_child_items:
        #     print i.data(0)
        #     i.append_child(TreeItem(["empty"]))

        ### Data ###
        self.checked_indexes = []

        # Names of objects that are expected to become available.
        # For example, when the creation of a new object will run
        # in the background and will complete some time in the
        # future. This is a way to reserve the name and to let other
        # tasks know that they have to wait until available.
        self.promises = set()

        ### View
        self.view = KeySensitiveListView()
        self.view.setSelectionMode(Qt.QAbstractItemView.ExtendedSelection)
        self.view.setModel(self)
        self.view.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)

        self.click_modifier = None

        ## GUI Events
        self.view.selectionModel().selectionChanged.connect(self.on_list_selection_change)
        self.view.activated.connect(self.on_item_activated)
        self.view.keyPressed.connect(self.on_key)
        self.view.clicked.connect(self.on_mouse_down)
        self.view.customContextMenuRequested.connect(self.on_menu_request)

    def promise(self, obj_name):
        FlatCAMApp.App.log.debug("Object %s has been promised." % obj_name)
        self.promises.add(obj_name)

    def has_promises(self):
        return len(self.promises) > 0

    def on_key(self, key):

        # Delete
        active = self.get_active()
        if key == QtCore.Qt.Key_Delete and active:
            # Delete via the application to
            # ensure cleanup of the GUI
            active.app.on_delete()

        if key == QtCore.Qt.Key_Space:
            self.get_active().ui.plot_cb.toggle()
            return

    def on_mouse_down(self, event):
        FlatCAMApp.App.log.debug("Mouse button pressed on list")

    def on_menu_request(self, pos):

        sel = len(self.view.selectedIndexes()) > 0
        self.app.ui.menuprojectenable.setEnabled(sel)
        self.app.ui.menuprojectdisable.setEnabled(sel)
        self.app.ui.menuprojectdelete.setEnabled(sel)

        if sel:
            self.app.ui.menuprojectgeneratecnc.setVisible(True)
            for obj in self.get_selected():
                if type(obj) != FlatCAMGeometry:
                    self.app.ui.menuprojectgeneratecnc.setVisible(False)
        else:
            self.app.ui.menuprojectgeneratecnc.setVisible(False)

        self.app.ui.menuproject.popup(self.view.mapToGlobal(pos))

    def index(self, row, column=0, parent=None, *args, **kwargs):
        if not self.hasIndex(row, column, parent):
            return QtCore.QModelIndex()

        if not parent.isValid():
            parent_item = self.root_item
        else:
            parent_item = parent.internalPointer()

        child_item = parent_item.child(row)

        if child_item:
            return self.createIndex(row, column, child_item)
        else:
            return QtCore.QModelIndex()

    def parent(self, index=None):
        if not index.isValid():
            return QtCore.QModelIndex()

        parent_item = index.internalPointer().parent_item

        if parent_item == self.root_item:
            return QtCore.QModelIndex()

        return self.createIndex(parent_item.row(), 0, parent_item)

    def rowCount(self, index=None, *args, **kwargs):
        if index.column() > 0:
            return 0

        if not index.isValid():
            parent_item = self.root_item
        else:
            parent_item = index.internalPointer()

        return parent_item.child_count()

    def columnCount(self, index=None, *args, **kwargs):
        if index.isValid():
            return index.internalPointer().column_count()
        else:
            return self.root_item.column_count()

    def data(self, index, role=None):
        if not index.isValid():
            return QtCore.QVariant()

        if role in [Qt.Qt.DisplayRole, Qt.Qt.EditRole]:
            obj = index.internalPointer().obj
            if obj:
                return obj.options["name"]
            else:
                return index.internalPointer().data(index.column())

        if role == Qt.Qt.ForegroundRole:
            obj = index.internalPointer().obj
            if obj:
                return Qt.QBrush(QtCore.Qt.black) if obj.options["plot"] else Qt.QBrush(QtCore.Qt.darkGray)
            else:
                return index.internalPointer().data(index.column())

        elif role == Qt.Qt.DecorationRole:
            icon = index.internalPointer().icon
            if icon:
                return icon
            else:
                return Qt.QPixmap()
        else:
            return QtCore.QVariant()

    def setData(self, index, data, role=None):
        if index.isValid():
            obj = index.internalPointer().obj
            if obj:
                obj.options["name"] = data.toString()
                obj.build_ui()

    def flags(self, index):
        if not index.isValid():
            return 0

        # Prevent groups from selection
        if not index.internalPointer().obj:
            return Qt.Qt.ItemIsEnabled
        else:
            return Qt.Qt.ItemIsEnabled | Qt.Qt.ItemIsSelectable | Qt.Qt.ItemIsEditable

        return QtCore.QAbstractItemModel.flags(self, index)

    # def data(self, index, role=Qt.Qt.DisplayRole):
    #     if not index.isValid() or not 0 <= index.row() < self.rowCount():
    #         return QtCore.QVariant()
    #     row = index.row()
    #     if role == Qt.Qt.DisplayRole:
    #         return self.object_list[row].options["name"]
    #     if role == Qt.Qt.DecorationRole:
    #         return self.icons[self.object_list[row].kind]
    #     # if role == Qt.Qt.CheckStateRole:
    #     #     if row in self.checked_indexes:
    #     #         return Qt.Qt.Checked
    #     #     else:
    #     #         return Qt.Qt.Unchecked

    def print_list(self):
        for obj in self.get_list():
            print obj

    def append(self, obj, active=False):
        FlatCAMApp.App.log.debug(str(inspect.stack()[1][3]) + " --> OC.append()")

        name = obj.options["name"]

        # Check promises and clear if exists
        if name in self.promises:
            self.promises.remove(name)
            FlatCAMApp.App.log.debug("Promised object %s became available." % name)
            FlatCAMApp.App.log.debug("%d promised objects remaining." % len(self.promises))

        # Prevent same name
        while name in self.get_names():
            ## Create a new name
            # Ends with number?
            FlatCAMApp.App.log.debug("new_object(): Object name (%s) exists, changing." % name)
            match = re.search(r'(.*[^\d])?(\d+)$', name)
            if match:  # Yes: Increment the number!
                base = match.group(1) or ''
                num = int(match.group(2))
                name = base + str(num + 1)
            else:  # No: add a number!
                name += "_1"
        obj.options["name"] = name

        obj.set_ui(obj.ui_type())

        # Required before appending (Qt MVC)
        group = self.group_items[obj.kind]
        group_index = self.index(group.row(), 0, Qt.QModelIndex())
        self.beginInsertRows(group_index, group.child_count(), group.child_count())

        # Append new item
        obj.item = TreeItem(None, self.icons[obj.kind], obj, group)

        # Required after appending (Qt MVC)
        self.endInsertRows()

        # Expand group
        if group.child_count() is 1:
            self.view.setExpanded(group_index, True)

    def get_names(self):
        """
        Gets a list of the names of all objects in the collection.

        :return: List of names.
        :rtype: list
        """

        FlatCAMApp.App.log.debug(str(inspect.stack()[1][3]) + " --> OC.get_names()")
        return [x.options['name'] for x in self.get_list()]

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

        # for obj in self.object_list:
        for obj in self.get_list():
            try:
                gxmin, gymin, gxmax, gymax = obj.bounds()
                xmin = min([xmin, gxmin])
                ymin = min([ymin, gymin])
                xmax = max([xmax, gxmax])
                ymax = max([ymax, gymax])
            except:
                FlatCAMApp.App.log.warning("DEV WARNING: Tried to get bounds of empty geometry.")

        return [xmin, ymin, xmax, ymax]

    def get_by_name(self, name):
        """
        Fetches the FlatCAMObj with the given `name`.

        :param name: The name of the object.
        :type name: str
        :return: The requested object or None if no such object.
        :rtype: FlatCAMObj or None
        """
        FlatCAMApp.App.log.debug(str(inspect.stack()[1][3]) + "--> OC.get_by_name()")

        for obj in self.get_list():
            if obj.options['name'] == name:
                return obj
        return None

    def delete_active(self):
        selections = self.view.selectedIndexes()
        if len(selections) == 0:
            return

        active = selections[0].internalPointer()
        group = active.parent_item

        self.beginRemoveRows(self.index(group.row(), 0, Qt.QModelIndex()), active.row(), active.row())

        group.remove_child(active)

        self.endRemoveRows()

    def get_active(self):
        """
        Returns the active object or None

        :return: FlatCAMObj or None
        """
        selections = self.view.selectedIndexes()
        if len(selections) == 0:
            return None

        return selections[0].internalPointer().obj

    def get_selected(self):
        """
        Returns list of objects selected in the view.

        :return: List of objects
        """
        return [sel.internalPointer().obj for sel in self.view.selectedIndexes()]

    def get_non_selected(self):
        """
        Returns list of objects non-selected in the view.

        :return: List of objects
        """

        l = self.get_list()

        for sel in self.get_selected():
            l.remove(sel)

        return l

    def set_active(self, name):
        """
        Selects object by name from the project list. This triggers the
        list_selection_changed event and call on_list_selection_changed.

        :param name: Name of the FlatCAM Object
        :return: None
        """
        obj = self.get_by_name(name)
        item = obj.item
        group = self.group_items[obj.kind]

        group_index = self.index(group.row(), 0, Qt.QModelIndex())
        item_index = self.index(item.row(), 0, group_index)

        self.view.selectionModel().select(item_index, QtGui.QItemSelectionModel.Select)

    def set_inactive(self, name):
        """
        Unselect object by name from the project list. This triggers the
        list_selection_changed event and call on_list_selection_changed.

        :param name: Name of the FlatCAM Object
        :return: None
        """
        obj = self.get_by_name(name)
        item = obj.item
        group = self.group_items[obj.kind]

        group_index = self.index(group.row(), 0, Qt.QModelIndex())
        item_index = self.index(item.row(), 0, group_index)

        self.view.selectionModel().select(item_index, QtGui.QItemSelectionModel.Deselect)

    def set_all_inactive(self):
        """
        Unselect all objects from the project list. This triggers the
        list_selection_changed event and call on_list_selection_changed.

        :return: None
        """
        for name in self.get_names():
            self.set_inactive(name)

    def on_list_selection_change(self, current, previous):
        FlatCAMApp.App.log.debug("on_list_selection_change()")
        FlatCAMApp.App.log.debug("Current: %s, Previous %s" % (str(current), str(previous)))

        try:
            obj = current.indexes()[0].internalPointer().obj
        except IndexError:
            FlatCAMApp.App.log.debug("on_list_selection_change(): Index Error (Nothing selected?)")

            try:
                self.app.ui.selected_scroll_area.takeWidget()
            except:
                FlatCAMApp.App.log.debug("Nothing to remove")

            self.app.setup_component_editor()
            return

        if obj:
            obj.build_ui()

    def on_item_activated(self, index):
        """
        Double-click or Enter on item.

        :param index: Index of the item in the list.
        :return: None
        """
        index.internalPointer().obj.build_ui()

    def delete_all(self):
        FlatCAMApp.App.log.debug(str(inspect.stack()[1][3]) + "--> OC.delete_all()")

        self.beginResetModel()

        self.checked_indexes = []
        for group in self.root_item.child_items:
            group.remove_children()

        self.endResetModel()

        self.app.plotcanvas.shape_collection.redraw()
        self.app.dblsidedtool.reset_fields()

    def get_list(self):
        obj_list = []
        for group in self.root_item.child_items:
            for item in group.child_items:
                obj_list.append(item.obj)

        return obj_list

    def update_view(self):
        self.dataChanged.emit(Qt.QModelIndex(), Qt.QModelIndex())
