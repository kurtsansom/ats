import sys, os
from atsut import abspath, AtsError, debug

class AtsLog (object):
    "Log and stderr echo facility"
    def __init__ (self, directory = '', name='',
                  echo=True, logging = False, indentation='   '):
        super(AtsLog, self).__init__ ()
        self.reset()
        self.echo=echo
        self.leading = ''
        self.indentation=indentation
        self.mode = "w"
        self.logging = False  #temporary
        self.set(directory=directory, name = name)
        self.logging = logging

    def set (self, directory = '', name = ''):
        "Set the name and directory of the log file."
        if not directory: 
            directory = os.getcwd()
        if not name:
            name = "ats.log"
        self.directory = abspath(directory)
        self.shortname = name
        self.name = os.path.join(self.directory, self.shortname)

    def reset (self):
        "Erase indentation history."
        self.__previous = []

    def _open(self, filename, mode):
        try:
            return open(filename, mode)
        except IOError:
            pass
        if not os.path.isdir(self.directory):
            os.makedirs(self.directory)
        return open(filename, mode)
           
    def putlist(self, linelist, **kw):
        """Write a list of lines that include newline at end. 
           Keywords echo and logging.
        """
# doesn't seem worth it to check for bad keywords
        echo = kw.get('echo', self.echo)
        logging = kw.get('logging', self.logging)
        indentation=self.leading
        if logging:
            d = self._open(self.name, self.mode)
            self.mode = 'a'
            for line in linelist:
                print >>d, indentation + line,
            print >>d
            d.close()

        if echo:
            d = sys.stderr
            for line in linelist:
                 print >>d, indentation + line,
            print >>d

    def write (self, *items, **kw):
        "Write one line, like a print. Keywords echo and logging."
        echo = kw.get('echo', self.echo)
        logging = kw.get('logging', self.logging)
        content = self.leading + ' '.join([str(k) for k in items])
        if logging:
            d = self._open(self.name, self.mode)
            self.mode = 'a'
            print >>d, content
            d.close()

        if echo:
            d = sys.stderr
            print >>d, content

    __call__ = write

    def indent (self):
        self.__previous.append(self.leading)
        self.leading += self.indentation
        
    def dedent (self):
        try:
            self.leading = self.__previous.pop()
        except IndexError:
            pass

    def fatal_error (self, msg):
        "Issue message and die."
        try:
            self('Fatal error:', msg, echo=True)
        except Exception:
            print >>sys.stderr, msg
        raise SystemExit, 1
                
log = AtsLog(name="ats.log") 
terminal = AtsLog(echo=True, logging=False)

if __name__ == "__main__":
    log = AtsLog(logging=True, directory='test.logs')
    print log.directory, log.name, log.shortname
    log('a','b','c')
    log.indent()
    log('this should be indented')
    log('aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa')
    log.dedent()
    list1 =  ['unindent here',
        'bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb',
        'ccccccccccccc',
        'ddddddddddddddddddddddddddddddddddddddd',
        'ddddddddddddddddddddddddddddddddddddddd',
        'ddddddddddddddddddddddddddddddddddddddd',
        'ddddddddddddddddddddddddddddddddddddddd',
        'ddddddddddddddddddddddddddddddddddddddd',
        'ddddddddddddddddddddddddddddddddddddddd'
        ]
    for line in list1:
        log(line)
    terminal('this to terminal')
