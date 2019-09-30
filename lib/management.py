import os, sys, time, tempfile, traceback, socket
from . import configuration, version
from .atsut import INVALID, PASSED, FAILED, SKIPPED, BATCHED, \
                  RUNNING, FILTERED, CREATED, TIMEDOUT, HALTED, EXPECTED,\
                  abspath, AtsError, is_valid_file, debug, statuses, \
                  expandpath, AttributeDict
from .times import hms, datestamp, Duration, wallTime, atsStartTime, \
                  atsStartTimeLong
from .tests import AtsTest
from .log import log, terminal

def standardIntrospection(line):
    "Standard magic detector for input."
    if line.startswith("#ATS:"):
        return line[5:]
    else:
        return None

def areBrothers(t1, t2):
    "are two tests part of a set of related tests?"
    if t1.group is t2.group:
        return True
    elif t1 in t2.dependents or t2 in t1.dependents:
        return True
    else:
        return False

class AtsManager (object):
    """This class is instantiated as a singleton instance, manager.

The principal entry is ``main``. 

Attributes:

* filters -- list of filters to be applied in choosing tests.
* testlist (readonly) -- list of tests processed.
* badlist (readonly) -- list of tests that could not be sourced properly
* started -- date time of initialization
* collectTimeEnded -- when test collection was done
* onExitRoutines -- list of routines for onExit to call
* onResultsRoutines -- list of routines for onResults to call
* continuationFileName -- "continue.ats" if written
* saveResultName -- default "atsr.py"
* groups -- dictionary of test group objects indexed by number

    """
    def __init__ (self):
        self.restart()

    def restart(self):
        "Reinitialize basic data structures."
        self.started = datestamp(int=1)
        self.collectTimeEnded = self.started
        self.filters = []
        self.testlist = []
        self.badlist = []
        self.onExitRoutines = []
        self.onResultsRoutines = []
        self.continuationFileName = ''
        self.saveResultsName = "atsr.py"
        #self.groups = {}
        AtsTest.restart()

    def filter (self, *filters):
        "Add filters to the list. Clear list if no arguments."
        if not filters:
            self.filters = []
            log('Filter list empty.', echo=self.verbose)
            return

        for f in filters:
            try:
                f = str(f)
            except Exception:
                raise AtsError("filter must be convertible to string")
            if not f:
                continue
            try:
                r = eval(f, {}, {})
            except SyntaxError:
                raise AtsError('Mal-formed filter, %s' % repr(f))
            except KeyboardInterrupt:
                raise
            except Exception:
                pass
            self.filters.append(f)
            log ('Added filter:', repr(f))

    def filterenv (self, test):
        """Compute the environment in which filters for test will be 
            evaluated.""" 
        if not isinstance(test, AtsTest):
            raise AtsError('filterenv argument must be a test instance.')
        fe = {}
        for f in _filterwith:
            exec(f, fe)
        fe.update(test.options)
        fe.update(testEnvironment)
        return fe

    def find_unmatched (self, test):
        """Does this manager's filters match the given test properties?
        Returns '' if it does, the filter that failed if not.
        """
        fe = self.filterenv(test)
        fe['SELF'] = test
        for f in self.filters:
            try:
                if eval(f, {}, fe.copy()):
                    pass
                else:
                    if debug():
                        log('Filter %s did not pass.'% repr(f))
                    return f
            except KeyboardInterrupt:
                raise
            except Exception as e:
                if debug():
                    log('In filter %s:'% repr(f), e)
                return f
        return ''

    def logDefinitions(self, *words, **options):
        """Log the current definitions of words; if none given show all.
         options passed to log (echo, logging)
        """
        logging = options.get('logging', True)
        echo = options.get('echo', True)
        log("Test environment symbols:", logging=logging, echo=echo)
        log.indent()
        if not words: 
            words = sorted(list(testEnvironment.keys()))
        for key in words:
            try:
                log(key,":", testEnvironment[key], logging=logging, echo=echo)
            except KeyError:
                log("Not defined:", key, logging=logging, echo=echo)
        log.dedent()

    def define(self, **definitions):
        "Define symbols for input files."
        testEnvironment.update(definitions)

    def undefine(*args):
        "Remove one or more symbols for input files."
        for x in args:
            if x in testEnvironment:
                del testEnvironment[x]

    def get(self, name):
        """Return the definition of name from the test environment. 
        """
        if name in testEnvironment:
            return testEnvironment.get(name)

        raise AtsError("Could not find name %s in vocabulary." % name)   
        
    alreadysourced = []

    def source (self, *paths, **vocabulary):
        """Input one or more source files, with optional additional vocabulary.
         If introspection=f given in the vocabulary, or using define,
         it should be a function taking one argument and returning any
         introspective portion of it.
        """
        if debug():
            log("source:", ' '.join(paths), echo=True)

        introspector = vocabulary.get('introspection', 
                   testEnvironment.get('introspection', standardIntrospection))

        for path in paths:
            self._source(path, introspector, vocabulary) 

    def _source(self, path, introspector, vocabulary):
        "Process source file. Returns true if successful"
        here = os.getcwd()
        t = abspath(path)
        directory, filename = os.path.split(t)
        name, e = os.path.splitext(filename)
        if e: 
            namelist = [t]
        else:
            namelist = [t, t+'.ats', t+'.py']
        for t1 in namelist:
            if t1 in AtsManager.alreadysourced:
                log("Already sourced:", t1)
                return
            try:
                f = open(t1)
                break
            except IOError as e:
                pass
        else:
            log("Error opening input file:", t1, echo=True)
            self.badlist.append(t1)
            raise AtsError("Could not open input file %s" % path)
        t = abspath(t1)
        directory, filename = os.path.split(t1)
        name, e = os.path.splitext(filename)
        AtsManager.alreadysourced.append(t1)
        # save to restore after this file is read
        savestuck = dict(AtsTest.stuck)
        savetacked = dict(AtsTest.tacked)
        unstick() #clear sticky list at the start of a file.
        AtsTest.waitNewSource()
        
        testenv = dict(testEnvironment)
        testenv.update(vocabulary)
        testenv['SELF'] = t1
        atstext = []
        for line1 in f:
            if not line1: continue
            if line1.startswith('#!'):
                continue
            magic = introspector(line1[:-1])
            if magic is not None:
                atstext.append(magic)
        f.close()
        if atstext:
            log('-> Executing statements in', t1, echo=False)
            log.indent()
            code = '\n'.join(atstext)
            if debug():
                for line in atstext:
                    log(line, echo=False)
            os.chdir(directory)
            try:
                exec(code, testenv)
                if debug(): 
                    log('Finished ', t1, datestamp())
            except KeyboardInterrupt:
               raise
            except Exception as details:
                self.badlist.append(t1)
                log('Error while processing statements in', t1, ':', echo=True)
                log(details, echo=True)
            log.dedent()
        else:
            log('-> Sourcing', t1, echo=False)
            log.indent()
            os.chdir(directory)
            try:
                exec(compile(open(t1, "rb").read(), t1, 'exec'), testenv)
                if debug(): log('Finished ', t1, datestamp())
                result = 1
            except KeyboardInterrupt:
                raise
            except Exception as details:
                self.badlist.append(t1)
                log('Error in input file', t1, ':', echo=True)
                log(details, echo=True)
                log('------------------------------------------', echo=True)
            log.dedent()
        AtsTest.endGroup()   
        unstick()
        stick(**savestuck)
        untack()
        tack(**savetacked)
        AtsTest.waitEndSource()
        os.chdir(here)

    def onExit(self, routine):
        "Call postprocessing routine before exiting with argument manager."
        self.onExitRoutines.append(routine)

    def finalReport(self):
        "Write the final report."
        log.reset()
        if self.testlist:
            log("""
=========================================================
ATS RESULTS %s""" % datestamp(int=1), echo = True)
            log('-------------------------------------------------',
                echo = True)
            self.report()
            log('-------------------------------------------------',
                echo = True) 
        if not configuration.options.skip:
            log("""
ATS SUMMARY %s""" % datestamp(int=1), echo = True)
            self.summary(log)
            self._summary2(log)
            
    def finalBanner(self):
        "Show final banner."
        log.logging = 1
        log.echo = True
        log("ATS WALL TIME", wallTime())
        log("ATS COLLECTION END", self.collectTimeEnded)
        log('ATS END', datestamp(int=1))
        log('ATS MACHINE TYPE', configuration.MACHINE_TYPE)
        if configuration.batchmachine is not None:
            log('ATS BATCH TYPE', configuration.BATCH_TYPE)
        log('ATS OUTPUT DIRECTORY', log.directory)
        if self.continuationFileName:
            log("ATS CONTINUATION FILE", self.continuationFileName, echo=True)
        log('ATS LOG FILE', log.name)
        log('ATS END OF RUN STARTED', self.started)
        
    def report (self):
        "Log a report, showing each test."
        doAll = debug() or \
               configuration.options.skip or \
               configuration.options.verbose

        outputCaptured = False
        for test in self.testlist:
            if test.output:
                outputCaptured = True

        if outputCaptured and not configuration.options.hideOutput:
            log("NOTICE:", "Captured output, see log.", echo=True, logging = False)

        for test in self.testlist:
            if doAll or test.notes or test.groupSerialNumber ==1 or \
                test.group.echoStatus() or test.options.get('record', False): 
                echo = True
            else:
                echo = False

            log("#%d %s %s %s (Group %d #%d)" % \
                   (test.serialNumber, test.status, test.name, test.message,
                    test.group.number, test.groupSerialNumber),
                    echo=echo)

            for line in test.notes:
                    log("NOTE:", line, echo=echo)

            log.indent()
            if debug() or configuration.options.skip:
                log([t.serialNumber for t in test.waitUntil], echo=False)
            log.dedent()

    def summary (self, log):
        "Log summary of the results."
        tlist = [t for t in self.testlist if t.options.get('report', True)]
        failed = [test.name for test in self.testlist if (test.status is FAILED)]
        timedout = [test.name for test in self.testlist if (test.status is TIMEDOUT)]
        ncs = [test for test in self.testlist \
             if (test.status is PASSED and test.options.get('check', False))]
        passed = [test.name for test in tlist \
                  if (test.status is PASSED and test not in ncs)]
        running = [test.name for test in self.testlist if (test.status is RUNNING)]
        halted = [test.name for test in self.testlist if (test.status is HALTED)]
        expected = [test.name for test in self.testlist if (test.status is EXPECTED)]
        if running:
            log("""\
RUNNING: %d %s""" % (len(running), ', '.join(running)), echo=True)

        if ncs: 
            log("""\
CHECK:    %d %s""" % (len(ncs), ', '.join([test.name for test in ncs])),
               echo = True)

        log("FAILED:   %d %s" % (len(failed), ', '.join(failed)),
               echo = True)
        if timedout:
            log("TIMEOUT:  %d %s" % (len(timedout), ', '.join(timedout)),
               echo = True)
        if halted:
            log("HALTED:   %d" % len(halted),
               echo = True)
        if expected:
            log("EXPECTED:   %d" % len(expected),
               echo = True)
        log("PASSED:   %d" % len(passed),
               echo = True)

        notrun = [test.name for test in self.testlist if (test.status is CREATED)]
        lnr = len(notrun)
        if notrun:
            log("""NOTRUN:   %d""" % len(notrun),
               echo = True)

    def _summary2(self, log):
        "Additional detail for  summary."
        tlist = [t for t in self.testlist if t.options.get('report', True)]
        invalid = [test.name for test in self.testlist if (test.status is INVALID)]
        batched = [test.name for test in tlist if (test.status is BATCHED)]
        skipped = [test.name for test in tlist if (test.status is SKIPPED)]
        filtered = [test.name for test in tlist if (test.status is FILTERED)]
        bad = self.badlist

        if invalid:
            log("INVALID:  %d %s" % (len(invalid) + len(bad), ', '.join(bad + invalid)),
               echo = True)
        if batched:
            log("BATCHED:  %d" % len(batched),
               echo = True) 
        if filtered:
            log("FILTERED: %d" % len(filtered),
               echo = True)
        if skipped:
            log("SKIPPED:  %d" % len(skipped),
               echo = True) 

    def test(self, *clas, **options):
        """Create one test. Signature is zero to two positional arguments,
then keyword / value options::

    test(**options) or
    test(script, **options) or
    test(script, clas, **options) 

See manual for discussion of these arguments.
"""
        testobj = AtsTest(*clas, **options)
        self.testlist.append(testobj)
