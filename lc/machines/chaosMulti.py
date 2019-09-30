#ATS:chaosM SELF ChaosMultiMachine 12
#ATS:chaos12 SELF ChaosMultiMachine 12
#ATS:chaos16 SELF ChaosMultiMachine 16
#ATS:zeusM  SELF ChaosMultiMachine 8



from ats import machines, debug, atsut
from ats import log, terminal
from ats import configuration
from ats.atsut import RUNNING, TIMEDOUT
import utils
import time

class ChaosMultiMachine (machines.Machine):
    """The chaos family with processor scheduling.
    """
    def init (self): 

        self.npBusy = 0

        self.stepToUse= None
        self.stepInUse= None

        self.npMax= self.numberTestsRunningMax

        self.stepUsedDic= {}

    def addOptions(self, parser): 

        "Add options needed on this machine."
        parser.add_option("--partition", action="store", type="string", dest='partition', 
            default = 'pdebug', 
            help = "Partition in which to run jobs with np > 0")
        parser.add_option("--numNodes", action="store", type="int", dest='numNodes',
           default = -1, 
           help="Number of nodes to use")
        parser.add_option("--srunOnlyWhenNecessary", action="store_true", dest='srun', default=False,
           help="Use srun only for np > 1")
        parser.add_option("--removeSrunStep", action="store_true", dest='removeSrunStep', default=False,
           help="Set to use srun job step.")

    def examineOptions(self, options): 
        "Examine options from command line, possibly override command line choices."
        # Grab option values.    
        super(ChaosMultiMachine, self).examineOptions(options)
        self.npMax= self.numberTestsRunningMax
        
        import os
        self.removeSrunStep = options.removeSrunStep
        if self.removeSrunStep == False:
            if 'SLURM_NNODES' not in os.environ:
                self.removeSrunStep= True
        
        if options.numNodes==-1:
            if 'SLURM_NNODES' in os.environ:
                options.numNodes= int(os.environ['SLURM_NNODES'])
               
            else:
                options.numNodes= 1
        self.numNodes= options.numNodes
        
        if self.npMax == 1: self.numNodes = 1
        self.numberMaxProcessors = self.npMax * self.numNodes

        self.srunOnlyWhenNecessary = options.srun
        self.partition = options.partition

        if not self.removeSrunStep:
            self.allNodeList= utils.getAllHostnames()
            if len(self.allNodeList) == 0:
                self.removeSrunStep = True
            else:
                self.stepId, self.nodeStepNumDic= utils.setStepNumWithNode(len(self.allNodeList))  
                for oneNode in self.allNodeList:
                   self.stepUsedDic[oneNode]= 0
                self.stepInUse= self.stepToUse

                # Let's check if there exists a srun <defunct> process
                if len(self.allNodeList) > 0:
                    srunDefunct= utils.checkForSrunDefunct(self.allNodeList[0])
                    self.numberMaxProcessors -= srunDefunct
                    self.stepUsedDic[self.allNodeList[0]] += srunDefunct


        self.numberTestsRunningMax = self.numberMaxProcessors
 
    def getResults(self):
        results = super(ChaosMultiMachine, self).getResults()
        results.srunOnlyWhenNecessary = self.srunOnlyWhenNecessary
        results.partition = self.partition
        results.numNodes = self.numNodes
        results.numberMaxProcessors = self.numberMaxProcessors
        
        if not self.removeSrunStep:
           results.allNodeList = self.allNodeList
        return results

    def label(self):
        return "chaos %d nodes %d processors per node." % (self.numNodes, self.npMax)

    def calculateCommandList(self, test): 
        """Prepare for run of executable using a suitable command. First we get the plain command
         line that would be executed on a vanilla serial machine, then we modify it if necessary
         for use on this machines.
        """
        commandList = self.calculateBasicCommandList(test)
        if self.srunOnlyWhenNecessary and test.np <= 1: 
            return commandList
        test.jobname = "t%d_%d%s" % (test.np, test.serialNumber, test.namebase)   #namebase is a space-free version of the name
        np = max(test.np, 1)
        nnn = str(test.numberOfNodesNeeded)
        if not self.removeSrunStep:
            if self.stepToUse is not None:
                finalList =  ["srun", "--label", "-J", test.jobname, "--share", "-N",  
                               "".join([nnn, "-", nnn]), 
                               "-n", str(np), "-r", str(self.stepToUse), "-p", 
                               self.partition] + commandList 
                self.stepToUse= None
                return finalList

        return ["srun", "--label", "-J", test.jobname, "--exclusive", "-N", 
                "".join([nnn, "-", nnn]), 
                "-n", str(np), "-p", self.partition] + commandList

    def canRun(self, test):
        "Do some precalculations here to make canRunNow quicker."
        test.requiredNP= max(test.np,1)
        test.numberOfNodesNeeded, r = divmod(test.requiredNP, self.npMax)
        if r: test.numberOfNodesNeeded += 1
        
        if self.removeSrunStep:
            test.requiredNP= max(test.np, self.npMax*test.numberOfNodesNeeded)  
        if test.requiredNP > self.numberMaxProcessors:
            return "Too many processors required, %d" % test.requiredNP
        
    def canRunNow(self, test): 
        "Is this machine able to run this test now? Return True/False"

            
        if (self.npBusy + test.requiredNP    ) > self.numberMaxProcessors:
            return False

        elif self.removeSrunStep:
            return True

        elif (self.stepToUse is None):
            test.step= -1
            
            self.stepToUse= utils.findAvailableStep(self.allNodeList, 
                                   self.stepUsedDic, self.nodeStepNumDic, 
                                   self.npMax, test.requiredNP, self.stepInUse
                            )
            
        if (self.stepToUse is not None):
            self.stepInUse= self.stepToUse
            test.step= self.stepToUse
            return True
        else:
            return False

    def noteLaunch(self, test):
        """A test has been launched."""

        if not self.removeSrunStep:
            utils.addToUsedTotalDic(self.stepUsedDic, self.nodeStepNumDic, self.npMax, self.stepInUse, test.np)
            self.npBusy += max(test.np, 1)
        else:
            self.npBusy += max(test.np, test.numberOfNodesNeeded*self.npMax)     # this is necessary when srun exclusive is used.

        if debug():
            log("Max np= %d. Launched %s with np= %d tests, total proc in use = %d" % \
                (self.numberMaxProcessors, test.name, test.np, self.npBusy), echo=True)
            self.scheduler.schedule("Max np= %d. Launched %s with np= %d tests, total proc in use = %d" % \
                (self.numberMaxProcessors, test.name, test.np, self.npBusy))
          
        self.numberTestsRunning= self.npBusy

    def noteEnd(self, test):
        """A test has finished running. """

        if not self.removeSrunStep:
            self.stepUsedDic= utils.removeFromUsedTotalDic(self.stepUsedDic, self.nodeStepNumDic, self.npMax, test.step, test.np, self.stepId, self.allNodeList)
            self.npBusy -= max(test.np, 1)
        else:
            self.npBusy -= max(test.np, test.numberOfNodesNeeded*self.npMax)     # this is necessary when srun exclusive is used.

        if debug():
            log("Finished %s, #total proc in use = %d" %  (test.name, self.npBusy), echo=True)
            self.scheduler.schedule("Finished %s, #total proc in use = %d" %  (test.name, self.npBusy))

        self.numberTestsRunning= self.npBusy

    def periodicReport(self): 
        "Report on current status of tasks"
        # Let's also write out the tests that are waiting ....
        
        super(ChaosMultiMachine, self).periodicReport()
        currentEligible=  [ t.name for t in self.scheduler.testlist() if t.status is atsut.CREATED ]

        if len(currentEligible) > 1:
            terminal("WAITING:", ", ".join(currentEligible[:5]), "... (more)")
        
    def kill(self, test): 
        "Final cleanup if any."
        # kill the test
        # This is necessary -- killing the srun command itself is not enough to end the job... it is still running (squeue will show this)
        import subprocess
        
        if test.status is RUNNING or test.status is TIMEDOUT:
            try:
                retcode= subprocess.call("scancel" + " -n  " + test.jobname, shell=True)
                if retcode < 0:
                    log("---- kill() in chaosMulti.py, command= scancel -n  %s failed with return code -%d  ----" %  (test.jobname, retcode), echo=True)
            except OSError as e:
                log("---- kill() in chaosMulti.py, execution of command failed (scancel -n  %s) failed:  %s----" %  (test.jobname, e), echo=True)

