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
        loadable = file_parsers.fileParser.get_loadable()
        for f in loadable:
            self.add_filter(f)

        #set default filter
        self.set_filter(loadable[0])

class htd_save(Gtk.FileChooserDialog):
    def __init__(self, parent):
        Gtk.FileChooserDialog.__init__(self, "Save As", parent, Gtk.FileChooserAction.SAVE)
        self.add_button(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL)
        self.add_button(Gtk.STOCK_SAVE, Gtk.ResponseType.ACCEPT)
        self.set_local_only(True)

        #set supported types
        saveable = file_parsers.fileParser.get_saveable()
        for f in saveable:
            self.add_filter(f)

        #set default filter
        self.set_filter(saveable[0])

class htd_warn_archive(Gtk.MessageDialog):
    def __init__(self, parent):
        flags = Gtk.DialogFlags.MODAL & Gtk.DialogFlags.DESTROY_WITH_PARENT
        Gtk.MessageDialog.__init__(self, parent, flags, Gtk.MessageType.WARNING, Gtk.ButtonsType.NONE, "Archive completed tasks?")
        self.format_secondary_text("This will move all top-level completed tasks to an archive list. This action cannot be undone.")
        self.add_button(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL)
        self.add_button(Gtk.STOCK_OK, Gtk.ResponseType.ACCEPT)
        self.set_default_response(Gtk.ResponseType.ACCEPT)

class htd_warn_discard(Gtk.MessageDialog):
    def __init__(self, parent, fname, time_since_save):
        flags = Gtk.DialogFlags.MODAL & Gtk.DialogFlags.DESTROY_WITH_PARENT
        Gtk.MessageDialog.__init__(self, parent, flags, Gtk.MessageType.WARNING, Gtk.ButtonsType.NONE, "Save changes to \"%s\" before closing?" % fname)
        self.format_secondary_text("If you don't save, changes from the last %s will be permanently lost." % time_since_save)
        delbtn = self.add_button("Close _without Saving", Gtk.ResponseType.CLOSE)
        self.add_button(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL)
        self.add_button(Gtk.STOCK_SAVE, Gtk.ResponseType.ACCEPT)
        self.set_default_response(Gtk.ResponseType.ACCEPT)

class htd_about(Gtk.AboutDialog):
    def __init__(self, parent):
        Gtk.AboutDialog.__init__(self)
        self.set_transient_for(parent)
        self.set_program_name("HiToDO")
        self.set_version(parent.PROGRAM_VERSION)
        self.set_copyright(u"Copyright \xa9 2013 Peter Andrews")
        self.set_comments("Heirarchical task manager inspired by AbstractSpoon's ToDoList.")
        self.set_license_type(Gtk.License.GPL_3_0)
        self.set_website("https://github.com/aurule/HiToDo")

class htd_version_warning(Gtk.MessageDialog):
    def __init__(self, parent):
        flags = Gtk.DialogFlags.MODAL & Gtk.DialogFlags.DESTROY_WITH_PARENT
        Gtk.MessageDialog.__init__(self, parent, flags, Gtk.MessageType.WARNING, Gtk.ButtonsType.NONE, "The file you selected is from a newer version of HiToDo")
        self.format_secondary_text("All the basics will work, but newer metadata and features will be lost if you overwrite the file.")
        self.add_button("_Open Anyway", 1)
        self.add_button(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL)
        self.add_button("Open a _Copy", 2)
        self.set_default_response(2)

class htd_file_read_error(Gtk.MessageDialog):
    def __init__(self, parent, fname):
        flags = Gtk.DialogFlags.MODAL & Gtk.DialogFlags.DESTROY_WITH_PARENT
        Gtk.MessageDialog.__init__(self, parent, flags, Gtk.MessageType.ERROR, Gtk.ButtonsType.CANCEL, "The file \"%s\" cannot be opened" % fname)
        self.format_secondary_text("You might not have permission to view this file, or it may be corrupted.")

class htd_file_write_error(Gtk.MessageDialog):
    def __init__(self, parent):
        flags = Gtk.DialogFlags.MODAL & Gtk.DialogFlags.DESTROY_WITH_PARENT
        Gtk.MessageDialog.__init__(self, parent, flags, Gtk.MessageType.ERROR, Gtk.ButtonsType.CANCEL, "Cannot save to the file you selected")
        self.format_secondary_text("Make sure you have permission to write to the file.")