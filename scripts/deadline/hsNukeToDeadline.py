#
#
# HOVERIN SOMBRERO 
# NUKE TO DEADLINE SUBMITTER
#
# We are going to use a custom submitter because the deadline one it's too big and dificult to mantain
#

import os
import subprocess
import threading
import locale 
import re

import nuke
import nukescripts

# THE DIALOG
class HS_DeadlineDialog( nukescripts.PythonPanel ):
    def __init__( self, maximumPriority, pools, secondaryPools, groups ):
        nukescripts.PythonPanel.__init__( self, "Submit To Deadline", "com.vfxboat.software.deadlinedialog" )

        width = 620
        height = 705
        
        self.setMinimumSize( width, height ) 

        self.jobTab = nuke.Tab_Knob( "Deadline_JobOptionsTab", "Job Options" )
        self.addKnob( self.jobTab )
        
        ##########################################################################################
        ## Job Description
        ##########################################################################################
        
        # Job Name
        # Get the jobname from the filename
        job = os.path.basename( nuke.Root().name() )
        self.jobName = nuke.String_Knob( "Deadline_JobName", "Job Name" )
        self.addKnob( self.jobName )
        self.jobName.setTooltip( "The name of your job. This is optional, and if left blank, it will default to 'Untitled'." )
        self.jobName.setValue( job )
        
        ##########################################################################################
        ## Job Scheduling
        ##########################################################################################
        
        # Pool
        self.pool = nuke.Enumeration_Knob( "Deadline_Pool", "Pool", pools )
        self.addKnob( self.pool )
        self.pool.setTooltip( "The pool that your job will be submitted to." )
        self.pool.setValue( "none" )
        
        ##########################################################################################
        ## Nuke Options
        ##########################################################################################
        
        self.draftSeparator1 = nuke.Text_Knob( "Deadline_DraftSeparator1", "" )
        self.addKnob( self.draftSeparator1 )
        
        # Frame List
        self.frameListMode = nuke.Enumeration_Knob( "Deadline_FrameListMode", "Frame List", ("Global", "Input", "Custom") )
        self.addKnob( self.frameListMode )
        self.frameListMode.setTooltip( "Select the Global, Input, or Custom frame list mode." )
        self.frameListMode.setValue( "Global" )
        
        self.frameList = nuke.String_Knob( "Deadline_FrameList", "" )
        self.frameList.clearFlag(nuke.STARTLINE)
        self.addKnob( self.frameList )
        self.frameList.setTooltip( "If Custom frame list mode is selected, this is the list of frames to render." )
        self.frameList.setValue( ("%s-%s" % (nuke.Root().firstFrame() , nuke.Root().lastFrame() ) ) )
        
        # Chunk Size
        self.chunkSize = nuke.Int_Knob( "Deadline_ChunkSize", "Frames Per Task" )
        self.addKnob( self.chunkSize )
        self.chunkSize.setTooltip( "This is the number of frames that will be rendered at a time for each job task." )
        self.chunkSize.setValue( 10 )
        
        # Only Submit Selected Nodes
        self.selectedOnly = nuke.Boolean_Knob( "Deadline_SelectedOnly", "Selected Nodes Only" )
        self.selectedOnly.setFlag(nuke.STARTLINE)
        self.addKnob( self.selectedOnly )
        self.selectedOnly.setTooltip( "If enabled, only the selected Write nodes will be rendered." )
        self.selectedOnly.setValue( True )
        
        ##########################################################################################
        ## Shotgun Options
        ##########################################################################################
        
        self.draftSeparator1 = nuke.Text_Knob( "Deadline_DraftSeparator1", "" )
        self.addKnob( self.draftSeparator1 )
        
        # SG User Name
        # Get the jobname from the filename
        self.sgUserName = nuke.String_Knob( "Deadline_sgUserName", "User" )
        self.addKnob( self.sgUserName )
        self.sgUserName.setTooltip( "The name of your job. This is optional, and if left blank, it will default to 'Untitled'." )
        self.sgUserName.setValue( '' )
        
        self.testButton = nuke.PyScript_Knob( "Deadline_TestButton", "Test" )
        self.addKnob( self.testButton )
        self.testButton.setTooltip( "Tests the SG connection." )
        
        # SG Task
        # Get the jobname from the os.environ
        sgTask = os.environ["TASK"]
        self.sgTaskCombo = nuke.Enumeration_Knob( "Deadline_sgTasks", "Tasks", [sgTask, "task 2", "task 3"] )
        self.addKnob( self.sgTaskCombo )
        self.sgTaskCombo.setTooltip( "Select your task" )
        
        # SG New Description
        self.sgDescription = nuke.String_Knob( "Deadline_sgDescription", "Description" )
        self.addKnob( self.sgDescription )
        self.sgDescription.setTooltip( "The description of the new Version that will be created." )
        self.sgDescription.setValue( "" )
        
        ##########################################################################################
        ## Draft Options
        ##########################################################################################
        
        self.draftSeparator1 = nuke.Text_Knob( "Deadline_DraftSeparator1", "" )
        self.addKnob( self.draftSeparator1 )
        
        # It should be by default
        # createNewVersion
        # submitDraftJob
        # uploadToSG
        # useQuickDraft ? (Should we? or should we create our own templates?)
        
