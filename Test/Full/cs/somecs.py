#ATS:test(SELF, '-v')
import unittest, sys
class FudgeCake (unittest.TestCase):
    def testOne (self):
        "Test the cake."
        self.failIf(0)

if __name__ == "__main__":
    unittest.main()
