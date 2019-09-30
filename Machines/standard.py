#ATS:darwin machines Machine -2
#ATS:win32 SELF WinMachine 1
#BATS:batchsimulator machines BatchSimulator 1200

from ats import machines
import shlex

class WinMachine (machines.Machine):
    "Windows machine."
    def split(self, clas):
        return shlex.split(clas, posix=False)

