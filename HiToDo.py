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
from gi.repository import Gtk, Gdk, Pango, Gio
from datetime import datetime, timedelta
from os import linesep
from os.path import basename, dirname, splitext
from urlparse import urlparse
from urllib import unquote
from dateutil.parser import parse as dateparse
from math import floor
import xml.etree.ElementTree as et
import operator
from cgi import escape

import testing
import dialogs
import file_parsers
import undobuffer

UI_XML = """
<ui>
    <menubar name='MenuBar'>
        <menu action='FileMenu'>
            <menuitem action="new_file" />
            <menuitem action="open_file" />
            <menuitem action="recents" />
            <separator />
            <menuitem action="save_file" />
            <menuitem action="saveas_file" />
            <menuitem action="save_copy" />
            <separator />
            <menuitem action="doc_props" />
            <separator />
            <menuitem action='close' />
            <menuitem action='quit' />
        </menu>
        <menu action='EditMenu'>
            <menuitem action='undo' />
            <menuitem action='redo' />
            <separator />
            <menuitem action='task_cut' />
            <menuitem action='task_copy' />
            <menuitem action='task_paste' />
            <menuitem action='task_paste_into' />
            <separator />
            <menuitem action='sel_all' />
            <menuitem action='sel_none' />
            <menuitem action='sel_inv' />
            <separator />
            <menu action='LabelMenu'>
                <menuitem action='edit_assigners' />
                <menuitem action='edit_assignees' />
                <menuitem action='edit_statii' />
            </menu>
            <menuitem action='prefs' />
        </menu>
        <menu action="ViewMenu">
            <menuitem action='show_toolbar' />
            <separator />
            <menuitem action='expand_all' />
            <menuitem action='collapse_all' />
        </menu>
        <menu action='TaskMenu'>
            <menuitem action='task_new' />
            <menuitem action='task_newsub' />
            <menuitem action='task_del' />
            <separator />
            <menuitem action='track_spent' />
            <separator />
            <menuitem action='archive_done' />
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
    <popup name="TaskPopup">
        <menuitem action="task_new" />
        <menuitem action="task_newsub" />
        <menuitem action='task_del' />
        <separator />
        <menuitem action='task_cut' />
        <menuitem action='task_copy' />
        <menuitem action='task_paste' />
        <menuitem action='task_paste_into' />
        <separator />
        <menuitem action='track_spent' />
    </popup>
</ui>
"""

CSS = '''
'''

