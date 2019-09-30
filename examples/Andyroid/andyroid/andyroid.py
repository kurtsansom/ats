#!/usr/bin/env python
import os, sys
from optparse import OptionParser

def addOptions(parser):
    parser.add_option("-i", "--input", dest="inputFile", default = '',
      help="input file name; if not given, use first positional argument")
    parser.add_option("-o", "--output", dest="outputFile", 
      help="output file name")
    parser.add_option("--delta", action='store_true', dest="addDelta",
       default=False, help="Add delta?")
    parser.add_option("--alpha", action='store', dest="alpha",
       default=1.0, help="A vital parameter")

parser=OptionParser()
addOptions(parser)

options, args = parser.parse_args(sys.argv[1:])

inputFile = options.inputFile
if not inputFile:
    if args: 
        inputFile = args[0]
    else:
        raise ValueError("No input file.")

print("Input file:", inputFile)
f = open(inputFile, 'r')

outputFile = options.outputFile
if not outputFile:
    outputFile = inputFile + ".out"
    outputFile = os.path.basename(outputFile)
print("Output file", outputFile)
g = open(outputFile, 'w')

delta = 0.0
if options.addDelta: 
    delta = 0.1

alpha = float(options.alpha)

for line in f:
    line =line.strip()
    if not line: continue
    if line.startswith("#"): continue
    a = float(line)
    if a > 10.0:
        raise ValueError("Input value %f too large." % a)
    print(a, alpha*a**2 + delta, file=g)
f.close()
g.close()


