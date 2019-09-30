#ATS:dawnCompile SELF DawnCompileMachine 1

import subprocess, sys, os, time, shlex
from ats import configuration
from ats import machines, debug, atsut
from ats import log, terminal
from ats.atsut import RUNNING, TIMEDOUT
from ats.atsut import debug, RUNNING, TIMEDOUT, PASSED, FAILED, \
     CREATED, SKIPPED, HALTED, AttributeDict, AtsError

import utils
from chaosMulti import ChaosMultiMachine

import os, string


class DawnCompileMachine (machines.Machine):
    """The dawn machine 
    """

    def __init__(self, name, npMaxH):   ## be sure to call this from child if overridden

        maxNumProcs= utils.getNumberOfProcessorsPerNode()
        super(DawnCompileMachine, self).__init__(name, maxNumProcs)  # let's use maxNumProcs instead
        
        self.comboFileHandle= None
        self.npMax= self.numberTestsRunningMax
        self.npBusy = 0
        self.envFilename= None


        
    def addOptions(self, parser): 
        "Add options needed on this machine."

        super(DawnCompileMachine, self).addOptions(parser)

        parser.add_option("--j", action="store", type="int", dest='numJ', default=1,
           help="Gmake j value ")

        parser.add_option("--nodeNames", action="store", type="string", dest='nodeNames', 
            default = '', 
            help = "The names of the nodes to make on. Comma separated.        ")

        parser.add_option("--numNodes", action="store", type="int", dest='numNodes',
           default = -1, 
           help="Number of nodes to use")


    def examineOptions(self, options): 
        "Examine options from command line, possibly override command line choices."
        # Grab option values.    
        super(DawnCompileMachine, self).examineOptions(options)

        self.numJ = options.numJ
        self.allNodes= []
        if options.nodeNames != '':
            #remove quotes -- single and double.
            options.nodeNames= options.nodeNames.strip().strip("'").strip('"')
            self.allNodes= options.nodeNames.split(',')
        else:
            import socket
            thisNode= socket.gethostname()
            
            if options.numNodes > 1:
                if 'dawndev' in thisNode:
                    dawnNodeList= ['rzdawndev1', 'rzdawndev2', 'rzdawndev3']
                else:
                    dawnNodeList= ['dawn1', 'dawn2', 'dawn3', 'dawn4', 'dawn5']
                self.allNodes= ",".join(dawnNodeList[0:options.numNodes])
            else:
                self.allNodes.append(thisNode)


        self.numNodes= len(self.allNodes)
        self.numberMaxProcessors = self.npMax * self.numNodes
        self.numberTestsRunningMax = self.numberMaxProcessors

        self.allNodesUsed= {}
        for anode in self.allNodes:
            self.allNodesUsed[anode]= 0


    def label(self):
        return "dawnCompile %d nodes %d processors per node." % (self.numNodes, self.npMax)

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

        test.jobname = "t%d%s" % (test.serialNumber, test.namebase)   #namebase is a space-free version of the name
        buildLibCmd= 'all_libraries'
        if buildLibCmd in test.namebase:
            test.np = max(test.np, 1)        
        else:
            test.np = max(test.np, self.numJ)

        if gmakeCmd  in commandList:
            pos= commandList.index(gmakeCmd)
            commandList.insert(pos+1, "-j") 
            commandList.insert(pos+2, str(test.np))

        import socket
        thisNode= socket.gethostname()
        if 'dawndev' in thisNode:
            #sshList= ["ssh", "-p", "622", "-x", test.nodename] 
            sshList= ["rsh", test.nodename] 
            #sshList= ["ssh", test.nodename] 
        else:
            sshList= ["ssh", "-x", test.nodename] 
        envStr= ""

        if self.envFilename is None:
            self.envFilename= test.outname + ".env"
            envHandle= open(self.envFilename, 'w')
            for eachEnv in os.environ.keys():
                envStr= envStr + "setenv " + eachEnv + ' "'+ os.environ[eachEnv] + '"\n'
                envStr= "setenv " + eachEnv + ' "'+ os.environ[eachEnv] + '"\n'
                envHandle.write(envStr)
            envHandle.close()


        finalString= " ".join(sshList) + \
                     ' cd ' + test.directory + ";" + \
                     ' unsetenv BG_PGM_LAUNCHER ' + ";" +\
                     'source ' + self.envFilename + ' ;' +\
                     " ".join(commandList) + ";" +\
                     'echo "$?"' + ";" +\
                     'hostname'

        finalList = shlex.split(finalString)
        
        return finalList 


    def getUnusedNodeName(self, numberProcessorsDesired):
    
        if sum(self.allNodesUsed.values())==0:
            # just return the first step
            return self.allNodes[0]
    
        import math
        desiredAmount= max(numberProcessorsDesired, 1)  # should desire at least 1 processor 
        
        minValue= min(self.allNodesUsed.values())
        if minValue + desiredAmount > self.npMax:
            return None
        for anode in self.allNodes:
            if self.allNodesUsed[anode]== minValue:
            #if self.allNodesUsed[anode] + desiredAmount <= self.npMax:
                return anode

        return None
                
    
    def canRun(self, test):
        """Is this machine able to run the test interactively when resources become available? 
           If so return ''.  Otherwise return the reason it cannot be run here.
        """
        if test.np > self.numberMaxProcessors:   
            return "Too many processors needed (%d)" % test.np
        return ''

    def canRunNow(self, test): 
        "Is this machine able to run this test now? Return True/False"

        # if default_cachedir in test.directory, then test.directory has to be changed
        if '/default_cachedir' in test.directory:
            thisDir= os.getcwd() + '/'
            pos= string.find(test.directory, 'default_cachedir')
            newDir= thisDir + test.directory[pos+17:]      #default_cachedir=16 chars + '/' = 17 chars total
            test.directory= newDir

        nodename= self.getUnusedNodeName(test.np)
        if nodename is not None:
            test.nodename= nodename
            return True
        
        return False


    def noteLaunch(self, test):
        """A test has been launched."""

        self.npBusy += max(test.np, 1)
        self.allNodesUsed[test.nodename] += max(test.np, 1)


        if debug():
            log("dawnCompile.py__ Max np= %d. Launched %s with np= %d tests, total proc used = %d" % \
                (self.numberMaxProcessors, test.name, test.np, self.npBusy), echo=True)
                
        self.numberTestsRunning= self.npBusy


    def noteEnd(self, test):
        """A test has finished running. """

        self.npBusy -= max(test.np, 1)
        self.allNodesUsed[test.nodename] -= max(test.np, 1)

        if debug():
            log("Finished %s, #total proc used = %d" % \
                (test.name, self.npBusy), echo=True)

        self.numberTestsRunning= self.npBusy

        # Add to combo log file
        self.catLogFiles(test)

    def periodicReport(self): 
        "Report on current status of tasks"
        # Let's also write out the tests that are waiting ....
        
        super(DawnCompileMachine, self).periodicReport()
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
            print "\ncat of log files failed for ", test.name, " -- ", str(e)


    def quit(self): #
        if self.comboFileHandle:
            self.comboFileHandle.close()

    def getStatus (self, test): #override if not using subprocess
        """Obtains the exit code of the test object process and then sets
           the status of the test object accordingly. Returns True if test done.

           When a test has completed you must set test.statusCode and
           call self.testEnded(test, status). You may add a message as a third arg,
           which will be shown in the test's final report.
           testEnded will call your bookkeeping method noteEnd.
        """
        if configuration.options.skip:
            return True
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
                self.testEnded(test, status, "Test used " + test.elapsedTime())
                return True
            else:
                return False
        else:
            #test.statusCode = test.child.returncode
            outRead= open(test.outname, 'r')
            outStr= outRead.readlines()
            
            statusVal= outStr[-2].strip()
            if statusVal == '0': # 0 == pass, else fail
                test.statusCode= 0
            else:
                test.statusCode= 1
            if test.statusCode == 0:                               # process is done
                status = PASSED
            else:
                status= FAILED
            self.testEnded(test, status)
            return True

