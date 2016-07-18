from PyQt4 import QtGui, QtCore, Qt
from GUIElements import *


class FlatCAMGUI(QtGui.QMainWindow):

    # Emitted when persistent window geometry needs to be retained
    geom_update = QtCore.pyqtSignal(int, int, int, int, int, name='geomUpdate')

    def __init__(self, version):
        super(FlatCAMGUI, self).__init__()

        # Divine icon pack by Ipapun @ finicons.com

        ############
        ### Menu ###
        ############
        self.menu = self.menuBar()

        ### File ###
        self.menufile = self.menu.addMenu('&File')

        # New
        self.menufilenew = QtGui.QAction(QtGui.QIcon('share/file16.png'), '&New', self)
        self.menufile.addAction(self.menufilenew)

        self.menufileopenproject = QtGui.QAction(QtGui.QIcon('share/folder16.png'), 'Open &Project ...', self)
        self.menufile.addAction(self.menufileopenproject)

        # Open gerber ...
        self.menufileopengerber = QtGui.QAction('Open &Gerber ...', self)
        self.menufile.addAction(self.menufileopengerber)

        # Open Excellon ...
        self.menufileopenexcellon = QtGui.QAction('Open &Excellon ...', self)
        self.menufile.addAction(self.menufileopenexcellon)

        # Open G-Code ...
        self.menufileopengcode = QtGui.QAction('Open G-&Code ...', self)
        self.menufile.addAction(self.menufileopengcode)

        # Recent
        self.recent = self.menufile.addMenu("Recent files")

        # Separator
        self.menufile.addSeparator()

        # Save Defaults
        self.menufilesavedefaults = QtGui.QAction('Save &Defaults', self)
        self.menufile.addAction(self.menufilesavedefaults)

        # Separator
        self.menufile.addSeparator()

        # Import SVG ...
        self.menufileimportsvg = QtGui.QAction('Import &SVG ...', self)
        self.menufile.addAction(self.menufileimportsvg)

        # Export SVG ...
        self.menufileexportsvg = QtGui.QAction('Export &SVG ...', self)
        self.menufile.addAction(self.menufileexportsvg)

        # Separator
        self.menufile.addSeparator()

        # Save Project
        self.menufilesaveproject = QtGui.QAction(QtGui.QIcon('share/floppy16.png'), '&Save Project', self)
        self.menufile.addAction(self.menufilesaveproject)

        # Save Project As ...
        self.menufilesaveprojectas = QtGui.QAction('Save Project &As ...', self)
        self.menufile.addAction(self.menufilesaveprojectas)

        # Save Project Copy ...
        self.menufilesaveprojectcopy = QtGui.QAction('Save Project C&opy ...', self)
        self.menufile.addAction(self.menufilesaveprojectcopy)

        # Separator
        self.menufile.addSeparator()

        # Quit
        exit_action = QtGui.QAction(QtGui.QIcon('share/power16.png'), 'E&xit', self)
        # exitAction.setShortcut('Ctrl+Q')
        # exitAction.setStatusTip('Exit application')
        exit_action.triggered.connect(QtGui.qApp.quit)

        self.menufile.addAction(exit_action)

        ### Edit ###
        self.menuedit = self.menu.addMenu('&Edit')
        self.menueditnew = self.menuedit.addAction(QtGui.QIcon('share/new_geo16.png'), 'New Geometry')
        self.menueditedit = self.menuedit.addAction(QtGui.QIcon('share/edit16.png'), 'Edit Geometry')
        self.menueditok = self.menuedit.addAction(QtGui.QIcon('share/edit_ok16.png'), 'Update Geometry')
        #self.menueditok.
        #self.menueditcancel = self.menuedit.addAction(QtGui.QIcon('share/cancel_edit16.png'), "Cancel Edit")
        self.menueditjoin = self.menuedit.addAction(QtGui.QIcon('share/join16.png'), 'Join Geometry')
        self.menueditdelete = self.menuedit.addAction(QtGui.QIcon('share/trash16.png'), 'Delete')

        ### Options ###
        self.menuoptions = self.menu.addMenu('&Options')
        self.menuoptions_transfer = self.menuoptions.addMenu('Transfer options')
        self.menuoptions_transfer_a2p = self.menuoptions_transfer.addAction("Application to Project")
        self.menuoptions_transfer_p2a = self.menuoptions_transfer.addAction("Project to Application")
        self.menuoptions_transfer_p2o = self.menuoptions_transfer.addAction("Project to Object")
        self.menuoptions_transfer_o2p = self.menuoptions_transfer.addAction("Object to Project")
        self.menuoptions_transfer_a2o = self.menuoptions_transfer.addAction("Application to Object")
        self.menuoptions_transfer_o2a = self.menuoptions_transfer.addAction("Object to Application")

        ### View ###
        self.menuview = self.menu.addMenu('&View')
        self.menuviewenable = self.menuview.addAction(QtGui.QIcon('share/replot16.png'), 'Enable all plots')
        self.menuviewdisableall = self.menuview.addAction(QtGui.QIcon('share/clear_plot16.png'), 'Disable all plots')
        self.menuviewdisableother = self.menuview.addAction(QtGui.QIcon('share/clear_plot16.png'),
                                                            'Disable non-selected')

        ### Tool ###
        #self.menutool = self.menu.addMenu('&Tool')
        self.menutool = QtGui.QMenu('&Tool')
        self.menutoolaction = self.menu.addMenu(self.menutool)
        self.menutoolshell = self.menutool.addAction(QtGui.QIcon('share/shell16.png'), '&Command Line')

        ### Help ###
        self.menuhelp = self.menu.addMenu('&Help')
        self.menuhelp_about = self.menuhelp.addAction(QtGui.QIcon('share/tv16.png'), 'About FlatCAM')
        self.menuhelp_home = self.menuhelp.addAction(QtGui.QIcon('share/home16.png'), 'Home')
        self.menuhelp_manual = self.menuhelp.addAction(QtGui.QIcon('share/globe16.png'), 'Manual')

        ####################
        ### Context menu ###
        ####################

        self.menuproject = QtGui.QMenu()
        self.menuprojectenable = self.menuproject.addAction('Enable')
        self.menuprojectdisable = self.menuproject.addAction('Disable')
        self.menuproject.addSeparator()
        self.menuprojectgeneratecnc = self.menuproject.addAction('Generate CNC')
        self.menuproject.addSeparator()
        self.menuprojectdelete = self.menuproject.addAction('Delete')

        ###############
        ### Toolbar ###
        ###############
        self.toolbarfile = QtGui.QToolBar('File')
        self.addToolBar(self.toolbarfile)
        self.file_new_btn = self.toolbarfile.addAction(QtGui.QIcon('share/file32.png'), "New project")
        self.file_open_btn = self.toolbarfile.addAction(QtGui.QIcon('share/folder32.png'), "Open project")
        self.file_save_btn = self.toolbarfile.addAction(QtGui.QIcon('share/floppy32.png'), "Save project")

        self.toolbargeo = QtGui.QToolBar('Edit')
        self.addToolBar(self.toolbargeo)

        self.newgeo_btn = self.toolbargeo.addAction(QtGui.QIcon('share/new_geo32.png'), "New Blank Geometry")
        self.delete_btn = self.toolbargeo.addAction(QtGui.QIcon('share/cancel_edit32.png'), "&Delete")
        self.editgeo_btn = self.toolbargeo.addAction(QtGui.QIcon('share/edit32.png'), "Edit Geometry")
        self.updategeo_btn = self.toolbargeo.addAction(QtGui.QIcon('share/edit_ok32.png'), "Update Geometry")
        self.updategeo_btn.setEnabled(False)
        #self.canceledit_btn = self.toolbar.addAction(QtGui.QIcon('share/cancel_edit32.png'), "Cancel Edit")

        self.toolbarview = QtGui.QToolBar('View')
        self.addToolBar(self.toolbarview)
        self.zoom_fit_btn = self.toolbarview.addAction(QtGui.QIcon('share/zoom_fit32.png'), "&Zoom Fit")
        self.zoom_in_btn = self.toolbarview.addAction(QtGui.QIcon('share/zoom_in32.png'), "&Zoom In")
        self.zoom_out_btn = self.toolbarview.addAction(QtGui.QIcon('share/zoom_out32.png'), "&Zoom Out")
        self.replot_btn = self.toolbarview.addAction(QtGui.QIcon('share/replot32.png'), "&Enable all")
        self.clear_plot_btn = self.toolbarview.addAction(QtGui.QIcon('share/clear_plot32.png'), "&Disable non-selected")

        self.toolbartools = QtGui.QToolBar('Tools')
        self.addToolBar(self.toolbartools)
        self.shell_btn = self.toolbartools.addAction(QtGui.QIcon('share/shell32.png'), "&Command Line")

        ################
        ### Splitter ###
        ################
        self.splitter = QtGui.QSplitter()
        self.setCentralWidget(self.splitter)

        ################
        ### Notebook ###
        ################
        self.notebook = QtGui.QTabWidget()
        # self.notebook.setMinimumWidth(250)

        ### Projet ###
        project_tab = QtGui.QWidget()
        # project_tab.setMinimumWidth(250)  # Hack
        self.project_tab_layout = QtGui.QVBoxLayout(project_tab)
        self.project_tab_layout.setContentsMargins(2, 2, 2, 2)
        self.notebook.addTab(project_tab, "Project")

        ### Selected ###
        self.selected_tab = QtGui.QWidget()
        self.selected_tab_layout = QtGui.QVBoxLayout(self.selected_tab)
        self.selected_tab_layout.setContentsMargins(2, 2, 2, 2)
        self.selected_scroll_area = VerticalScrollArea()
        self.selected_tab_layout.addWidget(self.selected_scroll_area)
        self.notebook.addTab(self.selected_tab, "Selected")

        ### Options ###
        self.options_tab = QtGui.QWidget()
        self.options_tab.setContentsMargins(0, 0, 0, 0)
        self.options_tab_layout = QtGui.QVBoxLayout(self.options_tab)
        self.options_tab_layout.setContentsMargins(2, 2, 2, 2)

        hlay1 = QtGui.QHBoxLayout()
        self.options_tab_layout.addLayout(hlay1)

        self.icon = QtGui.QLabel()
        self.icon.setPixmap(QtGui.QPixmap('share/gear48.png'))
        hlay1.addWidget(self.icon)

        self.options_combo = QtGui.QComboBox()
        self.options_combo.addItem("APPLICATION DEFAULTS")
        self.options_combo.addItem("PROJECT OPTIONS")
        hlay1.addWidget(self.options_combo)
        hlay1.addStretch()

        self.options_scroll_area = VerticalScrollArea()
        self.options_tab_layout.addWidget(self.options_scroll_area)

        self.notebook.addTab(self.options_tab, "Options")

        ### Tool ###
        self.tool_tab = QtGui.QWidget()
        self.tool_tab_layout = QtGui.QVBoxLayout(self.tool_tab)
        self.tool_tab_layout.setContentsMargins(2, 2, 2, 2)
        self.notebook.addTab(self.tool_tab, "Tool")
        self.tool_scroll_area = VerticalScrollArea()
        self.tool_tab_layout.addWidget(self.tool_scroll_area)

        self.splitter.addWidget(self.notebook)

        ######################
        ### Plot and other ###
        ######################
        right_widget = QtGui.QWidget()
        # right_widget.setContentsMargins(0, 0, 0, 0)
        self.splitter.addWidget(right_widget)
        self.right_layout = QtGui.QVBoxLayout()
        self.right_layout.setMargin(0)
        # self.right_layout.setContentsMargins(0, 0, 0, 0)
        right_widget.setLayout(self.right_layout)

        ################
        ### Info bar ###
        ################
        infobar = self.statusBar()

        #self.info_label = QtGui.QLabel("Welcome to FlatCAM.")
        #self.info_label.setFrameStyle(QtGui.QFrame.StyledPanel | QtGui.QFrame.Plain)
        #infobar.addWidget(self.info_label, stretch=1)
        self.fcinfo = FlatCAMInfoBar()
        infobar.addWidget(self.fcinfo, stretch=1)

        self.position_label = QtGui.QLabel("")
        #self.position_label.setFrameStyle(QtGui.QFrame.StyledPanel | QtGui.QFrame.Plain)
        self.position_label.setMinimumWidth(110)
        infobar.addWidget(self.position_label)

        self.units_label = QtGui.QLabel("[in]")
        # self.units_label.setFrameStyle(QtGui.QFrame.StyledPanel | QtGui.QFrame.Plain)
        self.units_label.setMargin(2)
        infobar.addWidget(self.units_label)

        self.progress_bar = QtGui.QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        #infobar.addWidget(self.progress_bar)

        self.activity_view = FlatCAMActivityView()
        infobar.addWidget(self.activity_view)

        #############
        ### Icons ###
        #############
        self.app_icon = QtGui.QIcon()
        self.app_icon.addFile('share/flatcam_icon16.png', QtCore.QSize(16, 16))
        self.app_icon.addFile('share/flatcam_icon24.png', QtCore.QSize(24, 24))
        self.app_icon.addFile('share/flatcam_icon32.png', QtCore.QSize(32, 32))
        self.app_icon.addFile('share/flatcam_icon48.png', QtCore.QSize(48, 48))
        self.app_icon.addFile('share/flatcam_icon128.png', QtCore.QSize(128, 128))
        self.app_icon.addFile('share/flatcam_icon256.png', QtCore.QSize(256, 256))
        self.setWindowIcon(self.app_icon)

        self.setGeometry(100, 100, 1024, 650)
        self.setWindowTitle('FlatCAM %s - Development Version' % version)
        self.show()

    def closeEvent(self, event):
        grect = self.geometry()
        self.geom_update.emit(grect.x(), grect.y(), grect.width(), grect.height(), self.splitter.sizes()[0])
        QtGui.qApp.quit()


