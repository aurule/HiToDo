# HiToDo

HiToDo is a heirarchical task list manager inspired by [ToDoList](http://www.abstractspoon.com/tdl_resources.html). It's designed to reproduce those features which I found most useful and needed in day-to-day use. There's a lot more that ToDoList can do, so check it out if you run Windows!

Although it isn't completely finished, HiToDo is stable and fairly usable for non-critical task management. However, I wouldn't recommend it for production use without a lot of backups and the patience to recreate lists as the format changes.

## Features

**Current Features:**

* Unlimited heirarchical nesting of tasks
* Arbitrary numeric priority levels
* Completion percent tracking/display
* Time estimate field
* Time taken field with live tracking (click a button and it starts to accrue time; click again and it adds that time to the task's spent total)
* Due date field
* Completed date field
* Assigner and Assignee fields with dropdown lists for convenience
* Status field with dropdown list for convenience
* Arbitrary-length plaintext notes for every task
* Save/Open htdl format files - xml for easy portability
* Cut, copy, paste, and paste-beneath operations for tasks
* Cut, copy, and paste for title and notes fields
* Undo/Redo for notes field
* Task reordering via drag-and-drop
* Unlimited per-session undo/redo for tasks

**Planned Features:**

* Global preferences stored with GSettings
* Open multiple files at once via multiple windows (launched from within the program) or tabs in a single window
* Open/Save of networked files
* Archive completed tasks
* Merge and split task lists
* Built-in encryption?
* Compressed save files? It would open up a lot of possibilities with bundled files.
    * File signing/integrity checksums
    * Embedding linked files
* i18n and l10n support
* Attach URLs to tasks
    * With compressed/bundled saves, files could also be embedded
* [todo.txt](http://todotxt.com/) save/open
* ToDoList save/open

# Requirements

HiToDo requires
* Python 2.5 or higher (2.7.5 recommended)
* GTK+ 3.2 or higher with python-gi bindings
* python-dateutil 1.5

# License

HiToDo is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

HiToDo is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more details.

The file named COPYING includes a copy of the GNU General Public License along with HiToDo. If you cannot access this file, see http://www.gnu.org/licenses/.
