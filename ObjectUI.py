############################################################
# FlatCAM: 2D Post-processing for Manufacturing            #
# http://caram.cl/software/flatcam                         #
# Author: Juan Pablo Caram (c)                             #
# Date: 2/5/2014                                           #
# MIT Licence                                              #
############################################################

from gi.repository import Gtk
from GUIElements import *


class ObjectUI(Gtk.VBox):
    """
    Base class for the UI of FlatCAM objects.
    """

    def __init__(self, icon_file='share/flatcam_icon32.png', title='FlatCAM Object'):
        Gtk.VBox.__init__(self, spacing=3, margin=5, vexpand=False)

        ## Page Title box (spacing between children)
        self.title_box = Gtk.Box.new(Gtk.Orientation.HORIZONTAL, 2)
        self.pack_start(self.title_box, expand=False, fill=False, padding=2)

        ## Page Title icon
        self.icon = Gtk.Image.new_from_file(icon_file)
        self.title_box.pack_start(self.icon, expand=False, fill=False, padding=2)

        ## Title label
        self.title_label = Gtk.Label()
        self.title_label.set_markup("<b>" + title + "</b>")
        self.title_label.set_justify(Gtk.Justification.CENTER)
        self.title_box.pack_start(self.title_label, expand=False, fill=False, padding=2)

        ## Object name
        self.name_box = Gtk.Box.new(Gtk.Orientation.HORIZONTAL, 2)
        self.pack_start(self.name_box, expand=False, fill=False, padding=2)
        name_label = Gtk.Label('Name:')
        name_label.set_justify(Gtk.Justification.RIGHT)
        self.name_box.pack_start(name_label,
                                 expand=False, fill=False, padding=2)
        self.name_entry = FCEntry()
        self.name_box.pack_start(self.name_entry, expand=True, fill=False, padding=2)

        ## Box box for custom widgets
        self.custom_box = Gtk.VBox(spacing=3, margin=0, vexpand=False)
        self.pack_start(self.custom_box, expand=False, fill=False, padding=0)

        ## Common to all objects
        ## Scale
        self.scale_label = Gtk.Label(justify=Gtk.Justification.LEFT, xalign=0, margin_top=5)
        self.scale_label.set_markup('<b>Scale:</b>')
        self.pack_start(self.scale_label, expand=False, fill=False, padding=2)

        grid5 = Gtk.Grid(column_spacing=3, row_spacing=2)
        self.pack_start(grid5, expand=False, fill=False, padding=2)

        # Factor
        l10 = Gtk.Label('Factor:', xalign=1)
        grid5.attach(l10, 0, 0, 1, 1)
        self.scale_entry = FloatEntry()
        self.scale_entry.set_text("1.0")
        grid5.attach(self.scale_entry, 1, 0, 1, 1)

        # GO Button
        self.scale_button = Gtk.Button(label='Scale')
        self.pack_start(self.scale_button, expand=False, fill=False, padding=2)

        ## Offset
        self.offset_label = Gtk.Label(justify=Gtk.Justification.LEFT, xalign=0, margin_top=5)
        self.offset_label.set_markup('<b>Offset:</b>')
        self.pack_start(self.offset_label, expand=False, fill=False, padding=2)

        grid6 = Gtk.Grid(column_spacing=3, row_spacing=2)
        self.pack_start(grid6, expand=False, fill=False, padding=2)

        # Vector
        l11 = Gtk.Label('Offset Vector:', xalign=1)
        grid6.attach(l11, 0, 0, 1, 1)
        self.offsetvector_entry = EvalEntry()
        self.offsetvector_entry.set_text("(0.0, 0.0)")
        grid6.attach(self.offsetvector_entry, 1, 0, 1, 1)

        self.offset_button = Gtk.Button(label='Scale')
        self.pack_start(self.offset_button, expand=False, fill=False, padding=2)

    def set_field(self, name, value):
        getattr(self, name).set_value(value)

    def get_field(self, name):
        return getattr(self, name).get_value()


