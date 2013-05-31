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

def print_tree_store(store):
    rootiter = store.get_iter_first()
    print_rows(store, rootiter, "")

def print_rows(store, treeiter, indent):
    while treeiter != None:
        print indent + str(store[treeiter][:])
        if store.iter_has_child(treeiter):
            childiter = store.iter_children(treeiter)
            print_rows(store, childiter, indent + "\t")
        treeiter = store.iter_next(treeiter)