class FlatCAMActivityView(QtGui.QWidget):

    def __init__(self, parent=None):
        super(FlatCAMActivityView, self).__init__(parent=parent)

        self.setMinimumWidth(200)

        self.icon = QtGui.QLabel(self)
        self.icon.setGeometry(0, 0, 12, 12)
        self.movie = QtGui.QMovie("share/active.gif")
        self.icon.setMovie(self.movie)
        #self.movie.start()

        layout = QtGui.QHBoxLayout()
        layout.setContentsMargins(5, 0, 5, 0)
        layout.setAlignment(QtCore.Qt.AlignLeft)
        self.setLayout(layout)

        layout.addWidget(self.icon)
        self.text = QtGui.QLabel(self)
        self.text.setText("Idle.")

        layout.addWidget(self.text)

    def set_idle(self):
        self.movie.stop()
        self.text.setText("Idle.")

    def set_busy(self, msg):
        self.movie.start()
        self.text.setText(msg)


class FlatCAMInfoBar(QtGui.QWidget):

    def __init__(self, parent=None):
        super(FlatCAMInfoBar, self).__init__(parent=parent)

        self.icon = QtGui.QLabel(self)
        self.icon.setGeometry(0, 0, 12, 12)
        self.pmap = QtGui.QPixmap('share/graylight12.png')
        self.icon.setPixmap(self.pmap)

        layout = QtGui.QHBoxLayout()
        layout.setContentsMargins(5, 0, 5, 0)
        self.setLayout(layout)

        layout.addWidget(self.icon)

        self.text = QtGui.QLabel(self)
        self.text.setText("Hello!")
        self.text.setToolTip("Hello!")

        layout.addWidget(self.text)

        layout.addStretch()

    def set_text_(self, text):
        self.text.setText(text)
        self.text.setToolTip(text)

    def set_status(self, text, level="info"):
        level = str(level)
        self.pmap.fill()
        if level == "error":
            self.pmap = QtGui.QPixmap('share/redlight12.png')
        elif level == "success":
            self.pmap = QtGui.QPixmap('share/greenlight12.png')
        elif level == "warning":
            self.pmap = QtGui.QPixmap('share/yellowlight12.png')
        else:
            self.pmap = QtGui.QPixmap('share/graylight12.png')

        self.icon.setPixmap(self.pmap)
        self.set_text_(text)


