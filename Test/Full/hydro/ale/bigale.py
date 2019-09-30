#ATS:stick(physics=['Lagrangian', 'ALE', 'lasers'], eos='LEOS', np=2)
#ATS:test(SELF, 'separate batchjob', label='separate', batch=1)
#ATS:t =test(SELF, 'parent batchjob', label='parent', batch=1)
#ATS:testif(t, SELF, 'mymessage batchjob', label='child should batch')
import sys
if sys.argv[1:]:
    a = " ".join(sys.argv[1:])
    print '#ATS:bigale', a

