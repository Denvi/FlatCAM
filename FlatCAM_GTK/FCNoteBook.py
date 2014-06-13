from gi.repository import Gtk


class FCNoteBook(Gtk.Notebook):

    def __init__(self):
        Gtk.Notebook.__init__(self, vexpand=True, vexpand_set=True, valign=1, expand=True)

        ###############
        ### Project ###
        ###############
        self.project_contents = Gtk.VBox(vexpand=True, valign=0, vexpand_set=True, expand=True)
        sw1 = Gtk.ScrolledWindow(vexpand=True, valign=0, vexpand_set=True, expand=True)
        sw1.add_with_viewport(self.project_contents)
        self.project_page_num = self.append_page(sw1, Gtk.Label("Project"))

        ################
        ### Selected ###
        ################
        self.selected_contents = Gtk.VBox()
        sw2 = Gtk.ScrolledWindow()
        sw2.add_with_viewport(self.selected_contents)
        self.selected_page_num = self.append_page(sw2, Gtk.Label("Selected"))

        ###############
        ### Options ###
        ###############
        self.options_contents_super = Gtk.VBox()
        sw3 = Gtk.ScrolledWindow()
        sw3.add_with_viewport(self.options_contents_super)
        self.options_page_num = self.append_page(sw3, Gtk.Label("Options"))

        hb = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        ico = Gtk.Image.new_from_file("share/gear32.png")
        hb.pack_start(ico, expand=False, fill=False, padding=0)
        self.combo_options = Gtk.ComboBoxText()
        hb.pack_start(self.combo_options, expand=True, fill=True, padding=0)
        self.options_contents_super.pack_start(hb, expand=False, fill=False, padding=0)
        self.options_contents = Gtk.VBox()
        self.options_contents_super.pack_start(self.options_contents, expand=False, fill=False, padding=0)

        ############
        ### Tool ###
        ############
        self.tool_contents = Gtk.VBox()
        self.tool_page_num = self.append_page(self.tool_contents, Gtk.Label("Tool"))
