from gi.repository import Gtk

import matplotlib.pyplot as plt
plt.ioff()

from matplotlib.figure import Figure
from numpy import arange, sin, pi
from matplotlib.backends.backend_gtk3agg import FigureCanvasGTK3Agg as FigureCanvas
#from matplotlib.backends.backend_gtk3 import NavigationToolbar2GTK3 as NavigationToolbar
#from matplotlib.backends.backend_gtk3cairo import FigureCanvasGTK3Cairo as FigureCanvas
#from matplotlib.backends.backend_cairo import FigureCanvasCairo as FigureCanvas
#import cairo

from camlib import *

class CirkuixObj:
    def __init__(self, name, kind):
        self.name = name
        self.kind = kind
        
class CirkuixGerber(CirkuixObj, Gerber):
    def __init__(self, name):
        Gerber.__init__(self)
        CirkuixObj.__init__(self, name, "gerber")
        self.fields = [{"name":"plot", 
                        "type":bool, 
                        "value":True, 
                        "get":None, 
                        "set":None, 
                        "onchange":None},
                       {}]
        
class CirkuixExcellon(CirkuixObj, Excellon):
    def __init__(self, name):
        Excellon.__init__(self)
        CirkuixObj.__init__(self, name, "excellon")
        self.options = {"plot": True,
                        "solid": False,
                        "multicolored": False}
        
class CirkuixCNCjob(CirkuixObj, CNCjob):
    def __init__(self, name):
        CNCjob.__init__(self)
        CirkuixObj.__init__(self, name, "cncjob")
        self.options = {"plot": True}

class CirkuixGeometry(CirkuixObj, Geometry):
    def __init__(self, name):
        CirkuixObj.__init__(self, name, "geometry")
        self.options = {"plot": True,
                        "solid": False,
                        "multicolored": False}

class CirkuixObjForm:
    def __init__(self, container, Cobj):
        self.Cobj = Cobj
        self.container = container
        self.fields = {}
    
    def populate(self):
        return
        
    def save(self):
        return

#class CirkuixGerberForm(CirkuixObjForm)
    

def get_entry_text(entry):
    return entry.get_text()
    
def get_entry_int(entry):
    return int(entry.get_text())
    
def get_entry_float(entry):
    return float(entry.get_text())
    
def get_entry_eval(entry):
    return eval(entry.get_text)

getters = {"entry_text":get_entry_text,
           "entry_int":get_entry_int,
           "entry_float":get_entry_float,
           "entry_eval":get_entry_eval}

setters = {"entry"}

