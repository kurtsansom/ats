#ATS:chaos             SELF ChaosMachine 8

from ats import machines, log, debug
from ats.atsut import RUNNING, TIMEDOUT

class ChaosMachine (machines.Machine):
    """The chaos family, one node.
    """
    def init (self): 
        self.npBusy = 0

    def addOptions(self, parser): 
        "Add options needed on this machine."
        parser.add_option("--partition", action="store", type="string", dest='partition', 
            default = 'pdebug', 
            help = "Partition in which to run jobs with np > 0")
        parser.add_option("--srunOnlyWhenNecessary", action="store_true", dest='srun', default=False,
           help="Use srun only for np > 1")

    def examineOptions(self, options): 
        "Examine options from command line, possibly override command line choices."
        super(ChaosMachine, self).examineOptions(options)
        self.srunOnlyWhenNecessary = options.srun
        self.partition = options.partition
            
    def calculateCommandList(self, test): 
        """Prepare for run of executable using a suitable command. First we get the plain command
         line that would be executed on a vanilla serial machine, then we modify it if necessary
         for use on this machines.
        """
        commandList = self.calculateBasicCommandList(test)
        if self.srunOnlyWhenNecessary and test.np <= 1: 
            return commandList
        np = max(test.np, 1)
        test.jobname = "t%05d%s" % (test.serialNumber, test.namebase)  #namebase is a space-free version of the name
        
        return ["srun", "--label", "-J", test.jobname, "--share", "-N", "1", "-n",
                str(np), "-p", self.partition] + commandList

    def canRun(self, test):
        """Is this machine able to run the test interactively when resources become available? 
           If so return ''.  Otherwise return the reason it cannot be run here.
        """
        if test.np > self.numberTestsRunningMax:   
            return "Too many processors needed (%d)" % test.np
        return ''

    def canRunNow(self, test): 
        "Is this machine able to run this test now? Return True/False"
        return (self.npBusy  + max(test.np, 1))  <= self.numberTestsRunningMax

    def noteLaunch(self, test):
        """A test has been launched."""
        self.npBusy += max(test.np, 1)
        if debug():
            log("Launched %s, now running %d tests, proc = %d" % \
                (test.name, self.numberTestsRunning, self.npBusy), echo=True)

    def noteEnd(self, test):
        """A test has finished running. """
        self.npBusy -= max(test.np, 1)
        if debug():
            log("Finished %s, now running %d tests, proc = %d" % \
                (test.name, self.numberTestsRunning, self.npBusy), echo=True)
    

    def kill(self, test): 
        "Final cleanup if any."
        # kill the test
        # This is necessary -- killing the srun command itself is not enough to end the job... it is still running (squeue will show this)
        import subprocess
        if test.status is RUNNING or test.status is TIMEDOUT:
            try:
                retcode= subprocess.call("scancel" + " -n  " + test.jobname, shell=True)
                if retcode < 0:
                    log("---- kill() in chaos.py, command= scancel -n  %s failed with return code -%d  ----" %  (test.jobname, retcode), echo=True)
            except OSError, e:
                log("---- kill() in chaos.py, execution of command failed (scancel -n  %s) failed:  %s----" %  (test.jobname, e), echo=True)

