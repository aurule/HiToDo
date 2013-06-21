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
        Gtk.Dialog.__init__(self, "Document Properties", parent, flags)
        close = self.add_button(Gtk.STOCK_OK, Gtk.ResponseType.CLOSE)
        close.connect("clicked", self.disappear)
        content = self.get_content_area()
        nb = Gtk.Notebook()
        
        #Tags tab
        taglbl = Gtk.Label("Tags")
        tagbox = Gtk.Box()
        tagbox.set_orientation(Gtk.Orientation.VERTICAL)
        nb.append_page(tagbox, taglbl)
        
        #Columns tab
        collbl = Gtk.Label("Columns")
        colbox = Gtk.Box()
        colbox.set_orientation(Gtk.Orientation.VERTICAL)
        #list widget
        col_view_scroller = Gtk.ScrolledWindow()
        col_view = Gtk.TreeView(parent.cols)
        visible = Gtk.CellRendererToggle(activatable=True, radio=False)
        visible.connect("toggled", parent.toggle_col_visible)
        col_visible = Gtk.TreeViewColumn(u"\u2713", visible, active=2, visible=3)
        col_view.append_column(col_visible)
        name = Gtk.CellRendererText(editable=False)
        col_name = Gtk.TreeViewColumn("Column", name, text=1)
        col_view.append_column(col_name)
        col_sel = col_view.get_selection()
        col_view_scroller.add(col_view)
        col_view_scroller.set_min_content_height(315)
        col_view_scroller.set_min_content_width(230)
        colbox.pack_start(col_view_scroller, True, True, 0)
        #up/down
        btnbox = Gtk.ButtonBox()
        btnbox.set_orientation(Gtk.Orientation.HORIZONTAL)
        btnbox.set_homogeneous(True)
        btnbox.set_layout(Gtk.ButtonBoxStyle.CENTER)
        upbtn = Gtk.Button(Gtk.STOCK_GO_UP)
        upbtn.set_use_stock(True)
        upbtn.connect("clicked", parent.move_col, col_sel, "up")
        dnbtn = Gtk.Button(Gtk.STOCK_GO_DOWN)
        dnbtn.set_use_stock(True)
        dnbtn.connect("clicked", parent.move_col, col_sel, "dn")
        btnbox.pack_start(upbtn, True, False, 0)
        btnbox.pack_start(dnbtn, True, False, 0)
        colbox.pack_start(btnbox, True, True, 0)
        #explanation
        expolbl = Gtk.Label("Choose which columns to show. To change their order, use the up and down buttons.")
        expolbl.set_property("wrap", True)
        expolbl.set_max_width_chars(20)
        colbox.pack_start(expolbl, False, False, 0)
        
        nb.append_page(colbox, collbl)
        
        #Stats tab
        statlbl = Gtk.Label("Stats")
        statbox = Gtk.Box()
        statbox.set_orientation(Gtk.Orientation.VERTICAL)
        nb.append_page(statbox, statlbl)
        
        #add the tabbed notebook
        content.pack_start(nb, True, True, 0)
        content.set_size_request(300, 400)
    
    def disappear(self, widget=None):
        self.hide()