class App:
    def __init__(self):
        
        ########################################
        ##                GUI                 ##
        ########################################       
        self.gladefile = "cirkuix.ui"
        self.builder = Gtk.Builder()
        self.builder.add_from_file(self.gladefile)
        self.window = self.builder.get_object("window1")
        self.window.set_title("Cirkuix")
        self.positionLabel = self.builder.get_object("label3")      
        self.grid = self.builder.get_object("grid1")
        self.notebook = self.builder.get_object("notebook1")
        
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
        self.stuff = {} # CirkuixObj's by name
        
        self.mouse = None
        
        # What is selected by the user. It is
        # a key if self.stuff
        self.selected_item_name = None
        
        ########################################
        ##              START                 ##
        ########################################
        self.window.show_all()
        Gtk.main()
        
    def plot_setup(self):
        self.figure = Figure(dpi=50)
        self.axes = self.figure.add_axes([0.05,0.05,0.9,0.9])
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
        self.canvas.set_can_focus(True) # For key press
        self.canvas.mpl_connect('key_press_event', self.on_key_over_plot)
        self.canvas.mpl_connect('scroll_event', self.on_scroll_over_plot)
        
        self.grid.attach(self.canvas,0,0,600,400)
    
    def zoom(self, factor, center=None):
        '''
        Zooms the plot by factor around a given
        center point. Takes care of re-drawing.
        '''
        xmin, xmax = self.axes.get_xlim()
        ymin, ymax = self.axes.get_ylim()
        width = xmax-xmin
        height = ymax-ymin
        
        if center == None:
            center = [(xmin+xmax)/2.0, (ymin+ymax)/2.0]
        
        # For keeping the point at the pointer location
        relx = (xmax-center[0])/width
        rely = (ymax-center[1])/height         
        
        new_width = width/factor
        new_height = height/factor
        
        self.axes.set_xlim((center[0]-new_width*(1-relx), center[0]+new_width*relx))
        self.axes.set_ylim((center[1]-new_height*(1-rely), center[1]+new_height*rely))
        
        self.canvas.queue_draw()

    def plot_gerber(self, gerber):
        gerber.create_geometry()
        
        # Options
        mergepolys = self.builder.get_object("cb_mergepolys").get_active()
        multicolored = self.builder.get_object("cb_multicolored").get_active()
        
        geometry = None
        if mergepolys:
            geometry = gerber.solid_geometry
        else:
            geometry = gerber.buffered_paths + \
                        [poly['polygon'] for poly in gerber.regions] + \
                        gerber.flash_geometry
        
        linespec = None
        if multicolored:
            linespec = '-'
        else:
            linespec = 'k-'

        for poly in geometry:
            x, y = poly.exterior.xy
            #a.plot(x, y)
            self.axes.plot(x, y, linespec)
            for ints in poly.interiors:
                x, y = ints.coords.xy
                self.axes.plot(x, y, linespec)
                
        self.canvas.queue_draw()
        
    def plot_excellon(self, excellon):
        excellon.create_geometry()
        
        # Plot excellon
        for geo in excellon.solid_geometry:
            x, y = geo.exterior.coords.xy
            self.axes.plot(x, y, 'r-')
            for ints in geo.interiors:
                x, y = ints.coords.xy
                self.axes.plot(x, y, 'g-')
                
        self.canvas.queue_draw()

    def plot_cncjob(self, job):
        #job.gcode_parse()
        tooldia_text = self.builder.get_object("entry_tooldia").get_text()
        tooldia_val = eval(tooldia_text)
        job.plot2(self.axes, tooldia=tooldia_val)
        
        self.canvas.queue_draw()
        
    def plot_geometry(self, geometry):
        for geo in geometry.solid_geometry:
            x, y = geo.exterior.coords.xy
            self.axes.plot(x, y, 'r-')
            for ints in geo.interiors:
                x, y = ints.coords.xy
                self.axes.plot(x, y, 'r-')
                
        self.canvas.queue_draw()
            
        
    def setup_component_viewer(self):
        '''
        List or Tree where whatever has been loaded or created is
        displayed.
        '''
        self.store = Gtk.ListStore(str)
        self.tree = Gtk.TreeView(self.store)
        select = self.tree.get_selection()
        self.signal_id = select.connect("changed", self.on_tree_selection_changed)
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
        box1.show()
        
    def plot_all(self):
        self.clear_plots()
        plotter = {"gerber":self.plot_gerber,
                   "excellon":self.plot_excellon,
                   "cncjob":self.plot_cncjob,
                   "geometry":self.plot_geometry}
        
        for i in self.stuff:
            kind = self.stuff[i].kind
            plotter[kind](self.stuff[i])
        
        self.on_zoom_fit(None)
        self.axes.grid()
        self.canvas.queue_draw()
        
    def clear_plots(self):
        self.axes.cla()
        self.canvas.queue_draw()

    ########################################
    ##         EVENT HANDLERS             ##
    ########################################
    def on_eval_update(self, widget):
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
        
                
        if treeiter != None:
            print "You selected", model[treeiter][0]
        else:
            return # TODO: Clear "Selected" page
        
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
        Opens the file chooser and runs on_success
        upon completion of valid file choice.
        '''
        dialog = Gtk.FileChooserDialog("Please choose a file", self.window,
            Gtk.FileChooserAction.OPEN,
            (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
             Gtk.STOCK_OPEN, Gtk.ResponseType.OK))
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            on_success(self, dialog.get_filename())
        elif response == Gtk.ResponseType.CANCEL:
            print("Cancel clicked")
        dialog.destroy()    
    
    def on_fileopengerber(self, param):
        def on_success(self, filename):
            name = filename.split('/')[-1].split('\\')[-1]
            gerber = CirkuixGerber(name)
            gerber.parse_file(filename)
            self.store.append([name])
            #self.gerbers.append(gerber)
            self.stuff[name] = gerber
            self.plot_gerber(gerber)
            self.on_zoom_fit(None)
        self.file_chooser_action(on_success)
    
    def on_fileopenexcellon(self, param):
        def on_success(self, filename):
            name = filename.split('/')[-1].split('\\')[-1]
            excellon = CirkuixExcellon(name)
            excellon.parse_file(filename)
            self.store.append([name])
            #self.excellons.append(excellon)
            self.stuff[name] = excellon
            self.plot_excellon(excellon)
            self.on_zoom_fit(None)
        self.file_chooser_action(on_success)
    
    def on_fileopengcode(self, param):
        def on_success(self, filename):
            name = filename.split('/')[-1].split('\\')[-1]
            f = open(filename)
            gcode = f.read()
            f.close()
            job = CirkuixCNCjob(name)
            job.gcode = gcode
            job.gcode_parse()
            job.create_geometry()
            self.store.append([name])
            #self.cncjobs.append(job)
            self.stuff[name] = job
            self.plot_cncjob(job)
            self.on_zoom_fit(None)
        self.file_chooser_action(on_success)
        
    def on_mouse_move_over_plot(self, event):
        try: # May fail in case mouse not within axes
            self.positionLabel.set_label("X: %.4f   Y: %.4f"%(
                                         event.xdata, event.ydata))
            self.mouse = [event.xdata, event.ydata]
        except:
            self.positionLabel.set_label("")
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
            self.axes.set_xlim((xmin-0.05*width, xmax+0.05*width))
            ycenter = (ymin+ymax)/2.0
            newheight = height*r/Fr
            self.axes.set_ylim((ycenter-newheight/2.0, ycenter+newheight/2.0))
        else:
            self.axes.set_ylim((ymin-0.05*height, ymax+0.05*height))
            xcenter = (xmax+ymin)/2.0
            newwidth = width*Fr/r
            self.axes.set_xlim((xcenter-newwidth/2.0, xcenter+newwidth/2.0))
        
        self.canvas.queue_draw()
        return
        
    def on_scroll_over_plot(self, event):
        print "Scroll"
        center = [event.xdata, event.ydata]
        if sign(event.step):
            self.zoom(1.5, center=center)
        else:
            self.zoom(1/1.5, center=center)
            
    def on_window_scroll(self, event):
        print "Scroll"
        
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
