from gi.repository import Gtk
import xml.etree.ElementTree as ET

class htd_filter(Gtk.FileFilter):
    def __init__(self):
        Gtk.FileFilter.__init__(self)
        self.add_pattern("*.htd")
        self.set_name("HiToDo Files (*.htd)")
    
    def read_to_store(self, fname, treestore):
        pass
    
    def write(self, fname):
        pass
