#!/usr/bin/env python

from gi.repository import Gtk, Gdk

# Define the gui and its actions.
class HiToDo:
    def __init__(self):
        self.builder = Gtk.Builder()
        self.builder.add_from_file("hitodo.ui")
        self.title = "HiToDo" #default title
        
        #TODO set up signal handlers
        handlers_main = {
            "app.quit": self.destroy
        }
        self.builder.connect_signals(handlers_main)
        
        # create a clipboard for easy copying
        self.clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        
        #set our initial title and display the lot
        self.window = self.builder.get_object("main_window")
        self.window.set_title(self.title)
        self.window.show_all()
    
    def destroy(self, widget, data=None):
        Gtk.main_quit()
    
    def update_title(self, title):
        self.title = title
        self.window.set_title(self.title)

def main():
    Gtk.main()
    return

# If the program is run directly or passed as an argument to the python
# interpreter then create a Picker instance and show it
if __name__ == "__main__":
    htd = HiToDo()
    main()
