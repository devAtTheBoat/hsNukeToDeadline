#####################
##  dev config   ##
##    init.py      ##
#####################
import os
nuke.tprint( "*------------------------------")
nuke.tprint( "* This is the dev config init.py")
nuke.tprint ("* Running from " + os.path.realpath(__file__))
nuke.tprint( "*------------------------------")

try:
    # prints all the environment
#    print "\n".join([ "{}: {}".format(key, value) for key, value in os.environ.iteritems() ])

    rootFolder = os.environ.get("ROOTFOLDER")
    job = os.environ.get("JOB")
    jobFolder = os.path.join(rootFolder, job)

    nuke.tprint ("Adding {} config scripts".format(job))

    jobConfigScripts = os.path.join( jobFolder , '_config' , 'scripts' )

    nuke.pluginAddPath( jobConfigScripts )

except NameError as e:
    print "Error:", e
except:
    print "Error:", sys.exc_info()[0]
    pass
