


# Some comments before the ATS statements
#ATS:stick(physics=['Lagrangian', 'ALE', 'lasers'], eos='LEOS')
#ATS:test(SELF,'mymessage', label='with arg')
#ATS:t = test(SELF,'timeout', label='time out', timelimit='10s')
#ATS:t.expectedResult=TIMEDOUT
#

#ATS:~test(SELF, label='without arg')  #fails
import sys, os, time
if sys.argv[1:]:
    a = " ".join(sys.argv[1:])
    print a
    if sys.argv[1].startswith('timeout'):
        i = 0
        w = range(1000000)
        while 1:
            for j in range(len(w)):
                if j == i: 
                    i += 1
                    break
            print os.times()[0:2], i
            time.sleep(2)
    print "#ATS:Times:", sys.argv[1], os.times()[0:2]
else:
   print 'I am not feeling well.   Uhhhh....'
   raise RuntimeError, 'Did not politely greet me, it dies.'

