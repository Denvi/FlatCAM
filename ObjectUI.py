import sys
from PyQt4 import QtGui, QtCore
#from GUIElements import *
from GUIElements import FCEntry, FloatEntry, EvalEntry, FCCheckBox, \
    LengthEntry, FCTextArea, IntEntry, RadioSet, OptionalInputSection


class ObjectUI(QtGui.QWidget):
    """
    Base class for the UI of FlatCAM objects. Deriving classes should
    put UI elements in ObjectUI.custom_box (QtGui.QLayout).
    """

    def __init__(self, icon_file='share/flatcam_icon32.png', title='FlatCAM Object', parent=None):
        QtGui.QWidget.__init__(self, parent=parent)

        layout = QtGui.QVBoxLayout()
        self.setLayout(layout)

        ## Page Title box (spacing between children)
        self.title_box = QtGui.QHBoxLayout()
        layout.addLayout(self.title_box)

        ## Page Title icon
        pixmap = QtGui.QPixmap(icon_file)
        self.icon = QtGui.QLabel()
        self.icon.setPixmap(pixmap)
        self.title_box.addWidget(self.icon, stretch=0)

        ## Title label
        self.title_label = QtGui.QLabel("<font size=5><b>" + title + "</b></font>")
        self.title_label.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        self.title_box.addWidget(self.title_label, stretch=1)

        ## Object name
        self.name_box = QtGui.QHBoxLayout()
        layout.addLayout(self.name_box)
        name_label = QtGui.QLabel("Name:")
        self.name_box.addWidget(name_label)
        self.name_entry = FCEntry()
        self.name_box.addWidget(self.name_entry)

        ## Box box for custom widgets
        # This gets populated in offspring implementations.
        self.custom_box = QtGui.QVBoxLayout()
        layout.addLayout(self.custom_box)

        ###########################
        ## Common to all objects ##
        ###########################

        #### Scale ####
        self.scale_label = QtGui.QLabel('<b>Scale:</b>')
        self.scale_label.setToolTip(
            "Change the size of the object."
        )
        layout.addWidget(self.scale_label)

        self.scale_grid = QtGui.QGridLayout()
        layout.addLayout(self.scale_grid)

        # Factor
        faclabel = QtGui.QLabel('Factor:')
        faclabel.setToolTip(
            "Factor by which to multiply\n"
            "geometric features of this object."
        )
        self.scale_grid.addWidget(faclabel, 0, 0)
        self.scale_entry = FloatEntry()
        self.scale_entry.set_value(1.0)
        self.scale_grid.addWidget(self.scale_entry, 0, 1)

        # GO Button
        self.scale_button = QtGui.QPushButton('Scale')
        self.scale_button.setToolTip(
            "Perform scaling operation."
        )
        layout.addWidget(self.scale_button)

        #### Offset ####
        self.offset_label = QtGui.QLabel('<b>Offset:</b>')
        self.offset_label.setToolTip(
            "Change the position of this object."
        )
        layout.addWidget(self.offset_label)

        self.offset_grid = QtGui.QGridLayout()
        layout.addLayout(self.offset_grid)

        self.offset_vectorlabel = QtGui.QLabel('Vector:')
        self.offset_vectorlabel.setToolTip(
            "Amount by which to move the object\n"
            "in the x and y axes in (x, y) format."
        )
        self.offset_grid.addWidget(self.offset_vectorlabel, 0, 0)
        self.offsetvector_entry = EvalEntry()
        self.offsetvector_entry.setText("(0.0, 0.0)")
        self.offset_grid.addWidget(self.offsetvector_entry, 0, 1)

        self.offset_button = QtGui.QPushButton('Offset')
        self.offset_button.setToolTip(
            "Perform the offset operation."
        )
        layout.addWidget(self.offset_button)

        layout.addStretch()


