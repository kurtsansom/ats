#ATS:test(SELF, "-v")
"Unit tests for ATS components."
import unittest, sys, os
import ats

def makeShortPythonScript():
    pythonScript = 'hoo.py'
    fp = open(pythonScript,'w')
    fp.write('print "hello world"')
    fp.close()
    return pythonScript

class AtsBatchTest (unittest.TestCase):

    def setUp (self):
        ats.log.logging = 0
        ats.log.verbose = 0
        ats.log.name = 'atstest.log'
        ats.manager.executable = sys.executable
        ats.manager.skip = 1
        ats.manager.init()
        ats.filterdefs()

    def testBatch (self):
        "Test setting of batch option"        

        foo = makeShortPythonScript()

        # batch option is on, test problem is for batch run
        ats.manager.batch=1
        ats.unstick()
        ats.stick(batch=1)
        ats.manager.test('foo.py')
        test = ats.manager.testlist[0]
        # will submit a batch job
        self.failUnless(test.options.has_key('batch'))
        self.assertEqual(test.options['batch'], 1)

        # ats batch option is on, but this test problem is not for batch run
        ats.manager.batch=1   # ats batch option is on
        ats.unstick()         # foo.py is not for batch run
        # batch is not submitted
        ats.manager.test('goo.py')
        test = ats.manager.testlist[1]
        self.failIf(test.options.has_key('batch'))
        self.assertEqual(test.options.get('batch',-1), -1)

        # ats batch option is not on, test problem is for batch run
        ats.manager.batch = 0 # ats batch option is not on
        ats.stick(batch=1)    # foo is not for batch run
        # should get SKIP for this batch job
        ats.manager.test(foo)
        test = ats.manager.testlist[2]
        self.assertEqual(test.status, ats.tests.SKIPPED)

        # remove this temporary python script
        os.remove(foo)

    def testgetName (self):
        "Test to create a unique batch job name"

        import time

        # make sure that 2 names do not collide and get unique name
        jobname1 = ats.batchRun.getName(name='goo',arch=os.uname()[0])
        jobname2 = ats.batchRun.getName(name='goo',arch=os.uname()[0])
        self.assertNotEqual(jobname1,jobname2)

if __name__ == "__main__":
    unittest.main()