#        if not self.groups.has_key(testobj.groupNumber):
#            self.groups[testobj.groupNumber] = testobj.group

        SYSTEMS = testobj.options.get('SYSTEMS', [self.machine.name])
        if testobj.status in (CREATED, BATCHED):
            if self.machine.name not in SYSTEMS:
                msg =  'Machine %s not in test SYSTEM list %s' % \
                   (self.machine.name, repr(SYSTEMS))
                testobj.set(FILTERED, msg)
                return testobj
            if testobj.np > self.machine.numberTestsRunningMax:
                testobj.set(FILTERED, 
"Number of processors %d exceeds %d"% (testobj.np, self.machine.numberTestsRunningMax))
                return testobj

# process filters
            unmatched = self.find_unmatched(testobj)
            if unmatched:
                testobj.set(FILTERED, "Does not satisfy: %s" % unmatched)

        log(testobj.status, "#%d"% testobj.serialNumber, testobj.name, 
            testobj.message, echo=self.verbose)
        return testobj

    def testif(self, parent, *clas, **options):
        "Create test, to be run only if othertest passed."
        testobj = self.test(*clas, **options)
        parent.addDependent(testobj)
        return testobj

    def collectTests(self):
        """Process the input and collect the tests to be executed.
We immediately make sure each input file exists and is readable.
(If we don't we might not find out until many tests have run.)
"""
        # It is worth settling this now.
        if debug():
            log("Checking that input files exist.")
        files = []
        for input_file in self.inputFiles:
            t = abspath(input_file)
            dir, filename = os.path.split(t)
            name, e = os.path.splitext(filename)
            if e: 
                namelist = [t]
            else:
                namelist = [t, t+'.ats', t+'.py']
            for t1 in namelist:
                try:
                    f = open(t1, 'r')
                    break
                except IOError:
                    pass
            else:
                log.fatal_error('Cannot open %s.' % t)
            f.close()
            files.append(t1)

        log("Input ok. Now collect the tests.")
        # Now collect the tests.   
        for t in files:
            self.source(t)

