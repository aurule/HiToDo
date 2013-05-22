from gi.repository import Gtk, Gdk

class htd_open(Gtk.FileChooserDialog):
    def __init__(self, parent):
        Gtk.FileChooserDialog.__init__(self, "Open File", parent, Gtk.FileChooserAction.OPEN)
        self.add_button(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL)
        self.add_button(Gtk.STOCK_OPEN, Gtk.ResponseType.ACCEPT)
        self.set_local_only(True)
        
        #set supported types
        all_files = Gtk.FileFilter()
        all_files.add_pattern("*.*")
        all_files.set_name("All Files")
        #self.add_filter(all_files)
        tdl = Gtk.FileFilter()
        tdl.add_pattern("*.tdl")
        tdl.set_name("ToDoList Files (*.tdl)")
        #self.add_filter(tdl)
        htd = Gtk.FileFilter()
        htd.add_pattern("*.htd")
        htd.set_name("HiToDo Files (*.htd)")
        #self.add_filter(htd)
        todotxt = Gtk.FileFilter()
        todotxt.add_pattern("todo.txt")
        todotxt.set_name("Todo.txt Files (todo.txt)")
        self.add_filter(todotxt)
        
        self.set_filter(todotxt)
        
