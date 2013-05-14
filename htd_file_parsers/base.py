class base_backend(object):
    '''Basic backend class. Does nothing, but implements the functions required
    of the other backends. When creating a new backend, inhereit from this class.'''
    
    def __init__(self):
        pass
    
    def read_file(self, fname):
        pass
    
    def write_file(self, fname):
        pass
