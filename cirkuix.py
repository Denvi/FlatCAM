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

class App:
    def __init__(self):
        
        ########################################
        ##                GUI                 ##
        ########################################
        self.gladefile = "cirkuix.ui"
        self.builder = Gtk.Builder()
        self.builder.add_from_file(self.gladefile)
        self.window = self.builder.get_object("window1")
        self.positionLabel = self.builder.get_object("label3")      
        self.grid = self.builder.get_object("grid1")
        
        ## Event handling ##
        self.builder.connect_signals(self)
        
        self.figure = None
        self.axes = None
        self.canvas = None
        
        ## Make plot area ##
        self.mplpaint()
        self.window.show_all()
        
        ########################################
        ##               DATA                 ##
        ########################################
        self.gerbers = []
        self.excellons = []
        
        self.mouse = None
        
        Gtk.main()
        
    def mplpaint(self):
        self.figure = Figure(dpi=50)
        #self.axes = self.figure.add_subplot(111)
        self.axes = self.figure.add_axes([0.05,0.05,0.9,0.9])
        self.axes.set_aspect(1)
        #t = arange(0.0,5.0,0.01)
        #s = sin(2*pi*t)
        #self.axes.plot(t,s)
        self.axes.grid()
        #a.patch.set_visible(False) Background of the axes
        self.figure.patch.set_visible(False)
        #self.figure.tight_layout()
        
        self.canvas = FigureCanvas(self.figure)  # a Gtk.DrawingArea
        #self.canvas.set_size_request(600,400)
        self.canvas.mpl_connect('button_press_event', self.on_click_over_plot)
        self.canvas.mpl_connect('motion_notify_event', self.on_mouse_move_over_plot)
        ##self.canvas.mpl_connect('scroll_event', self.on_scroll_over_plot)
        ##self.canvas.mpl_connect('key_press_event', self.on_key_over_plot)
        
        
        self.canvas.set_hexpand(1)
        self.canvas.set_vexpand(1)        
        
        #self.builder.get_object("viewport2").add(self.canvas)
        self.grid.attach(self.canvas,0,0,600,400)
        #self.builder.get_object("scrolledwindow1").add(self.canvas)
    

    def on_filequit(self, param):
        print "quit from menu"
        self.window.destroy()
        Gtk.main_quit()
    
    def on_closewindow(self, param):
        print "quit from X"
        self.window.destroy()
        Gtk.main_quit()
        
    def on_fileopengerber(self, param):
        print "File->Open Gerber"
        dialog = Gtk.FileChooserDialog("Please choose a file", self.window,
            Gtk.FileChooserAction.OPEN,
            (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
             Gtk.STOCK_OPEN, Gtk.ResponseType.OK))
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            ## Load the file ##
            print("Open clicked")
            print("File selected: " + dialog.get_filename())
            gerber = Gerber()
            gerber.parse_file(dialog.get_filename())
            self.gerbers.append(gerber)
            self.plot_gerber(gerber)
            ## End ##
        elif response == Gtk.ResponseType.CANCEL:
            print("Cancel clicked")
        dialog.destroy()
        
    def on_fileopenexcellon(self, param):
        print "File->Open Excellon"
        dialog = Gtk.FileChooserDialog("Please choose a file", self.window,
            Gtk.FileChooserAction.OPEN,
            (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
             Gtk.STOCK_OPEN, Gtk.ResponseType.OK))
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            ## Load the file ##
            print("Open clicked")
            print("File selected: " + dialog.get_filename())
            excellon = Excellon()
            excellon.parse_file(dialog.get_filename())
            self.excellons.append(excellon)
            self.plot_excellon(excellon)
            ## End ##
        elif response == Gtk.ResponseType.CANCEL:
            print("Cancel clicked")
        dialog.destroy()
        
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
        #f = Figure(dpi=75)
        #a = f.add_subplot(111)
        #a.set_aspect(1)
        for poly in geometry:
            x, y = poly.exterior.xy
            #a.plot(x, y)
            self.axes.plot(x, y, linespec)
            for ints in poly.interiors:
                x, y = ints.coords.xy
                self.axes.plot(x, y, linespec)
        
        #f.tight_layout()
        #canvas = FigureCanvas(f)  # a Gtk.DrawingArea
        #canvas.set_size_request(600,400)
        #self.grid.attach(canvas,1,1,600,400)
        #self.window.show_all()
        
    def plot_excellon(self, excellon):
        excellon.create_geometry()
        
        # Plot excellon
        for geo in excellon.solid_geometry:
            x, y = geo.exterior.coords.xy
            self.axes.plot(x, y, 'r-')
            for ints in geo.interiors:
                x, y = ints.coords.xy
                self.axes.plot(x, y, 'g-')
        
    def on_mouse_move_over_plot(self, event):
        try: # May fail in case mouse not within axes
            self.positionLabel.set_label("X: %.4f   Y: %.4f"%(
                                         event.xdata, event.ydata))
            self.mouse = [event.xdata, event.ydata]
        except:
            self.positionLabel.set_label("X: ---   Y: ---")
            self.mouse = None
        
    def on_click_over_plot(self, event):
        print 'button=%d, x=%d, y=%d, xdata=%f, ydata=%f'%(
        event.button, event.x, event.y, event.xdata, event.ydata)
        
    def get_bounds(self):
        xmin = Inf
        ymin = Inf
        xmax = -Inf
        ymax = -Inf
        
        geometry_sets = [self.gerbers, self.excellons]
        
        for gs in geometry_sets:
            for g in gs:
                gxmin, gymin, gxmax, gymax = g.solid_geometry.bounds
                xmin = min([xmin, gxmin])
                ymin = min([ymin, gymin])
                xmax = max([xmax, gxmax])
                ymax = max([ymax, gymax])
                
        return [xmin, ymin, xmax, ymax]
        
    def on_zoom_in(self, event):
        self.zoom(1.5)
        return
        
    def on_zoom_out(self, event):
        self.zoom(1/1.5)
         
    def on_zoom_fit(self, event):
        xmin, ymin, xmax, ymax = self.get_bounds()
        width = xmax-xmin
        height = ymax-ymin
        self.axes.set_xlim((xmin-0.05*width, xmax+0.05*width))
        self.axes.set_ylim((ymin-0.05*height, ymax+0.05*height))
        self.canvas.queue_draw()
        return
        
    def zoom(self, factor, center=None):
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
        
#    def on_scroll_over_plot(self, event):
#        print "Scroll"
#        center = [event.xdata, event.ydata]
#        if sign(event.step):
#            self.zoom(1.5, center=center)
#        else:
#            self.zoom(1/1.5, center=center)
#            
#    def on_window_scroll(self, event):
#        print "Scroll"
#        
#    def on_key_over_plot(self, event):
#        print 'you pressed', event.key, event.xdata, event.ydata
        
    def on_window_key_press(self, widget, event):
        print event.get_keycode(), event.get_keyval()
        val = int(event.get_keyval()[1])
        
        if val == 49: # 1
            self.on_zoom_fit(None)
            return
            
        if val == 50: # 2
            self.zoom(1/1.5, self.mouse)
            return
            
        if val == 51: # 3
            self.zoom(1.5, self.mouse)
            return

app = App()