# Stop the execution of ats when the first INVALID test is found unless option --okInvalid.
        log.indent()
        found = False
        for item in self.badlist:
            found = True
            log('Bad file:', item, echo=True)
        for test in self.testlist:
            if test.status is INVALID:
                found = True
                log(test.status, "#%d"%test.serialNumber, test.name, echo=True)
        log.dedent()

        if found:
            log('************************************************', echo = True)
            log('NOTE: Invalid tests or files', echo = True)
            if not configuration.options.okInvalid:
                log.fatal_error("Fix invalid tests or rerun with --okInvalid.")

# Make sure that every test has distinct name
        testnames = [t.name.lower() for t in self.testlist]
        for i in range(len(testnames)):
            name = testnames[i]
            while testnames.count(name) > 1:
                count = 1
                for j in range(i+1, len(testnames)):
                    if testnames[j] == name:
                        count += 1
                        t = self.testlist[j]
                        t.name += ("#%d" % count)
                        testnames[j] = t.name.lower()

# Add parents to each test's waitlist.
        for t in self.testlist:
            if t.status is CREATED:
                for d in t.dependents:
                    if t not in d.waitUntil:
                        d.waitUntil = d.waitUntil + [t]

        log.leading = ''
        log("------------------ Input complete --------", echo=True)
        echo =  configuration.options.verbose or \
                debug() or \
                configuration.options.skip
        for t in self.testlist:
            log(repr(t), echo=echo)
   
    def sortTests(self):
        """Sort the tests as to batch or interactive or other. Return two lists."""

