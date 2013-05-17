#!/usr/bin/env python

from gi.repository import Gtk, Gdk

UI_XML = """
<ui>
    <menubar name='MenuBar'>
        <menu action='FileMenu'>
            <menuitem action="new_file" />
            <menuitem action="open_file" />
            <separator />
            <menuitem action="save_file" />
            <menuitem action="saveas_file" />
            <separator />
            <menuitem action='quit' />
        </menu>
        <menu action='EditMenu'>
            <menuitem action='undo' />
            <menuitem action='redo' />
            <separator />
            <menuitem action='sel_inv' />
            <menuitem action='sel_all' />
            <menuitem action='sel_none' />
        </menu>
        <menu action='TaskMenu'>
            <menuitem action='task_new' />
            <menuitem action='task_newsub' />
            <menuitem action='task_del' />
            <separator />
            <menuitem action='task_cut' />
            <menuitem action='task_copy' />
            <menuitem action='task_paste' />
        </menu>
        <menu action='HelpMenu'>
            <menuitem action='help_about' />
        </menu>
    </menubar>
    <toolbar name='ToolBar'>
        <toolitem action='open_file' />
        <toolitem action='save_file' />
        <separator />
        <toolitem action='task_new' />
        <toolitem action='task_newsub' />
        <toolitem action='task_del' />
        <separator />
        <toolitem action='task_cut' />
        <toolitem action='task_copy' />
        <toolitem action='task_paste' />
    </toolbar>
</ui>
"""

# Define the gui and its actions.
class HiToDo(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self, title="HiToDo")
        self.set_default_size(900, 600)
        self.title = "HiToDo"
        
        #create core tree store
        self.tasklist = Gtk.TreeStore()
        #TODO externalize column defs to separate structure, for descriptions and more dynamic initialization
        self.tasklist.set_column_types([int, int, object, object, object, object, object, object, object, str, str, str, bool, str, object])
        #cols:
        #   priority by letter - spin/int
        #   pct. complete - int (no input)
        #   est. time taken - time
        #   act. time taken - time
        #   est. begin - datetime
        #   est. completion - datetime
        #   act. begin - datetime
        #   act. completion - datetime
        #   due - datetime
        #   from - combo/names
        #   to - combo/names
        #   status - combo
        #   done - bool/checkbox
        #   text - str
        #   notes - object (to allow for formatting later on)
        
        #create action groups
        top_actions = Gtk.ActionGroup("top_actions")
        self.create_top_actions(top_actions)
        task_actions = Gtk.ActionGroup("task_actions")
        self.create_task_actions(task_actions)
        
        #set up menu and toolbar
        uimanager = self.create_ui_manager()
        uimanager.insert_action_group(top_actions)
        uimanager.insert_action_group(task_actions)
        menubar = uimanager.get_widget("/MenuBar")
        toolbar = uimanager.get_widget("/ToolBar")
        toolbar.get_style_context().add_class(Gtk.STYLE_CLASS_PRIMARY_TOOLBAR)
        
        #start with a simple stacked layout
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        
        #add the menu and tool bars on top
        main_box.pack_start(menubar, False, False, 0)
        main_box.pack_start(toolbar, False, False, 0)
        
        #now we create a horizontal pane
        task_pane = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        task_pane.set_position(600)
        
        #add task list area
        task_scroll_win = Gtk.ScrolledWindow()
        task_scroll_win.set_hexpand(True)
        task_scroll_win.set_vexpand(True)
        self.task_view = Gtk.TreeView(self.tasklist)
        #TODO set up columns
        select = self.task_view.get_selection()
        select.connect("changed", self.task_selected)
        task_scroll_win.add(self.task_view)
        task_pane.pack1(task_scroll_win, True, True)
        
        #add notes area
        notes_scroll_win = Gtk.ScrolledWindow()
        notes_scroll_win.set_hexpand(True)
        notes_scroll_win.set_vexpand(True)
        self.notes_view = Gtk.TextView()
        self.notes_view.set_wrap_mode(Gtk.WrapMode.WORD)
        self.notes_buff = self.notes_view.get_buffer()
        notes_scroll_win.add(self.notes_view)
        task_pane.pack2(notes_scroll_win, True, True)
        
        #commit the task editing pane
        main_box.pack_start(task_pane, True, True, 0)
        
        #commit the ui
        self.add(main_box)
        
        # create a clipboard for easy copying
        self.clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)       
        self.connect("delete-event", Gtk.main_quit)
        self.show_all()
    
    def skip(self, widget=None, data=None):
        pass
    
    def open_file(self):
        #placeholder
        pass
        #when adding lots of rows (like from a new file)...
        self.task_view.freeze_child_notify()
        self.task_view.set_model(None)
        self.tasklist.clear()
        #disable model sorting
        #load the file and add rows to self.tasklist
        #re-enable model sorting
        self.task_view.set_model(self.tasklist)
        self.task_view.thaw_child_notify()
    
    def task_selected(self, widget, data=None):
        #set notes from task
        model, treeiter = widget.get_selected()
        if treeiter != None:
            self.notes_buff.set_text(model[treeiter][13])
    
    def create_top_actions(self, action_group):
        action_group.add_actions([
            ("new_file", Gtk.STOCK_NEW, None, "", None, self.skip),
            ("open_file", Gtk.STOCK_OPEN, None, None, "Open file", self.skip),
            ("save_file", Gtk.STOCK_SAVE, None, None, "Save file", self.skip),
            ("saveas_file", Gtk.STOCK_SAVE_AS, None, None, None, self.skip),
            ("quit", Gtk.STOCK_QUIT, None, None, None, self.destroy),
            ("help_about", Gtk.STOCK_ABOUT, None, None, None, self.skip),
            ("FileMenu", None, "_File"),
            ("EditMenu", None, "_Edit"),
            ("TaskMenu", None, "_Task"),
            ("HelpMenu", None, "_Help")
        ])
        
    def create_task_actions(self, action_group):
        action_group.add_actions([
            ("task_new", Gtk.STOCK_ADD, "New _Task", "<Primary>N", "New task", self.skip),
            ("task_newsub", Gtk.STOCK_INDENT, "New S_ubtask", "<Primary><Shift>N", "New subtask", self.skip),
            ("task_del", Gtk.STOCK_REMOVE, None, None, "Delete task", self.skip),
            ("task_cut", Gtk.STOCK_CUT, None, None, "Cut task", self.skip),
            ("task_copy", Gtk.STOCK_COPY, None, None, "Copy task", self.skip),
            ("task_paste", Gtk.STOCK_PASTE, None, None, "Paste task", self.skip),
            ("undo", Gtk.STOCK_UNDO, None, "<Primary>Z", "Undo", self.skip),
            ("redo", Gtk.STOCK_REDO, None, "<Primary><Shift>Z", "Redo", self.skip),
            ("sel_all", Gtk.STOCK_SELECT_ALL, None, "<Primary>A", None, self.skip),
            ("sel_inv", None, "_Invert Selection", None, None, self.skip),
            ("sel_none", None, "Select _None", "<Primary><Shift>A", None, self.skip)
        ])
    
    def create_ui_manager(self):
        uimanager = Gtk.UIManager()

        # Throws exception if something went wrong
        uimanager.add_ui_from_string(UI_XML)
        
        # Add the accelerator group to the toplevel window
        accelgroup = uimanager.get_accel_group()
        self.add_accel_group(accelgroup)
        return uimanager
    
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
