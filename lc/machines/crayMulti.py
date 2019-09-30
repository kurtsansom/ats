#ATS:cray SELF CrayMachine 16
#ATS:cielito SELF CrayMachine 16

#BATS:batchAllZeus  batchAllLinux Machine 8
#BATS:batchAllChaos  batchAllLinux Machine 16

from ats import machines, debug, atsut
from ats import log, terminal
from ats import configuration
from ats.atsut import RUNNING, TIMEDOUT
import utils
import time

class CrayMachine (machines.Machine):
    """The cray family with processor scheduling.
    """
    def init (self): 

        self.npBusy = 0

        self.stepToUse= None
        self.stepInUse= None

        self.npMax= self.numberTestsRunningMax

        self.stepUsedDic= {}

        self.eligible= None

        self.countTimesNoNodesAvailable= 0
        self.timeLastCalledCheckRunning= time.time()

    def addOptions(self, parser): 

        "Add options needed on this machine."
        parser.add_option("--partition", action="store", type="string", dest='partition', 
            default = 'pdebug', 
            help = "Partition in which to run jobs with np > 0")
        parser.add_option("--numNodes", action="store", type="int", dest='numNodes',
           default = -1, 
           help="Number of nodes to use")
           

    def examineOptions(self, options): 
        "Examine options from command line, possibly override command line choices."
        # Grab option values.    
        super(CrayMachine, self).examineOptions(options)
        
        if options.numNodes==-1:
            import os
            if 'PBS_ENVIRONMENT' in os.environ:
                options.numNodes= int(os.environ['PBS_NUM_NODES'])
            else:
                options.numNodes= 1
        self.numNodes= options.numNodes
        

        if self.npMax == 1: self.numNodes = 1
        self.numberMaxProcessors = self.npMax * self.numNodes

        self.partition = options.partition
       
        self.numberTestsRunningMax = self.numberMaxProcessors
 
    def getResults(self):
        results = super(CrayMachine, self).getResults()
        
        results.partition = self.partition
        results.numNodes = self.numNodes
        results.numberMaxProcessors = self.numberMaxProcessors
        
        return results

    def label(self):
        return "cray %d nodes %d processors per node." % (self.numNodes, self.npMax)

    def calculateCommandList(self, test): 
        """Prepare for run of executable using a suitable command. First we get the plain command
         line that would be executed on a vanilla serial machine, then we modify it if necessary
         for use on this machines.
        """
        commandList = self.calculateBasicCommandList(test)
        
       
        test.jobname = "t%d_%d%s" % (test.np, test.serialNumber, test.namebase)   #namebase is a space-free version of the name
        np = max(test.np, 1)
        numberOfNodesNeeded, r = divmod(np, self.npMax)
        if r: numberOfNodesNeeded += 1

        return ["aprun", "-F", "exclusive", "-n", str(np), ] + commandList


    def canRun(self, test):
        """Is this machine able to run the test interactively when resources become available? 
           If so return ''.  Otherwise return the reason it cannot be run here.
        """
        if test.np > self.numberMaxProcessors:   
            return "Too many processors needed (%d)" % test.np
        return ''

    def canRunNow(self, test): 
        "Is this machine able to run this test now? Return True/False"

        requiredNp= max(test.np,1)
        numberOfNodesNeeded, r = divmod(requiredNp, self.npMax)
        if r: numberOfNodesNeeded += 1
        test.nodes= numberOfNodesNeeded
        
        
        requiredNp= max(test.np, self.npMax*numberOfNodesNeeded)       
        if (self.npBusy + requiredNp    ) <= self.numberMaxProcessors:
            return True
        else:
            return False


    def noteLaunch(self, test):
        """A test has been launched."""

        
        numberOfNodesNeeded, r = divmod(max(test.np,1), self.npMax)
        if r: numberOfNodesNeeded += 1
        self.npBusy += max(test.np, numberOfNodesNeeded*self.npMax)     # this is necessary when srun exclusive is used.

        if debug():
            #log("cray.py__usedDic: %s" % \
            #    (self.stepUsedDic), echo=True)
            log("cray.py__ Max np= %d. Launched %s with np= %d tests, total proc used = %d" % \
                (self.numberMaxProcessors, test.name, test.np, self.npBusy), echo=True)
                
        self.numberTestsRunning= self.npBusy


    def noteEnd(self, test):
        """A test has finished running. """

        numberOfNodesNeeded, r = divmod(max(1,test.np), self.npMax)
        if r: numberOfNodesNeeded += 1
        self.npBusy -= max(test.np, numberOfNodesNeeded*self.npMax)     # this is necessary when srun exclusive is used.

        if debug():
            log("Finished %s, #total proc used = %d" %  (test.name, self.npBusy), echo=True)

        self.numberTestsRunning= self.npBusy

    def periodicReport(self): 
        "Report on current status of tasks"
        # Let's also write out the tests that are waiting ....
        
        super(CrayMachine, self).periodicReport()
        currentEligible=  [ t.name for t in self.scheduler.testlist() if t.status is atsut.CREATED ]

        if len(currentEligible) > 1:
            terminal("WAITING:", ", ".join(currentEligible[:5]), "... (more)")
        
