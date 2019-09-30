#ATS:glue(nightly=1)
#ATS:print checkGlue('nightly')

#ATS:isNightly= checkGlue('nightly')
#ATS:if SYS_TYPE.startswith('aix'):
#ATS:    if (isNightly is None) or (isNightly != 1):
#ATS:        # run on aix
#ATS:        print "run on aix only"
#ATS:        test(SELF, 'run on aix only')
#ATS:else:
#ATS:    test(SELF, 'run on linux only')
#ATS:    print "run on linux always"

import sys
print "testCheckGlue, ", sys.argv[1]
