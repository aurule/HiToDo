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

from gi.repository import Gtk
from xml.etree import ElementTree
from xml.etree.ElementTree import Element
from xml.etree.ElementTree import SubElement
from dateutil.parser import parse as dateparse
from datetime import datetime
from os.path import splitext

def pick_filter(file_name):
    ext = splitext(file_name)[1]
    if ext == '.htdl':
        f = htd_filter()
        return f

class htd_filter(Gtk.FileFilter):
    def __init__(self):
        Gtk.FileFilter.__init__(self)
        self.add_pattern("*.htdl")
        self.set_name("HiToDo Files (*.htdl)")
        self.file_extension = ".htdl"
        self.tasks = None
    
    def read_to_store(self, fname, froms, tos, stats, taskstore):
        '''Reads todo list data from xml file. Args:
* fname is the file's path
* froms is a list where assigner strings will be stored
* tos is a list where assignee strings will be stored
* stats is a list where status strings will be stored
* taskstore is a GtkTreeStore which will be populated from tasks in the file'''
        document = ElementTree.parse(fname)
        
        #get assigners, assignees, and statii lists
        assigners = document.find("assigners")
        for n in assigners.findall('name'):
            if n.text not in froms:
                froms.append(n.text)
        assignees = document.find("assignees")
        for n in assignees.findall('name'):
            if n.text not in tos:
                tos.append(n.text)
        statii = document.find("statii")
        for n in statii.findall('name'):
            if n.text not in stats:
                stats.append(n.text)
        
        #get highest-level tasklist element
        tasklist = document.find("tasklist")
        self.tasks = taskstore #store for use later
        self.__read_tasks(tasklist, None)
        
        exp = document.find('expanded')
        ret = []
        for n in exp.findall('path'):
            ret.append(n.text)
        seldata = document.find('selected')
        sel = seldata.text
        
        return (ret, sel)
    
    def __read_tasks(self, tasklist, parent=None):
        '''Internal function to recursively add tasks from an XML file to the treestore self.tasks.'''
        for task in tasklist.iterfind('./task'):
            #make a list from subelements and attributes to add to the treestore
            tlist = []
            tlist.append(int(task.get('priority')))
            tlist.append(int(task.find('pct').text))
            tlist.append(int(task.find('est').text))
            tlist.append(int(task.find('spent').text))
            tlist.append(None) #est begin
            tlist.append(None) #est complete
            tlist.append(None) #act begin
            completed_raw = task.find('completed').text
            if completed_raw is None:
                tlist.append(None)
            else:
                tlist.append(dateparse(completed_raw))
            due_raw = task.find('due').text
            if due_raw is None:
                tlist.append(None)
            else:
                tlist.append(dateparse(due_raw))
            assigner_raw = task.find('assigner').text
            if assigner_raw is None: assigner_raw = ''
            tlist.append(assigner_raw)
            assignee_raw = task.find('assignee').text
            if assignee_raw is None: assignee_raw = ''
            tlist.append(assignee_raw)
            status_raw = task.find('status').text
            if status_raw is None: status_raw = ''
            tlist.append(status_raw)
            done = task.get('done') == "True"
            tlist.append(done)
            tlist.append(task.find('title').text)
            notes_raw = task.find('notes').text
            if notes_raw is None: notes_raw = ''
            tlist.append(notes_raw)
            tlist.append(task.find('due').get('useTime') == "True")
            tlist.append(not done) #inverse done
            tlist.append(False) #time track flag
            
            #append to store
            treeiter = self.tasks.append(parent, tlist)
            self.__read_tasks(task.find('tasklist'), treeiter)
    
    def write(self, fname, froms, tos, stats, tasks, taskview, selpath):
        '''Writes todo list data to xml file. Args:
* fname is the file's path
* froms is a list of assigner strings
* tos is a list of assignee strings
* stats is a list of status strings
* tasks is a GtkTreeStore holding the task list itself'''
        htd = Element('htd')
        assigners = SubElement(htd, 'assigners')
        for f in sorted(froms):
            e = SubElement(assigners, 'name')
            e.text = f
        
        assignees = SubElement(htd, 'assignees')
        for f in sorted(tos):
            e = SubElement(assignees, 'name')
            e.text = f
        
        statii = SubElement(htd, 'statii')
        for f in sorted(stats):
            e = SubElement(statii, 'name')
            e.text = f
        
        #store list of expanded rows
        exp = SubElement(htd, 'expanded')
        taskview.map_expanded_rows(self.map_expanded, exp)
        
        #store path of selected row
        sel = SubElement(htd, 'selected')
        sel.text = selpath
        
        #create master tasklist element
        tasklist = SubElement(htd, 'tasklist')
        
        #iterate tasks and add to tasklist element
        self.store_tasks(tasks, tasklist)
        
        #write to file
        ofile = open(fname, 'w')
        ofile.write('<?xml version="1.0" encoding="ISO-8859-1"?>')
        ofile.write(ElementTree.tostring(htd))
        ofile.close()
    
    def map_expanded(self, treeview, path, xml):
        row = SubElement(xml, 'path')
        row.text = str(path)
    
    def store_tasks(self, tasks, taskelem):
        self.tasks = tasks
        treeiter = self.tasks.get_iter_first()
        self.__store_peers(treeiter, taskelem)
        self.tasks = None
    
    def __store_peers(self, treeiter, taskelem):
        while treeiter is not None:
            task = SubElement(taskelem, 'task')
            task.set('done', str(self.tasks[treeiter][12]))
            task.set('priority', str(self.tasks[treeiter][0]))
            e = SubElement(task, 'pct') #pct complete
            e.text = str(self.tasks[treeiter][1])
            e = SubElement(task, 'est') #est time
            e.text = str(self.tasks[treeiter][2])
            e = SubElement(task, 'spent') #time spent
            e.text = str(self.tasks[treeiter][3])
            
            #due
            if self.tasks[treeiter][8] is not None:
                val = self.tasks[treeiter][8]
                duetime = self.tasks[treeiter][15]
                fmt = "%x %X" if duetime else "%x"
                out = "" if val is None else val.strftime(fmt)
                
                due = SubElement(task, 'due')
                due.text = out
                due.set('useTime', str(self.tasks[treeiter][15]))
            else:
                due = SubElement(task, 'due')
                due.set('useTime', str(self.tasks[treeiter][15]))
            
            #completed
            if self.tasks[treeiter][7] is not None:
                val = self.tasks[treeiter][7]
                duetime = self.tasks[treeiter][15]
                fmt = "%x %X" if duetime else "%x"
                out = "" if val is None else val.strftime(fmt)
                
                e = SubElement(task, 'completed')
                e.text = out
            else:
                SubElement(task, 'completed')
            
            e = SubElement(task, 'assigner')
            e.text = self.tasks[treeiter][9]
            e = SubElement(task, 'assignee')
            e.text = self.tasks[treeiter][10]
            e = SubElement(task, 'status')
            e.text = self.tasks[treeiter][11]
            e = SubElement(task, 'title')
            e.text = self.tasks[treeiter][13]
            e = SubElement(task, 'notes')
            e.text = self.tasks[treeiter][14]
            tlist = SubElement(task, 'tasklist')
            if self.tasks.iter_has_child(treeiter):
                childiter = self.tasks.iter_children(treeiter)
                self.__store_peers(childiter, tlist)
            treeiter = self.tasks.iter_next(treeiter)
