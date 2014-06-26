# HiToDo

*Version 0.9.X*

HiToDo is a heirarchical task list manager inspired by [ToDoList](http://www.abstractspoon.com/tdl_resources.html). It's designed to reproduce those features which I found most useful and necessary in day-to-day use. There's a lot more that ToDoList can do, so check it out if you run Windows!

Although it isn't completely finished, HiToDo is stable and fairly usable for non-critical task management. However, I wouldn't recommend it for production use without regular backups and the patience to recreate lists as the format changes.

## Features

**Current Features:**

* Unlimited heirarchical nesting of tasks
* Arbitrary numeric priority levels
* Completion percent tracking/display
* Time estimate field
* Time spent field with live tracking (click a button and it starts to accrue time; click again and it adds that time to the task's spent total)
* Due date field
* Completed date field
* Assigner and Assignee fields with dropdown lists for convenience
* Status field with dropdown list for convenience
* Arbitrary-length plaintext notes for every task
* Save/Open htdl format files
* Cut, copy, paste, and paste-as-child operations for tasks
* Cut, copy, and paste within title and notes fields
* Undo/redo for tasks
* Text undo/Redo for notes field
* Preferences stored with GSettings
* Archive completed tasks

**Planned Features:**
* Open multiple files at once via multiple windows (launched from within the program) or tabs in a single window
* Open/Save of networked files
* Merge and split task lists
* File signing/integrity checksums
* Embedding linked files, other bundled files
* i18n / l10n support
* Attach URLs to tasks
* Built-in encryption?
* ToDoList save/open
* Task reordering via drag-and-drop?

# Requirements

HiToDo requires at least:
* Python 2.5
* GTK+ 3.2 with python-gi bindings
* zlib 1.1.4

## Compatibility

The Oxygen GTK theme has a bug which disables drag-and-drop reordering of columns. The only workaround is to use a different GTK theme.

## Versioning

HiToDo uses [Symantic Versioning](http://semver.org/) for its releases.

# License

HiToDo is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

HiToDo is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more details.

The file named COPYING includes a copy of the GNU General Public License along with HiToDo. If you cannot access this file, see http://www.gnu.org/licenses/.