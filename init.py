#!/usr/bin/env python
#####################
## the boat config ##
##    init.py      ##
#####################

import nuke, os, sys, re
from GizmoPathManager import GizmoPathManager 

rootFolder = os.environ.get("ROOTFOLDER")
rootFolderConfig = os.path.join(rootFolder, "_config")

nuke.tprint( "*------------------------" )
nuke.tprint( "* This is theboat init.py" )
nuke.tprint( "*", os.path.realpath(__file__) )
nuke.tprint( "*------------------------" )
nuke.tprint( "rootFolder:", rootFolder )
nuke.tprint( "rootFolderConfig:", rootFolderConfig )

job = 'jobNotSet'
shot = 'shotNotSet'

if os.environ.get("JOB"):
    job = os.environ.get("JOB")

if os.environ.get("SHOT"):
    shot = os.environ.get("SHOT")

jobConfig = os.path.join(rootFolder ,  job  , '_config')

if os.path.exists(jobConfig):
    print ('    Adding path '+jobConfig)
    nuke.pluginAddPath(jobConfig)


#nuke.tprint( "Plugins: import pasteToSelected" )
#import pasteToSelected

newFormat = "2048 1152 1.0 2k 1.77"
nuke.tprint( "nuke addFormat %s" % newFormat )
nuke.addFormat(newFormat)

# ViewerProcess LUTs
newLut = "AlexaV3Rec709"
nuke.tprint( "Register new LUT %s" % newLut )
nuke.ViewerProcess.register(newLut, nuke.Node, (newLut, ""))

newLut = "AlexaLogC"
nuke.tprint( "Register new LUT %s" % newLut )
nuke.ViewerProcess.register(newLut, nuke.Node, (newLut, ""))

newLut = "RLF2RG4"
nuke.tprint( "Register new LUT %s" % newLut )
nuke.ViewerProcess.register(newLut, nuke.Node, (newLut, ""))

# If Write dir does not exist, create it
def createWriteDir():
    file = nuke.filename(nuke.thisNode())
    dir = os.path.dirname( file )
    osdir = nuke.callbacks.filenameFilter( dir )
    try:
        os.makedirs( osdir )
        return
    except:
        return

# Activate the createWriteDir function
nuke.addBeforeRender( createWriteDir )
nuke.tprint ('Activated createWriteDir')

nuke.tprint("Loading LUMA PICTURES GIZMO LOADER")
# LUMA PICTURES GIZMO LOADER
if __name__ == '__main__':

    CUSTOM_GIZMO_LOCATION = rootFolderConfig
    CUSTOM_GIZMO_LOCATION = os.path.expandvars(CUSTOM_GIZMO_LOCATION.strip()).rstrip('/\\')
    if CUSTOM_GIZMO_LOCATION and os.path.isdir(CUSTOM_GIZMO_LOCATION):
        gizManager = GizmoPathManager(searchPaths=[CUSTOM_GIZMO_LOCATION])
    else:
        gizManager = GizmoPathManager()
    gizManager.addGizmoPaths()
    if not nuke.GUI:
        del gizManager
