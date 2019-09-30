#ATS:test(SELF, "-v")
import unittest
import test
import batchtest

loader = unittest.TestLoader()
runner = unittest.TextTestRunner()
suite  = unittest.TestSuite()

modules = [test, batchtest]
for module in modules:
    suite.addTests(loader.loadTestsFromModule(module)._tests)

runner.run(suite)