#        self.createNewVersion = nuke.Boolean_Knob( "Deadline_CreateNewVersion", "Create New Version" )
#        self.addKnob( self.createNewVersion )
#        self.createNewVersion.setEnabled( False )
#        self.createNewVersion.setTooltip( "If enabled, Deadline will connect to a new Version for this job." )
#        self.createNewVersion.setValue( False )

#        self.submitDraftJob = nuke.Boolean_Knob( "Deadline_SubmitDraftJob", "Submit Dependent Draft Job" )
#        self.addKnob( self.submitDraftJob )
#        self.submitDraftJob.setValue( False )

#        self.uploadToShotgun = nuke.Boolean_Knob( "Deadline_UploadToShotgun", "Upload to Shotgun" )
#        self.addKnob( self.uploadToShotgun )
#        self.uploadToShotgun.setEnabled( False )
#        self.uploadToShotgun.setTooltip( "If enabled, the Draft results will be uploaded to Shotgun when it is complete." )
#        self.uploadToShotgun.setValue( True )

#        self.useQuickDraft = nuke.Boolean_Knob("Deadline_DraftQuick", "Use Quick Draft")
#        self.addKnob(self.useQuickDraft)
#        self.useQuickDraft.setTooltip( "Whether to use controls to build a quick template options or custom ones." )
#        self.useQuickDraft.setEnabled(False)
        
        # WE SHOULD CHANGE THIS TO DRAFT QUALITY
        self.draftTemplateCombo = nuke.Enumeration_Knob( "Deadline_draftTemplate", "Draft Quality", ["Quality 1", "Quality 2", "Quality 3"] )
        self.addKnob( self.draftTemplateCombo )
        self.draftTemplateCombo.setTooltip( "Select the draft quality" )
        
    def ShowDialog( self ):
        return nukescripts.PythonPanel.showModalDialog( self )
    
    
    def knobChanged( self, knob ): 
        if knob == self.frameList:
            self.frameListMode.setValue( "Custom" )
        
        if knob == self.frameListMode:
            # In Custom mode, don't change anything
            if self.frameListMode.value() != "Custom":
                startFrame = nuke.Root().firstFrame()
                endFrame = nuke.Root().lastFrame()
                if self.frameListMode.value() == "Input":
                    try:
                        activeInput = nuke.activeViewer().activeInput()
                        startFrame = nuke.activeViewer().node().input(activeInput).frameRange().first()
                        endFrame = nuke.activeViewer().node().input(activeInput).frameRange().last()
                    except:
                        pass
                
                if startFrame == endFrame:
                    self.frameList.setValue( str(startFrame) )
                else:
                    self.frameList.setValue( str(startFrame) + "-" + str(endFrame) )
            

# 
def SubmitToDeadline( ):
    global dialog
    global deadlineHome    
    
    root = nuke.Root()

    # Check if the nk was saved
#    if root.name() == "Root":
#        noRoot = True
#        if not studio:
#            nuke.message( "The Nuke script must be saved before it can be submitted to Deadline." )
#            return
    
    nuke_projects = []
    valid_projects = []
    
    # location of the jobs files
    # we are running the script in scripts/deadline
    jobsTemp = '../../jobs'
    
    # Get the maximum priority.
    try:
        output = CallDeadlineCommand( ["-getmaximumpriority",] )
        maximumPriority = int(output)
    except:
        maximumPriority = 100
    
    # Get the pools.
    output = CallDeadlineCommand( ["-pools",] )
    pools = output.splitlines()
    
    secondaryPools = []
    secondaryPools.append(" ")
    for currPool in pools:
        secondaryPools.append(currPool)
    
    # Get the groups.
    output = CallDeadlineCommand( ["-groups",] )
    groups = output.splitlines()
    
    initFrameListMode = "Global"
    initCustomFrameList = ("%s-%s" % (root.knob( "first_frame" ).value() , root.knob( "last_frame" ).value() ) )
    
    # Get the Frame List from nuke
    if initFrameListMode != "Custom":
        startFrame = nuke.Root().firstFrame()
        endFrame = nuke.Root().lastFrame()
        if initFrameListMode == "Input":
            try:
                activeInput = nuke.activeViewer().activeInput()
                startFrame = nuke.activeViewer().node().input(activeInput).frameRange().first()
                endFrame = nuke.activeViewer().node().input(activeInput).frameRange().last()
            except:
                pass
        
#        if startFrame == endFrame:
#            DeadlineGlobals.initFrameList = str(startFrame)
#        else:
#            DeadlineGlobals.initFrameList = str(startFrame) + "-" + str(endFrame)
    else:
        if initCustomFrameList == None or initCustomFrameList.strip() == "":
            startFrame = nuke.Root().firstFrame()
            endFrame = nuke.Root().lastFrame()
