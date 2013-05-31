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
        self.set_version("0.8")
        self.set_copyright(u"Copyright \xa9 2013 Peter Andrews")
        self.set_comments("Heirarchical task manager inspired by AbstractSpoon's ToDoList.")
        self.set_license_type(Gtk.License.GPL_3_0)
        self.set_website("https://github.com/aurule/HiToDo")

class htd_prefs(Gtk.Dialog):
    def __init__(self, parent):
        flags = Gtk.DialogFlags.DESTROY_WITH_PARENT
        Gtk.Dialog.__init__(self, "HiToDo Preferences", parent, flags)
        close = self.add_button(Gtk.STOCK_CLOSE, Gtk.ResponseType.CLOSE)
        close.connect("clicked", self.disappear)
        actions = self.get_action_area()
        #TODO add settings widgets to "actions"
    
    def disappear(self, widget=None):
        self.hide()
