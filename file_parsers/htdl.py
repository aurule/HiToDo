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

class FileFilter(xml_filter.FileFilter):
    def __init__(self):
        Gtk.FileFilter.__init__(self)
        self.add_pattern("*.htdl")
        self.set_name("HiToDo Files (*.htdl)")
        self.file_extension = ".htdl"
        self.tasklist = None
        self.file_version = "1.0"

    def read_to_store(self, data):
        '''Reads todo list data from tgz'd xml file. Data is a dictionary of data holders to fill.'''
        with tarfile.open(data['filename'], 'r:gz') as tar:
            tar = tarfile.open(data['filename'], 'r:gz')
            f = tar.extractfile('todo.data')
            self.parse_raw(f, data)
            f.close()
            v = tar.extractfile('version.data')
            data['save_version'] = v.readline().rstrip() # version is in its own file
            v.close()

    def write(self, data, append):
        if append is True and isfile(data['filename']):
            self.write_append(data)
        else:
            self.write_simple(data)

    def write_simple(self, data):
        '''Writes todo list data to xml file. Data is a dictionary of data pieces to store.'''
        # create tgz-formatted output file and write
        with tarfile.open(data['filename'], 'w:gz') as tar:
            # store xml in a temp file
            (datafile, datafile_path) = mkstemp()
            super(FileFilter, self).write_simple(data, datafile_path)

            # store version in a temp file
            (verfile, verfile_path) = mkstemp()
            verfile = open(verfile_path, 'wb')
            verfile.write(self.file_version)
            verfile.close()

            tar.add(datafile_path, arcname="todo.data")
            tar.add(verfile_path, arcname="version.data")

            osremove(datafile_path)
            osremove(verfile_path)

    def write_append(self, data):
        '''Appends tasks to an existing file. CAUTION: This function does not add or update anything besides tasks.'''
        with tarfile.open(data['filename'], 'r:gz') as tar:
            f = tar.extractfile('todo.data')
            document = ElementTree.parse(f)
            f.close()

        htd = document.getroot()
        tasklist = document.find("tasklist")
        # TODO update the rest of the saved info
        super(FileFilter, self).store_tasks(data['task_store'], tasklist)

        #write to file
        with tarfile.open(data['filename'], 'w:gz') as tar:
            # store xml in a temp file
            (datafile, datafile_path) = mkstemp()
            datafile = open(datafile_path, 'wb')
            datafile.write(ElementTree.tostring(htd, encoding="UTF-8"))
            datafile.close()
 
            # store version in a temp file
            (verfile, verfile_path) = mkstemp()
            verfile = open(verfile_path, 'wb')
            verfile.write(self.file_version)
            verfile.close()

            # create tgz-formatted output file and write
            tar.add(datafile_path, arcname="todo.data")
            tar.add(verfile_path, arcname="version.data")
            tar.close()
            osremove(datafile_path)
            osremove(verfile_path)
