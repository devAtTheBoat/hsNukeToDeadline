#####################
## the boat config ##
##    menu.py      ##
#####################


import nuke, os, sys, re

nuke.tprint ("Running " +job+ " config from " + os.path.realpath(__file__))


job = 'jobNotSet'
shot = 'shotNotSet'
theBoatFolder = 'theBoatFolderNotSet'

if not os.environ.get("THEBOATFOLDER")==None:
    theBoatFolder = os.environ.get("THEBOATFOLDER")

if not os.environ.get("JOB")==None:
    job = os.environ.get("JOB")

if not os.environ.get("SHOT")==None:
    shot = os.environ.get("SHOT")


shotPath = theBoatFolder+'/'+job+'/'+shot
nuke.addFavoriteDir(shot, shotPath)


# THE BOAT TOOLBAR
toolbar = nuke.toolbar("Nodes") # Access the main toolbar
theboatNodes = toolbar.addMenu("theboat", icon= theBoatConfigFolder+'/icons/boatIcon.png')
generalNodes = theboatNodes.addMenu("theboat", icon= theBoatConfigFolder+'/icons/hoveringSombreroIcon.png')

# FrameHolds default to current frame
nuke.menu('Nodes').addCommand( "Time/FrameHold", "nuke.createNode('FrameHold')['first_frame'].setValue( nuke.frame() )", icon='FrameHold.png')

#LUMA'S GIZMO PATH MANAGER
if __name__ == '__main__':
    gizManager = globals().get('gizManager', None)
    if gizManager is None:
        print 'Problem finding GizmoPathManager - check that init.py was setup correctly'
    else:

        gizManager.addGizmoMenuItems(rootMenu=generalNodes)
        del gizManager

# PASTE TO SELECTED
menuBar = nuke.menu("Nuke")
menuBar.addCommand('Edit/Paste To Selected', 'pasteToSelected.pasteToSelected()', index=10)

# 3DE LENS DISTORTION NODES
nuke.menu("Nodes").addCommand("theboat/theboat/Lens Distortion/LD_3DE4_Anamorphic_Standard_Degree_4", "nuke.createNode('LD_3DE4_Anamorphic_Standard_Degree_4')")
nuke.menu("Nodes").addCommand("theboat/theboat/Lens Distortion/LD_3DE4_Anamorphic_Degree_6", "nuke.createNode('LD_3DE4_Anamorphic_Degree_6')")
nuke.menu("Nodes").addCommand("theboat/theboat/Lens Distortion/LD_3DE4_Radial_Standard_Degree_4", "nuke.createNode('LD_3DE4_Radial_Standard_Degree_4')")
nuke.menu("Nodes").addCommand("theboat/theboat/Lens Distortion/LD_3DE4_Radial_Fisheye_Degree_8", "nuke.createNode('LD_3DE4_Radial_Fisheye_Degree_8')")
nuke.menu("Nodes").addCommand("theboat/theboat/Lens Distortion/LD_3DE_Classic_LD_Model", "nuke.createNode('LD_3DE_Classic_LD_Model')")

# KNOB DEFAULTS
# RotoPaint
nuke.knobDefault('RotoPaint.cliptype','bbox')
nuke.knobDefault("RotoPaint.toolbox", "brush {{brush ltt 0} {clone ltt 0}}")
# Write
nuke.knobDefault("Write.exr.channels","rgba")
# Exposure
nuke.knobDefault("EXPTool.mode", "0")
# Format
nuke.knobDefault("Root.format", "2k 1.77")

# Deadline
# Instead of using the Deadline Submit Script
# Use the one in /scripts/deadline
nuke.pluginAddPath('scripts/deadline')
import hsNukeToDeadline
theboatNodes.addCommand("hsNukeToDeadline...", hsNukeToDeadline.SubmitToDeadline, icon= theBoatConfigFolder+'/icons/deadlineIcon.png')


#    import DeadlineNukeClient
#    menubar = nuke.menu("Nuke")
#    tbmenu = menubar.addMenu("&Thinkbox")
#    tbmenu.addCommand("Submit Nuke To Deadline", DeadlineNukeClient.main, "")
#    try:
#        if nuke.env[ 'studio' ]:
#            import DeadlineNukeFrameServerClient
#            tbmenu.addCommand("Reserve Frame Server Slaves", DeadlineNukeFrameServerClient.main, "")
#    except:
#        pass
#    try:
#        import DeadlineNukeVrayStandaloneClient
#        tbmenu.addCommand("Submit VRay Standalone to Deadline", DeadlineNukeVrayStandaloneClient.main, "")
#    except:
#        pass


nuke.tprint ("Finished running " +job+ " config from " + os.path.realpath(__file__))

