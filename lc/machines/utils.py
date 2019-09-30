import os, sys, string, subprocess
from ats import debug, SYS_TYPE

_myDebugLevel= 10

def utilDebugLevel(value=None):
    "Return the _myDebugLevel flag; if value given, set it."
    global _myDebugLevel
    if value is None:
        return _myDebugLevel
    else:
        _myDebugLevel = int(value)

#--------------------------------------------------------------------------

def tryint(s):
    try:
        return int(s)
    except:
        return s

def alphanum_key(s):
    """ Turn a string into a list of string and number chunks.
        "z23a" -> ["z", 23, "a"]
    """
    import re
    return [ tryint(c) for c in re.split('([0-9]+)', s) ]

# Used by getAllHostnames()
def sort_nicely(l): 

    """ Sort the given list in the way that humans expect.
    """
    l.sort(key=alphanum_key)


#--------------------------------------------------------------------------

def getAllHostnames():

    cmd= "srun hostname"
    if SYS_TYPE.startswith('aix'):
        cmd= "poe hostname"

    if debug() >= utilDebugLevel():
        print "in getAllHostnames() ---- running command:  ", cmd
    allHostname= []
    try:
        import subprocess
        import getpass

        proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
        stdout_value = proc.communicate()[0]

        if (len(stdout_value)==0):
            return allHostname

        theLines= string.split(stdout_value, '\n')

        for aline in theLines:
            aline= "spacer:" + aline
            oneHostname= string.split(aline,":")[-1]
            if oneHostname != '':
                if oneHostname not in allHostname:
                    allHostname.append(oneHostname)


        if debug() >= utilDebugLevel():
            print "DEBUG: before sort ", allHostname
        sort_nicely(allHostname)
        if debug() >= utilDebugLevel():
            print "DEBUG: after sort ", allHostname
        
    except:
        print "Unexpected error in utils.py getAllHostnames:", sys.exc_info()[0]
        return allHostname
    return allHostname



#------------------------------------------------------------------------------
def setStepNumWithNode(inMaxStepNum):
# inMaxStepNum - For a group of nodes, the max step number is the max number of nodes minus 1.
# Returns:  The stepid used to obtain the nodes and for each step, the node assoicated with it.  
#           returns --> stepid, nodeStepDic[node]=stepNum

    return  getNodeAndStepIdAssociatedWithStepNumberLinux(inMaxStepNum)

#------------------------------------------------------------------------------
def findAvailableStep(inNodeList, inNodeUsedTotalDic, inNodeStepNumDic, inMaxProcsPerNode, inDesiredAmount,  oldStep=0):


    if sum(inNodeUsedTotalDic.values())==0:
        return 0  # just return the first step, all nodes available

    nodeAvailDic= {}
    for anode in inNodeList:
       nodeAvailDic[anode]= inMaxProcsPerNode - inNodeUsedTotalDic[anode]

    if sum(nodeAvailDic.values()) == 0:
        return None   # no nodes available
    totalTasksUsed= 0
    stepWithAvailableProc= -1

    from operator import itemgetter
    stepNodeDic= dict([ (v,k) for (k,v) in inNodeStepNumDic.iteritems() ])

    stepNum= 0          #start with 0
    import math
    inDesiredAmount= max(inDesiredAmount, 1)  # should desire at least 1 processor 
    numNodesToUse= max(1, int(math.ceil(float(inDesiredAmount)/float(inMaxProcsPerNode))) )
    #-------------------------------------------
    # Find all the combinations
    #-------------------------------------------
    maxCount= len(inNodeList)
    if debug() >= utilDebugLevel():
        print "DEBUG: in utils::findAvailableStep() -- numNodesToUse= " , numNodesToUse
    comboList= []
    for ii in range (stepNum, maxCount):
        totalValue= ii
        tempCombo= []
        for jj in range(numNodesToUse):
            tempCombo.append(totalValue)
            if totalValue < maxCount-1:
                totalValue += 1
            else:
                break
        if len(tempCombo)==numNodesToUse:
            comboList.append(tempCombo)
    sys.stdout.flush()
    if debug() >= utilDebugLevel():
        print "DEBUG: in utils::findAvailableStep() -- inDesiredAmount= " , inDesiredAmount
        print "DEBUG: in utils::findAvailableStep() -- comboList= " , comboList
        print "DEBUG: in utils::findAvailableStep() -- nodeAvailDic= ", nodeAvailDic

    #-------------------------------sum all the combo
    allSavedStep= []
    for eachCombo in comboList:
         totalAvail= 0
         savedStep= -1
         for astep in eachCombo:
             if savedStep==-1:
                 savedStep= astep    # note the first step
             totalAvail= totalAvail + nodeAvailDic[ stepNodeDic[str(astep)] ]
             if debug() >= utilDebugLevel():
                 print " nodeAvailDic[ ", stepNodeDic[str(astep)], "= ", nodeAvailDic[ stepNodeDic[str(astep)]] 
                 print "eachCombo= ", eachCombo, "astep=", astep, "totalAvail=", totalAvail
             if totalAvail >= inDesiredAmount:
                 if savedStep != oldStep:
                     if debug() >= utilDebugLevel():
                         print "returned savedStep= ", savedStep
                     return savedStep           
                 else:
                     allSavedStep.append(savedStep)


    if len(allSavedStep) > 0:
       if debug() >= utilDebugLevel():
           print " ---- allSavedStep= ", allSavedStep
           print " ---- returned savedStep= ", savedStep
       return allSavedStep[0]
    return None



