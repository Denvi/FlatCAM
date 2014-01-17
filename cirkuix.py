import threading
from gi.repository import Gtk, Gdk, GLib, GObject


from matplotlib.figure import Figure
from numpy import arange, sin, pi
from matplotlib.backends.backend_gtk3agg import FigureCanvasGTK3Agg as FigureCanvas
#from matplotlib.backends.backend_gtk3cairo import FigureCanvasGTK3Cairo as FigureCanvas
#from matplotlib.backends.backend_cairo import FigureCanvasCairo as FigureCanvas

from camlib import *


########################################
##            CirkuixObj              ##
########################################
class CirkuixObj:
    """
    Base type of objects handled in Cirkuix. These become interactive
    in the GUI, can be plotted, and their options can be modified
    by the user in their respective forms.
    """

    form_getters = {}

    form_setters = {}

    # Instance of the application to which these are related.
    # The app should set this value.
    # TODO: Move the definitions of form_getters and form_setters
    # TODO: to their respective classes and use app to reference
    # TODO: the builder.
    app = None

    def __init__(self, name):
        self.options = {"name": name}
        self.form_kinds = {"name": "entry_text"}  # Kind of form element for each option
        self.radios = {}  # Name value pairs for radio sets
        self.radios_inv = {}  # Inverse of self.radios
        self.axes = None  # Matplotlib axes
        self.kind = None  # Override with proper name

    def setup_axes(self, figure):
        if self.axes is None:
            self.axes = figure.add_axes([0.05, 0.05, 0.9, 0.9],
                                        label=self.options["name"])
        elif self.axes not in figure.axes:
            figure.add_axes(self.axes)

        self.axes.patch.set_visible(False)  # No background
        self.axes.set_aspect(1)

        return self.axes

    def set_options(self, options):
        for name in options:
            self.options[name] = options[name]
        return

    def to_form(self):
        for option in self.options:
            self.set_form_item(option)

    def read_form(self):
        for option in self.form_getters:
            self.read_form_item(option)

    def build_ui(self):
        """
        Sets up the UI/form for this object.
        @return: None
        @rtype : None
        """

        # Where the UI for this object is drawn
        box_selected = self.app.builder.get_object("box_selected")

        # Remove anything else in the box
        box_children = box_selected.get_children()
        for child in box_children:
            box_selected.remove(child)

        osw = self.app.builder.get_object("offscrwindow_" + self.kind)  # offscreenwindow
        sw = self.app.builder.get_object("sw_" + self.kind)  # scrollwindows
        osw.remove(sw)  # TODO: Is this needed ?
        vp = self.app.builder.get_object("vp_" + self.kind)  # Viewport
        vp.override_background_color(Gtk.StateType.NORMAL, Gdk.RGBA(1, 1, 1, 1))

        # Put in the UI
        box_selected.pack_start(sw, True, True, 0)

        entry_name = self.app.builder.get_object("entry_text_" + self.kind + "_name")
        entry_name.connect("activate", self.app.on_activate_name)
        self.to_form()
        sw.show()

    def set_form_item(self, option):
        fkind = self.form_kinds[option]
        fname = fkind + "_" + self.kind + "_" + option

        if fkind == 'entry_eval' or fkind == 'entry_text':
            self.app.builder.get_object(fname).set_text(str(self.options[option]))
            return
        if fkind == 'cb':
            self.app.builder.get_object(fname).set_active(self.options[option])
            return
        if fkind == 'radio':
            self.app.builder.get_object(self.radios_inv[option][self.options[option]]).set_active(True)
            return
        print "Unknown kind of form item:", fkind

    def read_form_item(self, option):
        fkind = self.form_kinds[option]
        fname = fkind + "_" + self.kind + "_" + option

        if fkind == 'entry_text':
            self.options[option] = self.app.builder(fname).get_text()
            return
        if fkind == 'entry_eval':
            self.options[option] = self.app.get_eval(fname)
            return
        if fkind == 'cb':
            self.options[option] = self.app.builder.get_object(fname).get_active()
            return
        if fkind == 'radio':
            self.options[option] = self.app.get_radio_value(self.radios[option])
            return
        print "Unknown kind of form item:", fkind


