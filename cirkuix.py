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
        self.gladefile = "cirkuix.ui"
        self.builder = Gtk.Builder()
        self.builder.add_from_file(self.gladefile)
        self.window = self.builder.get_object("window1")

        #self.drawingarea = self.builder.get_object("drawingarea1")
        #self.drawingarea.connect("draw", self.cairopaint)        
        
        self.grid = self.builder.get_object("grid1")        
        self.builder.connect_signals(self)
        self.mplpaint()
        self.window.show_all()
        
        self.gerbers = []        
        
        Gtk.main()
        
    def mplpaint(self):
        f = Figure(dpi=50)
        a = f.add_subplot(111)
        a.set_aspect(1)
        t = arange(0.0,5.0,0.01)
        s = sin(2*pi*t)
        a.plot(t,s)
        a.grid()
        #a.patch.set_visible(False) Background of the axes
        f.patch.set_visible(False)
        f.tight_layout()
        
        canvas = FigureCanvas(f)  # a Gtk.DrawingArea
        canvas.set_size_request(600,400)
        self.grid.attach(canvas,1,1,600,400)
    
    def cairopaint(self, da, cr):
        width = 200
        height = 200
        #cr = widget.window.cairo_create() # Context
        cr.set_source_rgb(0.5, 0.5, 0.5)
        cr.rectangle(0, 0, width, height)
        cr.fill()

        # draw a rectangle
        cr.set_source_rgb(1.0, 1.0, 1.0)
        cr.rectangle(10, 10, width - 20, height - 20)
        cr.fill()

        # draw lines
        cr.set_source_rgb(0.0, 0.0, 0.8)
        cr.move_to(width / 3.0, height / 3.0)
        cr.rel_line_to(0, height / 6.0)
        cr.move_to(2 * width / 3.0, height / 3.0)
        cr.rel_line_to(0, height / 6.0)
        cr.stroke()

        # and a circle
        cr.set_source_rgb(1.0, 0.0, 0.0)
        radius = min(width, height)
        cr.arc(width / 2.0, height / 2.0, radius / 2.0 - 20, 0, 2 * pi)
        cr.stroke()
        cr.arc(width / 2.0, height / 2.0, radius / 3.0 - 10, pi / 3, 2 * pi / 3)
        cr.stroke()

    def on_filequit(self, param):
        print "quit from menu"
        self.window.destroy()
        Gtk.main_quit()
    
    def on_closewindow(self, param):
        print "quit from X"
        self.window.destroy()
        Gtk.main_quit()
        
    def on_fileopengeometry(self, param):
        print "File->Open Geometry"
        dialog = Gtk.FileChooserDialog("Please choose a file", self.window,
            Gtk.FileChooserAction.OPEN,
            (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
             Gtk.STOCK_OPEN, Gtk.ResponseType.OK))
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            print("Open clicked")
            print("File selected: " + dialog.get_filename())
            gerber = Gerber()
            gerber.parse_file(dialog.get_filename())
            gerber.create_geometry()
            self.gerbers.append(gerber)
            self.plot_gerber(gerber)
        elif response == Gtk.ResponseType.CANCEL:
            print("Cancel clicked")
        dialog.destroy()
        
    def plot_gerber(self, gerber):
        
        f = Figure(dpi=75)
        a = f.add_subplot(111)
        a.set_aspect(1)
        for poly in gerber.solid_geometry:
            x, y = poly.exterior.xy
            a.plot(x, y)
            for ints in poly.interiors:
                x, y = ints.coords.xy
                a.plot(x, y)
        a.grid()
        f.tight_layout()
        canvas = FigureCanvas(f)  # a Gtk.DrawingArea
        canvas.set_size_request(600,400)
        self.grid.attach(canvas,1,1,600,400)
        self.window.show_all()


app = App()
