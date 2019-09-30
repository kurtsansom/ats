#ATS:t = test(SELF, clas='a b c', eos='LEOS', np=0)
#ATS:testif(t, SELF, clas='d e f', label='np=2 conditional', eos='LEOS', np = 2, check=1)
import sys
print('#ATS: This tested an LEOS eos, args=%s' % str(sys.argv[1:]))