#------------------------------------------------------------------------------
def addToUsedTotalDic(inNodeUsedDic, inNodeStepNumDic, inMaxProcsPerNode, inFirstStep, inAmountToAdd):

    from operator import itemgetter
    stepNodeDic= dict([ (v,k) for (k,v) in inNodeStepNumDic.iteritems() ])

    import math
    numNodesToUse= max(1, int(math.ceil(float(inAmountToAdd)/float(inMaxProcsPerNode))) )
    #-------------------------------
    aStep= inFirstStep
    amountLeft= max(inAmountToAdd, 1)
    for ii in range(0, numNodesToUse):
        tempToAdd= min(amountLeft, inMaxProcsPerNode)
        inNodeUsedDic[ stepNodeDic[str( aStep )] ] += tempToAdd 
        amountLeft= amountLeft - tempToAdd
        aStep = (aStep + 1) % len(inNodeStepNumDic)

def removeFromUsedTotalDic (inNodeUsedDic, inNodeStepNumDic, inMaxProcsPerNode, inFirstStep, inAmountToDelete, inStepId, inNodeList):

    from operator import itemgetter
    stepNodeDic= dict([ (v,k) for (k,v) in inNodeStepNumDic.iteritems() ])

    import math
    numNodesToUse= max(1, int(math.ceil(float(inAmountToDelete)/float(inMaxProcsPerNode))) )
    #-------------------------------
    aStep= inFirstStep
    amountLeft= max(inAmountToDelete, 1)
    for ii in range(0, numNodesToUse):
        tempToDelete= min(amountLeft, inMaxProcsPerNode)
        inNodeUsedDic[ stepNodeDic[str( aStep )] ] -= tempToDelete

        amountLeft= amountLeft - tempToDelete
        aStep = (aStep + 1) % len(inNodeStepNumDic)
        if amountLeft<=0:
            break
    return inNodeUsedDic

#------------------------------------------------------------------------------
def checkForSrunDefunct(anode):
    rshCommand= 'rsh ' +  anode + ' ps u'
    returnCode, runOutput= runThisCommand(rshCommand)
   
    theLines= string.split(runOutput, '\n')
    for aline in theLines:
        if 'srun' in aline and 'defunct' in aline:
            return 1
    
    return 0

#------------------------------------------------------------------------------

def usingRshFindTotalProcessorsUsed (inNodeList, inStepNumNodeNameDic, maxProcsPerNode):
# assumes '-r ' is used in srun command: ie: "srun -r ..."
    taskTotal= {}
    for anode in inNodeList:
        taskTotal[anode]= 0

    for anode in inNodeList:
        rshCommand= 'rsh ' +  anode + ' ps u'
        returnCode, runOutput= runThisCommand(rshCommand)
   
        theLines= string.split(runOutput, '\n')
        for aline in theLines:
            if ' srun ' in aline:
                if ' -n ' in aline: 
                    lineVals= aline.split()

                    pos= lineVals.index('-n')
                    numProcessors=  int(lineVals[pos+1])

                    pos= lineVals.index('-r')
                    stepUsed=  lineVals[pos+1]
                     
                    nodeName= inStepNumNodeNameDic[stepUsed]
                    taskTotal[nodeName]= taskTotal[nodeName] + numProcessors


        break  # let's just check the 1st node, this should be enough

    return taskTotal

#------------------------------------------------------------------------------
def getUnusedNode(inNodeList, desiredAmount, maxProcsPerNode, 
                  inNodeStepNumDic, inStepId):
