# HiToDo

HiToDo is a heirarchical task list manager inspired by [ToDoList](http://www.abstractspoon.com/tdl_resources.html). It's designed to reproduce those features which I found most useful and needed in day-to-day use. There's a lot more that ToDoList can do, so check it out if you run windows!

Although it isn't completely finished, HiToDo is stable and usable day-to-day. However, I wouldn't recommend it for production use without a lot of backups (just in case) and the patience to recreate lists if/when the format changes.

## Features

**Current Features:**

* Unlimited heirarchical nesting of tasks
* Arbitrary numeric priority levels
* Completion percent tracking/display
* Time estimate field
* Time taken field with live tracking (push a button and it starts accruing time; push again and it adds that time to the task's spent total)
* Due date field
* Completed date field
* Assigner and Assignee fields with dropdown lists for convenience
* Status field with dropdown list for convenience
* Arbitrary-length plaintext notes for every task
* Save/Open htdl format files - xml for easy portability

**Coming Features:**

* Unlimited per-session undo/redo
* Task cut, copy, paste, and paste-beneath operations
* Task reordering via drag-and-drop
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
