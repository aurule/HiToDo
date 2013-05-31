#!/usr/bin/env python

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

from __future__ import division
from gi.repository import Gtk, Gdk, Pango
from datetime import datetime, timedelta
from os import linesep
from os.path import basename, dirname, splitext
from urlparse import urlparse
from urllib import unquote
from dateutil.parser import parse as dateparse
from math import floor
import xml.etree.ElementTree as et

import testing
import dialogs
import file_parsers

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
            <menuitem action="recents" />
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
            <separator />
            <menuitem action='prefs' />
        </menu>
        <menu action='TaskMenu'>
            <menuitem action='task_new' />
            <menuitem action='task_newsub' />
            <menuitem action='task_del' />
            <separator />
            <menuitem action='task_cut' />
            <menuitem action='task_copy' />
            <menuitem action='task_paste' />
            <menuitem action='task_paste_into' />
        </menu>
        <menu action="ViewMenu">
            <menuitem action='expand_all' />
            <menuitem action='collapse_all' />
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
        <toolitem action='undo' />
        <toolitem action='redo' />
        <separator />
        <toolitem action='task_cut' />
        <toolitem action='task_copy' />
        <toolitem action='task_paste' />
        <separator />
        <toolitem action='track_spent' />
    </toolbar>
</ui>
"""

# Define the gui and its actions.
class HiToDo(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self)
        self.set_default_size(1100, 700)
        self.title = "Untitled List - HiToDo"
        self.set_title(self.title)
        
        #create core tree store
        self.tasklist = Gtk.TreeStore(
            int,    #priority
            int,    #pct complete
            int,    #est time taken in seconds
            int,    #act time taken in seconds
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
            bool,   #use due time
            bool,   #inverted done flag
            bool    #whether this row's spent time is currently tracked
        )
        self.tasklist.set_sort_func(7, self.datecompare, None)
        self.tasklist.set_sort_func(8, self.datecompare, None)
        self.tasklist.connect("row-changed", self.make_dirty)
        self.tasklist.connect("row-deleted", self.make_dirty)
        
        self.defaults = [
            5,      #default priority
            0,      #pct complete
            0,      #est time taken
            0,      #act time taken
            None,   #est begin
            None,   #est complete
            None,   #act begin
            None,   #act complete
            None,   #due
            "",     #from
            "",     #to
            "",     #status
            False,  #done
            "",     #title
            "",     #notes
            False,  #use due time
            True,   #inverted done
            False   #spent tracked
        ]
        
        self.assignees = Gtk.ListStore(str)
        self.assignees_list = []
        self.assigners = Gtk.ListStore(str)
        self.assigners_list = []
        self.statii = Gtk.ListStore(str)
        self.statii_list = []
        self.priority_adj = Gtk.Adjustment(5, 0, 26, 1, 5, 5)
        self.seliter = None
        self.sellist = None
        self.selcount = 0
        self.title_editor = None
        self.notes_ctl_mask = False
        self.notes_shift_mask = False
        self.parent = None
        self.title_key_press_catcher = None
        self.file_name = ""
        self.file_filter = None
        self.file_dirty = False
        self.tracking = None
        self.timer_start = None
        self.last_save = datetime.now()
        
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
        task_pane.set_position(900)
        
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
        self.task_view.set_properties(expander_column=self.col_title, enable_tree_lines=True, reorderable=True, enable_search=True, search_column=13, rules_hint=True)
        self.task_view.connect('key-press-event', self.tasks_keys_dn)
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
        
        self.open_dlg = dialogs.htd_open(self)
        self.save_dlg = dialogs.htd_save(self)
        self.about_dlg = dialogs.htd_about(self)
        self.prefs_dlg = dialogs.htd_prefs(self)
    
    def skip(self, widget=None):
        pass
    
    def datecompare(self, model, row1, row2, data=None):
        sort_column, _ = model.get_sort_column_id()
        value1 = model.get_value(row1, sort_column)
        value2 = model.get_value(row2, sort_column)
        
        if value1 < value2:
            return -1
        elif value1 == value2:
            return 0
        else:
            return 1
    
    def add_task(self, widget=None, parent_iter=None):
        self.commit_all()
        
        #we can inherit some things if we're a new child
        if parent_iter is None and self.parent is not None:
            parent_iter = self.parent
            parent = self.tasklist[parent_iter]
        else:
            parent = self.defaults
        
        new_row_iter = self.tasklist.append(parent_iter, [
            parent[0],              #default priority (inherit from parent)
            self.defaults[1],       #pct complete
            self.defaults[2],       #est time taken
            self.defaults[3],       #act time taken
            self.defaults[4],       #est begin TODO if not set explicitly, this can be calculated from the earliest child est begin
            self.defaults[5],       #est complete
            self.defaults[6],       #act begin TODO if not set explicitly, this can be calculated from the earliest child act begin
            self.defaults[7],       #act complete
            self.defaults[8],       #due
            parent[9],              #from (inherit from parent)
            parent[10],             #to (inherit from parent)
            self.defaults[11],      #status
            self.defaults[12],      #done
            self.defaults[13],      #title
            self.defaults[14],      #notes
            parent[15],             #use due time (inherit from parent)
            self.defaults[16],      #inverted done
            self.defaults[17]       #spent tracked
        ])
        #select new row and immediately edit title field
        self.recalc_parent_pct(str(self.tasklist.get_path(new_row_iter)))
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
        self.commit_status()
        self.commit_assigner()
        self.commit_assignee()
        self.commit_due()
        self.commit_priority()
        self.commit_est()
        self.commit_spent()
    
    def commit_est(self, widget=None, path=None, new_est=None):
        if path is None: return
        
        if not is_number(new_est): return
        old_est = self.tasklist[path][2]
        new_est = float(new_est)
        out = floor(new_est * 3600)
        self.tasklist[path][2] = int(out)
    
        parts = path.rpartition(':')
        parent_path = parts[0]
        if parent_path != "":
            parent_est = self.tasklist[parent_path][2]
            pest = (parent_est + out - old_est)/3600
            self.commit_est(path=parent_path, new_est=pest)
        
    def est_edit_start(self, renderer, editor, path):
        val = self.tasklist[path][2]
        editor.set_text(str(val/3600)) #don't display the H suffix during editing
        editor.set_icon_from_stock(Gtk.EntryIconPosition.SECONDARY, Gtk.STOCK_REFRESH)
        editor.set_icon_tooltip_text(Gtk.EntryIconPosition.SECONDARY, "Recalculate from children")
        editor.connect("icon-press", self.derive_est, path)
    
    def derive_est(self, entry=None, pos=None, event=None, path=None):
        #Assumes the children are already calculated out and does not recurse.
        #Just peeks at the top level children's est totals.
        total_est = 0
        treeiter = self.tasklist.get_iter(path)
        if self.tasklist.iter_has_child(treeiter):
            n_children = self.tasklist.iter_n_children(treeiter)
            child_iter = self.tasklist.iter_children(treeiter)
            while child_iter is not None:
                total_est += self.tasklist[child_iter][3]
                child_iter = self.tasklist.iter_next(child_iter)
        self.tasklist[path][3] = total_est
    
    def commit_spent(self, widget=None, path=None, new_spent=None):
        if path is None or path == "": return
        
        if not is_number(new_spent): return
        old_spent = self.tasklist[path][3]
        new_spent = float(new_spent)
        out = floor(new_spent * 3600)
        self.tasklist[path][3] = int(out)
    
        parts = path.rpartition(':')
        parent_path = parts[0]
        if parent_path != "":
            parent_spent = self.tasklist[parent_path][3]
            pspent = (parent_spent + out - old_spent)/3600
            self.commit_spent(path=parent_path, new_spent=pspent)
        
    def spent_edit_start(self, renderer, editor, path):
        val = self.tasklist[path][3]
        editor.set_text(str(val/3600)) #don't display the H suffix during editing
        editor.set_icon_from_stock(Gtk.EntryIconPosition.SECONDARY, Gtk.STOCK_REFRESH)
        editor.set_icon_tooltip_text(Gtk.EntryIconPosition.SECONDARY, "Recalculate from children")
        editor.connect("icon-press", self.derive_spent, path)
    
    def derive_spent(self, entry=None, pos=None, event=None, path=None):
        #Assumes the children are already calculated out and does not recurse.
        #Just peeks at the top level children's spent totals.
        total_spent = 0
        treeiter = self.tasklist.get_iter(path)
        if self.tasklist.iter_has_child(treeiter):
            n_children = self.tasklist.iter_n_children(treeiter)
            child_iter = self.tasklist.iter_children(treeiter)
            while child_iter is not None:
                total_spent += self.tasklist[child_iter][3]
                child_iter = self.tasklist.iter_next(child_iter)
        self.tasklist[path][3] = total_spent
    
    def track_spent(self, action=None, data=None):
        on = action.get_active()
        if on:
            if self.seliter is None:
                action.set_active(False)
                return
            if self.tasklist[self.seliter][12]:
                action.set_active(False)
                return
            
            self.tracking = self.seliter
            self.timer_start = datetime.now()
            title = self.tasklist[self.tracking][13]
            self.tasklist[self.tracking][17] = True
            action.set_tooltip("Stop tracking time toward '%s'" % title)
        else:
            if self.tracking is None: return
            
            diff = datetime.now() - self.timer_start
            secs = int(diff.total_seconds())
            path = str(self.tasklist.get_path(self.tracking))
            nspent = (self.tasklist[self.tracking][3] + secs) / 3600
            self.commit_spent(path=path, new_spent = nspent)
            self.tasklist[self.tracking][17] = False
            self.make_dirty()
            
            self.tracking = None
            self.timer_start = None
            action.set_tooltip("Start tracking time toward current task")
    
    def commit_done(self, renderer=None, path=None, data=None):
        if path is None: return
        
        done = renderer.get_active()
        if not done:
            #we're transitioning from not-done to done
            
            #we're now 100% complete
            pct = 100
            
            self.force_children_done(path)
            self.tasklist[path][7] = datetime.now()
            if self.tasklist[path][17]:
                self.track_action.set_active(False)
        else:
            #we're transitioning from done to not-done
            pct = self.calc_pct_from_children(path)
        
        self.tasklist[path][12] = not done
        self.tasklist[path][16] = done
        self.tasklist[path][1] = pct
        
        #recalculate our parent's pct complete, if we have one
        self.recalc_parent_pct(path)
    
    def recalc_parent_pct(self, path):
        parts = path.rpartition(':')
        parent_path = parts[0]
        if parent_path == '': return
        
        parent_iter = self.tasklist.get_iter(parent_path)
        if self.tasklist[parent_iter][12]: return #skip calculation if parent is marked "done"
        
        n_children = self.tasklist.iter_n_children(parent_iter)
        if n_children == 0:
            final_pct = 0
        else:
            childiter = self.tasklist.iter_children(parent_iter)
            total_pct = 0
            while childiter != None:
                total_pct += self.tasklist[childiter][1]
                childiter = self.tasklist.iter_next(childiter)
            
            final_pct = int(floor(total_pct / n_children))
        
        self.tasklist[parent_iter][1] = final_pct
        self.recalc_parent_pct(parent_path)
    
    def calc_pct_from_children(self, path):
        #Assumes the children are already calculated out and does not recurse.
        #Just peeks at the top level children's pct completes.
        treeiter = self.tasklist.get_iter(path)
        if self.tasklist.iter_has_child(treeiter):
            n_children = self.tasklist.iter_n_children(treeiter)
            child_iter = self.tasklist.iter_children(treeiter)
            total_pct = 0
            while child_iter is not None:
                total_pct += self.tasklist[child_iter][1]
                child_iter = self.tasklist.iter_next(child_iter)
            
            return int(floor(total_pct / n_children))
        else:
            return 0
    
    def force_children_done(self, path):
        treeiter = self.tasklist.get_iter(path)
        childiter = self.tasklist.iter_children(treeiter)
        self.__force_peers_done(childiter)
    
    def __force_peers_done(self, treeiter):
        while treeiter != None:
            self.tasklist[treeiter][1] = 100
            self.tasklist[treeiter][12] = True
            self.tasklist[treeiter][16] = False
            if self.tasklist.iter_has_child(treeiter):
                child_iter = self.tasklist.iter_children(treeiter)
                self.__force_peers_done(child_iter)
            treeiter = self.tasklist.iter_next(treeiter)
    
    def commit_priority(self, widget=None, path=None, new_priority=None):
        if path is None: return
        
        #priorities have to be integers
        if new_priority.isdigit():
            self.tasklist[path][0] = int(new_priority)
    
    def commit_due(self, widget=None, path=None, new_due=None):
        if path is None: return
        
        try:
            dt = dateparse(new_due, fuzzy=True)
            self.tasklist[path][8] = dt
        except ValueError:
            pass
    
    def commit_complete(self, widget=None, path=None, new_complete=None):
        if path is None: return
        
        if new_complete == '':
            self.tasklist[path][7] = None
        else:
            try:
                dt = dateparse(new_complete, fuzzy=True)
                self.tasklist[path][7] = dt
            except ValueError:
                pass
    
    def commit_status(self, widget=None, path=None, new_status=None):
        if path is None: return
        
        if new_status != '' and new_status not in self.statii_list:
            self.statii.append([new_status])
            self.statii_list.append(new_status)
        self.tasklist[path][11] = new_status
    
    def commit_assigner(self, widget=None, path=None, new_assigner=None):
        if path is None: return
        
        if new_assigner != '' and new_assigner not in self.assigners_list:
            self.assigners.append([new_assigner])
            self.assigners_list.append(new_assigner)
        self.tasklist[path][9] = new_assigner
    
    def commit_assignee(self, widget=None, path=None, new_assignee=None):
        if path is None: return
        
        if new_assignee != '' and new_assignee not in self.assignees_list:
            self.assignees.append([new_assignee])
            self.assignees_list.append(new_assignee)
        self.tasklist[path][10] = new_assignee
    
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
    
    def due_edit_start(self, renderer, editor, path):
        editor.set_icon_from_icon_name(Gtk.EntryIconPosition.SECONDARY, "appointment-new")
        editor.connect("icon-press", self.due_pick)
    
    def due_pick(self, entry, pos, event, data=None):
        #TODO add calendar picker popup
        pass
    
    def complete_edit_start(self, renderer, editor, path):
        editor.set_icon_from_icon_name(Gtk.EntryIconPosition.SECONDARY, "appointment-new")
        editor.connect("icon-press", self.complete_pick)
    
    def complete_pick(self, entry, pos, event, data=None):
        #TODO add calendar picker popup
        pass
    
    def del_current_task(self, widget=None):
        if self.sellist is None: return
        refs = []
        #first we get references to each row
        for path in self.sellist:
            #stop tracking if needed
            if self.tasklist[path][17]:
                self.track_action.set_active(False)
            refs.append((self.tasklist.get_iter(path), path))
        #only then can we remove them without invalidating paths
        for ref, path in refs:
            self.commit_spent(path=str(path), new_spent=0)
            self.commit_est(path=str(path), new_est=0)
            
            self.tasklist.remove(ref)
            self.recalc_parent_pct(str(path))
        
        self.seliter = None
    
    def del_task(self, path):
        #stop tracking if needed
        if self.tasklist[path][17]:
            self.track_action.set_active(False)
        treeiter = self.tasklist.get_iter(path)
        self.commit_spent(path=path, new_spent=0)
        self.commit_est(path=path, new_est=0)
        self.tasklist.remove(treeiter)
        self.recalc_parent_pct(str(path))
    
    def notes_keys_dn(self, widget=None, event=None):
        kvn = Gdk.keyval_name(event.keyval)
        if kvn == "Control_L" or kvn == "Control_R":
            self.notes_ctl_mask = True
        if kvn == "Return" and self.notes_ctl_mask:
            self.commit_notes()
            self.notes_ctl_mask = False
            return True
    
    def notes_keys_up(self, widget=None, event=None):
        kvn = Gdk.keyval_name(event.keyval)
        if kvn == "Control_L" or kvn == "Control_R":
            self.notes_ctl_mask = False
    
    def tasks_keys_dn(self, widget=None, event=None):
        kvn = Gdk.keyval_name(event.keyval)
        if kvn == "Delete":
            self.del_current_task()
            return True
        if kvn == "F2":
            path = self.tasklist.get_path(self.seliter)
            self.task_view.set_cursor_on_cell(path, self.col_title, self.title_cell, True)
            return True
    
    def title_keys_dn(self, widget=None, event=None):
        kvn = Gdk.keyval_name(event.keyval)
        if kvn == "Escape":
            self.commit_title(path=self.title_edit_path, new_title='', write=False)
    
    def task_selected(self, widget):
        self.selcount = widget.count_selected_rows()
        self.sellist = widget.get_selected_rows()[1]
        
        #if there's anything in the list, commit our changes
        self.commit_all()
        
        #set internal selection vars    
        if self.selcount == 1:
            self.seliter = self.tasklist.get_iter(self.sellist[0])
            self.parent = self.tasklist.iter_parent(self.seliter)
            self.notes_buff.set_text(self.tasklist[self.seliter][14])
        else:
            self.seliter = None
            self.notes_buff.set_text('')
    
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
                childiter = self.tasklist.iter_children(treeiter)
                self.__invert_tasklist_selection(childiter)
            treeiter = self.tasklist.iter_next(treeiter)
    
    def expand_all(self, widget=None):
        self.task_view.expand_all()
    
    def collapse_all(self, widget=None):
        self.task_view.collapse_all()
    
    def open_recent(self, widget):
        uri = widget.get_current_uri()
        path = urlparse(uri).path
        self.file_name = unquote(path)
        self.file_filter = file_parsers.pick_filter(path)
        self.__do_open()
    
    def open_file(self, widget=None):
        if not self.confirm_discard(): return
        
        retcode = self.open_dlg.run()
        self.open_dlg.hide()
        if retcode != -3: return #cancel out if requested
        
        self.file_name = self.open_dlg.get_filename()
        self.file_filter = self.save_dlg.get_filter()
        self.__do_open()

    def __do_open(self):
        '''Internal function to open a file from self.file_name using the reader at self.file_filter.'''
        self.file_dirty = False
        self.update_title()
        
        #when adding lots of rows, we want to disable the display until we're done
        self.task_view.freeze_child_notify()
        self.task_view.set_model(None)
        self.tasklist.clear()
        
        #add rows to self.tasklist
        rows_to_expand, selme = self.file_filter.read_to_store(self.file_name, self.assigners_list, self.assignees_list, self.statii_list, self.tasklist)
        
        #iterate assigners, assignees, and statii to put names into respective liststores
        for n in self.assigners_list:
            self.assigners.append([n])
        for n in self.assignees_list:
            self.assignees.append([n])
        for n in self.statii_list:
            self.statii.append([n])
        
        #reconnect model to view
        self.task_view.set_model(self.tasklist)
        for pathstr in rows_to_expand:
            treeiter = self.tasklist.get_iter(pathstr)
            path = self.tasklist.get_path(treeiter)
            self.task_view.expand_row(path, False)
        if selme != '':
            self.selection.select_iter(self.tasklist.get_iter(selme))
        self.task_view.thaw_child_notify()
        
        self.update_title()
        self.last_save = datetime.now()
    
    def confirm_discard(self):
        if not self.file_dirty: return True
        
        diff = datetime.now() - self.last_save
        sec = diff.total_seconds()
        if sec > 86400:
            diff_num = int(sec / 86400)
            diff_unit = "day"
        elif sec > 3600:
            diff_num = int(sec / 3600)
            diff_unit = "hour"
        elif sec > 60:
            diff_num = int(sec / 60)
            diff_unit = "minute"
        else:
            diff_num = int(sec)
            diff_unit = "second"
        
        diff_text = "%s %s" % (diff_num, diff_unit)
        if diff_num > 1: diff_text += "s"
        
        fname = "Untitled List" if self.file_name == ""  else self.file_name
        
        dlg = dialogs.htd_warn_discard(self, fname, diff_text)
        retval = dlg.run()
        dlg.destroy()
        
        if retval == -3:
            #save
            self.save_file()
            return not self.file_dirty
        elif retval == -7:
            #discard
            return True
        else:
            #cancel or any other code (like from esc key)
            return False
    
    def save_file(self, widget=None):
        if self.file_name == "":
            self.save_file_as()
            return
        
        if self.seliter is not None:
            selpath = str(self.tasklist.get_path(self.seliter))
        else:
            selpath = ''
        self.file_filter.write(self.file_name, self.assigners_list, self.assignees_list, self.statii_list, self.tasklist, self.task_view, selpath)
        
        self.file_dirty = False
        self.update_title()
        self.last_save = datetime.now()
    
    def save_file_as(self, widget=None):
        retcode = self.save_dlg.run()
        self.save_dlg.hide()
        if retcode != -3: return #cancel out if requested
        
        self.file_name = self.save_dlg.get_filename()
        self.file_filter = self.save_dlg.get_filter()
        ext = splitext(self.file_name)[1]
        if ext == '':
            self.file_name += self.file_filter.file_extension
        self.save_file()
    
    def update_title(self):
        if self.file_name != "":
            ttl = "%s (%s) - HiToDo" % (basename(self.file_name), dirname(self.file_name))
        else:
            ttl = "Untitled List - HiToDo"
        
        self.title = "*"+ttl if self.file_dirty else ttl
        
        self.set_title(self.title)
    
    def make_dirty(self, path=None, it=None, data=None):
        self.file_dirty = True
        self.update_title()
    
    def new_file(self, widget=None):
        self.confirm_discard()
        self.tasklist.clear()
        self.file_name = ""
        self.file_dirty = False
    
    def show_about(self, widget=None):
        self.about_dlg.run()
        self.about_dlg.hide()
    
    def set_prefs(self, widget=None):
        self.prefs_dlg.show()
    
    def due_render(self, col, cell, model, tree_iter, data):
        val = model[tree_iter][8]
        duetime = model[tree_iter][15]
        
        fmt = "%x %X" if duetime else "%x"
        out = "" if val is None else val.strftime(fmt)
        cell.set_property("text", str(out))
    
    def completed_render(self, col, cell, model, tree_iter, data):
        val = model[tree_iter][7]
        duetime = model[tree_iter][15]
        
        fmt = "%x %X" if duetime else "%x"
        out = "" if val is None else val.strftime(fmt)
        cell.set_property("text", str(out))
    
    def note_render(self, col, cell, model, tree_iter, data):
        val = model[tree_iter][14]
        out = '' if val == '' else "[%s]" % val.replace(linesep, ' ')
        cell.set_property("text", out)
    
    def est_render(self, col, cell, model, tree_iter, data):
        val = model[tree_iter][2]
        out = '' if val == 0 else '%1.2fH' % (val/3600)
        cell.set_property("text", out)
    
    def spent_render(self, col, cell, model, tree_iter, data):
        val = model[tree_iter][3]
        out = '' if val == 0 else '%1.2fH' % (val/3600)
        cell.set_property("text", out)
    
    def create_view_columns(self):
        priority = Gtk.CellRendererText(editable=True, foreground="#999")
        priority.connect("edited", self.commit_priority)
        col_priority = Gtk.TreeViewColumn("!", priority, text=0, foreground_set=12)
        col_priority.set_sort_column_id(0)
        self.task_view.append_column(col_priority)
        
        pct = Gtk.CellRendererProgress()
        col_pct = Gtk.TreeViewColumn("%", pct, value=1, visible=16)
        col_pct.set_sort_column_id(1)
        self.task_view.append_column(col_pct)
        
        est = Gtk.CellRendererText(foreground="#999", editable=True)
        est.connect("edited", self.commit_est)
        est.connect("editing-started", self.est_edit_start)
        col_est = Gtk.TreeViewColumn("Est", est, foreground_set=12)
        col_est.set_sort_column_id(2)
        col_est.set_cell_data_func(est, self.est_render)
        self.task_view.append_column(col_est)
        
        spent = Gtk.CellRendererText(foreground="#999", editable=True)
        spent.connect("edited", self.commit_spent)
        spent.connect("editing-started", self.spent_edit_start)
        col_spent = Gtk.TreeViewColumn("Spent", spent, foreground_set=12)
        col_spent.set_sort_column_id(3)
        col_spent.set_cell_data_func(spent, self.spent_render)
        self.task_view.append_column(col_spent)
        
        tracking = Gtk.CellRendererText(foreground="#b00", text=u"\u231A")
        col_tracking = Gtk.TreeViewColumn(u"\u231A", tracking, visible=17)
        self.task_view.append_column(col_tracking)
        
        due = Gtk.CellRendererText(editable=True, foreground="#999")
        due.connect("edited", self.commit_due)
        due.connect("editing-started", self.due_edit_start)
        col_due = Gtk.TreeViewColumn("Due", due, foreground_set=12)
        col_due.set_sort_column_id(8)
        col_due.set_cell_data_func(due, self.due_render)
        self.task_view.append_column(col_due)
        
        completed = Gtk.CellRendererText(editable=True, foreground="#999")
        completed.connect("edited", self.commit_complete)
        completed.connect("editing-started", self.complete_edit_start)
        col_completed = Gtk.TreeViewColumn("Completed", completed, foreground_set=12, visible=12)
        col_completed.set_sort_column_id(7)
        col_completed.set_cell_data_func(completed, self.completed_render)
        self.task_view.append_column(col_completed)
        
        assigner = Gtk.CellRendererCombo(model=self.assigners, has_entry=True, editable=True, foreground="#999", text_column=0)
        assigner.connect("edited", self.commit_assigner)
        col_assigner = Gtk.TreeViewColumn("From", assigner, text=9, foreground_set=12)
        col_assigner.set_sort_column_id(9)
        self.task_view.append_column(col_assigner)
        
        assignee = Gtk.CellRendererCombo(model=self.assignees, has_entry=True, editable=True, foreground="#999", text_column=0)
        assignee.connect("edited", self.commit_assignee)
        col_assignee = Gtk.TreeViewColumn("To", assignee, text=10, foreground_set=12)
        col_assignee.set_sort_column_id(10)
        self.task_view.append_column(col_assignee)
        
        status = Gtk.CellRendererCombo(model=self.statii, has_entry=True, editable=True, foreground="#999", text_column=0)
        status.connect("edited", self.commit_status)
        col_stats = Gtk.TreeViewColumn("Status", status, text=11, foreground_set=12)
        col_stats.set_sort_column_id(11)
        self.task_view.append_column(col_stats)
        
        done = Gtk.CellRendererToggle(activatable=True, radio=False)
        done.connect("toggled", self.commit_done)
        col_done = Gtk.TreeViewColumn(u"\u2713", done, active=12)
        col_done.set_sort_column_id(12)
        self.task_view.append_column(col_done)
        
        self.title_cell = Gtk.CellRendererText(editable=True, ellipsize=Pango.EllipsizeMode.NONE, foreground="#999")
        self.title_cell.connect("edited", self.commit_title)
        self.title_cell.connect("editing-started", self.title_edit_start)
        self.title_cell.connect("editing-canceled", self.commit_title, None, None, True)
        note = Gtk.CellRendererText(editable=False, ellipsize=Pango.EllipsizeMode.MIDDLE, foreground="#999")
        self.col_title = Gtk.TreeViewColumn("Title")
        self.col_title.pack_start(self.title_cell, True)
        self.col_title.pack_start(note, False)
        self.col_title.add_attribute(self.title_cell, "text", 13)
        self.col_title.add_attribute(self.title_cell, "foreground-set", 12)
        self.col_title.add_attribute(self.title_cell, "strikethrough", 12)
        self.col_title.set_cell_data_func(note, self.note_render)
        self.col_title.add_attribute(note, "strikethrough", 12)
        self.col_title.set_sort_column_id(13)
        self.task_view.append_column(self.col_title)
    
    def create_top_actions(self, action_group):
        action_group.add_actions([
            ("new_file", Gtk.STOCK_NEW, None, "", None, self.new_file),
            ("open_file", Gtk.STOCK_OPEN, None, None, "Open file", self.open_file),
            ("save_file", Gtk.STOCK_SAVE, None, None, "Save file", self.save_file),
            ("saveas_file", Gtk.STOCK_SAVE_AS, None, None, None, self.save_file_as),
            ("quit", Gtk.STOCK_QUIT, None, None, None, self.destroy),
            ("help_about", Gtk.STOCK_ABOUT, None, None, None, self.show_about),
            ("prefs", Gtk.STOCK_PREFERENCES, None, None, None, self.set_prefs),
            ("FileMenu", None, "_File"),
            ("EditMenu", None, "_Edit"),
            ("TaskMenu", None, "_Task"),
            ("ViewMenu", None, "_View"),
            ("HelpMenu", None, "_Help")
        ])
        recent_files = Gtk.RecentAction("recents", "_Recent Files", "Open a recently-used file", None)
        recent_files.set_properties(icon_name="document-open-recent", local_only=True, sort_type=Gtk.RecentSortType.MRU, show_not_found=False)
        htdl_filter = Gtk.RecentFilter()
        htdl_filter.add_pattern("*.htdl")
        htdl_filter.set_name("HiToDo Files (*.htdl)")
        recent_files.add_filter(htdl_filter)
        recent_files.connect("item-activated", self.open_recent)
        action_group.add_action(recent_files)
        
        
    def create_task_actions(self, action_group):
        action_group.add_actions([
            ("task_new", Gtk.STOCK_ADD, "_New Task", "<Primary>N", "New task", self.add_task),
            ("task_newsub", Gtk.STOCK_INDENT, "New S_ubtask", "<Primary><Shift>N", "New subtask", self.add_subtask),
            ("task_del", Gtk.STOCK_REMOVE, None, None, "Delete task", self.del_current_task),
            ("task_cut", Gtk.STOCK_CUT, None, None, "Cut task", self.skip),
            ("task_copy", Gtk.STOCK_COPY, None, None, "Copy task", self.skip),
            ("task_paste", Gtk.STOCK_PASTE, None, None, "Paste task", self.skip),
            ("task_paste_into", None, "Paste as _Child", "<Primary><Shift>V", "Paste as child", self.skip),
            ("undo", Gtk.STOCK_UNDO, None, "<Primary>Z", "Undo", self.skip),
            ("redo", Gtk.STOCK_REDO, None, "<Primary><Shift>Z", "Redo", self.skip),
            ("sel_all", Gtk.STOCK_SELECT_ALL, None, "<Primary>A", None, self.select_all),
            ("sel_inv", None, "_Invert Selection", None, None, self.select_inv),
            ("sel_none", None, "Select _None", "<Primary><Shift>A", None, self.select_none),
            ("expand_all", None, "_Expand All", None, "Expand all tasks", self.expand_all),
            ("collapse_all", None, "_Collapse All", None, "Collapse all tasks", self.collapse_all)
        ])
        self.track_action = Gtk.ToggleAction("track_spent", "Track", "Track time worked toward this task", None)
        self.track_action.set_properties(icon_name="appointment-soon")
        self.track_action.connect("activate", self.track_spent)
        action_group.add_action(self.track_action)
    
    def create_ui_manager(self):
        uimanager = Gtk.UIManager()

        # Throws exception if something went wrong
        uimanager.add_ui_from_string(UI_XML)
        
        # Add the accelerator group to the toplevel window
        accelgroup = uimanager.get_accel_group()
        self.add_accel_group(accelgroup)
        return uimanager
    
    def destroy(self, widget):
        if not self.confirm_discard(): return
        Gtk.main_quit()

def main():
    Gtk.main()
    return

def is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        return False

# If the program is run directly or passed as an argument to the python
# interpreter then create a Picker instance and show it
if __name__ == "__main__":
    htd = HiToDo()
    main()
