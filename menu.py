#####################
## the boat config ##
##    menu.py      ##
#####################

import nuke, os, sys, re
# get the python modules
nuke.pluginAddPath("./python")

nuke.tprint( "*------------------------" )
nuke.tprint( "* This is theboat menu.py" )
nuke.tprint( "*", os.path.realpath(__file__) )
nuke.tprint( "*------------------------" )

job = 'jobNotSet'
shot = 'shotNotSet'
rootFolder = 'rootFolderNotSet'

if os.environ.get("ROOTFOLDER"):
    rootFolder = os.environ.get("ROOTFOLDER")

if os.environ.get("JOB"):
    job = os.environ.get("JOB")

if os.environ.get("SHOT"):
    shot = os.environ.get("SHOT")


rootFolderConfig = os.path.join(rootFolder, "_config")

nuke.tprint( "rootFolder: {}\njob: {}\nshot: {}".format(rootFolder,job,shot) )
shotPath = os.path.join(rootFolder, job, shot)
nuke.addFavoriteDir(shot, shotPath)

# THE BOAT TOOLBAR
toolbar = nuke.toolbar("Nodes") # Access the main toolbar
theboatNodes = toolbar.addMenu("theboat", icon= rootFolderConfig+'/icons/boatIcon.png')
generalNodes = theboatNodes.addMenu("theboat", icon= rootFolderConfig+'/icons/hoveringSombreroIcon.png')

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
import DeadlineNukeClient
theboatNodes.addCommand("Render on the farm...", DeadlineNukeClient.main, "")


#
# check if the opened script name is
# is similar to the environment
#
def checkScriptEnvironment():

    if os.environ.get("LINK") not in nuke.Root().name():
        nuke.message("You are opening a nuke script without the correct environment variables.")

nuke.addOnScriptLoad(checkScriptEnvironment)
from HSNukeMonitor import HSNukeMonitor

def addHSPanel():
    global hsPanel
    hsPanel = HSNukeMonitor()
    return hsPanel.addToPane()

paneMenu = nuke.menu('Pane')
paneMenu.addCommand('HoveringSombreroMonitor', addHSPanel)
nukescripts.registerPanel('com.hoveringsombrero.monitor', addHSPanel)