# 
# inNodeList - List of nodes available to use.
# desiredAmount - The number of processors needed.
# inNodeStepNumDic - Dic of (stepNum, node) association.
# inStepId - The step id used.
#
# Returns the step number that is qualified to provide the desired number of processors needed.
# If no steps are valid, None is returned.
#         returns -> stepNum 
#

    allHostname= []
    import subprocess
    import getpass 
    maxProcessorsList= []

    maxCount= len(inNodeList)

    from operator import itemgetter
    stepNodeDic= dict([ (v,k) for (k,v) in inNodeStepNumDic.iteritems() ])

    nodeUsedTotalDic= usingRshFindTotalProcessorsUsed(inNodeList, stepNodeDic, maxProcsPerNode)

    if sum(nodeUsedTotalDic.values())==0:
        # just return the first step
        return nodeUsedTotalDic, 0

    nodeAvailDic= {}
    for anode in inNodeList:
       nodeAvailDic[anode]= maxProcsPerNode - nodeUsedTotalDic[anode]
    totalTasksUsed= 0
    stepWithAvailableProc= -1


    stepNum= 0 #start with first node
    import math
    desiredAmount= max(desiredAmount, 1)  # should desire at least 1 processor 
    numNodesToUse= max(1, int(math.ceil(float(desiredAmount)/float(maxProcsPerNode))) )
    #-------------------------------------------
    # Find all the combinations
    #-------------------------------------------
    if debug() >= utilDebugLevel():
        print "DEBUG: in utils::getUnusedNode() -- numNodesToUse= " , numNodesToUse
    comboList= []
    for ii in range (stepNum, maxCount):
        totalValue= ii
        tempCombo= []
        for jj in range(numNodesToUse):
            tempCombo.append(totalValue)
            if totalValue < maxCount-1:
                totalValue += 1
            else:
                break
        if len(tempCombo)==numNodesToUse:
            comboList.append(tempCombo)
    sys.stdout.flush()
    if debug() >= utilDebugLevel():
        print "DEBUG: in utils::getUnusedNode() -- desiredAmount= " , desiredAmount
        print "DEBUG: in utils::getUnusedNode() -- comboList= " , comboList

    #-------------------------------sum all the combo
    for eachCombo in comboList:
         totalAvail= 0
         savedStep= -1

         for astep in eachCombo:
             if savedStep==-1:
                 savedStep= astep    # note the first step
             totalAvail= totalAvail + nodeAvailDic[ stepNodeDic[str(astep)] ]
             if debug() >= utilDebugLevel():
                 print "eachCombo= ", eachCombo, "astep=", astep, "totalAvail=", totalAvail
             if totalAvail >= desiredAmount:
                 if debug() >= utilDebugLevel():
                     print "returned savedStep= ", savedStep
                 return nodeUsedTotalDic, savedStep           

    return nodeUsedTotalDic, None


