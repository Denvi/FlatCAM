
import threading
from gi.repository import Gtk
#from gi.repository import Gdk
from gi.repository import GLib

from matplotlib.figure import Figure
from numpy import arange, sin, pi
from matplotlib.backends.backend_gtk3agg import FigureCanvasGTK3Agg as FigureCanvas
#from matplotlib.backends.backend_gtk3cairo import FigureCanvasGTK3Cairo as FigureCanvas
#from matplotlib.backends.backend_cairo import FigureCanvasCairo as FigureCanvas

from camlib import *

class CirkuixObj:
    def __init__(self, name, kind):
        self.name = name
        self.kind = kind  # TODO: Probably not needed
        self.axes = None  # Matplotlib axes
        self.options = {}

    def setup_axes(self, figure):
        if self.axes is None:
            self.axes = figure.add_axes([0.05, 0.05, 0.9, 0.9], label=self.name)
        elif self.axes not in figure.axes:
            figure.add_axes(self.axes)

        self.axes.patch.set_visible(False)  # No background
        self.axes.set_aspect(1)

        return self.axes

    def set_options(self, options):
        for name in options:
            self.options[name] = options[name]
        return


class CirkuixGerber(CirkuixObj, Gerber):
    def __init__(self, name):
        Gerber.__init__(self)
        CirkuixObj.__init__(self, name, "gerber")

        self.options = {
            "plot": True,
            "mergepolys": True,
            "multicolored": False,
            "solid": False,
            "isotooldia": 0.4/25.4,
            "cutoutmargin": 0.2,
            "cutoutgapsize": 0.15,
            "gaps": "tb"
        }

    def plot(self, figure):
        self.setup_axes(figure)

        self.create_geometry()

        geometry = None
        if self.options["mergepolys"]:
            geometry = self.solid_geometry
        else:
            geometry = self.buffered_paths + \
                        [poly['polygon'] for poly in self.regions] + \
                        self.flash_geometry

        linespec = None
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
    def __init__(self, name):
        Excellon.__init__(self)
        CirkuixObj.__init__(self, name, "excellon")

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
    def __init__(self, name, units="in", kind="generic", z_move=0.1,
                 feedrate=3.0, z_cut=-0.002, tooldia=0.0):
        CNCjob.__init__(self, units=units, kind=kind, z_move=z_move,
                        feedrate=feedrate, z_cut=z_cut, tooldia=tooldia)
        CirkuixObj.__init__(self, name, "cncjob")

    def plot(self, figure):
        self.setup_axes(figure)

        self.plot2(self.axes)


class CirkuixGeometry(CirkuixObj, Geometry):
    def __init__(self, name):
        CirkuixObj.__init__(self, name, "geometry")
        self.options = {"plot": True,
                        "solid": False,
                        "multicolored": False}

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


