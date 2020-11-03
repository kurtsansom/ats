# Automated Testing Suite (ATS)

The Automated Testing System (ATS) is an open-source, Python-based tool for automating the running of tests of an
application. ATS can test any program that can signal success or failure via its exit status

## License information

See the file "LICENSE-COPYRIGHT.txt" for licensing information. This is an
open source project.

## Build instructions

### Site installation of ATS

If you have a Python distribution you would like to install
the ATS into as a site package, use:

```sh
git clone https://github.com/kurtsansom/ats.git
cd ats
python setup.py install
```

After installation, atsb is the Unix executable. On Windows, you have to
make a shortcut that executes python atsb ... <rest of arguments>.

### Local installation of ATS

If you do not wish to install ATS as a site package, use a local
installation of python to execute the setup.py install script.
Check the README included with your python for the most up to
date instructions on installing python.

### Documentation

Documentation, including how to port atsb to a new machine, is in the docs 
directory. See also Examples/Android.

To install the documentation builder Sphinx into your python, use 

```sh
pip install -U sphinx
```

or reference the sphinx documentation

[Sphinx Installation Instructions](https://www.sphinx-doc.org/en/master/usage/installation.html)

e.g.

```sh
cd ./ats/docs
make html
```

Installation of latex is required to build the pdf. e.g.

```sh
make latexpdf
```
