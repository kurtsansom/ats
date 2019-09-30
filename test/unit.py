"Unit tests for ATS components."
#ATS:test(SELF, '-v')
import unittest, sys, os
import ats
from ats import times, testEnvironment, manager, configuration
filterdefs = ats.management.filterdefs
log = testEnvironment['log']
test = testEnvironment['test']
testif = testEnvironment['testif']
manager = testEnvironment['manager']
filter = testEnvironment['filter']
glue = testEnvironment['glue']
tack = testEnvironment['tack']
stick = testEnvironment['stick']
unglue = testEnvironment['unglue']
untack = testEnvironment['untack']
unstick = testEnvironment['unstick']
getOptions = testEnvironment['getOptions']
INVALID = testEnvironment['INVALID']
CREATED = testEnvironment['CREATED']
FILTERED = testEnvironment['FILTERED']

class LogTest(unittest.TestCase):
    "Test the ATS log."
    def setUp (self):
        argv = "--skip --log ats.logs --quiet"
        manager.init(argv)
        log.logging = 0
        unglue()
        unstick()

    def testLogCreation (self):
        "Test basic log creation."
        name = log.name
        self.assertTrue(os.path.isabs(name))
        self.assertEqual(log.directory, os.getcwd())
        self.assertEqual(log.shortname, 'ats.log')

    def testLogVerbosity (self):
        "Test that a --verbose ends up correctly."
        argv = "--skip --log ats.log --verbose"
        manager.init(argv)
        log.logging = 0
        self.assertEqual(manager.verbose, True)

    def testLogIndent (self):
        "Test log indent and dedent, leading and indentation"
        s3 = '>>>'
        s5 = '     '
        log.leading = s3
        log.indentation = s5
        self.assertEqual(log.leading, s3)
        self.assertEqual(log.indentation, s5)
        log.indent()
        self.assertEqual(log.leading, s3 + s5)
        log.indent()
        self.assertEqual(log.leading, s3 + s5 + s5)
        log.dedent()
        self.assertEqual(log.leading, s3 + s5)
        log.dedent()
        self.assertEqual(log.leading, s3)

    def testLogExcessDedent (self):
        "Test excessive log dedent."
        s3 = '>>>'
        s5 = '     '
        log.leading = s3
        log.indentation = s5
        log.indent()
        log.dedent()
        self.assertEqual(log.leading, s3)
        log.dedent()
        self.assertEqual(log.leading, s3)

class MachineTest(unittest.TestCase):
    "Test the machine module"
    def setUp(self):
        argv = "--skip --log ats.log --quiet"
        manager.restart()
        manager.init(argv)
        log.logging = 0
        unglue()
        unstick()
        untack()

    def testLaunch(self):
        "Try launching a job."
        script=''
        clas='-V'
        if not script:
            t = test(clas = clas, np=1)
        else:
            t=test(script, clas=clas, np=1)
        m = configuration.machine
        self.assertTrue(m.canRun(t) == '')
        self.assertTrue(m.canRunNow(t))
        m.load([t])
        print(t.status)
        count = 0
        while count < 100:
            count+= 1
            result = m.step()
            print(count, result)


