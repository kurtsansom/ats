# test1.py
stick(physics=['Lagrangian','ALE'])
test('testme.py', np=4)
test('hydro/ale/testale.py','parm=2.3', label='parameters')
test('hydro/ale/testale.py', label='no parameters')
test('hydro/flag/testflag.py' 'parm=2.3', label='parameters')
test('hydro/flag/testflag.py', label='no parameters')
unstick('physics')
source('testwz.py')
source('badfile')

