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

from simpleSgApi import simpleSgApi

# THE DIALOG
class HS_DeadlineDialog( nukescripts.PythonPanel ):
    def __init__( self, maximumPriority, pools, secondaryPools, groups ):
        nukescripts.PythonPanel.__init__( self, "Submit To Deadline", "com.vfxboat.software.deadlinedialog" )
        self.sg = simpleSgApi();

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
        self.sgUserName.setTooltip( "Your Shotgun account name" )
        self.sgUserName.setValue( '' )
        
        self.sgConnectButton = nuke.PyScript_Knob( "Deadline_SGConnectButton", "Connect")
        self.addKnob( self.sgConnectButton )
        self.sgConnectButton.setTooltip( "Connect to the SG" )
        
        # SG Task
        # Get the jobname from the os.environ
        sgTask = os.environ["TASK"]
        self.sgTaskCombo = nuke.Enumeration_Knob( "Deadline_sgTasks", "Tasks", [] )
        self.addKnob( self.sgTaskCombo )
        self.sgTaskCombo.setTooltip( "Select your task" )
        
        self.sgTaskId = nuke.String_Knob("Deadline_sgTaskId", "Task Id")
        self.addKnob( self.sgTaskId )
        self.sgTaskId.setEnabled( False )

        self.sgProjectName = nuke.String_Knob("Deadline_sgProjectName", "Project Name")
        self.addKnob( self.sgProjectName )
        self.sgProjectName.setEnabled( False )

        self.sgProjectId = nuke.String_Knob("Deadline_sgProjectId", "Project Id")
        self.addKnob( self.sgProjectId )
        self.sgProjectId.setEnabled( False )

        self.sgEntityName = nuke.String_Knob("Deadline_sgEntityName", "Entity")
        self.addKnob( self.sgEntityName )
        self.sgEntityName.setEnabled( False )

        self.sgEntityType = nuke.String_Knob("Deadline_sgEntityType", "Entity Type")
        self.addKnob( self.sgEntityType )
        self.sgEntityType.setEnabled( False )

        self.sgEntityId = nuke.String_Knob("Deadline_sgEntityId", "Entity Id")
        self.addKnob( self.sgEntityId )
        self.sgEntityId.setEnabled( False )

        self.sgVersionName = nuke.String_Knob("Deadline_sgVersionName", "Version Name")
        self.addKnob( self.sgVersionName )

        # SG New Description
        self.sgDescription = nuke.String_Knob( "Deadline_sgDescription", "Description" )
        self.addKnob( self.sgDescription )
        self.sgDescription.setTooltip( "The description of the new Version that will be created." )
        self.sgDescription.setValue( "" )
        
        ##########################################################################################
        ## Draft Options
        ##########################################################################################

        # WE SHOULD CHANGE THIS TO DRAFT QUALITY
        self.draftTemplateCombo = nuke.Enumeration_Knob( "Deadline_draftTemplate", "Draft Quality", ["Apple ProRes", "DNXHD", "H.264"] )
        self.addKnob( self.draftTemplateCombo )
        self.draftTemplateCombo.setTooltip( "Select the draft quality" )

    def ShowDialog( self ):
        return nukescripts.PythonPanel.showModalDialog( self )
    
    # listen to knobs changing
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

        # when the user press the connect button
        # populate the Task Combo with the user tasks
        if knob == self.sgConnectButton:
            if self.sgUserName.value() == '':
                nuke.message('You should write your SG account name')
            else:
                self.sg.connect(self.sgUserName.value())
                self.sgTasks = self.sg.getTasks()

                tasksContent = []
                for task in self.sgTasks:
                    tasksContent.append(task['content'])

                self.sgTaskCombo.setValues(tasksContent)

        # when the user select a task in the task combo
        # display the information
        if knob == self.sgTaskCombo:
            print ( "selected task %s" % self.sgTaskCombo.value() )
            for task in self.sgTasks:
                if self.sgTaskCombo.value() == task['content']:

                    print task

                    self.sgProjectName.setValue( task["project"]["name"] )
                    self.sgProjectId.setValue( str( task["project"]["id"] ) )
                    self.sgEntityName.setValue( task["entity"]["name"] )
                    self.sgEntityId.setValue( str(task["entity"]["id"]) )
                    self.sgEntityType.setValue( task["entity"]["type"] )
                    self.sgTaskId.setValue( str(task["id"]) )

                    # query the latest version name
                    latestVersionName = self.sg.getLatestVersion( task )

                    # default to v1 if there are no versions
                    if latestVersionName is None:
                        self.sgVersionName.setValue(task["content"] + '_v1')
                    else:

                        # separate the values
                        newVersionSplitted = latestVersionName["code"].split('_')

                        # get latest value (version number) and increment
                        try:
                            newVersionNumber = int(newVersionSplitted[-1].split('v')[1])
                            newVersionNumber += 1

                            # remove the version number from the string
                            del newVersionSplitted[-1]

                            newVersionName = "_".join(newVersionSplitted)

                            self.sgVersionName.setValue( "%s_v%i" % (newVersionName, newVersionNumber) )
                        except:
                            self.sgVersionName.setValue('')


