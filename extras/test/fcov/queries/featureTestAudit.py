import os, sys
from sets import Set
import gadfly

args = sys.argv
if len(args) != 2:
   print("usage: ", args[0], " [database]")
   sys.exit(1)

try:
   connection = gadfly.gadfly(args[1])

except IOError as e:
   print("ERROR: %s Database not found.\n"%e)
   sys.exit(1)

cursor = connection.cursor()
sql = "SELECT name, status, np \
       FROM tests "
cursor.execute(sql)
results_tests = cursor.fetchall()
print("Tests:")
print("---")
for row in results_tests:
   name = row[0]
   status = row[1]
   np = row[2]
     
   print("%s np=%s %s" % (name, np, status))      
   sql = "SELECT feature \
          FROM loggedFeatures \
          WHERE test = '%s'" % (name)
   cursor.execute(sql)
   features = cursor.fetchall()
   for entry in features:
      print("   %s, "  % (entry))
   print("")
print("")

sql = "SELECT DISTINCT feature, mesh FROM loggedFeatures"
cursor.execute(sql)
results_features= cursor.fetchall()
print("Features:")
print("---")
for row in results_features:
   feature_name = row[0]
   print("%s" % (feature_name), end=' ')
   mesh = row[1]
   #If feature has a mesh specified, append it to name
   if (mesh != ''):
      print("<%s>" % (mesh))
   else:
      print()

   sql = "SELECT test \
          FROM loggedFeatures \
          WHERE feature = '%s'" % (feature_name)
   cursor.execute(sql)
   results_test_names = cursor.fetchall()
   for test in results_test_names:
      sql = "SELECT name, status\
             FROM tests \
             WHERE name = '%s'" % (test)
      cursor.execute(sql)
      test = cursor.fetchall()
      print("   %s %s" % (test[0][0], test[0][1]))
   print("")
connection.close()
