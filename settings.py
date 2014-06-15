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

from __future__ import with_statement
import json
import os
from gi.repository import Gtk

class settings(object):
    '''Settings handler for HiToDo

    Loads, stores, and saves config data for HiToDo. Takes care of both the loading and saving of the configuration file, and the management of the preferences dialog.

    Settings are stored in $XDG_CONFIG_HOME/hitodo/settings.json
    '''

    prefs_dialog = None
    config_dir = ""
    _settings = []
    defaults = '''{
    "reopen": true,
    "show-toolbar": true,
    "use-tabs": true,
    "clobber-on-new": true,
    "clobber-on-open": true,
    "default-status": [],
    "default-from": [],
    "default-to": [],
    "default-columns": ["priority", "pct complete", "time est", "time spent", "tracked", "due date", "complete date", "from", "to", "status", "done", "title"]
}
'''

    def __init__(self, parent):
        # set config file location
        config = os.getenv("XDG_CONFIG_HOME")
        if not config:
            config = os.getenv("HOME") + "/.config"
        self.config_dir = config + "/hitodo"

        # try to load from our config file
        conf = self.config_dir + "/settings.json"
        if os.path.isfile(conf):
            try:
                with open(conf) as f:
                    self._settings = json.load(f)
            except EnvironmentError:
                pass

        # if that didn't work, load internal defaults
        if not self._settings:
            self._settings = json.loads(self.defaults)

        self.init_dialog(parent)

    def set(self, setting, value):
        '''Set the value of a named setting.

        Arguments:
        setting - string - The name of a setting
        value - type varies - The value to be stored
        '''
        self._settings[setting] = value

    def get(self, setting):
        '''Get the current value of a named setting

        Arguments:
        setting - string - The name of a setting stored in this object. Case-sensitive.

        Returns:
        The value of the named setting, or Mone if that setting does not exist.
        '''

        try:
            return self._settings[setting]
        except KeyError:
            return None

    def show_dialog(self):
        self.prefs_dialog.show_all()

    def save_prefs(self, widget):
        self.prefs_dialog.hide()
        conf = self.config_dir + "/settings.json"
        if not os.path.exists(self.config_dir):
            os.makedirs(self.config_dir)

        with open(conf, 'wb+') as f:
            json.dump(self._settings, f, indent=4, sort_keys=True)

    def init_dialog(self, parent):
        flags = Gtk.DialogFlags.DESTROY_WITH_PARENT
        self.prefs_dialog = Gtk.Dialog("HiToDo Preferences", parent, flags)

        close = self.prefs_dialog.add_button(Gtk.STOCK_OK, Gtk.ResponseType.CLOSE)
        close.connect("clicked", self.save_prefs)
        content = self.prefs_dialog.get_content_area()
        nb = Gtk.Notebook()
        nb.set_property("margin", 10)

        # TODO set up our preferences dialog

        content.add(nb)