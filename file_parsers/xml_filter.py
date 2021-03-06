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
from os.path import isfile
from os import remove as osremove
from tempfile import mkstemp
import gzip
import tarfile

import xml_filter

class FileFilter(Gtk.FileFilter):
    def __init__(self):
        Gtk.FileFilter.__init__(self)
        self.add_pattern("*.xml")
        self.set_name("HiToDo XML Files (*.xml)")
        self.file_extension = ".xml"
        self.tasklist = None
        self.file_version = "1.0"

    def read_to_store(self, data, fname=None):
        '''Reads todo list data from xml file. Data is a dictionary of data holders to fill.'''
        if fname is None:
            fname = data['filename']

        with open(fname, 'rb') as f:
            self.parse_raw(f, data)

    def parse_raw(self, f, data):
        document = ElementTree.parse(f)

        htd = document.getroot()
        data['save_version'] = float(htd.get('version'))
        data['our_version'] = self.file_version

        #get assigners, assignees, and statii lists
        assigners = document.find("assigners")
        for n in assigners.findall('name'):
            if n.text not in data['from_list']:
                data['from_list'].append(n.text)

        assignees = document.find("assignees")
        for n in assignees.findall('name'):
            if n.text not in data['to_list']:
                data['to_list'].append(n.text)

        statii = document.find("statii")
        for n in statii.findall('name'):
            if n.text not in data['status_list']:
                data['status_list'].append(n.text)

        #get visible column list
        columns = document.find('columns')
        for c in columns.findall('col'):
            data['cols'].append((c.text, c.attrib['visible'] == "True"))

        #get window geometry
        geo = document.find('geometry')
        maxed = geo.find('maximized').text == "True"
        height = int(geo.find('height').text)
        width = int(geo.find('width').text)
        task_width = int(geo.find('task-width').text)

        data['geometry'] = (maxed, height, width, task_width)

        #get highest-level tasklist element
        tlist = document.find("tasklist")
        self.tasklist = data['task_store']
        self.__read_tasks(tlist, None)

        exp = document.find('expanded')
        expanded_paths = []
        for n in exp.findall('path'):
            expanded_paths.append(n.text)
        seldata = document.find('selected')
        sel = seldata.text

        data['expanded'] = expanded_paths
        data['selected'] = sel

    def __read_tasks(self, tlist, parent=None):
        '''Internal function to recursively add tasks from an XML file to the treestore self.tasklist.'''
        for task in tlist.iterfind('./task'):
            #make a list from subelements and attributes to add to the treestore
            tasks = []
            tasks.append(int(task.get('priority')))
            tasks.append(int(task.find('pct').text))
            tasks.append(int(task.find('est').text))
            tasks.append(int(task.find('spent').text))
            est_begin_raw = task.find('est-begin').text
            if est_begin_raw is None:
                tasks.append("")
            else:
                tasks.append(dateparse(est_begin_raw))
            est_complete_raw = task.find('est-complete').text
            if est_complete_raw is None:
                tasks.append("")
            else:
                tasks.append(dateparse(est_complete_raw))
            act_begin_raw = task.find('act-begin').text
            if act_begin_raw is None:
                tasks.append("")
            else:
                tasks.append(dateparse(act_begin_raw))
            completed_raw = task.find('completed').text
            if completed_raw is None:
                tasks.append("")
            else:
                tasks.append(dateparse(completed_raw))
            due_raw = task.find('due').text
            if due_raw is None:
                tasks.append("")
            else:
                tasks.append(dateparse(due_raw))
            assigner_raw = task.find('assigner').text
            if assigner_raw is None: assigner_raw = ''
            tasks.append(assigner_raw)
            assignee_raw = task.find('assignee').text
            if assignee_raw is None: assignee_raw = ''
            tasks.append(assignee_raw)
            status_raw = task.find('status').text
            if status_raw is None: status_raw = ''
            tasks.append(status_raw)
            done = task.get('done') == "True"
            tasks.append(done)
            tasks.append(task.find('title').text)
            notes_raw = task.find('notes').text
            if notes_raw is None: notes_raw = ''
            tasks.append(notes_raw)
            tasks.append(task.find('due').get('useTime') == "True")
            tasks.append(not done) #inverse done
            tasks.append(False) #time track flag

            #append to store
            treeiter = self.tasklist.append(parent, tasks)
            self.__read_tasks(task.find('tasklist'), treeiter)

    def write(self, data, append):
        if append is True and isfile(data['filename']):
            self.write_append(data)
        else:
            self.write_simple(data)

    def write_simple(self, data, filename=None):
        '''Writes todo list data to xml file. Data is a dictionary of data pieces to store.'''
        htd = Element('htd')
        htd.set('version', self.file_version)

        #store assigners, assignees, and statii lists
        assigners = SubElement(htd, 'assigners')
        for f in data['from_list']:
            e = SubElement(assigners, 'name')
            e.text = unicode(f, 'utf-8')

        assignees = SubElement(htd, 'assignees')
        for f in data['to_list']:
            e = SubElement(assignees, 'name')
            e.text = unicode(f, 'utf-8')

        statii = SubElement(htd, 'statii')
        for f in data['status_list']:
            e = SubElement(statii, 'name')
            e.text = unicode(f, 'utf-8')

        #store list of expanded rows
        exp = SubElement(htd, 'expanded')
        data['task_view'].map_expanded_rows(self.map_expanded, exp)

        #store path of selected row
        sel = SubElement(htd, 'selected')
        sel.text = data['selection']

        #store cols list
        columns = SubElement(htd, 'columns')
        for col, vis in data['cols']:
            c = SubElement(columns, 'col')
            c.set("visible", str(vis))
            c.text = col

        #store window geometry
        geo = SubElement(htd, 'geometry')
        maxed = SubElement(geo, 'maximized')
        maxed.text = str(data['geometry'][0])
        height = SubElement(geo, 'height')
        height.text = str(data['geometry'][1])
        width = SubElement(geo, 'width')
        width.text = str(data['geometry'][2])
        task_width = SubElement(geo, 'task-width')
        task_width.text = str(data['geometry'][3])

        #create master tasklist element
        tasklist = SubElement(htd, 'tasklist')

        #iterate tasks and add to tasklist element
        self.store_tasks(data['task_store'], tasklist)

        # write to output file
        if filename is None:
            # get name from data if none is provided
            filename = data['filename']
        with open(filename, 'wb') as f:
            f.write(ElementTree.tostring(htd, encoding="UTF-8"))

    def write_append(self, data, ):
        '''Appends tasks to an existing file. CAUTION: This function does not add or update anything besides tasks.'''
        with open(data['filename'], 'rb') as f:
            document = ElementTree.parse(f)

        htd = document.getroot()
        tasklist = document.find("tasklist")
        # TODO update the rest of the saved info
        self.store_tasks(data['task_store'], tasklist)

        #write to file
        with open(filename, 'wb') as datafile:
            datafile.write(ElementTree.tostring(htd, encoding="UTF-8"))

    def map_expanded(self, treeview, path, xml):
        row = SubElement(xml, 'path')
        row.text = str(path)

    def store_tasks(self, treestore, taskelem):
        self.tasklist = treestore
        treeiter = self.tasklist.get_iter_first()
        self.__store_peers(treeiter, taskelem)
        self.tasklist = None

    def __store_peers(self, treeiter, taskelem):
        while treeiter is not None:
            task = SubElement(taskelem, 'task')
            task.set('done', str(self.tasklist[treeiter][12]))
            task.set('priority', str(self.tasklist[treeiter][0]))
            e = SubElement(task, 'pct') #pct complete
            e.text = str(self.tasklist[treeiter][1])
            e = SubElement(task, 'est') #est time
            e.text = str(self.tasklist[treeiter][2])
            e = SubElement(task, 'spent') #time spent
            e.text = str(self.tasklist[treeiter][3])

            #duetime flag changes datetime format
            duetime = self.tasklist[treeiter][15]
            fmt = "%Y-%m-%d %H:%M" if duetime else "%Y-%m-%d" #uses ISO 8601 format

            #due
            if self.tasklist[treeiter][8] is not '':
                val = self.tasklist[treeiter][8]
                out = "" if val is '' else val.strftime(fmt)

                due = SubElement(task, 'due')
                due.text = out
                due.set('useTime', str(self.tasklist[treeiter][15]))
            else:
                due = SubElement(task, 'due')
                due.set('useTime', str(self.tasklist[treeiter][15]))

            #completed
            if self.tasklist[treeiter][7] is not '':
                val = self.tasklist[treeiter][7]
                out = "" if val is '' else val.strftime(fmt)

                e = SubElement(task, 'completed')
                e.text = out
            else:
                SubElement(task, 'completed')

            #est begin
            if self.tasklist[treeiter][4] is not '':
                val = self.tasklist[treeiter][4]
                out = "" if val is '' else val.strftime(fmt)

                e = SubElement(task, 'est-begin')
                e.text = out
            else:
                SubElement(task, 'est-begin')

            #est complete
            if self.tasklist[treeiter][5] is not '':
                val = self.tasklist[treeiter][5]
                out = "" if val is '' else val.strftime(fmt)

                e = SubElement(task, 'est-complete')
                e.text = out
            else:
                SubElement(task, 'est-complete')

            #act begin
            if self.tasklist[treeiter][6] is not "":
                val = self.tasklist[treeiter][6]
                out = "" if val is '' else val.strftime(fmt)

                e = SubElement(task, 'act-begin')
                e.text = out
            else:
                SubElement(task, 'act-begin')
            e = SubElement(task, 'assigner')
            e.text = unicode(self.tasklist[treeiter][9], 'utf-8')
            e = SubElement(task, 'assignee')
            e.text = unicode(self.tasklist[treeiter][10], 'utf-8')
            e = SubElement(task, 'status')
            e.text = unicode(self.tasklist[treeiter][11], 'utf-8')
            e = SubElement(task, 'title')
            e.text = unicode(self.tasklist[treeiter][13], 'utf-8')
            e = SubElement(task, 'notes')
            e.text = unicode(self.tasklist[treeiter][14], 'utf-8')
            tlist = SubElement(task, 'tasklist')
            if self.tasklist.iter_has_child(treeiter):
                childiter = self.tasklist.iter_children(treeiter)
                self.__store_peers(childiter, tlist)
            treeiter = self.tasklist.iter_next(treeiter)