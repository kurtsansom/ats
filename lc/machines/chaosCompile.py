#ATS:chaos16Compile SELF ChaosCompileMachine 16
#ATS:chaos12Compile SELF ChaosCompileMachine 12

import subprocess, sys, os, time, shlex
from ats import machines, debug, atsut
from ats import log, terminal
from ats.atsut import RUNNING, TIMEDOUT
import utils
from chaosMulti import ChaosMultiMachine
import os, string

class ChaosCompileMachine (ChaosMultiMachine):
    """ To compile on a chaos machine.
    """

    def __init__(self, name, npMaxH):   ## be sure to call this from child if overridden

        maxNumProcs= utils.getNumberOfProcessorsPerNode()
        
        #super(ChaosCompileMachine, self).__init__(name, npMaxH)
        super(ChaosCompileMachine, self).__init__(name, maxNumProcs)  # let's use maxNumProcs instead


        self.comboFileHandle= None
        
    def addOptions(self, parser): 
        "Add options needed on this machine."

        super(ChaosCompileMachine, self).addOptions(parser)

        parser.add_option("--j", action="store", type="int", dest='numJ', default=1,
           help="Gmake j value ")

    def examineOptions(self, options): 
        "Examine options from command line, possibly override command line choices."
        # Grab option values.    
        super(ChaosCompileMachine, self).examineOptions(options)

        self.numJ = options.numJ
    def label(self):
        return "chaosCompile %d nodes %d processors per node." % (self.numNodes, self.npMax)

    def calculateCommandList(self, test): 
        """Prepare for run of executable using a suitable command. First we get the plain command
         line that would be executed on a vanilla serial machine, then we modify it if necessary
         for use on this machines.
        """
        commandList = self.calculateBasicCommandList(test)

	# gmake -> gmake -j someVal 
        gmakeCmd= 'gmake'
        for aCmd in commandList:
            if 'gmake' in aCmd:
                gmakeCmd= aCmd
                break
        if gmakeCmd  in commandList:
            pos= commandList.index(gmakeCmd)
            commandList.insert(pos+1, "-j") 
            commandList.insert(pos+2, str(self.numJ))

        test.jobname = "t%d%s" % (test.serialNumber, test.namebase)   #namebase is a space-free version of the name


        #buildLibCmd= 'all_libraries'
        #if buildLibCmd in test.jobname:
        #    np = max(test.np, 1)        
        #else:
        #    np = max(test.np, self.numJ)

        #np = max(test.np, 1)        
        np= 1              # let's set srun -N 1 -n "1"
        if self.srunOnlyWhenNecessary and test.np <= 1: 
            return commandList
        numberOfNodesNeeded, r = divmod(np, self.npMax)
        if r: numberOfNodesNeeded += 1


        if not self.removeSrunStep:
            if self.stepToUse is not None:
               
                finalList =  ["srun", "--label", "-J", test.jobname, "--share", "-N", str(numberOfNodesNeeded), "-n", str(np), "-r", str(self.stepToUse), "-p", self.partition] + commandList 

                self.stepToUse= None
                return finalList

        return ["srun", "--label", "-J", test.jobname, "--exclusive", "-N", str(numberOfNodesNeeded), "-n", str(np), "-p", self.partition] + commandList


    def canRun(self, test):
        """Is this machine able to run the test interactively when resources become available? 
           If so return ''.  Otherwise return the reason it cannot be run here.
        """
        if test.np > self.numberMaxProcessors:   
            return "Too many processors needed (%d)" % test.np
        return ''

    def canRunNow(self, test): 
        "Is this machine able to run this test now? Return True/False"
        buildLibCmd= 'all_libraries'
        if buildLibCmd in test.namebase:
            test.np = max(test.np, 1)        
        else:
            test.np = max(test.np, self.numJ)

        # if default_cachedir in test.directory, then test.directory has to be changed
        if '/default_cachedir' in test.directory:
            thisDir= os.getcwd() + '/'
            pos= string.find(test.directory, 'default_cachedir')
            newDir= thisDir + test.directory[pos+17:]      #default_cachedir=16 chars + '/' = 17 chars total
            test.directory= newDir


        if self.removeSrunStep:
            if (self.npBusy + test.np) <= self.numberMaxProcessors:
                return True
            else:
                return False

        if (self.npBusy + test.np) > self.numberMaxProcessors:
            # NO NEED TO TRY CHECKING SQUEUE: npBusg + testNp > max 
            return False
        elif (self.stepToUse is None):
            test.step= -1
            
            self.stepToUse= utils.findAvailableStep(self.allNodeList, self.stepUsedDic, self.nodeStepNumDic, 
                                                    self.npMax, test.np, self.stepInUse)
            if self.stepToUse==None:
                self.stepUsedDic, self.stepToUse= utils.getUnusedNode(self.allNodeList, test.np, self.npMax, self.nodeStepNumDic, self.stepId) 

            self.stepInUse= self.stepToUse

        if (self.stepToUse is not None):
            return True
        else:
            return False

    def noteLaunch(self, test):
        """A test has been launched."""

        self.npBusy += max(test.np, 1)

        if not self.removeSrunStep:
            test.step= self.stepInUse

            utils.addToUsedTotalDic(self.stepUsedDic, self.nodeStepNumDic, self.npMax, self.stepInUse, test.np)
               
        if debug():
            log("chaosCompile.py__ Max np= %d. Launched %s with np= %d tests, total proc used = %d" % \
                (self.numberMaxProcessors, test.name, test.np, self.npBusy), echo=True)
                
        self.numberTestsRunning= self.npBusy


    def noteEnd(self, test):
        """A test has finished running. """

        self.npBusy -= max(test.np, 1)
        if not self.removeSrunStep:

            self.stepUsedDic= utils.removeFromUsedTotalDic(self.stepUsedDic, self.nodeStepNumDic, self.npMax, test.step, test.np, self.stepId, self.allNodeList)

        if debug():
            log("Finished %s, #total proc used = %d" % \
                (test.name, self.npBusy), echo=True)

        self.numberTestsRunning= self.npBusy

        # Add to combo log file
        self.catLogFiles(test)

    def periodicReport(self): 
        "Report on current status of tasks"
        # Let's also write out the tests that are waiting ....
        
        super(ChaosCompileMachine, self).periodicReport()
        currentEligible=  [ t.name for t in self.scheduler.testlist() if t.status is atsut.CREATED ]

        if len(currentEligible) > 1:
            terminal("WAITING:", ", ".join(currentEligible[:5]), "... (more)")
        


    def catLogFiles(self, test): 
        
        if self.comboFileHandle is None:
            comboName= log.directory + "_combo_.log"
            self.comboFileHandle = open(comboName, 'w')
        try:
            finOut = open(test.outname, 'r')
            finErr = open(test.errname, 'r')
            self.comboFileHandle.write(finOut.read())
            self.comboFileHandle.write(finErr.read())
            
            finOut.close()
            finErr.close()

        except IOError:
            print("\ncat of log files failed for ", test.name, " -- ", str(e))


    def quit(self): #
        self.comboFileHandle.close()
