from gi.repository import Gtk

from FlatCAM_GTK import FCNoteBook


class FlatCAMGUI(Gtk.Window):

    MENU = """
    <ui>
      <menubar name='MenuBar'>
        <menu action='FileMenu'>
          <menuitem action='FileNew'>
          <separator />

          <menuitem action='FileQuit' />
        </menu>
      </menubar>
      <toolbar name='ToolBar'>
        <toolitem action='FileNewStandard' />
        <toolitem action='FileQuit' />
      </toolbar>
    </ui>
    """

    def __init__(self):
        """

        :return: The FlatCAM window.
        :rtype: FlatCAM
        """
        Gtk.Window.__init__(self, title="FlatCAM - 0.5")
        self.set_default_size(200, 200)

        vbox1 = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        ### Menu
        # action_group = Gtk.ActionGroup("my_actions")
        # self.add_file_menu_actions(action_group)
        # #self.add_edit_menu_actions(action_group)
        # #self.add_choices_menu_actions(action_group)
        #
        # uimanager = self.create_ui_manager()
        # uimanager.insert_action_group(action_group)
        #
        # menubar = uimanager.get_widget("/MenuBar")
        # vbox1.pack_start(menubar, False, False, 0)
        #
        # toolbar = uimanager.get_widget("/ToolBar")
        # vbox1.pack_start(toolbar, False, False, 0)

        menu = Gtk.MenuBar()

        ## File
        menufile = Gtk.MenuItem.new_with_label('File')
        menufile_menu = Gtk.Menu()
        menufile.set_submenu(menufile_menu)
        # New
        self.menufilenew = Gtk.ImageMenuItem.new_from_stock(Gtk.STOCK_NEW, None)
        menufile_menu.append(self.menufilenew)
        menufile_menu.append(Gtk.SeparatorMenuItem())
        # Open recent
        self.menufilerecent = Gtk.ImageMenuItem("Open Recent", image=Gtk.Image(stock=Gtk.STOCK_OPEN))
        menufile_menu.append(self.menufilerecent)
        menufile_menu.append(Gtk.SeparatorMenuItem())
        # Open Gerber ...
        self.menufileopengerber = Gtk.ImageMenuItem("Open Gerber ...", image=Gtk.Image(stock=Gtk.STOCK_OPEN))
        menufile_menu.append(self.menufileopengerber)
        # Open Excellon ...
        self.menufileopenexcellon = Gtk.ImageMenuItem("Open Excellon ...", image=Gtk.Image(stock=Gtk.STOCK_OPEN))
        menufile_menu.append(self.menufileopenexcellon)
        # Open G-Code ...
        self.menufileopengcode = Gtk.ImageMenuItem("Open G-Code ...", image=Gtk.Image(stock=Gtk.STOCK_OPEN))
        menufile_menu.append(self.menufileopengcode)
        menufile_menu.append(Gtk.SeparatorMenuItem())
        # Open Project ...
        self.menufileopenproject = Gtk.ImageMenuItem("Open Project ...", image=Gtk.Image(stock=Gtk.STOCK_OPEN))
        menufile_menu.append(self.menufileopenproject)
        menufile_menu.append(Gtk.SeparatorMenuItem())
        # Save Project
        self.menufilesaveproject = Gtk.ImageMenuItem("Save Project", image=Gtk.Image(stock=Gtk.STOCK_SAVE))
        menufile_menu.append(self.menufilesaveproject)
        # Save Project As ...
        self.menufilesaveprojectas = Gtk.ImageMenuItem("Save Project As ...", image=Gtk.Image(stock=Gtk.STOCK_SAVE_AS))
        menufile_menu.append(self.menufilesaveprojectas)
        # Save Project Copy ...
        self.menufilesaveprojectcopy = Gtk.ImageMenuItem("Save Project Copy ...", image=Gtk.Image(stock=Gtk.STOCK_SAVE_AS))
        menufile_menu.append(self.menufilesaveprojectcopy)
        menufile_menu.append(Gtk.SeparatorMenuItem())
        # Save Defaults
        self.menufilesavedefaults = Gtk.ImageMenuItem("Save Defaults", image=Gtk.Image(stock=Gtk.STOCK_SAVE))
        menufile_menu.append(self.menufilesavedefaults)
        menufile_menu.append(Gtk.SeparatorMenuItem())
        # Quit
        self.menufilequit = Gtk.ImageMenuItem.new_from_stock(Gtk.STOCK_QUIT, None)
        menufile_menu.append(self.menufilequit)
        menu.append(menufile)

        ## Edit
        menuedit = Gtk.MenuItem.new_with_label('Edit')
        menu.append(menuedit)
        menuedit_menu = Gtk.Menu()
        menuedit.set_submenu(menuedit_menu)
        # Delete
        self.menueditdelete = Gtk.ImageMenuItem.new_from_stock(Gtk.STOCK_DELETE, None)
        menuedit_menu.append(self.menueditdelete)

        ## View
        menuview = Gtk.MenuItem.new_with_label('View')
        menu.append(menuview)
        menuview_menu = Gtk.Menu()
        menuview.set_submenu(menuview_menu)
        # Disable all plots
        self.menuviewdisableall = Gtk.ImageMenuItem("Disable all plots", image=Gtk.Image.new_from_file('share/clear_plot16.png'))
        menuview_menu.append(self.menuviewdisableall)
        self.menuviewdisableallbutthis = Gtk.ImageMenuItem("Disable all plots but this one", image=Gtk.Image.new_from_file('share/clear_plot16.png'))
        menuview_menu.append(self.menuviewdisableallbutthis)
        self.menuviewenableall = Gtk.ImageMenuItem("Enable all plots", image=Gtk.Image.new_from_file('share/replot16.png'))
        menuview_menu.append(self.menuviewenableall)

        ## Options
        menuoptions = Gtk.MenuItem.new_with_label('Options')
        menu.append(menuoptions)
        menuoptions_menu = Gtk.Menu()
        menuoptions.set_submenu(menuoptions_menu)
        # Transfer Options
        menutransferoptions = Gtk.ImageMenuItem("Transfer Options", image=Gtk.Image.new_from_file('share/copy16.png'))
        menuoptions_menu.append(menutransferoptions)
        menutransferoptions_menu = Gtk.Menu()
        menutransferoptions.set_submenu(menutransferoptions_menu)
        self.menutransferoptions_p2a = Gtk.ImageMenuItem("Project to App", image=Gtk.Image.new_from_file('share/copy16.png'))
        menutransferoptions_menu.append(self.menutransferoptions_p2a)
        self.menutransferoptions_a2p = Gtk.ImageMenuItem("App to Project", image=Gtk.Image.new_from_file('share/copy16.png'))
        menutransferoptions_menu.append(self.menutransferoptions_a2p)
        self.menutransferoptions_o2p = Gtk.ImageMenuItem("Object to Project", image=Gtk.Image.new_from_file('share/copy16.png'))
        menutransferoptions_menu.append(self.menutransferoptions_o2p)
        self.menutransferoptions_o2a = Gtk.ImageMenuItem("Object to App", image=Gtk.Image.new_from_file('share/copy16.png'))
        menutransferoptions_menu.append(self.menutransferoptions_o2a)
        self.menutransferoptions_p2o = Gtk.ImageMenuItem("Project to Object", image=Gtk.Image.new_from_file('share/copy16.png'))
        menutransferoptions_menu.append(self.menutransferoptions_p2o)
        self.menutransferoptions_a2o = Gtk.ImageMenuItem("App to Object", image=Gtk.Image.new_from_file('share/copy16.png'))
        menutransferoptions_menu.append(self.menutransferoptions_a2o)

        ## Tools
        menutools = Gtk.MenuItem.new_with_label('Tools')
        menu.append(menutools)
        menutools_menu = Gtk.Menu()
        menutools.set_submenu(menutools_menu)
        # Double Sided PCB tool
        self.menutools_dblsided = Gtk.ImageMenuItem("Double-Sided PCB Tool", image=Gtk.Image(stock=Gtk.STOCK_PREFERENCES))
        menutools_menu.append(self.menutools_dblsided)

        ## Help
        menuhelp = Gtk.MenuItem.new_with_label('Help')
        menu.append(menuhelp)
        menuhelp_menu = Gtk.Menu()
        menuhelp.set_submenu(menuhelp_menu)
        # About
        self.menuhelpabout = Gtk.ImageMenuItem("About", image=Gtk.Image(stock=Gtk.STOCK_ABOUT))
        menuhelp_menu.append(self.menuhelpabout)
        # Updates
        self.menuhelpupdates = Gtk.ImageMenuItem("Check for updates", image=Gtk.Image(stock=Gtk.STOCK_DIALOG_INFO))
        menuhelp_menu.append(self.menuhelpupdates)

        vbox1.pack_start(menu, False, False, 0)
        ### End of menu

        ###############
        ### Toolbar ###
        ###############
        self.toolbar = Gtk.Toolbar(toolbar_style=Gtk.ToolbarStyle.ICONS)
        vbox1.pack_start(self.toolbar, False, False, 0)

        # Zoom fit
        zf_ico = Gtk.Image.new_from_file('share/zoom_fit32.png')
        self.zoom_fit_btn = Gtk.ToolButton.new(zf_ico, "")
        #zoom_fit.connect("clicked", self.on_zoom_fit)
        self.zoom_fit_btn.set_tooltip_markup("Zoom Fit.\n(Click on plot and hit <b>1</b>)")
        self.toolbar.insert(self.zoom_fit_btn, -1)

        # Zoom out
        zo_ico = Gtk.Image.new_from_file('share/zoom_out32.png')
        self.zoom_out_btn = Gtk.ToolButton.new(zo_ico, "")
        #zoom_out.connect("clicked", self.on_zoom_out)
        self.zoom_out_btn.set_tooltip_markup("Zoom Out.\n(Click on plot and hit <b>2</b>)")
        self.toolbar.insert(self.zoom_out_btn, -1)

        # Zoom in
        zi_ico = Gtk.Image.new_from_file('share/zoom_in32.png')
        self.zoom_in_btn = Gtk.ToolButton.new(zi_ico, "")
        #zoom_in.connect("clicked", self.on_zoom_in)
        self.zoom_in_btn.set_tooltip_markup("Zoom In.\n(Click on plot and hit <b>3</b>)")
        self.toolbar.insert(self.zoom_in_btn, -1)

        # Clear plot
        cp_ico = Gtk.Image.new_from_file('share/clear_plot32.png')
        self.clear_plot_btn = Gtk.ToolButton.new(cp_ico, "")
        #clear_plot.connect("clicked", self.on_clear_plots)
        self.clear_plot_btn.set_tooltip_markup("Clear Plot")
        self.toolbar.insert(self.clear_plot_btn, -1)

        # Replot
        rp_ico = Gtk.Image.new_from_file('share/replot32.png')
        self.replot_btn = Gtk.ToolButton.new(rp_ico, "")
        #replot.connect("clicked", self.on_toolbar_replot)
        self.replot_btn.set_tooltip_markup("Re-plot all")
        self.toolbar.insert(self.replot_btn, -1)

        # Delete item
        del_ico = Gtk.Image.new_from_file('share/delete32.png')
        self.delete_btn = Gtk.ToolButton.new(del_ico, "")
        #delete.connect("clicked", self.on_delete)
        self.delete_btn.set_tooltip_markup("Delete selected\nobject.")
        self.toolbar.insert(self.delete_btn, -1)

        #############
        ### Paned ###
        #############
        hpane = Gtk.Paned.new(Gtk.Orientation.HORIZONTAL)
        vbox1.pack_start(hpane, expand=True, fill=True, padding=0)

        ################
        ### Notebook ###
        ################
        self.notebook = FCNoteBook()
        hpane.pack1(self.notebook)

        #################
        ### Plot area ###
        #################
        # self.plotarea = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.plotarea = Gtk.Grid()
        self.plotarea_super = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.plotarea_super.pack_start(self.plotarea, expand=True, fill=True, padding=0)
        hpane.pack2(self.plotarea_super)

        ################
        ### Info bar ###
        ################
        infobox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        vbox1.pack_start(infobox, expand=False, fill=True, padding=0)
        ## Frame
        frame = Gtk.Frame(margin=2, hexpand=True, halign=0)
        infobox.pack_start(frame, expand=True, fill=True, padding=0)
        self.info_label = Gtk.Label("Not started.", margin=2, hexpand=True)
        frame.add(self.info_label)
        ## Coordinate Label
        self.position_label = Gtk.Label("X: 0.0   Y: 0.0", margin_left=4, margin_right=4)
        infobox.pack_start(self.position_label, expand=False, fill=False, padding=0)
        ## Units label
        self.units_label = Gtk.Label("[in]", margin_left=4, margin_right=4)
        infobox.pack_start(self.units_label, expand=False, fill=False, padding=0)
        ## Progress bar
        self.progress_bar = Gtk.ProgressBar(margin=2)
        infobox.pack_start(self.progress_bar, expand=False, fill=False, padding=0)

        self.add(vbox1)
        self.show_all()

    # def create_ui_manager(self):
    #     uimanager = Gtk.UIManager()
    #
    #     # Throws exception if something went wrong
    #     uimanager.add_ui_from_string(FlatCAM.MENU)
    #
    #     # Add the accelerator group to the toplevel window
    #     accelgroup = uimanager.get_accel_group()
    #     self.add_accel_group(accelgroup)
    #     return uimanager
    #
    # def add_file_menu_actions(self, action_group):
    #     action_filemenu = Gtk.Action("FileMenu", "File", None, None)
    #     action_group.add_action(action_filemenu)
    #
    #     action_filenewmenu = Gtk.Action("FileNew", None, None, Gtk.STOCK_NEW)
    #     action_group.add_action(action_filenewmenu)
    #
    #     action_new = Gtk.Action("FileNewStandard", "_New",
    #         "Create a new file", Gtk.STOCK_NEW)
    #     action_new.connect("activate", self.on_menu_file_new_generic)
    #     action_group.add_action_with_accel(action_new, None)
    #
    #     action_group.add_actions([
    #         ("FileNewFoo", None, "New Foo", None, "Create new foo",
    #          self.on_menu_file_new_generic),
    #         ("FileNewGoo", None, "_New Goo", None, "Create new goo",
    #          self.on_menu_file_new_generic),
    #     ])
    #
    #     action_filequit = Gtk.Action("FileQuit", None, None, Gtk.STOCK_QUIT)
    #     action_filequit.connect("activate", self.on_menu_file_quit)
    #     action_group.add_action(action_filequit)
    #
    # def on_menu_file_new_generic(self, widget):
    #     print("A File|New menu item was selected.")
    #
    # def on_menu_file_quit(self, widget):
    #     Gtk.main_quit()



if __name__ == "__main__":
    flatcam = FlatCAMGUI()
    Gtk.main()