def getNodeAndStepIdAssociatedWithStepNumberLinux(inMaxStep):
# 
# Returns the node and step id associated with the step number.
#       returns -> node, stepid
    #--------------------------------------------------
    # Determine who the user is..
    #--------------------------------------------------
    cmd= "whoami"
    proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)

    stdout_value = proc.communicate()[0]
    if (len(stdout_value)==0):
        
        if debug() >= utilDebugLevel():
            print "DEBUG: in utils::getNodeAndStepIdAssociatedWithStepNumberLinux() -- whoami " 
        userName= os.environ['LOGNAME']
    else:
        theLines= string.split(stdout_value, '\n')
        if len(theLines) >= 1:
            userName= theLines[0]

    #--------------------------------------------------
    # Gather any stepids for the user first
    # "squeue -s -u userName"                           
    #--------------------------------------------------
    #
    #  unset SQUEUE_FORMAT before using "squeue -s"
    #--------------------------------------------------
    if os.environ.has_key('SQUEUE_FORMAT'):
        oldSqueueFormatValue= os.environ['SQUEUE_FORMAT']
        os.unsetenv('SQUEUE_FORMAT') 

    squeueCmd= "squeue -s -u " + userName
    proc = subprocess.Popen(squeueCmd, shell=True, stdout=subprocess.PIPE)
    stdout_value = proc.communicate()[0]

    if (len(stdout_value)==0):          # no return values
        return inStepNum

    stepList= []
    nameList= []
        
    theLines= string.split(stdout_value, '\n')
    for aline in theLines:
        if "STEPID" in aline:
            continue
        else:
            splitVals= aline.split()
            if len(splitVals) > 4:
                stepList.append(splitVals[0])
            if len(splitVals) > 4:
                nameList.append(splitVals[1])

    if debug() >= utilDebugLevel():
        print "stepList= ", stepList
        print "nameList= ", nameList

    #--------------------------------------------------
    # For the step number, determine the node assoicated with it.
    #--------------------------------------------------
    # Using "sleep" check which node is used.
    #
    stepToCheck= 0
    for ii in range(inMaxStep):
        # embed the process id into the job name to distinguish between invocation of the ats.
        cmd= "srun -N1 -J %d_%d -n 1 -r %d sleep 5" % ( os.getpid(), ii, ii )
        sleepProc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)

    #--------------------------------------------------
    # "squeue -s -u userName " --- again to check which node corresponds to the step
    #--------------------------------------------------

    # continue issuing the squeueCmd until all the nodes corresponding to the step are found.
    stepIdToCheck= None
    while 1:  
        proc = subprocess.Popen(squeueCmd, shell=True, stdout=subprocess.PIPE)
        stdout_value = proc.communicate()[0]
        if (len(stdout_value)==0):
            return None

        theLines= string.split(stdout_value, '\n')
            
        if debug() >= utilDebugLevel():
            for aline in theLines:
                print "LINES READ: ", aline

        nodeToCheck= ""
        newStep= '0'
        nodeStepDic= {}
        for aline in theLines:
            if "STEPID" in aline:
                continue
            else:
                #STEPID         NAME PARTITION     USER      TIME NODELIST
                #1131361.3  sleepJob    pdebug    tangn      0:02 alastor6

                splitVals= aline.split()
                if len(splitVals) > 5:
                    newStep=  splitVals[0]
                    newName=   splitVals[1]
                    #checking newStep value is not enough because the user may have the step used to run something else.
                    if newStep not in stepList or newName not in nameList:  
                        nodeToCheck= splitVals[5]
                        pid, stepLink = splitVals[1].split("_")
                        if int(pid) == os.getpid():
                            nodeStepDic[nodeToCheck]= stepLink
                        else:
                            continue
                        
        if (len(nodeStepDic) > 0):
            stepIdToCheck= newStep.split(".")[0]

        if debug() >= utilDebugLevel():
            print "nodeStepDic= ", nodeStepDic
            print "stepIdToCheck= ", stepIdToCheck,

        if (len(nodeStepDic) == inMaxStep ):
            break
        # end while loop

    #  re-set SQUEUE_FORMAT after using "squeue -s"
    #--------------------------------------------------
    if os.environ.has_key('SQUEUE_FORMAT'):
        os.environ['SQUEUE_FORMAT']=  oldSqueueFormatValue

    if nodeToCheck == '' or newStep== '':
        return None, None

    return stepIdToCheck, nodeStepDic


#---------------------------------------------------------------------------
def getNumberOfProcessorsPerNode(useNode=None):
    # Assume all nodes on this machine has the same number of processors

    if os.environ.has_key('SYS_TYPE'):
        SYS_TYPE= os.environ['SYS_TYPE']
    else:
        SYS_TYPE= ''
    try:
        import string
        import subprocess
        stdout_value = '0'
        catCmd= 'lsdev -C -c processor | wc -l'

        if SYS_TYPE.startswith('aix'):

            cmd = 'scontrol show node | head -2 '

            proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
            stdout_value = proc.communicate()[0]
        
            cmdVal= repr(stdout_value)
            
            # Expect value to be similar to this format
            #
            # ["'NodeName", 'alc36 State', 'ALLOCATED CPUs', '2 AllocCPUs', '2 RealMemory', '3300 TmpDisk',"0\\n'"]
            #
            # grab cpu information
         
            allVals= string.split(cmdVal)
            
            numCPU= '0'
            for val in allVals:
                if val.startswith('CPUTot'):
                    numCPU= val.split('=')[-1]
                    break
           
            return  int(numCPU)

        else: #if SYS_TYPE.startswith('linux'):
            catCmd= 'cat /proc/cpuinfo | grep processor | wc -l'
        
        # grab cpu information
        if useNode==None:
            cmdToUse= catCmd 
        else:
            sshCmd= 'ssh ' + useNode + ' '
            cmdToUse= sshCmd + '"' + catCmd + '"'
        
        proc= subprocess.Popen(cmdToUse, shell=True, stdout=subprocess.PIPE,)
        stdout_value = proc.communicate()[0]
        numCpu= string.split(stdout_value)[0]   # another way of getting CPUs
        return  int(numCpu)
    except KeyboardInterrupt:
        raise
    except:
        print "Unexpected error in getNumberOfProcsPerNode:", sys.exc_info()
        return 0


#---------------------------------------------------------------------------

def runThisCommand(cmd):
    import subprocess
    aProcess= subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
    aProcess.wait()
    output = aProcess.communicate()[0]
    returnCode= aProcess.returncode

    return returnCode, output

#---------------------------------------------------------------------------

