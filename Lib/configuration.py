"""
Configuration and command-line processing.

Attributes include SYS_TYPE, MACHINE_TYPE, MACHINE_DIR, BATCH_TYPE, usage, 
options, defaultExecutable, inputFiles, timelimit, machine, batchmachine,
ATSROOT, cuttime, log.
     
The log object is created by importing log, but it can't write to a file 
until we process the options and get the desired properties.
"""
import os, sys, socket
import version, atsut
from optparse import OptionParser
from atsut import debug, AttributeDict, abspath
from log import log, terminal
from times import atsStartTime, Duration
import machines
import executables

SYS_TYPE = os.environ.get('SYS_TYPE', sys.platform)
config_directory = os.path.abspath(__file__)
full_path = config_directory.split(os.sep)
lib_dir_index = full_path.index('lib')
machine_dir = os.path.sep.join(full_path[:lib_dir_index])

MACHINE_DIR = abspath(os.environ.get('MACHINE_DIR', 
                             os.path.join(machine_dir, 'atsMachines')))
MACHINE_TYPE = os.environ.get('MACHINE_TYPE', SYS_TYPE)
BATCH_TYPE = os.environ.get('BATCH_TYPE', SYS_TYPE)

def addOptions(parser):
    """Note on default:

* default type is string if no type is specified.
* default action is store if no action is specified.
* default dest is name of long option string and if no long option,
  then short option name if dest is not specified.
"""
    parser.add_option(
        '--allInteractive', action='store_true', dest='allInteractive', default=False,
        help='Run every test in interactive mode.')

    parser.add_option(
        '--cutoff', dest='cuttime', default=None,
        help="""Set the cutoff time limit on each test. The value may be given 
as a digit followed by an s, m, or h to give the time in 
seconds, minutes (the default), or hours. This value if 
given causes jobs to fail with status HALTED if they 
run this long and have not already timed out or finished."""
        )
                      
    parser.add_option(
        '--debug', action='store_true', dest='debug', default = False,
        help='debug level; set to 1 or more for more output')

    parser.add_option(
        '-e', '--exec', dest='executable', metavar='EXEC', default=sys.executable,
        help='Set code to be tested.')

    parser.add_option(
        '-f', '--filter', action='append', dest='filter', default = [],
        help="""add a filter; may be repeated. Be sure to use quotes if the filter contains spaces and remember that the shell will remove one level of quotes. 
Example: --filter 'np>2' 
would run only jobs needing more than 2 processors.""")

    parser.add_option(
        '-g', '--glue', action='append', dest='glue', default = [],
        help="""set the default value for a test option; may be repeated. Be sure to use quotes if the value contains spaces and remember that the shell will remove one level of quotes. Equivalent to using a glue
statement at the start of the input.""")

    parser.add_option(
        '--hideOutput', action='store_true', dest='hideOutput', default=False,
        help = 'Do not print "magic" output lines in log.')

    parser.add_option(
        '-i', '--info', action='store_true', dest='info', default = False,
        help='Show extra information about options and machines.')

    parser.add_option(
        '-k', '--keep', action='store_true', dest='keep', default = False,
        help='keep the output files')

    parser.add_option(
        '--logs', dest='logdir', default='',
        help='sets the directory of the log file. Default is arch.time.logs, where arch will be an architecture-dependent name, and time will be digits of the form yymmddhhmmss.')

    parser.add_option('--level', dest='level', 
        help='Set the maximum level of test to run.')

    parser.add_option('-n', '--npMax', dest = 'npMax', type="int", default=0,
        help="Max number of tests to run at once (on a node, if multinode)")

    parser.add_option(
        '--okInvalid', action='store_true', dest='okInvalid', default=False,
        help='Run tests even if there is an invalid test.')

    parser.add_option(
        '--oneFailure', action='store_true', dest='oneFailure', default = False,
        help='Stop if a test fails.')

    parser.add_option (
        '--serial', action='store_true', dest='serial', default=False,
        help='Run only one job at a time.') 

    parser.add_option(
        '--skip', action='store_true', dest='skip',  default = False,
        help='skip actual execution of the tests, but show filtering results and missing test files.')

    parser.add_option(
        '-t', '--timelimit', dest='timelimit', default='29m',
        help="""Set the default time limit on each test. The value may be given 
as a digit followed by an s, m, or h to give the time in seconds, minutes 
(the default), or hours."""
        )

    parser.add_option(
        '-v', '--verbose', action='store_true', dest='verbose', default=False,
        help='verbose mode; increased level of terminal output')