# tests that were invalid, filtered, skipped etc. have status not CREATED
# This screens out things that recently got set SKIPPED, etc.

        interactiveTests = [t for t in self.testlist if t.status is CREATED]
        batchTests = [t for t in self.testlist if t.status is BATCHED]

# postcondition
        if (batchTests and (configuration.options.nobatch or \
                            configuration.options.allInteractive)):
            for t in batchTests:
                log( t, "BATCH sorting error.", echo=True)
            raise ValueError('batch test should not exist')
      
        return interactiveTests, batchTests
    

    def main(self, clas = '', adder=None, examiner=None):
        """
This is the main driver code. 
Returns true if all interactive tests found passed, false if interrupted or 
an error occurs.

``clas`` is a string containing command-line options, such as::

    --debug --level 18

If ``clas`` is blank, sys.argv[1:] is used as the arguments. 
See ``configuration.init``.

Routines ``adder`` and ``examiner``, if given,  are called in ``configuration`` 
to allow user a chance to add options and examine results of option parsing.
"""
        self.init(clas, adder, examiner)
        self.firstBanner()
        self.core()
        self.postprocess()
        self.finalReport()
        self.saveResults()
        self.finalBanner()

    def postprocess(self):
        "Call onExitRoutines."
        for r in self.onExitRoutines:
            log(" --------- Calling %s --------" % r.__name__, echo=True)
            try:
                r(self)
            except Exception as details:
                log(details, echo = True)
            except KeyboardInterrupt:
                log("Keyboard interrupt while in exit phase, terminating.", echo=True)
                return
            log("-------------------------------", echo=True)

    def init(self, clas = '', adder=None, examiner=None):
        """This initialization is separate so that unit tests can be done on this module.
            For this reason we delay any logging until main is called.
            adder and examiner are called in configuration if given to allow user
            a chance to add options and see results of option parsing.
        """
        tempfile.tempdir = os.getcwd()
        configuration.init(clas, adder, examiner)
        self.options = configuration.options
        self.inputFiles = configuration.inputFiles
        self.machine = configuration.machine
        self.batchmachine = configuration.batchmachine
        
        if configuration.options.nobatch:
            self.batchmachine = None 
        self.verbose = configuration.options.verbose or debug()
        log.echo = self.verbose
        self.started = datestamp(int=1)
        self.continuationFileName = ''
        self.atsRunPath = os.getcwd()
        for a in configuration.options.filter:
            self.filter(a)
        for a in configuration.options.glue:
            a= a.strip('"').strip("'")
            exec('AtsTest.glue(%s)' % a)
        if configuration.options.level:
            self.filter("level<= %s" % configuration.options.level)
        
    def firstBanner(self):
        "Write the opening banner."     
        log.echo = True
        log('ATS START', atsStartTimeLong)
        log('ATS VERSION', version.version)
        log('ATS HOST NAME:', socket.gethostname())
        log('ATS LOG DIRECTORY:', log.directory)
        log('SYS_TYPE:', configuration.SYS_TYPE)
        log('MACHINE_TYPE', configuration.MACHINE_TYPE)
        log('BATCH_TYPE', configuration.BATCH_TYPE)
        log("Machine description: ", self.machine.label(), echo=True)
        if self.batchmachine:
            log("Batch facility name:", self.batchmachine.label(), echo=True)
        else:
            log("No batch facility found.", echo=True)

        if configuration.options.info or debug():
            configuration.documentConfiguration()
            
        log.echo = self.verbose
        if configuration.options.oneFailure:
            log('Will stop after first failure.') 
    
        if configuration.options.allInteractive:
            log('Will run all tests (including any batch tests) as interactive.')

        log('Default time limit for each test=', 
            Duration(configuration.timelimit))

    def core(self):
        "This is the 'guts' of ATS."