class ManagerTest(unittest.TestCase):
    "Test the ATS manager."
    def setUp (self):
        argv = "--skip --log ats.log --quiet"
        manager.restart()
        manager.init(argv)
        log.logging = 0
        unglue()
        unstick()
        untack()

    def testExecutableArgument (self):
        "Test that executable with argument gets split properly."
        import ats.executables
        rest = "-O -v"
        e = sys.executable + " " + rest
        E = ats.executables.Executable(e)
        self.assertEqual(E.path, sys.executable)
        self.assertEqual(E.rest, rest)

    def testManagerCreation (self):
        "Test basic manager creation."
        self.assertEqual(manager.inputFiles, [])
        self.assertEqual(manager.groups, [0])

    def testAtsTest (self):
        "Test creation of a test."
        unstick()
        t = test('nofilenamedthis.py')
        self.assertEqual(len(manager.testlist), 1)
        self.assertTrue(t.status is INVALID)
        t = test(executable=sys.executable) # known to exist
        self.assertEqual(t.status, CREATED)
        self.assertTrue('level' in t.options)
        t = test(sys.executable, executable=1, level=20)
        self.assertEqual(t.options['level'], 20)
        t2 = testif(t, sys.executable, executable=1, level=10)
        self.assertTrue(t2.options['level'] >= t.options['level'])

    def testSticky (self):
        "Test setting of 'sticky/glue' options"        
        glue(permanent=3)
        glue(broomstick=12)
        stick(x = 7, y = 8)
        t = test('foo.py')
        self.assertTrue('permanent' in t.options)
        self.assertTrue('broomstick' in t.options)
        self.assertTrue('x' in t.options)
        self.assertTrue('y' in t.options)
        self.assertTrue('np' in t.options)
        self.assertEqual(t.options['permanent'], 3)
        self.assertEqual(t.options['broomstick'], 12)
        self.assertEqual(t.options['np'], 0)
        self.assertEqual(t.options['x'], 7)
        self.assertEqual(t.options['y'], 8)
        t = test('goo.py', y = 9, z = 6, permanent = 4)
        self.assertEqual(t.options['permanent'], 4)
        self.assertEqual(t.options['x'], 7)
        self.assertEqual(t.options['y'], 9)
        self.assertEqual(t.options['z'], 6)

    def testGetOptions (self):
        "Test of getOptions."
        tack(lovely=True)
        t = test('goo.py', y= 9, z= 6, lovely=False)
        self.assertEqual(t.options['lovely'], False)
        opts = getOptions()
        self.assertEqual(opts['lovely'], True)

    def testSYSTEMfilter (self):
        "Test that the SYSTEM filter works"
        t = test (SYSTEMS=['Hal', 'Ficus2000']) 
        self.assertTrue(t.status is FILTERED)

    def testStickyAdvanced (self):
        "Harder test of setting of 'sticky/glue' options"        
        glue(permanent=3)
        stick(permanent=4)
        t = test('foo.py')
        self.assertTrue('permanent' in t.options)
        self.assertEqual(t.options['permanent'], 4)

        t = test('goo.py', y = 9, z = 6, permanent = 9)
        self.assertTrue('permanent' in t.options)
        self.assertEqual(t.options['permanent'], 9)

        unstick('permanent')
        t = test('goo.py')
        self.assertTrue('permanent' in t.options)
        self.assertEqual(t.options['permanent'], 3)


    def testOptionsEnvironment (self):
        "Test the basic set up of the testing environment."
        t = test('foo.py')
        self.assertTrue('np' in t.options)
        self.assertEqual(t.options['np'], 0)

    def testFilterEnvironment (self):
        "Test the basic filter environment."
        t = test('foo.py')
        fe = manager.filterenv(t)
        for k in testEnvironment:
            self.assertTrue(k in fe)
            self.assertEqual(testEnvironment[k], fe[k])

    def testBasicFiltering (self):
        "Test simple filters."
        t = test('foo.py', np=8, delta=3, level=10)
        self.assertRaises(ats.AtsError, filter, 'np=9')
        list(filter('np==8'))
        f = manager.find_unmatched(t)
        self.assertEqual(f, '')
        d = 'delta==2'
        list(filter(d))
        f = manager.find_unmatched(t)
        self.assertEqual(f, d)
        manager.filter()
        d = 'delta==3'
        f = manager.find_unmatched(t)
        self.assertEqual(f, '')
        manager.filter()
        ltest = 'level <= 8'
        manager.filter(ltest)
        f = manager.find_unmatched(t)
        self.assertEqual(f, ltest)

    def testTimelimitFiltering (self):
        "Test filtering of time limits."
        list(filter())
        t = test('foo.py', timelimit='1h10m')
        d = "timelimit < '1h'"
        list(filter(d))
        f = manager.find_unmatched(t)
        self.assertEqual(f, d)

    def testDefFiltering (self):
        "Test that filterdefs works."
        list(filter())
        filterdefs('delta=4')
        list(filter('delta == 3'))
        t = test('foo.py', np=8, delta=3)
        f = manager.find_unmatched(t)
        self.assertEqual(f, '')
        t = test('foo.py', label='3', np=8)
        f = manager.find_unmatched(t)
        self.assertEqual(f, 'delta == 3')

class TestTimes(unittest.TestCase):
    "Test ats.times module."
    def testBasic(self):
        "Test basic functions."
        self.assertEqual(times.timeSecToSpec(times.timeSpecToSec('1h2m3s')),
                         '1h2m3s')
        self.assertEqual(times.timeSecToSpec(times.timeSpecToSec('1h3s')),
                         '1h0m3s')
        self.assertEqual(times.timeSecToSpec(times.timeSpecToSec('3s')),
                         '0h0m3s')
        self.assertEqual(times.timeSecToSpec(times.timeSpecToSec('2m3s')),
                         '0h2m3s')
        self.assertEqual(times.timeSecToSpec(times.timeSpecToSec(' 1h 2m 3s')),
                         '1h2m3s')
        self.assertEqual(times.timeSecToSpec(times.timeSpecToSec('2')),
                         '0h2m0s')

    def testDuration(self):
        "Test basic functions of Duration class."
        d = times.Duration('1h2m3s')
        self.assertEqual(d.value, times.timeSpecToSec('1h2m3s'))
        self.assertEqual(str(d), '1h2m3s')
        self.assertEqual(repr(d), "Duration('1h2m3s')")

    def testDurationCompares(self):
        "Test comparison operations on Durations."
        d = times.Duration('70s')
        c = times.Duration('1m15s')
        self.assertTrue(d < c)
        self.assertTrue(d < 80)
        self.assertTrue(d == d)
        self.assertTrue(d != c)
        self.assertTrue(d <= c)
        self.assertTrue(c >= d)
        self.assertFalse(d != d)
        self.assertTrue(c < '1h')

if __name__ == "__main__":
    unittest.main()