#            if startFrame == endFrame:
#                DeadlineGlobals.initFrameList = str(startFrame)
#            else:
#                DeadlineGlobals.initFrameList = str(startFrame) + "-" + str(endFrame)
#        else:
#            DeadlineGlobals.initFrameList = initCustomFrameList.strip()

    # Spawn extra info
    extraInfo = [ "" ] * 10
#    extraInfo[ 0 ] = DeadlineGlobals.initExtraInfo0
#    extraInfo[ 1 ] = DeadlineGlobals.initExtraInfo1
#    extraInfo[ 2 ] = DeadlineGlobals.initExtraInfo2
#    extraInfo[ 3 ] = DeadlineGlobals.initExtraInfo3
#    extraInfo[ 4 ] = DeadlineGlobals.initExtraInfo4
#    extraInfo[ 5 ] = DeadlineGlobals.initExtraInfo5
#    extraInfo[ 6 ] = DeadlineGlobals.initExtraInfo6
#    extraInfo[ 7 ] = DeadlineGlobals.initExtraInfo7
#    extraInfo[ 8 ] = DeadlineGlobals.initExtraInfo8
#    extraInfo[ 9 ] = DeadlineGlobals.initExtraInfo9

 
    # Check for potential issues and warn user about any that are found.
    warningMessages = ""
    nodeClasses = [ "Write", "DeepWrite", "WriteGeo" ]
    writeNodes = RecursiveFindNodes( nodeClasses, nuke.Root() )
    precompWriteNodes = RecursiveFindNodesInPrecomp( nodeClasses, nuke.Root() )
    
    print "Found a total of %d write nodes" % len( writeNodes )
    print "Found a total of %d write nodes within precomp nodes" % len( precompWriteNodes )
    
    # Check all the output filenames if they are local or not padded (non-movie files only).
    outputCount = 0
    
    # Check for errors and mistakes
#    for node in writeNodes:
#        reading = False
#        if node.knob( 'reading' ):
#            reading = node.knob( 'reading' ).value()
#        
#        # Need at least one write node that is enabled, and not set to read in as well.
#        if not node.knob( 'disable' ).value() and not reading:
#            outputCount = outputCount + 1
#            filename = nuke.filename(node)
#
#            if filename == "":
#                warningMessages = warningMessages + "No output path for write node '" + node.name() + "' is defined\n\n"
#            else:
#                fileType = node.knob( 'file_type' ).value()
#                
#                if filename == None:
#                    warningMessages = warningMessages + "Output path for write node '" + node.name() + "' is empty\n\n"
#                else:
#                    if IsPathLocal( filename ):
#                        warningMessages = warningMessages + "Output path for write node '" + node.name() + "' is local:\n" + filename + "\n\n"
#                    if not HasExtension( filename ) and fileType.strip() == "":
#                        warningMessages = warningMessages + "Output path for write node '%s' has no extension:\n%s\n\n"  % (node.name(), filename)
#                    if not IsMovie( filename ) and not IsPadded( os.path.basename( filename ) ):
#                        warningMessages = warningMessages + "Output path for write node '" + node.name() + "' is not padded:\n" + filename + "\n\n"
#    
#    # Warn if there are no write nodes.
#    if outputCount == 0 and not noRoot:
#        warningMessages = warningMessages + "At least one enabled write node that has 'read file' disabled is required to render\n\n"
#    
#    if len(nuke.views())  == 0:
#        warningMessages = warningMessages + "At least one view is required to render\n\n"
#    
#    # If there are any warning messages, show them to the user.
#    if warningMessages != "":
#        warningMessages = warningMessages + "Do you still wish to submit this job to Deadline?"
#        answer = nuke.ask( warningMessages )
#        if not answer:
#            return
    
    print "Creating submission dialog..."
    
    # Create the dialog
    dialog = HS_DeadlineDialog( maximumPriority, pools, secondaryPools, groups )

    # Show the dialog.
    success = False
    while not success:
        success = dialog.ShowDialog()
        if not success:
#            WriteStickySettings( dialog, configFile )
            return
        
        errorMessages = ""
        warningMessages = ""
        
        # Check that frame range is valid.
        if dialog.frameList.value().strip() == "":
            errorMessages = errorMessages + "No frame list has been specified.\n\n"
        
        # If submitting separate write nodes, make sure there are jobs to submit
        if dialog.selectedOnly.value():
            validNodeFound = False
            for node in writeNodes:
                if not node.knob( 'disable' ).value():
                    validNodeFound = True
                    if dialog.selectedOnly.value() and not IsNodeOrParentNodeSelected(node):
                        validNodeFound = False

                    if validNodeFound:
                        break
            else:
                for node in precompWriteNodes:
                    if not node.knob( 'disable' ).value():
                        validNodeFound = True
                        if dialog.selectedOnly.value() and not IsNodeOrParentNodeSelected(node):
                            validNodeFound = False
                        
                        if validNodeFound:
                            break

            if not validNodeFound:
                if dialog.selectedOnly.value():
                    errorMessages = errorMessages + "There are no selected write nodes, so there are no jobs to submit.\n\n"
        