class CNCObjectUI(ObjectUI):
    """
    User interface for CNCJob objects.
    """

    def __init__(self, parent=None):
        """
        Creates the user interface for CNCJob objects. GUI elements should
        be placed in ``self.custom_box`` to preserve the layout.
        """

        ObjectUI.__init__(self, title='CNC Job Object', icon_file='share/cnc32.png', parent=parent)

        # Scale and offset are not available for CNCJob objects.
        # Hiding from the GUI.
        for i in range(0, self.scale_grid.count()):
            self.scale_grid.itemAt(i).widget().hide()
        self.scale_label.hide()
        self.scale_button.hide()

        for i in range(0, self.offset_grid.count()):
            self.offset_grid.itemAt(i).widget().hide()
        self.offset_label.hide()
        self.offset_button.hide()

        ## Plot options
        self.plot_options_label = QtGui.QLabel("<b>Plot Options:</b>")
        self.custom_box.addWidget(self.plot_options_label)

        grid0 = QtGui.QGridLayout()
        self.custom_box.addLayout(grid0)

        # Plot CB
        # self.plot_cb = QtGui.QCheckBox('Plot')
        self.plot_cb = FCCheckBox('Plot')
        self.plot_cb.setToolTip(
            "Plot (show) this object."
        )
        grid0.addWidget(self.plot_cb, 0, 0)

        # Tool dia for plot
        tdlabel = QtGui.QLabel('Tool dia:')
        tdlabel.setToolTip(
            "Diameter of the tool to be\n"
            "rendered in the plot."
        )
        grid0.addWidget(tdlabel, 1, 0)
        self.tooldia_entry = LengthEntry()
        grid0.addWidget(self.tooldia_entry, 1, 1)

        # Update plot button
        self.updateplot_button = QtGui.QPushButton('Update Plot')
        self.updateplot_button.setToolTip(
            "Update the plot."
        )
        self.custom_box.addWidget(self.updateplot_button)

        ##################
        ## Export G-Code
        ##################
        self.export_gcode_label = QtGui.QLabel("<b>Export G-Code:</b>")
        self.export_gcode_label.setToolTip(
            "Export and save G-Code to\n"
            "make this object to a file."
        )
        self.custom_box.addWidget(self.export_gcode_label)

        # Prepend text to Gerber
        prependlabel = QtGui.QLabel('Prepend to G-Code:')
        prependlabel.setToolTip(
            "Type here any G-Code commands you would\n"
            "like to add to the beginning of the generated file."
        )
        self.custom_box.addWidget(prependlabel)

        self.prepend_text = FCTextArea()
        self.custom_box.addWidget(self.prepend_text)

        # Append text to Gerber
        appendlabel = QtGui.QLabel('Append to G-Code:')
        appendlabel.setToolTip(
            "Type here any G-Code commands you would\n"
            "like to append to the generated file.\n"
            "I.e.: M2 (End of program)"
        )
        self.custom_box.addWidget(appendlabel)

        self.append_text = FCTextArea()
        self.custom_box.addWidget(self.append_text)

        # Dwell
        grid1 = QtGui.QGridLayout()
        self.custom_box.addLayout(grid1)

        dwelllabel = QtGui.QLabel('Dwell:')
        dwelllabel.setToolTip(
            "Pause to allow the spindle to reach its\n"
            "speed before cutting."
        )
        dwelltime = QtGui.QLabel('Duration [sec.]:')
        dwelltime.setToolTip(
            "Number of second to dwell."
        )
        self.dwell_cb = FCCheckBox()
        self.dwelltime_entry = FCEntry()
        grid1.addWidget(dwelllabel, 0, 0)
        grid1.addWidget(self.dwell_cb, 0, 1)
        grid1.addWidget(dwelltime, 1, 0)
        grid1.addWidget(self.dwelltime_entry, 1, 1)

        # GO Button
        self.export_gcode_button = QtGui.QPushButton('Export G-Code')
        self.export_gcode_button.setToolTip(
            "Opens dialog to save G-Code\n"
            "file."
        )
        self.custom_box.addWidget(self.export_gcode_button)