class CirkuixGerber(CirkuixObj, Gerber):
    """
    Represents Gerber code.
    """

    def __init__(self, name):
        Gerber.__init__(self)
        CirkuixObj.__init__(self, name)

        self.kind = "gerber"

        # The 'name' is already in self.options
        self.options.update({
            "plot": True,
            "mergepolys": True,
            "multicolored": False,
            "solid": False,
            "isotooldia": 0.4/25.4,
            "cutoutmargin": 0.2,
            "cutoutgapsize": 0.15,
            "gaps": "tb",
            "noncoppermargin": 0.0
        })

        self.form_kinds.update({
            "plot": "cb",
            "mergepolys": "cb",
            "multicolored": "cb",
            "solid": "cb",
            "isotooldia": "entry_eval",
            "cutoutmargin": "entry_eval",
            "cutoutgapsize": "entry_eval",
            "gaps": "radio",
            "noncoppermargin": "entry_eval"
        })

        self.radios = {"gaps": {"rb_2tb": "tb", "rb_2lr": "lr", "rb_4": "4"}}
        self.radios_inv = {"gaps": {"tb": "rb_2tb", "lr": "rb_2lr", "4": "rb_4"}}

    def plot(self, figure):
        self.setup_axes(figure)

        self.create_geometry()

        geometry = None  # TODO: Test if needed
        if self.options["mergepolys"]:
            geometry = self.solid_geometry
        else:
            geometry = self.buffered_paths + \
                        [poly['polygon'] for poly in self.regions] + \
                        self.flash_geometry

        linespec = None  # TODO: Test if needed
        if self.options["multicolored"]:
            linespec = '-'
        else:
            linespec = 'k-'

        for poly in geometry:
            x, y = poly.exterior.xy
            self.axes.plot(x, y, linespec)
            for ints in poly.interiors:
                x, y = ints.coords.xy
                self.axes.plot(x, y, linespec)


class CirkuixExcellon(CirkuixObj, Excellon):
    """
    Represents Excellon code.
    """

    def __init__(self, name):
        Excellon.__init__(self)
        CirkuixObj.__init__(self, name)

        self.kind = "excellon"

        self.options.update({
            "plot": True,
            "solid": False,
            "multicolored": False
        })

        self.form_kinds.update({
            "plot": "cb",
            "solid": "cb",
            "multicolored": "cb"
        })

    def plot(self, figure):
        self.setup_axes(figure)
        self.create_geometry()

        # Plot excellon
        for geo in self.solid_geometry:
            x, y = geo.exterior.coords.xy
            self.axes.plot(x, y, 'r-')
            for ints in geo.interiors:
                x, y = ints.coords.xy
                self.axes.plot(x, y, 'g-')


class CirkuixCNCjob(CirkuixObj, CNCjob):
    """
    Represents G-Code.
    """
    def __init__(self, name, units="in", kind="generic", z_move=0.1,
                 feedrate=3.0, z_cut=-0.002, tooldia=0.0):
        CNCjob.__init__(self, units=units, kind=kind, z_move=z_move,
                        feedrate=feedrate, z_cut=z_cut, tooldia=tooldia)
        CirkuixObj.__init__(self, name)

        self.kind = "cncjob"

        self.options.update({
            "plot": True,
            "solid": False,
            "multicolored": "cb",
            "tooldia": 0.4/25.4  # 0.4mm in inches
        })

        self.form_kinds.update({
            "plot": "cb",
            "solid": "cb",
            "multicolored": "cb",
            "tooldia": "entry_eval"
        })

    def plot(self, figure):
        self.setup_axes(figure)
        self.plot2(self.axes, tooldia=self.options["tooldia"])


