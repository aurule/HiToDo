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
        close = self.add_button(Gtk.STOCK_CLOSE, Gtk.ResponseType.CLOSE)
        close.connect("clicked", self.disappear)
        
        #internal vars
        self.treestore = None
        self.parent = parent
        self.name_edit_path = ""
        self.name_edit_old_val = ""
        self.name_editor = None
        self.name_key_press_catcher = None
        
        #get content area and do widget setup
        content = self.get_content_area()
        
        #start with a list widget for the columns
        #first a scrolling window to put it in
        scroller = Gtk.ScrolledWindow()
        scroller.set_min_content_height(315)
        scroller.set_min_content_width(250)
        
        self.view = Gtk.TreeView()
        self.view.set_headers_visible(False)
        self.selection = self.view.get_selection() #store selection for later
        
        #title display
        self.name_renderer = Gtk.CellRendererText(editable=True)
        self.name_renderer.connect("edited", self.commit_name)
        self.name_renderer.connect("editing-started", self.name_edit_start)
        self.name_renderer.connect("editing-canceled", self.commit_name, None, None, True)
        self.col_name = Gtk.TreeViewColumn("", self.name_renderer, text=0)
        self.view.append_column(self.col_name)
        
        #add it
        scroller.add(self.view)
        content.pack_start(scroller, True, True, 0)
        
        #now for the "add" field and delete button
        actions = self.get_action_area() #get button area
        
        addbtn = Gtk.Button(Gtk.STOCK_ADD)
        addbtn.set_use_stock(True)
        addbtn.connect("clicked", self.add_label)
        actions.pack_start(addbtn, False, False, 0)
        actions.set_child_secondary(addbtn, True)
        
        delbtn = Gtk.Button(Gtk.STOCK_REMOVE)
        delbtn.set_use_stock(True)
        delbtn.connect("clicked", self.del_selected_label)
        actions.pack_start(delbtn, False, False, 0)
        actions.set_child_secondary(delbtn, True)
    
    def disappear(self, widget=None):
        self.view.set_model(None)
        self.hide()
    
    def set_store(self, treestore):
        self.treestore = treestore
        self.view.set_model(self.treestore)
    
    def set_list(self, label_list):
        label_list.sort()
        self.label_list = label_list
    
    def add_label(self, widget, data=None):
        newiter = self.treestore.append("")
        path = self.treestore.get_path(newiter)
        self.selection.select_iter(newiter)
        self.view.set_cursor_on_cell(path, self.col_name, self.name_renderer, True)
    
    def del_selected_label(self, widget, data=None):
        store, seliter = self.selection.get_selected()
        self.del_label(seliter = seliter)
        
    def del_label(self, path=None, seliter=None):
        if path is None and seliter is None: return
        if seliter is None:
            seliter = self.treestore.get_iter(path)
        
        val = self.treestore[seliter][0]
        if val is not None:
            idex = self.label_list.index(val)
            if idex is not None:
                del self.label_list[idex]
                self.parent.make_dirty()
        self.treestore.remove(seliter)
    
    def commit_name(self, widget=None, path=None, new_name=None, write=True):
        if path is None:
            if self.name_editor is None: return
            path = self.name_edit_path
            new_name = self.name_editor.get_text()
            self.name_editor.disconnect(self.name_key_press_catcher)
        self.name_editor = None #clear this to prevent eating memory
        
        old_name = self.treestore[path][0]
        
        if new_name is None:
            if old_name == '':
                self.del_label(path)
            return
        
        #If the new name is blank and the task is new, just delete it.
        #If the new name is blank but the task has an existing name, cancel the edit.
        if new_name == '':
            if old_name == '' or old_name is None:
                self.del_label(path)
                return
            else:
                return
        
        #finally, set the new name if allowed
        if write is True:
            self.treestore[path][0] = new_name
            self.label_list.append(new_name)
    
    def name_edit_start(self, renderer, editor, path):
        self.name_edit_path = str(path)
        self.name_edit_old_val = self.treestore[path][0]
        self.name_editor = editor
        self.name_key_press_catcher = editor.connect("key-press-event", self.name_keys_dn)
    
    def name_keys_dn(self, widget=None, event=None):
        kvn = Gdk.keyval_name(event.keyval)
        if kvn == "Escape":
            self.commit_name(path=self.name_edit_path, new_name='', write=False)
