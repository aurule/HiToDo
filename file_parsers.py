from gi.repository import Gtk
from xml.etree import ElementTree
from xml.etree.ElementTree import Element
from xml.etree.ElementTree import SubElement

class htd_filter(Gtk.FileFilter):
    def __init__(self):
        Gtk.FileFilter.__init__(self)
        self.add_pattern("*.htdl")
        self.set_name("HiToDo Files (*.htdl)")
        self.file_extension = ".htdl"
        self.tasks = None
    
    def read_to_store(self, fname, froms, tos, stats, taskstore):
        '''Reads todo list data from xml file. Args:
* fname is the file's path
* froms is a list where assigner strings will be stored
* tos is a list where assignee strings will be stored
* stats is a list where status strings will be stored
* taskstore is a GtkTreeStore which will be populated from tasks in the file'''
        document = ElementTree.parse(fname)
        #TODO read through elements
    
    def write(self, fname, froms, tos, stats, tasks):
        '''Writes todo list data to xml file. Args:
* fname is the file's path
* froms is a list of assigner strings
* tos is a list of assignee strings
* stats is a list of status strings
* tasks is a GtkTreeStore holding the task list itself'''
        htd = Element('htd')
        assigners = SubElement(htd, 'assigners')
        for f in sorted(froms):
            SubElement(assigners, 'name', text=f)
        
        assignees = SubElement(htd, 'assignees')
        for f in sorted(tos):
            SubElement(assignees, 'name', text=f)
        
        statii = SubElement(htd, 'statii')
        for f in sorted(stats):
            SubElement(statii, 'name', text=f)
        
        #create master tasklist element
        tasklist = SubElement(htd, 'tasklist')
        
        #iterate tasks and add to tasklist element
        self.store_tasks(tasks, tasklist)
        
        #write to file
        ofile = open(fname, 'w')
        ofile.write('<?xml version="1.0"?>')
        ofile.write(ElementTree.tostring(htd))
        ofile.close()
    
    def store_tasks(self, tasks, taskelem):
        self.tasks = tasks
        treeiter = self.tasks.get_iter_first()
        self.__store_peers(treeiter, taskelem)
        self.tasks = None
    
    def __store_peers(self, treeiter, taskelem):
        while treeiter is not None:
            task = SubElement(taskelem, 'task')
            task.set('done', str(self.tasks[treeiter][12]))
            SubElement(task, 'pct', text=str(self.tasks[treeiter][1])) #pct complete
            SubElement(task, 'est', text=str(self.tasks[treeiter][2])) #est time
            SubElement(task, 'spent', text=str(self.tasks[treeiter][3])) #time spent
            
            #due
            if self.tasks[treeiter][8] is not None:
                val = self.tasks[treeiter][8]
                duetime = self.tasks[treeiter][15]
                fmt = "%x %X" if duetime else "%x"
                out = "" if val is None else val.strftime(fmt)
                
                due = SubElement(task, 'due', text=out)
                due.set('useTime', str(self.tasks[treeiter][15]))
            else:
                due = SubElement(task, 'due')
                due.set('useTime', str(self.tasks[treeiter][15]))
            
            #completed
            if self.tasks[treeiter][7] is not None:
                val = self.tasks[treeiter][7]
                duetime = self.tasks[treeiter][15]
                fmt = "%x %X" if duetime else "%x"
                out = "" if val is None else val.strftime(fmt)
                
                SubElement(task, 'completed', text=out)
                pass
            else:
                SubElement(task, 'completed')
            
            SubElement(task, 'assigner', text=self.tasks[treeiter][9])
            SubElement(task, 'assignee', text=self.tasks[treeiter][10])
            SubElement(task, 'status', text=self.tasks[treeiter][11])
            SubElement(task, 'title', text=self.tasks[treeiter][13])
            SubElement(task, 'notes', text=self.tasks[treeiter][14])
            tlist = SubElement(task, 'tasklist')
            if self.tasks.iter_has_child(treeiter):
                childiter = self.tasks.iter_children(treeiter)
                self.__store_peers(childiter, tlist)
            treeiter = self.tasks.iter_next(treeiter)
