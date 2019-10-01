import sys, os
inputFile = sys.argv[1]
f = open(inputFile, 'r')
count = 0
for line in f:
    count += 1
    print(line, end=' ')
f.close()
print("%d lines in file." % count)