# Phase 1 -- collect the tests
        errorOccurred = False
        try:   # surround with keyboard interrupt, AtsError handlers
            self.collectTests()
             
        except AtsError:
            log("ATS error while collecting tests.", echo=True)
            log(traceback.format_exc(), echo=True)
            errorOccurred = True
            self.collectTimeEnded = datestamp(int=1)

        except KeyboardInterrupt:
            log("Keyboard interrupt while collecting tests, terminating.", echo=True)
            errorOccurred = True

        self.collectTimeEnded = datestamp(int=1)
        if errorOccurred:
            return
        
# divide into interactive and batch tests
        interactiveTests, batchTests = self.sortTests()
        if len(interactiveTests) + len(batchTests) == 0:
            log("No tests found.", echo = True)
            return

# Phase 2 -- dispatch the batch tests
        
        if self.batchmachine and batchTests:
            if configuration.options.skip:
                log("Skipping execution due to --skip")
            else:
                try:
                    log("Sending %d tests to %s." % (len(batchTests), self.batchmachine.name),
                        echo = True)
                    self.batchmachine.load(batchTests)
                except AtsError:
                    log(traceback.format_exc(), echo=True)
                    log("ATS error.", echo=True)
                    return
                except KeyboardInterrupt:
                    log("Keyboard interrupt while dispatching batch, terminating.", echo=True)
                    return