# 
def SubmitToDeadline( ):
    global dialog
    global deadlineHome    
    
    root = nuke.Root()

    # Check if the nk was saved
    if root.name() == "Root":
        nuke.message( "The Nuke script must be saved before it can be submitted to Deadline." )
        return
    
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
    else:
        if initCustomFrameList == None or initCustomFrameList.strip() == "":
            startFrame = nuke.Root().firstFrame()
            endFrame = nuke.Root().lastFrame()

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
    for node in writeNodes:
        reading = False
        if node.knob( 'reading' ):
            reading = node.knob( 'reading' ).value()

        # Need at least one write node that is enabled, and not set to read in as well.
        if not node.knob( 'disable' ).value() and not reading:
            outputCount = outputCount + 1
            filename = nuke.filename(node)

            if filename == "":
                warningMessages = warningMessages + "No output path for write node '" + node.name() + "' is defined\n\n"
            else:
                fileType = node.knob( 'file_type' ).value()

                if filename == None:
                    warningMessages = warningMessages + "Output path for write node '" + node.name() + "' is empty\n\n"
                else:
                    if IsPathLocal( filename ):
                        warningMessages = warningMessages + "Output path for write node '" + node.name() + "' is local:\n" + filename + "\n\n"
                    if not HasExtension( filename ) and fileType.strip() == "":
                        warningMessages = warningMessages + "Output path for write node '%s' has no extension:\n%s\n\n"  % (node.name(), filename)
                    if not IsMovie( filename ) and not IsPadded( os.path.basename( filename ) ):
                        warningMessages = warningMessages + "Output path for write node '" + node.name() + "' is not padded:\n" + filename + "\n\n"

    # Warn if there are no write nodes.
    if outputCount == 0 and not noRoot:
        warningMessages = warningMessages + "At least one enabled write node that has 'read file' disabled is required to render\n\n"

    if len(nuke.views())  == 0:
        warningMessages = warningMessages + "At least one view is required to render\n\n"

    # If there are any warning messages, show them to the user.
    if warningMessages != "":
        warningMessages = warningMessages + "Do you still wish to submit this job to Deadline?"
        answer = nuke.ask( warningMessages )
        if not answer:
            return
    
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
    fileHandle.write( EncodeAsUTF16String( "TaskTimeoutMinutes=%s\n"                % 15                         ) )
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
    for v in viewsToRender:
        for tempNode in writeNodes:
            if not tempNode.knob( 'disable' ).value():
                enterLoop = True
                if dialog.selectedOnly.value():
                    enterLoop = enterLoop and IsNodeOrParentNodeSelected(tempNode)

                if enterLoop:
                    #gets the filename/proxy filename and evaluates TCL + vars, but *doesn't* swap frame padding
                    fileValue = nuke.filename( tempNode )

                    if ( root.proxy() and tempNode.knob( 'proxy' ).value() != "" ):
                        evaluatedValue = tempNode.knob( 'proxy' ).evaluate(view=v)
                    else:
                        evaluatedValue = tempNode.knob( 'file' ).evaluate(view=v)

                    if fileValue != None and fileValue != "" and evaluatedValue != None and evaluatedValue != "":
                        tempPath, tempFilename = os.path.split( evaluatedValue )

                        if IsPadded( os.path.basename( fileValue ) ):
                            tempFilename = GetPaddedPath( tempFilename )

                        paddedPath = os.path.join( tempPath, tempFilename )

                        #Handle escape character cases
                        paddedPath = paddedPath.replace( "\\", "/" )

                        fileHandle.write( EncodeAsUTF16String( "OutputFilename%s=%s\n" % (index, paddedPath ) ) )

                        #Check if the Write Node will be modifying the output's Frame numbers
                        if tempNode.knob( 'frame_mode' ):
                            if ( tempNode.knob( 'frame_mode' ).value() == "offset" ):
                                fileHandle.write( EncodeAsUTF16String( "ExtraInfoKeyValue%d=OutputFrameOffset%s=%s\n" % ( extraKVPIndex, index, str( int( tempNode.knob( 'frame' ).value() ) ) ) ) )
                                extraKVPIndex += 1
                            elif ( tempNode.knob( 'frame_mode' ).value() == "start at" or tempNode.knob( 'frame_mode' ).value() == "start_at"):
                                franges = nuke.FrameRanges( tempFrameList )
                                fileHandle.write( EncodeAsUTF16String( "ExtraInfoKeyValue%d=OutputFrameOffset%s=%s\n" % ( extraKVPIndex, index, str( int( tempNode.knob( 'frame' ).value() ) - franges.minFrame() ) ) ) )
                                extraKVPIndex += 1
                            else:
                                #TODO: Handle 'expression'? Would be much harder
                                pass

                        index = index + 1

    # Write the shotgun data.
    groupBatch = True

    # Creating a new version in SG
    fileHandle.write( EncodeAsUTF16String( "ExtraInfo0=%s\n" % dialog.sgTaskCombo.value() ) )
    fileHandle.write( EncodeAsUTF16String( "ExtraInfo1=%s\n" % dialog.sgProjectName.value() ) )
    fileHandle.write( EncodeAsUTF16String( "ExtraInfo2=%s\n" % dialog.sgEntityName.value() ) )
    fileHandle.write( EncodeAsUTF16String( "ExtraInfo3=%s\n" % dialog.sgVersionName.value() ) )
    fileHandle.write( EncodeAsUTF16String( "ExtraInfo4=%s\n" % dialog.sgDescription.value() ) )
    fileHandle.write( EncodeAsUTF16String( "ExtraInfo5=%s\n" % dialog.sgUserName.value() ) )


    # Draft Stuff
    extraKVPIndex = 0


    fileHandle.write( EncodeAsUTF16String( "ExtraInfoKeyValue%d=UserName=%s\n"      % (extraKVPIndex, dialog.sgUserName.value() ) ) )
    extraKVPIndex += 1
    fileHandle.write( EncodeAsUTF16String( "ExtraInfoKeyValue%d=Description=%s\n"   % (extraKVPIndex, dialog.sgDescription.value() ) ) )
    extraKVPIndex += 1
    fileHandle.write( EncodeAsUTF16String( "ExtraInfoKeyValue%d=ProjectName=%s\n"   % (extraKVPIndex, dialog.sgProjectName.value() ) ) )
    extraKVPIndex += 1
    fileHandle.write( EncodeAsUTF16String( "ExtraInfoKeyValue%d=EntityName=%s\n"    % (extraKVPIndex, dialog.sgEntityName.value() ) ) )
    extraKVPIndex += 1
    fileHandle.write( EncodeAsUTF16String( "ExtraInfoKeyValue%d=EntityType=%s\n"    % (extraKVPIndex, dialog.sgEntityType.value() ) ) )
    extraKVPIndex += 1
    fileHandle.write( EncodeAsUTF16String( "ExtraInfoKeyValue%d=VersionName=%s\n"   % (extraKVPIndex, dialog.sgVersionName.value() ) ) )
    extraKVPIndex += 1
    fileHandle.write( EncodeAsUTF16String( "ExtraInfoKeyValue%d=ProjectId=%s\n"     % (extraKVPIndex, dialog.sgProjectId.value() ) ) )
    extraKVPIndex += 1
    fileHandle.write( EncodeAsUTF16String( "ExtraInfoKeyValue%d=TaskId=%s\n"        % (extraKVPIndex, dialog.sgTaskId.value() ) ) )
    extraKVPIndex += 1
    fileHandle.write( EncodeAsUTF16String( "ExtraInfoKeyValue%d=TaskName=%s\n"      % (extraKVPIndex, dialog.sgTaskCombo.value() ) ) )
    extraKVPIndex += 1
    fileHandle.write( EncodeAsUTF16String( "ExtraInfoKeyValue%d=EntityId=%s\n"      % (extraKVPIndex, dialog.sgEntityId.value() ) ) )
    extraKVPIndex += 1


    # Instead of using the quickdraft use the template, so we can burn in the info
    draftTemplateAbsolutePath = os.path.join(os.path.dirname(__file__), 'draft/draftTemplate.py')

    fileHandle.write( EncodeAsUTF16String( "ExtraInfoKeyValue%d=DraftTemplate=%s\n" % (extraKVPIndex, draftTemplateAbsolutePath ) ) )
    extraKVPIndex += 1
    fileHandle.write( EncodeAsUTF16String( "ExtraInfoKeyValue%d=DraftUsername=%s\n" % (extraKVPIndex, dialog.sgUserName.value() ) ) )
    extraKVPIndex += 1
    fileHandle.write( EncodeAsUTF16String( "ExtraInfoKeyValue%d=DraftEntity=%s\n" % (extraKVPIndex, dialog.sgTaskCombo.value() ) ) )
    extraKVPIndex += 1
    fileHandle.write( EncodeAsUTF16String( "ExtraInfoKeyValue%d=DraftVersion=%s\n" % (extraKVPIndex, dialog.sgVersionName.value() ) ) )
    extraKVPIndex += 1
    fileHandle.write( EncodeAsUTF16String( "ExtraInfoKeyValue%d=DraftFrameWidth=%s\n" % (extraKVPIndex, 1280 ) ) )
    extraKVPIndex += 1
    fileHandle.write( EncodeAsUTF16String( "ExtraInfoKeyValue%d=DraftFrameHeight=%s\n" % (extraKVPIndex, 720 ) ) )
    extraKVPIndex += 1
    fileHandle.write( EncodeAsUTF16String( "ExtraInfoKeyValue%d=DraftExtraArgs=%s\n" % (extraKVPIndex, "" ) ) )
    extraKVPIndex += 1

    # This line renders a mov for shotgun using the Draft_CreateShotgunMovie.py from the repo
#    fileHandle.write( EncodeAsUTF16String( "ExtraInfoKeyValue%s=Draft_CreateSGMovie=True\n" % extraKVPIndex ) )
#    extraKVPIndex += 1

    # This line renders a filmstrip for shotgun
#    fileHandle.write( EncodeAsUTF16String( "ExtraInfoKeyValue%s=Draft_CreateSGFilmstrip=True\n" % extraKVPIndex ) )
#    extraKVPIndex += 1

    # This line uploads the movie to shotgun
    fileHandle.write( EncodeAsUTF16String( "ExtraInfoKeyValue%d=DraftUploadToShotgun=%s\n" % (extraKVPIndex,  True ) ) )
    extraKVPIndex += 1


    fileHandle.write( EncodeAsUTF16String( "BatchName=%s\n" % dialog.jobName.value() ) )


    # ENV KEYS
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