class GeometryObjectUI(ObjectUI):
    """
    User interface for Geometry objects.
    """

    def __init__(self, parent=None):
        super(GeometryObjectUI, self).__init__(title='Geometry Object', icon_file='share/geometry32.png', parent=parent)

        ## Plot options
        self.plot_options_label = QtGui.QLabel("<b>Plot Options:</b>")
        self.custom_box.addWidget(self.plot_options_label)

        # Plot CB
        self.plot_cb = FCCheckBox(label='Plot')
        self.plot_cb.setToolTip(
            "Plot (show) this object."
        )
        self.custom_box.addWidget(self.plot_cb)

        #-----------------------------------
        # Create CNC Job
        #-----------------------------------
        self.cncjob_label = QtGui.QLabel('<b>Create CNC Job:</b>')
        self.cncjob_label.setToolTip(
            "Create a CNC Job object\n"
            "tracing the contours of this\n"
            "Geometry object."
        )
        self.custom_box.addWidget(self.cncjob_label)

        grid1 = QtGui.QGridLayout()
        self.custom_box.addLayout(grid1)

        cutzlabel = QtGui.QLabel('Cut Z:')
        cutzlabel.setToolTip(
            "Cutting depth (negative)\n"
            "below the copper surface."
        )
        grid1.addWidget(cutzlabel, 0, 0)
        self.cutz_entry = LengthEntry()
        grid1.addWidget(self.cutz_entry, 0, 1)

        # Travel Z
        travelzlabel = QtGui.QLabel('Travel Z:')
        travelzlabel.setToolTip(
            "Height of the tool when\n"
            "moving without cutting."
        )
        grid1.addWidget(travelzlabel, 1, 0)
        self.travelz_entry = LengthEntry()
        grid1.addWidget(self.travelz_entry, 1, 1)

        # Feedrate
        frlabel = QtGui.QLabel('Feed Rate:')
        frlabel.setToolTip(
            "Cutting speed in the XY\n"
            "plane in units per minute"
        )
        grid1.addWidget(frlabel, 2, 0)
        self.cncfeedrate_entry = LengthEntry()
        grid1.addWidget(self.cncfeedrate_entry, 2, 1)

        # Tooldia
        tdlabel = QtGui.QLabel('Tool dia:')
        tdlabel.setToolTip(
            "The diameter of the cutting\n"
            "tool (just for display)."
        )
        grid1.addWidget(tdlabel, 3, 0)
        self.cnctooldia_entry = LengthEntry()
        grid1.addWidget(self.cnctooldia_entry, 3, 1)

        # Spindlespeed
        spdlabel = QtGui.QLabel('Spindle speed:')
        spdlabel.setToolTip(
            "Speed of the spindle\n"
            "in RPM (optional)"
        )
        grid1.addWidget(spdlabel, 4, 0)
        self.cncspindlespeed_entry = IntEntry(allow_empty=True)
        grid1.addWidget(self.cncspindlespeed_entry, 4, 1)

        # Multi-pass
        mpasslabel = QtGui.QLabel('Multi-Depth:')
        mpasslabel.setToolTip(
            "Use multiple passes to limit\n"
            "the cut depth in each pass. Will\n"
            "cut multiple times until Cut Z is\n"
            "reached."
        )
        grid1.addWidget(mpasslabel, 5, 0)
        self.mpass_cb = FCCheckBox()
        grid1.addWidget(self.mpass_cb, 5, 1)

        maxdepthlabel = QtGui.QLabel('Depth/pass:')
        maxdepthlabel.setToolTip(
            "Depth of each pass (positive)."
        )
        grid1.addWidget(maxdepthlabel, 6, 0)
        self.maxdepth_entry = LengthEntry()
        grid1.addWidget(self.maxdepth_entry, 6, 1)

        self.ois_mpass = OptionalInputSection(self.mpass_cb, [self.maxdepth_entry])

        # Button
        self.generate_cnc_button = QtGui.QPushButton('Generate')
        self.generate_cnc_button.setToolTip(
            "Generate the CNC Job object."
        )
        self.custom_box.addWidget(self.generate_cnc_button)

        #------------------------------
        # Paint area
        #------------------------------
        self.paint_label = QtGui.QLabel('<b>Paint Area:</b>')
        self.paint_label.setToolTip(
            "Creates tool paths to cover the\n"
            "whole area of a polygon (remove\n"
            "all copper). You will be asked\n"
            "to click on the desired polygon."
        )
        self.custom_box.addWidget(self.paint_label)

        grid2 = QtGui.QGridLayout()
        self.custom_box.addLayout(grid2)

        # Tool dia
        ptdlabel = QtGui.QLabel('Tool dia:')
        ptdlabel.setToolTip(
            "Diameter of the tool to\n"
            "be used in the operation."
        )
        grid2.addWidget(ptdlabel, 0, 0)

        self.painttooldia_entry = LengthEntry()
        grid2.addWidget(self.painttooldia_entry, 0, 1)

        # Overlap
        ovlabel = QtGui.QLabel('Overlap:')
        ovlabel.setToolTip(
            "How much (fraction) of the tool\n"
            "width to overlap each tool pass."
        )
        grid2.addWidget(ovlabel, 1, 0)
        self.paintoverlap_entry = LengthEntry()
        grid2.addWidget(self.paintoverlap_entry, 1, 1)

        # Margin
        marginlabel = QtGui.QLabel('Margin:')
        marginlabel.setToolTip(
            "Distance by which to avoid\n"
            "the edges of the polygon to\n"
            "be painted."
        )
        grid2.addWidget(marginlabel, 2, 0)
        self.paintmargin_entry = LengthEntry()
        grid2.addWidget(self.paintmargin_entry, 2, 1)

        # Method
        methodlabel = QtGui.QLabel('Method:')
        methodlabel.setToolTip(
            "Algorithm to paint the polygon:<BR>"
            "<B>Standard</B>: Fixed step inwards.<BR>"
            "<B>Seed-based</B>: Outwards from seed."
        )
        grid2.addWidget(methodlabel, 3, 0)
        self.paintmethod_combo = RadioSet([
            {"label": "Standard", "value": "standard"},
            {"label": "Seed-based", "value": "seed"}
        ])
        grid2.addWidget(self.paintmethod_combo, 3, 1)

        # GO Button
        self.generate_paint_button = QtGui.QPushButton('Generate')
        self.generate_paint_button.setToolTip(
            "After clicking here, click inside\n"
            "the polygon you wish to be painted.\n"
            "A new Geometry object with the tool\n"
            "paths will be created."
        )
        self.custom_box.addWidget(self.generate_paint_button)


