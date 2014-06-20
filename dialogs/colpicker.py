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
    '''Simple column picker'''

    def __init__(self, parent):
        '''Populate the dialog and set current check status'''

        self._pickers = {}
        self._static = ('title', 'done')

        #handle dialog init
        flags = Gtk.DialogFlags.DESTROY_WITH_PARENT
        Gtk.Dialog.__init__(self, "Visible Columns", parent, flags)
        self.add_button(Gtk.STOCK_OK, Gtk.ResponseType.OK)
        self.add_button(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL)
        self.add_button("Save as Default", Gtk.ResponseType.ACCEPT)
        self.set_default_response(Gtk.ResponseType.CLOSE)
        content = self.get_content_area()
        self.parent = parent

        colframe = Gtk.Frame()
        colframe.set_label_widget(Gtk.Label("All Columns"))
        colbox = Gtk.Grid()
        colbox.set_column_spacing(5)
        colframe.add(colbox)

        # create a checkbox for each of our parent's stored rows
        stepx = 0
        stepy = 0
        for col in parent.cols:
            x = Gtk.CheckButton.new_with_label(col[1])
            x.set_active(col[0] in parent.cols_visible)
            if col[0] in self._static:
                x.set_sensitive(False)
            colbox.attach(x, stepx, stepy, 1, 1)
            self._pickers[col[0]] = x
            stepy += 1
            if stepy >= 8:
                stepx += 1
                stepy = 0

        content.pack_start(colframe, True, True, 0)
        self.show_all()

    def update(self, cols_visible = None):
        '''Update checkboxes to reflect current visibility'''

        if cols_visible is None:
            cols_visible = self.parent.cols_visible

        for col in self.parent.cols:
            code = col[0]
            x = self._pickers[code]
            x.set_active(code in cols_visible)

    def go(self):
        '''Show ourselves and then collate checkbox states into a list'''

        oldcols = self.parent.cols_visible
        ret = self.run()
        self.hide()

        # create new column list from our checked boxes
        newcols = []
        if ret != Gtk.ResponseType.CANCEL:
            newcols = [code for code, x in self._pickers.items() if x.get_active()]
            return (newcols, ret)

        return None