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

from gi.repository import Gtk

def copy_treemodel(orig):
    '''Create a new treemodel with the same columns as model'''

    column_types = []
    column_numbers = range(orig.get_n_columns())
    for i in column_numbers:
        column_types.append(orig.get_column_type(i))
    copy = Gtk.TreeStore(*column_types)
    return copy

def append_row(orig, path, treeiter, copy):
    '''Append a row to the treemodel copy from the treemodel orig

    Preserves parent-child relationships. Meant to be run as
    'orig.foreach(append_row, copy)'
    '''
    strpath = path.to_string()

    parts = strpath.rsplit(':', 1)
    parent_path = parts[0]
    parent_iter = None if parent_path == strpath else copy.get_iter(parent_path)

    copy.append(parent_iter, orig[treeiter][:])

def is_number(s):
    '''Determines whether s can be cast to a float'''

    try:
        float(s)
        return True
    except ValueError:
        return False
