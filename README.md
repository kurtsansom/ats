License information
===================

See the file "LICENSE-COPYRIGHT.txt" for licensing information. This is an
open source project.

Build instructions
==================

-----------------------------------------------------
Site installation of ATS
-----------------------------------------------------

If you have a Python distribution you would like to install
the ATS into as a site package, use:

$> python setup.py install

After installation, atsb is the Unix executable. On Windows, you have to 
make a shortcut that executes python atsb ... <rest of arguments>.


-----------------------------------------------------
Local installation of ATS
-----------------------------------------------------

If you do not wish to install ATS as a site package, use a local
installation of python to execute the setup.py install script.
Check the README included with your python for the most up to
date instructions on installing python.

-------------
Documentation
-------------

Documentation, including how to port atsb to a new machine, is in the docs 
directory. See also Examples/Android.

To install the documentation builder Sphinx into your python, use 
easy_install -U Sphinx.
