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

from os.path import splitext

import htdl
import xml_filter

def pick_filter(file_name):
    '''Pick the best filter for a given filename'''
    ext = splitext(file_name)[1]
    if ext == '.htdl':
        return htdl.FileFilter()
    if ext == '.xml':
        return xml_filter.FileFilter()

def get_loadable():
    return [htdl.FileFilter()]

def get_importable():
    return [xml_filter.FileFilter()]

def get_saveable():
    return [htdl.FileFilter()]

def get_exportable():
    return [xml_filter.FileFilter()]