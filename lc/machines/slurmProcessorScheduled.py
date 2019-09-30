#ATS:SlurmProcessorScheduled SELF SlurmProcessorScheduled 12
#ATS:chaos_4_x86_64_ib SELF SlurmProcessorScheduled 12
#ATS:chaos_3_x86_64_ib SELF SlurmProcessorScheduled 8
#ATS:chaos_3_x86_elan3 SELF SlurmProcessorScheduled 2
#ATS:chaos_5_x86_64_ib SELF SlurmProcessorScheduled 16


from ats import machines, debug, atsut
from ats import log, terminal
from ats import configuration
from ats.atsut import RUNNING, TIMEDOUT
import utils
import os

class SlurmProcessorScheduled (machines.Machine):

    def init (self):
        
        self.runWithSalloc= True

        if "SLURM_NNODES" in os.environ.keys():
            self.numNodes= int(os.getenv("SLURM_NNODES"))
            self.npMax= int(os.getenv("SLURM_TASKS_PER_NODE", "1").split("(")[0])
        elif "SLURM_JOB_NUM_NODES" in os.environ.keys():
            self.numNodes= int(os.getenv("SLURM_JOB_NUM_NODES"))
            self.npMax= int(os.getenv("SLURM_JOB_CPUS_PER_NODE", "1").split("(")[0])
        else:
            self.runWithSalloc= False
            self.npMax= self.numberTestsRunningMax

            #raise RuntimeError, ("To use the SlurmProcessorScheduled machine module,"
            #                     " you must allocate nodes with salloc or msub")

        if self.runWithSalloc==True:
            self.numberMaxProcessors = self.npMax * self.numNodes 
            self.numberTestsRunningMax = self.numberMaxProcessors * self.numNodes # needed in base
            #check if running ats on one of the salloc nodes, if so, remove one proc from max proc count.
            if self.checkForAtsProc():
                self.numberMaxProcessors -= 1
            self.numProcsAvailable = self.numberMaxProcessors

    def checkForAtsProc(self):
        rshCommand= 'ps uwww'
        returnCode, runOutput= utils.runThisCommand(rshCommand)
        import string 
        theLines= string.split(runOutput, '\n')
        foundAts= False
        for aline in theLines:
            #if 'srun' in aline and 'defunct' in aline:
            if 'salloc ' in aline:
                # NO ats running.
                return 0
            if 'bin/ats ' in aline:
                foundAts= True
    
        if foundAts:
            # Found ats running.
            return 1
        # NO ats running.
        return 0
        
    def getNumberOfProcessors(self):
        return self.numberMaxProcessors
    
    def examineOptions(self, options): 
        "Examine options from command line, possibly override command line choices."
        # Grab option values.    
        # Note, this machines.Machine.examineOptions call will reset self.numberTestsRunningMax
        # self.numberTestsRunningMax is set in init(), not need to call machines.Machine.examineOptions
        #machines.Machine.examineOptions(self, options)     
        if self.runWithSalloc:
            options.numNodes = self.numNodes
        
        if not self.runWithSalloc:
            super(SlurmProcessorScheduled, self).examineOptions(options)
            self.npMax= self.numberTestsRunningMax
            self.numNodes= options.numNodes
            self.partition = options.partition

            self.numberMaxProcessors = self.npMax * self.numNodes
            self.numProcsAvailable = self.numberMaxProcessors

            # this needs to be set for the manager for filter the jobs correctly. 
            self.numberTestsRunningMax = self.numberMaxProcessors   

    def addOptions(self, parser): 

        "Add options needed on this machine."
        parser.add_option("--partition", action="store", type="string", dest='partition', 
            default = 'pdebug', 
            help = "Partition in which to run jobs with np > 0")
        parser.add_option("--numNodes", action="store", type="int", dest='numNodes',
           default = 2, 
           help="Number of nodes to use")
        
    def getResults(self):
        """I'm not sure what this function is supposed to do"""
        return machines.Machine.getResults(self)

    def label(self):
        return "SlurmProcessorScheduled: %d nodes, %d processors per node." % (
            self.numNodes, self.npMax)

    def calculateCommandList(self, test): 
        """Prepare for run of executable using a suitable command. First we get the plain command
         line that would be executed on a vanilla serial machine, then we modify it if necessary
         for use on this machines.
        """
        np = max(test.np, 1)
        commandList = self.calculateBasicCommandList(test)
        import time
        timeNow= time.strftime('%H%M%S',time.localtime())
        test.jobname = "t%d_%d%s%s" % (np, test.serialNumber, test.namebase, timeNow)
        minNodes = np / self.npMax + (np % self.npMax != 0 )
 
        if self.runWithSalloc == False:
               return ["srun", "--label", "-J", test.jobname, "--share", 
                #"-N", "".join([nnn, "-", nnn]), 
                "-n", str(np), "-p", self.partition] + commandList
 
        return ["srun", "--label", "-J", test.jobname, "--exclusive",
                "--contiguous",
                #"-N", str(minNodes),
                "-n", str(np) ] + commandList


    def canRun(self, test):
        """Is this machine able to run the test interactively when resources become available? 
           If so return ''.  Otherwise return the reason it cannot be run here.
        """
        np = max(test.np, 1)
        if np > self.numberMaxProcessors:   
            return "Too many processors needed (%d)" % np
        return ''

    def canRunNow(self, test): 
        "Is this machine able to run this test now? Return True/False"
        np = max(test.np, 1)
        return self.numProcsAvailable >= np

    def noteLaunch(self, test):
        """A test has been launched."""
        np = max(test.np, 1)
        self.numProcsAvailable -= np
        
        
    def noteEnd(self, test):
        """A test has finished running. """
        np = max(test.np, 1)
        self.numProcsAvailable += np
        
    def periodicReport(self): 
        "Report on current status of tasks"
        if len(self.running):
            terminal("CURRENTLY RUNNING %d tests:" % len(self.running),
                     " ".join([t.name for t in self.running]))
        terminal("-"*80)
        terminal("CURRENTLY UTILIZING %d of %d processors." % (
            self.numberMaxProcessors - self.numProcsAvailable, self.numberMaxProcessors))
        terminal("-"*80)
    
    def kill(self, test): 
        "Final cleanup if any."
        
        # kill the test This is necessary -- killing the srun command
        # itself is not enough to end the job... it is still running
        # (squeue will show this)
        
        import subprocess
        
        if test.status is RUNNING or test.status is TIMEDOUT:
            try:
                retcode= subprocess.call("scancel" + " -n  " + test.jobname, shell=True)
                if retcode < 0:
                    log("---- kill() in slurmProcessorScheduled.py, command= scancel -n  %s failed with return code -%d  ----" %  (test.jobname, retcode), echo=True)
            except OSError, e:
                log("---- kill() in slurmProcessorScheduled.py, execution of command failed (scancel -n  %s) failed:  %s----" %  (test.jobname, e), echo=True)

