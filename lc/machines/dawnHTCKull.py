#ATS:dawndevKull SELF DawnHTCKullMachine 1              
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
from dawnHTC import DawnHTCMachine


class DawnHTCKullMachine (DawnHTCMachine):
    """The dawn family with processor scheduling.
    """
    def init (self): 
        super(DawnHTCKullMachine, self).init()
        self.forkSubprocess= None
                 
    def forkServerSetup (self): 
        import tempfile
        if not os.environ.has_key('FORKSERVERDIR'):
            forkCommand= "/usr/gapps/coop/forkserver/bin/forkserver.py"
            try:
                outHandle= tempfile.NamedTemporaryFile('w')
                errHandle=  tempfile.NamedTemporaryFile('w')
                self.forkSubprocess= subprocess.Popen(forkCommand, shell=True, stdout=outHandle, stderr=errHandle)
            except OSError, e:
                #print "error in running forkserver .."
                print "Error in running the forkserver. ", sys.exc_info()[0]
                outHandle.close()
                errHandle.close()

            import time
            time.sleep(2)  # give the forkserver a sec to write out the directory name
   
            try:
                newfile= open(outHandle.name, 'r') 
                line1= newfile.readlines()
    
                os.environ['FORKSERVERDIR']= line1[0].strip()
                log("Note: setting FORKSERVER env to be %s" % (line1[0]), echo=True)
            except:
                log("Note: setting FORKSERVER env to be .", echo=True)

    def addOptions(self, parser): 

        super(DawnHTCKullMachine, self).addOptions(parser)

        # change parser defaults
        parser.set_defaults(bank='kull')
        parser.set_defaults(libDir='/usr/apps/kull/lib//v2.16/bgpxlc-cross/optimize/')
        parser.set_defaults(buildDir='.')

    def examineOptions(self, options):
        "Examine options from command line, possibly override command line choices."
        # Grab option values.    
        super(DawnHTCKullMachine, self).examineOptions(options)
        
        if self.forkSubprocess is None and not options.skip:
            self.forkServerSetup()


    # depends on the bank settings here 
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


    def createMoreEnvPart(self, test):

        if not os.environ.has_key('KULL_TESTDATA'):
            envTestData= '-env KULL_TESTDATA=.'
        else:
            envTestData= '-env KULL_TESTDATA=' + os.environ['KULL_TESTDATA']
        #-------------------------------------------------------------- 
        if not os.environ.has_key('FORKSERVERDIR'):
            envExtra= '-env FORKSERVERDIR=.'
        else:
            envExtra= '-env FORKSERVERDIR=' + os.environ['FORKSERVERDIR']
        #-------------------------------------------------------------- 
        buildDir= self.buildDir
        if buildDir is None or buildDir=='.':
            buildDir= '/'.join(test.executable.path.split('/')[0:-2])
            
        envPythonPath= '-env PYTHONPATH=' + buildDir + '/lib:' + self.libDir + "/lib "

        ldOldPath= '.'
        if os.environ.has_key('LD_LIBRARY_PATH'):
            ldOldPath= os.environ['LD_LIBRARY_PATH']   # expand this because submit will expand before checking the line length.
        
        envLdLibraryPathMustHave= '-env  LD_LIBRARY_PATH=/opt/ibmcmp/lib/bg/bglib:' + \
                                  buildDir + '/lib:' + self.libDir + "/lib:" + \
                                  buildDir + '/swigTypeCheck/:' + ldOldPath

        return " ".join([astring for astring in (envTestData,\
                                                 envExtra,\
                                                 envPythonPath,\
                                                 envLdLibraryPathMustHave )])
        





    def quit(self): #
        "Final cleanup if any."
        log("dawnHTCKull.py --- quit() -- final cleanup", echo=True)
        if self.forkSubprocess:
            import signal
            import time
            os.kill(self.forkSubprocess.pid, signal.SIGTERM)


