#ATS:t1= test(SELF,"restartFrom= 0",np=1,label='restart-0')
#ATS:testif(t1, SELF,"restartFrom=10",np=1,label='restart-1')
#ATS:testif(t1, SELF,"restartFrom=20",np=1,label='restart-2')
print "iftest_2tests passed"