class OptionsGroupUI(QtGui.QGroupBox):
    def __init__(self, title, parent=None):
        QtGui.QGroupBox.__init__(self, title, parent=parent)
        self.setStyleSheet("""
        QGroupBox
        {
            font-size: 16px;
            font-weight: bold;
        }
        """)

        self.layout = QtGui.QVBoxLayout()
        self.setLayout(self.layout)


class GerberOptionsGroupUI(OptionsGroupUI):
    def __init__(self, parent=None):
        OptionsGroupUI.__init__(self, "Gerber Options", parent=parent)

        ## Plot options
        self.plot_options_label = QtGui.QLabel("<b>Plot Options:</b>")
        self.layout.addWidget(self.plot_options_label)

        grid0 = QtGui.QGridLayout()
        self.layout.addLayout(grid0)
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
        self.layout.addWidget(self.isolation_routing_label)

        grid1 = QtGui.QGridLayout()
        self.layout.addLayout(grid1)
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
        
        self.combine_passes_cb = FCCheckBox(label='Combine Passes')
        self.combine_passes_cb.setToolTip(
            "Combine all passes into one object"
        )
        grid1.addWidget(self.combine_passes_cb, 3, 0)

        ## Clear non-copper regions
        self.clearcopper_label = QtGui.QLabel("<b>Clear non-copper:</b>")
        self.clearcopper_label.setToolTip(
            "Create a Geometry object with\n"
            "toolpaths to cut all non-copper regions."
        )
        self.layout.addWidget(self.clearcopper_label)

        grid5 = QtGui.QGridLayout()
        self.layout.addLayout(grid5)
        ncctdlabel = QtGui.QLabel('Tools dia:')
        ncctdlabel.setToolTip(
            "Diameters of the cutting tools, separated by ','"
        )
        grid5.addWidget(ncctdlabel, 0, 0)
        self.ncc_tool_dia_entry = FCEntry()
        grid5.addWidget(self.ncc_tool_dia_entry, 0, 1)

        nccoverlabel = QtGui.QLabel('Overlap:')
        nccoverlabel.setToolTip(
            "How much (fraction of tool width)\n"
            "to overlap each pass."
        )
        grid5.addWidget(nccoverlabel, 1, 0)
        self.ncc_overlap_entry = FloatEntry()
        grid5.addWidget(self.ncc_overlap_entry, 1, 1)

        nccmarginlabel = QtGui.QLabel('Margin:')
        nccmarginlabel.setToolTip(
            "Bounding box margin."
        )
        grid5.addWidget(nccmarginlabel, 2, 0)
        self.ncc_margin_entry = FloatEntry()
        grid5.addWidget(self.ncc_margin_entry, 2, 1)

        ## Board cuttout
        self.board_cutout_label = QtGui.QLabel("<b>Board cutout:</b>")
        self.board_cutout_label.setToolTip(
            "Create toolpaths to cut around\n"
            "the PCB and separate it from\n"
            "the original board."
        )
        self.layout.addWidget(self.board_cutout_label)

        grid2 = QtGui.QGridLayout()
        self.layout.addLayout(grid2)
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

        ## Non-copper regions
        self.noncopper_label = QtGui.QLabel("<b>Non-copper regions:</b>")
        self.noncopper_label.setToolTip(
            "Create polygons covering the\n"
            "areas without copper on the PCB.\n"
            "Equivalent to the inverse of this\n"
            "object. Can be used to remove all\n"
            "copper from a specified region."
        )
        self.layout.addWidget(self.noncopper_label)

        grid3 = QtGui.QGridLayout()
        self.layout.addLayout(grid3)

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

        ## Bounding box
        self.boundingbox_label = QtGui.QLabel('<b>Bounding Box:</b>')
        self.layout.addWidget(self.boundingbox_label)

        grid4 = QtGui.QGridLayout()
        self.layout.addLayout(grid4)

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


