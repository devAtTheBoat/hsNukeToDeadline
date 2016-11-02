#####################
## the boat config ##
##    menu.py      ##
#####################

import nuke, os, sys, re

nuke.tprint( "*------------------------" )
nuke.tprint( "* This is theboat menu.py" )
nuke.tprint( "*", os.path.realpath(__file__) )
nuke.tprint( "*------------------------" )

job = 'jobNotSet'
shot = 'shotNotSet'
theBoatFolder = 'theBoatFolderNotSet'

if os.environ.get("THEBOATFOLDER"):
    theBoatFolder = os.environ.get("THEBOATFOLDER")

if os.environ.get("JOB"):
    job = os.environ.get("JOB")

if os.environ.get("SHOT"):
    shot = os.environ.get("SHOT")

nuke.tprint( "theBoatFolder: {}\njob: {}\nshot: {}".format(theBoatFolder,job,shot) )
shotPath = os.path.join(theBoatFolder, job, shot)
nuke.addFavoriteDir(shot, shotPath)

# THE BOAT TOOLBAR
toolbar = nuke.toolbar("Nodes") # Access the main toolbar
theboatNodes = toolbar.addMenu("theboat", icon= theBoatConfigFolder+'/icons/boatIcon.png')
generalNodes = theboatNodes.addMenu("theboat", icon= theBoatConfigFolder+'/icons/hoveringSombreroIcon.png')

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

# FrameHolds default to current frame
nuke.menu('Nodes').addCommand( "Time/FrameHold", "nuke.createNode('FrameHold')['first_frame'].setValue( nuke.frame() )", icon='FrameHold.png')


# Hovering Sombrero Nuke to Deadline
nuke.pluginAddPath('scripts/deadline')
import hsNukeToDeadline as _hsNukeToDeadline
theboatNodes.addCommand("Render on the farm...", _hsNukeToDeadline.SubmitToDeadline, icon= theBoatConfigFolder+'/icons/deadlineIcon.png')

#nuke.tprint ("Finished running "+job+" config from " + os.path.realpath(__file__)) #for job _config
nuke.tprint ("Finished running general config from " + os.path.realpath(__file__))