#        # Check Draft template path
#        if dialog.submitDraftJob.value():
#            if not os.path.exists( dialog.templatePath.value() ):
#                errorMessages += "Draft job submission is enabled, but a Draft template has not been selected (or it does not exist). Either select a valid template, or disable Draft job submission.\n\n"
                    
        # Alert the user of any errors.
        if errorMessages != "":
            errorMessages = errorMessages + "Please fix these issues and submit again."
            nuke.message( errorMessages )
            success = False
        
        # Alert the user of any warnings.
        if success and warningMessages != "":
            warningMessages = warningMessages + "Do you still wish to submit this job to Deadline?"
            answer = nuke.ask( warningMessages )
            if not answer:
#                WriteStickySettings( dialog, configFile )
                return
            
    tempJobName = dialog.jobName.value()
    tempDependencies = ""
    tempFrameList = dialog.frameList.value().strip()
    tempChunkSize = dialog.chunkSize.value()
    tempIsMovie = False
    semaphore = threading.Semaphore()
    
    for tempNode in writeNodes:
        if not tempNode.knob( 'disable' ).value():
            enterLoop = True
            if dialog.selectedOnly.value():
                enterLoop = enterLoop and IsNodeOrParentNodeSelected(tempNode)

            if enterLoop:
                if IsMovie( tempNode.knob( 'file' ).value() ):
                    tempChunkSize = 1000000
                    tempIsMovie = True
                    break

    #Create a new thread to do the submission
    print "Spawning submission thread..."
    submitThread = threading.Thread( None, SubmitJob, None, ( dialog, root, None, writeNodes, jobsTemp, tempJobName, tempFrameList, tempDependencies, tempChunkSize, tempIsMovie, 1, None, extraInfo ) )
    submitThread.start()  
    

def SubmitJob( dialog, root, node, writeNodes, jobsTemp, tempJobName, tempFrameList, tempDependencies, tempChunkSize, tempIsMovie, jobCount, semaphore,  extraInfo ):
#    global ResolutionsDict
#    global FormatsDict
    viewsToRender = nuke.views()
        
    print "Preparing job #%d for submission.." % jobCount
    
    # Create a task in Nuke's progress  bar dialog
    #progressTask = nuke.ProgressTask("Submitting %s to Deadline" % tempJobName)
    progressTask = nuke.ProgressTask("Job Submission")
    progressTask.setMessage("Creating Job Info File")
    progressTask.setProgress(0)
    
    # the open method does not understand relative paths
    # so we have to join it with the path of the current script
    jobInfoFile = (u"%s/nuke_submit_info%d.job" % (os.path.join(os.path.dirname(__file__), jobsTemp), jobCount))
    fileHandle = open( jobInfoFile, "wb" )
    fileHandle.write( EncodeAsUTF16String( "Plugin=Nuke\n"                                                      ) )
    fileHandle.write( EncodeAsUTF16String( "Name=%s\n"                              % tempJobName               ) )
    fileHandle.write( EncodeAsUTF16String( "Comment=%s\n"                           % ''                        ) )
    fileHandle.write( EncodeAsUTF16String( "Department=%s\n"                        % ''                        ) )
    fileHandle.write( EncodeAsUTF16String( "Pool=%s\n"                              % dialog.pool.value()       ) )
    fileHandle.write( EncodeAsUTF16String( "SecondaryPool=%s\n"                     % ''                        ) )
    fileHandle.write( EncodeAsUTF16String( "Group=%s\n"                             % "none"                    ) )
    fileHandle.write( EncodeAsUTF16String( "Priority=%s\n"                          % 50                        ) )
    fileHandle.write( EncodeAsUTF16String( "MachineLimit=%s\n"                      % 0                         ) )
    fileHandle.write( EncodeAsUTF16String( "TaskTimeoutMinutes=%s\n"                % 0                         ) )
    fileHandle.write( EncodeAsUTF16String( "EnableAutoTimeout=%s\n"                 % True                      ) )
    fileHandle.write( EncodeAsUTF16String( "ConcurrentTasks=%s\n"                   % 1                         ) )
    fileHandle.write( EncodeAsUTF16String( "LimitConcurrentTasksToNumberOfCpus=%s\n" % True                     ) )
    fileHandle.write( EncodeAsUTF16String( "LimitGroups=%s\n"                       % ""                        ) )
    fileHandle.write( EncodeAsUTF16String( "JobDependencies=%s\n"                   %  tempDependencies         ) )
    fileHandle.write( EncodeAsUTF16String( "OnJobComplete=%s\n"                     % "Nothing"                 ) )
    fileHandle.write( EncodeAsUTF16String( "ForceReloadPlugin=%s\n"                 % False                     ) )
    fileHandle.write( EncodeAsUTF16String( "Frames=%s\n"                            % tempFrameList             ) )
    fileHandle.write( EncodeAsUTF16String( "ChunkSize=%s\n"                         % tempChunkSize             ) )
    fileHandle.write( EncodeAsUTF16String( "Whitelist=%s\n"                         % ""                        ) )
