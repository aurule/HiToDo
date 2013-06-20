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
import file_parsers

class htd_open(Gtk.FileChooserDialog):
    def __init__(self, parent):
        Gtk.FileChooserDialog.__init__(self, "Open File", parent, Gtk.FileChooserAction.OPEN)
        self.add_button(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL)
        self.add_button(Gtk.STOCK_OPEN, Gtk.ResponseType.ACCEPT)
        self.set_local_only(True)
        
        #set supported types
        htd = file_parsers.htd_filter()
        self.add_filter(htd)
        
        #set default filter
        self.set_filter(htd)

class htd_save(Gtk.FileChooserDialog):
    def __init__(self, parent):
        Gtk.FileChooserDialog.__init__(self, "Save As", parent, Gtk.FileChooserAction.SAVE)
        self.add_button(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL)
        self.add_button(Gtk.STOCK_SAVE, Gtk.ResponseType.ACCEPT)
        self.set_local_only(True)
        
        #set supported types
        htd = file_parsers.htd_filter()
        self.add_filter(htd)
        
        #set default filter
        self.set_filter(htd)

class htd_warn_discard(Gtk.MessageDialog):
    def __init__(self, parent, fname, time_since_save):
        flags = Gtk.DialogFlags.MODAL & Gtk.DialogFlags.DESTROY_WITH_PARENT
        Gtk.MessageDialog.__init__(self, parent, flags, Gtk.MessageType.WARNING, Gtk.ButtonsType.NONE, "Save changes to \"%s\" before closing?" % fname)
        self.format_secondary_text("If you don't save, changes from the last %s will be permanently lost." % time_since_save)
        self.add_button("Close _without Saving", Gtk.ResponseType.CLOSE)
        self.add_button(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL)
        self.add_button(Gtk.STOCK_SAVE, Gtk.ResponseType.ACCEPT)

class htd_about(Gtk.AboutDialog):
    def __init__(self, parent):
        Gtk.AboutDialog.__init__(self)
        self.set_transient_for(parent)
        self.set_program_name("HiToDO")
        self.set_version("0.9")
        self.set_copyright(u"Copyright \xa9 2013 Peter Andrews")
        self.set_comments("Heirarchical task manager inspired by AbstractSpoon's ToDoList.")
        self.set_license_type(Gtk.License.GPL_3_0)
        self.set_website("https://github.com/aurule/HiToDo")

class htd_prefs(Gtk.Dialog):
    def __init__(self, parent):
        flags = Gtk.DialogFlags.DESTROY_WITH_PARENT
        Gtk.Dialog.__init__(self, "HiToDo Preferences", parent, flags)
        close = self.add_button(Gtk.STOCK_OK, Gtk.ResponseType.CLOSE)
        close.connect("clicked", self.disappear)
        content = self.get_content_area()
        #TODO add settings widgets to "content"
    
    def disappear(self, widget=None):
        self.hide()

class htd_docprops(Gtk.Dialog):
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
        #explanation
        expolbl = Gtk.Label("Choose which columns to show. To change their order, just drag the column headers in the main window.")
        expolbl.set_property("wrap", True)
        expolbl.set_max_width_chars(20)
        colbox.pack_start(expolbl, False, False, 0)
        #list widget
        col_view_scroller = Gtk.ScrolledWindow()
        col_view = Gtk.TreeView(parent.cols)
        visible = Gtk.CellRendererToggle(activatable=True, radio=False)
        visible.connect("toggled", parent.skip)
        col_visible = Gtk.TreeViewColumn(u"\u2713", visible, active=2)
        col_view.append_column(col_visible)
        name = Gtk.CellRendererText(editable=False)
        col_name = Gtk.TreeViewColumn("Column", name, text=1)
        col_view.append_column(col_name)
        col_view_scroller.add(col_view)
        col_view_scroller.set_min_content_height(315)
        col_view_scroller.set_min_content_width(230)
        colbox.pack_start(col_view_scroller, True, True, 0)
        
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