class App:
    def __init__(self):
        # Needed to interact with the GUI from other threads.
        GLib.threads_init()

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
        self.plot_setup()
        
        self.setup_component_viewer()
        self.setup_component_editor()
        
        ########################################
        ##               DATA                 ##
        ########################################
        self.stuff = {}  # CirkuixObj's by name
        
        self.mouse = None
        
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
        Gtk.main()
        
    def plot_setup(self):
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
        
        ########################################
        ##              EVENTS                ##
        ########################################
        self.canvas.mpl_connect('button_press_event', self.on_click_over_plot)
        self.canvas.mpl_connect('motion_notify_event', self.on_mouse_move_over_plot)
        self.canvas.set_can_focus(True)  # For key press
        self.canvas.mpl_connect('key_press_event', self.on_key_over_plot)
        #self.canvas.mpl_connect('scroll_event', self.on_scroll_over_plot)
        
        self.grid.attach(self.canvas, 0, 0, 600, 400)

    def info(self, text):
        """
        Show text on the status bar.
        """
        self.info_label.set_text(text)

    def zoom(self, factor, center=None):
        """
        Zooms the plot by factor around a given
        center point. Takes care of re-drawing.
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
        
        #self.axes.set_xlim((center[0]-new_width*(1-relx), center[0]+new_width*relx))
        #self.axes.set_ylim((center[1]-new_height*(1-rely), center[1]+new_height*rely))
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

    # def plot_gerber(self, gerber):
    #     gerber.create_geometry()
    #
    #     # Options
    #     mergepolys = self.builder.get_object("cb_mergepolys").get_active()
    #     multicolored = self.builder.get_object("cb_multicolored").get_active()
    #
    #     geometry = None
    #     if mergepolys:
    #         geometry = gerber.solid_geometry
    #     else:
    #         geometry = gerber.buffered_paths + \
    #                    [poly['polygon'] for poly in gerber.regions] + \
    #                    gerber.flash_geometry
    #
    #     linespec = None
    #     if multicolored:
    #         linespec = '-'
    #     else:
    #         linespec = 'k-'
    #
    #     for poly in geometry:
    #         x, y = poly.exterior.xy
    #         #a.plot(x, y)
    #         self.axes.plot(x, y, linespec)
    #         for ints in poly.interiors:
    #             x, y = ints.coords.xy
    #             self.axes.plot(x, y, linespec)
    #
    #     self.canvas.queue_draw()
    #
    # def plot_excellon(self, excellon):
    #     excellon.create_geometry()
    #
    #     # Plot excellon
    #     for geo in excellon.solid_geometry:
    #         x, y = geo.exterior.coords.xy
    #         self.axes.plot(x, y, 'r-')
    #         for ints in geo.interiors:
    #             x, y = ints.coords.xy
    #             self.axes.plot(x, y, 'g-')
    #
    #     self.canvas.queue_draw()
    #
    # def plot_cncjob(self, job):
    #     #job.gcode_parse()
    #     job.plot2(self.axes)
    #     self.canvas.queue_draw()
    #
    # def plot_geometry(self, geometry):
    #     for geo in geometry.solid_geometry:
    #
    #         if type(geo) == Polygon:
    #             x, y = geo.exterior.coords.xy
    #             self.axes.plot(x, y, 'r-')
    #             for ints in geo.interiors:
    #                 x, y = ints.coords.xy
    #                 self.axes.plot(x, y, 'r-')
    #             continue
    #
    #         if type(geo) == LineString or type(geo) == LinearRing:
    #             x, y = geo.coords.xy
    #             self.axes.plot(x, y, 'r-')
    #             continue
    #
    #     self.canvas.queue_draw()

    def setup_component_viewer(self):
        """
        List or Tree where whatever has been loaded or created is
        displayed.
        """
        self.store = Gtk.ListStore(str)
        self.tree = Gtk.TreeView(self.store)
        #self.list = Gtk.ListBox()
        self.tree_select  = self.tree.get_selection()
        self.signal_id = self.tree_select.connect("changed", self.on_tree_selection_changed)
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Title", renderer, text=0)
        self.tree.append_column(column)
        self.builder.get_object("notebook1").append_page(self.tree, Gtk.Label("Project"))
        
    def setup_component_editor(self):
        box1 = Gtk.Box(Gtk.Orientation.VERTICAL)
        label1 = Gtk.Label("Choose an item from Project")
        box1.pack_start(label1, False, False, 1)
        self.builder.get_object("notebook1").append_page(box1, Gtk.Label("Selection"))
        
    def build_list(self):
        self.store.clear()
        for key in self.stuff:
            self.store.append([key])
        
    def build_gerber_ui(self):
        print "build_gerber_ui()"
        osw = self.builder.get_object("offscrwindow_gerber")
        box1 = self.builder.get_object("box_gerber")
        osw.remove(box1)
        self.notebook.append_page(box1, Gtk.Label("Selection"))
        gerber = self.stuff[self.selected_item_name]
        entry_name = self.builder.get_object("entry_gerbername")
        entry_name.set_text(self.selected_item_name)
        entry_name.connect("activate", self.on_activate_name)
        if self.selected_item_name is not None:
            self.selected_object_to_form()
        box1.show()
        
    def build_excellon_ui(self):
        print "build_excellon_ui()"
        osw = self.builder.get_object("offscrwindow_excellon")
        box1 = self.builder.get_object("box_excellon")
        osw.remove(box1)
        self.notebook.append_page(box1, Gtk.Label("Selection"))
        entry_name = self.builder.get_object("entry_excellonname")
        entry_name.set_text(self.selected_item_name)
        entry_name.connect("activate", self.on_activate_name)
        if self.selected_item_name is not None:
            self.selected_object_to_form()
        box1.show()
        
    def build_cncjob_ui(self):
        print "build_cncjob_ui()"
        osw = self.builder.get_object("offscrwindow_cncjob")
        box1 = self.builder.get_object("box_cncjob")
        osw.remove(box1)
        self.notebook.append_page(box1, Gtk.Label("Selection"))
        entry_name = self.builder.get_object("entry_cncjobname")
        entry_name.set_text(self.selected_item_name)
        entry_name.connect("activate", self.on_activate_name)
        if self.selected_item_name is not None:
            self.selected_object_to_form()
        box1.show()
        
    def build_geometry_ui(self):
        print "build_geometry_ui()"
        osw = self.builder.get_object("offscrwindow_geometry")
        box1 = self.builder.get_object("box_geometry")
        osw.remove(box1)
        self.notebook.append_page(box1, Gtk.Label("Selection"))
        entry_name = self.builder.get_object("entry_geometryname")
        entry_name.set_text(self.selected_item_name)
        entry_name.connect("activate", self.on_activate_name)
        if self.selected_item_name is not None:
            self.selected_object_to_form()
        box1.show()

    def get_radio_value(self, radio_set):
        """
        Returns the radio_set[key] if the radiobutton
        whose name is key is active.
        """
        for name in radio_set:
            if self.builder.get_object(name).get_active():
                return radio_set[name]

    def selected_object_to_form(self):
        print "Object --> Form"
        obj = self.stuff[self.selected_item_name]

        if obj.__class__.__name__ == 'CirkuixGerber':
            setters = {
                "plot": self.builder.get_object("cb_gerber_plot").set_active,
                "mergepolys": self.builder.get_object("cb_gerber_mergepolys").set_active,
                "solid": self.builder.get_object("cb_gerber_solid").set_active,
                "multicolored": self.builder.get_object("cb_gerber_multicolored").set_active,
                "isotooldia": lambda x: self.builder.get_object("entry_gerberisotooldia").set_text(str(x)),
                "cutoutmargin": lambda x: self.builder.get_object("entry_gerber_cutout_margin").set_text(str(x)),
                "cutoutgapsize": lambda x: self.builder.get_object("entry_gerber_cutout_gapsize").set_text(str(x)),
                "gaps": lambda x: self.builder.get_object("cb_gerber_solid").set_active(
                                        {"tb": "rb_2tb", "lr": "rb_2lr", "4": "rb_4"}[x])
            }
            for option in obj.options:
                if option in setters:
                    setters[option](obj.options[option])
            return

        if obj.__class__.__name__ == 'CirkuixExcellon':
            setters = {
                "plot": self.builder.get_object("cb_excellon_plot").set_active,
                "solid": self.builder.get_object("cb_excellon_solid").set_active,
                "multicolored": self.builder.get_object("cb_excellon_multicolored").set_active
            }
            for option in obj.options:
                if option in setters:
                    setters[option](obj.options[option])
            return

        if obj.__class__.__name__ == 'CirkuixCNCjob':
            obj.set_options({
                "plot": self.builder.get_object("cb_cncjob_plot").set_active,
                "solid": self.builder.get_object("cb_cncjob_solid").set_active,
                "tooldia": lambda x: self.builder.get_object("entry_cncjob_tooldia").set_text(str(x))
            })

    def form_to_selected_object(self):
        obj = self.stuff[self.selected_item_name]

        if obj.__class__.__name__ == 'CirkuixGerber':

            obj.set_options({
                "plot": self.builder.get_object("cb_gerber_plot").get_active(),
                "mergepolys": self.builder.get_object("cb_gerber_mergepolys").get_active(),
                "solid": self.builder.get_object("cb_gerber_solid").get_active(),
                "multicolored": self.builder.get_object("cb_gerber_multicolored").get_active(),
                "isotooldia": self.get_eval("entry_gerberisotooldia"),
                "cutoutmargin": self.get_eval("entry_gerber_cutout_margin"),
                "cutoutgapsize": self.get_eval("entry_gerber_cutout_gapsize"),
                "gaps": lambda x: self.get_radio_value({"rb_2tb": "tb", "rb_2lr": "lr", "rb_4": "4"})
            })
            return

        if obj.__class__.__name__ == 'CirkuixExcellon':
            obj.set_options({
                "plot": self.builder.get_object("cb_excellon_plot").get_active(),
                "solid": self.builder.get_object("cb_excellon_solid").get_active(),
                "multicolored": self.builder.get_object("cb_excellon_multicolored").get_active()
            })

            return

        if obj.__class__.__name__ == 'CirkuixCNCjob':
            obj.set_options({
                "plot": self.builder.get_object("cb_cncjob_plot").get_active(),
                "solid": self.builder.get_object("cb_cncjob_solid").get_active(),
                "multicolored": self.builder.get_object("cb_cncjob_multicolored").get_active(),
                "tooldia": self.get_eval("entry_cncjob_tooldia")
            })

        if type(obj) is CirkuixGeometry:
            obj.set_options({
                "plot": self.builder.get_object("cb_geometry_plot").get_active(),
                "solid": self.builder.get_object("cb_geometry_solid").get_active(),
                "multicolored": self.builder.get_object("cb_geometry_multicolored").get_active(),
                "cutz": self.get_eval("entry_geometry_cutz"),
                "travelz": self.get_eval("entry_geometry_travelz"),
                "feedrate": self.get_eval("entry_geometry_feedrate")
            })

    def plot_all(self):
        self.clear_plots()
        #plotter = {"gerber": self.plot_gerber,
        #           "excellon": self.plot_excellon,
        #           "cncjob": self.plot_cncjob,
        #           "geometry": self.plot_geometry}
        
        for i in self.stuff:
            #kind = self.stuff[i].kind
            #plotter[kind](self.stuff[i])
            self.stuff[i].plot(self.figure)
        
        self.on_zoom_fit(None)
        self.axes.grid()
        self.canvas.queue_draw()
        
    def clear_plots(self):
        self.axes.cla()
        self.figure.clf()
        self.figure.add_axes(self.axes)
        self.canvas.queue_draw()

    def get_eval(self, widget_name):
        value = self.builder.get_object(widget_name).get_text()
        return eval(value)

    def set_list_selection(self, name):
        iter = self.store.get_iter_first()
        while iter is not None and self.store[iter][0] != name:
            iter = self.store.iter_next(iter)
        self.tree_select.unselect_all()
        self.tree_select.select_iter(iter)

    ########################################
    ##         EVENT HANDLERS             ##
    ########################################
    def on_gerber_generate_boundary(self, widget):
        margin = self.get_eval("entry_gerber_cutout_margin")
        gap_size = self.get_eval("entry_gerber_cutout_gapsize")
        gerber = self.stuff[self.selected_item_name]
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
        name = self.selected_item_name + "_cutout"
        geometry = CirkuixGeometry(name)
        cuts = None
        if self.builder.get_object("rb_2tb").get_active():
            cuts = cases["tb"]
        elif self.builder.get_object("rb_2lr").get_active():
            cuts = cases["lr"]
        else:
            cuts = cases["4"]
        geometry.solid_geometry = cascaded_union([LineString(segment) for segment in cuts])

        # Add to App and update.
        self.stuff[name] = geometry
        self.build_list()

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
        # Get required info
        tooldia = self.builder.get_object("entry_gerberisotooldia").get_text()
        tooldia = eval(tooldia)
        print "tooldia:", tooldia
        
        # Generate
        iso = self.stuff[self.selected_item_name].isolation_geometry(tooldia/2.0)
        # TODO: This will break if there is something with this name already        
        iso_name = self.selected_item_name + "_iso"
        geo = CirkuixGeometry(iso_name)
        geo.solid_geometry = iso

        # Add to App and update.        
        self.stuff[iso_name] = geo        
        self.build_list()
        
    def on_generate_cncjob(self, widget):
        print "Generating CNC job"
        # Get required info
        cutz = self.get_eval("entry_geometry_cutz")
        travelz = self.get_eval("entry_geometry_travelz")
        feedrate = self.get_eval("entry_geometry_feedrate")
        
        geometry = self.stuff[self.selected_item_name]
        job_name = self.selected_item_name + "_cnc"
        job = CirkuixCNCjob(job_name, z_move=travelz, z_cut=cutz, feedrate=feedrate)
        job.generate_from_geometry(geometry.solid_geometry)
        job.gcode_parse()
        job.create_geometry()
        
        # Add to App and update.        
        self.stuff[job_name] = job      
        self.build_list()

    def on_cncjob_tooldia_activate(self, widget):
        job = self.stuff[self.selected_item_name]
        tooldia = self.get_eval("entry_cncjob_tooldia")
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
        self.build_list() # Update the items list
        #self.signal_id = self.tree.get_selection().connect(
        #                     "changed", self.on_tree_selection_changed)
                             
        self.plot_all()
        #self.notebook.set_current_page(1)
                             
    def on_replot(self, widget):
        self.plot_all()
    
    def on_clear_plots(self, widget):
        self.clear_plots()
        
    def on_activate_name(self, entry):
        '''
        Hitting 'Enter' after changing the name of an item
        updates the item dictionary and re-builds the item list.
        '''
        print "Changing name"
        self.tree.get_selection().disconnect(self.signal_id)
        new_name = entry.get_text() # Get from form
        self.stuff[new_name] = self.stuff.pop(self.selected_item_name) # Update dictionary
        self.selected_item_name = new_name # Update selection name
        self.build_list() # Update the items list
        self.signal_id = self.tree.get_selection().connect(
                             "changed", self.on_tree_selection_changed)
                             
    def on_tree_selection_changed(self, selection):
        model, treeiter = selection.get_selected()

        if treeiter is not None:
            print "You selected", model[treeiter][0]
        else:
            return  # TODO: Clear "Selected" page
        
        self.selected_item_name = model[treeiter][0]
        # Remove the current selection page
        # from the notebook
        # TODO: Assuming it was last page or #2. Find the right page
        self.builder.get_object("notebook1").remove_page(2)
        
        # Determine the kind of item selected
        kind = self.stuff[model[treeiter][0]].kind
        
        # Build the UI
        builder = {"gerber": self.build_gerber_ui,
                   "excellon": self.build_excellon_ui,
                   "cncjob": self.build_cncjob_ui,
                   "geometry": self.build_geometry_ui}
        builder[kind]()
    
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
        def on_success(self, filename):
            self.progress_bar.set_text("Opening Gerber ...")
            self.progress_bar.set_fraction(0.1)

            name = filename.split('/')[-1].split('\\')[-1]
            gerber = CirkuixGerber(name)

            self.progress_bar.set_text("Parsing ...")
            self.progress_bar.set_fraction(0.2)

            gerber.parse_file(filename)
            self.store.append([name])
            self.stuff[name] = gerber

            self.progress_bar.set_text("Plotting ...")
            self.progress_bar.set_fraction(0.6)

            #self.plot_gerber(gerber)
            gerber.plot(self.figure)
            gerber.axes.set_alpha(0.0)
            self.on_zoom_fit(None)

            self.progress_bar.set_text("Done!")
            self.progress_bar.set_fraction(1.0)

            self.notebook.set_current_page(1)
            self.set_list_selection(name)

            def clear_bar(bar):
                bar.set_text("")
                bar.set_fraction(0.0)

            threading.Timer(1, clear_bar, args=(self.progress_bar,)).start()
        self.file_chooser_action(on_success)
    
    def on_fileopenexcellon(self, param):
        def on_success(self, filename):
            self.progress_bar.set_text("Opening Excellon ...")
            self.progress_bar.set_fraction(0.1)

            name = filename.split('/')[-1].split('\\')[-1]
            excellon = CirkuixExcellon(name)

            self.progress_bar.set_text("Parsing ...")
            self.progress_bar.set_fraction(0.2)

            excellon.parse_file(filename)
            self.store.append([name])
            self.stuff[name] = excellon

            self.progress_bar.set_text("Plotting ...")
            self.progress_bar.set_fraction(0.6)

            #self.plot_excellon(excellon)
            excellon.plot(self.figure)
            self.on_zoom_fit(None)

            self.progress_bar.set_text("Done!")
            self.progress_bar.set_fraction(1.0)

            def clear_bar(bar):
                bar.set_text("")
                bar.set_fraction(0.0)
            threading.Timer(1, clear_bar, args=(self.progress_bar,)).start()

        self.file_chooser_action(on_success)
    
    def on_fileopengcode(self, param):
        def on_success(self, filename):
            self.progress_bar.set_text("Opening G-Code ...")
            self.progress_bar.set_fraction(0.1)

            name = filename.split('/')[-1].split('\\')[-1]
            f = open(filename)
            gcode = f.read()
            f.close()
            tooldia = self.get_eval("entry_tooldia")
            job = CirkuixCNCjob(name, tooldia=tooldia)
            job.gcode = gcode

            self.progress_bar.set_text("Parsing ...")
            self.progress_bar.set_fraction(0.2)

            job.gcode_parse()
            job.create_geometry()
            self.store.append([name])
            self.stuff[name] = job

            self.progress_bar.set_text("Plotting ...")
            self.progress_bar.set_fraction(0.6)

            #self.plot_cncjob(job)
            job.plot(self.figure)
            self.on_zoom_fit(None)

            self.progress_bar.set_text("Done!")
            self.progress_bar.set_fraction(1.0)

            def clear_bar(bar):
                bar.set_text("")
                bar.set_fraction(0.0)
            threading.Timer(1, clear_bar, args=(self.progress_bar,)).start()
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
        
        print 'button=%d, x=%d, y=%d, xdata=%f, ydata=%f'%(
        event.button, event.x, event.y, event.xdata, event.ydata)
        
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