#    fileHandle.write( EncodeAsUTF16String( "InitialStatus=%s\n"                     % "Active"                  ) )
    
    extraKVPIndex = 0
    index = 0
#    
#    for v in viewsToRender:
#        for tempNode in writeNodes:
#            if not tempNode.knob( 'disable' ).value():
#                enterLoop = True
#                if dialog.selectedOnly.value():
#                    enterLoop = enterLoop and IsNodeOrParentNodeSelected(tempNode)
#                
#                if enterLoop:
#                    #gets the filename/proxy filename and evaluates TCL + vars, but *doesn't* swap frame padding
#                    fileValue = nuke.filename( tempNode )
#
#                    if ( root.proxy() and tempNode.knob( 'proxy' ).value() != "" ):
#                        evaluatedValue = tempNode.knob( 'proxy' ).evaluate(view=v)
#                    else:
#                        evaluatedValue = tempNode.knob( 'file' ).evaluate(view=v)
#
#                    if fileValue != None and fileValue != "" and evaluatedValue != None and evaluatedValue != "":
#                        tempPath, tempFilename = os.path.split( evaluatedValue )
#                        
#                        if IsPadded( os.path.basename( fileValue ) ):
#                            tempFilename = GetPaddedPath( tempFilename )
#
#                        paddedPath = os.path.join( tempPath, tempFilename )
#                        
#                        #Handle escape character cases
#                        paddedPath = paddedPath.replace( "\\", "/" )
#
#                        fileHandle.write( EncodeAsUTF16String( "OutputFilename%s=%s\n" % (index, paddedPath ) ) )
#
#                        #Check if the Write Node will be modifying the output's Frame numbers
#                        if tempNode.knob( 'frame_mode' ):
#                            if ( tempNode.knob( 'frame_mode' ).value() == "offset" ):
#                                fileHandle.write( EncodeAsUTF16String( "ExtraInfoKeyValue%d=OutputFrameOffset%s=%s\n" % ( extraKVPIndex, index, str( int( tempNode.knob( 'frame' ).value() ) ) ) ) )
#                                extraKVPIndex += 1
#                            elif ( tempNode.knob( 'frame_mode' ).value() == "start at" or tempNode.knob( 'frame_mode' ).value() == "start_at"):
#                                franges = nuke.FrameRanges( tempFrameList )
#                                fileHandle.write( EncodeAsUTF16String( "ExtraInfoKeyValue%d=OutputFrameOffset%s=%s\n" % ( extraKVPIndex, index, str( int( tempNode.knob( 'frame' ).value() ) - franges.minFrame() ) ) ) )
#                                extraKVPIndex += 1
#                            else:
#                                #TODO: Handle 'expression'? Would be much harder
#                                pass
#
#                        index = index + 1        

    # Write the shotgun data.
    groupBatch = False
#    if dialog.createNewVersion.value():
#        # we should get all this information from SG
#        # at the begginng with HS
#        if 'TaskName' in dialog.shotgunKVPs:
#            fileHandle.write( EncodeAsUTF16String( "ExtraInfo0=%s\n" % dialog.shotgunKVPs['TaskName'] ) )
#
#        if 'ProjectName' in dialog.shotgunKVPs:
#            fileHandle.write( EncodeAsUTF16String( "ExtraInfo1=%s\n" % dialog.shotgunKVPs['ProjectName'] ) )
#
#        if 'EntityName' in dialog.shotgunKVPs:
#            fileHandle.write( EncodeAsUTF16String( "ExtraInfo2=%s\n" % dialog.shotgunKVPs['EntityName'] ) )
#
#        if 'VersionName' in dialog.shotgunKVPs:
#            fileHandle.write( EncodeAsUTF16String( "ExtraInfo3=%s\n" % dialog.shotgunKVPs['VersionName'] ) )
#
#        if 'Description' in dialog.shotgunKVPs:
#            fileHandle.write( EncodeAsUTF16String( "ExtraInfo4=%s\n" % dialog.shotgunKVPs['Description'] ) )
#
#        if 'UserName' in dialog.shotgunKVPs:
#            fileHandle.write( EncodeAsUTF16String( "ExtraInfo5=%s\n" % dialog.shotgunKVPs['UserName'] ) )
#
#        #dump the rest in as KVPs
#        for key in dialog.shotgunKVPs:
#            if key != "DraftTemplate":
#                fileHandle.write( EncodeAsUTF16String( "ExtraInfoKeyValue%d=%s=%s\n" % ( extraKVPIndex, key, dialog.shotgunKVPs[key] ) ) )
#                extraKVPIndex += 1
#
#        if dialog.draftCreateMovie.value():
#            fileHandle.write( EncodeAsUTF16String( "ExtraInfoKeyValue%s=Draft_CreateSGMovie=True\n" % extraKVPIndex ) )
#            extraKVPIndex += 1
#            groupBatch = True
#
#        if dialog.draftCreateFilmStrip.value():
#            fileHandle.write( EncodeAsUTF16String( "ExtraInfoKeyValue%s=Draft_CreateSGFilmstrip=True\n" % extraKVPIndex ) )
#            extraKVPIndex += 1
#            groupBatch = True

    #Draft stuff
