#!/usr/bin/env python
""" This example shows how to add your own option to ATS with a custom driver.
    Note that the first argument to main is blank; this will result in the command-line
    arguments being used.

    By running 
        python addExample.py --postprocess otherarguments 
    or making addExample.py executable and running 
       ./addExample.py --postprocess otherarguments
    an extra postprocessing list of the tests will be made.

   Also running with --help and --info will show the new option.
"""
from ats import manager

def myposter(manager):
    for t in manager.testlist:
        print t

def addopt (parser):
    parser.add_option('--postprocess', action='store_true', dest = 'postprocess',
         default = False,
         help='Use --postprocess to do postprocessing.')

def examiner (options):
    if options.postprocess:
        manager.onExit(myposter)

manager.main('', addopt, examiner)

