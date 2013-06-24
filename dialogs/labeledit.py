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
        Gtk.Dialog.__init__(self, "Manage Labels", parent, flags)
        close = self.add_button(Gtk.STOCK_OK, Gtk.ResponseType.CLOSE)
        close.connect("clicked", self.disappear)
        
        #internal vars
        self.treestore = None
        
        #get content area and do widget setup
        content = self.get_content_area()
        
        #start with a list widget for the columns
        #first a scrolling window to put it in
        scroller = Gtk.ScrolledWindow()
        scroller.set_min_content_height(315)
        scroller.set_min_content_width(250)
        
        self.view = Gtk.TreeView()
        self.view.set_headers_visible(False)
        sel = self.view.get_selection() #store selection for later
        
        #title display
        name = Gtk.CellRendererText(editable=True)
        self.col_name = Gtk.TreeViewColumn("", name, text=0)
        self.view.append_column(self.col_name)
        
        #add it
        scroller.add(self.view)
        content.pack_start(scroller, True, True, 0)
        
        #TODO now for the "add" field and delete button
    
    def disappear(self, widget=None):
        self.view.set_model(None)
        self.hide()
    
    def set_store(self, treestore):
        self.treestore = treestore
        self.view.set_model(self.treestore)