#    if dialog.submitDraftJob.value():
#        draftNode = node
#        #TODO: Need to figure out if we want to do something else in this case (all write nodes being submitted in one job)
#        if node == None:
#            draftNode = writeNodes[0] 
#        
#        if dialog.useQuickDraft.value():
#            fileHandle.write( EncodeAsUTF16String( "ExtraInfoKeyValue%d=SubmitQuickDraft=True\n" % (extraKVPIndex) ) )
#            extraKVPIndex += 1
#            fileHandle.write( EncodeAsUTF16String( "ExtraInfoKeyValue%d=DraftExtension=%s\n" % (extraKVPIndex, FormatsDict[dialog.draftFormat.value()][0]) ) )
#            extraKVPIndex += 1
#            fileHandle.write( EncodeAsUTF16String( "ExtraInfoKeyValue%d=DraftType=%s\n" % (extraKVPIndex, FormatsDict[dialog.draftFormat.value()][1]) ) )
#            extraKVPIndex += 1
#            fileHandle.write( EncodeAsUTF16String( "ExtraInfoKeyValue%d=DraftResolution=%s\n" % (extraKVPIndex, ResolutionsDict[dialog.draftResolution.value()]) ) )
#            extraKVPIndex += 1
#            fileHandle.write( EncodeAsUTF16String( "ExtraInfoKeyValue%d=DraftCodec=%s\n" % (extraKVPIndex, dialog.draftCodec.value() ) ) )
#            extraKVPIndex += 1
#            fileHandle.write( EncodeAsUTF16String( "ExtraInfoKeyValue%d=DraftQuality=%s\n" % (extraKVPIndex, dialog.draftQuality.value() ) ) )
#            extraKVPIndex += 1
#            fileHandle.write( EncodeAsUTF16String( "ExtraInfoKeyValue%d=DraftFrameRate=%s\n" % (extraKVPIndex, dialog.draftFrameRate.value() ) ) )
#            extraKVPIndex += 1
#        else:
#            fileHandle.write( EncodeAsUTF16String( "ExtraInfoKeyValue%d=DraftTemplate=%s\n" % (extraKVPIndex, dialog.templatePath.value() ) ) )
#            extraKVPIndex += 1
#            fileHandle.write( EncodeAsUTF16String( "ExtraInfoKeyValue%d=DraftUsername=%s\n" % (extraKVPIndex, dialog.draftUser.value() ) ) )
#            extraKVPIndex += 1
#            fileHandle.write( EncodeAsUTF16String( "ExtraInfoKeyValue%d=DraftEntity=%s\n" % (extraKVPIndex, dialog.draftEntity.value()) ) )
#            extraKVPIndex += 1
#            fileHandle.write( EncodeAsUTF16String( "ExtraInfoKeyValue%d=DraftVersion=%s\n" % (extraKVPIndex, dialog.draftVersion.value()) ) )
#            extraKVPIndex += 1
#            fileHandle.write( EncodeAsUTF16String( "ExtraInfoKeyValue%d=DraftFrameWidth=%s\n" % (extraKVPIndex, draftNode.width()) ) )
#            extraKVPIndex += 1
#            fileHandle.write( EncodeAsUTF16String( "ExtraInfoKeyValue%d=DraftFrameHeight=%s\n" % (extraKVPIndex, draftNode.height()) ) )
#            extraKVPIndex += 1
#            fileHandle.write( EncodeAsUTF16String( "ExtraInfoKeyValue%d=DraftExtraArgs=%s\n" % (extraKVPIndex, dialog.draftExtraArgs.value()) ) )
#            extraKVPIndex += 1
#            
#        fileHandle.write( EncodeAsUTF16String( "ExtraInfoKeyValue%d=DraftUploadToShotgun=%s\n" % (extraKVPIndex, str(dialog.uploadToShotgun.enabled() and dialog.uploadToShotgun.value())) ) )
#        extraKVPIndex += 1
#        extraKVPIndex += 1
#        
#        groupBatch = True
#        
#    if groupBatch:
#        fileHandle.write( EncodeAsUTF16String( "BatchName=%s\n" % batchName ) )
#    
#    fileHandle.write( EncodeAsUTF16String( "IncludeEnvironment=%s\n"        % True ) ) 
    fileHandle.write( EncodeAsUTF16String( "EnvironmentKeyValue%s=%s=%s\n"  % (0, "THEBOATFOLDER",os.environ["THEBOATFOLDER"]) ) ) 
    fileHandle.write( EncodeAsUTF16String( "EnvironmentKeyValue%s=%s=%s\n"  % (1, "SHOT",os.environ["SHOT"]) ) ) 
    fileHandle.write( EncodeAsUTF16String( "EnvironmentKeyValue%s=%s=%s\n"  % (2, "NUKE_PATH",os.environ["NUKE_PATH"]) ) ) 
    fileHandle.write( EncodeAsUTF16String( "EnvironmentKeyValue%s=%s=%s\n"  % (3, "JOB",os.environ["JOB"]) ) ) 
    fileHandle.write( EncodeAsUTF16String( "EnvironmentKeyValue%s=%s=%s\n"  % (4, "TASK",os.environ["TASK"]) ) ) 
    
    fileHandle.close()
    
    # Update task progress
    progressTask.setMessage("Creating Plugin Info File")
    progressTask.setProgress(10)
    
    # Create the plugin info file
    # the open method does not understand relative paths
    # so we have to join it with the path of the current script
    pluginInfoFile = (u"%s/nuke_plugin_info%d.job" % (os.path.join(os.path.dirname(__file__), jobsTemp), jobCount))
    fileHandle = open( pluginInfoFile, "w" )
    
    fileHandle.write( EncodeAsUTF16String( "Version=%s.%s\n"            % (nuke.env[ 'NukeVersionMajor' ], nuke.env['NukeVersionMinor']) ) )
    fileHandle.write( EncodeAsUTF16String( "Threads=%s\n"               % 0                             ) )
    fileHandle.write( EncodeAsUTF16String( "RamUse=%s\n"                % 0                             ) )
    fileHandle.write( EncodeAsUTF16String( "BatchMode=%s\n"             % True                          ) )
    fileHandle.write( EncodeAsUTF16String( "BatchModeIsMovie=%s\n"      % tempIsMovie ) )
    
    if dialog.selectedOnly.value():
        writeNodesStr = ""

        for tempNode in writeNodes:
            if not tempNode.knob( 'disable' ).value():
                enterLoop = True
                if dialog.selectedOnly.value():
                    enterLoop = enterLoop and IsNodeOrParentNodeSelected(tempNode)

                if enterLoop:
                    #we need the fullName of the node here, otherwise write nodes that are embedded in groups won't work
                    writeNodesStr += ("%s," % tempNode.fullName())
        writeNodesStr = writeNodesStr.strip( "," )
        fileHandle.write( EncodeAsUTF16String( "WriteNode=%s\n" % writeNodesStr ) )

    fileHandle.write( EncodeAsUTF16String( "NukeX=%s\n"     % False                ) )
    fileHandle.write( EncodeAsUTF16String( "UseGpu=%s\n"    % False                ) )

    fileHandle.write( EncodeAsUTF16String( "RenderMode=%s\n"                % "Use Scene Settings" ) )
    fileHandle.write( EncodeAsUTF16String( "EnforceRenderOrder=%s\n"        % False ) )
    fileHandle.write( EncodeAsUTF16String( "ContinueOnError=%s\n"           % False ) )
    fileHandle.write( EncodeAsUTF16String( "PerformanceProfiler=%s\n"       % False ) )
    fileHandle.write( EncodeAsUTF16String( "PerformanceProfilerDir=%s\n"    % "" ) )
    fileHandle.write( EncodeAsUTF16String( "Views=%s\n"                     % "" ) )
    fileHandle.write( EncodeAsUTF16String( "StackSize=%s\n"                 % 0  ) )

    fileHandle.close()
    
    # Update task progress
    progressTask.setMessage("Submitting Job %d to Deadline" % jobCount)
    progressTask.setProgress(30)
    
    # Submit the job to Deadline
    args = []
    args.append( jobInfoFile.encode(locale.getpreferredencoding() ) )
    args.append( pluginInfoFile.encode(locale.getpreferredencoding() ) )
    args.append( root.name() ) # SUBMIT SCENE
        
    tempResults = ""
    
    # Submit Job
    progressTask.setProgress(50)
    
    # If submitting multiple jobs, acquire the semaphore so that only one job is submitted at a time.
    if semaphore:
        semaphore.acquire()
        
    try:
        tempResults = CallDeadlineCommand( args )
    finally:
        # Release the semaphore if necessary.
        if semaphore:
            semaphore.release()
    
    # Update task progress
    progressTask.setMessage("Complete!")
    progressTask.setProgress(100)
    
    print "Job submission #%d complete" % jobCount
    
    # If submitting multiple jobs, just print the results to the console, otherwise show them to the user.
    if semaphore:
        print tempResults
    else:
        nuke.executeInMainThread( nuke.message, tempResults )
    
    return tempResults