class CirkuixGeometry(CirkuixObj, Geometry):
    """
    Geometric object not associated with a specific
    format.
    """

    def __init__(self, name):
        CirkuixObj.__init__(self, name)

        self.kind = "geometry"

        self.options.update({
            "plot": True,
            "solid": False,
            "multicolored": False,
            "cutz": -0.002,
            "travelz": 0.1,
            "feedrate": 5.0
        })

        self.form_kinds.update({
            "plot": "cb",
            "solid": "cb",
            "multicolored": "cb",
            "cutz": "entry_eval",
            "travelz": "entry_eval",
            "feedrate": "entry_eval"
        })

    def plot(self, figure):
        self.setup_axes(figure)

        for geo in self.solid_geometry:

            if type(geo) == Polygon:
                x, y = geo.exterior.coords.xy
                self.axes.plot(x, y, 'r-')
                for ints in geo.interiors:
                    x, y = ints.coords.xy
                    self.axes.plot(x, y, 'r-')
                continue

            if type(geo) == LineString or type(geo) == LinearRing:
                x, y = geo.coords.xy
                self.axes.plot(x, y, 'r-')
                continue


########################################
##                App                 ##
########################################
class App:
    """
    The main application class. The constructor starts the GUI.
    """

    def __init__(self):
        """
        Starts the application and the Gtk.main().
        @return: app
        """

        # Needed to interact with the GUI from other threads.
        #GLib.threads_init()
        GObject.threads_init()
        #Gdk.threads_init()

        ########################################
        ##                GUI                 ##
        ########################################       
        self.gladefile = "cirkuix.ui"
        self.builder = Gtk.Builder()
        self.builder.add_from_file(self.gladefile)
        self.window = self.builder.get_object("window1")
        self.window.set_title("Cirkuix")
        self.position_label = self.builder.get_object("label3")
        self.grid = self.builder.get_object("grid1")
        self.notebook = self.builder.get_object("notebook1")
        self.info_label = self.builder.get_object("label_status")
        self.progress_bar = self.builder.get_object("progressbar")
        self.progress_bar.set_show_text(True)

        ## Event handling ##
        self.builder.connect_signals(self)
        
        ## Make plot area ##
        self.figure = None
        self.axes = None
        self.canvas = None
        self.setup_plot()
        
        self.setup_component_viewer()
        self.setup_component_editor()
        
        ########################################
        ##               DATA                 ##
        ########################################
        self.setup_obj_classes()
        self.stuff = {}    # CirkuixObj's by name
        self.mouse = None  # Mouse coordinates over plot
        
        # What is selected by the user. It is
        # a key if self.stuff
        self.selected_item_name = None

        # For debugging only
        def someThreadFunc(self):
            print "Hello World!"
        t = threading.Thread(target=someThreadFunc, args=(self,))
        t.start()

        ########################################
        ##              START                 ##
        ########################################
        self.window.show_all()
        #Gtk.main()
        
    def setup_plot(self):
        """
        Sets up the main plotting area by creating a matplotlib
        figure in self.canvas, adding axes and configuring them.
        These axes should not be ploted on and are just there to
        display the axes ticks and grid.
        @return: None
        """

        self.figure = Figure(dpi=50)
        self.axes = self.figure.add_axes([0.05, 0.05, 0.9, 0.9], label="base", alpha=0.0)
        self.axes.set_aspect(1)
        #t = arange(0.0,5.0,0.01)
        #s = sin(2*pi*t)
        #self.axes.plot(t,s)
        self.axes.grid()
        self.figure.patch.set_visible(False)
        
        self.canvas = FigureCanvas(self.figure)  # a Gtk.DrawingArea
        self.canvas.set_hexpand(1)
        self.canvas.set_vexpand(1)

        # Events
        self.canvas.mpl_connect('button_press_event', self.on_click_over_plot)
        self.canvas.mpl_connect('motion_notify_event', self.on_mouse_move_over_plot)
        self.canvas.set_can_focus(True)  # For key press
        self.canvas.mpl_connect('key_press_event', self.on_key_over_plot)
        #self.canvas.mpl_connect('scroll_event', self.on_scroll_over_plot)
        
        self.grid.attach(self.canvas, 0, 0, 600, 400)

    def setup_obj_classes(self):
        CirkuixObj.app = self

    def setup_component_viewer(self):
        """
        List or Tree where whatever has been loaded or created is
        displayed.
        @return: None
        """

        self.store = Gtk.ListStore(str)
        self.tree = Gtk.TreeView(self.store)
        #self.list = Gtk.ListBox()
        self.tree_select  = self.tree.get_selection()
        self.signal_id = self.tree_select.connect("changed", self.on_tree_selection_changed)
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Title", renderer, text=0)
        self.tree.append_column(column)
        self.builder.get_object("box_project").pack_start(self.tree, False, False, 1)
        
    def setup_component_editor(self):
        """
        Initial configuration of the component editor. Creates
        a page titled "Selection" on the notebook on the left
        side of the main window.
        @return: None
        """

        box_selected = self.builder.get_object("box_selected")

        # Remove anything else in the box
        box_children = box_selected.get_children()
        for child in box_children:
            box_selected.remove(child)

        box1 = Gtk.Box(Gtk.Orientation.VERTICAL)
        label1 = Gtk.Label("Choose an item from Project")
        box1.pack_start(label1, False, False, 1)
        box_selected.pack_start(box1, True, True, 0)

    def info(self, text):
        """
        Show text on the status bar.
        @return: None
        """

        self.info_label.set_text(text)

    def zoom(self, factor, center=None):
        """
        Zooms the plot by factor around a given
        center point. Takes care of re-drawing.
        @return: None
        """
        xmin, xmax = self.axes.get_xlim()
        ymin, ymax = self.axes.get_ylim()
        width = xmax-xmin
        height = ymax-ymin

        if center is None:
            center = [(xmin+xmax)/2.0, (ymin+ymax)/2.0]

        # For keeping the point at the pointer location
        relx = (xmax-center[0])/width
        rely = (ymax-center[1])/height

        new_width = width/factor
        new_height = height/factor

        xmin = center[0]-new_width*(1-relx)
        xmax = center[0]+new_width*relx
        ymin = center[1]-new_height*(1-rely)
        ymax = center[1]+new_height*rely

        for name in self.stuff:
            self.stuff[name].axes.set_xlim((xmin, xmax))
            self.stuff[name].axes.set_ylim((ymin, ymax))
        self.axes.set_xlim((xmin, xmax))
        self.axes.set_ylim((ymin, ymax))

        self.canvas.queue_draw()

    def build_list(self):
        """
        Clears and re-populates the list of objects in tcurrently
        in the project.
        @return: None
        """
        self.store.clear()
        for key in self.stuff:
            self.store.append([key])

    def get_radio_value(self, radio_set):
        """
        Returns the radio_set[key] if the radiobutton
        whose name is key is active.
        @return: radio_set[key]
        """

        for name in radio_set:
            if self.builder.get_object(name).get_active():
                return radio_set[name]

    def plot_all(self):
        """
        Re-generates all plots from all objects.
        @return: None
        """

        self.clear_plots()
        
        for i in self.stuff:
            self.stuff[i].plot(self.figure)
        
        self.on_zoom_fit(None)
        self.axes.grid()
        self.canvas.queue_draw()
        
    def clear_plots(self):
        """
        Clears self.axes and self.figure.
        @return: None
        """

        self.axes.cla()
        self.figure.clf()
        self.figure.add_axes(self.axes)
        self.canvas.queue_draw()

    def get_eval(self, widget_name):
        """
        Runs eval() on the on the text entry of name 'widget_name'
        and returns the results.
        @param widget_name: Name of Gtk.Entry
        @return: Depends on contents of the entry text.
        """

        value = self.builder.get_object(widget_name).get_text()
        return eval(value)

    def set_list_selection(self, name):
        """
        Marks a given object as selected in the list ob objects
        in the GUI. This selection will in turn trigger
        self.on_tree_selection_changed().
        @param name: Name of the object.
        @return: None
        """

        iter = self.store.get_iter_first()
        while iter is not None and self.store[iter][0] != name:
            iter = self.store.iter_next(iter)
        self.tree_select.unselect_all()
        self.tree_select.select_iter(iter)

        # Need to return False such that GLib.idle_add
        # or .timeout_add do not repear.
        return False

    def new_object(self, kind, name, initialize):
        """
        Creates a new specalized CirkuixObj and attaches it to the application,
        this is, updates the GUI accordingly, any other records and plots it.
        @param kind: Knd of object to create.
        @param name: Name for the object.
        @param initilize: Function to run after the
            object has been created but before attacing it
            to the application. Takes the new object and the
            app as parameters.
        @return: The object requested
        @rtype : CirkuixObj extended
        """

        # Check for existing name
        if name in self.stuff:
            return None

        # Create object
        classdict = {
            "gerber": CirkuixGerber,
            "excellon": CirkuixExcellon,
            "cncjob": CirkuixCNCjob,
            "geometry": CirkuixGeometry
        }
        obj = classdict[kind](name)

        # Initialize as per user request
        # User must take care to implement initialize
        # in a thread-safe way as is is likely that we
        # have been invoked in a separate thread.
        initialize(obj, self)

        # Add to our records
        self.stuff[name] = obj

        # Update GUI list and select it (Thread-safe?)
        self.store.append([name])
        #self.build_list()
        GLib.idle_add(lambda: self.set_list_selection(name))
        # TODO: Gtk.notebook.set_current_page is not known to
        # TODO: return False. Fix this??
        GLib.timeout_add(100, lambda: self.notebook.set_current_page(1))

        # Plot
        # TODO: (Thread-safe?)
        obj.plot(self.figure)
        obj.axes.set_alpha(0.0)
        self.on_zoom_fit(None)

        return obj

    def set_progress_bar(self, percentage, text=""):
        self.progress_bar.set_text(text)
        self.progress_bar.set_fraction(percentage)
        return False

    ########################################
    ##         EVENT HANDLERS             ##
    ########################################
    def on_gerber_generate_noncopper(self, widget):
        name = self.selected_item_name + "_noncopper"

        def geo_init(geo_obj, app_obj):
            assert isinstance(geo_obj, CirkuixGeometry)
            gerber = app_obj.stuff[self.selected_item_name]
            assert isinstance(gerber, CirkuixGerber)
            gerber.read_form()
            bounding_box = gerber.solid_geometry.envelope.buffer(gerber.options["noncoppermargin"])
            non_copper = bounding_box.difference(gerber.solid_geometry)
            geo_obj.solid_geometry = non_copper

        # TODO: Check for None
        self.new_object("geometry", name, geo_init)

    def on_gerber_generate_cutout(self, widget):
        name = self.selected_item_name + "_cutout"

        def geo_init(geo_obj, app_obj):
            # TODO: get from object
            margin = app_obj.get_eval("entry_eval_gerber_cutoutmargin")
            gap_size = app_obj.get_eval("entry_eval_gerber_cutoutgapsize")
            gerber = app_obj.stuff[app_obj.selected_item_name]
            minx, miny, maxx, maxy = gerber.bounds()
            minx -= margin
            maxx += margin
            miny -= margin
            maxy += margin
            midx = 0.5 * (minx + maxx)
            midy = 0.5 * (miny + maxy)
            hgap = 0.5 * gap_size
            pts = [[midx-hgap, maxy],
                   [minx, maxy],
                   [minx, midy+hgap],
                   [minx, midy-hgap],
                   [minx, miny],
                   [midx-hgap, miny],
                   [midx+hgap, miny],
                   [maxx, miny],
                   [maxx, midy-hgap],
                   [maxx, midy+hgap],
                   [maxx, maxy],
                   [midx+hgap, maxy]]
            cases = {"tb": [[pts[0], pts[1], pts[4], pts[5]],
                            [pts[6], pts[7], pts[10], pts[11]]],
                     "lr": [[pts[9], pts[10], pts[1], pts[2]],
                            [pts[3], pts[4], pts[7], pts[8]]],
                     "4": [[pts[0], pts[1], pts[2]],
                           [pts[3], pts[4], pts[5]],
                           [pts[6], pts[7], pts[8]],
                           [pts[9], pts[10], pts[11]]]}
            cuts = cases[app.get_radio_value({"rb_2tb": "tb", "rb_2lr": "lr", "rb_4": "4"})]
            geo_obj.solid_geometry = cascaded_union([LineString(segment) for segment in cuts])

        # TODO: Check for None
        self.new_object("geometry", name, geo_init)

    def on_eval_update(self, widget):
        """
        Modifies the content of a Gtk.Entry by running
        eval() on its contents and puting it back as a
        string.
        """
        # TODO: error handling here
        widget.set_text(str(eval(widget.get_text())))

    def on_generate_isolation(self, widget):
        print "Generating Isolation Geometry:"
        iso_name = self.selected_item_name + "_iso"

        def iso_init(geo_obj, app_obj):
            # TODO: Object must be updated on form change and the options
            # TODO: read from the object.
            tooldia = app_obj.get_eval("entry_eval_gerber_isotooldia")
            geo_obj.solid_geometry = self.stuff[self.selected_item_name].isolation_geometry(tooldia/2.0)

        # TODO: Do something if this is None. Offer changing name?
        self.new_object("geometry", iso_name, iso_init)

        
    def on_generate_cncjob(self, widget):
        print "Generating CNC job"

        job_name = self.selected_item_name + "_cnc"

        def job_init(job_obj, app_obj):
            # TODO: Object must be updated on form change and the options
            # TODO: read from the object.
            z_cut = app_obj.get_eval("entry_eval_geometry_cutz")
            z_move = app_obj.get_eval("entry_eval_geometry_travelz")
            feedrate = app_obj.get_eval("entry_eval_geometry_feedrate")

            geometry = app_obj.stuff[app_obj.selected_item_name]
            assert isinstance(job_obj, CirkuixCNCjob)
            job_obj.z_cut = z_cut
            job_obj.z_move = z_move
            job_obj.feedrate = feedrate
            job_obj.generate_from_geometry(geometry.solid_geometry)
            job_obj.gcode_parse()
            job_obj.create_geometry()

        self.new_object("cncjob", job_name, job_init)

    def on_cncjob_tooldia_activate(self, widget):
        job = self.stuff[self.selected_item_name]
        tooldia = self.get_eval("entry_eval_cncjob_tooldia")
        job.tooldia = tooldia
        print "Changing tool diameter to:", tooldia

    def on_cncjob_exportgcode(self, widget):
        def on_success(self, filename):
            cncjob = self.stuff[self.selected_item_name]
            f = open(filename, 'w')
            f.write(cncjob.gcode)
            f.close()
            print "Saved to:", filename
        self.file_chooser_save_action(on_success)

    def on_delete(self, widget):
        self.stuff.pop(self.selected_item_name)
        
        #self.tree.get_selection().disconnect(self.signal_id)
        self.build_list()  # Update the items list
        #self.signal_id = self.tree.get_selection().connect(
        #                     "changed", self.on_tree_selection_changed)
                             
        self.plot_all()
        #self.notebook.set_current_page(1)
                             
    def on_replot(self, widget):
        self.plot_all()
    
    def on_clear_plots(self, widget):
        self.clear_plots()
        
    def on_activate_name(self, entry):
        """
        Hitting 'Enter' after changing the name of an item
        updates the item dictionary and re-builds the item list.
        """

        # Disconnect event listener
        self.tree.get_selection().disconnect(self.signal_id)

        new_name = entry.get_text()  # Get from form
        self.stuff[new_name] = self.stuff.pop(self.selected_item_name)  # Update dictionary
        self.stuff[new_name].options["name"] = new_name  # update object
        self.info('Name change: ' + self.selected_item_name + " to " + new_name)
        self.selected_item_name = new_name  # Update selection name

        self.build_list()  # Update the items list

        # Reconnect event listener
        self.signal_id = self.tree.get_selection().connect(
                             "changed", self.on_tree_selection_changed)
                             
    def on_tree_selection_changed(self, selection):
        model, treeiter = selection.get_selected()

        if treeiter is not None:
            print "You selected", model[treeiter][0]
            self.selected_item_name = model[treeiter][0]
            #self.stuff[self.selected_item_name].build_ui()
            GLib.timeout_add(100, lambda: self.stuff[self.selected_item_name].build_ui())
        else:
            print "Nothing selected"
            self.selected_item_name = None
            self.setup_component_editor()

    def on_file_new(self, param):
        print "File->New not implemented yet."

    def on_filequit(self, param):
        print "quit from menu"
        self.window.destroy()
        Gtk.main_quit()
    
    def on_closewindow(self, param):
        print "quit from X"
        self.window.destroy()
        Gtk.main_quit()
    
    def file_chooser_action(self, on_success):
        '''
        Opens the file chooser and runs on_success on a separate thread
        upon completion of valid file choice.
        '''
        dialog = Gtk.FileChooserDialog("Please choose a file", self.window,
            Gtk.FileChooserAction.OPEN,
            (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
             Gtk.STOCK_OPEN, Gtk.ResponseType.OK))
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            filename = dialog.get_filename()
            dialog.destroy()
            t = threading.Thread(target=on_success, args=(self, filename))
            t.daemon = True
            t.start()
            #on_success(self, filename)
        elif response == Gtk.ResponseType.CANCEL:
            print("Cancel clicked")
            dialog.destroy()    
    
    def file_chooser_save_action(self, on_success):
        """
        Opens the file chooser and runs on_success
        upon completion of valid file choice.
        """
        dialog = Gtk.FileChooserDialog("Save file", self.window,
            Gtk.FileChooserAction.SAVE,
            (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
             Gtk.STOCK_SAVE, Gtk.ResponseType.OK))
        dialog.set_current_name("Untitled")
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            filename = dialog.get_filename()
            dialog.destroy()
            on_success(self, filename)
        elif response == Gtk.ResponseType.CANCEL:
            print("Cancel clicked")
            dialog.destroy()
    
    def on_fileopengerber(self, param):

        # IMPORTANT: on_success will run on a separate thread. Use
        # GLib.idle_add(function, **kwargs) to launch actions that will
        # updata the GUI.
        def on_success(app_obj, filename):
            assert isinstance(app_obj, App)
            GLib.idle_add(lambda: app_obj.set_progress_bar(0.1, "Opening Gerber ..."))

            def obj_init(gerber_obj, app_obj):
                GLib.idle_add(lambda: app_obj.set_progress_bar(0.2, "Parsing ..."))
                gerber_obj.parse_file(filename)
                GLib.idle_add(lambda: app_obj.set_progress_bar(0.6, "Plotting ..."))

            name = filename.split('/')[-1].split('\\')[-1]
            app_obj.new_object("gerber", name, obj_init)

            GLib.idle_add(lambda: app_obj.set_progress_bar(1.0, "Done!"))
            GLib.timeout_add_seconds(1, lambda: app_obj.set_progress_bar(0.0, ""))

        # on_success gets run on a separate thread
        self.file_chooser_action(on_success)
    
    def on_fileopenexcellon(self, param):

        # IMPORTANT: on_success will run on a separate thread. Use
        # GLib.idle_add(function, **kwargs) to launch actions that will
        # updata the GUI.
        def on_success(app_obj, filename):
            assert isinstance(app_obj, App)
            GLib.idle_add(lambda: app_obj.set_progress_bar(0.1, "Opening Excellon ..."))

            def obj_init(excellon_obj, app_obj):
                GLib.idle_add(lambda: app_obj.set_progress_bar(0.2, "Parsing ..."))
                excellon_obj.parse_file(filename)
                GLib.idle_add(lambda: app_obj.set_progress_bar(0.6, "Plotting ..."))

            name = filename.split('/')[-1].split('\\')[-1]
            app_obj.new_object("excellon", name, obj_init)

            GLib.idle_add(lambda: app_obj.set_progress_bar(1.0, "Done!"))
            GLib.timeout_add_seconds(1, lambda: app_obj.set_progress_bar(0.0, ""))

        # on_success gets run on a separate thread
        self.file_chooser_action(on_success)
    
    def on_fileopengcode(self, param):

        # IMPORTANT: on_success will run on a separate thread. Use
        # GLib.idle_add(function, **kwargs) to launch actions that will
        # updata the GUI.
        def on_success(app_obj, filename):
            assert isinstance(app_obj, App)

            def obj_init(job_obj, app_obj):
                assert isinstance(app_obj, App)
                GLib.idle_add(lambda: app_obj.set_progress_bar(0.1, "Opening G-Code ..."))

                f = open(filename)
                gcode = f.read()
                f.close()

                job_obj.gcode = gcode

                GLib.idle_add(lambda: app_obj.set_progress_bar(0.2, "Parsing ..."))
                job_obj.gcode_parse()

                GLib.idle_add(lambda: app_obj.set_progress_bar(0.6, "Creating geometry ..."))
                job_obj.create_geometry()

                GLib.idle_add(lambda: app_obj.set_progress_bar(0.6, "Plotting ..."))

            name = filename.split('/')[-1].split('\\')[-1]
            app_obj.new_object("cncjob", name, obj_init)

            GLib.idle_add(lambda: app_obj.set_progress_bar(1.0, "Done!"))
            GLib.timeout_add_seconds(1, lambda: app_obj.set_progress_bar(0.0, ""))

        # on_success gets run on a separate thread
        self.file_chooser_action(on_success)
        
    def on_mouse_move_over_plot(self, event):
        try: # May fail in case mouse not within axes
            self.position_label.set_label("X: %.4f   Y: %.4f"%(
                                         event.xdata, event.ydata))
            self.mouse = [event.xdata, event.ydata]
        except:
            self.position_label.set_label("")
            self.mouse = None
        
    def on_click_over_plot(self, event):
        # For key presses
        self.canvas.grab_focus()

        try:
            print 'button=%d, x=%d, y=%d, xdata=%f, ydata=%f'%(
            event.button, event.x, event.y, event.xdata, event.ydata)
        except:
            print "Outside plot!"
        
    def on_zoom_in(self, event):
        self.zoom(1.5)
        return
        
    def on_zoom_out(self, event):
        self.zoom(1/1.5)
         
    def on_zoom_fit(self, event):
        xmin, ymin, xmax, ymax = get_bounds(self.stuff)
        width = xmax-xmin
        height = ymax-ymin
        r = width/height
        
        Fw, Fh = self.canvas.get_width_height()
        Fr = float(Fw)/Fh
        print "Window aspect ratio:", Fr
        print "Data aspect ratio:", r
        
        #self.axes.set_xlim((xmin-0.05*width, xmax+0.05*width))
        #self.axes.set_ylim((ymin-0.05*height, ymax+0.05*height))
        
        if r > Fr:
            #self.axes.set_xlim((xmin-0.05*width, xmax+0.05*width))
            xmin -= 0.05*width
            xmax += 0.05*width
            ycenter = (ymin+ymax)/2.0
            newheight = height*r/Fr
            ymin = ycenter-newheight/2.0
            ymax = ycenter+newheight/2.0
            #self.axes.set_ylim((ycenter-newheight/2.0, ycenter+newheight/2.0))
        else:
            #self.axes.set_ylim((ymin-0.05*height, ymax+0.05*height))
            ymin -= 0.05*height
            ymax += 0.05*height
            xcenter = (xmax+ymin)/2.0
            newwidth = width*Fr/r
            xmin = xcenter-newwidth/2.0
            xmax = xcenter+newwidth/2.0
            #self.axes.set_xlim((xcenter-newwidth/2.0, xcenter+newwidth/2.0))

        for name in self.stuff:
            self.stuff[name].axes.set_xlim((xmin, xmax))
            self.stuff[name].axes.set_ylim((ymin, ymax))
        self.axes.set_xlim((xmin, xmax))
        self.axes.set_ylim((ymin, ymax))

        self.canvas.queue_draw()
        return
        
    # def on_scroll_over_plot(self, event):
    #     print "Scroll"
    #     center = [event.xdata, event.ydata]
    #     if sign(event.step):
    #         self.zoom(1.5, center=center)
    #     else:
    #         self.zoom(1/1.5, center=center)
    #
    # def on_window_scroll(self, event):
    #     print "Scroll"
        
    def on_key_over_plot(self, event):
        print 'you pressed', event.key, event.xdata, event.ydata
        
        if event.key == '1': # 1
            self.on_zoom_fit(None)
            return
            
        if event.key == '2': # 2
            self.zoom(1/1.5, self.mouse)
            return
            
        if event.key == '3': # 3
            self.zoom(1.5, self.mouse)
            return

app = App()
Gtk.main()
