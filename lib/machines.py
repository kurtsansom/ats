"""Definition of class Machine for overriding. 
"""
import subprocess, sys, os, time, shlex
from .atsut import debug, RUNNING, TIMEDOUT, PASSED, FAILED, \
     CREATED, SKIPPED, HALTED, EXPECTED, statuses, AttributeDict, AtsError
from . import configuration
from .log import log, terminal, AtsLog

def comparePriorities (t1, t2): 
    "Input is two tests; return comparison based on totalPriority."
    return t2.totalPriority - t1.totalPriority

class MachineCore(object):
    """Invariable parts of a machine. Not capable of being instantiated"""
    def label(self):
        return '%s(%d)' % (self.name, self.numberTestsRunningMax)

    def split(self, astring):
        "Correctly split a clas string into a list of arguments for this machine."
        return shlex.split(astring)
        
    def calculateBasicCommandList(self, test): 
        """Prepare for run of executable using a suitable command. 
           Returns the plain command line that would be executed on a vanilla 
           serial machine. 
        """
        return test.executable.commandList + test.clas

    def examineBasicOptions(self, options):
        "Examine options from command line, possibly override command line choices."
        if options.serial:
            self.numberTestsRunningMax = 1
        elif self.hardLimit:
            if options.npMax > 0:
                self.numberTestsRunningMax = min(self.numberTestsRunningMax, 
                                                 options.npMax)
        else:
            if options.npMax > 0:
                self.numberTestsRunningMax = options.npMax

    def checkForTimeOut(self, test):
        """ Check the time elapsed since test's start time.  If greater
        then the timelimit, return true, else return false.  test's
        end time is set if time elapsed exceeds time limit """
        timeNow= time.time()
        timePassed= timeNow - test.startTime
        cut = configuration.cuttime
        if (timePassed < 0):         # system clock change, reset start time
            test.setStartTimeDate()
        elif (timePassed >= test.timelimit.value):   # process timed out
            return 1
        elif cut is not None and timePassed >= cut.value:
            return -1
        return 0

    def checkRunning(self):
        """Find those tests still running. getStatus checks for timeout.
        """
        time.sleep(self.naptime)
        stillRunning = []
        for test in self.running:
             done = self.getStatus(test)
             if not done:
                 stillRunning.append(test)
             else:   # test has finished
                 if test.status is not PASSED:
                     if configuration.options.oneFailure:
                         raise AtsError("Test failed in oneFailure mode.")
        self.running = stillRunning

    def remainingCapacity(self):
        """How many processors are free? Could be overriden to answer the real question,
what is the largest job you could start at this time?"""
        return self.numberTestsRunningMax - self.numberTestsRunning

    def getStatus (self, test): 
        """
Override this only if not using subprocess (unusual).
Obtains the exit code of the test object process and then sets
the status of the test object accordingly. Returns True if test done.
           
When a test has completed you must set test.statusCode and
call self.testEnded(test, status). You may add a message as a third arg,
which will be shown in the test's final report.
testEnded will call your bookkeeping method noteEnd.
"""
        test.child.poll()
        if test.child.returncode is None: #still running, but too long?
            overtime = self.checkForTimeOut(test)
            if overtime != 0:
                self.kill(test)
                test.statusCode=2
                test.setEndDateTime()
                if overtime > 0:
                    status = TIMEDOUT
                else:
                    status = HALTED  #one minute mode
            else:
                return False
        else:
            test.setEndDateTime()
            test.statusCode = test.child.returncode
            if test.statusCode == 0:                               # process is done
                status = PASSED
            else:
                status= FAILED
        self.testEnded(test, status)
        return True

    def testEnded(self, test, status):
        """Do book-keeping when a job has exited; 
call noteEnd for machine-specific part.
"""
        self.numberTestsRunning -= 1
        test.set(status, test.elapsedTime())  
           #note test.status is not necessarily status after this!
           #see test.expectedResult
        self.noteEnd(test)  #to be defined in children
# now close the outputs
        test.outhandle.close()
        test.errhandle.close()
        self.scheduler.testEnded(test)
        
    def kill(self, test): # override if not using subprocess
        "Kill the job running test."
        if test.child:
            test.child.kill()
            test.outhandle.close()
            test.errhandle.close()

    def launch (self, test): 
        """Start executable using a suitable command. 
           Return True if able to do so.
           Call noteLaunch if launch succeeded."""
        test.commandList = self.calculateCommandList(test)
        test.commandLine = " ".join(test.commandList)

        if configuration.options.skip:
            test.set(SKIPPED, "--skip option")
            return False

        test.setStartDateTime()
        result = self._launch(test)
        if result:
            self.noteLaunch(test)
        return result

    def _launch(self, test): 
        """Replace if not using subprocess (unusual).
The subprocess part of launch. Also the part that might fail.
"""
        try:
            test.outhandle = open(test.outname, 'w')
            test.errhandle = open(test.errname, 'w')
            Eadd = test.options.get('env', None)
            if Eadd is None:
                E = None
            else:
                E = os.environ.copy()
                E.update(Eadd)
            test.child = subprocess.Popen(test.commandList, cwd=test.directory, 
                   stdout = test.outhandle, stderr = test.errhandle, env=E)
            test.set(RUNNING, test.commandLine)
            self.running.append(test)
            self.numberTestsRunning += 1
            return True
        except OSError as e:
            test.outhandle.close()
            test.errhandle.close()
            test.set(FAILED, str(e))
            return False
   
    def startRun(self, test):
        """For interactive test object, launch the test object.
           Return True if able to start the test.
        """
        self.runOrder += 1
        test.runOrder = self.runOrder 
        return self.launch(test)


