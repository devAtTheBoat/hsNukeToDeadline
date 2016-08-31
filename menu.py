######################
###    DEV          ##
###    menu.py      ##
######################
#
#import nuke, os, sys, re
#job = os.environ.get("JOB")
#theBoatFolder = globals().get('theBoatFolder')
#
#theBoatConfigFolder = os.path.join(theBoatFolder , '_config')
#jobFolder = os.path.join(theBoatFolder , job)
#
#pluginPath = os.path.join(theBoatFolder, jobFolder, '_config', 'scripts')
#
#
#try:
#    # Deadline
#    nuke.pluginAddPath(pluginPath)
#    import hsNukeToDeadlineDev
#
#    jobToolbar = toolbar.addMenu("theboat/"+job)
#    jobToolbar.addCommand("hsNukeToDeadline...", hsNukeToDeadlineDev.SubmitToDeadline, icon= theBoatConfigFolder+'/icons/deadlineIcon.png')
#except:
#    print "Cant find path " + pluginPath
#    pass