class ExcellonOptionsGroupUI(OptionsGroupUI):
    def __init__(self, parent=None):
        OptionsGroupUI.__init__(self, "Excellon Options", parent=parent)

        ## Plot options
        self.plot_options_label = QtGui.QLabel("<b>Plot Options:</b>")
        self.layout.addWidget(self.plot_options_label)

        grid0 = QtGui.QGridLayout()
        self.layout.addLayout(grid0)
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

        ## Create CNC Job
        self.cncjob_label = QtGui.QLabel('<b>Create CNC Job</b>')
        self.cncjob_label.setToolTip(
            "Create a CNC Job object\n"
            "for this drill object."
        )
        self.layout.addWidget(self.cncjob_label)

        grid1 = QtGui.QGridLayout()
        self.layout.addLayout(grid1)

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

        toolchangezlabel = QtGui.QLabel('Toolchange Z:')
        toolchangezlabel.setToolTip(
            "Tool Z where user can change drill bit\n"
        )
        grid1.addWidget(toolchangezlabel, 3, 0)
        self.toolchangez_entry = LengthEntry()
        grid1.addWidget(self.toolchangez_entry, 3, 1)

        spdlabel = QtGui.QLabel('Spindle speed:')
        spdlabel.setToolTip(
            "Speed of the spindle\n"
            "in RPM (optional)"
        )
        grid1.addWidget(spdlabel, 4, 0)
        self.spindlespeed_entry = IntEntry(allow_empty=True)
        grid1.addWidget(self.spindlespeed_entry, 4, 1)

        #### Milling Holes ####
        self.mill_hole_label = QtGui.QLabel('<b>Mill Holes</b>')
        self.mill_hole_label.setToolTip(
            "Create Geometry for milling holes."
        )
        self.layout.addWidget(self.mill_hole_label)

        grid1 = QtGui.QGridLayout()
        self.layout.addLayout(grid1)
        tdlabel = QtGui.QLabel('Tool dia:')
        tdlabel.setToolTip(
            "Diameter of the cutting tool."
        )
        grid1.addWidget(tdlabel, 0, 0)
        self.tooldia_entry = LengthEntry()
        grid1.addWidget(self.tooldia_entry, 0, 1)


