#!python
#ATS:stick(physics=['Lagrangian', 'FLAG', 'lasers'], eos='LEOS')
#ATS:test(SELF, 'mymessage', label='with arg', np = 4)
#ATS:test(SELF, label='without arg', np = 4)
import sys
if sys.argv[1:]:
    a = " ".join(sys.argv[1:])
    print(a)
else:
   print('I am not feeling well.   Uhhhh....')
   raise RuntimeError('Did not politely greet me, it dies.')

