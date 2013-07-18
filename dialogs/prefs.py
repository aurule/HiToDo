# Copyright 2013 Peter Andrews

# This file is part of HiToDo.
#
# HiToDo is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# HiToDo is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with HiToDo.  If not, see <http://www.gnu.org/licenses/>.

from gi.repository import Gtk, Gdk

class main(Gtk.Dialog):
    def __init__(self, parent):
        flags = Gtk.DialogFlags.DESTROY_WITH_PARENT
        Gtk.Dialog.__init__(self, "HiToDo Preferences", parent, flags)
        self.parent = parent
        
        close = self.add_button(Gtk.STOCK_OK, Gtk.ResponseType.CLOSE)
        close.connect("clicked", self.disappear)
        content = self.get_content_area()
        nb = Gtk.Notebook()
        nb.set_property("margin", 10)
        
        #
        #Interface tab
        #
        iface_lbl = Gtk.Label("_Interface")
        iface_lbl.set_property("use-underline", True)
        iface_content = Gtk.Box()
        iface_content.set_property("orientation", Gtk.Orientation.VERTICAL)
        iface_content.set_property("margin", 6)

        layout_frame = Gtk.Frame()
        layout_lbl = Gtk.Label("<b>Layout</b>")
        layout_lbl.set_property("use-markup", True)
        layout_frame.set_label_widget(layout_lbl)
        layout_frame.set_property("shadow-type", Gtk.ShadowType.NONE)
        
        layout_box = Gtk.Box()
        layout_box.set_property("orientation", Gtk.Orientation.VERTICAL)
        layout_box.set_property("margin-left", 12)
        
        self.use_tabs_toggle = Gtk.RadioButton.new_with_mnemonic_from_widget(None, "Use _Tabs to show multiple task lists")
        self.use_tabs_toggle.set_sensitive(False) #TODO remove this block once tabs are actually implemented
        self.use_tabs_toggle.connect("toggled", self.parent.toggle_use_tabs)
        layout_box.pack_start(self.use_tabs_toggle, False, False, 2)
        self.use_wins_toggle = Gtk.RadioButton.new_with_mnemonic_from_widget(self.use_tabs_toggle, "Use _Windows to show multiple task lists")
        layout_box.pack_start(self.use_wins_toggle, False, False, 2)
        
        layout_frame.add(layout_box)
        iface_content.pack_start(layout_frame, False, True, 0)
        
        behavior_frame = Gtk.Frame()
        behavior_lbl = Gtk.Label("<b>Behavior</b>")
        behavior_lbl.set_property("use-markup", True)
        behavior_frame.set_label_widget(behavior_lbl)
        behavior_frame.set_property("shadow-type", Gtk.ShadowType.NONE)
        
        behavior_box = Gtk.Box()
        behavior_box.set_property("orientation", Gtk.Orientation.VERTICAL)
        behavior_box.set_property("margin-left", 12)
        
        self.clobber_toggle = Gtk.CheckButton.new_with_mnemonic("Cl_ose the current task list before opening a new one")
        self.clobber_toggle.set_active(self.parent.clobber)
        self.clobber_toggle.connect("toggled", self.parent.toggle_clobber)
        behavior_box.pack_start(self.clobber_toggle, False, False, 5)
        
        self.reopen_toggle = Gtk.CheckButton.new_with_mnemonic("_Re-open most recent file on program start")
        self.reopen_toggle.set_active(self.parent.open_last_file)
        self.reopen_toggle.connect("toggled", self.parent.toggle_reopen)
        behavior_box.pack_start(self.reopen_toggle, False, False, 5)
        
        behavior_frame.add(behavior_box)
        iface_content.pack_start(behavior_frame, False, True, 0)
        nb.append_page(iface_content, iface_lbl)
        
        #
        #Labels tab
        #
        labels_lbl = Gtk.Label("_Labels")
        labels_lbl.set_property("use-underline", True)
        labels_content = Gtk.Box()
        labels_content.set_property("orientation", Gtk.Orientation.VERTICAL)
        labels_content.set_property("margin", 6)
        
        from_frame = Gtk.Frame()
        from_lbl = Gtk.Label("<b>Assigners (From)</b>")
        from_lbl.set_property("use-markup", True)
        from_frame.set_label_widget(from_lbl)
        from_frame.set_property("shadow-type", Gtk.ShadowType.NONE)
        
        from_box = Gtk.Box()
        from_box.set_property("orientation", Gtk.Orientation.VERTICAL)
        from_box.set_property("margin-left", 12)
        
        self.assigners_list_label = Gtk.Label()
        self.assigners_list_label.set_max_width_chars(24)
        from_box.pack_start(self.assigners_list_label, True, True, 2)
        
        from_edit_box = Gtk.ButtonBox()
        from_edit_box.set_orientation(Gtk.Orientation.HORIZONTAL)
        from_edit_box.set_layout(Gtk.ButtonBoxStyle.START)
        edit_assigners = Gtk.Button("Edit Assigne_rs", None, True)
        edit_assigners_icon = Gtk.Image.new_from_stock(Gtk.STOCK_EDIT, Gtk.IconSize.BUTTON)
        edit_assigners.set_image(edit_assigners_icon)
        from_edit_box.add(edit_assigners)
        from_box.pack_start(from_edit_box, True, True, 2)
        
        from_frame.add(from_box)
        labels_content.pack_start(from_frame, False, True, 0)
        
        to_frame = Gtk.Frame()
        to_lbl = Gtk.Label("<b>Assignees (To)</b>")
        to_lbl.set_property("use-markup", True)
        to_frame.set_label_widget(to_lbl)
        to_frame.set_property("shadow-type", Gtk.ShadowType.NONE)
        to_frame.set_property("margin-top", 6)
        
        to_box = Gtk.Box()
        to_box.set_property("orientation", Gtk.Orientation.VERTICAL)
        to_box.set_property("margin-left", 12)
        
        self.assignees_list_label = Gtk.Label()
        self.assignees_list_label.set_max_width_chars(24)
        to_box.pack_start(self.assignees_list_label, True, True, 2)
        
        to_edit_box = Gtk.ButtonBox()
        to_edit_box.set_orientation(Gtk.Orientation.HORIZONTAL)
        to_edit_box.set_layout(Gtk.ButtonBoxStyle.START)
        edit_assignees = Gtk.Button("Edit Assigne_es", None, True)
        edit_assignees_icon = Gtk.Image.new_from_stock(Gtk.STOCK_EDIT, Gtk.IconSize.BUTTON)
        edit_assignees.set_image(edit_assignees_icon)
        to_edit_box.add(edit_assignees)
        to_box.pack_start(to_edit_box, True, True, 2)
        
        to_frame.add(to_box)
        labels_content.pack_start(to_frame, False, True, 0)
        
        
        status_frame = Gtk.Frame()
        status_lbl = Gtk.Label("<b>Status</b>")
        status_lbl.set_property("use-markup", True)
        status_frame.set_label_widget(status_lbl)
        status_frame.set_property("shadow-type", Gtk.ShadowType.NONE)
        status_frame.set_property("margin-top", 6)
        
        status_box = Gtk.Box()
        status_box.set_property("orientation", Gtk.Orientation.VERTICAL)
        status_box.set_property("margin-left", 12)
        
        self.status_list_label = Gtk.Label()
        self.status_list_label.set_max_width_chars(24)
        status_box.pack_start(self.status_list_label, True, True, 2)
        
        status_edit_box = Gtk.ButtonBox()
        status_edit_box.set_orientation(Gtk.Orientation.HORIZONTAL)
        status_edit_box.set_layout(Gtk.ButtonBoxStyle.START)
        edit_status = Gtk.Button("Edit _Status Labels", None, True)
        edit_status_icon = Gtk.Image.new_from_stock(Gtk.STOCK_EDIT, Gtk.IconSize.BUTTON)
        edit_status.set_image(edit_status_icon)
        status_edit_box.add(edit_status)
        status_box.pack_start(status_edit_box, True, True, 2)
        
        status_frame.add(status_box)
        labels_content.pack_start(status_frame, False, True, 0)
        
        nb.append_page(labels_content, labels_lbl)
        
        #
        #Columns tab
        #
        cols_lbl = Gtk.Label("_Columns")
        cols_lbl.set_property("use-underline", True)
        cols_content = Gtk.Box()
        cols_content.set_property("orientation", Gtk.Orientation.VERTICAL)
        cols_content.set_property("margin", 6)
        
        first_box = Gtk.Box()
        first_box.set_orientation(Gtk.Orientation.VERTICAL)
        first_box.set_property("margin-left", 12)
        
        #explanation text
        expolbl = Gtk.Label("Choose which columns to show by default. To change their order, use the up and down buttons.")
        expolbl.set_property("wrap", True)
        expolbl.set_max_width_chars(24)
        first_box.pack_start(expolbl, False, False, 0)
        
        #set up main box
        main_box = Gtk.Box()
        main_box.set_orientation(Gtk.Orientation.HORIZONTAL)
        first_box.pack_start(main_box, True, True, 0)
        
        #start with a list widget for the columns
        #first a scrolling window to put it in
        col_view_scroller = Gtk.ScrolledWindow()
        col_view_scroller.set_min_content_height(315)
        col_view_scroller.set_min_content_width(300)
        
        col_view = Gtk.TreeView()#self.parent.cols)
        col_sel = col_view.get_selection() #store selection for later
        
        #set up the columns for our treeview
        #visible checkbox
        visible = Gtk.CellRendererToggle(activatable=True, radio=False)
        #visible.connect("toggled", self.parent.toggle_col_visible)
        col_visible = Gtk.TreeViewColumn(u"\u2713", visible, active=2, visible=3)
        col_view.append_column(col_visible)
        
        #title display
        name = Gtk.CellRendererText(editable=False)
        col_name = Gtk.TreeViewColumn("Column", name, text=1)
        col_view.append_column(col_name)
        
        #add it
        col_view_scroller.add(col_view)
        main_box.pack_start(col_view_scroller, True, True, 0)
        
        #up/down buttons
        btnbox = Gtk.ButtonBox()
        btnbox.set_orientation(Gtk.Orientation.VERTICAL)
        btnbox.set_homogeneous(True)
        btnbox.set_layout(Gtk.ButtonBoxStyle.START)
        
        upbtn = Gtk.Button(Gtk.STOCK_GO_UP)
        upbtn.set_use_stock(True)
        #upbtn.connect("clicked", self.parent.move_col, col_sel, "up")
        btnbox.pack_start(upbtn, False, False, 0)
        
        dnbtn = Gtk.Button(Gtk.STOCK_GO_DOWN)
        dnbtn.set_use_stock(True)
        #dnbtn.connect("clicked", self.parent.move_col, col_sel, "dn")
        btnbox.pack_start(dnbtn, False, False, 0)
        
        sep = Gtk.Separator()
        sep.set_property("orientation", Gtk.Orientation.HORIZONTAL)
        btnbox.pack_start(sep, False, False, 0)
        btnbox.set_child_non_homogeneous(sep, True)
        
        defaultbtn = Gtk.Button("De_fault")
        defaultbtn.set_use_underline(True)
        #defaultbtn.connect("clicked", self.parent.reset_cols)
        btnbox.pack_start(defaultbtn, False, False, 0)
        
        main_box.pack_start(btnbox, False, False, 0)
        cols_content.add(first_box)
        
        nb.append_page(cols_content, cols_lbl)
        
        content.add(nb)
    
    def disappear(self, widget=None):
        self.hide()