# Define the gui and its actions.
class HiToDo(Gtk.Window):
    program_version = "0.9.3"

    def skip(self, widget=None):
        '''Placeholder function for unimplemented UI actions.'''
        pass

    def track_focus(self, widget, event=None):
        '''Sets internal reference to the widget we consider to have focus. This
        may not match with what *actually* has focus in the WM. The reference is
        used to choose which action to take on undo, redo, cut, copy, paste, etc.'''
        self.focus = widget

    def add_task(self, widget=None, parent_iter=None):
        '''Adds a new task to the task list, underneath 'parent_iter'. When
        'parent_iter' is None, it's inserted at the top level.

        If a task other than the parent is selected, we append the new task as
        its sibling.

        The new task is populated with data from 'self.defaults' and its parent,
        if set. Its title field then receives focus for editing.'''
        self.commit_all()

        #we can inherit some things if we're a new child
        if parent_iter is None and self.parent is not None:
            parent_iter = self.parent
            parent = self.tasklist[parent_iter]
        elif parent_iter is not None:
            parent = self.tasklist[parent_iter]
        else:
            parent = self.defaults

        row_data = [
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
        ]


        if self.seliter is not None and parent_iter is not self.seliter:
            new_row_iter = self.tasklist.insert_after(None, self.seliter, row_data)
        else:
            new_row_iter = self.tasklist.prepend(parent_iter, row_data)

        path = self.tasklist.get_path(new_row_iter)
        spath = path.to_string()

        #ensure parent is not Done and recalc its pct complete
        self.force_parent_not_done(spath)
        self.calc_parent_pct(spath)

        #push add action to undo list
        if parent_iter is not None:
            ppath = self.tasklist.get_path(parent_iter)
        else:
            ppath = None
        selpath = self.sellist[0] if self.seliter is not None else None
        self.__push_undoable("add", (spath, ppath, selpath))

        #select new row and immediately edit title field
        self.tasklist_filter.convert_child_iter_to_iter(new_row_iter)
        self.selection.select_iter(new_row_iter)
        if parent_iter is not None:
            self.task_view.expand_to_path(path)
        self.task_view.set_cursor_on_cell(path, self.col_title, self.title_cell, True)

    def add_subtask(self, widget=None):
        '''Helper function to add a new task beneath the selected task. See add_task.'''
        self.add_task(parent_iter = self.seliter)

    def commit_all(self):
        '''Commit all possibly-in-progress edits.'''
        self.commit_title()
        self.commit_notes()
        self.commit_date(field = 8)
        self.commit_priority()

    def commit_est(self, widget=None, path=None, new_est=None):
        '''Save user-entered time estimate. Value of 'new_est' is expected to be
        in hours, so it's converted to seconds before saving.

        Once saved, we recurse up our chain of parents, adding our value to
        theirs.'''
        if path is None: return
        if type(path) is str and path == "": return
        if not is_number(new_est): return

        old_est = self.tasklist[path][2] #store for later
        new_est = float(new_est)
        out = floor(new_est * 3600) #convert to seconds
        self.tasklist[path][2] = int(out) #save

        #now we need to adjust our parent's total
        parts = str(path).rpartition(':')
        parent_path = parts[0] #find parent path
        if parent_path != "":
            parent_est = self.tasklist[parent_path][2]
            pest = (parent_est + out - old_est)/3600 #calculate new parent estimate
            self.commit_est(path=parent_path, new_est=pest) #commit up the chain

        # Push undoable only on user click, not internal call. Very important since we recurse.
        if widget is not None:
            self.__push_undoable("est", (path, old_est, int(out)))

    def commit_est_iter(self, treeiter=None, new_est=0):
        '''Helper function to save a time estimate (in hours) when all we have
        is a treeiter. See 'commit_est'.'''
        if treeiter is None: return
        path = self.tasklist.get_path(treeiter).to_string()
        self.commit_est(path=path, new_est=new_est)

    def est_edit_start(self, renderer, editor, path):
        '''Set up time estimate editing field. Converts saved seconds into
        hours, and adds an icon for recalculating. See 'derive_est'.'''
        val = self.tasklist[path][2]
        self.track_focus(widget = editor)
        editor.set_text(str(val/3600)) #don't display the H suffix during editing
        editor.set_icon_from_stock(Gtk.EntryIconPosition.SECONDARY, Gtk.STOCK_REFRESH)
        editor.set_icon_tooltip_text(Gtk.EntryIconPosition.SECONDARY, "Recalculate from children")
        editor.connect("icon-press", self.derive_est, path)

    def derive_est(self, entry=None, pos=None, event=None, path=None):
        '''Recalculate our time estimate based on our children's estimates. We
        assume our children are already calculated, so we only have to peek at
        our top-level children's time estimates.'''
        total_est = 0
        treeiter = self.tasklist.get_iter(path)
        #no children means our est is 0 and we can stop
        if self.tasklist.iter_has_child(treeiter):
            #loop through our children and add their est total to ours
            child_iter = self.tasklist.iter_children(treeiter)
            while child_iter is not None:
                total_est += self.tasklist[child_iter][2]
                child_iter = self.tasklist.iter_next(child_iter)
        old_est = self.tasklist[path][2]
        self.commit_est(path = path, new_est = total_est/3600) #save it

        #push undoable. We have to push our own because commit_est only pushes when called from the UI.
        self.__push_undoable("est", (path, old_est, total_est))

    def commit_spent(self, widget=None, path=None, new_spent=None):
        '''Save user-entered time spent. Value of 'new_spent' is expected to be
        in hours, so it's converted to seconds before saving.

        Once saved, we recurse up our chain of parents, adding our value to
        theirs.'''
        if path is None: return
        if type(path) is str and path == "": return

        if not is_number(new_spent): return
        old_spent = self.tasklist[path][3]
        new_spent = float(new_spent)
        out = floor(new_spent * 3600)
        self.tasklist[path][3] = int(out)

        parts = str(path).rpartition(':')
        parent_path = parts[0]
        if parent_path != "":
            parent_spent = self.tasklist[parent_path][3]
            pspent = (parent_spent + out - old_spent)/3600
            self.commit_spent(path=parent_path, new_spent=pspent)

        #push undoable only on user click
        if widget is not None:
            self.__push_undoable("spent", (path, old_spent, int(out)))

    def commit_spent_iter(self, treeiter=None, new_spent=0):
        '''Helper function to save time spent (in hours) when all we have is a
        treeiter. See 'commit_spent'.'''
        if treeiter is None: return
        path = self.tasklist.get_path(treeiter).to_string()
        self.commit_spent(path=path, new_spent=new_spent)

    def spent_edit_start(self, renderer, editor, path):
        '''Set up time spent editing field. Converts saved seconds into
        hours, and adds an icon for recalculating. See 'derive_spent'.'''
        val = self.tasklist[path][3]
        self.track_focus(widget = editor)
        editor.set_text(str(val/3600)) #don't display the H suffix during editing
        editor.set_icon_from_stock(Gtk.EntryIconPosition.SECONDARY, Gtk.STOCK_REFRESH)
        editor.set_icon_tooltip_text(Gtk.EntryIconPosition.SECONDARY, "Recalculate from children")
        editor.connect("icon-press", self.derive_spent, path)

    def derive_spent(self, entry=None, pos=None, event=None, path=None):
        '''Recalculate our time spent based on our children's estimates. We
        assume our children are already calculated, so we only have to peek at
        our top-level children's time spent.'''
        total_spent = 0
        treeiter = self.tasklist.get_iter(path)
        if self.tasklist.iter_has_child(treeiter):
            n_children = self.tasklist.iter_n_children(treeiter)
            child_iter = self.tasklist.iter_children(treeiter)
            while child_iter is not None:
                total_spent += self.tasklist[child_iter][3]
                child_iter = self.tasklist.iter_next(child_iter)
        old_spent = self.tasklist[path][3]
        self.commit_spent(path=path, new_spent = total_spent) #save it

        #push undoable
        self.__push_undoable("spent", (path, old_spent, total_spent))

    def track_spent(self, action=None, data=None):
        '''Handles time spent tracking. Only really useful when called from the
        UI. When tracking is toggled on, a timestamp is saved. When tracking is
        toggled off, a new timestamp is fetched and the difference applied to
        that row's time spent total.

        Only one row (task) can be tracked at a time. We store a treeiter
        pointing to that row as well as set the row's tracked flag (field 17).'''
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
            path = self.tasklist.get_path(self.tracking).to_string()
            nspent = (self.tasklist[self.tracking][3] + secs) / 3600
            self.commit_spent(path=path, new_spent = nspent)
            self.tasklist[self.tracking][17] = False
            self.make_dirty()

            self.tracking = None
            self.timer_start = None
            action.set_tooltip("Start tracking time toward current task")

    def commit_done(self, renderer=None, path=None, new_done=None):
        '''Toggles a task's 'done' flag (field 12) and handles tracking and pct
        propagation. Note that field 16 is the 'anti-done' flag and always set
        to the opposite value of field 12.

        When transition to done state, pct is set to 100, children are forced to
        'done' state (see force_children_done), the 'completed' timestamp is
        set, and tracking is toggled off if applicable.

        When transition to the not-done state, our parent is set to not-done
        (see force_parent_not_done), our parent's pct is recalculated (see
        calc_parent_pct), and our own pct is recalculated (see calc_pct).'''
        if path is None: return

        done = not new_done if new_done is not None else self.tasklist[path][12]

        if not done:
            #we're transitioning from not-done to done
            self.tasklist[path][1] = 100 #no need to calculate; we're 100% complete

            self.force_children_done(path)
            self.tasklist[path][7] = datetime.now()
            if self.tasklist[path][17]:
                self.track_action.set_active(False)
        else:
            #we're transitioning from done to not-done
            self.force_parent_not_done(path)
            self.calc_parent_pct(path)
            self.calc_pct(path)

        self.tasklist[path][12] = not done
        self.tasklist[path][16] = done

        #add undo action only on user click
        if renderer is not None:
            self.__push_undoable("done", (path, done, not done))

        #recalculate our parent's pct complete, if we have one
        self.calc_parent_pct(path)

    def force_children_done(self, path):
        '''Finds the first child of 'path' and uses a private function to mark
        it and all of its peers done. See __force_peers_done().'''
        treeiter = self.tasklist.get_iter(path)
        child_iter = self.tasklist.iter_children(treeiter)
        self.__force_peers_done(child_iter)

    def __force_peers_done(self, treeiter):
        '''Marks all tasks on this level as done, and recurses to every task's
        children.

        See commit_done() for a description of what happens when transition to
        the done state.'''
        while treeiter != None:
            #handle tracking
            if self.tasklist[treeiter][17]:
                self.track_action.set_active(False)
            #set pct complete
            self.tasklist[treeiter][1] = 100
            #set complete timestamp if not already present
            if self.tasklist[treeiter][7] == "":
                self.tasklist[treeiter][7] = datetime.now()
            #set done and anti-done flags
            self.tasklist[treeiter][12] = True
            self.tasklist[treeiter][16] = False
            #recurse if necessary
            if self.tasklist.iter_has_child(treeiter):
                child_iter = self.tasklist.iter_children(treeiter)
                self.__force_peers_done(child_iter)
            #iterate to next sibling
            treeiter = self.tasklist.iter_next(treeiter)

    def force_parent_not_done(self, path):
        '''Iterates all levels of path, marking the first row of each level
        not done.'''
        parts = path.split(':')
        oldpath = ''
        for parent_path in parts:
            newpath = oldpath + parent_path
            parent_iter = self.tasklist.get_iter(newpath)
            self.tasklist[parent_iter][12] = False
            self.tasklist[parent_iter][16] = True
            oldpath = newpath + ':'

    def calc_parent_pct(self, path):
        '''Gets the parent path of 'path' and uses a private function to
        calculate the parent's pct complete. See __do_pct().'''
        parts = path.partition(':')
        parent_path = parts[0]
        if parent_path == path: return

        parent_iter = self.tasklist.get_iter(parent_path)
        self.__do_pct(parent_iter)

    def calc_pct(self, path):
        '''Uses a private function to calculate the pct complete of the row at
        'path'. When the row has no children, its pct complete is set to zero
        as a shortcut. See __do_pct().

        This function does not handle the case where the row is marked done.'''
        treeiter = self.tasklist.get_iter(path)
        if self.tasklist.iter_n_children(treeiter) == 0:
            self.tasklist[treeiter][1] = 0
            return

        self.__do_pct(treeiter)

    def __do_pct(self, treeiter):
        '''Calculates the pct complete of the row at 'treeiter' from the number
        of children marked done. Children with children of their own (branches)
        are ignored.'''
        n_children = 0 #This is not the liststore's child count. It omits children who have children of their own.
        n_done = 0 #Also omits children who have children.
        child_iter = self.tasklist.iter_children(treeiter)
        while child_iter is not None:
            if self.tasklist.iter_n_children(child_iter):
                #for branches, get their pct and grab child numbers for our own
                nc, nd = self.__do_pct(child_iter)
                n_children += nc
                n_done += nd
            else:
                #for leaves, inc counters as appropriate
                n_children += 1
                n_done += self.tasklist[child_iter][12]
            child_iter = self.tasklist.iter_next(child_iter)

        self.tasklist[treeiter][1] = int((n_done / n_children) * 100)
        return n_children, n_done

    def commit_priority(self, widget=None, path=None, new_priority=None):
        '''Sets the priority for 'path' to the value of 'new_priority'.'''
        if path is None: return

        old_val = self.tasklist[path][0]

        #priorities have to be integers
        if new_priority.isdigit():
            self.tasklist[path][0] = int(new_priority)
            self.__push_undoable("change", (path, 0, old_val, int(new_priority)))

    def commit_date(self, widget=None, path=None, new_date=None, field=None):
        '''Sets the value of a date field (due, complete, act begin, est begin,
        est complete) to the value of 'new_date'. The dateparse module is used to
        convert the string input into a datetime object.'''
        if path is None: return

        old_val = self.tasklist[path][field]

        if new_date.lower() == "tomorrow":
            #manually handle "tomorrow" keyword, along with others in the future
            delta = timedelta(days=1)
            dt = datetime.today() + delta
        elif new_date == "":
            dt = ""
        else:
            try:
                dt = dateparse(new_date, fuzzy=True)
            except ValueError:
                dt = ""

        self.tasklist[path][field] = dt
        self.__push_undoable("change", (path, field, old_val, dt))

    def commit_status(self, widget=None, path=None, new_status=None):
        '''Set the status string of 'path' to the value of 'new_status'. That
        value is also added to our internal list and liststore of status
        strings, if not already present.'''
        if path is None: return

        #add the new status to our lists if necessary
        if new_status != '' and new_status not in self.statii_list:
            self.statii.append([new_status]) #liststore
            self.statii_list.append(new_status) #normal list
        old_status = self.tasklist[path][11]

        self.tasklist[path][11] = new_status
        self.track_focus(widget = self.task_view)
        self.__push_undoable("change", (path, 11, old_status, new_status))

    def commit_assigner(self, widget=None, path=None, new_assigner=None):
        '''Set the status string of 'path' to the value of 'new_assigner'. That
        value is also added to our internal list and liststore of assigner
        strings, if not already present.'''
        if path is None: return

        if new_assigner != '' and new_assigner not in self.assigners_list:
            self.assigners.append([new_assigner])
            self.assigners_list.append(new_assigner)
        old_assigner = self.tasklist[path][9]

        self.tasklist[path][9] = new_assigner
        self.track_focus(widget = self.task_view)
        self.__push_undoable("change", (path, 9, old_assigner, new_assigner))

    def commit_assignee(self, widget=None, path=None, new_assignee=None):
        '''Set the status string of 'path' to the value of 'new_assignee'. That
        value is also added to our internal list and liststore of assignee
        strings, if not already present.'''
        if path is None: return

        if new_assignee != '' and new_assignee not in self.assignees_list:
            self.assignees.append([new_assignee])
            self.assignees_list.append(new_assignee)
        old_assignee = self.tasklist[path][10]

        self.tasklist[path][10] = new_assignee
        self.track_focus(widget = self.task_view)
        self.__push_undoable("change", (path, 10, old_assignee, new_assignee))

    def commit_notes(self, widget=None, data=None):
        '''Save the user-entered notes text to the notes field.'''
        if self.seliter is None: return
        if self.notes_view.has_focus():
            self.task_view.grab_focus()
        else:
            return #just in case we were called when the notes view was not actually being used

        start = self.notes_buff.get_iter_at_offset(0)
        end = self.notes_buff.get_iter_at_offset(-1)
        text = self.notes_buff.get_text(start, end, False)

        path = self.tasklist.get_path(self.seliter)
        oldtext = self.tasklist[self.seliter][14]

        self.tasklist[self.seliter][14] = text
        self.__push_undoable("notes", (path, oldtext, text))

    def commit_title(self, widget=None, path=None, new_title=None, write=True):
        '''Save the user-entered title.

        When the entry is blank, we simply revert to the previous title. If the
        title is made blank on a new task, however, the task is deleted instead,
        as there is no previous title to use.

        The 'write' flag is used when we want to evaluate 'new_title' against
        the old title, but don't want to change anything if it doesn't revert.'''
        if path is None:
            if self.title_editor is None: return
            #if we have no path, but there is an active title editing field, we can use that instead
            path = self.title_edit_path #grab the stored path
            new_title = self.title_editor.get_text() #get user text
            self.title_editor.disconnect(self.title_key_press_catcher) #kill off the key catcher
        self.title_editor = None #clear this once it's no longer necessary

        old_title = self.tasklist[path][13]

        # If the new title is blank...
        if new_title is None or new_title == '':
            if old_title == '':
                # and the task is new, just delete it.
                self.del_task(path)
                self.undobuffer.pop()
            return # cancel the edit.

        #finally, set the new title if allowed
        if write is True:
            self.tasklist[path][13] = new_title
            self.__push_undoable("change", (path, 13, old_title, new_title))

    def title_edit_start(self, renderer, editor, path):
        '''Set up the title editor widget and store its edit path. We also set
        the internal focus to the editor (see track_focus()) and attach a key
        listener. See title_keys_dn().'''
        editor.set_text(self.tasklist[path][13])
        self.title_edit_path = path
        self.title_editor = editor
        self.track_focus(widget=editor)
        self.title_key_press_catcher = editor.connect("key-press-event", self.title_keys_dn)

    def combo_edit_start(self, renderer, editor, path):
        '''Sets internal focus to the combot widget. See track_focus().'''
        self.track_focus(widget=editor.get_child())

    def priority_edit_start(self, renderer, editor, path):
        '''Sets internal focus to the priority widget. See track_focus().'''
        self.track_focus(widget = editor)

    def date_edit_start(self, renderer, editor, path):
        '''Sets up the date editing widget and sets internal focus to it. These
        have an icon which pops up a reference calendar. See track_focus().'''
        self.track_focus(widget = editor)
        editor.set_icon_from_icon_name(Gtk.EntryIconPosition.SECONDARY, "appointment-new")
        editor.connect("icon-press", self.date_pick)

    def date_pick(self, entry, pos, event, data=None):
        '''Displays a calendar popoup for date entry widgets. See date_edit_start().'''
        #TODO add calendar picker popup
        pass

    def del_current_task(self, widget=None):
        '''Removes every selected row from the task list. These are stored in
        self.sellist (see 'task_selected()').

        Spent time tracking is ended as needed. Parent pct complete, time spent,
        and est are recaulculated.'''
        if self.sellist is None: return
        refs = []
        #first we get references to each row
        for path in self.sellist:
            path = str(path)
            #stop tracking if needed
            if self.tasklist[path][17]:
                self.track_action.set_active(False)
            refs.append((self.tasklist.get_iter(path), path, path.count(':')))

        refs.sort(key=operator.itemgetter(2))

        #push action tuple to undo buffer
        row_data = []
        self.__do_copy_real(self.sellist, row_data)
        path = self.tasklist.get_path(refs[0][0])
        path.prev()
        spath = path.to_string()
        path.up()
        ppath = path.to_string()
        self.__push_undoable("del", (ppath, spath, row_data)),

        #now we can remove them without invalidating paths
        for ref, path, pathlen in refs:
            self.commit_spent_iter(ref, new_spent=0)
            self.commit_est(ref, new_est=0)

            self.calc_parent_pct(str(path))
            self.tasklist.remove(ref)

        self.task_selected(self.selection)

    def del_task(self, path):
        '''Deletes the row at 'path'. Ceases tracking and recalculates parent
        time spent, est, and pct complete.'''
        #stop tracking if needed
        if self.tasklist[path][17]:
            self.track_action.set_active(False)
        treeiter = self.tasklist.get_iter(path)

        self.commit_spent(path=path, new_spent=0)
        self.commit_est(path=path, new_est=0)
        self.tasklist.remove(treeiter)
        self.calc_parent_pct(str(path))

    def del_task_iter(self, treeiter):
        '''Deletes the row at 'treeiter'. Just a wrapper for del_task().'''
        path = self.tasklist.get_path(treeiter)
        self.del_task(path)

    def task_selected(self, widget):
        '''Stores references to the task(s) selected by the user. Also sets the
        correct buffer for notes editing and enables/disables row editing
        controls (cut, copy, paste, etc.) as needed.'''
        self.selcount = widget.count_selected_rows()
        self.sellist = widget.get_selected_rows()[1]

        #if there's anything in the list, commit our changes
        self.commit_all()

        #set internal selection vars
        if self.selcount == 1:
            self.seliter = self.tasklist.get_iter(self.sellist[0])
            self.parent = self.tasklist.iter_parent(self.seliter)
            self.notes_buff.set_text(self.tasklist[self.seliter][14])

            #enable controls which can act on a singleton
            self.task_cut.set_sensitive(True)
            self.task_copy.set_sensitive(True)
            self.task_del.set_sensitive(True)
            self.task_paste.set_sensitive(True)
            self.task_paste_into.set_sensitive(True)
            self.notes_view.set_sensitive(True)
        else:
            self.seliter = None
            self.notes_buff.set_text('')

            #enable controls which can act on a group
            self.task_cut.set_sensitive(True)
            self.task_copy.set_sensitive(True)
            self.task_del.set_sensitive(True)

            #disable controls which require a single selection
            self.task_paste.set_sensitive(False)
            self.task_paste_into.set_sensitive(False)
            self.notes_view.set_sensitive(False)

        self.notes_buff.clear_undo()

    def select_all(self, widget=None):
        '''Handles Select All events based on the internal focus pointer. If
        focus is on the task list, controls are enabled/disabled as required.
        Currently supports the task view, notes view, and title editor.'''
        if self.focus == self.task_view:
            self.selection.select_all()

            #enable controls which can act on a group
            self.task_cut.set_sensitive(True)
            self.task_copy.set_sensitive(True)
            self.task_del.set_sensitive(True)

            #disable controls which require a single selection
            self.task_paste.set_sensitive(False)
            self.task_paste_into.set_sensitive(False)
            self.notes_view.set_sensitive(False)
        elif self.focus == self.notes_view:
            self.focus.emit('select-all', True)
        elif self.title_editor is not None and self.focus == self.title_editor:
            self.focus.select_region(0, -1)

    def select_none(self, widget=None):
        '''Handles Select None events based on the internal focus pointer. If
        focus is on the task list, controls are enabled/disabled as required.
        Currently supports the task view, notes view, and title editor.'''
        if self.focus == self.task_view:
            self.selection.unselect_all()

            #disable controls which require a selection
            self.task_cut.set_sensitive(False)
            self.task_copy.set_sensitive(False)
            self.task_paste.set_sensitive(False)
            self.task_paste_into.set_sensitive(False)
            self.notes_view.set_sensitive(False)
            self.task_del.set_sensitive(False)
        elif self.focus == self.notes_view:
            self.focus.emit('select-all', False)
        elif self.title_editor is not None and self.focus == self.title_editor:
            self.focus.select_region(0,0)

    def select_inv(self, widget=None):
        '''Inverts task selection: all selected tasks are unselected, and all
        previously unselected tasks are selected. Uses select all or select none where possible, and otherwise calls a private function to invert recursively (see __invert_tasklist_selection()).'''
        if self.focus != self.task_view: return

        if self.selcount == 0:
            self.select_all()
        elif self.selcount == len(self.tasklist):
            self.select_none()
        else:
            #disconnect selection changed handler
            self.selection.disconnect(self.sel_changed_handler)
            #invert recursively
            self.__invert_tasklist_selection(self.tasklist_filter.get_iter_first())
            #reconnect selection changed handler
            self.sel_changed_handler = self.selection.connect("changed", self.task_selected)
            self.task_selected(self.selection)

    def __invert_tasklist_selection(self, treeiter):
        '''Recursively switches each row's selected status, inverting the user's selection.'''
        while treeiter != None:
            #swap selection state on iter
            if self.selection.iter_is_selected(treeiter):
                self.selection.unselect_iter(treeiter)
            else:
                self.selection.select_iter(treeiter)
            #probe children
            if self.tasklist_filter.iter_has_child(treeiter):
                child_iter = self.tasklist_filter.iter_children(treeiter)
                self.__invert_tasklist_selection(child_iter)
            treeiter = self.tasklist_filter.iter_next(treeiter)

    def expand_all(self, widget=None):
        '''Expands all tasks.'''
        self.task_view.expand_all()

    def collapse_all(self, widget=None):
        '''Collapses all tasks.'''
        self.task_view.collapse_all()

    def new_file(self, widget=None):
        '''Creates a new file by clearing the treestore, undo/redo buffer,
        visible columns, assigners, assignees, statii, file name, etc.

        Right now, it replaces the current file without question, but in the
        future will honor a settings variable to possibly open a new window or
        tab instead.'''
        if not self.confirm_discard(): return

        self.tasklist.clear()

        #clear undo and redo buffers
        del self.undobuffer[:]
        del self.redobuffer[:]

        #reset to default columns
        self.cols_visible = self.cols_default[:]
        self.display_columns()

        #reset to default assigners, assignees, and statii
        self.assigners_list = self.assigners_default[:]
        self.assignees_list = self.assignees_default[:]
        self.statii_list = self.statii_default[:]

        self.assigners.clear()
        self.assignees.clear()
        self.statii.clear()
        for n in self.assigners_list:
            self.assigners.append([n])
        for n in self.assignees_list:
            self.assignees.append([n])
        for n in self.statii_list:
            self.statii.append([n])

        self.file_name = ""
        self.file_dirty = False
        self.update_title()

    def open_file(self, widget=None):
        '''Prompts the user the choose a file to load. Uses __do_open() to read
        the file once it's known.'''
        if not self.confirm_discard(): return

        retcode = self.open_dlg.run()
        self.open_dlg.hide()
        if retcode != -3: return #cancel out if requested

        self.file_name = self.open_dlg.get_filename()
        self.file_filter = self.save_dlg.get_filter()
        self.__do_open()

    def open_recent(self, widget):
        '''Opens a file from the Recent Files widget. Saves file information and
        calls __do_open() for the real work.'''
        if not self.confirm_discard(): return

        uri = widget.get_current_uri()
        fpath = urlparse(uri).path
        self.file_name = unquote(fpath)
        self.file_filter = file_parsers.pick_filter(fpath)
        self.__do_open()

    def __open_last(self):
        '''Private function to open the most recent file on program start.'''
        retval = self.recent_files.get_uris()
        if retval == []: return
        if retval[0] == []: return
        uri = retval[0]
        fpath = urlparse(uri).path
        self.file_name = unquote(fpath)
        self.file_filter = file_parsers.pick_filter(fpath)
        self.__do_open()

    def __do_open(self):
        '''Private function which opens the file at self.file_name using the
        reader self.file_filter.

        First, self.file_filter processes the file and puts the file's data into
        a dict for loading. Save version is checked for compatability and then
        things are loaded into our internal vars.'''
        templist = copy_treemodel(self.tasklist)
        data = {
            'filename': self.file_name,
            'from_list': [],
            'to_list': [],
            'status_list': [],
            'task_store': templist,
            'cols': [],
            'geometry': ()
            #data also has save_version, our_version, expanded, and selected keys
        }
        self.file_filter.read_to_store(data)

        #check version compatability
        file_version = data['save_version']
        native_version = data['our_version']
        force_save = False
        if native_version < file_version:
            response = self.version_warn_dlg.run()
            if response == 2:
                data['filename'] = self.pick_savefile()
                force_save = True
            elif response == Gtk.ResponseType.CANCEL:
                return

            self.version_warn_dlg.hide()

        #load vars
        del self.cols_visible[:]

        self.file_name = data['filename']
        self.assigners_list = data['from_list']
        self.assignees_list = data['to_list']
        self.statii_list = data['status_list']
        #self.tasklist is handled later
        self.cols_visible = data['cols']
        rows_to_expand = data['expanded']
        selme = data['selected']

        #add rows
        #when adding lots of rows, we want to disable the display until we're done
        self.task_view.freeze_child_notify()
        self.task_view.set_model(None)
        self.tasklist.clear()
        #TODO clear filter
        #self.tasklist_filter.refilter()

        #now we can import the task list data from templist
        templist.foreach(append_row, self.tasklist)
        del templist

        #adjust for different column lists
        if len(self.cols_visible) <= len(self.cols):
            codes = []
            for code, flag in self.cols_visible:
                codes.append(code)
            former = 0
            for col in self.cols:
                try:
                    i = codes.index(col[0])
                except ValueError:
                    self.cols_visible.insert(former, (col[0], False))
                former += 1

        #iterate assigners, assignees, and statii to put names into respective liststores
        self.assigners.clear()
        self.assignees.clear()
        self.statii.clear()
        for n in self.assigners_list:
            self.assigners.append([n])
        for n in self.assignees_list:
            self.assignees.append([n])
        for n in self.statii_list:
            self.statii.append([n])

        #show requested columns
        self.display_columns()

        #set window geometry
        self.set_default_size(data['geometry'][1], data['geometry'][2])
        if data['geometry'][0]:
            self.maximize()
        else:
            self.unmaximize()
            self.resize(data['geometry'][1], data['geometry'][2])
        #this is still a little buggy, but it approximates the sidebar width fairly well
        self.notes_view.set_size_request(data['geometry'][3], -1)

        #reconnect model to view
        self.task_view.set_model(self.tasklist)

        #expand requested rows
        for pathstr in rows_to_expand:
            path = Gtk.TreePath.new_from_string(pathstr)
            self.task_view.expand_row(path, False)

        #select requested rows
        if selme != '' and selme is not None:
            try:
                treeiter = self.tasklist.get_iter(selme)
                self.tasklist_filter.convert_child_iter_to_iter(treeiter)
                self.selection.select_iter(treeiter)
            except ValueError:
                self.selection.unselect_all()

        #start sending signals again and take focus
        self.task_view.thaw_child_notify()
        self.task_view.grab_focus()

        #clear undo and redo buffers
        del self.undobuffer[:]
        del self.redobuffer[:]

        self.last_save = datetime.now()
        self.file_dirty = False
        self.update_title()

        # If we opened a file as a "copy", what we're really doing is a quick
        # file-open and file-save-as operation. This is the saving bit.
        if force_save:
            self.save_file()

    def pick_savefile(self):
        '''Prompts the user to pick a save location. The chosen extension is
        added automatically if the user left it out, and the resulting full path
        is returned.'''
        #set up starting name
        if self.file_name != "":
            self.save_dlg.set_filename(self.file_name)
        else:
            self.save_dlg.set_current_name("Untitled list.htdl")
        #show the dialog
        retcode = self.save_dlg.run()
        self.save_dlg.hide()
        if retcode != -3: return #cancel out if requested

        #get entered path+filename
        filename = self.save_dlg.get_filename()
        self.file_filter = self.save_dlg.get_filter()
        ext = splitext(filename)[1]
        if ext == '':
            #add extension if needed
            filename += self.file_filter.file_extension

        return filename

    def save_file_as(self, widget=None):
        '''Prompts user for a save location (see pick_savefile()) and then saves
        there using __do_save(). The location is preserved for future saves.'''
        self.file_name = self.pick_savefile()
        self.__do_save(self.file_name, self.tasklist)

    def save_file(self, widget=None):
        '''Saves the current file at its known location. If we don't have a
        location yet, the user is prompted to choose one.'''
        if self.file_name == "":
            self.save_file_as()
            return

        self.__do_save(self.file_name, self.tasklist)

    def save_copy(self, widget=None):
        '''Prompts the user to pick a save location then saves the current file
        there. However, the new location is then discarded and will not be used
        for future saves.'''
        filename = self.pick_savefile()
        self.__do_save(filename, self.tasklist)

    def __do_save(self, filename, tasklist, append=False, file_filter=None):
        '''Private function to save our data to the file at 'filename'. The data
        is bundled into a dict and all the writing is handled by a filter from
        file_parsers.py.'''
        if file_filter is None: file_filter = file_parsers.pick_filter(filename)

        if tasklist is self.tasklist and self.seliter is not None:
            selpath = tasklist.get_path(self.seliter).to_string()
        else:
            selpath = ''

        width, height = self.get_size()
        task_width = width - self.task_pane.get_position()
        data = {
            'filename': filename,
            'from_list': sorted(self.assigners_list),
            'to_list': sorted(self.assignees_list),
            'status_list': sorted(self.statii_list),
            'task_store': tasklist,
            'task_view': self.task_view,
            'selection': selpath,
            'cols': self.cols_visible,
            'geometry': (self.maximized, width, height, task_width)
        }
        file_filter.write(data, append)

        self.file_dirty = False
        self.update_title()
        self.last_save = datetime.now()

    def confirm_discard(self):
        '''Prompts the user about discarding unsaved changes. Returns True if
        the user wants to discard their changes, and False otherwise. Handles
        saving with save_file().'''
        if not self.file_dirty: return True

        #get the right unit
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

        #construct the time field
        diff_text = "%s %s" % (diff_num, diff_unit)
        if diff_num > 1: diff_text += "s"

        #make sure we have a file name of some sort
        fname = "Untitled List" if self.file_name == ""  else self.file_name

        dlg = dialogs.misc.htd_warn_discard(self, fname, diff_text)
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

    def make_dirty(self, path=None, it=None, data=None):
        '''Marks our data as dirty (unsaved) and changes the title to reflect
        this. See update_title().'''
        self.file_dirty = True
        self.update_title()

    def update_title(self):
        '''Updates the window's title to reflect the current file's name, path,
        and dirty state.'''
        if self.file_name != "":
            ttl = "%s (%s) - HiToDo" % (basename(self.file_name), dirname(self.file_name))
        else:
            ttl = "Untitled List - HiToDo"

        self.title = "*"+ttl if self.file_dirty else ttl

        self.set_title(self.title)

    def show_about(self, widget=None):
        '''Shows the About dialog.'''
        self.about_dlg.run()
        self.about_dlg.hide()

    def set_prefs(self, widget=None):
        self.prefs_dlg.show_all()

    def set_docprops(self, widget=None):
        '''Shows the Document Properties dialog. See move_col() and
        toggle_col_visible() for how column settings are manipulated.'''
        self.docprops_dlg.show_all()

    def do_cut(self, widget=None):
        '''Applies cut operation depending on current internal focus. For notes
        or title, the 'cut-clipboard' signal is emitted. For the task list, the
        selected rows are copied to internal storage and the clipboard, then
        deleted. See __do_copy_real().'''
        if self.focus == self.notes_view or (self.title_editor is not None and self.focus == self.title_editor):
            self.focus.emit('cut-clipboard')
        elif self.focus == self.task_view:
            if self.sellist is None: return
            row_texts = self.__do_copy_real(self.sellist, self.copied_rows)
            self.clipboard.set_text("\n".join(row_texts), -1)
            self.del_current_task() #this also pushes an undo action

    def do_copy(self, widget=None):
        '''Applies copy operation depending on current internal focus. For notes
        or title, the 'copy-clipboard' signal is emitted. For the task list, the
        selected rows are copied to internal storage and the clipboard. See
        __do_copy_real().'''
        if self.focus == self.notes_view or (self.title_editor is not None and self.focus == self.title_editor):
            self.focus.emit('copy-clipboard')
        elif self.focus == self.task_view:
            if self.sellist is None: return
            row_texts = self.__do_copy_real(self.sellist, self.copied_rows)
            self.clipboard.set_text("\n".join(row_texts), -1)

    def __do_copy_real(self, subject, rowlist):
        '''Iterates selected rows and their children, storing shallow copies of
        their data with [:]. See __copy_children() for child recursion.'''
        row_texts = []
        del rowlist[:]
        for path in subject:
            row_texts.append(self.tasklist[path][13])
            # We store a parent reference along with each row's data. At the top
            # level, that reference is obviously nothing, but children refer to
            # their parent iters to maintain the tree.
            rowlist.append([0] + self.tasklist[path][:])
            treeiter = self.tasklist.get_iter(path)
            self.__copy_children(treeiter, len(rowlist), rowlist)
        return row_texts

    def __copy_children(self, treeiter, parent_index, rowlist):
        '''Iterates a list of children and recurses to their own children,
        storing shallow copies of their data with [:].'''
        child_iter = self.tasklist.iter_children(treeiter)
        while child_iter != None:
            rowlist.append([parent_index] + self.tasklist[child_iter][:])
            self.__copy_children(child_iter, len(rowlist), rowlist)
            child_iter = self.tasklist.iter_next(child_iter)

    def do_paste(self, widget=None):
        '''Applies paste operation depending on current internal focus. For
        notes or title, the 'paste-clipboard' signal is emitted. For the task
        list, new rows are created after the current row and populated with data
        our internal 'clipboard' of rows. See __do_paste_real().'''
        if self.focus == self.notes_view or (self.title_editor is not None and self.focus == self.title_editor):
            self.focus.emit('paste-clipboard')
        elif self.focus == self.task_view:
            if not self.copied_rows: return

            if self.seliter is None:
                parent_iter = None
            else:
                #get parent
                path = self.tasklist.get_path(self.seliter).to_string()
                parts = path.rpartition(':')
                parent_path = parts[0]
                if parent_path != "":
                    parent_iter = self.tasklist.get_iter(parent_path)
                else:
                    parent_iter = None

            #do the actual pasting
            new_iters = self.__do_paste_real(parent_iter, self.seliter, self.copied_rows)

            #push "paste" undo entry
            ppath = parent_path if parent_iter is not None else None
            spath = self.sellist[0] if self.seliter is not None else None
            self.__push_undoable("paste", (ppath, spath, self.copied_rows[:], new_iters))

    def __do_paste_real(self, parent_iter, sibling_iter, row_data, apply_filter=True):
        '''Private function which creates new rows and populates them with data
        from the internal clipboard.

        If apply_filter is True, the data is first filtered to remove done
        state, completion date, etc. as these are often undesirable in pasted
        rows. Setting that flag to false forces all row data to be copied
        verbatim, which is good when dealing with undo/redo operations.'''
        new_iters = []
        # Since row data is stored in a flat list, we have to track parentage and siblings manually.
        parents = [parent_iter] # List of parents by index. Top level always points to the meta-parent we were given.
        last_row = sibling_iter # Track previous sibling to maintain row order

        #iterate row data and add it
        for row in row_data:
            new_row = self.defaults[:]
            if apply_filter:
                inherit = [0,4,5,8,9,10,11,13,14] #columns to preserve from original row
                for i in inherit:
                    new_row[i] = row[i+1]
            else:
                for i in range(len(self.defaults)):
                    new_row[i] = row[i+1]

            #handle parent/sibling logic
            parent = parents[row[0]]
            if parent == parent_iter:
                sibling = last_row
            else:
                sibling = None
            #add the new row with its data
            treeiter = self.tasklist.insert_after(parent, sibling, new_row)

            #add new parent to the lsit
            parents.append(treeiter)
            if parent == parent_iter:
                new_iters.append(treeiter)
                last_row = treeiter

            #update time est and percent separately
            self.commit_est_iter(treeiter, row[3]/3600)
            self.calc_parent_pct(self.tasklist.get_path(treeiter).to_string())

        self.make_dirty()
        return new_iters

    def do_paste_into(self, widget=None):
        '''Sets up a paste operation with a row as the new parent. See
        __do_paste_real().'''
        if self.focus != self.task_view: return
        if self.seliter is None: return

        new_iters = self.__do_paste_real(self.seliter, None, self.copied_rows)

        #push "paste" undo
        ppath = self.sellist[0]
        self.__push_undoable("paste", (ppath, None, self.copied_rows[:], new_iters))

        self.make_dirty()

    def do_undo(self, widget=None):
        '''Handles undo logic. For the notes entry, it just calls that object's
        own undo() function (see undobuffer module). For the task list, it
        relies on a list of undoable actions pushed by every function which
        supports undo (see __push_undoable()). Each action has its own undo
        procedure.'''
        #Note that we never set the undo or redo action's sensitivities. They
        #must always be sensitive to allow for undo/redo within the notes_view
        #widget, regardless of the task undo/redo buffers' statii.

        if self.focus == self.notes_view:
            self.notes_buff.undo()
        elif self.focus == self.task_view:
            if len(self.undobuffer) == 0: return

            #get action tuple
            action = self.undobuffer.pop()
            #execute action's inverse
            if action[0] == "add":
                paths = action[1]
                data = self.tasklist[paths[0]][:]
                self.del_task(paths[0])
                self.redobuffer.append((action[0], (paths, data)))
            elif action[0] == "notes":
                path = action[1][0]
                oldtext = action[1][1]
                self.tasklist[path][14] = oldtext
                if self.sellist[0] == path:
                    self.notes_buff.set_text(oldtext)
                self.redobuffer.append(action)
            elif action[0] == "change":
                # Handler generic field changes. Anything that needs extra
                # processing should get its own handler.
                params = action[1]
                path = params[0]
                field = params[1]
                oldval = params[2]
                self.tasklist[path][field] = oldval
                self.redobuffer.append(action)
            elif action[0] == "spent":
                path = action[1][0]
                oldval = action[1][1]
                self.commit_spent(path=path, new_spent = oldval/3600)
                self.redobuffer.append(action)
            elif action[0] == "est":
                path = action[1][0]
                oldval = action[1][1]
                self.commit_est(path=path, new_est = oldval/3600)
                self.redobuffer.append(action)
            elif action[0] == "done":
                path = action[1][0]
                oldval = action[1][1]
                self.commit_done(path=path, new_done = oldval)
                self.redobuffer.append(action)
            elif action[0] == "paste":
                data = action[1]
                for treeiter in data[3]:
                    #ensure we aren't tracking anything
                    if self.tasklist[treeiter][17]:
                        self.track_action.set_active(False)

                    self.commit_est_iter(treeiter, 0) #void our est time
                    self.commit_spent_iter(treeiter, 0) #void our spent time
                    self.tasklist.remove(treeiter)

                #update parent pct done
                if data[0] is not None:
                    self.calc_pct(data[0])

                self.redobuffer.append(("paste", (data[0], data[1], data[2])))
            elif action[0] == "del":
                #TODO clean up task order
                data = action[1]
                parent_iter = self.tasklist.get_iter(data[0]) if data[0] is not None else None
                sibling_iter = self.tasklist.get_iter(data[1]) if data[1] is not None else None
                new_iters = self.__do_paste_real(parent_iter, sibling_iter, data[2], False)
                self.task_selected(self.selection)
                self.redobuffer.append(("del", (data[0], data[1], data[2], new_iters)))

    def do_redo(self, widget=None):
        '''Handles redo logic. For the notes entry, it just calls that object's
        own redo() function (see undobuffer module). For the task list, it
        relies on a list of undoable actions which were pushed to the redo stack
        by do_undo(). Each action has its own redo procedure.'''
        if self.focus == self.notes_view:
            self.notes_buff.redo()
        elif self.focus == self.task_view:
            if len(self.redobuffer) == 0: return

            #get action tuple
            action = self.redobuffer.pop()
            #execute action
            if action[0] == "add":
                paths = action[1][0]
                row_data = action[1][1]
                if paths[2] is not None and paths[1] is not paths[2]:
                    seliter = self.tasklist.get_iter(paths[2])
                    new_row_iter = self.tasklist.insert_after(None, seliter, row_data)
                else:
                    parent_iter = self.tasklist.get_iter(paths[1]) if paths[1] is not None else None
                    new_row_iter = self.tasklist.append(parent_iter, row_data)
                newpath = self.tasklist.get_path(new_row_iter).to_string()
                self.undobuffer.append((action[0], (newpath, paths[1], paths[2])))
            elif action[0] == "notes":
                path = action[1][0]
                newtext = action[1][2]
                self.tasklist[path][14] = newtext
                if self.sellist[0] == path:
                    self.notes_buff.set_text(newtext)
                self.undobuffer.append(action)
            elif action[0] == "change":
                # Handler generic field changes. Anything that needs extra
                # processing should get its own handler.
                params = action[1]
                path = params[0]
                field = params[1]
                newval = params[3]
                self.tasklist[path][field] = newval
                self.undobuffer.append(action)
            elif action[0] == "spent":
                path = action[1][0]
                newval = action[1][2]
                self.commit_spent(path=path, new_spent = newval/3600)
                self.undobuffer.append(action)
            elif action[0] == "est":
                path = action[1][0]
                newval = action[1][2]
                self.commit_est(path=path, new_est = newval/3600)
                self.undobuffer.append(action)
            elif action[0] == "done":
                path = action[1][0]
                newval = action[1][1]
                self.commit_done(path=path, new_done = newval)
                self.undobuffer.append(action)
            elif action[0] == "paste":
                #TODO clean up task order
                data = action[1]
                parent_iter = self.tasklist.get_iter(data[0]) if data[0] is not None else None
                sibling_iter = self.tasklist.get_iter(data[1]) if data[1] is not None else None
                new_iters = self.__do_paste_real(parent_iter, sibling_iter, data[2])
                self.undobuffer.append(("paste", (data[0], data[1], data[2], new_iters)))
            elif action[0] == "del":
                data = action[1]
                for treeiter in data[3]:
                    #ensure we aren't tracking anything
                    if self.tasklist[treeiter][17]:
                        self.track_action.set_active(False)

                    self.commit_est_iter(treeiter, 0) #void our est time
                    self.commit_spent_iter(treeiter, 0) #void our spent time
                    self.tasklist.remove(treeiter)

                #update parent pct done
                if data[0] is not None:
                    self.calc_pct(data[0])

                self.undobuffer.append(("del", (data[0], data[1], data[2])))

    def __push_undoable(self, action, data):
        '''Pushes a tuple onto the undobuffer list consisting of the action name
        and accompanying data. The name must be recognized by do_undo() and
        do_redo().'''
        self.undobuffer.append((action, data))
        del self.redobuffer[:]

    def display_columns(self):
        '''Clears the currently displayed columns and loads the ones specified
        in 'self.cols_visible'. Order is honored.'''
        #clear current cols
        for col in self.task_view.get_columns():
            self.task_view.remove_column(col)
        cols_vis = []

        #add columns from global var, in order specified
        for col, vis in self.cols_visible:
            if vis:
                self.task_view.append_column(self.cols_available[col])
                cols_vis.append(col)

        #mark new visibilities
        for row in self.cols:
            row[2] = row[0] in cols_vis

        #ensure the title column always expands to show children
        self.task_view.set_properties(expander_column=self.col_title)

    def notes_keys_dn(self, widget=None, event=None):
        '''Catches key-down events in the notes editor to enable custom actions.
        Currently it tracks the status of the Control_* and Enter keys. When
        Control+Enter appear together, the contents of the editor are saved.'''
        kvn = Gdk.keyval_name(event.keyval)
        if kvn == "Control_L" or kvn == "Control_R":
            self.notes_ctl_mask = True
        if kvn == "Return" and self.notes_ctl_mask:
            self.commit_notes()
            self.notes_ctl_mask = False
            return True

    def notes_keys_up(self, widget=None, event=None):
        '''Catches key-up events in the notes editor. Used to clear the
        Control-key state mask.'''
        kvn = Gdk.keyval_name(event.keyval)
        if kvn == "Control_L" or kvn == "Control_R":
            self.notes_ctl_mask = False

    def tasks_keys_dn(self, widget=None, event=None):
        '''Catches key-down events for the task list itself. This allows us to
        bind the Delete key to del_current_task() and force F2 to begin editing
        the current row's title.'''
        kvn = Gdk.keyval_name(event.keyval)
        if kvn == "Delete":
            self.del_current_task()
            return True
        if kvn == "F2":
            path = self.tasklist.get_path(self.seliter)
            self.task_view.set_cursor_on_cell(path, self.col_title, self.title_cell, True)
            return True

    def title_keys_dn(self, widget=None, event=None):
        '''Catches key-down events for the task title editor. Lets us cancel
        in-progress edits when the Escape key is pressed.'''
        kvn = Gdk.keyval_name(event.keyval)
        if kvn == "Escape":
            self.commit_title(path=self.title_edit_path, new_title='', write=False)

    def tasks_mouse_click(self, widget=None, event=None):
        '''Catches mouse clicks for the task list. Allows us to show the context
        menu on a right-click.'''
        if event.button == 3 and event.type == Gdk.EventType.BUTTON_PRESS:
            self.task_popup.show_all()
            self.task_popup.popup(None, None,
                lambda menu, data: (
                    event.get_root_coords()[0],
                    event.get_root_coords()[1], True),
                None, event.button, event.time)
            return True

    def track_maximized(self, widget, event, data=None):
        '''Tracks the window's maximized state. We save this as part of the
        window geometry in htdl files.'''
        mask = Gdk.WindowState.MAXIMIZED
        self.maximized = (widget.get_window().get_state() & mask) == mask

    def toggle_col_visible(self, widget, path, data=None):
        '''Adds and removes columns from the task list. Used by Document
        Properties.'''
        code = self.cols[path][0] #internal name of the column
        visible_now = self.cols[path][2] #current state
        real_idex = self.cols_visible.index((code, visible_now)) #index of the row
        idex = real_idex
        # Now we modify the index based on the visibility of the other columns.
        # This gives us an index relative to the columns displayed by the task
        # list.
        for col in self.cols_visible[:real_idex]:
            if not col[1]: idex -= 1

        #remove or insert as necessary
        if visible_now:
            self.task_view.remove_column(self.cols_available[code])
        else:
            self.task_view.insert_column(self.cols_available[code], idex)

        #update flags in 'cols_visible' list, 'cols' liststore
        self.cols_visible[real_idex] = (code, not visible_now)
        self.cols[path][2] = not visible_now
        self.make_dirty()

    def move_col(self, widget, sel, offset):
        '''Shift a column up or down in the column list. Effectively moves
        columns left or right within the task list's display. Used by Document
        Properties dialog.'''
        colstore, orig = sel.get_selected()
        if orig is None: return

        #store the treeiter we'll swap with
        if offset == "up":
            target = colstore.iter_previous(orig)
        else:
            target = colstore.iter_next(orig)

        #store column tuples; consists of column name and visible flag
        col1 = (colstore[orig][0], colstore[orig][2])
        col2 = (colstore[target][0], colstore[target][2])
        #now cache their indexes
        id1 = self.cols_visible.index(col1)
        id2 = self.cols_visible.index(col2)

        # We can only actually shift in one direction, so we work out how to do
        # that using the relative indices of the columns. I.e. we move the
        # smaller index in front of the bigger index.
        small = min(id1, id2)
        big = max(id1, id2)
        s = self.cols_available[self.cols_visible[small][0]]
        b = self.cols_available[self.cols_visible[big][0]]
        self.task_view.move_column_after(s, b) #do the shift

        #swap positions in 'cols_visible' list and 'colstore' liststore
        self.cols_visible[id2], self.cols_visible[id1] = self.cols_visible[id1], self.cols_visible[id2]
        colstore.swap(target, orig)
        self.make_dirty()

    def reset_cols(self, widget):
        self.cols_visible = self.cols_default[:]
        self.display_columns()

    def make_stats(self, treeiter = None):
        '''Creates a dict of document statistics. Right now, it includes the
        total number of tasks, number open, and number done. Used by Document
        Properties dialog.'''
        if treeiter is None:
            treeiter = self.tasklist.get_iter_first()

        total = 0
        total_open = 0
        total_done = 0

        while treeiter is not None:
            if self.tasklist.iter_n_children(treeiter):
                childiter = self.tasklist.iter_children(treeiter)
                ret = self.make_stats(childiter)
                total += ret['total']
                total_open += ret['open']
                total_done += ret['done']
            total += 1
            if self.tasklist[treeiter][12]:
                total_done += 1
            else:
                total_open += 1
            treeiter = self.tasklist.iter_next(treeiter)

        return {'total': total, 'open': total_open, 'done': total_done}

    def edit_assigners(self, widget, data=None):
        '''Wrapper for the label edit dialog (see the 'labeledit' module). Sets
        up the dialog's title, the liststore to edit, and the list to use for
        reference.'''
        self.label_edit_dlg.set_title("Manage Assigners (From)")
        self.label_edit_dlg.set_frame_label("Manage Assigners")
        self.label_edit_dlg.set_store(self.assigners)
        self.label_edit_dlg.set_list(self.assigners_list)
        self.label_edit_dlg.set_instructions("Assigners", "From")
        self.label_edit_dlg.show_all()

    def edit_assignees(self, widget, data=None):
        '''Wrapper for the label edit dialog (see the 'labeledit' module). Sets
        up the dialog's title, the liststore to edit, and the list to use for
        reference.'''
        self.label_edit_dlg.set_title("Manage Assignees (To)")
        self.label_edit_dlg.set_frame_label("Manage Assignees")
        self.label_edit_dlg.set_store(self.assignees)
        self.label_edit_dlg.set_list(self.assignees_list)
        self.label_edit_dlg.set_instructions("Assignees", "To")
        self.label_edit_dlg.show_all()

    def edit_statii(self, widget, data=None):
        '''Wrapper for the label edit dialog (see the 'labeledit' module). Sets
        up the dialog's title, the liststore to edit, and the list to use for
        reference.'''
        self.label_edit_dlg.set_title("Manage Status Labels")
        self.label_edit_dlg.set_frame_label("Manage Status Labels")
        self.label_edit_dlg.set_store(self.statii)
        self.label_edit_dlg.set_list(self.statii_list)
        self.label_edit_dlg.set_instructions("Status labels", "Status")
        self.label_edit_dlg.show_all()

    def main_filter(self, model, treeiter, data=None):
        '''Task list filtering function. Currently a placeholder.'''
        return True

    def archive_done(self, widget, data=None):
        '''Saves top-level done tasks (and descendents) to a separate archive
        file, then deletes them. Currently a placeholder.'''

        # show the export dialog
        dlg = dialogs.misc.htd_warn_archive(self)
        retval = dlg.run()
        dlg.destroy()

        if retval == -3:
            #do the archive operation

            # archive filename is our path + _archive + ext
            bits = splitext(self.file_name)
            archive_path = bits[0]+'_archive'+bits[1]

            # someplace to store the DONE entries
            # templist = copy_treemodel(self.tasklist)

            # disable signals while we make big changes to the model
            self.task_view.freeze_child_notify()

            # loop through self.tasklist, adding DONE entries and descendents to templist and removing them from our list
            archive_filter = self.tasklist.filter_new(None)
            archive_filter.set_visible_column(12)

            # append our rows to the selected file
            self.__do_save(archive_path, archive_filter, True)
            del archive_filter

            # remove rows from the main file
            treeiter = self.tasklist.get_iter_first()
            while treeiter is not None:
                if self.tasklist[treeiter][12] is True:
                    self.tasklist.remove(treeiter)
                else:
                    treeiter = self.tasklist.iter_next(treeiter)

            #start sending signals again and take focus
            self.task_view.thaw_child_notify()
            self.task_view.grab_focus()

            #clear undo and redo buffers
            del self.undobuffer[:]
            del self.redobuffer[:]

            self.file_dirty = True
            self.update_title()
            return True
        else:
            #cancel or any other code (like from esc key)
            return False

    def import_settings(self):
        '''Loads global setting vars from gsettings object.'''
        #parse column order and visibility
        col_order = self.settings.get_value("col-order")
        col_mask = self.settings.get_value("col-visibility")
        for i in range(len(col_order)):
            self.cols_visible.append((col_order[i], col_mask[i]))
            self.cols_default.append((col_order[i], col_mask[i]))

        #add assigners, assignees, statii
        self.assigners_default = list(self.settings.get_value("default-assigners"))
        self.assignees_default = list(self.settings.get_value("default-assignees"))
        self.statii_default = list(self.settings.get_value("default-statii"))

        #store open last file
        self.open_last_file = self.settings.get_boolean("reopen")

        #store use_tabs
        self.use_tabs = self.settings.get_boolean("use-tabs")

        #store toolbar vis
        self.toolbar_visible = self.settings.get_boolean("show-toolbar")

        #store whether to clobber current file on open
        self.clobber = self.settings.get_boolean("clobber-on-new")

    def toggle_toolbar(self, widget=None, event=None):
        '''Toggles visibility of the toolbar. Toggles the gsettings far, whose
        update triggers a separate function to update the bar's visibility
        setting and our internal flag.'''
        self.settings.set_boolean("show-toolbar", widget.get_active())

    def settings_toolbar_vis_changed(self, settings, key, data=None):
        '''Handles external changes to the toolbar visibility setting.'''
        self.toolbar_visible = settings.get_boolean("show-toolbar")
        self.toolbar.set_visible(self.toolbar_visible)
        self.toolbar_action.set_active(self.toolbar_visible)

    def toggle_reopen(self, widget, data=None):
        self.settings.set_boolean("reopen", widget.get_active())

    def settings_reopen_changed(self, settings, key, data=None):
        self.open_last_file = settings.get_boolean("reopen")
        self.prefs_dlg.reopen_toggle.set_active(self.open_last_file)

    def toggle_clobber(self, widget, data=None):
        self.settings.set_boolean("clobber-on-new", widget.get_active())

    def settings_clobber_changed(self, settings, key, data=None):
        self.clobber = settings.get_boolean("clobber-on-new")
        self.prefs_dlg.clobber_toggle.set_active(self.clobber)

    def toggle_use_tabs(self, widget, data=None):
        self.settings.set_boolean("use-tabs", widget.get_active())

    def settings_use_tabs_changed(self, settings, key, data=None):
        self.use_tabs = settings.get_boolean("use-tabs")
        self.prefs_dlg.use_tabs_toggle.set_active(self.use_tabs)
        self.prefs_dlg.use_wins_toggle.set_active(not self.use_tabs)

    def __init__(self):
        '''Program setup and initialization. Sets up internal variables and
        constructs the UI with some helper functions.'''
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
        self.tasklist_filter = self.tasklist.filter_new()
        self.tasklist_filter.set_visible_func(self.main_filter)

        self.defaults = [
            5,      #default priority
            0,      #pct complete
            0,      #est time taken
            0,      #act time taken
            "",     #est begin
            "",     #est complete
            "",     #act begin
            "",     #act complete
            "",     #due
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

        self.assigners = Gtk.ListStore(str)
        self.assigners.set_sort_column_id(0, Gtk.SortType.ASCENDING)
        self.assigners_list = []
        self.assigners_default = []
        self.assignees = Gtk.ListStore(str)
        self.assignees.set_sort_column_id(0, Gtk.SortType.ASCENDING)
        self.assignees_list = []
        self.assignees_default = []
        self.statii = Gtk.ListStore(str)
        self.statii.set_sort_column_id(0, Gtk.SortType.ASCENDING)
        self.statii_list = []
        self.statii_default = []
        self.seliter = None
        self.sellist = None
        self.selcount = 0
        self.title_editor = None
        self.notes_ctl_mask = False
        self.notes_shift_mask = False
        self.parent = None
        self.title_key_press_catcher = None
        self.title_buff = None
        self.file_name = ""
        self.file_filter = None
        self.file_dirty = False
        self.tracking = None
        self.timer_start = None
        self.last_save = datetime.now()
        self.focus = None
        self.copied_rows = []
        self.cols_available = {}
        self.cols_visible = []
        self.cols_default = []
        self.cols = Gtk.ListStore(str, str, bool, bool) #code, label for settings screen, visible flag, can hide flag
        self.undobuffer = []
        self.redobuffer = []
        self.maximized = False

        #construct settings object and changed::* bindings
        self.settings = Gio.Settings.new("apps.hitodo")
        self.settings.connect("changed::col-order", self.skip)
        self.settings.connect("changed::col-visibility", self.skip)
        self.settings.connect("changed::default-assigners", self.skip)
        self.settings.connect("changed::default-assignees", self.skip)
        self.settings.connect("changed::default-statii", self.skip)
        self.settings.connect("changed::reopen", self.settings_reopen_changed)
        self.settings.connect("changed::use-tabs", self.settings_use_tabs_changed)
        self.settings.connect("changed::show-toolbar", self.settings_toolbar_vis_changed)
        self.settings.connect("changed::clobber-on-new", self.settings_clobber_changed)

        #These are overwridden by GSettings object
        self.toolbar_visible = True
        self.clobber = False
        self.use_tabs = False
        self.open_last_file = True

        self.import_settings()

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
        self.toolbar = uimanager.get_widget("/ToolBar")
        self.toolbar.get_style_context().add_class(Gtk.STYLE_CLASS_PRIMARY_TOOLBAR)
        self.task_popup = uimanager.get_widget("/TaskPopup")

        #start with a simple stacked layout
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        #add the menu and tool bars on top
        main_box.pack_start(menubar, False, False, 0)
        main_box.pack_start(self.toolbar, False, False, 0)

        #now we create a horizontal pane
        self.task_pane = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        self.task_pane.set_position(900)

        #add task list area
        task_scroll_win = Gtk.ScrolledWindow()
        task_scroll_win.set_hexpand(True)
        task_scroll_win.set_vexpand(True)
        self.task_view = Gtk.TreeView(self.tasklist_filter)

        #set up columns
        self.create_columns()
        self.display_columns()

        #set up selection handling and add the completed table widget
        self.selection = self.task_view.get_selection()
        self.selection.set_mode(Gtk.SelectionMode.MULTIPLE)
        self.sel_changed_handler = self.selection.connect("changed", self.task_selected)
        self.task_view.set_properties(enable_tree_lines=True, reorderable=True, enable_search=True, search_column=13, rules_hint=True)
        self.task_view.connect('key-press-event', self.tasks_keys_dn)
        self.task_view.connect('focus-in-event', self.track_focus)
        self.task_view.connect('button-press-event', self.tasks_mouse_click)
        task_scroll_win.add(self.task_view)
        self.task_pane.pack1(task_scroll_win, True, True)

        #add notes area
        notes_box = Gtk.Frame()
        #notes_box.set_orientation(Gtk.Orientation.VERTICAL)
        notes_box.set_shadow_type(Gtk.ShadowType.NONE)
        notes_lbl = Gtk.Label()
        notes_lbl.set_markup("<b>_Comments</b>")
        notes_lbl.set_property("use-underline", True)
        notes_box.set_label_widget(notes_lbl)
        #notes_box.pack_start(notes_lbl, False, False, 3)

        notes_scroll_win = Gtk.ScrolledWindow()
        notes_scroll_win.set_hexpand(True)
        notes_scroll_win.set_vexpand(True)
        self.notes_buff = undobuffer.UndoableTextBuffer()
        self.notes_view = Gtk.TextView()
        self.notes_view.set_buffer(self.notes_buff)
        self.notes_view.connect('focus-in-event', self.track_focus)
        self.notes_view.connect('focus-out-event', self.commit_notes)
        self.notes_view.connect('key-press-event', self.notes_keys_dn)
        self.notes_view.connect('key-release-event', self.notes_keys_up)
        self.notes_view.set_wrap_mode(Gtk.WrapMode.WORD)
        notes_scroll_win.add(self.notes_view)

        notes_lbl.set_mnemonic_widget(self.notes_view)

        #notes_box.pack_start(notes_scroll_win, True, True, 0)
        notes_box.add(notes_scroll_win)
        self.task_pane.pack2(notes_box, True, True)

        #commit the task editing pane
        main_box.pack_start(self.task_pane, True, True, 0)

        #commit the ui
        self.add(main_box)

        #set up styling
        style_provider = Gtk.CssProvider()
        style_provider.load_from_data(CSS)
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
            style_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        # create a clipboard for easy copying
        self.clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        self.connect("delete-event", self.destroy)
        self.connect("window-state-event", self.track_maximized)
        self.show_all()

        #now we can hide the toolbar
        self.toolbar.set_visible(self.toolbar_visible)

        #set up our dialogs
        self.open_dlg = dialogs.misc.htd_open(self)
        self.save_dlg = dialogs.misc.htd_save(self)
        self.about_dlg = dialogs.misc.htd_about(self)
        self.prefs_dlg = dialogs.prefs.main(self)
        self.settings_use_tabs_changed(self.settings, key=None, data=None) #toggle visibility here to avoid errors from a spurious "toggled" event
        self.docprops_dlg = dialogs.docprops.main(self)
        self.label_edit_dlg = dialogs.labeledit.main(self)
        self.version_warn_dlg = dialogs.misc.htd_version_warning(self)

        if self.open_last_file: self.__open_last()

    def date_render(self, col, cell, model, tree_iter, data):
        '''Cell renderer for date cells. Converts datetime objects from the
        tasklist model to displayable strings.'''
        val = model[tree_iter][data]
        duetime = model[tree_iter][15]

        fmt = "%x %X" if duetime else "%x"
        out = "" if val is "" else val.strftime(fmt)
        cell.set_property("text", str(out))

    def datecompare(self, model, row1, row2, data=None):
        '''Sorting function for date cells. Compares datetime objects from two
        rows.'''
        sort_column, _ = model.get_sort_column_id()
        value1 = model.get_value(row1, sort_column)
        if value1 is "": value1 = datetime.min
        value2 = model.get_value(row2, sort_column)
        if value2 is "": value2 = datetime.min

        if value1 < value2:
            return -1
        elif value1 == value2:
            return 0
        else:
            return 1

    def title_render(self, col, cell, model, tree_iter, data):
        '''Cell renderer for notes field. Eliminates line breaks so that no task
        entry takes up multiple lines.'''
        text = model[tree_iter][13]
        notes = model[tree_iter][14]
        out = escape(text) if notes == '' else "%s  <span color=\"#999\">[%s]</span>" % (escape(text), escape(notes.replace(linesep, ' ')))
        cell.set_property("markup", out)

    def duration_render(self, col, cell, model, tree_iter, data):
        '''Cell renderer for est and spent cells. Converts seconds into hours
        with a suffix. May expand later to intelligently use other units.'''
        val = model[tree_iter][data]
        out = '' if val == 0 else '%1.2fH' % (val/3600)
        cell.set_property("text", out)

    def create_columns(self):
        '''Creates the columns used by the task list view.'''
        priority = Gtk.CellRendererText(editable=True, foreground="#999")
        priority.connect("edited", self.commit_priority)
        priority.connect("editing-started", self.priority_edit_start)
        col_priority = Gtk.TreeViewColumn("!", priority, text=0, foreground_set=12)
        col_priority.set_sort_column_id(0)
        #col_priority.set_reorderable(True)
        col_priority.code = "priority"
        self.cols_available['priority'] = col_priority
        self.cols.append(['priority', 'Priority (!)', True, True])

        pct = Gtk.CellRendererProgress()
        col_pct = Gtk.TreeViewColumn("%", pct, value=1, visible=16)
        #col_pct.set_reorderable(True)
        col_pct.set_sort_column_id(1)
        col_pct.code = "pct complete"
        self.cols_available['pct complete'] = col_pct
        self.cols.append(['pct complete', 'Percent Complete (%)', True, True])

        est = Gtk.CellRendererText(foreground="#999", editable=True)
        est.connect("edited", self.commit_est)
        est.connect("editing-started", self.est_edit_start)
        col_est = Gtk.TreeViewColumn("Est", est, foreground_set=12)
        #col_est.set_reorderable(True)
        col_est.set_sort_column_id(2)
        col_est.set_cell_data_func(est, self.duration_render, 2)
        col_est.code = "time est"
        self.cols_available['time est'] = col_est
        self.cols.append(['time est', 'Est', True, True])

        spent = Gtk.CellRendererText(foreground="#999", editable=True)
        spent.connect("edited", self.commit_spent)
        spent.connect("editing-started", self.spent_edit_start)
        col_spent = Gtk.TreeViewColumn("Spent", spent, foreground_set=12)
        #col_spent.set_reorderable(True)
        col_spent.set_sort_column_id(3)
        col_spent.set_cell_data_func(spent, self.duration_render, 3)
        col_spent.code = "time spent"
        self.cols_available['time spent'] = col_spent
        self.cols.append(['time spent', 'Spent', True, True])

        tracking = Gtk.CellRendererText(foreground="#b00", text=u"\u231A")
        col_tracking = Gtk.TreeViewColumn(u"\u231A", tracking, visible=17)
        #col_tracking.set_reorderable(True)
        col_tracking.code = "tracked"
        self.cols_available['tracked'] = col_tracking
        self.cols.append(['tracked', u'Tracking (\u231A)', True, True])

        est_begin = Gtk.CellRendererText(editable=True, foreground="#999")
        est_begin.connect("edited", self.commit_date, 4)
        est_begin.connect("editing-started", self.date_edit_start)
        col_est_begin = Gtk.TreeViewColumn("Est Begin", est_begin, foreground_set=12)
        #col_est_begin.set_reorderable(True)
        col_est_begin.set_sort_column_id(4)
        col_est_begin.set_cell_data_func(est_begin, self.date_render, 4)
        col_est_begin.code = "est begin"
        self.cols_available['est begin'] = col_est_begin
        self.cols.append(['est begin', 'Est Begin', False, True])

        est_complete = Gtk.CellRendererText(editable=True, foreground="#999")
        est_complete.connect("edited", self.commit_date, 5)
        est_complete.connect("editing-started", self.date_edit_start)
        col_est_complete = Gtk.TreeViewColumn("Est Complete", est_complete, foreground_set=12)
        #col_est_complete.set_reorderable(True)
        col_est_complete.set_sort_column_id(5)
        col_est_complete.set_cell_data_func(est_complete, self.date_render, 5)
        col_est_complete.code = "est begin"
        self.cols_available['est complete'] = col_est_complete
        self.cols.append(['est complete', 'Est Complete', False, True])

        due = Gtk.CellRendererText(editable=True, foreground="#999")
        due.connect("edited", self.commit_date, 8)
        due.connect("editing-started", self.date_edit_start)
        col_due = Gtk.TreeViewColumn("Due", due, foreground_set=12)
        #col_due.set_reorderable(True)
        col_due.set_sort_column_id(8)
        col_due.set_cell_data_func(due, self.date_render, 8)
        col_due.code = "due date"
        self.cols_available['due date'] = col_due
        self.cols.append(['due date', 'Due', True, True])

        act_begin = Gtk.CellRendererText(editable=True, foreground="#999")
        act_begin.connect("edited", self.commit_date, 6)
        act_begin.connect("editing-started", self.date_edit_start)
        col_act_begin = Gtk.TreeViewColumn("Begin", act_begin, foreground_set=12)
        #col_act_begin.set_reorderable(True)
        col_act_begin.set_sort_column_id(6)
        col_act_begin.set_cell_data_func(act_begin, self.date_render, 6)
        col_act_begin.code = "act begin"
        self.cols_available['act begin'] = col_act_begin
        self.cols.append(['act begin', 'Begin', False, True])

        completed = Gtk.CellRendererText(editable=True, foreground="#999")
        completed.connect("edited", self.commit_date, 7)
        completed.connect("editing-started", self.date_edit_start)
        col_completed = Gtk.TreeViewColumn("Completed", completed, foreground_set=12, visible=12)
        #col_completed.set_reorderable(True)
        col_completed.set_sort_column_id(7)
        col_completed.set_cell_data_func(completed, self.date_render, 7)
        col_completed.code = "complete date"
        self.cols_available['complete date'] = col_completed
        self.cols.append(['complete date', 'Completed', True, True])

        assigner = Gtk.CellRendererCombo(model=self.assigners, has_entry=True, editable=True, foreground="#999", text_column=0)
        assigner.connect("edited", self.commit_assigner)
        assigner.connect("editing-started", self.combo_edit_start)
        col_assigner = Gtk.TreeViewColumn("From", assigner, text=9, foreground_set=12)
        #col_assigner.set_reorderable(True)
        col_assigner.set_sort_column_id(9)
        col_assigner.code = "from"
        self.cols_available['from'] = col_assigner
        self.cols.append(['from', 'From', True, True])

        assignee = Gtk.CellRendererCombo(model=self.assignees, has_entry=True, editable=True, foreground="#999", text_column=0)
        assignee.connect("edited", self.commit_assignee)
        assignee.connect("editing-started", self.combo_edit_start)
        col_assignee = Gtk.TreeViewColumn("To", assignee, text=10, foreground_set=12)
        #col_assignee.set_reorderable(True)
        col_assignee.set_sort_column_id(10)
        col_assignee.code = "to"
        self.cols_available['to'] = col_assignee
        self.cols.append(['to', 'To', True, True])

        status = Gtk.CellRendererCombo(model=self.statii, has_entry=True, editable=True, foreground="#999", text_column=0)
        status.connect("edited", self.commit_status)
        status.connect("editing-started", self.combo_edit_start)
        col_status = Gtk.TreeViewColumn("Status", status, text=11, foreground_set=12)
        #col_status.set_reorderable(True)
        col_status.set_sort_column_id(11)
        col_status.code = "status"
        self.cols_available['status'] = col_status
        self.cols.append(['status', 'Status', True, True])

        done = Gtk.CellRendererToggle(activatable=True, radio=False)
        done.connect("toggled", self.commit_done)
        col_done = Gtk.TreeViewColumn(u"\u2713", done, active=12)
        col_done.set_sort_column_id(12)
        #col_done.set_reorderable(True)
        col_done.code = "done"
        self.cols_available['done'] = col_done
        self.cols.append(['done', u'Done (\u2713)', True, False])

        self.title_cell = Gtk.CellRendererText(editable=True, ellipsize=Pango.EllipsizeMode.MIDDLE, foreground="#999")
        self.title_cell.connect("edited", self.commit_title)
        self.title_cell.connect("editing-started", self.title_edit_start)
        self.title_cell.connect("editing-canceled", self.commit_title, None, None, True)
        self.col_title = Gtk.TreeViewColumn("Title")
        self.col_title.pack_start(self.title_cell, True)
        self.col_title.add_attribute(self.title_cell, "foreground-set", 12)
        self.col_title.add_attribute(self.title_cell, "strikethrough", 12)
        self.col_title.set_cell_data_func(self.title_cell, self.title_render)
        self.col_title.set_sort_column_id(13)
        self.col_title.code = "title"
        self.cols_available['title'] = self.col_title
        self.cols.append(['title', 'Title', True, False])

    def create_top_actions(self, action_group):
        '''Creates actions for UI menus and buttons. These are application-wide
        actions.'''
        action_group.add_actions([
            ("new_file", Gtk.STOCK_NEW, None, "", None, self.new_file),
            ("open_file", Gtk.STOCK_OPEN, None, None, "Open file", self.open_file),
            ("saveas_file", Gtk.STOCK_SAVE_AS, None, None, None, self.save_file_as),
            ("save_copy", None, "Sa_ve A Copy...", None, None, self.save_copy),
            ("archive_done", None, "Arc_hive Completed Tasks", None, None, self.archive_done),
            ("close", Gtk.STOCK_CLOSE, None, None, None, self.new_file),
            ("quit", Gtk.STOCK_QUIT, None, None, None, self.destroy),
            ("help_about", Gtk.STOCK_ABOUT, None, None, None, self.show_about),
            ("prefs", Gtk.STOCK_PREFERENCES, "Pr_eferences", None, None, self.set_prefs),
            ("doc_props", Gtk.STOCK_PROPERTIES, "_Document Properties", None, None, self.set_docprops),
            ("edit_assigners", None, "Assigne_rs (From)", None, "Manage this list's assigners", self.edit_assigners),
            ("edit_assignees", None, "Assigne_es (To)", None, "Manage this list's assignees", self.edit_assignees),
            ("edit_statii", None, "_Status", None, "Manage this list's status labels", self.edit_statii),
            ("FileMenu", None, "_File"),
            ("EditMenu", None, "_Edit"),
            ("TaskMenu", None, "_Task"),
            ("ViewMenu", None, "_View"),
            ("HelpMenu", None, "_Help"),
            ("LabelMenu", None, "_Manage Labels")
        ])
        self.toolbar_action = Gtk.ToggleAction("show_toolbar", "_Toolbar", "Show or hide the toolbar", None)
        self.toolbar_action.set_active(self.toolbar_visible)
        self.toolbar_action.connect("activate", self.toggle_toolbar)
        action_group.add_action(self.toolbar_action)

        self.recent_files = Gtk.RecentAction("recents", "_Recent Files", "Open a recently-used file", None)
        self.recent_files.set_properties(icon_name="document-open-recent", local_only=True, sort_type=Gtk.RecentSortType.MRU, show_not_found=False, show_numbers=True)
        htdl_filter = Gtk.RecentFilter()
        htdl_filter.add_pattern("*.htdl")
        htdl_filter.set_name("HiToDo Files (*.htdl)")
        self.recent_files.add_filter(htdl_filter)
        self.recent_files.connect("item-activated", self.open_recent)
        action_group.add_action(self.recent_files)

        save_file = Gtk.Action("save_file", None, "Save task list", Gtk.STOCK_SAVE)
        save_file.connect("activate", self.save_file)
        save_file.set_is_important(True)
        action_group.add_action_with_accel(save_file, None)


    def create_task_actions(self, action_group):
        '''Creates actions for UI menus and buttons. These are task-specific
        actions.'''
        action_group.add_actions([
            ("task_newsub", Gtk.STOCK_INDENT, "New S_ubtask", "<Primary><Shift>N", "Add a new subtask", self.add_subtask),
            ("sel_all", Gtk.STOCK_SELECT_ALL, None, "<Primary>A", None, self.select_all),
            ("sel_inv", None, "_Invert Selection", None, None, self.select_inv),
            ("sel_none", None, "Select _None", "<Primary><Shift>A", None, self.select_none),
            ("expand_all", None, "_Expand All", None, "Expand all tasks", self.expand_all),
            ("collapse_all", None, "_Collapse All", None, "Collapse all tasks", self.collapse_all)
        ])

        self.task_del = Gtk.Action("task_del", "Delete task", "Delete selected task(s)", Gtk.STOCK_REMOVE)
        self.task_del.connect("activate", self.del_current_task)
        action_group.add_action(self.task_del)

        self.task_cut = Gtk.Action("task_cut", None, "Cut", Gtk.STOCK_CUT)
        self.task_cut.connect("activate", self.do_cut)
        action_group.add_action_with_accel(self.task_cut, None)

        self.task_copy = Gtk.Action("task_copy", None, "Copy", Gtk.STOCK_COPY)
        self.task_copy.connect("activate", self.do_copy)
        action_group.add_action_with_accel(self.task_copy, None)

        self.task_paste = Gtk.Action("task_paste", None, "Paste", Gtk.STOCK_PASTE)
        self.task_paste.connect("activate", self.do_paste)
        action_group.add_action_with_accel(self.task_paste, None)

        self.task_paste_into = Gtk.Action("task_paste_into", "Paste as _Child", "Paste task as child", None)
        self.task_paste_into.connect("activate", self.do_paste_into)
        action_group.add_action_with_accel(self.task_paste_into, "<Primary><Shift>V")

        task_new = Gtk.Action("task_new", "_New Task", "Add a new task", Gtk.STOCK_ADD)
        task_new.connect("activate", self.add_task)
        task_new.set_is_important(True)
        task_new.set_short_label("Add")
        action_group.add_action_with_accel(task_new, "<Primary>N")

        self.undo_action = Gtk.Action("undo", None, "Undo", Gtk.STOCK_UNDO)
        self.undo_action.connect("activate", self.do_undo)
        self.undo_action.set_is_important(True)
        action_group.add_action_with_accel(self.undo_action, "<Primary>Z")

        self.redo_action = Gtk.Action("redo", None, "Redo", Gtk.STOCK_REDO)
        self.redo_action.connect("activate", self.do_redo)
        action_group.add_action_with_accel(self.redo_action, "<Primary><Shift>Z")

        self.track_action = Gtk.ToggleAction("track_spent", "_Track spent time", "Track time worked toward this task", None)
        self.track_action.set_properties(icon_name="appointment-soon")
        self.track_action.connect("activate", self.track_spent)
        self.track_action.set_is_important(True)
        self.track_action.set_short_label("Track")
        action_group.add_action_with_accel(self.track_action, "<Primary>T")

    def create_ui_manager(self):
        '''Constructs a ui manager, complete with acceleratorgroup.'''
        uimanager = Gtk.UIManager()

        # Throws exception if something went wrong
        uimanager.add_ui_from_string(UI_XML)

        # Add the accelerator group to the toplevel window
        accelgroup = uimanager.get_accel_group()
        self.add_accel_group(accelgroup)
        return uimanager

    def destroy(self, widget=None, data=None):
        '''Shows the 'confirm discard' dialog before closing, if applicable.'''
        if not self.confirm_discard(): return True
        Gtk.main_quit()

def copy_treemodel(orig):
    '''Create a new treemodel with the same columns as 'model'.'''
    column_types = []
    column_numbers = range(orig.get_n_columns())
    for i in column_numbers:
        column_types.append(orig.get_column_type(i))
    copy = Gtk.TreeStore(*column_types)
    return copy

def append_row(orig, path, treeiter, copy):
    '''Append a row to the treemodel 'copy' from the treemodel 'orig' while preserving parent-child relationships.
    Meant to be run as 'orig.foreach(append_row, copy)'.'''
    strpath = path.to_string()

    parts = strpath.rsplit(':', 1)
    parent_path = parts[0]
    parent_iter = None if parent_path == strpath else copy.get_iter(parent_path)

    copy.append(parent_iter, orig[treeiter][:])

def main():
    Gtk.main()
    return

def is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        return False

if __name__ == "__main__":
    htd = HiToDo()
    main()
