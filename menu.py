######################
###    DEV          ##
###    menu.py      ##
######################

import sys

nuke.tprint( "*------------------------------")
nuke.tprint( "* This is the dev config menu.py")
nuke.tprint ("* Running from " + os.path.realpath(__file__))
nuke.tprint( "*------------------------------")

try:
    # Deadline
    import scripts.deadline.hsNukeToDeadline as hsNukeToDeadlineDev

    job = os.environ.get("JOB")

    jobToolbar = toolbar.addMenu("theboat/"+job)
    jobToolbar.addCommand("hsNukeToDeadline...", hsNukeToDeadlineDev.SubmitToDeadline, icon=rootFolderConfig+'/icons/deadlineIcon.png')
except:
    print "Error:", sys.exc_info()[0]
    pass
