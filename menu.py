######################
###    DEV          ##
###    menu.py      ##
######################
nuke.tprint( "*------------------------------")
nuke.tprint( "* This is the dev config menu.py")
nuke.tprint ("* Running from " + os.path.realpath(__file__))
nuke.tprint( "*------------------------------")

try:
    # Deadline
    import scripts.deadline.hsNukeToDeadline as hsNukeToDeadlineDev

    jobToolbar = toolbar.addMenu("theboat/"+job)
    jobToolbar.addCommand("hsNukeToDeadline...", hsNukeToDeadlineDev.SubmitToDeadline, icon= theBoatConfigFolder+'/icons/deadlineIcon.png')
except:
    print "Cant find path " + pluginPath
    pass
