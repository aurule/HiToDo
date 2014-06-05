# Copyright 2013 Peter Andrews

# Based on code from the PyGTK project. That code was modified by converting it to the PyGI interface.
# Original code Copyright 2011 PyGTK project

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

from datetime import datetime, date
from gi.repository import Gtk, Gdk

class CellRendererDate(Gtk.CellRendererText):

    __gtype_name__ = 'CellRendererDate'

    def __init__(self, *args, **kwargs):
        Gtk.CellRendererText.__init__(self, *args, **kwargs)
        self.date_format = '%m/%d/%Y'
        self.calendar_window = None
        self.calendar = None

    def _create_calendar(self, treeview):
        self.calendar_window = Gtk.Dialog(parent=treeview.get_toplevel())
        self.calendar_window.action_area.hide()
        self.calendar_window.set_decorated(False)
        self.calendar_window.set_property('skip-taskbar-hint', True)

        self.calendar = Gtk.Calendar()
        self.calendar.set_display_options(Gtk.CalendarDisplayOptions.SHOW_DAY_NAMES | Gtk.CalendarDisplayOptions.SHOW_HEADING)
        self.calendar.connect('day-selected-double-click', self._day_selected, None)
        self.calendar.connect('key-press-event', self._day_selected)
        self.calendar.connect('focus-out-event', self._selection_cancelled)
        self.calendar_window.set_transient_for(None) # cancel the modality of dialog
        self.calendar_window.vbox.pack_start(self.calendar, False, False, 0)


        # necessary for getting the (width, height) of calendar_window
        self.calendar.show()
        self.calendar_window.realize()

    def do_start_editing(self, event, treeview, path, background_area, cell_area, flags):
        if not self.get_property('editable'):
            return None

        # self.entry = Gtk.CellRendererText.do_start_editing(self, event, treeview, path, background_area, cell_area, flags)
        self.entry = Gtk.Entry()
        self.path = path

        if not self.calendar_window:
            self._create_calendar(treeview)

        # select cell's previously stored date if any exists - or today
        if self.get_property('text'):
            ddate = datetime.strptime(self.get_property('text'), self.date_format)
        else:
            ddate = datetime.today()
        self.calendar.freeze_child_notify() # prevent flicker
        (year, month, day) = (ddate.year, ddate.month - 1, ddate.day) # datetime's month starts from one
        self.calendar.select_month(int(month), int(year))
        self.calendar.select_day(int(day))
        self.calendar.thaw_child_notify()

        # position the popup on the edited cell (and try hard to keep the popup within the toplevel window)
        (tree_x, tree_y) = treeview.get_bin_window().get_origin()[1:3]
        (tree_w, tree_h) = treeview.get_window().get_geometry()[2:4]
        (calendar_w, calendar_h) = self.calendar_window.get_window().get_geometry()[2:4]
        x = tree_x + min(cell_area.x, tree_w - calendar_w + treeview.get_visible_rect().x)
        y = tree_y + min(cell_area.y, tree_h - calendar_h + treeview.get_visible_rect().y)
        self.calendar_window.move(x, y)

        self.calendar_window.show()
        return self.entry

    def _day_selected(self, calendar, event):
        # event == None for day selected via doubleclick
        if not event or event.type == Gdk.EventType.KEY_PRESS and Gdk.keyval_name(event.keyval) == 'Return':
            # self.calendar_window.response(Gtk.ResponseType.OK)
            self.entry.hide()
            self.calendar_window.destroy()
            self.calendar_window = None
            (year, month, day) = self.calendar.get_date()
            ddate = date(year, month + 1, day)
            ddate = ddate.strftime(self.date_format) # gtk.Calendar's month starts from zero
            self.emit('edited', self.path, ddate)
            return True

    def _selection_cancelled(self, calendar, event):
        # self.calendar_window.response(Gtk.ResponseType.CANCEL)
        self.entry.hide()
        self.calendar_window.destroy()
        self.calendar_window = None
        return True