class CNCObjectUI(ObjectUI):
    """
    User interface for CNCJob objects.
    """

    def __init__(self):
        ObjectUI.__init__(self, title='CNC Job Object', icon_file='share/cnc32.png')

        ## Plot options
        self.plot_options_label = Gtk.Label(justify=Gtk.Justification.LEFT, xalign=0, margin_top=5)
        self.plot_options_label.set_markup("<b>Plot Options:</b>")
        self.custom_box.pack_start(self.plot_options_label, expand=False, fill=True, padding=2)

        grid0 = Gtk.Grid(column_spacing=3, row_spacing=2)
        self.custom_box.pack_start(grid0, expand=False, fill=False, padding=2)

        # Plot CB
        self.plot_cb = FCCheckBox(label='Plot')
        grid0.attach(self.plot_cb, 0, 0, 2, 1)

        # Tool dia for plot
        l1 = Gtk.Label('Tool dia:', xalign=1)
        grid0.attach(l1, 0, 1, 1, 1)
        self.tooldia_entry = LengthEntry()
        grid0.attach(self.tooldia_entry, 1, 1, 1, 1)

        # Update plot button
        self.updateplot_button = Gtk.Button(label='Update Plot')
        self.custom_box.pack_start(self.updateplot_button, expand=False, fill=False, padding=2)

        ## Export G-Code
        self.export_gcode_label = Gtk.Label(justify=Gtk.Justification.LEFT, xalign=0, margin_top=5)
        self.export_gcode_label.set_markup("<b>Export G-Code:</b>")
        self.custom_box.pack_start(self.export_gcode_label, expand=False, fill=False, padding=2)

        # GO Button
        self.export_gcode_button = Gtk.Button(label='Export G-Code')
        self.custom_box.pack_start(self.export_gcode_button, expand=False, fill=False, padding=2)


