

o: How To Build ATS on All Platforms on LC machines:

1. cd to /usr/dnta/kull/developers/tools

2. if you want a new ats version, create a new directory, say ats-1.7.
   if you want to build bug-fixed ats only, then cd to current existing
   directory and go to step 4.

3. cd to the new directory, create .p4settings with say, P4CLIENT=ats-1.7
   and do a 'p4 client -t ats-1.6' for example. Then do a 'p4 sync ...' to
   populate sources.

4. for each platform (AIX and Linux), do one of the following:
      gmake do_all    #to build a new version in a newly created directory
      gmake do_ats    #to build a bug-fixed ats only.

5. DONE for bug-fixed ats only case.

   For new ats version in the newly created directory, do the following.
   for SYS_TYPE in [aix_5_ll, chaos_3_x86_elan3]
      cd to /usr/dnta/kull/bin/$SYS_TYPE
      do necessary symbolic link for atsold, ats and atsnew

6. do a cd to the directory of the previous version.
   delete .p4settings and do a 'p4 client -d ats-1.6' for example to 
   completely severe the mapping between repository and the client of 
   the previous version. 
   do the following so that other members can modify or delete 
   completely from the tools directory if necessary or obsolete.
   [I am not too sure of we should do this... as anyone can tamper with]

   chmod -R +wX *
   chmod -R g+wX *

   also make sure that the directory of the previous version has write 
   privilege for the group so that this directory can be deleted.

NOTE:
On the local machine different from LC machines, you will need to set
SYS_TYPE environment variable to "local"