#### end of MachineCore

class Machine (MachineCore):
    """Class intended for override by specific machine environments.
Some methods are possible overrides.
Usually the parent version should be called too.
To call the parent version of foo: super(YourClass, self).foo(args)
However, the most important methods have a "basic" verison you can just call.
You can call your class anything, just put the correct comment line at 
the top of your machine. See documentation for porting.
"""
    def __init__(self, name, npMaxH):   
        """Be sure to call this from child if overridden

Initialize this machine. npMax supplied by __init__, hardware limit.
If npMax is negative, may be overridden by command line. If positive,
is hard upper limit.
"""
        self.name =  name
        self.numberTestsRunning = 0
        self.numberTestsRunningMax = max(1, abs(npMaxH))
        self.hardLimit = (npMaxH > 0)
        self.naptime = 0.2 #number of seconds to sleep between checks on running tests.
        self.running = []
        self.runOrder = 0
        from . import schedulers
        self.scheduler = schedulers.StandardScheduler()
        self.init()

    def init(self):  
        "Override to add any needed initialization."
        pass

    def addOptions(self, parser): 
        "Override to add  options needed on this machine."
        pass

    def examineOptions(self, options): 
        """Examine options from command line, possibly override command line choices.
           Always call examineBasicOptions
        """
        self.examineBasicOptions(options)
            
 
    def calculateCommandList(self, test): 
        """Prepare for run of executable using a suitable command. 
If overriding, get the vanilla one from ``calculateBasicCommand``,
then modify if necessary.
        """
        return self.calculateBasicCommandList(test)

    def periodicReport(self):
        "Make the machine-specific part of periodic report to the terminal."
        terminal(len(self.running), "tests running on", self.numberTestsRunning, 
              "of", self.numberTestsRunningMax, "processors.")

    def canRun(self, test): 
        """
A child will almost always replace this method.

Is this machine able to run the test interactively when resources become 
available?  If so return ''.

Otherwise return the reason it cannot be run here.
"""
        if test.np > 1:   #generic machine serial only
            return "Too many processors needed (%d)" % test.np
        return ''

    def canRunNow(self, test): 
        """
A child will almost replace this method. No need to call parent version.

Is this machine able to run this test now? Return True/False.
If True is returned, an attempt will be made to launch. noteLaunch will be
called if this succeeds.
"""
        return self.numberTestsRunning  + 1 <= self.numberTestsRunningMax

    def noteLaunch(self, test): 
        """
A child will almost replace this method. No need to call parent version.

test has been launched. Do your bookkeeping. numberTestsRunning has already 
been incremented.
"""
        pass

    def noteEnd(self, test): 
        """
A child will almost replace this method. No need to call parent version.

test has finished running. Do any bookkeeping you need. numberTestsRunning has
already been decremented.
"""
        pass
    
    def quit(self): 
        """
A child might replace this method. No need to call parent version.
Final cleanup if any.
        """
        pass

    def getResults(self):
        """
A child might replace this to put more information in the results,
but probaby wants to call the parent and then update the
dictionary this method returns.

Return AttributeDict of machine-specific facts for manager postprocessing state.
Include results from the scheduler.
"""
        result = AttributeDict()
        result.update(self.scheduler.getResults())
        result.update( 
           dict(name=self.name, 
           numberTestsRunningMax = self.numberTestsRunningMax,
           hardLimit = self.hardLimit,
           naptime = self.naptime)
           )
        return result

class BatchFacility(object):
    """Interface to a batchmachine"""
    def init(self):
        pass

    def getResults(self):
        "Return machine-specific facts for manager postprocessing state."
        return AttributeDict(name=self.label())

    def label(self):
        "Return a name for this facility."
        return ''

    def addOptions(self, parser):
        "Add batch options to command line (see optparser)"
        pass

    def examineOptions(self, options):
        "Examine the options."
        pass

    def load(self, testlist):
        "Execute these tests"
        return

    def quit(self):
        "Called when ats is done."
        pass

        
class BatchSimulator(BatchFacility):
    """
A fake batch you can use for debugging input by setting::

    BATCH_TYPE=batchsimulator

"""
    def label(self):
        return "BatchSimulator"

    def __init__(self, name, npMaxH):   
        self.name =  name
        self.npMaxH = npMaxH
        self.np = npMaxH
        
    def load(self, batchlist):
        "Simulate the batch system"
        log("Simulation of batch load:",  echo=True)
        for t in batchlist:
            log(t, echo=True)