class GeometryObjectUI(ObjectUI):
    """
    User interface for Geometry objects.
    """

    def __init__(self):
        ObjectUI.__init__(self, title='Geometry Object', icon_file='share/geometry32.png')

        ## Plot options
        self.plot_options_label = Gtk.Label(justify=Gtk.Justification.LEFT, xalign=0, margin_top=5)
        self.plot_options_label.set_markup("<b>Plot Options:</b>")
        self.custom_box.pack_start(self.plot_options_label, expand=False, fill=True, padding=2)

        grid0 = Gtk.Grid(column_spacing=3, row_spacing=2)
        self.custom_box.pack_start(grid0, expand=True, fill=False, padding=2)

        # Plot CB
        self.plot_cb = FCCheckBox(label='Plot')
        grid0.attach(self.plot_cb, 0, 0, 1, 1)

        ## Create CNC Job
        self.cncjob_label = Gtk.Label(justify=Gtk.Justification.LEFT, xalign=0, margin_top=5)
        self.cncjob_label.set_markup('<b>Create CNC Job:</b>')
        self.custom_box.pack_start(self.cncjob_label, expand=True, fill=False, padding=2)

        grid1 = Gtk.Grid(column_spacing=3, row_spacing=2)
        self.custom_box.pack_start(grid1, expand=True, fill=False, padding=2)

        # Cut Z
        l1 = Gtk.Label('Cut Z:', xalign=1)
        grid1.attach(l1, 0, 0, 1, 1)
        self.cutz_entry = LengthEntry()
        grid1.attach(self.cutz_entry, 1, 0, 1, 1)

        # Travel Z
        l2 = Gtk.Label('Travel Z:', xalign=1)
        grid1.attach(l2, 0, 1, 1, 1)
        self.travelz_entry = LengthEntry()
        grid1.attach(self.travelz_entry, 1, 1, 1, 1)

        l3 = Gtk.Label('Feed rate:', xalign=1)
        grid1.attach(l3, 0, 2, 1, 1)
        self.cncfeedrate_entry = LengthEntry()
        grid1.attach(self.cncfeedrate_entry, 1, 2, 1, 1)

        l4 = Gtk.Label('Tool dia:', xalign=1)
        grid1.attach(l4, 0, 3, 1, 1)
        self.cnctooldia_entry = LengthEntry()
        grid1.attach(self.cnctooldia_entry, 1, 3, 1, 1)

        self.generate_cnc_button = Gtk.Button(label='Generate')
        self.custom_box.pack_start(self.generate_cnc_button, expand=True, fill=False, padding=2)

        ## Paint Area
        self.paint_label = Gtk.Label(justify=Gtk.Justification.LEFT, xalign=0, margin_top=5)
        self.paint_label.set_markup('<b>Paint Area:</b>')
        self.custom_box.pack_start(self.paint_label, expand=True, fill=False, padding=2)

        grid2 = Gtk.Grid(column_spacing=3, row_spacing=2)
        self.custom_box.pack_start(grid2, expand=True, fill=False, padding=2)

        # Tool dia
        l5 = Gtk.Label('Tool dia:', xalign=1)
        grid2.attach(l5, 0, 0, 1, 1)
        self.painttooldia_entry = LengthEntry()
        grid2.attach(self.painttooldia_entry, 1, 0, 1, 1)

        # Overlap
        l6 = Gtk.Label('Overlap:', xalign=1)
        grid2.attach(l6, 0, 1, 1, 1)
        self.paintoverlap_entry = LengthEntry()
        grid2.attach(self.paintoverlap_entry, 1, 1, 1, 1)

        # Margin
        l7 = Gtk.Label('Margin:', xalign=1)
        grid2.attach(l7, 0, 2, 1, 1)
        self.paintmargin_entry = LengthEntry()
        grid2.attach(self.paintmargin_entry, 1, 2, 1, 1)

        # GO Button
        self.generate_paint_button = Gtk.Button(label='Generate')
        self.custom_box.pack_start(self.generate_paint_button, expand=True, fill=False, padding=2)


class ExcellonObjectUI(ObjectUI):
    """
    User interface for Excellon objects.
    """

    def __init__(self):
        ObjectUI.__init__(self, title='Excellon Object', icon_file='share/drill32.png')

        ## Plot options
        self.plot_options_label = Gtk.Label(justify=Gtk.Justification.LEFT, xalign=0, margin_top=5)
        self.plot_options_label.set_markup("<b>Plot Options:</b>")
        self.custom_box.pack_start(self.plot_options_label, expand=False, fill=True, padding=2)

        grid0 = Gtk.Grid(column_spacing=3, row_spacing=2)
        self.custom_box.pack_start(grid0, expand=True, fill=False, padding=2)

        self.plot_cb = FCCheckBox(label='Plot')
        grid0.attach(self.plot_cb, 0, 0, 1, 1)

        self.solid_cb = FCCheckBox(label='Solid')
        grid0.attach(self.solid_cb, 1, 0, 1, 1)

        ## Create CNC Job
        self.cncjob_label = Gtk.Label(justify=Gtk.Justification.LEFT, xalign=0, margin_top=5)
        self.cncjob_label.set_markup('<b>Create CNC Job</b>')
        self.custom_box.pack_start(self.cncjob_label, expand=True, fill=False, padding=2)

        grid1 = Gtk.Grid(column_spacing=3, row_spacing=2)
        self.custom_box.pack_start(grid1, expand=True, fill=False, padding=2)

        l1 = Gtk.Label('Cut Z:', xalign=1)
        grid1.attach(l1, 0, 0, 1, 1)
        self.cutz_entry = LengthEntry()
        grid1.attach(self.cutz_entry, 1, 0, 1, 1)

        l2 = Gtk.Label('Travel Z:', xalign=1)
        grid1.attach(l2, 0, 1, 1, 1)
        self.travelz_entry = LengthEntry()
        grid1.attach(self.travelz_entry, 1, 1, 1, 1)

        l3 = Gtk.Label('Feed rate:', xalign=1)
        grid1.attach(l3, 0, 2, 1, 1)
        self.feedrate_entry = LengthEntry()
        grid1.attach(self.feedrate_entry, 1, 2, 1, 1)

        l4 = Gtk.Label('Tools:', xalign=1)
        grid1.attach(l4, 0, 3, 1, 1)
        boxt = Gtk.Box()
        grid1.attach(boxt, 1, 3, 1, 1)
        self.tools_entry = FCEntry()
        boxt.pack_start(self.tools_entry, expand=True, fill=False, padding=2)
        self.choose_tools_button = Gtk.Button(label='Choose...')
        boxt.pack_start(self.choose_tools_button, expand=True, fill=False, padding=2)

        self.generate_cnc_button = Gtk.Button(label='Generate')
        self.custom_box.pack_start(self.generate_cnc_button, expand=True, fill=False, padding=2)


