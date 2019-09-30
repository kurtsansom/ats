import sys, os, shutil, glob
from distutils.core import setup
exec(compile(open(os.path.join('lib', 'version.py'),"rb").read(),
                  os.path.join('lib', 'version.py'), 'exec'))
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
    print ("ats module cannot be imported; check Python path.", file=sys.stderr)
    print (sys.path, file=sys.stderr)
    raise SystemExit(1)

result = ats.manager.main()
sys.exit(result)
""" % sys.exec_prefix
print(driverscript, file=f)
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
       package_dir = {'ats': 'lib'},
       scripts = [codename],
       data_files = [('atsMachines', glob.glob('machines/*.py')), ('atsExtras', glob.glob('extras/*.py'))]

      )

