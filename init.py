#####################
##  dev config   ##
##    init.py      ##
#####################
import os

#job = 'gilda'
#
#nuke.tprint ("Running " +job+ " config from " + os.path.realpath(__file__))
#
#theBoatFolder = globals().get('theBoatFolder')
#jobFolder = theBoatFolder +'/'+ job
#
#
#nuke.pluginAddPath(jobFolder+'/_config/gizmos')
#nuke.pluginAddPath(jobFolder+'/_config/scripts')
#
#nuke.tprint ("Finished running " +job+ " config from " + os.path.realpath(__file__))

try:
    rootfolder = os.environ.get("theBoatFolder")
    job = os.environ.get("JOB")

    jobFolder = os.path.join(rootfolder, job)

    nuke.tprint ("Running " +job+ " config from " + os.path.realpath(__file__))

    nuke.pluginAddPath(jobFolder+'/_config/scripts')

    nuke.tprint ("Finished running " +job+ " config from " + os.path.realpath(__file__))
except NameError as e:
    print "Error:", e
except:
#    nuke.tprint( "Error in dev init.py\n" + sys.exc_info()[0] )
    print "Error:", sys.exc_info()[0]
    pass
