import sys, os, shutil, glob
from distutils.core import setup
execfile(os.path.join('Lib', 'version.py'))
codename = 'ats'
#
# write atsb script
#
f = open(codename, 'w')
driverscript = """#!%s/bin/python
import sys

try:
    import ats
except ImportError:
    print >>sys.stderr, "ats module cannot be imported; check Python path."
    print >>sys.stderr, sys.path
    raise SystemExit, 1

result = ats.manager.main()
sys.exit(result)
""" % sys.exec_prefix
print >>f, driverscript
f.close()
#os.chmod(codename, 7*64 + 7*8 + 5)
if os.path.exists('build'):
    shutil.rmtree('build')

setup (name = "ats",
       author="Paul F. Dubois",
       author_email="pfdubois@gmail.com",
       url="http://pfdubois.com",
       version=version,
       description = "Automated Testing System",
       packages = ['ats'],
       package_dir = {'ats': 'Lib'},
       scripts = [codename],
       data_files = [('atsMachines', glob.glob('Machines/*.py')), ('atsExtras', glob.glob('Extras/*.py'))]

      )