class ExcellonObjectUI(ObjectUI):
    """
    User interface for Excellon objects.
    """

    def __init__(self, parent=None):
        ObjectUI.__init__(self, title='Excellon Object',
                          icon_file='share/drill32.png',
                          parent=parent)

        #### Plot options ####

        self.plot_options_label = QtGui.QLabel("<b>Plot Options:</b>")
        self.custom_box.addWidget(self.plot_options_label)

        grid0 = QtGui.QGridLayout()
        self.custom_box.addLayout(grid0)
        self.plot_cb = FCCheckBox(label='Plot')
        self.plot_cb.setToolTip(
            "Plot (show) this object."
        )
        grid0.addWidget(self.plot_cb, 0, 0)
        self.solid_cb = FCCheckBox(label='Solid')
        self.solid_cb.setToolTip(
            "Solid circles."
        )
        grid0.addWidget(self.solid_cb, 0, 1)

        #### Tools ####

        self.tools_table_label = QtGui.QLabel('<b>Tools</b>')
        self.tools_table_label.setToolTip(
            "Tools in this Excellon object."
        )
        self.custom_box.addWidget(self.tools_table_label)
        self.tools_table = QtGui.QTableWidget()
        self.tools_table.setFixedHeight(100)
        self.custom_box.addWidget(self.tools_table)

        #### Create CNC Job ####

        self.cncjob_label = QtGui.QLabel('<b>Create CNC Job</b>')
        self.cncjob_label.setToolTip(
            "Create a CNC Job object\n"
            "for this drill object."
        )
        self.custom_box.addWidget(self.cncjob_label)

        grid1 = QtGui.QGridLayout()
        self.custom_box.addLayout(grid1)

        cutzlabel = QtGui.QLabel('Cut Z:')
        cutzlabel.setToolTip(
            "Drill depth (negative)\n"
            "below the copper surface."
        )
        grid1.addWidget(cutzlabel, 0, 0)
        self.cutz_entry = LengthEntry()
        grid1.addWidget(self.cutz_entry, 0, 1)

        travelzlabel = QtGui.QLabel('Travel Z:')
        travelzlabel.setToolTip(
            "Tool height when travelling\n"
            "across the XY plane."
        )
        grid1.addWidget(travelzlabel, 1, 0)
        self.travelz_entry = LengthEntry()
        grid1.addWidget(self.travelz_entry, 1, 1)

        frlabel = QtGui.QLabel('Feed rate:')
        frlabel.setToolTip(
            "Tool speed while drilling\n"
            "(in units per minute)."
        )
        grid1.addWidget(frlabel, 2, 0)
        self.feedrate_entry = LengthEntry()
        grid1.addWidget(self.feedrate_entry, 2, 1)

        # Tool change:
        toolchlabel = QtGui.QLabel("Tool change:")
        toolchlabel.setToolTip(
            "Include tool-change sequence\n"
            "in G-Code (Pause for tool change)."
        )
        self.toolchange_cb = FCCheckBox()
        grid1.addWidget(toolchlabel, 3, 0)
        grid1.addWidget(self.toolchange_cb, 3, 1)

        # Tool change Z:
        toolchzlabel = QtGui.QLabel("Tool change Z:")
        toolchzlabel.setToolTip(
            "Z-axis position (height) for\n"
            "tool change."
        )
        grid1.addWidget(toolchzlabel, 4, 0)
        self.toolchangez_entry = LengthEntry()
        grid1.addWidget(self.toolchangez_entry, 4, 1)
        self.ois_tcz = OptionalInputSection(self.toolchange_cb, [self.toolchangez_entry])

        # Spindlespeed
        spdlabel = QtGui.QLabel('Spindle speed:')
        spdlabel.setToolTip(
            "Speed of the spindle\n"
            "in RPM (optional)"
        )
        grid1.addWidget(spdlabel, 5, 0)
        self.spindlespeed_entry = IntEntry(allow_empty=True)
        grid1.addWidget(self.spindlespeed_entry, 5, 1)

        choose_tools_label = QtGui.QLabel(
            "Select from the tools section above\n"
            "the tools you want to include."
        )
        self.custom_box.addWidget(choose_tools_label)

        self.generate_cnc_button = QtGui.QPushButton('Generate')
        self.generate_cnc_button.setToolTip(
            "Generate the CNC Job."
        )
        self.custom_box.addWidget(self.generate_cnc_button)

        #### Milling Holes ####
        self.mill_hole_label = QtGui.QLabel('<b>Mill Holes</b>')
        self.mill_hole_label.setToolTip(
            "Create Geometry for milling holes."
        )
        self.custom_box.addWidget(self.mill_hole_label)

        grid1 = QtGui.QGridLayout()
        self.custom_box.addLayout(grid1)
        tdlabel = QtGui.QLabel('Tool dia:')
        tdlabel.setToolTip(
            "Diameter of the cutting tool."
        )
        grid1.addWidget(tdlabel, 0, 0)
        self.tooldia_entry = LengthEntry()
        grid1.addWidget(self.tooldia_entry, 0, 1)

        choose_tools_label2 = QtGui.QLabel(
            "Select from the tools section above\n"
            "the tools you want to include."
        )
        self.custom_box.addWidget(choose_tools_label2)

        self.generate_milling_button = QtGui.QPushButton('Generate Geometry')
        self.generate_milling_button.setToolTip(
            "Create the Geometry Object\n"
            "for milling toolpaths."
        )
        self.custom_box.addWidget(self.generate_milling_button)