class GeometryOptionsGroupUI(OptionsGroupUI):
    def __init__(self, parent=None):
        OptionsGroupUI.__init__(self, "Geometry Options", parent=parent)

        ## Plot options
        self.plot_options_label = QtGui.QLabel("<b>Plot Options:</b>")
        self.layout.addWidget(self.plot_options_label)

        # Plot CB
        self.plot_cb = FCCheckBox(label='Plot')
        self.plot_cb.setToolTip(
            "Plot (show) this object."
        )
        self.layout.addWidget(self.plot_cb)

        ## Create CNC Job
        self.cncjob_label = QtGui.QLabel('<b>Create CNC Job:</b>')
        self.cncjob_label.setToolTip(
            "Create a CNC Job object\n"
            "tracing the contours of this\n"
            "Geometry object."
        )
        self.layout.addWidget(self.cncjob_label)

        grid1 = QtGui.QGridLayout()
        self.layout.addLayout(grid1)

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

        spdlabel = QtGui.QLabel('Spindle speed:')
        spdlabel.setToolTip(
            "Speed of the spindle\n"
            "in RPM (optional)"
        )
        grid1.addWidget(spdlabel, 4, 0)
        self.cncspindlespeed_entry = IntEntry(allow_empty=True)
        grid1.addWidget(self.cncspindlespeed_entry, 4, 1)

        ## Paint area
        self.paint_label = QtGui.QLabel('<b>Paint Area:</b>')
        self.paint_label.setToolTip(
            "Creates tool paths to cover the\n"
            "whole area of a polygon (remove\n"
            "all copper). You will be asked\n"
            "to click on the desired polygon."
        )
        self.layout.addWidget(self.paint_label)

        grid2 = QtGui.QGridLayout()
        self.layout.addLayout(grid2)

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
        grid2.addWidget(self.paintmargin_entry)


