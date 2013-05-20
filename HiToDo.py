#!/usr/bin/env python

from gi.repository import Gtk, Gdk, Pango
from datetime import datetime, timedelta as td
from os import linesep

import testing

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
            <menuitem action='sel_all' />
            <menuitem action='sel_none' />
            <menuitem action='sel_inv' />
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
        self.tasklist = Gtk.TreeStore(
            int,    #priority
            int,    #pct complete
            object, #est time taken
            object, #act time taken
            object, #est begin
            object, #est complete
            object, #act begin
            object, #act complete
            object, #due
            str,    #from
            str,    #to
            str,    #status
            bool,   #done
            str,    #title
            str,    #notes
            bool    #use due time
        )
        
        self.assignees = Gtk.ListStore(str)
        self.assigners = Gtk.ListStore(str)
        self.statii = Gtk.ListStore(str)
        self.priority_adj = Gtk.Adjustment(5, 0, 26, 1, 5, 5)
        self.seliter = None
        self.sellist = None
        self.selcount = 0
        self.title_editor = None
        self.notes_ctl_mask = False
        self.notes_shift_mask = False
        
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
        #   notes - str
        #   use due time - bool
        
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
        
        #set up columns
        self.create_view_columns()
        
        #set up selection handling and add the completed table widget
        self.selection = self.task_view.get_selection()
        self.selection.set_mode(Gtk.SelectionMode.MULTIPLE)
        self.sel_changed_handler = self.selection.connect("changed", self.task_selected)
        self.task_view.set_properties(expander_column=self.col_title, enable_tree_lines=True, reorderable=True)
        self.task_view.connect('key-press-event', self.tasks_keys_dn)
        self.task_view.connect('key-release-event', self.tasks_keys_up)
        task_scroll_win.add(self.task_view)
        task_pane.pack1(task_scroll_win, True, True)
        
        #add notes area
        notes_scroll_win = Gtk.ScrolledWindow()
        notes_scroll_win.set_hexpand(True)
        notes_scroll_win.set_vexpand(True)
        self.notes_view = Gtk.TextView()
        self.notes_view.connect('focus-out-event', self.commit_notes)
        self.notes_view.connect('key-press-event', self.notes_keys_dn)
        self.notes_view.connect('key-release-event', self.notes_keys_up)
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
    
    def skip(self, widget=None):
        pass
    
    def add_task(self, widget=None, parent_iter=None):
        self.commit_all()
        new_row_iter = self.tasklist.append(parent_iter, [
            5,      #default priority TODO inherit from parent
            0,      #pct complete
            None,   #est time taken TODO if not set explicitly, this can be calculated as sum(children's est duration)
            None,   #act time taken TODO if not set explicitly, this can be calculated as sum(children's act duration)
            None,   #est begin TODO if not set explicitly, this can be calculated from the earliest child est begin
            None,   #est complete TODO if not set explicitly, this can be calculated from the latest child est complete
            None,   #act begin TODO if not set explicitly, this can be calculated from the earliest child act begin
            None,   #act complete TODO if not set explicitly, this can be calculated from the earliest child act complete
            None,   #due TODO inherit from parent, if present
            "",     #from TODO inherit from parent, if present
            "",     #to TODO inerherit from parent, if present
            "",     #status
            False,  #done
            "",     #title
            "",     #notes
            False   #use due time TODO inerherit from parent, if present
            ])
        #select new row and immediately edit title field
        self.selection.select_iter(new_row_iter)
        path = self.tasklist.get_path(new_row_iter)
        if parent_iter is not None:
            self.task_view.expand_to_path(path)
        self.task_view.set_cursor_on_cell(path, self.col_title, self.title_cell, True)
    
    def add_subtask(self, widget=None):
        self.add_task(parent_iter = self.seliter)
    
    def commit_all(self):
        '''Commit all possibly-in-progress edits.'''
        self.commit_title()
        self.commit_notes()
        #TODO commit other editable fields (from, to, status, and maybe others)
    
    def commit_notes(self, widget=None, data=None):
        if self.seliter is None: return
        if self.notes_view.has_focus():
            self.task_view.grab_focus()
        else:
            return
        
        start = self.notes_buff.get_iter_at_offset(0)
        end = self.notes_buff.get_iter_at_offset(-1)
        text = self.notes_buff.get_text(start, end, False)
        self.tasklist[self.seliter][14] = text
    
    def commit_title(self, widget=None, path=None, new_title=None, write=True):
        if path is None:
            if self.title_editor is None: return
            path = self.title_edit_path
            new_title = self.title_editor.get_text()
            self.title_editor.disconnect(self.title_key_press_catcher)
        self.title_editor = None #clear this to prevent eating memory
        
        old_title = self.tasklist[path][13]
        
        if new_title is None:
            if old_title == '':
                self.del_task(path)
            return
        
        #If the new title is blank and the task is new, just delete it.
        #If the new title is blank but the task has an existing title, cancel the edit.
        if new_title == '':
            if old_title == '':
                self.del_task(path)
                return
            else:
                return
        
        #finally, set the new title if allowed
        if write is True: self.tasklist[path][13] = new_title
    
    def title_edit_start(self, renderer, editor, path):
        self.title_edit_path = str(path)
        self.title_edit_old_val = self.tasklist[path][13]
        self.title_editor = editor
        self.title_key_press_catcher = editor.connect("key-press-event", self.title_keys_dn)
    
    def commit_done(self):
        #TODO
        #self.title_cell.set_properties(strikethrough=True, foreground="#bbb")
        pass
    
    def del_current_task(self, widget=None):
        refs = []
        #first we get references to each row
        for path in self.sellist:
            refs.append(self.tasklist.get_iter(path))
        #only then can we remove them without invalidating paths
        for ref in refs:
            self.tasklist.remove(ref)
        
        self.seliter = None
    
    def del_task(self, path):
        treeiter = self.tasklist.get_iter(path)
        self.tasklist.remove(treeiter)
    
    def update_task(self, widget=None):
        #TODO
        #when Done is True, we need to mark our pct complete as 100, then ping our parent so it can update its percent complete
        #when our pct complete is updated, we also need to ping our parent
        #pct complete is calculated differently by whether or not we have children:
        #   with chlidren, pct complete = number of children * 100 / sum(children's pct completes)
        #   sans children, pct complete = 100 * Done
        pass
    
    def notes_keys_dn(self, widget=None, event=None):
        kvn = Gdk.keyval_name(event.keyval)
        if kvn == "Control_L" or kvn == "Control_R":
            self.notes_ctl_mask = True
        if kvn == "Return" and self.notes_ctl_mask:
            self.commit_notes()
            return True
    
    def notes_keys_up(self, widget=None, event=None):
        kvn = Gdk.keyval_name(event.keyval)
        if kvn == "Control_L" or kvn == "Control_R":
            self.notes_ctl_mask = False
    
    def tasks_keys_dn(self, widget=None, event=None):
        kvn = Gdk.keyval_name(event.keyval)
        if kvn == "Delete":
            self.del_current_task()
    
    def tasks_keys_up(self, widget=None, event=None):
        kvn = Gdk.keyval_name(event.keyval)
    
    def title_keys_dn(self, widget=None, event=None):
        kvn = Gdk.keyval_name(event.keyval)
        if kvn == "Escape":
            self.commit_title(path=self.title_edit_path, new_title='', write=False)
    
    def select_none(self, widget=None):
        self.selection.unselect_all()
    
    def select_all(self, widget=None):
        self.selection.select_all()
    
    def select_inv(self, widget=None):
        if self.selcount == 0:
            self.select_all()
        elif self.selcount == len(self.tasklist):
            self.select_none()
        else:
            #disconnect selection changed handler
            self.selection.disconnect(self.sel_changed_handler)
            #invert recursively
            self.__invert_tasklist_selection(self.tasklist.get_iter_first())
            #reconnect selection changed handler
            self.sel_changed_handler = self.selection.connect("changed", self.task_selected)
            self.task_selected(self.selection)
    
    def __invert_tasklist_selection(self, treeiter):
        while treeiter != None:
            #swap selection state on iter
            if self.selection.iter_is_selected(treeiter):
                self.selection.unselect_iter(treeiter)
            else:
                self.selection.select_iter(treeiter)
            #probe children
            if self.tasklist.iter_has_child(treeiter):
                childiter = store.iter_children(treeiter)
                self.__invert_tasklist_selection(childiter)
            treeiter = self.tasklist.iter_next(treeiter)
    
    def open_file(self):
        #placeholder
        return
        #when adding lots of rows (like from a new file)...
        self.task_view.freeze_child_notify()
        self.task_view.set_model(None)
        self.tasklist.clear()
        #disable model sorting
        #load the file and add rows to self.tasklist
        #re-enable model sorting
        self.task_view.set_model(self.tasklist)
        self.task_view.thaw_child_notify()
    
    def task_selected(self, widget):
        self.selcount = widget.count_selected_rows()
        self.sellist = widget.get_selected_rows()[1]
        
        #if there's anything in the list, commit our changes
        self.commit_all()
        
        #set internal selection vars    
        if self.selcount == 1:
            self.seliter = self.tasklist.get_iter(self.sellist[0])
            self.notes_buff.set_text(self.tasklist[self.seliter][14])
        else:
            self.seliter = None
            self.notes_buff.set_text('')
    
    def due_render(self, col, cell, model, tree_iter, data):
        val = model[tree_iter][8]
        duetime = model[tree_iter][15]
        
        fmt = "%x %X" if duetime else "%x"
        out = "" if val is None else val.strftime(fmt)
        
        cell.set_property("text", str(out))
    
    def note_render(self, col, cell, model, tree_iter, data):
        val = model[tree_iter][14]
        out = '' if val == '' else "[%s]" % val.replace(linesep, ' ')
        
        cell.set_property("text", out)
    
    def create_view_columns(self):
        priority = Gtk.CellRendererSpin(editable=True, digits=2, adjustment=self.priority_adj)
        col_priority = Gtk.TreeViewColumn("!", priority, text=0)
        col_priority.set_sort_column_id(0)
        self.task_view.append_column(col_priority)
        
        due = Gtk.CellRendererText()
        col_due = Gtk.TreeViewColumn("Due", due)
        col_due.set_sort_column_id(8)
        col_due.set_cell_data_func(due, self.due_render)
        self.task_view.append_column(col_due)
        
        pct = Gtk.CellRendererProgress()
        col_pct = Gtk.TreeViewColumn("%", pct, value=1)
        col_pct.set_sort_column_id(1)
        self.task_view.append_column(col_pct)
        
        assigner = Gtk.CellRendererCombo(model=self.assigners, has_entry=True, editable=True)
        col_assigner = Gtk.TreeViewColumn("From", assigner, text_column=9)
        col_assigner.set_sort_column_id(9)
        self.task_view.append_column(col_assigner)
        
        assignee = Gtk.CellRendererCombo(model=self.assignees, has_entry=True, editable=True)
        col_assignee = Gtk.TreeViewColumn("To", assignee, text_column=10)
        col_assignee.set_sort_column_id(10)
        self.task_view.append_column(col_assignee)
        
        status = Gtk.CellRendererCombo(model=self.statii, has_entry=True, editable=True)
        col_stats = Gtk.TreeViewColumn("Status", status, text_column=11)
        col_stats.set_sort_column_id(11)
        self.task_view.append_column(col_stats)
        
        done = Gtk.CellRendererToggle(activatable=True, radio=False)
        col_done = Gtk.TreeViewColumn(u"\u2713", done, active=12)
        col_done.set_sort_column_id(12)
        self.task_view.append_column(col_done)
        
        self.title_cell = Gtk.CellRendererText(editable=True, ellipsize=Pango.EllipsizeMode.NONE)
        self.title_cell.connect("edited", self.commit_title)
        self.title_cell.connect("editing-started", self.title_edit_start)
        self.title_cell.connect("editing-canceled", self.commit_title, None, None, True)
        note = Gtk.CellRendererText(editable=False, ellipsize=Pango.EllipsizeMode.MIDDLE, foreground="#bbb")
        self.col_title = Gtk.TreeViewColumn("Title")
        self.col_title.pack_start(self.title_cell, True)
        self.col_title.pack_start(note, False)
        self.col_title.add_attribute(self.title_cell, "text", 13)
        self.col_title.set_cell_data_func(note, self.note_render)
        self.col_title.set_sort_column_id(13)
        self.task_view.append_column(self.col_title)
        '''
        renderer = Gtk.CellRendererText()
        col_ = Gtk.TreeViewColumn("Title", renderer, text=0)
        col_.set_sort_column_id(model data col)
        self.task_view.append_column(col_)
        '''
    
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
            ("task_new", Gtk.STOCK_ADD, "_New Task", "<Primary>N", "New task", self.add_task),
            ("task_newsub", Gtk.STOCK_INDENT, "New S_ubtask", "<Primary><Shift>N", "New subtask", self.add_subtask),
            ("task_del", Gtk.STOCK_REMOVE, None, None, "Delete task", self.del_current_task),
            ("task_cut", Gtk.STOCK_CUT, None, None, "Cut task", self.skip),
            ("task_copy", Gtk.STOCK_COPY, None, None, "Copy task", self.skip),
            ("task_paste", Gtk.STOCK_PASTE, None, None, "Paste task", self.skip),
            ("undo", Gtk.STOCK_UNDO, None, "<Primary>Z", "Undo", self.skip),
            ("redo", Gtk.STOCK_REDO, None, "<Primary><Shift>Z", "Redo", self.skip),
            ("sel_all", Gtk.STOCK_SELECT_ALL, None, "<Primary>A", None, self.select_all),
            ("sel_inv", None, "_Invert Selection", None, None, self.select_inv),
            ("sel_none", None, "Select _None", "<Primary><Shift>A", None, self.select_none)
        ])
    
    def create_ui_manager(self):
        uimanager = Gtk.UIManager()

        # Throws exception if something went wrong
        uimanager.add_ui_from_string(UI_XML)
        
        # Add the accelerator group to the toplevel window
        accelgroup = uimanager.get_accel_group()
        self.add_accel_group(accelgroup)
        return uimanager
    
    def destroy(self, widget):
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
