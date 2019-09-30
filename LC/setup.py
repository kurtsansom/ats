import sys, os, shutil, glob
from distutils.core import setup
if os.path.exists('build'):
    shutil.rmtree('build')

here = os.getcwd()
machs = glob.glob(os.path.join(here, 'Machines', '*.py'))
setup (name = "atsLC",
       author="Paul F. Dubois",
       author_email="pfdubois@gmail.com",
       url="http://pfdubois.com",
       version='1.0',
       description = "Automated Testing System LC addons",
       data_files = [('atsMachines', machs)],
       scripts = ['atsWrap'],
      )
