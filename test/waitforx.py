import sys

color = sys.argv[1]
action = sys.argv[2]
print("#ATS:waitforx input is", color, action)
if action == 'write':
    f = open('colorout', 'w')
    print(color, file=f)
    f.close()
if action == 'read':
    f = open('colorout', 'r')
    line = f.readline()
    colorf = line.strip()
    if color != colorf:
        raise ValueError("%s is not %s" % (colorf, color))
