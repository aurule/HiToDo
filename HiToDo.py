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
from xml.etree.ElementTree import ParseError
from tarfile import ReadError
from os import linesep
from os.path import basename, dirname, splitext
from urlparse import urlparse
from urllib import unquote
from math import floor
import xml.etree.ElementTree as et
import operator
from cgi import escape
import sys
import re

import dialogs
from file_parsers import fileParser
import settings
import tools
import widgets
import undobuffer

UI_XML = """
<ui>
    <menubar name='MenuBar'>
        <menu action='FileMenu'>
            <menuitem action="new_file" />
            <menuitem action="open_file" />
            <menuitem action="recents" />
            <menuitem action="toggle_reopen" />
            <separator />
            <menuitem action="save_file" />
            <menuitem action="saveas_file" />
            <menuitem action="save_copy" />
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
        </menu>
        <menu action="ViewMenu">
            <menuitem action='show_toolbar' />
            <separator />
            <menuitem action='expand_all' />
            <menuitem action='collapse_all' />
            <separator />
            <menuitem action='swap_focus' />
            <menuitem action='pick_cols' />
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

# Define the gui and its actions.
class HiToDo(Gtk.Window):
    PROGRAM_VERSION = "0.9.5"

    def track_focus(self, widget, event=None):
        '''Updates internal focus tracking reference

        Our internal focus is used to choose which action to take on undo, redo,
        cut, copy, paste, etc.

        It may not match with the global input focus, usually because we don't
        always care about child widgets.

        Arguments:
        widget - Gtk.Widget - The widget we should consider as having focus
        '''
        self.focus = widget

    def add_task(self, widget=None, parent_iter=None):
        '''Adds a new task to the task list and begins editing

        Most of the time, parent_iter is None and the new task is added as a
        sibling of the currently-selected task. If no task is selected, the new
        task is added at the topmost level of the tree. The task is prepopulated
        with data from self.defaults.

        When parent_iter is given, the new task is prepended to that iter's
        children. The task is then populated with data from self.defaults and
        its parent. Inherited fields are priority, from, to, and the use due
        time flag.

        After being created, the new task's title field is given focus for
        immediate editing.

        Arguments:
        parent_iter - Gtk.TreeIter - Iter to our parent task, or None
        '''
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
        self.selection.unselect_all()
        self.selection.select_iter(new_row_iter)
        if parent_iter is not None:
            self.task_view.expand_to_path(path)
        self.task_view.set_cursor_on_cell(path, self.col_title, self.title_cell, True)

    def add_subtask(self, widget=None):
        '''Wrapper for add_task to create new task as child of current selected task'''

        self.add_task(parent_iter = self.seliter)

    def commit_all(self):
        '''Commit all possibly-in-progress edits.

        The functions commit_title, commit_notes, commit_date, and
        commit_priority are all invoked to ensure minimum data loss.
        '''
        self.commit_title()
        self.commit_notes()
        self.commit_date(field = 8)
        self.commit_priority()

    def save_work(self, widget, path, new_work, work_type):
        '''Save user-entered work time.

        This function takes data from an entry and converts it to hours before
        handing off to commit_work() for the heavy lifting.
        '''

        if isinstance(new_work, basestring):
            # interpret and convert to hours as needed
            new_work = new_work.strip()
            parts = re.match(r'(\d+\.?\d*)([\w ]*)', new_work)
            if parts:
                number = float(parts.group(1))
                unit = parts.group(2).strip()

                if unit in ('min', 'minutes', 'm'):
                    new_work = number / 60
                elif unit in ('day', 'days', 'd'):
                    new_work = number * 24
                else:
                    new_work = number

        self.commit_work(widget, path, new_work, work_type)


    def commit_work(self, widget=None, path=None, new_work=-1.0, work_type=''):
        '''Change a task's work time.

        Once our value is committed, we iterate up our parents, updating their values to account for ours.

        Keyword args:
        widget -- Gtk.Widget, optional, default None -- The calling widget. When populated, an undo entry will be pushed after execution.
        path -- str or Gtk.TreePath -- Path to the relevant model row.
        new_work -- float, default -1.0 -- Number of hours of work to commit. Non-float data aborts. Negative number causes a re-derive; see self.derive_work()
        work_type -- str, default None -- Describes what kind of work is being saved. Either "est" or "spent"; others may be added in the future.
        '''

        # fail out on bad args
        if path is None: return
        if work_type is None or work_type not in self.work_cols: return
        if type(path) is str and path == "": return
        if not tools.is_number(new_work): return

        work_col = self.work_cols[work_type]

        new_work = float(new_work)
        if new_work < 0:
            # if we were set to 0, derive instead of committing a literal zero
            self._derive_work(path, work_type)
            return

        old_work = self.tasklist[path][work_col] #store for later
        out = floor(new_work * 3600) #convert to seconds
        self.tasklist[path][work_col] = int(out) #save

        #now we need to adjust our parent's total
        parts = str(path).rpartition(':')
        parent_path = parts[0] #find parent path
        if parent_path != "":
            parent_work = self.tasklist[parent_path][work_col]
            pwork = (parent_work + out - old_work)/3600 #calculate new parent work
            self.commit_work(path=parent_path, new_work=pwork, work_type=work_type) #commit up the chain

        # Push undoable only on user click, not internal call. Very important since we recurse.
        if widget is not None:
            self.__push_undoable(work_type, (path, old_work, int(out)))

    def _derive_work(self, path=None, work_type=''):
        '''Calculates task work time based on children

        Iterates child tasks and sums up their work total, either est or spent.
        That total is saved to the task at path.

        Arguments:
        path - Gtk.TreePath, default None - Path of the task to start from
        work_type -- str, default None -- Describes what kind of work is being saved. Either "est" or "spent"; others may be added in the future.
        '''
        work_col = self.work_cols[work_type]

        total_work = 0
        treeiter = self.tasklist.get_iter(path)
        #no children means our work is 0 and we can stop
        if self.tasklist.iter_has_child(treeiter):
            #loop through our children and add their work total to ours
            child_iter = self.tasklist.iter_children(treeiter)
            while child_iter is not None:
                total_work += self.tasklist[child_iter][work_col]
                child_iter = self.tasklist.iter_next(child_iter)
        old_work = self.tasklist[path][work_col]
        self.commit_work(path = path, new_work = total_work/3600, work_type=work_type) #save it

        #push undoable. We have to push our own because commit_work only pushes when called from the UI.
        self.__push_undoable(work_type, (path, old_work, total_work))

    def duration_edit_start(self, renderer, editor, path, col=0):
        '''Set up time estimate editing field.

        Converts saved seconds into hours, truncating for brevity.
        Overrides the edit_start function of Gtk.CellRendererEditable.
        There is only one unique argument:
        col -- int, default 0 -- The treemodel column whose value should be displayed
        '''
        val = self.tasklist[path][col]
        self.track_focus(widget = editor)

    def track_spent(self, action=None, path=None, state=None):
        '''Handles time spent tracking

        Only really useful when called from the
        UI. When tracking is toggled on, a timestamp is saved. When tracking is
        toggled off, a new timestamp is fetched and the difference applied to
        that row's time spent total.

        Only one row (task) can be tracked at a time. We store a treeiter
        pointing to that row as well as set the row's tracked flag (field 17).
        '''

        on = action.get_active() if state is None else state

        if on:
            # if we're already tracking something, abort
            if self.tracking is not None:
                return

            # get our tracking iter and check for sanity
            trackiter = self.seliter if path is None else self.tasklist.get_iter(path)
            if trackiter is None:
                action.set_active(False)
                return
            if self.tasklist[trackiter][12]:
                action.set_active(False)
                return

            # set flags and store a timer object
            self.tracking = trackiter
            self.timer_start = datetime.now()
            title = self.tasklist[trackiter][13]
            self.tasklist[trackiter][17] = True
            action.set_tooltip("Stop tracking time toward '%s'" % title)
            self.__push_undoable('track_spent', (self.tasklist.get_path(trackiter)))
        else:
            # only track if we have an iter to track on
            if self.tracking is not None:
                diff = datetime.now() - self.timer_start
                secs = int(diff.total_seconds())
                path = self.tasklist.get_path(self.tracking)
                nspent = (self.tasklist[self.tracking][3] + secs) / 3600
                self.commit_work(path=path, new_work=nspent, work_type='spent')
                self.tasklist[self.tracking][17] = False
                self.make_dirty()

            self.tracking = None
            self.timer_start = None
            action.set_tooltip("Start tracking time toward current task")

    def commit_done(self, renderer=None, path=None, new_done=None):
        '''Toggles a task's done flag and handles the fallout

        Note: field 16 is the 'anti-done' flag and always set to the opposite value of field 12 ('done' flag).

        When moving to Done, a number of things happen:
        1. Pct complete is set to 100
        2. Children are forced to the Done state using __force_peers_done()
        3. Complete datetime is set to datetime.now()
        4. Tracking is canceled if applicable, which triggers its own handler, track_spent()

        When moving to Not Done, various other things happen:
        1. Our parent(s) are forced to the Not Done state using force_parent_not_done()
        3. Our own pct complete is recalculated with calc_pct()

        Finally, our parent's percent complete is always recalculated with calc_parent_pct()
        '''
        if path is None: return

        done = not new_done if new_done is not None else self.tasklist[path][12]

        if not done:
            #we're transitioning from not-done to done
            self.tasklist[path][1] = 100 #no need to calculate; we're 100% complete

            child_iter = self.tasklist.iter_children(self.tasklist.get_iter(path))
            forced = self.__force_peers_done(child_iter)
            self.tasklist[path][7] = datetime.now()
            if self.tasklist[path][17]:
                self.track_action.set_active(False)
        else:
            #we're transitioning from done to not-done
            forced = self.force_parent_not_done(path)
            self.calc_pct(path)

        self.tasklist[path][12] = not done
        self.tasklist[path][16] = done

        #add undo action only on user click
        if renderer is not None:
            self.__push_undoable("done", (path, done, not done, forced))

        #recalculate our parent's pct complete, if we have one
        self.calc_parent_pct(path)

    def __force_peers_done(self, treeiter):
        '''Recursively marks all tasks on this level as Done

        This involves a few steps:
        1. Tracking is ended, which triggers its own handler, track_spent()
        2. Pct complete is set to 100
        3. Completed timestamp is set to datetime.now() unless it's already been set.
        4. The Done flag and its sister are set

        Returns a list of paths which were forced to be done
        '''

        forced = []
        while treeiter != None:
            if self.tasklist[treeiter][12] == False:
                forced.append(self.tasklist.get_path(treeiter))

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
                forced += self.__force_peers_done(child_iter)

            #iterate to next sibling
            treeiter = self.tasklist.iter_next(treeiter)
        return forced

    def force_parent_not_done(self, path):
        '''Sets Done flag and its sister to False for all direct parents of path'''

        forced = []
        if not isinstance(path, basestring):
            path = path.to_string()
        parts = path.split(':')
        oldpath = ''
        for parent_path in parts:
            newpath = oldpath + parent_path
            parent_iter = self.tasklist.get_iter(newpath)
            if self.tasklist[parent_iter][12]:
                forced.append(newpath)
            self.tasklist[parent_iter][12] = False
            self.tasklist[parent_iter][16] = True
            oldpath = newpath + ':'
        return forced

    def calc_parent_pct(self, path):
        '''Calculates the pct complete of the direct parent of path.'''

        if not isinstance(path, basestring):
            path = path.to_string()
        parts = path.partition(':')
        parent_path = parts[0]
        if parent_path == path: return

        parent_iter = self.tasklist.get_iter(parent_path)
        self.__do_pct(parent_iter)

    def calc_pct(self, path):
        '''Calculates the pct complete of the task at path

        Mostly a wrapper function for __do_pct, as that requires an iter.
        '''
        treeiter = self.tasklist.get_iter(path)
        if self.tasklist.iter_n_children(treeiter) == 0:
            self.tasklist[treeiter][1] = 0
            return

        self.__do_pct(treeiter)

    def __do_pct(self, treeiter):
        '''Calculates the pct complete of the row at 'treeiter'

        Iterates through all levels of children, tallying the number marked Done
        against the total number found. Both tallies ignore children with
        children of their own (branches), since branches just summarize the pct
        complete of their own children.
        '''
        n_children = 0 # This is not the liststore's child count. It omits children who have children of their own.
        n_done = 0 # Also omits children who have children.
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

        if n_children is 0:
            self.tasklist[treeiter][1] = 0
        else:
            self.tasklist[treeiter][1] = int((n_done / n_children) * 100)
        return n_children, n_done

    def commit_priority(self, widget=None, path=None, new_priority=None):
        '''Sets the priority for 'path' to the value of new_priority'''

        if path is None: return

        old_val = self.tasklist[path][0]

        #priorities have to be integers
        if new_priority.isdigit():
            self.tasklist[path][0] = int(new_priority)
            self.__push_undoable("change", (path, 0, old_val, int(new_priority)))

    def commit_date(self, widget=None, path=None, new_date=None, field=None):
        '''Sets the value of a date field (due, complete, act begin, est begin,
        est complete) to the value of new_date'''

        if path is None: return

        old_val = self.tasklist[path][field]

        if new_date == "":
            dt = ""
        else:
            try:
                dt = datetime.strptime(new_date, '%x')
            except ValueError:
                dt = ""

        self.tasklist[path][field] = dt
        self.__push_undoable("change", (path, field, old_val, dt))

    def commit_status(self, widget=None, path=None, new_status=None):
        '''Sets the status string of 'path' to the value of new_status

        The value of new_status is also compared to the internal statii list and
        if it's new, it's added.
        '''
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
        '''Sets the status string of 'path' to the value of new_assigner

        The value of new_assigner is also compared to the internal from list and
        if it's new, it's added.
        '''
        if path is None: return

        if new_assigner != '' and new_assigner not in self.assigners_list:
            self.assigners.append([new_assigner])
            self.assigners_list.append(new_assigner)
        old_assigner = self.tasklist[path][9]

        self.tasklist[path][9] = new_assigner
        self.track_focus(widget = self.task_view)
        self.__push_undoable("change", (path, 9, old_assigner, new_assigner))

    def commit_assignee(self, widget=None, path=None, new_assignee=None):
        '''Sets the status string of 'path' to the value of new_assignee

        The value of new_assignee is also compared to the internal to list and
        if it's new, it's added.
        '''
        if path is None: return

        if new_assignee != '' and new_assignee not in self.assignees_list:
            self.assignees.append([new_assignee])
            self.assignees_list.append(new_assignee)
        old_assignee = self.tasklist[path][10]

        self.tasklist[path][10] = new_assignee
        self.track_focus(widget = self.task_view)
        self.__push_undoable("change", (path, 10, old_assignee, new_assignee))

    def commit_notes(self, widget=None, data=None):
        '''Saves the user-entered notes text to the notes field'''

        if self.seliter is None: return
        if not self.notes_view.has_focus():
            return #just in case we were called when the notes view was not actually being used

        start = self.notes_buff.get_iter_at_offset(0)
        end = self.notes_buff.get_iter_at_offset(-1)
        text = self.notes_buff.get_text(start, end, False)

        path = self.tasklist.get_path(self.seliter)
        oldtext = self.tasklist[self.seliter][14]

        self.tasklist[self.seliter][14] = text
        self.__push_undoable("notes", (path, oldtext, text))

    def commit_title(self, widget=None, path=None, new_title=None):
        '''Saves the user-entered title.

        Behavior differs for blank fields based on whether the task is new or
        not. If it's a new task (i.e. its existing title is blank), passing an
        empty string for new_title deletes the task. If it's an existing task,
        an empty new_title cancels the edit and the existing title is not
        changed.

        Arguments:
        path - Gtk.TreePath - Path of the task to change
        new_title - string - New title string to set
        '''
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
        self.tasklist[path][13] = new_title
        self.__push_undoable("change", (path, 13, old_title, new_title))

    def title_edit_start(self, renderer, editor, path):
        '''Set up the title editor widget

        We store the edit path, attach title_keys_dn() as a listener, and set
        our internal focus tracker to the new editor widget using track_focus().
        '''
        editor.set_text(self.tasklist[path][13])
        self.title_edit_path = path
        self.title_editor = editor
        self.track_focus(widget=editor)
        self.title_key_press_catcher = editor.connect("key-press-event", self.title_keys_dn)

    def list_edit_start(self, renderer, editor, path, model):
        '''Set up the widget for editing a list-backed field

        Our editor is given an autocomplete component backed by model. Then we
        set our internal focus tracker to the new editor using track_focus().
        '''
        completer = Gtk.EntryCompletion(model=model, popup_completion=True, inline_completion=True, inline_selection=True, popup_single_match=False, minimum_key_length=0)
        completer.set_text_column(0)
        editor.set_completion(completer)
        self.track_focus(widget=editor)

    def priority_edit_start(self, renderer, editor, path):
        '''Sets internal focus to the priority widget with track_focus()'''

        self.track_focus(widget = editor)

    def date_edit_start(self, renderer, editor, path):
        '''Sets internal focus to the date picker widget with track_focus().'''

        self.track_focus(widget = editor)

    def del_current_task(self, widget=None):
        '''Removes every selected row from the task list

        Spent time tracking is ended as needed. Parent pct complete, time spent,
        and est are recaulculated.
        '''
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
            self.commit_work(path=path, new_work=0, work_type='spent')
            self.commit_work(path=path, new_work=0, work_type='est')

            self.tasklist.remove(ref)
            self.calc_parent_pct(path)

        self.task_selected(self.selection)

    def del_task(self, path):
        '''Deletes the row at 'path'

        Ends tracking and recalculates parent time spent, est, and pct complete.
        '''
        #stop tracking if needed
        if self.tasklist[path][17]:
            self.track_action.set_active(False)
        treeiter = self.tasklist.get_iter(path)

        self.commit_work(path=path, new_work=0, work_type='spent')
        self.commit_work(path=path, new_work=0, work_type='est')
        self.tasklist.remove(treeiter)
        self.calc_parent_pct(str(path))

    def task_selected(self, widget):
        '''Stores references to the task(s) selected by the user

        Sets the correct buffer for notes editing and enables/disables row
        editing controls (cut, copy, paste, etc.) as needed.
        '''
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
        '''Handles Select All events based on the internal focus pointer

        If focus is on the task list, controls are enabled/disabled as required.

        Currently supports the task view, notes view, and all entry fields.
        '''
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
        elif type(self.focus) == Gtk.Entry:
            self.focus.select_region(0, -1)

    def select_none(self, widget=None):
        '''Handles Select None events based on the internal focus pointer

        If focus is on the task list, controls are enabled/disabled as required.

        Currently supports the task view, notes view, and all entry fields.
        '''
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
        elif type(self.focus) == Gtk.Entry:
            self.focus.select_region(0,0)

    def select_inv(self, widget=None):
        '''Inverts task selection

        All selected tasks are unselected, and all previously unselected tasks
        are selected. Uses select all or select none where possible. Otherwise
        calls __invert_tasklist_selection().
        '''
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
        '''Recursively switches each row's selected status'''

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
        '''Expands all tasks'''

        self.task_view.expand_all()

    def collapse_all(self, widget=None):
        '''Collapses all tasks'''

        self.task_view.collapse_all()

    def swap_focus(self, widget=None):
        '''Changes focus between Task list and Comments'''

        if self.notes_view.has_focus():
            self.task_view.grab_focus()
        else:
            self.notes_view.grab_focus()

    def pick_cols(self, widget=None):
        '''Changes column visibility based on the results of the column picker dialog

        New columns are always prepended.
        '''

        if self.colpicker_dlg is None:
            self.colpicker_dlg = dialogs.colpicker.main(self)
        else:
            self.colpicker_dlg.update()

        ret = self.colpicker_dlg.go()
        if ret is not None:
            collist, action = ret
            pull = [c for c in self.cols_visible if c not in set(collist)]
            push = [c for c in collist if c not in set(self.cols_visible)]
            for code in pull:
                self.task_view.remove_column(self.cols_available[code])
                self.cols_visible.remove(code)
            for code in push:
                self.task_view.insert_column(self.cols_available[code], 0)
                self.cols_visible.insert(0, code)

            if action is Gtk.ResponseType.ACCEPT:
                self.settings.set("default-columns", collist)
                self.settings.save_prefs()

    def new_file(self, widget=None):
        '''Creates a new task list

        Clears the treestore, undo/redo buffer, visible columns, assigners,
        assignees, statii, file name, etc.

        Right now, it replaces the current file without question, but in the
        future will honor a settings variable to possibly open a new window or
        tab instead.
        '''
        if not self.confirm_discard(): return

        self.tasklist.clear()

        #clear undo and redo buffers
        del self.undobuffer[:]
        del self.redobuffer[:]

        #reset to default columns
        self.cols_visible = self.settings.get("default-columns")
        self.display_columns(self.cols_visible)

        #reset to default assigners, assignees, and statii
        self.assigners_list = self.settings.get("default-from")[:]
        self.assignees_list = self.settings.get("default-to")[:]
        self.statii_list = self.settings.get("default-status")[:]

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
        '''Prompts the user the choose a file to load

        Uses __do_open() to read the file once it's known.
        '''
        if not self.confirm_discard(): return

        retcode = self.open_dlg.run()
        self.open_dlg.hide()
        if retcode != -3: return #cancel out if requested

        self.file_name = self.open_dlg.get_filename()
        self.file_filter = self.save_dlg.get_filter()
        self.__do_open()

    def open_recent(self, widget):
        '''Opens a file from the Recent Files widget

        Saves file information and calls __do_open() for the real work.
        '''
        if not self.confirm_discard(): return

        uri = widget.get_current_uri()
        fpath = urlparse(uri).path
        self.file_name = unquote(fpath)
        self.file_filter = fileParser.pick_filter(fpath)
        self.__do_open()

    def __open_last(self):
        '''Opens the most recently used file

        Meant to be run at the end of __init__()
        '''

        retval = self.recent_files.get_uris()
        if retval == []: return
        if retval[0] == []: return
        uri = retval[0]
        fpath = urlparse(uri).path
        self.file_name = unquote(fpath)
        self.file_filter = fileParser.pick_filter(fpath)
        self.__do_open()

    def __do_open(self):
        '''Loads the file at self.file_name using the reader self.file_filter

        We let self.file_filter process the file and put its data into a dict.
        Save version is checked for compatability and then we use that dict to
        populate our real internal vars.
        '''
        templist = tools.copy_treemodel(self.tasklist)
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
        try:
            self.file_filter.read_to_store(data)
        except (ParseError, IOError, ReadError, KeyError):
            dlg = dialogs.misc.htd_file_read_error(self, self.file_name)
            dlg.run()
            dlg.destroy()
            return

        #check version compatability
        file_version = data['save_version']
        native_version = data['our_version']
        force_save = False
        if native_version < file_version:
            response = self.version_warn_dlg.run()
            self.version_warn_dlg.hide()
            if response == 2:
                data['filename'] = self.pick_savefile()
                force_save = True
            elif response == Gtk.ResponseType.CANCEL:
                return

        self.file_name = data['filename']
        self.assigners_list = data['from_list']
        self.assignees_list = data['to_list']
        self.statii_list = data['status_list']
        #self.tasklist is handled later
        cols = data['cols']
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
        templist.foreach(tools.append_row, self.tasklist)
        del templist

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
        self.cols_visible = [n for n, v in cols if v]
        self.display_columns(self.cols_visible)

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
        '''Prompts the user to pick a save location

        The chosen extension is added automatically if the user left it out and
        the resulting full path is returned.
        '''
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
        '''Prompts user for a save location using pick_savefile() and then saves
        there using __do_save()

        The location is preserved for future saves.
        '''
        self.file_name = self.pick_savefile()
        self.__do_save(self.file_name, self.tasklist)

    def save_file(self, widget=None):
        '''Writes the current list to the saved file location

        If we don't have a location yet, the user is prompted to choose one.
        '''
        if self.file_name == "":
            self.save_file_as()
            return

        self.__do_save(self.file_name, self.tasklist)

    def save_copy(self, widget=None):
        '''Prompts user for a save location using pick_savefile() and then saves
        there using __do_save()

        Unlike save_file_as(), the location is NOT preserved for future saves.
        '''
        filename = self.pick_savefile()
        self.__do_save(filename, self.tasklist)

    def __do_save(self, filename, tasklist, append=False, file_filter=None):
        '''Writes our data to the file at 'filename'

        The data is bundled into a dict and all the writing is handled by a
        filter from file_parsers.
        '''
        if file_filter is None: file_filter = fileParser.pick_filter(filename)

        if tasklist is self.tasklist and self.seliter is not None:
            selpath = tasklist.get_path(self.seliter).to_string()
        else:
            selpath = ''

        # get window geometry bits
        width, height = self.get_size()
        task_width = width - self.task_pane.get_position()

        # derive column visibility
        present = [(col.code, True) for col in self.task_view.get_columns()]
        absent = [(code, False) for code in self.cols_available.keys() if (code, True) not in present]

        data = {
            'filename': filename,
            'from_list': sorted(self.assigners_list),
            'to_list': sorted(self.assignees_list),
            'status_list': sorted(self.statii_list),
            'task_store': tasklist,
            'task_view': self.task_view,
            'selection': selpath,
            'cols': present+absent,
            'geometry': (self.maximized, width, height, task_width)
        }
        try:
            file_filter.write(data, append)
        except IOError:
            self.save_warn_dlg.run()
            return

        self.file_dirty = False
        self.update_title()
        self.last_save = datetime.now()

    def confirm_discard(self):
        '''Warns the user about discarding changes

        Saves with save_file() if that option is chosen.

        Returns True if the user wants to discard their changes, and False otherwise.
        '''
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
        '''Marks data as unsaved and changes the title to reflect this using update_title()'''

        self.file_dirty = True
        self.update_title()

    def update_title(self):
        '''Updates the window's title to reflect the current file's name, path,
        and dirty state'''

        if self.file_name != "":
            ttl = "%s (%s) - HiToDo" % (basename(self.file_name), dirname(self.file_name))
        else:
            ttl = "Untitled List - HiToDo"

        self.title = "*"+ttl if self.file_dirty else ttl

        self.set_title(self.title)

    def show_about(self, widget=None):
        '''Shows the About dialog'''

        if self.about_dlg is None:
            self.about_dlg = dialogs.misc.htd_about(self)

        self.about_dlg.run()
        self.about_dlg.hide()

    def set_prefs(self, widget=None):
        '''Shows the settings module's own preferences dialog'''

        self.settings.show_dialog(self)

    def do_cut(self, widget=None):
        '''Applies cut operation depending on current internal focus

        For notes or title, the 'cut-clipboard' signal is emitted. For the task
        list, __do_copy_real() is used and the rows are deleted.
        '''
        if self.focus == self.notes_view or (self.title_editor is not None and self.focus == self.title_editor):
            self.focus.emit('cut-clipboard')
        elif self.focus == self.task_view:
            if self.sellist is None: return
            row_texts = self.__do_copy_real(self.sellist, self.copied_rows)
            self.clipboard.set_text("\n".join(row_texts), -1)
            self.del_current_task() #this also pushes an undo action

    def do_copy(self, widget=None):
        '''Applies copy operation depending on current internal focus

        For notes or title, the 'copy-clipboard' signal is emitted. For the task
        list, __do_copy_real() is used.
        '''
        if self.focus == self.notes_view or (self.title_editor is not None and self.focus == self.title_editor):
            self.focus.emit('copy-clipboard')
        elif self.focus == self.task_view:
            if self.sellist is None: return
            row_texts = self.__do_copy_real(self.sellist, self.copied_rows)
            self.clipboard.set_text("\n".join(row_texts), -1)

    def __do_copy_real(self, subject, rowlist, recurse=True):
        '''Stores shallow copies of selected rows and their children to rowlist

        Returns list of row titles for clipboard use. Uses __copy_children() for
        recursion when flag is set.
        '''
        row_texts = []
        del rowlist[:]
        for path in subject:
            row_texts.append(self.tasklist[path][13])
            # We store a parent reference along with each row's data. At the top
            # level, that reference is obviously nothing, but children refer to
            # their parent iters to maintain the tree.
            rowlist.append(self.tasklist[path][:])
            treeiter = self.tasklist.get_iter(path)
            if recurse:
                rowlist[-1].append(self.__copy_children(treeiter))
        return row_texts

    def __copy_children(self, treeiter):
        '''Makes shallow copies of the children of treeiter

        Iterates through treeiter's children and copies their data to
        a list. Recurses automatically to children's children.

        Returns a list of children.
        '''

        children = []

        child_iter = self.tasklist.iter_children(treeiter)
        while child_iter != None:
            children.append(self.tasklist[child_iter][:]) # append the child
            children[-1].append(self.__copy_children(child_iter)) # stick a list of its children on the end
            child_iter = self.tasklist.iter_next(child_iter) # move to the next child

        return children

    def do_paste(self, widget=None):
        '''Applies paste operation depending on current internal focus

        For notes or title, the 'paste-clipboard' signal is emitted. For the
        task list, new rows are created after the current row and populated with
        data from our internal 'clipboard' of rows using __do_paste_real().
        '''
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

            self.selection.unselect_all()
            self.selection.select_iter(new_iters[0])

    def __do_paste_real(self, parent_iter, sibling_iter, row_data, sanitize=True):
        '''Creates new rows and populates them with data from the internal clipboard

        If sanitize is True, the data is first filtered to remove done
        state, completion date, etc. as these are often undesirable in pasted
        rows. Setting that flag to false forces all row data to be copied
        verbatim, which is good when dealing with undo/redo operations.
        '''
        new_iters = []

        #iterate row data and add it
        for row in row_data:
            new_row = self.defaults[:]
            if sanitize:
                inherit = [0,4,5,8,9,10,11,13,14] #columns to preserve from original row
                for i in inherit:
                    new_row[i] = row[i]
            else:
                for i in range(len(self.defaults)):
                    new_row[i] = row[i]

            #add the new row with its data
            treeiter = self.tasklist.insert_after(parent_iter, sibling_iter, new_row)
            new_iters.append(treeiter)

            if row[-1]:
                self.__do_paste_real(treeiter, None, row[-1], sanitize)

            sibling_iter = treeiter # next row should be our sibling

            #update time est and percent separately
            path = self.tasklist.get_path(treeiter)
            self.commit_work(path=path, new_work=row[2]/3600, work_type='est')
            self.calc_parent_pct(path.to_string())

        self.make_dirty()
        return new_iters

    def do_paste_into(self, widget=None):
        '''Pastes rows underneath current selection'''

        if self.focus != self.task_view: return
        if self.seliter is None: return

        new_iters = self.__do_paste_real(self.seliter, None, self.copied_rows)

        #push "paste" undo
        ppath = self.sellist[0]
        self.__push_undoable("paste", (ppath, None, self.copied_rows[:], new_iters))

        self.task_view.expand_to_path(self.tasklist.get_path(new_iters[0]))
        self.selection.unselect_all()
        self.selection.select_iter(new_iters[0])
        self.make_dirty()

    def do_undo(self, widget=None):
        '''Handles undo logic

        For the notes entry, it just calls that object's own undo() function
        (see undobuffer module). For the task list, it relies on a list of
        undoable actions pushed by every function which supports undo (see
        __push_undoable()). Each action has its own undo procedure.
        '''
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
                self.commit_work(path=path, new_work=oldval/3600, work_type='spent')
                self.redobuffer.append(action)
            elif action[0] == "est":
                path = action[1][0]
                oldval = action[1][1]
                self.commit_work(path=path, new_work=oldval/3600, work_type='est')
                self.redobuffer.append(action)
            elif action[0] == "done":
                path = action[1][0]
                oldval = action[1][1]
                forced = action[1][3]

                if oldval:
                    # we're undoing a move from done to not-done

                    # mark path done
                    self.tasklist[path][1] = 100
                    self.tasklist[path][12] = True
                    self.tasklist[path][16] = False

                    # mark forced rows done
                    for row in forced:
                        self.tasklist[row][12] = True
                        self.tasklist[row][16] = False
                else:
                    # we're undoing a move from not-done to done

                    # mark path Not Done
                    self.tasklist[path][12] = False
                    self.tasklist[path][16] = True

                    # mark forced rows Not Done
                    for row in forced:
                        self.tasklist[row][1] = 0
                        self.tasklist[row][12] = False
                        self.tasklist[row][16] = True

                    # recalc self pct complete
                    self.calc_pct(path)

                self.calc_parent_pct(path)

                self.redobuffer.append(action)
            elif action[0] == "paste":
                data = action[1]
                for treeiter in data[3]:
                    #ensure we aren't tracking anything
                    if self.tasklist[treeiter][17]:
                        self.track_action.set_active(False)

                    path = self.tasklist.get_path(treeiter)
                    self.commit_work(path=path, new_work=0, work_type='est')
                    self.commit_work(path=path, new_work=0, work_type='spent')
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
            elif action[0] == 'track_spent':
                path = action[1][0]
                self.tasklist[path][17] = False
                self.tracking = None
                self.track_action.set_active(False)
                self.redobuffer.append(('track_spent', (str(path))))

    def do_redo(self, widget=None):
        '''Handles redo logic

        For the notes entry, it just calls that object's own redo() function
        (see undobuffer module). For the task list, it relies on a list of
        redoable actions pushed by every function which supports redo (see
        __push_undoable()). Each action has its own redo procedure.
        '''
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
                self.commit_work(path=path, new_work=newval/3600, work_type='spent')
                self.undobuffer.append(action)
            elif action[0] == "est":
                path = action[1][0]
                newval = action[1][2]
                self.commit_work(path=path, new_work=newval/3600, work_type='est')
                self.undobuffer.append(action)
            elif action[0] == "done":
                path = action[1][0]
                newval = action[1][1]
                self.commit_done(path = path, new_done = not newval)

                self.undobuffer.append(action)
            elif action[0] == "paste":
                data = action[1]
                parent_iter = self.tasklist.get_iter(data[0]) if data[0] is not None else None
                sibling_iter = self.tasklist.get_iter(data[1]) if data[1] is not None else None
                new_iters = self.__do_paste_real(parent_iter, sibling_iter, data[2])

                self.task_view.expand_to_path(self.tasklist.get_path(new_iters[0]))
                self.selection.unselect_all()
                self.selection.select_iter(new_iters[0])

                self.undobuffer.append(("paste", (data[0], data[1], data[2], new_iters)))
            elif action[0] == "del":
                data = action[1]
                for treeiter in data[3]:
                    #ensure we aren't tracking anything
                    if self.tasklist[treeiter][17]:
                        self.track_action.set_active(False)

                    path = self.tasklist.get_path(treeiter)
                    self.commit_work(path=path, new_work=0, work_type='est')
                    self.commit_work(path=path, new_work=0, work_type='spent')
                    self.tasklist.remove(treeiter)

                #update parent pct done
                if data[0] is not None:
                    self.calc_pct(data[0])

                self.undobuffer.append(("del", (data[0], data[1], data[2])))
            elif action[0] == 'track_spent':
                path = action[1][0]
                self.track_spent(self.track_action, path, True)
                self.track_action.set_active(True)
                self.undobuffer.append(('track_spent', (str(path))))

    def __push_undoable(self, action, data):
        '''Pushes a tuple onto the undobuffer list

        The data tuple must consist of the action name and related data. The
        name must be recognized by do_undo() and do_redo().
        '''
        self.undobuffer.append((action, data))
        del self.redobuffer[:]

    def display_columns(self, cols=None):
        '''Clears the currently displayed columns and loads the ones in
        self.cols_visible

        Order is honored.
        '''
        if cols is None:
            cols = self.cols_visible

        #clear current cols
        for col in self.task_view.get_columns():
            self.task_view.remove_column(col)

        #add columns in order specified
        for col in cols:
            self.task_view.append_column(self.cols_available[col])

        #mark new visibilities
        for row in self.cols:
            row[2] = row[0] in cols

        #ensure the title column always expands to show children
        self.task_view.set_properties(expander_column=self.cols_available['title'])

    def notes_keys_dn(self, widget=None, event=None):
        '''Catches key-down events in the notes editor to enable custom actions

        Currently it tracks the status of the Control_* and Enter keys. When
        Control+Enter appear together, the contents of the editor are saved.
        '''
        kvn = Gdk.keyval_name(event.keyval)
        if kvn == "Control_L" or kvn == "Control_R":
            self.notes_ctl_mask = True
        if kvn == "Return" and self.notes_ctl_mask:
            self.commit_notes()
            self.notes_ctl_mask = False
            return True

    def notes_keys_up(self, widget=None, event=None):
        '''Catches key-up events in the notes editor

        Used to clear the Control-key state mask.
        '''
        kvn = Gdk.keyval_name(event.keyval)
        if kvn == "Control_L" or kvn == "Control_R":
            self.notes_ctl_mask = False

    def tasks_keys_dn(self, widget=None, event=None):
        '''Catches key-down events for the task list

        Allows us to bind the Delete key to del_current_task() and force F2 to
        begin editing the current row's title.
        '''
        kvn = Gdk.keyval_name(event.keyval)
        if kvn == "Delete":
            self.del_current_task()
            return True
        if kvn == "F2":
            path = self.tasklist.get_path(self.seliter)
            self.task_view.set_cursor_on_cell(path, self.col_title, self.title_cell, True)
            return True
        # NOTE We can override the spacebar to always mark/unmark our Done flag, but this breaks keyboard navigation
        # if kvn == "space":
        #     path = self.tasklist.get_path(self.seliter)
        #     self.commit_done(path = str(path), new_done = not self.tasklist[path][12])
        #     return True

    def title_keys_dn(self, widget=None, event=None):
        '''Catches key-down events for the task title editor

        Lets us cancel in-progress edits when the Escape key is pressed.
        '''
        kvn = Gdk.keyval_name(event.keyval)
        if kvn == "Escape":
            # widget.emit('editing-canceled')
            self.commit_title(path=self.title_edit_path, new_title='')

    def tasks_mouse_click(self, widget=None, event=None):
        '''Catches mouse clicks for the task list

        Used to show the context menu on a right-click.
        '''
        if event.button == 3 and event.type == Gdk.EventType.BUTTON_PRESS:
            self.task_popup.show_all()
            self.task_popup.popup(None, None,
                lambda menu, data: (
                    event.get_root_coords()[0],
                    event.get_root_coords()[1], True),
                None, event.button, event.time)
            return True

    def track_maximized(self, widget, event, data=None):
        '''Tracks the window's maximized state

        We store this as part of the window geometry in save files.
        '''
        mask = Gdk.WindowState.MAXIMIZED
        self.maximized = (widget.get_window().get_state() & mask) == mask

    def edit_assigners(self, widget, data=None):
        '''Assigners wrapper for the label edit dialog'''

        self.label_edit_dlg.set_title("Manage Assigners (From)")
        self.label_edit_dlg.set_frame_label("Manage Assigners")
        self.label_edit_dlg.set_store(self.assigners)
        self.label_edit_dlg.set_list(self.assigners_list)
        self.label_edit_dlg.set_instructions("Assigners", "From")
        self.label_edit_dlg.set_pref('default-from')
        ret = self.label_edit_dlg.show_all()

    def edit_assignees(self, widget, data=None):
        '''Assignees wrapper for the label edit dialog'''

        self.label_edit_dlg.set_title("Manage Assignees (To)")
        self.label_edit_dlg.set_frame_label("Manage Assignees")
        self.label_edit_dlg.set_store(self.assignees)
        self.label_edit_dlg.set_list(self.assignees_list)
        self.label_edit_dlg.set_instructions("Assignees", "To")
        self.label_edit_dlg.set_pref('default-to')
        ret = self.label_edit_dlg.run()

    def edit_statii(self, widget, data=None):
        '''Status wrapper for the label edit dialog'''

        self.label_edit_dlg.set_title("Manage Status Labels")
        self.label_edit_dlg.set_frame_label("Manage Status Labels")
        self.label_edit_dlg.set_store(self.statii)
        self.label_edit_dlg.set_list(self.statii_list)
        self.label_edit_dlg.set_instructions("Status labels", "Status")
        self.label_edit_dlg.set_pref('default-status')
        ret = self.label_edit_dlg.run()

    def main_filter(self, model, treeiter, data=None):
        '''Task list filtering function'''

        # TODO implement me
        return True

    def archive_done(self, widget, data=None):
        '''Saves top-level done tasks (and descendents) to a separate archive
        file, then deletes them'''

        # show the export dialog
        dlg = dialogs.misc.htd_warn_archive(self)
        retval = dlg.run()
        dlg.destroy()

        if retval == -3:
            #do the archive operation

            # archive filename is our path + _archive + ext
            bits = splitext(self.file_name)
            archive_path = bits[0]+'_archive'+bits[1]

            # disable signals while we make big changes to the model
            self.task_view.freeze_child_notify()

            # set up a filter for our Done entries
            archive_filter = self.tasklist.filter_new(None)
            archive_filter.set_visible_column(12)

            # append to the selected file
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

    def toggle_toolbar(self, widget=None, event=None):
        '''Toggles visibility of the toolbar'''

        vis = widget.get_active()
        self.toolbar.set_visible(vis)
        self.settings.set('show-toolbar', vis)

    def toggle_reopen(self, widget=None, event=None):
        '''Toggles the "open last used file on start" flag'''

        vis = widget.get_active()
        self.settings.set('reopen', vis)
        self.settings.save_prefs()

    def __init__(self):
        '''Program setup and initialization.

        Initializes internal variables and constructs the UI with some helper
        functions.
        '''
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
        self.tasklist.set_sort_func(4, self.datecompare, None)
        self.tasklist.set_sort_func(5, self.datecompare, None)
        self.tasklist.set_sort_func(6, self.datecompare, None)
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

        self.work_cols = {
            'est': 2,
            'spent': 3
        }

        self.assigners = Gtk.ListStore(str)
        self.assigners.set_sort_column_id(0, Gtk.SortType.ASCENDING)
        self.assigners_list = []
        self.assignees = Gtk.ListStore(str)
        self.assignees.set_sort_column_id(0, Gtk.SortType.ASCENDING)
        self.assignees_list = []
        self.statii = Gtk.ListStore(str)
        self.statii.set_sort_column_id(0, Gtk.SortType.ASCENDING)
        self.statii_list = []
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
        self.cols = Gtk.ListStore(str, str, bool, bool) #code, label for settings screen, visible flag, can hide flag
        self.undobuffer = []
        self.redobuffer = []
        self.maximized = False

        #construct settings object and changed::* bindings
        self.settings = settings.settings(self)
        self.cols_visible = self.settings.get("default-columns")

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
        self.task_view = Gtk.TreeView()
        self.task_view.set_model(self.tasklist_filter)

        #set up columns
        self.create_columns()
        self.display_columns(self.cols_visible)

        #set up selection handling and add the completed table widget
        self.selection = self.task_view.get_selection()
        self.selection.set_mode(Gtk.SelectionMode.MULTIPLE)
        self.sel_changed_handler = self.selection.connect("changed", self.task_selected)
        self.task_view.set_properties(enable_tree_lines=True, reorderable=False, enable_search=True, search_column=13, rules_hint=True)
        # TODO think about allowing and tracking reorder in the future
        # if it's turned back on, we need to track drag and drop via:
        #   drag flag turned on when mouse is held down and we catch a row-deleted signal
        #   drop undoable pushed when drag flag is on and we catch a row-inserted signal
        #   while drag flag is on:
        #       block Delete key
        #       Escape key sets drag flag off
        self.task_view.connect('key-press-event', self.tasks_keys_dn)
        self.task_view.connect('focus-in-event', self.track_focus)
        self.task_view.connect('button-press-event', self.tasks_mouse_click)
        task_scroll_win.add(self.task_view)
        self.task_pane.pack1(task_scroll_win, True, True)

        #add notes area
        notes_box = Gtk.Frame()
        notes_box.set_shadow_type(Gtk.ShadowType.NONE)
        notes_lbl = Gtk.Label()
        notes_lbl.set_markup("<b>_Comments</b>")
        notes_lbl.set_property("use-underline", True)
        notes_box.set_label_widget(notes_lbl)

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

        notes_box.add(notes_scroll_win)
        self.task_pane.pack2(notes_box, True, True)

        #commit the task editing pane
        main_box.pack_start(self.task_pane, True, True, 0)

        #commit the ui
        self.add(main_box)

        # create a clipboard for easy copying
        self.clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        self.connect("delete-event", self.destroy)
        self.connect("window-state-event", self.track_maximized)
        self.show_all()

        # now we can hide or show the toolbar as desired
        self.toolbar.set_visible(self.settings.get("show-toolbar"))

        # set up our dialogs
        self.open_dlg = dialogs.misc.htd_open(self)
        self.save_dlg = dialogs.misc.htd_save(self)
        self.label_edit_dlg = dialogs.labeledit.main(self)
        self.version_warn_dlg = dialogs.misc.htd_version_warning(self)
        self.save_warn_dlg = dialogs.misc.htd_file_write_error(self)
        # create as needed later
        self.about_dlg = None
        self.colpicker_dlg = None

        # if a filename was given on the command line, open it
        if len(sys.argv) >= 2:
            self.file_name = unquote(sys.argv[1])
            self.file_filter = fileParser.pick_filter(sys.argv[1])
            self.__do_open()
            return

        # open last file if requested
        if self.settings.get("reopen"):
            self.__open_last()

    def date_render(self, col, cell, model, tree_iter, data):
        '''Renders date cells

        Converts datetime objects from the tasklist model to displayable strings.
        '''
        val = model[tree_iter][data]
        duetime = model[tree_iter][15]

        fmt = "%x %X" if duetime else "%x"
        out = "" if val is "" else val.strftime(fmt)
        cell.set_property("text", str(out))

    def datecompare(self, model, row1, row2, data=None):
        '''Sorts date cells

        Compares datetime objects from two rows.
        '''
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
        '''Render title and notes together

        Eliminates line breaks in notes so that no task entry takes up multiple lines.
        '''
        text = model[tree_iter][13]
        notes = model[tree_iter][14]
        out = escape(text) if notes == '' else "%s  <span color=\"#999\">[%s]</span>" % (escape(text), escape(notes.replace(linesep, ' ')))
        cell.set_property("markup", out)

    def work_render(self, col, cell, model, tree_iter, data):
        '''Render est and spent cells

        Converts stored seconds into hours or minutes with a suffix.
        '''
        val = model[tree_iter][data]

        if val == 0:
            out = ''
            tip = '';
        else:
            minutes = '%im' % round(val / 60)
            hours = '%1.2fh' % (val/3600)
            days = '%1.2fd' % (val/86400)
            if val < 3600:
                out = minutes
            else:
                out = hours
            tip = "Minutes: "+minutes+"\nHours: "+hours+"\nDays: "+days
            # TODO use this for tooltip text, somehow
        cell.set_property("text", out)

    def create_columns(self):
        '''Creates the columns used by the task list view'''

        priority = Gtk.CellRendererText(editable=True, foreground="#999")
        priority.connect("edited", self.commit_priority)
        priority.connect("editing-started", self.priority_edit_start)
        col_priority = Gtk.TreeViewColumn("!", priority, text=0, foreground_set=12)
        col_priority.set_sort_column_id(0)
        col_priority.set_reorderable(True)
        col_priority.code = "priority"
        self.cols_available['priority'] = col_priority
        self.cols.append(['priority', 'Priority (!)', True, True])

        pct = Gtk.CellRendererProgress()
        col_pct = Gtk.TreeViewColumn("%", pct, value=1, visible=16)
        col_pct.set_reorderable(True)
        col_pct.set_sort_column_id(1)
        col_pct.code = "pct complete"
        self.cols_available['pct complete'] = col_pct
        self.cols.append(['pct complete', 'Percent Complete (%)', True, True])

        est = Gtk.CellRendererText(foreground="#999", editable=True)
        est.connect("edited", self.save_work, 'est')
        est.connect("editing-started", self.duration_edit_start, 2)
        col_est = Gtk.TreeViewColumn("Est", est, foreground_set=12)
        col_est.set_reorderable(True)
        col_est.set_sort_column_id(2)
        col_est.set_cell_data_func(est, self.work_render, 2)
        col_est.code = "time est"
        self.cols_available['time est'] = col_est
        self.cols.append(['time est', 'Est', True, True])

        spent = Gtk.CellRendererText(foreground="#999", editable=True)
        spent.connect("edited", self.save_work, 'spent')
        spent.connect("editing-started", self.duration_edit_start, 3)
        col_spent = Gtk.TreeViewColumn("Spent", spent, foreground_set=12)
        col_spent.set_reorderable(True)
        col_spent.set_sort_column_id(3)
        col_spent.set_cell_data_func(spent, self.work_render, 3)
        col_spent.code = "time spent"
        self.cols_available['time spent'] = col_spent
        self.cols.append(['time spent', 'Spent', True, True])

        tracking = Gtk.CellRendererText(foreground="#b00", text=u"\u231A")
        col_tracking = Gtk.TreeViewColumn(u"\u231A", tracking, visible=17)
        col_tracking.set_reorderable(True)
        col_tracking.code = "tracked"
        self.cols_available['tracked'] = col_tracking
        self.cols.append(['tracked', u'Tracking (\u231A)', True, True])

        est_begin = widgets.CellRendererDate(editable=True, foreground="#999")
        est_begin.connect("edited", self.commit_date, 4)
        est_begin.connect("editing-started", self.date_edit_start)
        col_est_begin = Gtk.TreeViewColumn("Est Begin", est_begin, foreground_set=12)
        col_est_begin.set_reorderable(True)
        col_est_begin.set_sort_column_id(4)
        col_est_begin.set_cell_data_func(est_begin, self.date_render, 4)
        col_est_begin.code = "est begin"
        self.cols_available['est begin'] = col_est_begin
        self.cols.append(['est begin', 'Est Begin', False, True])

        est_complete = widgets.CellRendererDate(editable=True, foreground="#999")
        est_complete.connect("edited", self.commit_date, 5)
        est_complete.connect("editing-started", self.date_edit_start)
        col_est_complete = Gtk.TreeViewColumn("Est Complete", est_complete, foreground_set=12)
        col_est_complete.set_reorderable(True)
        col_est_complete.set_sort_column_id(5)
        col_est_complete.set_cell_data_func(est_complete, self.date_render, 5)
        col_est_complete.code = "est begin"
        self.cols_available['est complete'] = col_est_complete
        self.cols.append(['est complete', 'Est Complete', False, True])

        due = widgets.CellRendererDate(editable=True, foreground="#999")
        due.connect("edited", self.commit_date, 8)
        due.connect("editing-started", self.date_edit_start)
        col_due = Gtk.TreeViewColumn("Due", due, foreground_set=12)
        col_due.set_reorderable(True)
        col_due.set_sort_column_id(8)
        col_due.set_cell_data_func(due, self.date_render, 8)
        col_due.code = "due date"
        self.cols_available['due date'] = col_due
        self.cols.append(['due date', 'Due', True, True])

        act_begin = widgets.CellRendererDate(editable=True, foreground="#999")
        act_begin.connect("edited", self.commit_date, 6)
        act_begin.connect("editing-started", self.date_edit_start)
        col_act_begin = Gtk.TreeViewColumn("Begin", act_begin, foreground_set=12)
        col_act_begin.set_reorderable(True)
        col_act_begin.set_sort_column_id(6)
        col_act_begin.set_cell_data_func(act_begin, self.date_render, 6)
        col_act_begin.code = "act begin"
        self.cols_available['act begin'] = col_act_begin
        self.cols.append(['act begin', 'Begin', False, True])

        completed = widgets.CellRendererDate(editable=True, foreground="#999")
        completed.connect("edited", self.commit_date, 7)
        completed.connect("editing-started", self.date_edit_start)
        col_completed = Gtk.TreeViewColumn("Completed", completed, foreground_set=12, visible=12)
        col_completed.set_reorderable(True)
        col_completed.set_sort_column_id(7)
        col_completed.set_cell_data_func(completed, self.date_render, 7)
        col_completed.code = "complete date"
        self.cols_available['complete date'] = col_completed
        self.cols.append(['complete date', 'Completed', True, True])

        assigner = Gtk.CellRendererText(editable=True, foreground="#999")
        assigner.connect("edited", self.commit_assigner)
        assigner.connect("editing-started", self.list_edit_start, self.assigners)
        col_assigner = Gtk.TreeViewColumn("From", assigner, text=9, foreground_set=12)
        col_assigner.set_reorderable(True)
        col_assigner.set_sort_column_id(9)
        col_assigner.code = "from"
        self.cols_available['from'] = col_assigner
        self.cols.append(['from', 'From', True, True])

        assignee = Gtk.CellRendererText(editable=True, foreground="#999")
        assignee.connect("edited", self.commit_assignee)
        assignee.connect("editing-started", self.list_edit_start, self.assignees)
        col_assignee = Gtk.TreeViewColumn("To", assignee, text=10, foreground_set=12)
        col_assignee.set_reorderable(True)
        col_assignee.set_sort_column_id(10)
        col_assignee.code = "to"
        self.cols_available['to'] = col_assignee
        self.cols.append(['to', 'To', True, True])

        status = Gtk.CellRendererText(editable=True, foreground="#999")
        status.connect("edited", self.commit_status)
        status.connect("editing-started", self.list_edit_start, self.statii)
        col_status = Gtk.TreeViewColumn("Status", status, text=11, foreground_set=12)
        col_status.set_reorderable(True)
        col_status.set_sort_column_id(11)
        col_status.code = "status"
        self.cols_available['status'] = col_status
        self.cols.append(['status', 'Status', True, True])

        done = Gtk.CellRendererToggle(activatable=True, radio=False)
        done.connect("toggled", self.commit_done)
        col_done = Gtk.TreeViewColumn(u"\u2713", done, active=12)
        col_done.set_sort_column_id(12)
        col_done.set_reorderable(True)
        col_done.code = "done"
        self.cols_available['done'] = col_done
        self.cols.append(['done', u'Done (\u2713)', True, False])

        self.title_cell = Gtk.CellRendererText(editable=True, ellipsize=Pango.EllipsizeMode.MIDDLE, foreground="#999")
        self.title_cell.connect("edited", self.commit_title)
        self.title_cell.connect("editing-started", self.title_edit_start)
        self.title_cell.connect("editing-canceled", self.commit_title, None, None)
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
        '''Creates application-wide actions for UI menus and buttons'''

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
            # ("doc_props", Gtk.STOCK_PROPERTIES, "_Document Properties", None, None, self.set_docprops),
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
        self.toolbar_action.set_active(self.settings.get("show-toolbar"))
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

        self.reopen_action = Gtk.ToggleAction("toggle_reopen", "_Reopen last file on start", "Reopen the last used file on program startup", None)
        self.reopen_action.set_active(self.settings.get("reopen"))
        self.reopen_action.connect("activate", self.toggle_reopen)
        action_group.add_action(self.reopen_action)

        save_file = Gtk.Action("save_file", None, "Save task list", Gtk.STOCK_SAVE)
        save_file.connect("activate", self.save_file)
        save_file.set_is_important(True)
        action_group.add_action_with_accel(save_file, None)


    def create_task_actions(self, action_group):
        '''Creates task-specific actions for UI menus and buttons'''

        action_group.add_actions([
            ("task_newsub", Gtk.STOCK_INDENT, "New S_ubtask", "<Primary><Shift>N", "Add a new subtask", self.add_subtask),
            ("sel_all", Gtk.STOCK_SELECT_ALL, None, "<Primary>A", None, self.select_all),
            ("sel_inv", None, "_Invert Selection", None, None, self.select_inv),
            ("sel_none", None, "Select _None", "<Primary><Shift>A", None, self.select_none),
            ("expand_all", None, "_Expand All", None, "Expand all tasks", self.expand_all),
            ("collapse_all", None, "_Collapse All", None, "Collapse all tasks", self.collapse_all),
            ("swap_focus", None, "Swap _Focus", "F11", "Change focus between Tasks and Comments", self.swap_focus),
            ("pick_cols", None, "_Show Columns...", None, "Choose which columns are visible", self.pick_cols)
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
        '''Constructs a ui manager, complete with accelerator group'''

        uimanager = Gtk.UIManager()

        # Throws exception if something went wrong
        uimanager.add_ui_from_string(UI_XML)

        # Add the accelerator group to the toplevel window
        accelgroup = uimanager.get_accel_group()
        self.add_accel_group(accelgroup)
        return uimanager

    def destroy(self, widget=None, data=None):
        '''Shows the 'confirm discard' dialog before closing, if applicable'''

        if not self.confirm_discard(): return True
        self.settings.save_prefs()
        Gtk.main_quit()

def main():
    '''Starts the Gtk main loop'''

    Gtk.main()
    return

if __name__ == "__main__":
    htd = HiToDo()
    main()
