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