# Phase 3 -- run the interactive tests
        dieDieDie = False
        if interactiveTests:
            try:
                log("Total number of interactive tests = ", len(interactiveTests), echo=True)
                log("---------------------------------------------------",echo=True)
                self.run(interactiveTests)
            except AtsError:
                log(traceback.format_exc(), echo=True)
                log("ATS error. Removing running jobs....", echo=True)
                dieDieDie = True
    
            except KeyboardInterrupt:
                dieDieDie = True
                log("Keyboard interrupt. Removing running jobs....", echo=True)
    
        if dieDieDie:
            time.sleep(3)   
            for test in self.testlist:
                if (test.status is RUNNING):
                    self.machine.kill(test)
            
        self.machine.quit() #machine shutdown / cleanup

# Phase 4 -- Continuation file         
    # Write out a continuation file ?
        for t in interactiveTests:
            if t.status not in  (PASSED, EXPECTED, FILTERED):
                break
        else:
            self.continuationFileName = ''
            return

# In this scheme, the job is rerun but previously passed jobs are marked passed
# and batched jobs are marked SKIPPED.
        self.continuationFileName= os.path.join(log.directory, 'continue.ats')
        fc = open(self.continuationFileName, 'w')
        print("""
import ats
testlist = ats.manager.testlist
PASSED = ats.PASSED
EXPECTED = ats.EXPECTED
BATCHED = ats.BATCHED
""", file=fc)
        
