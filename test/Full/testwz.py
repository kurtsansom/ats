#ATS:stick(eos='ANALYTIC')
#ATS:log('Note: this test fails; it is for testing ATS.')
#ATS:~test(SELF, label='kamikaze -- should fail', np=2)
import sys
print("Aieeeee....I'm dying.")
raise SystemExit(1)

