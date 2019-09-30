#ATS:angrenSandia SELF AngrenSandiaMachine 2
#ATS:rhe_4_ia32 SELF AngrenSandiaMachine 2

from ats import machines, debug, atsut
from ats import log, terminal
from ats import configuration
from ats.atsut import RUNNING, TIMEDOUT
import utils
import time

class AngrenSandiaMachine (machines.Machine):
    """The AngrenSandiaMachine family with node scheduling.
    """
    def init (self): 

        self.npBusy = 0

        self.stepToUse= None
        self.stepInUse= None

        self.npMax= self.numberTestsRunningMax

        self.mapNodeName_ProcUsed= {}

    def addOptions(self, parser): 

        "Add options needed on this machine."
        parser.add_option("--partition", action="store", type="string", dest='partition', 
            default = 'pdebug', 
            help = "Partition in which to run jobs with np > 0")
        #parser.add_option("--numNodes", action="store", type="int", dest='numNodes',
        #   default = -1, 
        #   help="Number of nodes to use")
        parser.add_option(
            '--nodeFilename', action='store', type= 'string', dest='inputNodeListFilename', metavar='FILE', 
            help='execute test scripts in parallel using nodes or machine defined in FILE. FILE contains a list of one or more pairs of nodeName and numProcs, or machineName and numProcs pair.') 
        

    def examineOptions(self, options): 
        "Examine options from command line, possibly override command line choices."
        # Grab option values.    
        super(AngrenSandiaMachine, self).examineOptions(options)
        
        self.inputNodeListFilename= options.inputNodeListFilename
        self.setNodeList(self.inputNodeListFilename)
        

        self.numNodes= len(self.mapNodeName_ProcsUsed)
        
        self.numberMaxProcessors = self.npMax * self.numNodes

        self.numberTestsRunningMax = self.numberMaxProcessors

    def setNodeList(nodelistFn):
        """
        Sets a map: self.mapNodeName_ProcsUsed.

        Reads nodelist information from nodelistFn.  
        nodelistFn:
        machineName1 numberOfProcessorsAvailable
        machineName2 numberOfProcessorsAvailable
        """
        try:
            fp= open(nodelistFn)
        except IOError:
            log("ATS error: Could not open node list file %s"% nodeListFn, echo=True)

        try:
            for line in fp.readlines():
                if line[0][0] == '#':
                    continue                             #skip this line
                words= string.split(line)
                if (len(words) < 1):
                    continue                              # skip this line

                nodeName= string.strip(words[0])
                try:
                    numProcsRead= string.atoi(words[1])
                except IndexError:
                    numProcsRead= ats.manager.numNodesATSHas

                self.mapNodeName_ProcsUsed[nodeName]= 0

            fp.close()

        except Exception, error:
            ats.log(str(error), verbose=1)
            fp.close()
            log("ATS error: Error with parsing node file %s"% nodeListFn, echo=True)


    def getResults(self):
        results = super(AngrenSandiaMachine, self).getResults()
        results.numNodes = self.numNodes
        results.numberMaxProcessors = self.numberMaxProcessors
        return results

    def label(self):
        return "angren-sandia %d nodes %d processors per node." % (self.numNodes, self.npMax)

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

        sshPart= "ssh -x " + test.nodeToUse + "'cd " + test.directory 
        if test.mpiNodesFilename is None:
            return [sshPart] + ["mpirun", "-n", str(numberOfNodesNeeded), "-np", str(np)]  + commandList + ["'"]


        return [sshPart] + ["mpirun", "-n", str(numberOfNodesNeeded), "-np", str(np), '-machinefile', test.mpiNodesFilename]  + commandList + ["'"]

        


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
        
        nodesAvailable= [ anode for anode in self.mapNodeName_ProcsUsed.keys() if self.mapNodeName_ProcsUsed[anode] == 0 ]
        if len(nodesAvailable) <= 0:
            return False
        
        test.nodeToUse= nodesAvailable[0]
        test.mpiNodesFilename= None
        test.mpiNodesList= []

        if test.nodes > 2:
            # create a nodelist file for mpirun to use
            import tempfile
            test.mpiNodesFilename= os.path.join(".hosts", dir=log.directory)
            mpiNodesFp= open(test.mpiNodesFilename, "w")
            counter= 0
            for anode in nodesAvailable:
                mpiNodesFp.write(anode);
                test.mpiNodesList.append(anode)
                counter += self.npMax
                if counter >= requiredNp:
                    break
            mpiNodesFp.close()
            if counter < requiredNp:
                return False             # not enough nodes 
                
            
        return True

    def noteLaunch(self, test):
        """A test has been launched."""

        if test.mpiNodesFilename is not None:
            for anode in test.mpiNodesList:
                self.mapNodeName_ProcsUsed[anode]= 1
        else:
            self.mapNodeName_ProcsUsed[test.nodeToUse]= 1
            
        if debug():
            log("angrenSandia.py__ Max np= %d. Launched %s with np= %d tests, total proc used = %d" % \
                (self.numberMaxProcessors, test.name, test.np, self.npBusy), echo=True)
                
            
        #self.numberTestsRunning= self.npBusy


    def noteEnd(self, test):
        """A test has finished running. """

        if test.mpiNodesFilename is not None:
            for anode in test.mpiNodesList:
                self.mapNodeName_ProcsUsed[anode]= 0
        else:
            self.mapNodeName_ProcsUsed[test.nodeToUse]= 0

        if debug():
            log("Finished %s, #total proc used = %d" %  (test.name, self.npBusy), echo=True)

        self.numberTestsRunning= self.npBusy

    def periodicReport(self): 
        "Report on current status of tasks"
        # Let's also write out the tests that are waiting ....
        
        super(AngrenSandiaMachine, self).periodicReport()
        currentEligible=  [ t.name for t in self.scheduler.testlist() if t.status is atsut.CREATED ]

        if len(currentEligible) > 1:
            terminal("WAITING:", ", ".join(currentEligible[:5]), "... (more)")
        