class GerberObjectUI(ObjectUI):
    """
    User interface for Gerber objects.
    """
    def __init__(self):
        ObjectUI.__init__(self, title='Gerber Object')

        ## Plot options
        self.plot_options_label = Gtk.Label(justify=Gtk.Justification.LEFT, xalign=0, margin_top=5)
        self.plot_options_label.set_markup("<b>Plot Options:</b>")
        self.custom_box.pack_start(self.plot_options_label, expand=False, fill=True, padding=2)

        grid0 = Gtk.Grid(column_spacing=3, row_spacing=2)
        self.custom_box.pack_start(grid0, expand=True, fill=False, padding=2)

        # Plot CB
        self.plot_cb = FCCheckBox(label='Plot')
        grid0.attach(self.plot_cb, 0, 0, 1, 1)

        # Solid CB
        self.solid_cb = FCCheckBox(label='Solid')
        grid0.attach(self.solid_cb, 1, 0, 1, 1)

        # Multicolored CB
        self.multicolored_cb = FCCheckBox(label='Multicolored')
        grid0.attach(self.multicolored_cb, 2, 0, 1, 1)

        ## Isolation Routing
        self.isolation_routing_label = Gtk.Label(justify=Gtk.Justification.LEFT, xalign=0, margin_top=5)
        self.isolation_routing_label.set_markup("<b>Isolation Routing:</b>")
        self.custom_box.pack_start(self.isolation_routing_label, expand=True, fill=False, padding=2)

        grid = Gtk.Grid(column_spacing=3, row_spacing=2)
        self.custom_box.pack_start(grid, expand=True, fill=False, padding=2)

        l1 = Gtk.Label('Tool diam:', xalign=1)
        grid.attach(l1, 0, 0, 1, 1)
        self.iso_tool_dia_entry = LengthEntry()
        grid.attach(self.iso_tool_dia_entry, 1, 0, 1, 1)

        l2 = Gtk.Label('Width (# passes):', xalign=1)
        grid.attach(l2, 0, 1, 1, 1)
        self.iso_width_entry = IntEntry()
        grid.attach(self.iso_width_entry, 1, 1, 1, 1)

        l3 = Gtk.Label('Pass overlap:', xalign=1)
        grid.attach(l3, 0, 2, 1, 1)
        self.iso_overlap_entry = FloatEntry()
        grid.attach(self.iso_overlap_entry, 1, 2, 1, 1)

        self.generate_iso_button = Gtk.Button(label='Generate Geometry')
        self.custom_box.pack_start(self.generate_iso_button, expand=True, fill=False, padding=2)

        ## Board cuttout
        self.isolation_routing_label = Gtk.Label(justify=Gtk.Justification.LEFT, xalign=0, margin_top=5)
        self.isolation_routing_label.set_markup("<b>Board cutout:</b>")
        self.custom_box.pack_start(self.isolation_routing_label, expand=True, fill=False, padding=2)

        grid2 = Gtk.Grid(column_spacing=3, row_spacing=2)
        self.custom_box.pack_start(grid2, expand=True, fill=False, padding=2)

        l4 = Gtk.Label('Tool dia:', xalign=1)
        grid2.attach(l4, 0, 0, 1, 1)
        self.cutout_tooldia_entry = LengthEntry()
        grid2.attach(self.cutout_tooldia_entry, 1, 0, 1, 1)

        l5 = Gtk.Label('Margin:', xalign=1)
        grid2.attach(l5, 0, 1, 1, 1)
        self.cutout_margin_entry = LengthEntry()
        grid2.attach(self.cutout_margin_entry, 1, 1, 1, 1)

        l6 = Gtk.Label('Gap size:', xalign=1)
        grid2.attach(l6, 0, 2, 1, 1)
        self.cutout_gap_entry = LengthEntry()
        grid2.attach(self.cutout_gap_entry, 1, 2, 1, 1)

        l7 = Gtk.Label('Gaps:', xalign=1)
        grid2.attach(l7, 0, 3, 1, 1)
        self.gaps_radio = RadioSet([{'label': '2 (T/B)', 'value': 'tb'},
                                    {'label': '2 (L/R)', 'value': 'lr'},
                                    {'label': '4', 'value': '4'}])
        grid2.attach(self.gaps_radio, 1, 3, 1, 1)

        self.generate_cutout_button = Gtk.Button(label='Generate Geometry')
        self.custom_box.pack_start(self.generate_cutout_button, expand=True, fill=False, padding=2)

        ## Non-copper regions
        self.noncopper_label = Gtk.Label(justify=Gtk.Justification.LEFT, xalign=0, margin_top=5)
        self.noncopper_label.set_markup("<b>Non-copper regions:</b>")
        self.custom_box.pack_start(self.noncopper_label, expand=True, fill=False, padding=2)

        grid3 = Gtk.Grid(column_spacing=3, row_spacing=2)
        self.custom_box.pack_start(grid3, expand=True, fill=False, padding=2)

        l8 = Gtk.Label('Boundary margin:', xalign=1)
        grid3.attach(l8, 0, 0, 1, 1)
        self.noncopper_margin_entry = LengthEntry()
        grid3.attach(self.noncopper_margin_entry, 1, 0, 1, 1)

        self.noncopper_rounded_cb = FCCheckBox(label="Rounded corners")
        grid3.attach(self.noncopper_rounded_cb, 0, 1, 2, 1)

        self.generate_noncopper_button = Gtk.Button(label='Generate Geometry')
        self.custom_box.pack_start(self.generate_noncopper_button, expand=True, fill=False, padding=2)

        ## Bounding box
        self.boundingbox_label = Gtk.Label(justify=Gtk.Justification.LEFT, xalign=0, margin_top=5)
        self.boundingbox_label.set_markup('<b>Bounding Box:</b>')
        self.custom_box.pack_start(self.boundingbox_label, expand=True, fill=False, padding=2)

        grid4 = Gtk.Grid(column_spacing=3, row_spacing=2)
        self.custom_box.pack_start(grid4, expand=True, fill=False, padding=2)

        l9 = Gtk.Label('Boundary Margin:', xalign=1)
        grid4.attach(l9, 0, 0, 1, 1)
        self.bbmargin_entry = LengthEntry()
        grid4.attach(self.bbmargin_entry, 1, 0, 1, 1)

        self.bbrounded_cb = FCCheckBox(label="Rounded corners")
        grid4.attach(self.bbrounded_cb, 0, 1, 2, 1)

        self.generate_bb_button = Gtk.Button(label='Generate Geometry')
        self.custom_box.pack_start(self.generate_bb_button, expand=True, fill=False, padding=2)