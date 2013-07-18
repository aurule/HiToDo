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
        Gtk.Dialog.__init__(self, "Document Properties", parent, flags)
        close = self.add_button(Gtk.STOCK_OK, Gtk.ResponseType.CLOSE)
        close.connect("clicked", self.disappear)
        self.set_default_response(Gtk.ResponseType.CLOSE)
        content = self.get_content_area()
        self.parent = parent
        
        nb = Gtk.Notebook()
        nb.set_property("margin", 10)
        
        #Stats tab
        statlbl = Gtk.Label("_Stats")
        statlbl.set_use_underline(True)
        stattab = self.create_stats_tab()
        nb.append_page(stattab, statlbl)
        
        #Columns tab
        collbl = Gtk.Label("_Columns")
        collbl.set_use_underline(True)
        coltab = self.create_cols_tab()
        nb.append_page(coltab, collbl)
        
        #add the tabbed notebook
        content.pack_start(nb, True, True, 0)
    
    def disappear(self, widget=None):
        self.hide()
    
    def create_cols_tab(self):
        frame = Gtk.Frame()
        frame_lbl = Gtk.Label("<b>List Columns</b>")
        frame_lbl.set_property("use-markup", True)
        frame.set_label_widget(frame_lbl)
        frame.set_property("margin", 10)
        frame.set_property("shadow-type", Gtk.ShadowType.NONE)
        
        first_box = Gtk.Box()
        first_box.set_orientation(Gtk.Orientation.VERTICAL)
        first_box.set_property("margin-left", 12)
        frame.add(first_box)
        
        #explanation text
        expolbl = Gtk.Label("Choose which columns to show. To change their order, use the up and down buttons.")
        expolbl.set_property("wrap", True)
        expolbl.set_max_width_chars(24)
        first_box.pack_start(expolbl, False, False, 0)
        
        #set up main box
        main_box = Gtk.Box()
        main_box.set_orientation(Gtk.Orientation.HORIZONTAL)
        first_box.pack_start(main_box, True, True, 0)
        
        #start with a list widget for the columns
        #first a scrolling window to put it in
        col_view_scroller = Gtk.ScrolledWindow()
        col_view_scroller.set_min_content_height(315)
        col_view_scroller.set_min_content_width(300)
        
        col_view = Gtk.TreeView(self.parent.cols)
        col_sel = col_view.get_selection() #store selection for later
        
        #set up the columns for our treeview
        #visible checkbox
        visible = Gtk.CellRendererToggle(activatable=True, radio=False)
        visible.connect("toggled", self.parent.toggle_col_visible)
        col_visible = Gtk.TreeViewColumn(u"\u2713", visible, active=2, visible=3)
        col_view.append_column(col_visible)
        
        #title display
        name = Gtk.CellRendererText(editable=False)
        col_name = Gtk.TreeViewColumn("Column", name, text=1)
        col_view.append_column(col_name)
        
        #add it
        col_view_scroller.add(col_view)
        main_box.pack_start(col_view_scroller, True, True, 0)
        
        #up/down buttons
        btnbox = Gtk.ButtonBox()
        btnbox.set_orientation(Gtk.Orientation.VERTICAL)
        btnbox.set_homogeneous(True)
        btnbox.set_layout(Gtk.ButtonBoxStyle.START)
        
        upbtn = Gtk.Button(Gtk.STOCK_GO_UP)
        upbtn.set_use_stock(True)
        upbtn.connect("clicked", self.parent.move_col, col_sel, "up")
        btnbox.pack_start(upbtn, False, False, 0)
        
        dnbtn = Gtk.Button(Gtk.STOCK_GO_DOWN)
        dnbtn.set_use_stock(True)
        dnbtn.connect("clicked", self.parent.move_col, col_sel, "dn")
        btnbox.pack_start(dnbtn, False, False, 0)
        
        sep = Gtk.Separator()
        sep.set_property("orientation", Gtk.Orientation.HORIZONTAL)
        btnbox.pack_start(sep, False, False, 0)
        btnbox.set_child_non_homogeneous(sep, True)
        
        defaultbtn = Gtk.Button("De_fault")
        defaultbtn.set_use_underline(True)
        defaultbtn.connect("clicked", self.parent.reset_cols)
        btnbox.pack_start(defaultbtn, False, False, 0)
        
        main_box.pack_start(btnbox, False, False, 0)
        
        return frame
    
    def create_stats_tab(self):
        main_box = Gtk.Box()
        main_box.set_orientation(Gtk.Orientation.VERTICAL)
        main_box.set_property("margin", 10)
        
        #first up are stats directly related to tasks
        tasksframe = Gtk.Frame()
        tasksframe_lbl = Gtk.Label()
        tasksframe_lbl.set_markup("<b>Tasks</b>")
        tasksframe.set_label_widget(tasksframe_lbl)
        tasksframe.set_shadow_type(Gtk.ShadowType.NONE)
        tasksframe.set_border_width(5)
        taskstats_align = Gtk.Alignment()
        taskstats_align.set_property("left-padding", 5)
        taskstats = Gtk.Grid()
        taskstats.set_column_spacing(50)
        taskstats.set_border_width(10)
        
        tlabel = Gtk.Label("Total")
        self.tstat = Gtk.Label("0")
        taskstats.attach(tlabel, 0, 0, 1, 1)
        taskstats.attach(self.tstat, 1, 0, 1, 1)
        olabel = Gtk.Label("Open")
        self.ostat = Gtk.Label("0")
        taskstats.attach(olabel, 0, 1, 1, 1)
        taskstats.attach(self.ostat, 1, 1, 1, 1)
        dlabel = Gtk.Label("Done")
        self.dstat = Gtk.Label("0")
        taskstats.attach(dlabel, 0, 2, 1, 1)
        taskstats.attach(self.dstat, 1, 2, 1, 1)
        
        taskstats_align.add(taskstats)
        tasksframe.add(taskstats_align)
        main_box.add(tasksframe)
        
        return main_box
    
    def show_all(self):
        stats = self.parent.make_stats()
        self.tstat.set_text(str(stats['total']))
        self.ostat.set_text(str(stats['open']))
        self.dstat.set_text(str(stats['done']))
        #self.from_list.set_text(', '.join(sorted(self.parent.assigners_list)))
        #self.to_list.set_text(', '.join(sorted(self.parent.assignees_list)))
        #self.status_list.set_text(', '.join(sorted(self.parent.statii_list)))
        Gtk.Dialog.show_all(self)