# The goal here is to mark passed things that need not be rerun. Sometimes 
# something passed but a child did not, which could be a fault in the parent
# so we rerun the parent. This scheme is conservative.
# also if anything fails in a group, rerun the whole group.

        remaining = {}
        for t in self.testlist:
            if t not in interactiveTests:
                print("testlist[%d].set(SKIPPED, 'was %s') # %s" % \
                     (t.serialNumber -1, t.status.name, t.name), file=fc)
            else:
                remaining[t.serialNumber] = t

        while remaining:
             sns = list(remaining.keys())
             u = remaining[sns[0]]
             brothers = [v for v in list(remaining.values()) if areBrothers(u, v)]
             for v in brothers:
                 del remaining[v.serialNumber]
             for v in brothers:
                 if v.status not in (PASSED, EXPECTED):
                     break
             else: 
                 for v in brothers:
                    print("testlist[%d].set(%s, 'Previously ran.') # %s" % \
                                 (v.serialNumber-1, v.status.name, v.name), file=fc)

        fc.close()

    def run(self, interactiveTests):
        """Examine the interactive tests and hand them off to the machine. 
           At this point they have been vetted as tests that the machine canRun.
        """
        machine = self.machine
        unfinished = machine.scheduler.load(interactiveTests)
        if configuration.options.skip:
            self.machine.scheduler.reportObstacles(echo = True)
            log("In skip mode....!")
        else:
            log("Beginning test executions")
        timeStatusReport = time.time()        
        while unfinished:
            timeNow= time.time()
            timePassed= timeNow - timeStatusReport
            if timePassed >= 60:   
                terminal("ATS REPORT AT ELAPSED TIME", wallTime())
                timeStatusReport = timeNow
                self.summary(terminal)
                machine.scheduler.periodicReport()
            unfinished = machine.scheduler.step()


    def getResults(self):
        """Returns an attribute dictionary containing the state of this
           manager suitable for postprocessing. After forming a potential
           result r, calls any resultsHooks functions (r, manager)
        """
        r = AttributeDict(
            started = self.started,
            options = self.options,
            savedTime = datestamp(int=1),
            collectTimeEnded = self.collectTimeEnded,
            badlist = self.badlist,
            filters = self.filters,
            groups = {},
            onExitRoutines = [f.__name__ for f in self.onExitRoutines],
            onResultsRoutines = [f.__name__ for f in self.onResultsRoutines],
            )
        r.testlist = [t.getResults() for t in self.testlist]

        if not hasattr(self, 'machine'):
             return r # never initialized, nothing else of interest.

        r.inputFiles = self.inputFiles
        r.verbose = self.verbose
        r.machine = AttributeDict()
        r.batchmachine = None
        for key, value in list(self.machine.getResults().items()):
            r.machine[key] = value
        if self.batchmachine:
            r.batchmachine = AttributeDict()
            for key, value in list(self.batchmachine.getResults().items()):
                r.batchmachine[key] = value
        for hook in self.onResultsRoutines:
            log('   Calling onResults function', hook.__name__, echo=True)
            hook(r, self)
        return r
            
    def onSave(self, hook):
        """Add a hook for the results function. Will be passed two arguments:

1. The proposed state r, an AttributeDict
2. This manager

The hook will sually will add items to r, but can make any desired
modification to r. Note that at this stage the dependents and depends_on
fields of a test are not present; instead depends_on_serial and
dependents_serial contain the serial numbers of the relevant tests.
        """
        self.onResultsRoutines.append(hook)

    def saveResults(self):
        """Save the state to a file using saveResultsName as file name; 
           if not absolute, put it in the log directory.
        """
        filename = self.saveResultsName
        if not os.path.isabs(filename):
            filename = os.path.join(log.directory, filename)
        log("Saving state to ", filename, echo=True)
        f = open(filename, 'w')
        self.printResults(file = f)
        f.close()

    def printResults(self, file=sys.stdout):
        "Print state to file, formatting items with repr"
# import * is bad style but helps with robustness with respect to ats changes:
        print("""from ats import *""", file=file)
        print("state = ", end=' ', file=file) 
        print(repr(self.getResults()), file=file)
        print("logDirectory = ", repr(log.directory), file=file)
        print("machineName = ", repr(self.machine.name), file=file)