class CNCJobOptionsGroupUI(OptionsGroupUI):
    def __init__(self, parent=None):
        OptionsGroupUI.__init__(self, "CNC Job Options", parent=None)

        ## Plot options
        self.plot_options_label = QtGui.QLabel("<b>Plot Options:</b>")
        self.layout.addWidget(self.plot_options_label)

        grid0 = QtGui.QGridLayout()
        self.layout.addLayout(grid0)

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

        ## Export G-Code
        self.export_gcode_label = QtGui.QLabel("<b>Export G-Code:</b>")
        self.export_gcode_label.setToolTip(
            "Export and save G-Code to\n"
            "make this object to a file."
        )
        self.layout.addWidget(self.export_gcode_label)

        # Prepend to G-Code
        prependlabel = QtGui.QLabel('Prepend to G-Code:')
        prependlabel.setToolTip(
            "Type here any G-Code commands you would\n"
            "like to add at the beginning of the G-Code file."
        )
        self.layout.addWidget(prependlabel)

        self.prepend_text = FCTextArea()
        self.layout.addWidget(self.prepend_text)

        # Append text to G-Code
        appendlabel = QtGui.QLabel('Append to G-Code:')
        appendlabel.setToolTip(
            "Type here any G-Code commands you would\n"
            "like to append to the generated file.\n"
            "I.e.: M2 (End of program)"
        )
        self.layout.addWidget(appendlabel)

        self.append_text = FCTextArea()
        self.layout.addWidget(self.append_text)

        # Dwell
        grid1 = QtGui.QGridLayout()
        self.layout.addLayout(grid1)

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
        self.dwelltime_cb = FCEntry()
        grid1.addWidget(dwelllabel, 0, 0)
        grid1.addWidget(self.dwell_cb, 0, 1)
        grid1.addWidget(dwelltime, 1, 0)
        grid1.addWidget(self.dwelltime_cb, 1, 1)


