#ATS:dawnHTC SELF DawnHTCMachine 1              
########## set to 1 since on dawn, can't use processor scheduling

from ats import machines, debug, atsut
from ats import log, terminal
from ats import times
import utils

import shlex
import subprocess
import sys, os, time, shlex, math
from ats.atsut import debug, RUNNING, TIMEDOUT, PASSED, FAILED, CREATED, SKIPPED
#import configuration, log

class DawnHTCMachine (machines.Machine):
    """The dawn family with processor scheduling.
    """
    def init (self): 
        self.npBusy = 0
        
        self.numNodesPerTest= 16      # on dawndev
        self.numCPUPerNode= 1         # on dawndev, SMP mode
        self.numHTCUsed= 0
                 
    def addOptions(self, parser): 

        "Add options needed on this machine."
        parser.add_option("--partition", action="store", type="string", dest='partition', 
            default = 'pdebug', 
            help = "Partition in which to run jobs with np > 0")
        parser.add_option("--bank", action="store", type="string", dest='bank', 
            default = "",
            help = "bank account for salloc to use.. 'mshare' to see what's avaialable.")
        parser.add_option("--libDir", action="store", type="string", dest='libDir', 
            default = "",
            help = "Directory of the libraries.")
        parser.add_option("--buildDir", action="store", type="string", dest='buildDir', 
            default = ".",
            help = "Director of the build executable.")

        parser.add_option("--numNodes", action="store", type="int", dest='numNodes',
           default = 1, 
           help="Number of nodes to use")
        parser.add_option("--noSalloc", action="store_true", dest='noSalloc',
           default=False,
           help="Remove salloc from run command.")
        parser.add_option("--numHTCNodes", action="store", type="int", dest='maxHTCNodes',
           default = -1, 
           help="Number of HTC nodes to use. (Any negative setting means ats will determine the max value based on available resources.)")
        parser.add_option("--htcMode", action="store", type="string", dest='htcMode', 
            default = 'smp', 
            help = "htc mode: smp, dual, or vn.")

    def examineOptions(self, options): 
        "Examine options from command line, possibly override command line choices."
        # Grab option values.    
        super(DawnHTCMachine, self).examineOptions(options)

        self.numNodes = options.numNodes
        
        if options.maxHTCNodes>=0:
            self.maxHTCNodes= options.maxHTCNodes
        else:
            if 'SLURM_NNODES' in os.environ: 
                self.maxHTCNodes= int(os.environ['SLURM_NNODES'])
            else:
                self.maxHTCNodes= options.maxHTCNodes

        if 'smp' in options.htcMode:
            self.htcMode= 1
        elif 'dual' in options.htcMode:
            self.htcMode= 2 
        elif 'vn' in options.htcMode:
            self.htcMode= 4
        else:
            self.htcMode= 1          # default to smp
        self.htcStr= options.htcMode

        self.npMax = 1

        self.maxNormalNodesRunning = (self.numNodes * self.numNodesPerTest * self.numCPUPerNode)# normal nodes

        self.maxHTCNodesRunning = (self.maxHTCNodes * self.htcMode)                            # htc nodes

        self.numberTestsRunningMax= self.maxNormalNodesRunning + self.maxHTCNodesRunning


        self.partition = options.partition
        self.bank = options.bank
        self.buildDir = options.buildDir
        self.libDir = options.libDir
       
        self.noSalloc= options.noSalloc


    def label(self):
        return "dawn %d nodes %d processors per node." % (self.numNodes, self.npMax)


    def createMpiSallocPart(self, test): 
        np = max(test.np, 1)

        test.jobname = "t%d_%d%s" % (test.np, test.serialNumber, test.namebase)   

        
      
        import string
        if not hasattr(test, 'script') or len(test.script)<=0:
            # use test.clas to obtain directory if it exists
            if not hasattr(test, 'clas') or len(test.clas)<=0:

                cdPart= "" #use current directory       .... this won't work if exe's have clas
            else:
                if len(test.clas) > 0:
                    justFullScript= test.clas[0]
                    cdPart=     "/".join( justFullScript.split('/')[0:-1] )
                else:
                    cdPart= test.directory
        else:
            cdPart=  test.directory

        test.directory= cdPart
        
        if test.useHTCNode:
            sallocPart= "cd " + cdPart + " ; " + "submit -raise -env_all -mode " + self.htcStr + " "
            mpiPart= " "
        else:
            sallocPart= "cd " + cdPart + " ; " + " salloc --reboot -J %s -A %s -p %s -t %d  -N %d         "  % (test.jobname, self.bank, self.partition,times.timeSpecToSec(test.timelimit)/60.0,test.nodes)


            mpiPart= "mpirun "  + " -n " + str(np)  
        
        return mpiPart, sallocPart

    def createCoreEnvPart(self, test): 

        import os, getpass
        #-------------------------------------------------------------- 
        if not os.environ.has_key('USER'):
            envUser= '-env USER=' + getpass.getuser()
        else:
            envUser= '-env USER='+ os.environ['USER']

        if not os.environ.has_key('LOGNAME'):
            envUser=  envUser + ' -env LOGNAME=.'
        else:
            envUser=  envUser + ' -env LOGNAME='+ os.environ['LOGNAME']
        #-------------------------------------------------------------- 
        envPwd=  ' -env PWD=' + test.directory
        #-------------------------------------------------------------- 
        if not os.environ.has_key('HOME'):
            envHome= '-env HOME=.'
        else:
            envHome= '-env HOME='+ os.environ['HOME']
            
            if not os.environ.has_key('PATH'):
                envHome= envHome + ' -env PATH=.'
            else:
                allPaths= os.environ['PATH']
                allPathList= allPaths.split(":")
                allPathSet= set(allPathList)
                thePath= ":".join(allPathSet)    
                envHome= envHome +  ' -env PATH=.:'+ thePath  
        #-------------------------------------------------------------- 

        return " ".join([astring for astring in (envUser,envPwd,envHome)])


    def createMoreEnvPart(self, test):

        envPythonPath= '-env PYTHONPATH=' + self.libDir + "/lib "
        envLdLibraryPathMustHave= '-env  LD_LIBRARY_PATH=/opt/ibmcmp/lib/bg/bglib ' 

        return " ".join([astring for astring in (envPythonPath,\
                                                 envLdLibraryPathMustHave )])
        


    def calculateCommandList(self, test): 
        """Prepare for run of executable using a suitable command. First we get the plain command
         line that would be executed on a vanilla serial machine, then we modify it if necessary
         for use on this machines.
        """

        commandList = self.calculateBasicCommandList(test)
        
        mpiPart, sallocPart= self.createMpiSallocPart(test)
        allEnvPart= self.createCoreEnvPart(test) + " " + self.createMoreEnvPart(test)

        #-------------------------------------------------------------- 

        finalCommand= " "
        if not self.noSalloc:
            finalCommand= finalCommand  + sallocPart

        finalCommand= finalCommand + " "+\
                      mpiPart + " " +\
                      allEnvPart
                      
        finalCommandList= shlex.split(finalCommand) + commandList 

        finalPart=  " ".join(finalCommandList)
        if test.useHTCNode:        #check the submit line len
            maxSubmitLength= 1420                # max for submit 
        else:
            maxSubmitLength= 2020                # max 

        import string
        checkLength= 1

        if checkLength:
            finalSubmitPart=  finalPart
            
            resultStringLd= self.getShortSubmit(finalSubmitPart, 'LD_LIBRARY_PATH', minNumPath=4)
            finalSubmitPart= resultStringLd
            finalPart= finalSubmitPart
            if resultStringLd is not None:
                resultStringPath= self.getShortSubmit(resultStringLd, 'PATH', minNumPath=4)
                finalSubmitPart= resultStringPath
                finalPart= finalSubmitPart
               
                if resultStringPath is None or len(resultStringPath) > maxSubmitLength:
                    if test.useHTCNode==True:
                        test.useHTCNode= False
                        test.cancelRun= True
                        return self.calculateCommandList(test)
            else:
                if test.useHTCNode==True:
                    test.useHTCNode= False
                    test.cancelRun= True
                    return self.calculateCommandList(test)

        # "/dev/null" is needed to prevent atsb from going into suspend mode if the os is expecting something from the exe.
        finalCommandList= shlex.split(finalPart) + shlex.split(" < /dev/null")
        return finalCommandList


    def getShortSubmit(self, inString, envName, minNumPath=1):
       import string
       # grab just the envName part 
       #print " -- envName= ", envName
       #print " -- inString= ", inString
       posStart= string.find(inString,envName)
       posEnd= string.find(inString, " ", posStart)
       if posEnd == -1:      # " " not found
          posEnd= len(inString)
       
       toChangePart= inString[posStart:posEnd]
       #print " -- toChangePart= ", toChangePart

       aList= toChangePart.split(':')
       oldList= aList[1:]
       newString= toChangePart

       moreToRemove= 1
       while moreToRemove and len(newString) > 100:
           if len(oldList) > minNumPath-1:         #need the first x paths
               oldList= oldList[0:-1]
               aSet= set(oldList)
               if len(aSet)>1:
                   #newPath= "".join([aList[0] , ":",  ":".join(aSet)] )
                   newList= []
                   for aPath in oldList:
                       if aPath in aSet:
                           newList.append(aPath)
                           aSet.remove(aPath)
                   newPath= aList[0] +  ":" + ":".join(newList)
               else:
                   newPath= aList[0]
               newString= inString[0:posStart] + newPath + inString[posEnd:]
           else:
               moreToRemove= 0

       # there is a max length count for each env var also.. it is less than 500.
       if len(newPath)>395:      
           return None
       #print " -- return newString= ", newString
       return newString


    def canRun(self, test):
        """Is this machine able to run the test interactively when resources become available? 
           If so return ''.  Otherwise return the reason it cannot be run here.
        """
        # determine the number of nodes this test requires
        np = max(test.np, 1)
        numProcessPerMpiRun= self.numCPUPerNode      
        numberOfNodesNeeded, r = divmod(np, numProcessPerMpiRun)
        if r: numberOfNodesNeeded += 1
        test.nodes= numberOfNodesNeeded
        test.cancelRun= False
        
        if np==1 and self.maxHTCNodes>0:
            test.useHTCNode= True    # setting all np==1 jobs for the HTC nodes.
        else:
            test.useHTCNode= False
        
        if test.np > max(self.htcMode, self.maxNormalNodesRunning):  
            return "Too many processors needed (%d)" % test.np
        return ''

    def canRunNow(self, test): 
        "Is this machine able to run this test now? Return True/False"

        # check if test is able to run using the HTC nodes
        np = max(test.np, 1)
        if test.useHTCNode and (self.maxHTCNodes > 0):
            if (self.numHTCUsed + test.nodes) <= self.maxHTCNodes:

                # call this to determine whether to use or not use the htc node.
                commandList = self.calculateCommandList(test)  
                if test.cancelRun:
                    test.cancelRun= False
                    return False 

                return True
            else:
                return False           
        
        # now check if any normal nodes are available
        if ( self.npBusy + ( math.ceil(test.nodes/float(self.numNodesPerTest)) * self.numNodesPerTest * self.numCPUPerNode) ) > self.maxNormalNodesRunning:
            return False
        else:
            return True
        return False

    def _launch(self, test): #replace if not using subprocess

        try:
            test.outhandle = open(test.outname, 'w')
            test.errhandle = open(test.errname, 'w')
            Eadd = test.options.get('env', None)
            if Eadd is None:
                E = None
            else:
                E = os.environ.copy()
                E.update(Eadd)

            test.child = subprocess.Popen(test.commandLine, shell=True, cwd=test.directory, 
                                          stdout = test.outhandle, stderr = test.errhandle)
            test.set(RUNNING, test.commandLine)
            self.running.append(test)

            return True
        except OSError, e:
            test.outhandle.close()
            test.errhandle.close()
            test.set(FAILED, str(e))
            return False
   
    

    def noteLaunch(self, test):
        """A test has been launched."""
        # noteLaunch is called by machines.py (startRun() -> launch() -> noteLaunch()

        import math

        if test.useHTCNode:
            self.numHTCUsed += test.nodes
        else:
            self.npBusy += ( math.ceil(test.nodes/float(self.numNodesPerTest))   * self.numNodesPerTest * self.numCPUPerNode)
        self.numberTestsRunning = self.numHTCUsed + ( self.npBusy / self.numNodesPerTest )

        if debug():
            log("dawnHTC.py:  Launched %s,\tnow running %d tests,\t#nodes used = %d,\t#htc used= %d" % \
                (test.name, self.numberTestsRunning, self.npBusy, self.numHTCUsed), echo=True)
           

        self.periodicReport()

    def noteEnd(self, test):
        """A test has finished running. """
        # noteEnd is called by machines.py (getStatus() -> testEnded() -> noteEnd()

        import math
        if test.useHTCNode:
            self.numHTCUsed -= test.nodes
        else:
            self.npBusy -= ( math.ceil(test.nodes/float(self.numNodesPerTest))  * self.numNodesPerTest * self.numCPUPerNode)

        self.numberTestsRunning = self.numHTCUsed + ( self.npBusy / self.numNodesPerTest )

        if debug():
            log("Finished %s, now running %d tests, #proc used = %d" % \
                (test.name, self.numberTestsRunning, self.npBusy), echo=True)

    def periodicReport(self): 
        "Report on current status of tasks"
        # Let's also write out the tests that are waiting ....
        
        super(DawnHTCMachine, self).periodicReport()

        runningInHTCNode=  [ t.name for t in self.scheduler.testlist() if hasattr(t,'useHTCNode') and t.useHTCNode and t.status is RUNNING]

        if len(runningInHTCNode) > 1:
            terminal("HTC RUNNING:", len(runningInHTCNode), ", ".join(runningInHTCNode[:]))
        
        
        currentEligible=  [ t.name for t in self.scheduler.testlist() if t.status is atsut.CREATED ]

        if len(currentEligible) > 1:
            terminal("WAITING:", ", ".join(currentEligible[:5]), "... (more)")
       

        terminal("----------------------------------------")

    def quit(self): #
        "Final cleanup if any."
        if debug():
            log("dawnHTC.py --- quit() -- final cleanup", echo=True)


    def kill(self, test): 

        "Final cleanup if any."
        # kill the test
        # This is necessary -- killing the srun command itself is not enough to end the job... it is still running (squeue will show this)
        import subprocess
        
        if test.status is RUNNING or test.status is TIMEDOUT:
            try:
                if not test.useHTCNode:
                    if debug():
                        log("---- kill() in dawnHTC.py, command= scancel -n  %s ----" %  (test.jobname), echo=True)
                        
                    retcode= subprocess.call("scancel" + " -n  " + test.jobname, shell=True)
                    if retcode < 0:
                        log("---- kill() in dawnHTC.py, command= scancel -n  %s failed with return code -%d  ----" %  (test.jobname, retcode), echo=True)
            except OSError, e:
                log("---- kill() in dawnHTC.py, execution of command failed (scancel -n  %s) failed:  %s----" %  (test.jobname, e), echo=True)