class GerberObjectUI(ObjectUI):
    """
    User interface for Gerber objects.
    """

    def __init__(self, parent=None):
        ObjectUI.__init__(self, title='Gerber Object', parent=parent)

        ## Plot options
        self.plot_options_label = QtGui.QLabel("<b>Plot Options:</b>")
        self.custom_box.addWidget(self.plot_options_label)

        grid0 = QtGui.QGridLayout()
        self.custom_box.addLayout(grid0)
        # Plot CB
        self.plot_cb = FCCheckBox(label='Plot')
        self.plot_options_label.setToolTip(
            "Plot (show) this object."
        )
        grid0.addWidget(self.plot_cb, 0, 0)

        # Solid CB
        self.solid_cb = FCCheckBox(label='Solid')
        self.solid_cb.setToolTip(
            "Solid color polygons."
        )
        grid0.addWidget(self.solid_cb, 0, 1)

        # Multicolored CB
        self.multicolored_cb = FCCheckBox(label='Multicolored')
        self.multicolored_cb.setToolTip(
            "Draw polygons in different colors."
        )
        grid0.addWidget(self.multicolored_cb, 0, 2)

        ## Isolation Routing
        self.isolation_routing_label = QtGui.QLabel("<b>Isolation Routing:</b>")
        self.isolation_routing_label.setToolTip(
            "Create a Geometry object with\n"
            "toolpaths to cut outside polygons."
        )
        self.custom_box.addWidget(self.isolation_routing_label)

        grid1 = QtGui.QGridLayout()
        self.custom_box.addLayout(grid1)
        tdlabel = QtGui.QLabel('Tool dia:')
        tdlabel.setToolTip(
            "Diameter of the cutting tool."
        )
        grid1.addWidget(tdlabel, 0, 0)
        self.iso_tool_dia_entry = LengthEntry()
        grid1.addWidget(self.iso_tool_dia_entry, 0, 1)

        passlabel = QtGui.QLabel('Width (# passes):')
        passlabel.setToolTip(
            "Width of the isolation gap in\n"
            "number (integer) of tool widths."
        )
        grid1.addWidget(passlabel, 1, 0)
        self.iso_width_entry = IntEntry()
        grid1.addWidget(self.iso_width_entry, 1, 1)

        overlabel = QtGui.QLabel('Pass overlap:')
        overlabel.setToolTip(
            "How much (fraction of tool width)\n"
            "to overlap each pass."
        )
        grid1.addWidget(overlabel, 2, 0)
        self.iso_overlap_entry = FloatEntry()
        grid1.addWidget(self.iso_overlap_entry, 2, 1)

        # combine all passes CB
        self.combine_passes_cb = FCCheckBox(label='Combine Passes')
        self.combine_passes_cb.setToolTip(
            "Combine all passes into one object"
        )
        grid1.addWidget(self.combine_passes_cb, 3, 0)


        self.generate_iso_button = QtGui.QPushButton('Generate Geometry')
        self.generate_iso_button.setToolTip(
            "Create the Geometry Object\n"
            "for isolation routing."
        )
        self.custom_box.addWidget(self.generate_iso_button)

        ## Board cuttout
        self.board_cutout_label = QtGui.QLabel("<b>Board cutout:</b>")
        self.board_cutout_label.setToolTip(
            "Create toolpaths to cut around\n"
            "the PCB and separate it from\n"
            "the original board."
        )
        self.custom_box.addWidget(self.board_cutout_label)

        grid2 = QtGui.QGridLayout()
        self.custom_box.addLayout(grid2)
        tdclabel = QtGui.QLabel('Tool dia:')
        tdclabel.setToolTip(
            "Diameter of the cutting tool."
        )
        grid2.addWidget(tdclabel, 0, 0)
        self.cutout_tooldia_entry = LengthEntry()
        grid2.addWidget(self.cutout_tooldia_entry, 0, 1)

        marginlabel = QtGui.QLabel('Margin:')
        marginlabel.setToolTip(
            "Distance from objects at which\n"
            "to draw the cutout."
        )
        grid2.addWidget(marginlabel, 1, 0)
        self.cutout_margin_entry = LengthEntry()
        grid2.addWidget(self.cutout_margin_entry, 1, 1)

        gaplabel = QtGui.QLabel('Gap size:')
        gaplabel.setToolTip(
            "Size of the gaps in the toolpath\n"
            "that will remain to hold the\n"
            "board in place."
        )
        grid2.addWidget(gaplabel, 2, 0)
        self.cutout_gap_entry = LengthEntry()
        grid2.addWidget(self.cutout_gap_entry, 2, 1)

        gapslabel = QtGui.QLabel('Gaps:')
        gapslabel.setToolTip(
            "Where to place the gaps, Top/Bottom\n"
            "Left/Rigt, or on all 4 sides."
        )
        grid2.addWidget(gapslabel, 3, 0)
        self.gaps_radio = RadioSet([{'label': '2 (T/B)', 'value': 'tb'},
                                    {'label': '2 (L/R)', 'value': 'lr'},
                                    {'label': '4', 'value': '4'}])
        grid2.addWidget(self.gaps_radio, 3, 1)

        self.generate_cutout_button = QtGui.QPushButton('Generate Geometry')
        self.generate_cutout_button.setToolTip(
            "Generate the geometry for\n"
            "the board cutout."
        )
        self.custom_box.addWidget(self.generate_cutout_button)

        ## Non-copper regions
        self.noncopper_label = QtGui.QLabel("<b>Non-copper regions:</b>")
        self.noncopper_label.setToolTip(
            "Create polygons covering the\n"
            "areas without copper on the PCB.\n"
            "Equivalent to the inverse of this\n"
            "object. Can be used to remove all\n"
            "copper from a specified region."
        )
        self.custom_box.addWidget(self.noncopper_label)

        grid3 = QtGui.QGridLayout()
        self.custom_box.addLayout(grid3)

        # Margin
        bmlabel = QtGui.QLabel('Boundary Margin:')
        bmlabel.setToolTip(
            "Specify the edge of the PCB\n"
            "by drawing a box around all\n"
            "objects with this minimum\n"
            "distance."
        )
        grid3.addWidget(bmlabel, 0, 0)
        self.noncopper_margin_entry = LengthEntry()
        grid3.addWidget(self.noncopper_margin_entry, 0, 1)

        # Rounded corners
        self.noncopper_rounded_cb = FCCheckBox(label="Rounded corners")
        self.noncopper_rounded_cb.setToolTip(
            "Creates a Geometry objects with polygons\n"
            "covering the copper-free areas of the PCB."
        )
        grid3.addWidget(self.noncopper_rounded_cb, 1, 0, 1, 2)

        self.generate_noncopper_button = QtGui.QPushButton('Generate Geometry')
        self.custom_box.addWidget(self.generate_noncopper_button)

        ## Bounding box
        self.boundingbox_label = QtGui.QLabel('<b>Bounding Box:</b>')
        self.custom_box.addWidget(self.boundingbox_label)

        grid4 = QtGui.QGridLayout()
        self.custom_box.addLayout(grid4)

        bbmargin = QtGui.QLabel('Boundary Margin:')
        bbmargin.setToolTip(
            "Distance of the edges of the box\n"
            "to the nearest polygon."
        )
        grid4.addWidget(bbmargin, 0, 0)
        self.bbmargin_entry = LengthEntry()
        grid4.addWidget(self.bbmargin_entry, 0, 1)

        self.bbrounded_cb = FCCheckBox(label="Rounded corners")
        self.bbrounded_cb.setToolTip(
            "If the bounding box is \n"
            "to have rounded corners\n"
            "their radius is equal to\n"
            "the margin."
        )
        grid4.addWidget(self.bbrounded_cb, 1, 0, 1, 2)

        self.generate_bb_button = QtGui.QPushButton('Generate Geometry')
        self.generate_bb_button.setToolTip(
            "Genrate the Geometry object."
        )
        self.custom_box.addWidget(self.generate_bb_button)


# def main():
#
#     app = QtGui.QApplication(sys.argv)
#     fc = GerberObjectUI()
#     sys.exit(app.exec_())
#
#
# if __name__ == '__main__':
#     main()