def IsNodeOrParentNodeSelected( node ):
    if node.isSelected():
        return True
    
    parentNode = nuke.toNode( '.'.join( node.fullName().split('.')[:-1] ) )
    if parentNode:
        return IsNodeOrParentNodeSelected( parentNode )
    
    return False

#This will recursively find nodes of the given class (used to find write nodes, even if they're embedded in groups).  
def RecursiveFindNodes(nodeClasses, startNode):
    nodeList = []
    
    if startNode != None:
        if startNode.Class() in nodeClasses:
            nodeList = [startNode]
        elif isinstance(startNode, nuke.Group):
            for child in startNode.nodes():
                nodeList.extend( RecursiveFindNodes(nodeClasses, child) )
        
    return nodeList

def RecursiveFindNodesInPrecomp(nodeClasses, startNode):
    nodeList = []
    
    if startNode != None:
        if startNode.Class() == "Precomp":
            for child in startNode.nodes():
                nodeList.extend( RecursiveFindNodes(nodeClasses, child) )
        elif isinstance(startNode, nuke.Group):
            for child in startNode.nodes():
                nodeList.extend( RecursiveFindNodesInPrecomp(nodeClasses, child) )
    
    return nodeList
    
# Checks a path to make sure it has an extension
def HasExtension( path ):
    filename = os.path.basename( path )
    
    return filename.rfind( "." ) > -1