def documentConfiguration():
     """Write the configuration to the log."""
     log('Configuration:')
     log.indent()
     log('Input files:',  inputFiles)
     log('Python path:', sys.executable)
     log('ATS from ', os.path.dirname(__file__))
     log('ATS version:', version.version)
     log('Options:')
     log.indent()
     olist = options.keys()
     olist.sort()
     for k in olist:
         log(k + ":", repr(getattr(options, k)))
     log.dedent()
     log.dedent()

def init(clas = '', adder = None, examiner=None):
    """Called by manager.init(class, adder, examiner)
       Initialize configuration and process command-line options; create log,
       options, inputFiles, timelimit, machine, and batchmatchine.
       Call backs to machine and to adder/examiner for options.
    """
    global log, options, inputFiles, timelimit, machine, batchmachine,\
           defaultExecutable, ATSROOT, cuttime
# get the machine and possible batch facility
    machineDir = MACHINE_DIR
    machineList = [x for x in os.listdir(machineDir) if x.endswith('.py')]
    sys.path.insert(0, machineDir)
    machine = None
    batchmachine = None
    specFoundIn = ''
    bspecFoundIn = ''

    for fname in machineList:
        moduleName = ''
        full_path = os.path.join(machineDir, fname)
        f = open(full_path, 'r')
        for line in f:
            if line.startswith('#ATS:'):
                items = line[5:-1].split()
                machineName, moduleName, machineClass, npMaxH = items
                
                if machineName == MACHINE_TYPE:
                    if moduleName == "SELF":
                        moduleName, junk = os.path.splitext(fname)
                    specFoundIn = full_path
                    exec('from %s import %s as Machine' % (moduleName, machineClass))
                    machine = Machine(machineName, int(npMaxH))
                  
            elif line.startswith('#BATS:'):
                items = line[6:-1].split()
                machineName, moduleName, machineClass, npMaxH = items
            
                if machineName == BATCH_TYPE:
                    if moduleName == "SELF":
                        moduleName, junk = os.path.splitext(fname)
                    bspecFoundIn = full_path
                    exec('from %s import %s as BMachine' % (moduleName, machineClass))
                    batchmachine = BMachine(moduleName, int(npMaxH))
                   
        f.close()
        
        if machine and batchmachine:
            break

    if machine is None:
        terminal("No machine specifications for", SYS_TYPE, "found, using generic.")
        machine = machines.Machine('generic', -1)
        
# create the option set
    usage = "usage: %prog [options] [input files]"
    parser = OptionParser(usage=usage, version="%prog " + version.version)
    addOptions(parser)
    machine.addOptions(parser)
# add the --nobatch option but force it true if no batch facility here.
    parser.add_option(
        '--nobatch', action='store_true', dest='nobatch', default=(batchmachine is None),
        help = 'Do not run batch jobs.')
    if batchmachine:
        batchmachine.addOptions(parser)
# user callback?
    if adder is not None: 
        adder(parser)
# parse the command line
    if clas:
        import shlex
        argv = shlex.split(clas)
    else:
        argv = sys.argv[1:]
    (toptions, inputFiles) = parser.parse_args(argv)

# immediately make the options a real dictionary -- the way optparse leaves it
# is misleading.
    options = AttributeDict()
    for k in vars(toptions).keys():
        options[k] = getattr(toptions, k)
    
# let the machine(s) modify the results or act upon them in other ways.
    machine.examineOptions(options)
    if batchmachine:
        batchmachine.examineOptions(options)
# unpack basic options
    debug(options.debug)
    if options.logdir:
        log.set(directory = options.logdir)
    else:
        dirname = SYS_TYPE + "." + atsStartTime + ".logs"
        log.set(directory = dirname)
    log.mode="w"
    log.logging = 1
# user callback?
    if examiner is not None: 
        examiner(options)

    if specFoundIn:
        log("Found specification for", MACHINE_TYPE, "in", specFoundIn)
    else:
        log("No specification found for", MACHINE_TYPE, ', using generic')
    if bspecFoundIn:
        log("Batch specification for ", BATCH_TYPE, "in", bspecFoundIn)

# unpack other options
    cuttime = options.cuttime
    if cuttime is not None:
        cuttime = Duration(cuttime)
    timelimit = Duration(options.timelimit) 
    defaultExecutable = executables.Executable(abspath(options.executable))
    # ATSROOT is used in tests.py to allow paths pointed at the executable's directory
    commandList = machine.split(repr(defaultExecutable))
    if os.environ.has_key('ATSROOT'):
        ATSROOT = os.environ['ATSROOT']
    else:
        ATSROOT = os.path.dirname(defaultExecutable.path)

