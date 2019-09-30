import os, sys
from sets import Set
import gadfly

args = sys.argv
if len(args) != 2:
   print "usage: ", args[0], " [database]"
   sys.exit(1)

try:
   connection = gadfly.gadfly(args[1])
except IOError:
   print "Could not find database '%s'" % args[1]
   sys.exit(1)

cursor = connection.cursor()

tiers=['a','b','c','d','e']

for tier in tiers:
    # Get all feature with tier 'tier'
    sql = "SELECT DISTINCT name, mesh FROM features WHERE tier = '%s'" % tier
    #Gadfly doesn't support count(distinct name, mesh), so need to have python do the count
    cursor.execute(sql)
    results= cursor.fetchall()
    if results == None:
       numFeatInTier = 0
    else:
       numFeatInTier = len(results)

    sql = "SELECT features.name, features.mesh, features.tier \
           FROM features, loggedFeatures, tests \
           WHERE features.name = loggedFeatures.feature \
           AND features.mesh = loggedFeatures.mesh \
           AND tests.name = loggedFeatures.test \
           AND features.tier = '%s'" % (tier)
    cursor.execute(sql)

    # Get logged features with tier 'tier'
    sql = "SELECT DISTINCT features.name, features.mesh \
           FROM features, loggedFeatures, tests \
           WHERE features.name = loggedFeatures.feature \
           AND features.mesh = loggedFeatures.mesh \
           AND tests.name = loggedFeatures.test \
           AND features.tier = '%s'" % (tier)
    cursor.execute(sql)
    #Again, use python to remove duplicate entries
    results = cursor.fetchall()
    if results == None:
       numLoggedInTier = 0
    else:
       numLoggedInTier = len(results)

    print "   Tier %s: %u/%u features covered." % (tier, numLoggedInTier, numFeatInTier)

connection.close()