# Checks if path is local (c, d, or e drive).
def IsPathLocal( path ):
    lowerPath = path.lower()
    if lowerPath.startswith( "c:" ) or lowerPath.startswith( "d:" ) or lowerPath.startswith( "e:" ):
        return True
    return False

# Checks if the given filename ends with a movie extension
def IsMovie( path ):
    lowerPath = path.lower()
    if lowerPath.endswith( ".mov" ):
        return True
    return False

# Checks if the filename is padded (ie: \\output\path\filename_%04.tga).
def IsPadded( path ):
    #Check for padding in the file
    paddingRe = re.compile( "%([0-9]+)d", re.IGNORECASE )
    if paddingRe.search( path ) != None:
        return True
    elif path.find( "#" ) > -1:
        return True
    return False

# Parses through the filename looking for the last padded pattern, replaces
# it with the correct number of #'s, and returns the new padded filename.
def GetPaddedPath( path ):
    paddingRe = re.compile( "([0-9]+)", re.IGNORECASE )
    
    paddingMatches = paddingRe.findall( path )
    if paddingMatches != None and len( paddingMatches ) > 0:
        paddingString = paddingMatches[ len( paddingMatches ) - 1 ]
        paddingSize = len(paddingString)
        
        padding = ""
        while len(padding) < paddingSize:
            padding = padding + "#"
        
        path = RightReplace( path, paddingString, padding, 1 )
    
    return path
    
def RightReplace(s, old, new, occurrence):
    li = s.rsplit(old, occurrence)
    return new.join(li)

def EncodeAsUTF16String( unicodeString ):
    return unicodeString.decode( "utf-8" ).encode( "utf-16-le" )

def CallDeadlineCommand( arguments, hideWindow=True ):
    # On OSX, we look for the DEADLINE_PATH file. On other platforms, we use the environment variable.
    if os.path.exists( "/Users/Shared/Thinkbox/DEADLINE_PATH" ):
        with open( "/Users/Shared/Thinkbox/DEADLINE_PATH" ) as f: deadlineBin = f.read().strip()
        deadlineCommand = deadlineBin + "/deadlinecommand"
    else:
        deadlineBin = os.environ['DEADLINE_PATH']
        if os.name == 'nt':
            deadlineCommand = deadlineBin + "\\deadlinecommand.exe"
        else:
            deadlineCommand = deadlineBin + "/deadlinecommand"
    
    startupinfo = None
    if hideWindow and os.name == 'nt':
        # Python 2.6 has subprocess.STARTF_USESHOWWINDOW, and Python 2.7 has subprocess._subprocess.STARTF_USESHOWWINDOW, so check for both.
        if hasattr( subprocess, '_subprocess' ) and hasattr( subprocess._subprocess, 'STARTF_USESHOWWINDOW' ):
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess._subprocess.STARTF_USESHOWWINDOW
        elif hasattr( subprocess, 'STARTF_USESHOWWINDOW' ):
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    
    environment = {}
    for key in os.environ.keys():
        environment[key] = str(os.environ[key])
        
    # Need to set the PATH, cuz windows seems to load DLLs from the PATH earlier that cwd....
    if os.name == 'nt':
        environment['PATH'] = str(deadlineBin + os.pathsep + os.environ['PATH'])
    
    arguments.insert( 0, deadlineCommand)
    
    # Specifying PIPE for all handles to workaround a Python bug on Windows. The unused handles are then closed immediatley afterwards.
    proc = subprocess.Popen(arguments, cwd=deadlineBin, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, startupinfo=startupinfo, env=environment)
    proc.stdin.close()
    proc.stderr.close()
    
    output = proc.stdout.read()
    
    return output
