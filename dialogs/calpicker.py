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
        # handle main dialog setup
        flags = Gtk.DialogFlags.DESTROY_WITH_PARENT
        Gtk.Dialog.__init__(self, "Document Properties", parent, flags)
        close = self.add_button(Gtk.STOCK_OK, Gtk.ResponseType.OK)
        close.connect("clicked", self.disappear)
        self.set_default_response(Gtk.ResponseType.OK)
        content = self.get_content_area()
        self.parent = parent

        # make the calendar
        cal = Gtk.Calendar()
        # TODO work out how to place the window right below the main window input field
        # TODO get the date

    def disappear(self, widget=None):
        self.hide()