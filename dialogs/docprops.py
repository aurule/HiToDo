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
        #handle dialog init
        flags = Gtk.DialogFlags.DESTROY_WITH_PARENT
        Gtk.Dialog.__init__(self, "Document Properties", parent, flags)
        close = self.add_button(Gtk.STOCK_OK, Gtk.ResponseType.CLOSE)
        close.connect("clicked", self.disappear)
        content = self.get_content_area()
        self.parent = parent
        
        nb = Gtk.Notebook()
        
        #Tags tab
        taglbl = Gtk.Label("Tags")
        tagtab = self.create_tags_tab()
        nb.append_page(tagtab, taglbl)
        
        #Columns tab
        collbl = Gtk.Label("Columns")
        coltab = self.create_cols_tab()
        nb.append_page(coltab, collbl)
        
        #Stats tab
        statlbl = Gtk.Label("Stats")
        stattab = self.create_stats_tab()
        nb.append_page(stattab, statlbl)
        
        #add the tabbed notebook
        content.pack_start(nb, True, True, 0)
        content.set_size_request(300, 400)
    
    def disappear(self, widget=None):
        self.hide()
    
    def create_tags_tab(self):
        main_box = Gtk.Box()
        main_box.set_orientation(Gtk.Orientation.VERTICAL)
        return main_box
    
    def create_cols_tab(self):
        #set up main box
        main_box = Gtk.Box()
        main_box.set_orientation(Gtk.Orientation.VERTICAL)
        
        #start with a list widget for the columns
        #first a scrolling window to put it in
        col_view_scroller = Gtk.ScrolledWindow()
        col_view_scroller.set_min_content_height(315)
        col_view_scroller.set_min_content_width(230)
        
        col_view = Gtk.TreeView(self.parent.cols)
        col_sel = col_view.get_selection() #store selection for later
        
        #set up the columns for our treeview
        #visible checkbox
        visible = Gtk.CellRendererToggle(activatable=True, radio=False)
        visible.connect("toggled", self.parent.toggle_col_visible)
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
        btnbox.set_orientation(Gtk.Orientation.HORIZONTAL)
        btnbox.set_homogeneous(True)
        btnbox.set_layout(Gtk.ButtonBoxStyle.CENTER)
        
        upbtn = Gtk.Button(Gtk.STOCK_GO_UP)
        upbtn.set_use_stock(True)
        upbtn.connect("clicked", self.parent.move_col, col_sel, "up")
        btnbox.pack_start(upbtn, True, False, 0)
        
        dnbtn = Gtk.Button(Gtk.STOCK_GO_DOWN)
        dnbtn.set_use_stock(True)
        dnbtn.connect("clicked", self.parent.move_col, col_sel, "dn")
        btnbox.pack_start(dnbtn, True, False, 0)
        
        main_box.pack_start(btnbox, True, True, 0)
        
        #explanation text
        expolbl = Gtk.Label("Choose which columns to show. To change their order, use the up and down buttons.")
        expolbl.set_property("wrap", True)
        expolbl.set_max_width_chars(20)
        main_box.pack_start(expolbl, False, False, 0)
        
        return main_box
    
    def create_stats_tab(self):
        main_box = Gtk.Box()
        main_box.set_orientation(Gtk.Orientation.VERTICAL)
        return main_box
