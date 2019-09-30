
from ats import manager, log

def f (m):
    log('End of the run we started way back at ', m.started)

def g(r, m):
    r['myFavoriteAuthor'] = 'Dickens'
    r['numberOfTests'] = len(m.testlist)

manager.init()
manager.onExit(f)
manager.onSave(g)

manager.filter('level < 20')
manager.test(clas='-c 3', level=12)
manager.test(clas='-c 4', level=22)
manager.main()