class GlobalOptionsUI(QtGui.QWidget):
    """
    This is the app and project options editor.
    """
    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent=parent)

        layout = QtGui.QVBoxLayout()
        self.setLayout(layout)

        hlay1 = QtGui.QHBoxLayout()
        layout.addLayout(hlay1)
        unitslabel = QtGui.QLabel('Units:')
        hlay1.addWidget(unitslabel)
        self.units_radio = RadioSet([{'label': 'inch', 'value': 'IN'},
                                     {'label': 'mm', 'value': 'MM'}])
        hlay1.addWidget(self.units_radio)

        ####### Gerber #######
        # gerberlabel = QtGui.QLabel('<b>Gerber Options</b>')
        # layout.addWidget(gerberlabel)
        self.gerber_group = GerberOptionsGroupUI()
        # self.gerber_group.setFrameStyle(QtGui.QFrame.StyledPanel)
        layout.addWidget(self.gerber_group)

        ####### Excellon #######
        # excellonlabel = QtGui.QLabel('<b>Excellon Options</b>')
        # layout.addWidget(excellonlabel)
        self.excellon_group = ExcellonOptionsGroupUI()
        # self.excellon_group.setFrameStyle(QtGui.QFrame.StyledPanel)
        layout.addWidget(self.excellon_group)

        ####### Geometry #######
        # geometrylabel = QtGui.QLabel('<b>Geometry Options</b>')
        # layout.addWidget(geometrylabel)
        self.geometry_group = GeometryOptionsGroupUI()
        # self.geometry_group.setStyle(QtGui.QFrame.StyledPanel)
        layout.addWidget(self.geometry_group)

        ####### CNC #######
        # cnclabel = QtGui.QLabel('<b>CNC Job Options</b>')
        # layout.addWidget(cnclabel)
        self.cncjob_group = CNCJobOptionsGroupUI()
        # self.cncjob_group.setStyle(QtGui.QFrame.StyledPanel)
        layout.addWidget(self.cncjob_group)

# def main():
#
#     app = QtGui.QApplication(sys.argv)
#     fc = FlatCAMGUI()
#     sys.exit(app.exec_())
#
#
# if __name__ == '__main__':
#     main()
