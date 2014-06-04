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

from gi.repository import Gtk, Gdk

class main(Gtk.Dialog):
    def __init__(self, parent):
        #handle dialog init
        flags = Gtk.DialogFlags.DESTROY_WITH_PARENT
        Gtk.Dialog.__init__(self, "Choose a Date", parent, flags)
        close = self.add_button(Gtk.STOCK_CLOSE, Gtk.ResponseType.CLOSE)
        close.connect("clicked", self.disappear)
        self.set_default_response(Gtk.ResponseType.CLOSE)
        content = self.get_content_area()
        self.parent = parent

        # add our calendar
        self.cal = Gtk.Calendar()
        self.cal.connect("day-selected", self.day_picked)
        content.pack_start(self.cal, False, False, 0)

        # placeholder for our entry field


    def show_for_entry(self, path):
        self.show_all()
        self.target = self.parent.tasklist[path]

    def disappear(self, widget=None):
        self.hide()

    def day_picked(self, data):
        print self.cal.get_date()
        print self.target
        # TODO store the selected date
        # if we have a place to put it, grab self.cal.get_date()
        # returns year, month, day
        # store that somehow