# now print the trailer
        print("""
# now fix up test objects
# First we need an object that prints like a test to avoid recursion.

class TestLike (AttributeDict):
    def __init__ (self, anAttributeDict):
        AttributeDict.__init__(self, **anAttributeDict)
        n = self.groupNumber
        if not state.groups.has_key(n):
            state.groups[n] = AtsTestGroup(n)
        self.group = state.groups[n]
        self.group.append(self)
        
    def __str__ (self):
        return str(self.status) + ' ' + self.name + ' ' + self.message
 
    def __repr__(self):
        return "Test #%d %s %s" %(self.serialNumber, self.name, self.status)


for i in range(len(state.testlist)):
    state.testlist[i] = TestLike(state.testlist[i])
    
for t in state.testlist:
    if t.depends_on_serial == 0:
        t.depends_on = None
    else:
        t.depends_on = state.testlist[t.depends_on_serial -1 ]
    t.dependents = [state.testlist[serial-1] for serial in t.dependents_serial]
    t.waitUntil = [state.testlist[serial-1] for serial in t.waitUntil_serial]
   
# clean up
del i, t 
""", file=file)

# --------- END OF AtsManager --------------

stick=AtsTest.stick
unstick = AtsTest.unstick
tack = AtsTest.tack
untack = AtsTest.untack
glue=AtsTest.glue
unglue = AtsTest.unglue
checkGlue = AtsTest.checkGlue
getOptions= AtsTest.getOptions
wait = AtsTest.wait
group = AtsTest.newGroup
endgroup = AtsTest.endGroup
manager = AtsManager()
# Pull methods out to user level
test = manager.test
testif = manager.testif
source = manager.source
filter = manager.filter
define = manager.define
undefine = manager.undefine
get = manager.get
logDefinitions = manager.logDefinitions
onExit = manager.onExit
onSave = manager.onSave
getResults = manager.getResults
SYS_TYPE= configuration.SYS_TYPE,
MACHINE_TYPE=configuration.MACHINE_TYPE,
BATCH_TYPE=configuration.BATCH_TYPE,
MACHINE_DIR=configuration.MACHINE_DIR,
#
_filterwith = []
def filterdefs (text=None):
    """Add the given text into the environment 
       used for filtering.
       With no arguments, clear defined list.
    """
    global _filterwith
    if text is None: 
        log('filterdefs: erasing definitions')
        _filterwith = []
    else:
        try:
            d = {}
            for f in _filterwith:
                exec(f, d)
            exec(text, d)
        except SyntaxError as e:
            raise AtsError(e)
        except KeyboardInterrupt:
            raise
        except Exception as e:
            pass
        if debug():
            log('filterdefs:')
            log.indent()
            log(text)
            log.dedent()
        _filterwith.append(text)

# Set up the testing environment, add statuses to it.    
testEnvironment =AttributeDict(
        debug= debug,
        manager= manager,
        test= test,
        testif= testif,
        source= source,
        log= log,
        define= define,
        undefine= undefine,
        get= get,
        logDefinitions= logDefinitions,
        filter= filter,
        filterdefs= filterdefs,
        wait= wait,
        stick= stick,
        unstick= unstick,
        tack= tack,
        untack= untack,
        group = group,
        endgroup = endgroup,
        glue= glue,
        unglue= unglue,
        checkGlue= checkGlue,
        getOptions= getOptions,
        sys= sys,
        os= os,
        abspath= abspath,
        AtsError= AtsError,
        is_valid_file= is_valid_file,
        SYS_TYPE= configuration.SYS_TYPE,
        MACHINE_TYPE=configuration.MACHINE_TYPE,
        BATCH_TYPE=configuration.BATCH_TYPE,
        MACHINE_DIR=configuration.MACHINE_DIR,
        onExit = onExit,
        onSave = onSave,
        getResults = getResults,
        )
testEnvironment.update(statuses)

if __name__ == "__main__":
    logDefinitions()
