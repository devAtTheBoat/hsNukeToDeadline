# -- coding: utf-8 --
import os
import sys
import re
import traceback
import subprocess
import ast
import threading
import time
import locale

try:
    import ConfigParser
except:
    print( "Could not load ConfigParser module, sticky settings will not be loaded/saved" )

try:
    import hiero
    from hiero import core as hcore
except:
    pass

import nuke
import nukescripts

dialog = None
#deadlineCommand = None
Formats = []
Resolutions = []
FrameRates = []
Restrictions = []
dlRenderModes = [ "Use Scene Settings", "Render Full Resolution", "Render using Proxies" ]

FormatsDict = {}
ResolutionsDict = {}
CodecsDict = {}
RestrictionsDict = {}

class DeadlineDialog( nukescripts.PythonPanel ):
    pools = []
    groups = []

    shotgunKVPs = {}
    ftrackKVPs = {}
    pulledFTrackKVPs = {}
    nimKVPs = {}

    def __init__( self, maximumPriority, pools, secondaryPools, groups ):
        global Formats
        global Resolutions
        global FrameRates
        global Restrictions
        global dlRenderModes

        nukescripts.PythonPanel.__init__( self, "Submit To Deadline", "com.thinkboxsoftware.software.deadlinedialog" )

        width = 620
        height = 705 #Nuke v6 or earlier UI height

        if int(nuke.env[ 'NukeVersionMajor' ]) >= 7: #GPU rendering UI
            height += 20
        if int(nuke.env[ 'NukeVersionMajor' ]) >= 9: #Performance Profiler UI
            height += 40

        self.setMinimumSize( width, height ) # width, height
        self.ReadInDraftOptions()
        self.jobTab = nuke.Tab_Knob( "Deadline_JobOptionsTab", "Render on the farm" )
        self.addKnob( self.jobTab )

        ##########################################################################################
        ## Job Description
        ##########################################################################################

        # Job Name
        self.jobName = nuke.String_Knob( "Deadline_JobName", "Job Name" )
        self.addKnob( self.jobName )
        self.jobName.setTooltip( "The name of your job. This is optional, and if left blank, it will default to 'Untitled'." )
        self.jobName.setValue( "Untitled" )

        # Comment
        self.comment = nuke.String_Knob( "Deadline_Comment", "Comment" )
        self.addKnob( self.comment )
        self.comment.setTooltip( "A simple description of your job. This is optional and can be left blank." )
        self.comment.setValue( "" )

        # Department
        self.department = nuke.String_Knob( "Deadline_Department", "Department" )
        self.addKnob( self.department )
        self.department.setTooltip( "The department you belong to. This is optional and can be left blank." )
        self.department.setValue( "" )

        # Separator
#        self.separator1 = nuke.Text_Knob( "Deadline_Separator1", "" )
#        self.addKnob( self.separator1 )

        ##########################################################################################
        ## Job Scheduling
        ##########################################################################################

        # Pool
        self.pool = nuke.Enumeration_Knob( "Deadline_Pool", "Pool", pools )
        self.addKnob( self.pool )
        self.pool.setTooltip( "The pool that your job will be submitted to." )
        self.pool.setValue( "none" )

        # Secondary Pool
        self.secondaryPool = nuke.Enumeration_Knob( "Deadline_SecondaryPool", "Secondary Pool", secondaryPools )
        self.addKnob( self.secondaryPool )
        self.secondaryPool.setTooltip( "The secondary pool lets you specify a Pool to use if the primary Pool does not have any available Slaves." )
        self.secondaryPool.setValue( " " )

        # Group
        self.group = nuke.Enumeration_Knob( "Deadline_Group", "Group", groups )
        self.addKnob( self.group )
        self.group.setTooltip( "The group that your job will be submitted to." )
        self.group.setValue( "none" )

        # Priority
        self.priority = nuke.Int_Knob( "Deadline_Priority", "Priority" )
        self.addKnob( self.priority )
        self.priority.setTooltip( "A job can have a numeric priority ranging from 0 to " + str(maximumPriority) + ", where 0 is the lowest priority." )
        self.priority.setValue( 50 )

        # Task Timeout
        self.taskTimeout = nuke.Int_Knob( "Deadline_TaskTimeout", "Task Timeout" )
        self.addKnob( self.taskTimeout )
        self.taskTimeout.setTooltip( "The number of minutes a slave has to render a task for this job before it requeues it. Specify 0 for no limit." )
        self.taskTimeout.setValue( 0 )

        # Auto Task Timeout
        self.autoTaskTimeout = nuke.Boolean_Knob( "Deadline_AutoTaskTimeout", "Enable Auto Task Timeout" )
        self.addKnob( self.autoTaskTimeout )
        self.autoTaskTimeout.setTooltip( "If the Auto Task Timeout is properly configured in the Repository Options, then enabling this will allow a task timeout to be automatically calculated based on the render times of previous frames for the job." )
        self.autoTaskTimeout.setValue( False )

        # Concurrent Tasks
        self.concurrentTasks = nuke.Int_Knob( "Deadline_ConcurrentTasks", "Concurrent Tasks" )
        self.addKnob( self.concurrentTasks )
        self.concurrentTasks.setTooltip( "The number of tasks that can render concurrently on a single slave. This is useful if the rendering application only uses one thread to render and your slaves have multiple CPUs." )
        self.concurrentTasks.setValue( 1 )

        # Limit Concurrent Tasks
        self.limitConcurrentTasks = nuke.Boolean_Knob( "Deadline_LimitConcurrentTasks", "Limit Tasks To Slave's Task Limit" )
        self.addKnob( self.limitConcurrentTasks )
        self.limitConcurrentTasks.setTooltip( "If you limit the tasks to a slave's task limit, then by default, the slave won't dequeue more tasks then it has CPUs. This task limit can be overridden for individual slaves by an administrator." )
        self.limitConcurrentTasks.setValue( False )

        # Machine Limit
        self.machineLimit = nuke.Int_Knob( "Deadline_MachineLimit", "Machine Limit" )
        self.addKnob( self.machineLimit )
        self.machineLimit.setTooltip( "Use the Machine Limit to specify the maximum number of machines that can render your job at one time. Specify 0 for no limit." )
        self.machineLimit.setValue( 0 )

        # Machine List Is Blacklist
        self.isBlacklist = nuke.Boolean_Knob( "Deadline_IsBlacklist", "Machine List Is A Blacklist" )
        self.addKnob( self.isBlacklist )
        self.isBlacklist.setTooltip( "You can force the job to render on specific machines by using a whitelist, or you can avoid specific machines by using a blacklist." )
        self.isBlacklist.setValue( False )

        # Machine List
        self.machineList = nuke.String_Knob( "Deadline_MachineList", "Machine List" )
        self.addKnob( self.machineList )
        self.machineList.setTooltip( "The whitelisted or blacklisted list of machines." )
        self.machineList.setValue( "" )

        self.machineListButton = nuke.PyScript_Knob( "Deadline_MachineListButton", "Browse" )
        self.addKnob( self.machineListButton )

        # Limit Groups
        self.limitGroups = nuke.String_Knob( "Deadline_LimitGroups", "Limits" )
        self.addKnob( self.limitGroups )
        self.limitGroups.setTooltip( "The Limits that your job requires." )
        self.limitGroups.setValue( "" )

        self.limitGroupsButton = nuke.PyScript_Knob( "Deadline_LimitGroupsButton", "Browse" )
        self.addKnob( self.limitGroupsButton )

        # Dependencies
        self.dependencies = nuke.String_Knob( "Deadline_Dependencies", "Dependencies" )
        self.addKnob( self.dependencies )
        self.dependencies.setTooltip( "Specify existing jobs that this job will be dependent on. This job will not start until the specified dependencies finish rendering." )
        self.dependencies.setValue( "" )

        self.dependenciesButton = nuke.PyScript_Knob( "Deadline_DependenciesButton", "Browse" )
        self.addKnob( self.dependenciesButton )

        # On Complete
        self.onComplete = nuke.Enumeration_Knob( "Deadline_OnComplete", "On Job Complete", ("Nothing", "Archive", "Delete") )
        self.addKnob( self.onComplete )
        self.onComplete.setTooltip( "If desired, you can automatically archive or delete the job when it completes." )
        self.onComplete.setValue( "Nothing" )

        # Submit Suspended
        self.submitSuspended = nuke.Boolean_Knob( "Deadline_SubmitSuspended", "Submit Job As Suspended" )
        self.addKnob( self.submitSuspended )
        self.submitSuspended.setTooltip( "If enabled, the job will submit in the suspended state. This is useful if you don't want the job to start rendering right away. Just resume it from the Monitor when you want it to render." )
        self.submitSuspended.setValue( False )

        # Separator
        self.separator1 = nuke.Text_Knob( "Deadline_Separator2", "" )
        self.addKnob( self.separator1 )

        ##########################################################################################
        ## Nuke Options
        ##########################################################################################

        # Frame List
        self.frameListMode = nuke.Enumeration_Knob( "Deadline_FrameListMode", "Frame List", ("Global", "Input", "Custom") )
        self.addKnob( self.frameListMode )
        self.frameListMode.setTooltip( "Select the Global, Input, or Custom frame list mode." )
        self.frameListMode.setValue( "Global" )

        self.frameList = nuke.String_Knob( "Deadline_FrameList", "" )
        self.frameList.clearFlag(nuke.STARTLINE)
        self.addKnob( self.frameList )
        self.frameList.setTooltip( "If Custom frame list mode is selected, this is the list of frames to render." )
        self.frameList.setValue( "" )

        # Chunk Size
        self.chunkSize = nuke.Int_Knob( "Deadline_ChunkSize", "Frames Per Task" )
        self.addKnob( self.chunkSize )
        self.chunkSize.setTooltip( "This is the number of frames that will be rendered at a time for each job task." )
        self.chunkSize.setValue( 10 )

        # NukeX
        self.useNukeX = nuke.Boolean_Knob( "Deadline_UseNukeX", "Render With NukeX" )
        self.addKnob( self.useNukeX )
        self.useNukeX.setTooltip( "If checked, NukeX will be used instead of just Nuke." )
        self.useNukeX.setValue( False )

        # Batch Mode
        self.batchMode = nuke.Boolean_Knob( "Deadline_BatchMode", "Use Batch Mode" )
        self.addKnob( self.batchMode )
        self.batchMode.setTooltip( "This uses the Nuke plugin's Batch Mode. It keeps the Nuke script loaded in memory between frames, which reduces the overhead of rendering the job." )
        self.batchMode.setValue( True )

        # Threads
        self.threads = nuke.Int_Knob( "Deadline_Threads", "Render Threads" )
        self.addKnob( self.threads )
        self.threads.setTooltip( "The number of threads to use for rendering. Set to 0 to have Nuke automatically determine the optimal thread count." )
        self.threads.setValue( 0 )

        # Use GPU
        self.useGpu = nuke.Boolean_Knob( "Deadline_UseGpu", "Use The GPU For Rendering" )
        if int(nuke.env[ 'NukeVersionMajor' ]) >= 7:
            self.addKnob( self.useGpu )
        self.useGpu.setTooltip( "If Nuke should also use the GPU for rendering." )
        self.useGpu.setValue( False )

        # Render Mode
        self.renderMode = nuke.Enumeration_Knob( "Deadline_RenderMode", "Render Mode", dlRenderModes )
        self.addKnob( self.renderMode )
        self.renderMode.setTooltip( "The mode to render with." )
        self.renderMode.setValue( "Use Scene Settings" )

        # Memory Usage
        self.memoryUsage = nuke.Int_Knob( "Deadline_MemoryUsage", "Maximum RAM Usage" )
        self.memoryUsage.setFlag(nuke.STARTLINE)
        self.addKnob( self.memoryUsage )
        self.memoryUsage.setTooltip( "The maximum RAM usage (in MB) to be used for rendering. Set to 0 to not enforce a maximum amount of RAM." )
        self.memoryUsage.setValue( 0 )

        # Enforce Write Node Render Order
        self.enforceRenderOrder = nuke.Boolean_Knob( "Deadline_EnforceRenderOrder", "Enforce Write Node Render Order" )
        self.addKnob( self.enforceRenderOrder )
        self.enforceRenderOrder.setTooltip( "Forces Nuke to obey the render order of Write nodes." )
        self.enforceRenderOrder.setValue( False )

        # Stack Size
        self.stackSize = nuke.Int_Knob( "Deadline_StackSize", "Minimum Stack Size" )
        self.addKnob( self.stackSize )
        self.stackSize.setTooltip( "The minimum stack size (in MB) to be used for rendering. Set to 0 to not enforce a minimum stack size." )
        self.stackSize.setValue( 0 )

        # Continue On Error
        self.continueOnError = nuke.Boolean_Knob( "Deadline_ContinueOnError", "Continue On Error" )
        self.addKnob( self.continueOnError )
        self.continueOnError.setTooltip( "Enable to allow Nuke to continue rendering if it encounters an error." )
        self.continueOnError.setValue( False )

        # Submit Scene
        self.submitScene = nuke.Boolean_Knob( "Deadline_SubmitScene", "Submit Nuke Script File With Job" )
        self.addKnob( self.submitScene )
        self.submitScene.setTooltip( "If this option is enabled, the Nuke script file will be submitted with the job, and then copied locally to the slave machine during rendering." )
        self.submitScene.setValue( False )

        # Performance Profiler
        self.performanceProfiler = nuke.Boolean_Knob( "Deadline_PerformanceProfiler", "Use Performance Profiler" )
        self.performanceProfiler.setFlag(nuke.STARTLINE)
        if int(nuke.env[ 'NukeVersionMajor' ]) >= 9:
            self.addKnob( self.performanceProfiler )
        self.performanceProfiler.setTooltip( "If checked, Nuke will profile the performance of the Nuke script whilst rendering and create a *.xml file per task for later analysis." )
        self.performanceProfiler.setValue( False )

        #Reload Plugin Between Task
        self.reloadPlugin = nuke.Boolean_Knob( "Deadline_ReloadPlugin", "Reload Plugin Between Tasks" )
        self.addKnob( self.reloadPlugin)
        self.reloadPlugin.setTooltip( "If checked, Nuke will force all memory to be released before starting the next task, but this can increase the overhead time between tasks." )
        self.reloadPlugin.setValue( False )

        # Performance Profiler Path
        self.performanceProfilerPath = nuke.File_Knob( "Deadline_PerformanceProfilerDir", "XML Directory" )
        if int(nuke.env[ 'NukeVersionMajor' ]) >= 9:
            self.addKnob( self.performanceProfilerPath )
        self.performanceProfilerPath.setTooltip( "The directory on the network where the performance profile *.xml files will be saved." )
        self.performanceProfilerPath.setValue( "" )
        self.performanceProfilerPath.setEnabled(False)

        # Views
        self.chooseViewsToRender = nuke.Boolean_Knob( "Deadline_ChooseViewsToRender", "Choose Views To Render" )
        self.chooseViewsToRender.setFlag(nuke.STARTLINE)
        self.addKnob( self.chooseViewsToRender)
        self.chooseViewsToRender.setTooltip( "Choose the view(s) you wish to render. This is optional." )

        currentViews = nuke.views()
        self.viewToRenderKnobs = []
        for x, v in enumerate(currentViews):
            currKnob = nuke.Boolean_Knob(('Deadline_ViewToRender_%d' % x), v)
            currKnob.setFlag(0x1000)
            self.viewToRenderKnobs.append((currKnob, v))
            self.addKnob(currKnob)
            currKnob.setValue(True)
            currKnob.setVisible(False) # Hide for now until the checkbox above is enabled.

        # Separator
        self.separator1 = nuke.Text_Knob( "Deadline_Separator3", "" )
        self.addKnob( self.separator1 )

        # Separate Jobs
        self.separateJobs = nuke.Boolean_Knob( "Deadline_SeparateJobs", "Submit Write Nodes As Separate Jobs" )
        self.addKnob( self.separateJobs )
        self.separateJobs.setTooltip( "Enable to submit each write node to Deadline as a separate job." )
        self.separateJobs.setValue( False )

        # Use Node's Frame List
        self.useNodeRange = nuke.Boolean_Knob( "Deadline_UseNodeRange", "Use Node's Frame List" )
        self.addKnob( self.useNodeRange )
        self.useNodeRange.setTooltip( "If submitting each write node as a separate job, enable this to pull the frame range from the write node, instead of using the global frame range." )
        self.useNodeRange.setValue( True )

        #Separate Job Dependencies
        self.separateJobDependencies = nuke.Boolean_Knob( "Deadline_SeparateJobDependencies", "Set Dependencies Based on Write Node Render Order" )
        self.separateJobDependencies.setFlag(nuke.STARTLINE)
        self.addKnob( self.separateJobDependencies )
        self.separateJobDependencies.setTooltip( "Enable each separate job to be dependent on the previous job." )
        self.separateJobDependencies.setValue( False )

        # Separate Tasks
        self.separateTasks = nuke.Boolean_Knob( "Deadline_SeparateTasks", "Submit Write Nodes As Separate Tasks For The Same Job" )
        self.separateTasks.setFlag(nuke.STARTLINE)
        self.addKnob( self.separateTasks )
        self.separateTasks.setTooltip( "Enable to submit a job to Deadline where each task for the job represents a different write node, and all frames for that write node are rendered by its corresponding task." )
        self.separateTasks.setValue( False )

        # Only Submit Selected Nodes
        self.selectedOnly = nuke.Boolean_Knob( "Deadline_SelectedOnly", "Selected Nodes Only" )
        self.selectedOnly.setFlag(nuke.STARTLINE)
        self.addKnob( self.selectedOnly )
        self.selectedOnly.setTooltip( "If enabled, only the selected Write nodes will be rendered." )
        self.selectedOnly.setValue( False )

        # Only Submit Read File Nodes
        self.readFileOnly = nuke.Boolean_Knob( "Deadline_ReadFileOnly", "Nodes With 'Read File' Enabled Only" )
        self.addKnob( self.readFileOnly )
        self.readFileOnly.setTooltip( "If enabled, only the Write nodes that have the 'Read File' option enabled will be rendered." )
        self.readFileOnly.setValue( False )

        # Only Submit Selected Nodes
        self.precompFirst = nuke.Boolean_Knob( "Deadline_PrecompFirst", "Render Precomp Nodes First" )
        self.precompFirst.setFlag(nuke.STARTLINE)
        self.addKnob( self.precompFirst )
        self.precompFirst.setTooltip( "If enabled, all write nodes in precomp nodes will be rendered before the main job." )
        self.precompFirst.setValue( False )

        # Only Submit Read File Nodes
        self.precompOnly = nuke.Boolean_Knob( "Deadline_PrecompOnly", "Only Render Precomp Nodes" )
        self.addKnob( self.precompOnly )
        self.precompOnly.setTooltip( "If enabled, only the Write nodes that are in precomp nodes will be rendered." )
        self.precompOnly.setValue( False )

        ##########################################################################################
        ## Project Management Options (aka Shotgun/FTrack/NIM)
        ##########################################################################################
#
#        self.integrationTab = nuke.Tab_Knob( "Deadline_IntegrationTab", "Integration" )
#        self.addKnob( self.integrationTab )

        # Separator
        self.separator1 = nuke.Text_Knob( "Deadline_Separator100", "" )
        self.addKnob( self.separator1 )

        self.projectManagementCombo = nuke.Enumeration_Knob( "Deadline_PMIntegration", "Project Management", ["Shotgun", "FTrack", "NIM"] )
        self.addKnob( self.projectManagementCombo )
        self.projectManagementCombo.setTooltip( "Select which project management integration to use." )

        self.connectButton = nuke.PyScript_Knob( "Deadline_ConnectButton", "Connect..." )
        self.addKnob( self.connectButton )
        self.connectButton.setTooltip( "Opens the connection window." )

        self.createNewVersion = nuke.Boolean_Knob( "Deadline_CreateNewVersion", "Create New Version" )
        self.addKnob( self.createNewVersion )
        self.createNewVersion.setEnabled( False )
        self.createNewVersion.setTooltip( "If enabled, Deadline will connect to a new Version for this job." )
        self.createNewVersion.setValue( False )

        self.projMgmtVersion = nuke.String_Knob( "Deadline_ProjMgmtVersion", "Version Name" )
        self.addKnob( self.projMgmtVersion )
        self.projMgmtVersion.setEnabled( False )
        self.projMgmtVersion.setTooltip( "The name of the new Version that will be created." )
        self.projMgmtVersion.setValue( "" )

        self.projMgmtDescription = nuke.String_Knob( "Deadline_ProjMgmtDescription", "Version Description" )
        self.addKnob( self.projMgmtDescription )
        self.projMgmtDescription.setEnabled( False )
        self.projMgmtDescription.setTooltip( "The description of the new Version that will be created." )
        self.projMgmtDescription.setValue( "" )

        self.projMgmtInfo = nuke.Multiline_Eval_String_Knob( "Deadline_ProjMgmtInfo", "Selected Entity" )
        self.addKnob( self.projMgmtInfo )
        self.projMgmtInfo.setEnabled( False )
        self.projMgmtInfo.setTooltip( "Miscellaneous information associated with the Version to be created." )
        self.projMgmtDescription.setValue( "" )

        self.draftCreateMovie = nuke.Boolean_Knob( "Deadline_DraftCreateMovie", "Create/Upload Movie" )
        self.addKnob( self.draftCreateMovie )
        self.draftCreateMovie.setValue( False )
        self.draftCreateMovie.setFlag(nuke.STARTLINE)
        self.draftCreateMovie.setEnabled( False )

        self.draftCreateFilmStrip = nuke.Boolean_Knob( "Deadline_DraftCreateFilmStrip", "Create/Upload Film Strip" )
        self.addKnob( self.draftCreateFilmStrip )
        self.draftCreateFilmStrip.setValue( False )
        self.draftCreateFilmStrip.setEnabled( False )

        ##########################################################################################
        ## Draft Options
        ##########################################################################################

        # self.draftTab = nuke.Tab_Knob( "draftTab", "Draft" )
        # self.addKnob( self.draftTab )

        self.draftSeparator1 = nuke.Text_Knob( "Deadline_DraftSeparator1", "" )
        self.addKnob( self.draftSeparator1 )

        self.submitDraftJob = nuke.Boolean_Knob( "Deadline_SubmitDraftJob", "Submit Dependent Draft Job" )
        self.addKnob( self.submitDraftJob )
        self.submitDraftJob.setValue( False )

        self.uploadToShotgun = nuke.Boolean_Knob( "Deadline_UploadToShotgun", "Upload to Shotgun" )
        self.addKnob( self.uploadToShotgun )
        self.uploadToShotgun.setEnabled( False )
        self.uploadToShotgun.setTooltip( "If enabled, the Draft results will be uploaded to Shotgun when it is complete." )
        self.uploadToShotgun.setValue( True )

        self.useQuickDraft = nuke.Boolean_Knob("Deadline_DraftQuick", "Use Quick Draft")
        self.addKnob(self.useQuickDraft)
        self.useQuickDraft.setTooltip( "Whether to use controls to build a quick template options or custom ones." )
        self.useQuickDraft.setEnabled(False)

        self.draftFormat = nuke.Enumeration_Knob("Deadline_DraftFormat", "Format", Formats)
        self.addKnob(self.draftFormat)
        self.draftFormat.setTooltip("The output format used by the Quick Draft submission.")
        self.draftFormat.setEnabled(False)

        selectedFormat = FormatsDict[self.draftFormat.value()][0]
        self.draftCodec = nuke.Enumeration_Knob("Deadline_DraftCodec", "Compression", CodecsDict[selectedFormat])
        self.addKnob(self.draftCodec)
        self.draftCodec.setTooltip("The compression used by the Quick Draft submission.")
        self.draftCodec.setEnabled(False)

        self.draftResolution = nuke.Enumeration_Knob("Deadline_DraftResolution", "Resolution", Resolutions)
        self.addKnob(self.draftResolution)
        self.draftResolution.setTooltip("The resolution used by the Quick Draft submission.")
        self.draftResolution.setEnabled(False)

        self.draftQuality = nuke.Int_Knob("Deadline_DraftQuality", "Quality")
        self.addKnob(self.draftQuality)
        self.draftQuality.setTooltip("The quality used by the Quick Draft submission.")
        self.draftQuality.setEnabled(True)
        self.draftQuality.setValue(85)

        self.draftFrameRate = nuke.Enumeration_Knob("Deadline_DraftFrameRate", "Frame Rate", FrameRates)
        self.addKnob(self.draftFrameRate)
        self.draftFrameRate.setTooltip("The frame rate used by the Quick Draft submission.")
        self.draftFrameRate.setEnabled(False)
        self.draftFrameRate.setValue(24)

        self.templatePath = nuke.File_Knob( "Deadline_TemplatePath", "Draft Template" )
        self.addKnob( self.templatePath )
        self.templatePath.setEnabled( False )
        self.templatePath.setTooltip( "The Draft template file to use." )
        self.templatePath.setValue( "" )

        self.draftUser = nuke.String_Knob( "Deadline_DraftUser", "User" )
        self.addKnob( self.draftUser )
        self.draftUser.setEnabled( False )
        self.draftUser.setTooltip( "The user name used by the Draft template." )
        self.draftUser.setValue( "" )

        self.draftEntity = nuke.String_Knob( "Deadline_DraftEntity", "Entity" )
        self.addKnob( self.draftEntity )
        self.draftEntity.setEnabled( False )
        self.draftEntity.setTooltip( "The entity name used by the Draft template." )
        self.draftEntity.setValue( "" )

        self.draftVersion = nuke.String_Knob( "Deadline_DraftVersion", "Version" )
        self.addKnob( self.draftVersion )
        self.draftVersion.setEnabled( False )
        self.draftVersion.setTooltip( "The version name used by the Draft template." )
        self.draftVersion.setValue( "" )

        self.draftExtraArgs = nuke.String_Knob( "Deadline_DraftExtraArgs", "Additional Args" )
        self.addKnob( self.draftExtraArgs )
        self.draftExtraArgs.setEnabled( False )
        self.draftExtraArgs.setTooltip( "The additional arguments used by the Draft template." )
        self.draftExtraArgs.setValue( "" )

        self.useShotgunDataButton = nuke.PyScript_Knob( "Deadline_UseShotgunDataButton", "Use Shotgun Data" )
        self.useShotgunDataButton.setFlag(nuke.STARTLINE)
        self.addKnob( self.useShotgunDataButton )
        self.useShotgunDataButton.setEnabled( False )
        self.useShotgunDataButton.setTooltip( "Pulls the Draft settings directly from the Shotgun data above (if there is any)." )

        self.pulledFTrackKVPs = getFtrackData()
        if len(self.pulledFTrackKVPs) == 8:
            self.ftrackKVPs = self.pulledFTrackKVPs
            self.pulledFTrackKVPs = {}
        elif len(self.pulledFTrackKVPs) >0:
            self.ftrackKVPs = {}


        ##########################################################################################
        ## HIDE DEFAULT KNOBSSSSS
        ##########################################################################################


#        self.jobName.setVisible(False)
        self.comment.setVisible(False)
        self.department.setVisible(False)
#        self.separator1.setVisible(False)
#        self.pool.setVisible(False)
        self.secondaryPool.setVisible(False)
        self.group.setVisible(False)
        self.priority.setVisible(False)
        self.taskTimeout.setVisible(False)
        self.autoTaskTimeout.setVisible(False)
        self.concurrentTasks.setVisible(False)
        self.limitConcurrentTasks.setVisible(False)
        self.machineLimit.setVisible(False)
        self.isBlacklist.setVisible(False)
        self.machineList.setVisible(False)
        self.machineListButton.setVisible(False)
        self.limitGroups.setVisible(False)
        self.limitGroupsButton.setVisible(False)
        self.dependencies.setVisible(False)
        self.dependenciesButton.setVisible(False)
        self.onComplete.setVisible(False)
        self.submitSuspended .setVisible(False)
#        self.frameListMode.setVisible(False)
#        self.frameList.setVisible(False)
#        self.chunkSize.setVisible(False)
        self.useNukeX.setVisible(False)
        self.batchMode.setVisible(False)
        self.threads.setVisible(False)
        self.useGpu.setVisible(False)
        self.renderMode.setVisible(False)
        self.memoryUsage.setVisible(False)
        self.enforceRenderOrder.setVisible(False)
        self.stackSize.setVisible(False)
        self.continueOnError.setVisible(False)
        self.submitScene.setVisible(False)
        self.performanceProfiler.setVisible(False)
        self.reloadPlugin.setVisible(False)
        self.performanceProfilerPath.setVisible(False)
        self.chooseViewsToRender.setVisible(False)
        self.separator1.setVisible(False)
        self.separateJobs.setVisible(False)
        self.useNodeRange.setVisible(False)
        self.separateJobDependencies.setVisible(False)
        self.separateTasks.setVisible(False)
        self.selectedOnly.setVisible(False)
        self.readFileOnly.setVisible(False)
        self.precompFirst.setVisible(False)
        self.precompOnly.setVisible(False)










#        self.integrationTab.setVisible(False)
#        self.projectManagementCombo.setVisible(False)
#        self.connectButton.setVisible(False)
#        self.createNewVersion.setVisible(False)
#        self.projMgmtVersion.setVisible(False)
#        self.projMgmtDescription.setVisible(False)
#        self.projMgmtInfo.setVisible(False)
#        self.draftCreateMovie.setVisible(False)
#        self.draftCreateFilmStrip.setVisible(False)
#        self.draftSeparator1.setVisible(False)
#        self.submitDraftJob.setVisible(False)
#        self.uploadToShotgun.setVisible(False)
#        self.useQuickDraft.setVisible(False)
#        self.draftFormat.setVisible(False)
#        self.draftCodec.setVisible(False)
#        self.draftResolution.setVisible(False)
#        self.draftQuality.setVisible(False)
#        self.draftFrameRate.setVisible(False)
#        self.templatePath.setVisible(False)
#        self.draftUser.setVisible(False)
#        self.draftEntity.setVisible(False)
#        self.draftVersion.setVisible(False)
#        self.draftExtraArgs.setVisible(False)
#        self.useShotgunDataButton.setVisible(False)

    def ReadInDraftOptions(self):
        global Formats
        global Resolutions
        global FrameRates
        global Restrictions

        # Read in configuration files for Draft drop downs
        mainDraftFolder = GetRepositoryPath("submission/Draft/Main")
        Formats = self.ReadInFormatsFile( os.path.join( mainDraftFolder, "formats.txt" ) )
        Resolutions = self.ReadInResolutionsFile( os.path.join( mainDraftFolder, "resolutions.txt" ) )
        self.ReadInCodecsFile( os.path.join( mainDraftFolder, "codecs.txt" ) )
        FrameRates = self.ReadInFile( os.path.join( mainDraftFolder, "frameRates.txt" ) )

        # Read special restrictions for the list of options
        Restrictions = self.ReadInRestrictionsFile( os.path.join( mainDraftFolder, "restrictions.txt" ) )

    def ReadInFormatsFile( self, filename ):
        global FormatsDict

        results = []
        try:
            for line in open( filename ):
                words = line.split(',')
                name = words[1].strip() + " (" + words[0].strip() + ")"
                results.append( name )
                FormatsDict[name] = [words[0].strip(), words[2].strip()]
            results = filter( None, results )
        except:
            errorMsg = "Failed to read in configuration file " + filename + "."
            print errorMsg
            raise Exception(errorMsg)
        return results

    def ReadInResolutionsFile( self, filename ):
        global ResolutionsDict

        results = []
        try:
            for line in open( filename ):
                words = line.split(',')
                name = words[1].strip()
                results.append( name )
                ResolutionsDict[name] = words[0].strip()
            results = filter( None, results )
        except:
            errorMsg = "Failed to read in configuration file " + filename + "."
            print errorMsg
            raise Exception(errorMsg)
        return results

    def ReadInFile( self, filename ):
        try:
            results = filter( None, [line.strip() for line in open( filename )] )
        except:
            errorMsg = "Failed to read in configuration file " + filename + "."
            print errorMsg
            raise Exception(errorMsg)
        return results

    def ReadInCodecsFile( self, filename ):
        global CodecsDict
        try:
            for line in open( filename ):
                words = line.split( ':' )
                name = words[0].strip()
                codecList = map( str.strip, words[1].split( "," ) )
                if not name in CodecsDict:
                    CodecsDict[name] = {}

                CodecsDict[name] = codecList

        except:
            errorMsg = "Failed to read in configuration file " + filename + "."
            print errorMsg
            raise Exception( errorMsg )

    def ReadInRestrictionsFile( self, filename ):
        global RestrictionsDict
        results = []
        try:
            for line in open( filename ):
                words = line.split( ':' )
                name = words[0].strip()
                restriction = words[1].split( '=' )
                restrictionType = restriction[0].strip()
                restrictionList = map( str.strip, restriction[1].split( "," ) )
                if not name in RestrictionsDict:
                    results.append( name )
                    #RestrictionsDict[name] = [[restrictionType, restrictionList]]
                    RestrictionsDict[name] = {}
                    RestrictionsDict[name][restrictionType] = restrictionList
                else:
                    #RestrictionsDict[name].append([restrictionType, restrictionList])
                    RestrictionsDict[name][restrictionType] = restrictionList
            results = filter( None, results )
        except:
            errorMsg = "Failed to read in configuration file " + filename + "."
            print errorMsg
            raise Exception( errorMsg )
        return results

    def IsMovieFromFormat( self, format ):
        global FormatsDict

        return ( FormatsDict[format][1] == 'movie' )

    def knobChanged( self, knob ):

        if knob == self.machineListButton:
            GetMachineListFromDeadline()

        if knob == self.limitGroupsButton:
            GetLimitGroupsFromDeadline()

        if knob == self.dependenciesButton:
            GetDependenciesFromDeadline()

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

        if knob == self.separateJobs or knob == self.separateTasks:
            self.separateJobs.setEnabled( not self.separateTasks.value() )
            self.separateTasks.setEnabled( not self.separateJobs.value() )

            self.separateJobDependencies.setEnabled( self.separateJobs.value() )
            if not self.separateJobs.value():
                self.separateJobDependencies.setValue( self.separateJobs.value() )

            self.useNodeRange.setEnabled( self.separateJobs.value() or self.separateTasks.value() )
            self.precompFirst.setEnabled( ( self.separateJobs.value() or self.separateTasks.value() ) and not self.precompOnly.value() )
            self.precompOnly.setEnabled( ( self.separateJobs.value() or self.separateTasks.value() ) and not self.precompFirst.value() )

            self.frameList.setEnabled( not (self.separateJobs.value() and self.useNodeRange.value()) and not self.separateTasks.value() )
            self.chunkSize.setEnabled( not self.separateTasks.value() )

        if knob == self.precompFirst or knob == self.precompOnly:
            self.precompFirst.setEnabled( not self.precompOnly.value() )
            self.precompOnly.setEnabled( not self.precompFirst.value() )

        if knob == self.useNodeRange:
            self.frameListMode.setEnabled( not (self.separateJobs.value() and self.useNodeRange.value()) and not self.separateTasks.value() )
            self.frameList.setEnabled( not (self.separateJobs.value() and self.useNodeRange.value()) and not self.separateTasks.value() )

        if knob == self.performanceProfiler:
            self.performanceProfilerPath.setEnabled( self.performanceProfiler.value() )

        if knob == self.chooseViewsToRender:
            visible = self.chooseViewsToRender.value()
            for vk in self.viewToRenderKnobs:
                vk[0].setVisible(visible)

        if knob == self.projectManagementCombo:
            ChangeProjectManager( knob.value() )

        if knob == self.connectButton:
            if self.projectManagementCombo.value() == "Shotgun":
                GetShotgunInfo()
                self.uploadToShotgun.setLabel( "Upload To Shotgun" )
            elif self.projectManagementCombo.value() == "FTrack":
                GetFTrackInfo()
                self.uploadToShotgun.setLabel( "Upload To FTrack" )
            elif self.projectManagementCombo.value() == "NIM":
                GetNimInfo()
                self.uploadToShotgun.setLabel( "Upload To NIM" )

        if knob == self.useShotgunDataButton:
            if self.projectManagementCombo.value() == "Shotgun":
                user = self.shotgunKVPs.get( 'UserName', "" )
                version = self.shotgunKVPs.get( 'VersionName', "" )

                task = self.shotgunKVPs.get( 'TaskName', "" )
                project = self.shotgunKVPs.get( 'ProjectName', "" )
                entity = self.shotgunKVPs.get( 'EntityName', "" )
                draftTemplate = self.shotgunKVPs.get( 'DraftTemplate', "" )

                if task.strip() != "":
                    self.draftEntity.setValue( "%s" % task )
                elif project.strip() != "" and entity.strip() != "":
                    self.draftEntity.setValue( "%s > %s" % (project, entity) )

                if draftTemplate.strip() != "" and draftTemplate != "None":
                    self.templatePath.setValue( draftTemplate )

            elif self.projectManagementCombo.value() == "FTrack":
                user = self.ftrackKVPs.get( 'FT_Username', "" )
                version = self.ftrackKVPs.get( 'FT_AssetName', "" )

                entity = self.ftrackKVPs.get( 'FT_TaskName', "" )
                self.draftEntity.setValue( "%s" % entity )

            elif self.projectManagementCombo.value() == "NIM":
                user = self.nimKVPs.get( 'nim_user', "" )
                version = self.nimKVPs.get( 'nim_renderName', "" )

                task = self.nimKVPs.get( 'nim_taskID', "" )
                asset = self.nimKVPs.get( 'nim_assetName', "" )
                shotName = self.nimKVPs.get( 'nim_shotName', "" )

                entity = ""
                if len(asset) > 0:
                    entity = asset
                elif len(shotName) > 0:
                    entity = shotName

                if len(task) > 0:
                    self.draftEntity.setValue( "%s" % task )
                else:
                    self.draftEntity.setValue( "%s" % entity )

            #set any relevant values
            self.draftUser.setValue( user )
            self.draftVersion.setValue( version )

        if knob == self.projMgmtVersion:
            if self.projectManagementCombo.value() == "Shotgun":
                self.shotgunKVPs['VersionName'] = self.projMgmtVersion.value()

        if knob == self.projMgmtDescription:
            if self.projectManagementCombo.value() == "Shotgun":
                self.shotgunKVPs['Description'] = self.projMgmtDescription.value()
            elif self.projectManagementCombo.value() == "FTrack":
                self.ftrackKVPs['FT_Description'] = self.projMgmtDescription.value()
            elif self.projectManagementCombo.value() == "NIM":
                self.nimKVPs['nim_description'] = self.projMgmtDescription.value()

        if knob == self.createNewVersion:
            #draft controls that require shotgun to be used
            self.uploadToShotgun.setEnabled( self.createNewVersion.value() and self.submitDraftJob.value() )
            self.useShotgunDataButton.setEnabled( self.createNewVersion.value() and self.submitDraftJob.value() )

            shotgunSelected = (self.projectManagementCombo.value() == "Shotgun")
            nimSelected = (self.projectManagementCombo.value() == "NIM")

            self.projMgmtVersion.setEnabled( self.createNewVersion.value() and (shotgunSelected or nimSelected) )
            self.projMgmtDescription.setEnabled( self.createNewVersion.value() )

            dialog.draftCreateMovie.setEnabled(self.createNewVersion.value() )
            dialog.draftCreateFilmStrip.setEnabled(self.createNewVersion.value() and shotgunSelected )

        if knob == self.submitDraftJob:
            self.EnableDraftKnobs()

            self.useShotgunDataButton.setEnabled( self.createNewVersion.value() and self.submitDraftJob.value() )
            self.uploadToShotgun.setEnabled( self.createNewVersion.value() and self.submitDraftJob.value() )

        if knob == self.useQuickDraft:
            self.EnableDraftKnobs()

        if knob == self.draftFormat:
            self.EnableDraftKnobs()
            self.AdjustCodecs()
            self.AdjustFrameRates()

        if knob == self.draftCodec:
            self.AdjustFrameRates()
            self.AdjustQuality()

    def ShowDialog( self ):
        return nukescripts.PythonPanel.showModalDialog( self )

    def EnableDraftKnobs(self):
        isQuick = self.useQuickDraft.value()
        draftCreatesMovie = self.IsMovieFromFormat( self.draftFormat.value() )

        self.useQuickDraft.setEnabled( self.submitDraftJob.value())
        self.templatePath.setEnabled( self.submitDraftJob.value() and not isQuick )
        self.draftUser.setEnabled( self.submitDraftJob.value() and not isQuick)
        self.draftEntity.setEnabled( self.submitDraftJob.value() and not isQuick)
        self.draftVersion.setEnabled( self.submitDraftJob.value() and not isQuick)
        self.draftExtraArgs.setEnabled( self.submitDraftJob.value() and not isQuick)
        self.draftCodec.setEnabled(self.submitDraftJob.value() and isQuick)
        self.draftFormat.setEnabled(self.submitDraftJob.value() and isQuick)
        self.draftFrameRate.setEnabled(self.submitDraftJob.value() and isQuick and draftCreatesMovie)
        self.draftResolution.setEnabled(self.submitDraftJob.value() and isQuick )
        self.AdjustQuality()

    def SetOptions(self, type, options):
        if type == "Codec":
            draftBox = self.draftCodec
        else:
            draftBox = self.draftFrameRate

        selection = draftBox.value()
        draftBox.setValues(options)

        if selection in options:
            draftBox.setValue(selection)
        elif type == "FrameRate":
            draftBox.setValue(24)
        else:
            if draftBox.numValues() > 0:
                value = draftBox.values()[0]
                draftBox.setValue(value)


    def GetOptions( self, selection, selectionType, validOptions):
        global RestrictionsDict

        if selection in RestrictionsDict:
            if selectionType in RestrictionsDict[selection]:
                restrictedOptions = RestrictionsDict[selection][selectionType]
                validOptions = set( validOptions ).intersection( restrictedOptions )
        return list(validOptions)

    def AdjustCodecs( self, *args ):
        global FormatsDict
        global Restrictions
        global FrameRates

        selectedFormat = FormatsDict[self.draftFormat.value()][0]
        validOptions = CodecsDict[selectedFormat]
        validOptions = self.GetOptions( selectedFormat, "Codec", validOptions )

        self.SetOptions("Codec", validOptions)

    def AdjustFrameRates( self, *args ):
        global FormatsDict
        global Restrictions
        global FrameRates

        validOptions = FrameRates

        selectedFormat = FormatsDict[self.draftFormat.value()][0]
        validOptions = self.GetOptions( selectedFormat, "FrameRate", validOptions )

        selectedCodec = self.draftCodec.value()
        validOptions = self.GetOptions( selectedCodec, "FrameRate", validOptions )

        self.SetOptions("FrameRate", validOptions)

    def AdjustQuality( self ):
        draftQuickEnabled = self.useQuickDraft.value()
        selectedFormat = FormatsDict[self.draftFormat.value()][0]
        selectedCodec = self.draftCodec.value()
        draftQualityEnabled = self.ValidQuality( selectedFormat, selectedCodec, "EnableQuality" )

        self.draftQuality.setEnabled(self.submitDraftJob.value() and draftQuickEnabled and draftQualityEnabled)

    def ValidQuality( self, selectedFormat, selectedCodec, enableQuality ):
        global RestrictionsDict
        if selectedFormat in RestrictionsDict:
            if enableQuality in RestrictionsDict[selectedFormat]:
                validQualityCodecs = RestrictionsDict[selectedFormat][enableQuality]
                if selectedCodec in (codec.lower() for codec in validQualityCodecs):
                    return True
        return False

class DeadlineContainerDialog( DeadlineDialog):
    def __init__(self, maximumPriority, pools, secondaryPools, groups, projects, hasComp ):
        super(DeadlineContainerDialog, self).__init__(maximumPriority, pools, secondaryPools, groups)
        self.projects = projects
        self.hasComp = hasComp

        self.studioTab = nuke.Tab_Knob( "Deadline_StudioTab", "Studio Sequence Options" )
        self.addKnob( self.studioTab )

        #If we should submit separate jobs for each comp
        self.submitSequenceJobs = nuke.Boolean_Knob( "Deadline_SubmitSequenceJobs", "Submit Jobs for Comps in Sequence" )
        self.addKnob( self.submitSequenceJobs )
        self.submitSequenceJobs.setValue( False )
        self.submitSequenceJobs.setTooltip("If selected a separate job will be submitted for each comp in the sequence.")

        projectNames = []
        first = ""
        for project in self.projects:
            projectNames.append(str(project.name()))

        #The project
        if len(projectNames) > 0:
            first = str(projectNames[0])
        self.studioProject = nuke.Enumeration_Knob( "Deadline_StudioProject", "Project", projectNames )
        self.addKnob(self.studioProject)
        self.studioProject.setTooltip("The Nuke Studio Project to submit the containers from.")
        self.studioProject.setValue(first)

        #The comps to render
        self.chooseCompsToRender = nuke.Boolean_Knob( "Deadline_ChooseSequencesToRender", "Choose Sequences To Render" )
        self.chooseCompsToRender.setFlag(nuke.STARTLINE)
        self.addKnob( self.chooseCompsToRender)
        self.chooseCompsToRender.setTooltip( "Choose the sequence(s) you wish to render. This is optional." )

        #Get the sequences and their comps
        self.projectSequences = {}
        self.validSequenceNames = []
        self.validComps = {}
        for project in self.projects:
            self.projectSequences[project.name()] = []
            self.validComps[project.name()] = {}
            #This is the current project, grab its sequences
            sequences = project.sequences()
            for sequence in sequences:
                comps = []
                tracks = sequence.binItem().activeItem().items()
                for track in tracks:
                    items = track.items()
                    for item in items:
                        if item.isMediaPresent():
                            infos = item.source().mediaSource().fileinfos()
                            for info in infos:
                                comps.append(info)

                #If there are any comps saved, this is a valid sequence
                self.projectSequences[project.name()].append(sequence.name())
                self.validComps[project.name()][sequence.name()]=comps

        self.sequenceKnobs = []
        for pname in projectNames:
            sequences = self.projectSequences[pname]
            for x, s in enumerate(sequences):
                seqKnob = nuke.Boolean_Knob( ('Deadline_Sequence_%d' % x), s )
                seqKnob.setFlag(nuke.STARTLINE)
                self.sequenceKnobs.append( (seqKnob, (s,pname) ) )
                self.addKnob(seqKnob)
                seqKnob.setValue(True)
                seqKnob.setVisible(False)


    def toggledContainerMode(self):

        self.frameListMode.setEnabled(self.hasComp and (not (self.separateJobs.value() and self.useNodeRange.value()) and not self.separateTasks.value()))
        self.chooseViewsToRender.setEnabled(self.hasComp)
        self.selectedOnly.setEnabled(self.hasComp)
        self.frameList.setEnabled(self.hasComp and (not (self.separateJobs.value() and self.useNodeRange.value()) and not self.separateTasks.value()))
        self.chunkSize.setEnabled(self.hasComp and not self.separateTasks.value())
        self.separateJobs.setEnabled( self.hasComp and not self.separateTasks.value() )
        self.separateTasks.setEnabled( self.hasComp and not self.separateJobs.value() )

        if self.submitSequenceJobs.value():
            self.studioProject.setEnabled(True)
            self.chooseCompsToRender.setEnabled(True)
            for sk in self.sequenceKnobs:
                sk[0].setEnabled(True)
        else:
            self.studioProject.setEnabled(False)
            self.chooseCompsToRender.setEnabled(False)
            for sk in self.sequenceKnobs:
                sk[0].setEnabled(False)


    def knobChanged(self, knob):
        super(DeadlineContainerDialog, self).knobChanged(knob)

        if knob == self.submitSequenceJobs:
            self.toggledContainerMode()

        if knob == self.chooseCompsToRender:
            self.populateSequences()

        if knob == self.studioProject:
            self.populateSequences()

    def populateSequences(self):
        visible = self.chooseCompsToRender.value()
        projectName = self.studioProject.value()

        for sk in self.sequenceKnobs:
            if sk[1][1] == projectName:
                sk[0].setVisible(visible)
            else:
                sk[0].setVisible(False)

    def ShowDialog( self ):
        self.toggledContainerMode()
        return nukescripts.PythonPanel.showModalDialog( self )

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

def GetProjMgmtInfo( scriptPath, additionalArgs=[] ):
    argArray = ["ExecuteScript", scriptPath, "Nuke"]
    for arg in additionalArgs:
        argArray.append(arg)

    output = CallDeadlineCommand( argArray, False )
    outputLines = output.splitlines()

    keyValuePairs = {}

    for line in outputLines:
        line = line.strip()
        if not line.startswith("("):
            tokens = line.split( '=', 1 )

            if len( tokens ) > 1:
                key = tokens[0]
                value = tokens[1]

                keyValuePairs[key] = value

    return keyValuePairs

def getFtrackData():
    # get ftrack data from launched app
    import os
    ftrackData = {}
    try:
        import ftrack
    except:
        return ftrackData

    import json
    import base64

    ftrackConnectVar = os.environ.get('FTRACK_CONNECT_EVENT');
    if ftrackConnectVar is None:
        return ftrackData

    decodedEventData = json.loads(
        base64.b64decode(
            ftrackConnectVar
        )
    )

    try:
        taskId = decodedEventData.get('selection')[0]['entityId']
        user = decodedEventData.get('source')['user']
        task = ftrack.Task(taskId)
    except:
        return ftrackData

    ftrackData["FT_Username"] = user['username']
    ftrackData["FT_TaskName"] = task.getName()
    ftrackData["FT_TaskId"] = task.getId()
    ftrackData["FT_Description"] = task.getDescription()
    try:
        project = task.getProject()
        ftrackData["FT_ProjectName"] = project.getName()
        ftrackData["FT_ProjectId"] = project.getId()
    except:
        pass

    try:
        asset = task.getAssets()[0]
        ftrackData[ "FT_AssetName" ] = asset.getName()
        ftrackData["FT_AssetId"] = asset.getId()
    except:
        pass

    return ftrackData

def GetFTrackInfo():
    global dialog

    ftrackPath = GetRepositoryPath("submission/FTrack/Main")
    ftrackScript = ftrackPath + "/FTrackUI.py"
    additionalArgs = []

    kvps = dialog.ftrackKVPs
    if len(dialog.pulledFTrackKVPs)>0:
        kvps = dialog.pulledFTrackKVPs

    if 'FT_Username' in kvps:
        userName = str(kvps[ 'FT_Username' ])
        if len(userName) > 0 and userName != "":
            additionalArgs.append("UserName="+str(userName))

    if 'FT_TaskName' in kvps:
        taskName = str(kvps[ 'FT_TaskName' ])
        if len(taskName) > 0 and taskName != "":
            additionalArgs.append("TaskName="+str(taskName))

    if 'FT_ProjectName' in kvps:
        projectName = str(kvps[ 'FT_ProjectName' ])
        if len(projectName) > 0 and projectName != "":
            additionalArgs.append("ProjectName="+str(projectName))

    if 'FT_AssetName' in kvps:
        assetName = str(kvps[ 'FT_AssetName' ])
        if len(assetName) > 0 and assetName != "":
            additionalArgs.append("AssetName="+str(assetName))

    tempKVPs = GetProjMgmtInfo( ftrackScript, additionalArgs )

    if len( tempKVPs ) > 0:
        dialog.ftrackKVPs = tempKVPs
        UpdateProjectManagementUI( True )
        dialog.pulledFTrackKVPs = {}

def GetShotgunInfo():
    global dialog

    shotgunPath = GetRepositoryPath("events/Shotgun")
    shotgunScript = shotgunPath + "/ShotgunUI.py"
    additionalArgs = []
    if dialog.shotgunKVPs != None:
        if 'VersionName' in dialog.shotgunKVPs:
            versionValue = str(dialog.shotgunKVPs.get( 'VersionName', "" ))
            if len(versionValue) > 0 and versionValue != "":
                additionalArgs.append("VersionName="+str(versionValue))

        if 'UserName' in dialog.shotgunKVPs:
            userName = str(dialog.shotgunKVPs[ 'UserName' ])
            if len(userName) > 0 and userName != "":
                additionalArgs.append("UserName="+str(userName))

        if 'TaskName' in dialog.shotgunKVPs:
            taskName = str(dialog.shotgunKVPs[ 'TaskName' ])
            if len(taskName) > 0 and taskName != "":
                additionalArgs.append("TaskName="+str(taskName))

        if 'ProjectName' in dialog.shotgunKVPs:
            projectName = str(dialog.shotgunKVPs[ 'ProjectName' ])
            if len(projectName) > 0 and projectName != "":
                additionalArgs.append("ProjectName="+str(projectName))

        if 'EntityName' in dialog.shotgunKVPs:
            entityName = str(dialog.shotgunKVPs[ 'EntityName' ])
            if len(entityName) > 0 and entityName != "":
                additionalArgs.append("EntityName="+str(entityName))

        if 'EntityType' in dialog.shotgunKVPs:
            entityType = str(dialog.shotgunKVPs[ 'EntityType' ])
            if len(entityType) > 0 and entityType != "":
                additionalArgs.append("EntityType="+str(entityType))

    tempKVPs = GetProjMgmtInfo( shotgunScript, additionalArgs )

    if len( tempKVPs ) > 0:
        dialog.shotgunKVPs = tempKVPs
        UpdateProjectManagementUI( True )

##--------------------------------------------------------------
# NIM

def GetNimInfo():
    global dialog

    additionalArgs = []
    if dialog.nimKVPs != None:
        for key in dialog.nimKVPs:
            additionalArgs.append( key + "=" + dialog.nimKVPs[key] )

    nimPath = GetRepositoryPath("events/NIM")
    nimScript = nimPath + "/NIM_UI.py"

    tempKVPs = GetProjMgmtInfo( nimScript, additionalArgs )

    if len( tempKVPs ) > 0:
        dialog.nimKVPs = tempKVPs
        UpdateProjectManagementUI( True )

# END NIM
##-----------------------------------------------------------

def ChangeProjectManager( switchTo ):
    global dialog

    #defaults
    versionLabel = "Version Name"
    descLabel = "Version Description"
    miscLabel = "Selected Entity"
    createVersionLabel = "Create New Version"
    uploadLabel = "Upload to Shotgun"
    uploadTooltip = "If enabled, the Draft results will be uploaded to Shotgun when it is complete."
    useDataLabel = "Use Shotgun Data"

    #integration-specific overrides
    if switchTo == "FTrack":
        versionLabel = "Selected Asset"
        miscLabel = "Miscellaneous Info"
        createVersionLabel = "Create New Version"
        uploadLabel = "Upload to FTrack"
        uploadTooltip = "If enabled, the Draft results will be uploaded to FTrack when it is complete."
        useDataLabel = "Use FTrack Data"

    elif switchTo == "Shotgun":
        versionLabel = "Version Name"
        descLabel = "Version Description"
        miscLabel = "Selected Entity"
        createVersionLabel = "Create New Version"

    elif switchTo == "NIM":
        versionLabel = "Render Name"
        miscLabel = "NIM Data"
        createVersionLabel = "Add NIM Render"
        uploadLabel = "Upload to NIM"
        uploadTooltip = "If enabled, the Draft results will be uploaded to NIM when it is complete."
        useDataLabel = "Use NIM Data"
    else:
        #invalid
        return

    dialog.projMgmtVersion.setLabel( versionLabel )
    dialog.projMgmtDescription.setLabel( descLabel )
    dialog.projMgmtInfo.setLabel( miscLabel )
    dialog.createNewVersion.setLabel( createVersionLabel )

    ##--------------------------------------------------------------
    # NIM

    dialog.uploadToShotgun.setLabel( uploadLabel )
    dialog.uploadToShotgun.setTooltip( uploadTooltip )
    dialog.useShotgunDataButton.setLabel( useDataLabel )

    '''
    # TODO: Fix so Boolean_Knob will refresh the name but remain on current tab
    #dialog.uploadToShotgun.setFlag(nuke.KNOB_CHANGED_RECURSIVE)
    #dialog.uploadToShotgun.clearFlag(nuke.KNOB_CHANGED_RECURSIVE)
    #dialog.integrationTab.clearFlag(nuke.INVISIBLE)
    '''
    # END NIM
    ##--------------------------------------------------------------

    UpdateProjectManagementUI( dialog.createNewVersion.value() )


#Updates the Project Management UI to reflect the contents of the Shotgun/FTrack KVPs
def UpdateProjectManagementUI( forceOn=False ):
    global dialog

    projectManager = dialog.projectManagementCombo.value()

    createValue = False
    createEnabled = False

    versionValue = ""
    versionEnabled = False

    descValue = ""
    descEnabled = False

    infoValue = ""
    infoEnabled = False

    draftIntegrationEnabled = False

    if projectManager == "Shotgun":
        if dialog.shotgunKVPs != None:
            createEnabled = len(dialog.shotgunKVPs) > 0

            if forceOn and createEnabled:
                createValue = True

            versionValue = dialog.shotgunKVPs.get( 'VersionName', "" )
            versionEnabled = createValue
            descValue = dialog.shotgunKVPs.get( 'Description', "" )
            descEnabled = createValue

            if 'UserName' in dialog.shotgunKVPs:
                infoValue += "User Name: %s\n" % dialog.shotgunKVPs[ 'UserName' ]
            if 'TaskName' in dialog.shotgunKVPs:
                infoValue += "Task Name: %s\n" % dialog.shotgunKVPs[ 'TaskName' ]
            if 'ProjectName' in dialog.shotgunKVPs:
                infoValue += "Project Name: %s\n" % dialog.shotgunKVPs[ 'ProjectName' ]
            if 'EntityName' in dialog.shotgunKVPs:
                infoValue += "Entity Name: %s\n" % dialog.shotgunKVPs[ 'EntityName' ]
            if 'EntityType' in dialog.shotgunKVPs:
                infoValue += "Entity Type: %s\n" % dialog.shotgunKVPs[ 'EntityType' ]
            if 'DraftTemplate' in dialog.shotgunKVPs:
                infoValue += "Draft Template: %s\n" % dialog.shotgunKVPs[ 'DraftTemplate' ]

    elif projectManager == "FTrack":
        if dialog.ftrackKVPs:
            createEnabled = True
            createValue = forceOn

            versionValue = dialog.ftrackKVPs.get( 'FT_AssetName', "" )
            descValue = dialog.ftrackKVPs.get( 'FT_Description', "" )
            descEnabled = createValue

            for key in dialog.ftrackKVPs:
                infoValue += "{0}: {1}\n".format( key, dialog.ftrackKVPs[key] )

    elif projectManager == "NIM":
        if dialog.nimKVPs != None:
            createEnabled = len(dialog.nimKVPs) > 0

            if forceOn and createEnabled:
                createValue = True

            versionValue = dialog.nimKVPs.get( 'nim_renderName', "" )
            versionEnabled = createValue
            descValue = dialog.nimKVPs.get( 'nim_description', "" )
            descEnabled = createValue

            if 'nim_useNim' in dialog.nimKVPs:
                infoValue += "Use Nim: %s\n" % dialog.nimKVPs[ 'nim_useNim' ]
            if 'nim_basename' in dialog.nimKVPs:
                infoValue += "Basename: %s\n" % dialog.nimKVPs[ 'nim_basename' ]
            if 'nim_jobName' in dialog.nimKVPs:
                infoValue += "Job Name: %s\n" % dialog.nimKVPs[ 'nim_jobName' ]
            if 'nim_class' in dialog.nimKVPs:
                infoValue += "Class: %s\n" % dialog.nimKVPs[ 'nim_class' ]
            if 'nim_assetName' in dialog.nimKVPs:
                infoValue += "Asset Name: %s\n" % dialog.nimKVPs[ 'nim_assetName' ]
            if 'nim_showName' in dialog.nimKVPs:
                infoValue += "Show Name: %s\n" % dialog.nimKVPs[ 'nim_showName' ]
            if 'nim_shotName' in dialog.nimKVPs:
                infoValue += "Shot Name: %s\n" % dialog.nimKVPs[ 'nim_shotName' ]
            if 'nim_taskID' in dialog.nimKVPs:
                infoValue += "Task ID: %s\n" % dialog.nimKVPs[ 'nim_taskID' ]
            if 'nim_itemID' in dialog.nimKVPs:
                infoValue += "Item ID: %s\n" % dialog.nimKVPs[ 'nim_itemID' ]
            if 'nim_jobID' in dialog.nimKVPs:
                infoValue += "Job ID: %s\n" % dialog.nimKVPs[ 'nim_jobID' ]
            if 'nim_fileID' in dialog.nimKVPs:
                infoValue += "File ID: %s\n" % dialog.nimKVPs[ 'nim_fileID' ]
    else:
        #Invalid...
        pass

    #update the draft stuff that relies on shotgun
    draftIntegrationEnabled = dialog.submitDraftJob.value() and createValue

    dialog.createNewVersion.setValue( createValue )
    dialog.createNewVersion.setEnabled( createEnabled )

    dialog.projMgmtVersion.setValue( versionValue )
    dialog.projMgmtVersion.setEnabled( versionEnabled )

    dialog.projMgmtDescription.setValue( descValue )
    dialog.projMgmtDescription.setEnabled( descEnabled )

    dialog.projMgmtInfo.setValue( infoValue )
    dialog.projMgmtInfo.setEnabled( infoEnabled )

    dialog.draftCreateMovie.setEnabled(versionEnabled )
    dialog.draftCreateFilmStrip.setEnabled(versionEnabled and projectManager == "Shotgun")

    dialog.uploadToShotgun.setEnabled( draftIntegrationEnabled )
    dialog.useShotgunDataButton.setEnabled( draftIntegrationEnabled )


def GetMachineListFromDeadline():
    global dialog
    output = CallDeadlineCommand( ["-selectmachinelist", dialog.machineList.value()], False )
    output = output.replace( "\r", "" ).replace( "\n", "" )
    if output != "Action was cancelled by user":
        dialog.machineList.setValue( output )


def GetLimitGroupsFromDeadline():
    global dialog
    output = CallDeadlineCommand( ["-selectlimitgroups", dialog.limitGroups.value()], False )
    output = output.replace( "\r", "" ).replace( "\n", "" )
    if output != "Action was cancelled by user":
        dialog.limitGroups.setValue( output )

def GetDependenciesFromDeadline():
    global dialog
    output = CallDeadlineCommand( ["-selectdependencies", dialog.dependencies.value()], False )
    output = output.replace( "\r", "" ).replace( "\n", "" )
    if output != "Action was cancelled by user":
        dialog.dependencies.setValue( output )

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

def RightReplace(s, old, new, occurrence):
    li = s.rsplit(old, occurrence)
    return new.join(li)

def StrToBool(str):
    return str.lower() in ("yes", "true", "t", "1", "on")

# Parses through the filename looking for the last padded pattern, replaces
# it with the correct number of #'s, and returns the new padded filename.
def GetPaddedPath( path ):
    # paddingRe = re.compile( "%([0-9]+)d", re.IGNORECASE )

    # paddingMatch = paddingRe.search( path )
    # if paddingMatch != None:
        # paddingSize = int(paddingMatch.lastgroup)

        # padding = ""
        # while len(padding) < paddingSize:
            # padding = padding + "#"

        # path = paddingRe.sub( padding, path, 1 )

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

def buildKnob(name, abr):
    try:
        root = nuke.Root()
        if "Deadline" not in root.knobs():
            tabKnob = nuke.Tab_Knob("Deadline")
            root.addKnob(tabKnob)

        if name in root.knobs():
            return root.knob( name )
        else:
            tKnob = nuke.String_Knob( name, abr )
            root.addKnob ( tKnob )
            return  tKnob
    except:
        print "Error in knob creation. "+ name + " " + abr

def WriteStickySettings( dialog, configFile ):

    try:
        print "Writing sticky settings..."
        config = ConfigParser.ConfigParser()
        config.add_section( "Sticky" )

        config.set( "Sticky", "FrameListMode", dialog.frameListMode.value() )
        config.set( "Sticky", "CustomFrameList", dialog.frameList.value().strip() )

        config.set( "Sticky", "Department", dialog.department.value() )
        config.set( "Sticky", "Pool", dialog.pool.value() )
        config.set( "Sticky", "SecondaryPool", dialog.secondaryPool.value() )
        config.set( "Sticky", "Group", dialog.group.value() )
        config.set( "Sticky", "Priority", str( dialog.priority.value() ) )
        config.set( "Sticky", "MachineLimit", str( dialog.machineLimit.value() ) )
        config.set( "Sticky", "IsBlacklist", str( dialog.isBlacklist.value() ) )
        config.set( "Sticky", "MachineList", dialog.machineList.value() )
        config.set( "Sticky", "LimitGroups", dialog.limitGroups.value() )
        config.set( "Sticky", "SubmitSuspended", str( dialog.submitSuspended.value() ) )
        config.set( "Sticky", "ChunkSize", str( dialog.chunkSize.value() ) )
        config.set( "Sticky", "ConcurrentTasks", str( dialog.concurrentTasks.value() ) )
        config.set( "Sticky", "LimitConcurrentTasks", str( dialog.limitConcurrentTasks.value() ) )
        config.set( "Sticky", "Threads", str( dialog.threads.value() ) )
        config.set( "Sticky", "SubmitScene", str( dialog.submitScene.value() ) )
        config.set( "Sticky", "BatchMode", str( dialog.batchMode.value() ) )
        config.set( "Sticky", "ContinueOnError", str( dialog.continueOnError.value() ) )
        config.set( "Sticky", "UseNodeRange", str( dialog.useNodeRange.value() ) )
        config.set( "Sticky", "UseGpu", str( dialog.useGpu.value() ) )
        config.set( "Sticky", "EnforceRenderOrder", str( dialog.enforceRenderOrder.value() ) )
        config.set( "Sticky", "RenderMode", str(dialog.renderMode.value() ) )
        config.set( "Sticky", "PerformanceProfiler", str(dialog.performanceProfiler.value() ) )
        config.set( "Sticky", "ReloadPlugin", str( dialog.reloadPlugin.value() ) )
        config.set( "Sticky", "PerformanceProfilerPath", dialog.performanceProfilerPath.value() )
        config.set( "Sticky", "CreateUploadMovie", str(dialog.draftCreateMovie.value() ) )
        config.set( "Sticky", "CreateUploadFilmStrip", str(dialog.draftCreateFilmStrip.value() ) )

        config.set( "Sticky", "UseDraft", str( dialog.submitDraftJob.value() ) )
        config.set( "Sticky", "DraftQuick", str( dialog.useQuickDraft.value() ) )
        config.set( "Sticky", "DraftCodec", str( dialog.draftCodec.value() ) )
        config.set( "Sticky", "DraftFormat", str( dialog.draftFormat.value() ) )
        config.set( "Sticky", "DraftFrameRate", str( dialog.draftFrameRate.value() ) )
        config.set( "Sticky", "DraftResolution", str( dialog.draftResolution.value() ) )
        config.set( "Sticky", "DraftQuality", str( dialog.draftQuality.value() ) )
        config.set( "Sticky", "DraftTemplate", dialog.templatePath.value() )
        config.set( "Sticky", "DraftUser", dialog.draftUser.value() )
        config.set( "Sticky", "DraftEntity", dialog.draftEntity.value() )
        config.set( "Sticky", "DraftVersion", dialog.draftVersion.value() )
        config.set( "Sticky", "DraftExtraArgs", dialog.draftExtraArgs.value() )

        config.set( "Sticky", "ProjectManagement", dialog.projectManagementCombo.value() )

        fileHandle = open( unicode( configFile, "utf-8" ), "w" )
        config.write( fileHandle )
        fileHandle.close()
    except:
        print( "Could not write sticky settings" )
        print traceback.format_exc()

    try:
        #Saves all the sticky setting to the root
        tKnob = buildKnob( "FrameListMode" , "frameListMode")
        tKnob.setValue( dialog.frameListMode.value() )

        tKnob = buildKnob( "CustomFrameList", "customFrameList" )
        tKnob.setValue( dialog.frameList.value().strip() )

        tKnob = buildKnob( "Department", "department" )
        tKnob.setValue( dialog.department.value() )

        tKnob = buildKnob( "Pool", "pool" )
        tKnob.setValue( dialog.pool.value() )

        tKnob = buildKnob( "SecondaryPool", "secondaryPool" )
        tKnob.setValue( dialog.secondaryPool.value() )

        tKnob = buildKnob( "Group", "group" )
        tKnob.setValue( dialog.group.value() )

        tKnob = buildKnob( "Priority", "priority" )
        tKnob.setValue( str( dialog.priority.value() ) )

        tKnob = buildKnob( "MachineLimit", "machineLimit" )
        tKnob.setValue( str( dialog.machineLimit.value() ) )

        tKnob = buildKnob( "IsBlacklist", "isBlacklist" )
        tKnob.setValue( str( dialog.isBlacklist.value() ) )

        tKnob = buildKnob( "MachineList", "machineList" )
        tKnob.setValue( dialog.machineList.value() )

        tKnob = buildKnob( "LimitGroups", "limitGroups" )
        tKnob.setValue( dialog.limitGroups.value() )

        tKnob = buildKnob( "SubmitSuspended", "submitSuspended" )
        tKnob.setValue( str( dialog.submitSuspended.value() ) )

        tKnob = buildKnob( "ChunkSize", "chunkSize" )
        tKnob.setValue( str( dialog.chunkSize.value() ) )

        tKnob = buildKnob( "ConcurrentTasks", "concurrentTasks" )
        tKnob.setValue( str( dialog.concurrentTasks.value() ) )

        tKnob = buildKnob( "LimitConcurrentTasks", "limitConcurrentTasks" )
        tKnob.setValue( str( dialog.limitConcurrentTasks.value() ) )

        tKnob = buildKnob( "Threads", "threads" )
        tKnob.setValue( str( dialog.threads.value() ) )

        tKnob = buildKnob( "SubmitScene", "submitScene" )
        tKnob.setValue( str( dialog.submitScene.value() ) )

        tKnob = buildKnob( "BatchMode", "batchMode" )
        tKnob.setValue( str( dialog.batchMode.value() ) )

        tKnob = buildKnob( "ContinueOnError", "continueOnError" )
        tKnob.setValue( str( dialog.continueOnError.value() ) )

        tKnob = buildKnob( "UseNodeRange", "useNodeRange" )
        tKnob.setValue( str( dialog.useNodeRange.value() ) )

        tKnob = buildKnob( "UseGpu", "useGpu" )
        tKnob.setValue( str( dialog.useGpu.value() ) )

        tKnob = buildKnob( "EnforceRenderOrder", "enforceRenderOrder" )
        tKnob.setValue( str( dialog.enforceRenderOrder.value() ) )

        tKnob = buildKnob( "DeadlineRenderMode", "deadlineRenderMode" )
        tKnob.setValue( str( dialog.renderMode.value() ) )

        tKnob = buildKnob( "PerformanceProfiler", "performanceProfiler" )
        tKnob.setValue( str( dialog.performanceProfiler.value() ) )

        tKnob = buildKnob( "ReloadPlugin", "reloadPlugin" )
        tKnob.setValue( str( dialog.reloadPlugin.value() ) )

        tKnob = buildKnob( "PerformanceProfilerPath", "performanceProfilerPath" )
        tKnob.setValue( dialog.performanceProfilerPath.value() )

        tKnob = buildKnob( "CreateUploadMovie", "createUploadMovie" )
        tKnob.setValue( str( dialog.draftCreateMovie.value() ) )

        tKnob = buildKnob( "CreateUploadFilmStrip", "createUploadFilmStrip" )
        tKnob.setValue( str( dialog.draftCreateFilmStrip.value() ) )

        tKnob = buildKnob( "UseDraft", "useDraft" )
        tKnob.setValue( str( dialog.submitDraftJob.value() ) )

        tKnob = buildKnob( "DraftQuick", "draftQuick" )
        tKnob.setValue( str( dialog.useQuickDraft.value() ) )

        tKnob = buildKnob( "DraftCodec", "draftCodec" )
        tKnob.setValue( str( dialog.draftCodec.value() ) )

        tKnob = buildKnob( "DraftFormat", "draftFormat" )
        tKnob.setValue( str( dialog.draftFormat.value() ) )

        tKnob = buildKnob( "DraftFrameRate", "draftFrameRate" )
        tKnob.setValue( str( dialog.draftFrameRate.value() ) )

        tKnob = buildKnob( "DraftResolution", "draftResolution" )
        tKnob.setValue( str( dialog.draftResolution.value() ) )

        tKnob = buildKnob( "DraftQuality", "draftQuality" )
        tKnob.setValue( str( dialog.draftQuality.value() ) )

        tKnob = buildKnob( "DraftTemplate", "draftTemplate" )
        tKnob.setValue( dialog.templatePath.value() )

        tKnob = buildKnob( "DraftUser", "draftUser" )
        tKnob.setValue( dialog.draftUser.value() )

        tKnob = buildKnob( "DraftEntity", "draftEntity" )
        tKnob.setValue( dialog.draftEntity.value() )

        tKnob = buildKnob( "DraftVersion", "draftVersion" )
        tKnob.setValue( dialog.draftVersion.value() )

        tKnob = buildKnob( "DraftExtraArgs", "draftExtraArgs" )
        tKnob.setValue( dialog.draftExtraArgs.value() )

        tKnob = buildKnob( "ProjectManagement", "projectManagement")
        tKnob.setValue( dialog.projectManagementCombo.value() )

        tKnob = buildKnob( "DeadlineSGData", "shotgunKVPs" )
        tKnob.setValue( str(dialog.shotgunKVPs) )

        tKnob = buildKnob( "DeadlineFTData", "ftrackKVPs" )
        tKnob.setValue( str(dialog.ftrackKVPs) )

        tKnob = buildKnob( "DeadlineNIMData", "nimKVPs" )
        tKnob.setValue( str(dialog.nimKVPs) )
        # If the Nuke script has been modified, then save it to preserve SG settings.
        root = nuke.Root()
        if root.modified():
            if root.name() != "Root":
                nuke.scriptSave( root.name() )

    except:
        print( "Could not write knob settings." )
        print traceback.format_exc()

def SubmitSequenceJobs(dialog, deadlineTemp, tempDependencies, semaphore, extraInfo):
    global ResolutionsDict
    global FormatsDict
    projectName = dialog.studioProject.value()
    #Get the comps that will be submitted for the project selected in the dialog
    comps = dialog.validComps[projectName]

    node = None

    #Get the sequences that will be submitted
    sequenceKnobs = dialog.sequenceKnobs
    allSequences = not dialog.chooseCompsToRender.value()

    sequences = []
    for knobTuple in sequenceKnobs:
        if knobTuple[1][1] == projectName:
            if not allSequences:
                if knobTuple[0].value():
                    sequences.append(knobTuple[1][0])
            else:
                sequences.append(knobTuple[1][0])

    allComps = []
    for sequence in sequences:
        for comp in comps[sequence]:
            allComps.append(comp)

    batchName = str(str(dialog.jobName.value())+" ("+projectName + ")")

    jobCount = len(allComps)
    currentJobIndex = 1

    previousJobId = ""
    #Submit all comps in each sequence
    for sequence in sequences:
        compNum = 1
        for comp in comps[sequence]:
            print "Preparing job #%d for submission.." % currentJobIndex

            progressTask = nuke.ProgressTask("Job Submission")
            progressTask.setMessage("Creating Job Info File")
            progressTask.setProgress(0)
            if len(comps[sequence]) > 1:
                name = sequence + " - Comp "+str(compNum)
            else:
                name = sequence

            if dialog.separateJobDependencies.value():
                if len(previousJobId) > 1 and jobCount > 1 and not tempDependencies == "":
                    tempDependencies = tempDependencies + "," + previousJobId
                elif tempDependencies == "":
                    tempDependencies = previousJobId

            # Create the submission info file (append job count since we're submitting multiple jobs at the same time in different threads)
            jobInfoFile = unicode(deadlineTemp, "utf-8") + (u"/nuke_submit_info%d.job" % currentJobIndex)
            fileHandle = open( jobInfoFile, "w" )
            fileHandle.write( "Plugin=Nuke\n" )
            fileHandle.write( "Name=%s\n" % str(str(dialog.jobName.value())+"("+name+")") )
            fileHandle.write( "Comment=%s\n" % dialog.comment.value() )
            fileHandle.write( "Department=%s\n" % dialog.department.value() )
            fileHandle.write( "Pool=%s\n" % dialog.pool.value() )
            if dialog.secondaryPool.value() == "":
                fileHandle.write( "SecondaryPool=\n" )
            else:
                fileHandle.write( "SecondaryPool=%s\n" % dialog.secondaryPool.value() )
            fileHandle.write( "Group=%s\n" % dialog.group.value() )
            fileHandle.write( "Priority=%s\n" % dialog.priority.value() )
            fileHandle.write( "MachineLimit=%s\n" % dialog.machineLimit.value() )
            fileHandle.write( "TaskTimeoutMinutes=%s\n" % dialog.taskTimeout.value() )
            fileHandle.write( "EnableAutoTimeout=%s\n" % dialog.autoTaskTimeout.value() )
            fileHandle.write( "ConcurrentTasks=%s\n" % dialog.concurrentTasks.value() )
            fileHandle.write( "LimitConcurrentTasksToNumberOfCpus=%s\n" % dialog.limitConcurrentTasks.value() )
            fileHandle.write( "LimitGroups=%s\n" % dialog.limitGroups.value() )
            fileHandle.write( "JobDependencies=%s\n" %  tempDependencies)
            fileHandle.write( "OnJobComplete=%s\n" % dialog.onComplete.value() )

            tempFrameList = str(int(comp.startFrame())) + "-" + str(int(comp.endFrame()))

            fileHandle.write( "Frames=%s\n" % tempFrameList )
            fileHandle.write( "ChunkSize=1\n" )

            if dialog.submitSuspended.value():
                fileHandle.write( "InitialStatus=Suspended\n" )

            if dialog.isBlacklist.value():
                fileHandle.write( "Blacklist=%s\n" % dialog.machineList.value() )
            else:
                fileHandle.write( "Whitelist=%s\n" % dialog.machineList.value() )

            #NOTE: We're not writing out NIM/FTrack/Shotgun or Draft extra info here because we do not have a defined output file to operate on in this case.

            if jobCount > 1:
                fileHandle.write( "BatchName=%s\n" % batchName )

            fileHandle.close()

            # Update task progress
            progressTask.setMessage("Creating Plugin Info File")
            progressTask.setProgress(10)

            # Create the plugin info file
            pluginInfoFile = unicode( deadlineTemp, "utf-8" ) + (u"/nuke_plugin_info%d.job" % currentJobIndex)
            fileHandle = open( pluginInfoFile, "w" )
            fileHandle.write( "SceneFile=%s\n" % comp.filename() )
            fileHandle.write( "Version=%s.%s\n" % (nuke.env[ 'NukeVersionMajor' ], nuke.env['NukeVersionMinor']) )
            fileHandle.write( "Threads=%s\n" % dialog.threads.value() )
            fileHandle.write( "RamUse=%s\n" % dialog.memoryUsage.value() )
            fileHandle.write( "BatchMode=%s\n" % dialog.batchMode.value())
            fileHandle.write( "BatchModeIsMovie=%s\n" % False )

            fileHandle.write( "NukeX=%s\n" % dialog.useNukeX.value() )

            if int(nuke.env[ 'NukeVersionMajor' ]) >= 7:
                fileHandle.write( "UseGpu=%s\n" % dialog.useGpu.value() )

            fileHandle.write( "RenderMode=%s\n" % dialog.renderMode.value() )
            fileHandle.write( "EnforceRenderOrder=%s\n" % dialog.enforceRenderOrder.value() )
            fileHandle.write( "ContinueOnError=%s\n" % dialog.continueOnError.value() )

            if int(nuke.env[ 'NukeVersionMajor' ]) >= 9:
                fileHandle.write( "PerformanceProfiler=%s\n" % dialog.performanceProfiler.value() )
                fileHandle.write( "PerformanceProfilerDir=%s\n" % dialog.performanceProfilerPath.value() )

            fileHandle.write( "StackSize=%s\n" % dialog.stackSize.value() )
            fileHandle.close()

            # Update task progress
            progressTask.setMessage("Submitting Job %d to Deadline" % currentJobIndex)
            progressTask.setProgress(30)

            # Submit the job to Deadline
            args = []
            args.append( jobInfoFile.encode(locale.getpreferredencoding() ) )
            args.append( pluginInfoFile.encode(locale.getpreferredencoding() ) )
            args.append( comp.filename() )

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

            print "Job submission #%d complete" % currentJobIndex

            # If submitting multiple jobs, just print the results to the console, otherwise show them to the user.
            if semaphore:
                print tempResults
            else:
                nuke.executeInMainThread( nuke.message, tempResults )

            currentJobIndex = currentJobIndex + 1
            compNum = compNum + 1

            for line in tempResults.splitlines():
                if line.startswith("JobID="):
                    previousJobId = line[6:]
                    break

    nuke.executeInMainThread( nuke.message, "Sequence Job Submission complete. "+str(jobCount)+" Job(s) submitted to Deadline." )

def EncodeAsUTF16String( unicodeString ):
    return unicodeString.decode( "utf-8" ).encode( "utf-16-le" )

def SubmitJob( dialog, root, node, writeNodes, deadlineTemp, tempJobName, tempFrameList, tempDependencies, tempChunkSize, tempIsMovie, jobCount, semaphore,  extraInfo ):
    global ResolutionsDict
    global FormatsDict

    viewsToRender = []
    if dialog.chooseViewsToRender.value():
        for vk in dialog.viewToRenderKnobs:
            if vk[0].value():
                viewsToRender.append(vk[1])
    else:
        viewsToRender = nuke.views()


    print "Preparing job #%d for submission.." % jobCount

    # Create a task in Nuke's progress  bar dialog
    #progressTask = nuke.ProgressTask("Submitting %s to Deadline" % tempJobName)
    progressTask = nuke.ProgressTask("Job Submission")
    progressTask.setMessage("Creating Job Info File")
    progressTask.setProgress(0)

    batchName = dialog.jobName.value()
    # Create the submission info file (append job count since we're submitting multiple jobs at the same time in different threads)
    jobInfoFile = unicode(deadlineTemp, "utf-8") + (u"/nuke_submit_info%d.job" % jobCount)
    fileHandle = open( jobInfoFile, "wb" )
    fileHandle.write( EncodeAsUTF16String( "Plugin=Nuke\n" ) )
    fileHandle.write( EncodeAsUTF16String( "Name=%s\n" % tempJobName ) )
    fileHandle.write( EncodeAsUTF16String( "Comment=%s\n" % dialog.comment.value() ) )
    fileHandle.write( EncodeAsUTF16String( "Department=%s\n" % dialog.department.value() ) )
    fileHandle.write( EncodeAsUTF16String( "Pool=%s\n" % dialog.pool.value() ) )
    if dialog.secondaryPool.value() == "":
        fileHandle.write( EncodeAsUTF16String( "SecondaryPool=\n" ) )
    else:
        fileHandle.write( EncodeAsUTF16String( "SecondaryPool=%s\n" % dialog.secondaryPool.value() ) )
    fileHandle.write( EncodeAsUTF16String( "Group=%s\n" % dialog.group.value() ) )
    fileHandle.write( EncodeAsUTF16String( "Priority=%s\n" % dialog.priority.value() ) )
    fileHandle.write( EncodeAsUTF16String( "MachineLimit=%s\n" % dialog.machineLimit.value() ) )
    fileHandle.write( EncodeAsUTF16String( "TaskTimeoutMinutes=%s\n" % dialog.taskTimeout.value() ) )
    fileHandle.write( EncodeAsUTF16String( "EnableAutoTimeout=%s\n" % dialog.autoTaskTimeout.value() ) )
    fileHandle.write( EncodeAsUTF16String( "ConcurrentTasks=%s\n" % dialog.concurrentTasks.value() ) )
    fileHandle.write( EncodeAsUTF16String( "LimitConcurrentTasksToNumberOfCpus=%s\n" % dialog.limitConcurrentTasks.value() ) )
    fileHandle.write( EncodeAsUTF16String( "LimitGroups=%s\n" % dialog.limitGroups.value() ) )
    fileHandle.write( EncodeAsUTF16String( "JobDependencies=%s\n" %  tempDependencies ) )
    fileHandle.write( EncodeAsUTF16String( "OnJobComplete=%s\n" % dialog.onComplete.value() ) )
    fileHandle.write( EncodeAsUTF16String( "ForceReloadPlugin=%s\n" % dialog.reloadPlugin.value() ) )

    if dialog.separateTasks.value():
        writeNodeCount = 0
        for tempNode in writeNodes:
            if not tempNode.knob( 'disable' ).value():
                enterLoop = True
                if dialog.readFileOnly.value() and tempNode.knob( 'reading' ):
                    enterLoop = enterLoop and tempNode.knob( 'reading' ).value()
                if dialog.selectedOnly.value():
                    enterLoop = enterLoop and IsNodeOrParentNodeSelected(tempNode)

                if enterLoop:
                    writeNodeCount += 1


        fileHandle.write( EncodeAsUTF16String( "Frames=0-%s\n" % (writeNodeCount-1) ) )
        fileHandle.write( EncodeAsUTF16String( "ChunkSize=1\n" ) )
    else:
        fileHandle.write( EncodeAsUTF16String( "Frames=%s\n" % tempFrameList ) )
        fileHandle.write( EncodeAsUTF16String( "ChunkSize=%s\n" % tempChunkSize ) )

    if dialog.submitSuspended.value():
        fileHandle.write( EncodeAsUTF16String( "InitialStatus=Suspended\n" ) )

    if dialog.isBlacklist.value():
        fileHandle.write( EncodeAsUTF16String( "Blacklist=%s\n" % dialog.machineList.value() ) )
    else:
        fileHandle.write( EncodeAsUTF16String( "Whitelist=%s\n" % dialog.machineList.value() ) )

    extraKVPIndex = 0

    index = 0

    for v in viewsToRender:
        if dialog.separateJobs.value():

            #gets the filename/proxy filename and evaluates TCL + vars, but *doesn't* swap frame padding
            fileValue = nuke.filename( node )

            if ( root.proxy() and node.knob( 'proxy' ).value() != "" ):
                evaluatedValue = node.knob( 'proxy' ).evaluate(view=v)
            else:
                evaluatedValue = node.knob( 'file' ).evaluate(view=v)

            if fileValue != None and fileValue != "" and evaluatedValue != None and evaluatedValue != "":
                tempPath, tempFilename = os.path.split( evaluatedValue )
                if IsPadded( os.path.basename( fileValue ) ):
                    tempFilename = GetPaddedPath( tempFilename )

                paddedPath = os.path.join( tempPath, tempFilename )
                #Handle cases where file name might start with an escape character
                paddedPath = paddedPath.replace( "\\", "/" )

                fileHandle.write( EncodeAsUTF16String( "OutputFilename%i=%s\n" % ( index, paddedPath ) ) )

                #Check if the Write Node will be modifying the output's Frame numbers
                if node.knob( 'frame_mode' ):
                    if ( node.knob( 'frame_mode' ).value() == "offset" ):
                        fileHandle.write( EncodeAsUTF16String( "ExtraInfoKeyValue%d=OutputFrameOffset%i=%s\n" % ( extraKVPIndex,index, str( int( node.knob( 'frame' ).value() ) ) ) ) )
                        extraKVPIndex += 1
                    elif ( node.knob( 'frame_mode' ).value() == "start at" or node.knob( 'frame_mode' ).value() == "start_at"):
                        franges = nuke.FrameRanges( tempFrameList )
                        fileHandle.write( EncodeAsUTF16String( "ExtraInfoKeyValue%d=OutputFrameOffset%i=%s\n" % ( extraKVPIndex,index, str( int( node.knob( 'frame' ).value() ) - franges.minFrame() ) ) ) )
                        extraKVPIndex += 1
                    else:
                        #TODO: Handle 'expression'? Would be much harder
                        pass
                index+=1
        else:
            for tempNode in writeNodes:
                if not tempNode.knob( 'disable' ).value():
                    enterLoop = True
                    if dialog.readFileOnly.value() and tempNode.knob( 'reading' ):
                        enterLoop = enterLoop and tempNode.knob( 'reading' ).value()
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

                            if dialog.separateTasks.value():
                                fileHandle.write( EncodeAsUTF16String( "OutputDirectory%s=%s\n" % ( index, tempPath ) ) )
                            else:
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
    groupBatch = False
    if dialog.createNewVersion.value():
        if dialog.projectManagementCombo.value() == "Shotgun":

            if 'TaskName' in dialog.shotgunKVPs:
                fileHandle.write( EncodeAsUTF16String( "ExtraInfo0=%s\n" % dialog.shotgunKVPs['TaskName'] ) )

            if 'ProjectName' in dialog.shotgunKVPs:
                fileHandle.write( EncodeAsUTF16String( "ExtraInfo1=%s\n" % dialog.shotgunKVPs['ProjectName'] ) )

            if 'EntityName' in dialog.shotgunKVPs:
                fileHandle.write( EncodeAsUTF16String( "ExtraInfo2=%s\n" % dialog.shotgunKVPs['EntityName'] ) )

            if 'VersionName' in dialog.shotgunKVPs:
                fileHandle.write( EncodeAsUTF16String( "ExtraInfo3=%s\n" % dialog.shotgunKVPs['VersionName'] ) )

            if 'Description' in dialog.shotgunKVPs:
                fileHandle.write( EncodeAsUTF16String( "ExtraInfo4=%s\n" % dialog.shotgunKVPs['Description'] ) )

            if 'UserName' in dialog.shotgunKVPs:
                fileHandle.write( EncodeAsUTF16String( "ExtraInfo5=%s\n" % dialog.shotgunKVPs['UserName'] ) )

            #dump the rest in as KVPs
            for key in dialog.shotgunKVPs:
                if key != "DraftTemplate":
                    fileHandle.write( EncodeAsUTF16String( "ExtraInfoKeyValue%d=%s=%s\n" % ( extraKVPIndex, key, dialog.shotgunKVPs[key] ) ) )
                    extraKVPIndex += 1

            if dialog.draftCreateMovie.value():
                fileHandle.write( EncodeAsUTF16String( "ExtraInfoKeyValue%s=Draft_CreateSGMovie=True\n" % extraKVPIndex ) )
                extraKVPIndex += 1
                groupBatch = True

            if dialog.draftCreateFilmStrip.value():
                fileHandle.write( EncodeAsUTF16String( "ExtraInfoKeyValue%s=Draft_CreateSGFilmstrip=True\n" % extraKVPIndex ) )
                extraKVPIndex += 1
                groupBatch = True


        elif dialog.projectManagementCombo.value() == "FTrack":

            if 'FT_TaskName' in dialog.ftrackKVPs:
                fileHandle.write( EncodeAsUTF16String( "ExtraInfo0=%s\n" % dialog.ftrackKVPs['FT_TaskName'] ) )

            if 'FT_ProjectName' in dialog.ftrackKVPs:
                fileHandle.write( EncodeAsUTF16String( "ExtraInfo1=%s\n" % dialog.ftrackKVPs['FT_ProjectName'] ) )

            if 'FT_AssetName' in dialog.ftrackKVPs:
                fileHandle.write( EncodeAsUTF16String( "ExtraInfo2=%s\n" % dialog.ftrackKVPs['FT_AssetName'] ) )

            #will update Version # in EI3 when it gets created

            if 'FT_Description' in dialog.ftrackKVPs:
                fileHandle.write( EncodeAsUTF16String( "ExtraInfo4=%s\n" % dialog.ftrackKVPs['FT_Description'] ) )

            if 'FT_Username' in dialog.ftrackKVPs:
                fileHandle.write( EncodeAsUTF16String( "ExtraInfo5=%s\n" % dialog.ftrackKVPs['FT_Username'] ) )

            for key in dialog.ftrackKVPs:
                fileHandle.write( EncodeAsUTF16String( "ExtraInfoKeyValue%d=%s=%s\n" % ( extraKVPIndex, key, dialog.ftrackKVPs[key] ) ) )
                extraKVPIndex += 1

            if dialog.draftCreateMovie.value():
                fileHandle.write( EncodeAsUTF16String( "ExtraInfoKeyValue%s=Draft_CreateFTMovie=True\n" % (extraKVPIndex) ) )
                extraKVPIndex += 1
                groupBatch = True

        elif dialog.projectManagementCombo.value() == "NIM":

            if 'nim_renderName' in dialog.nimKVPs:
                fileHandle.write( EncodeAsUTF16String( "ExtraInfo0=%s\n" % dialog.nimKVPs['nim_renderName'] ) )

            if 'nim_jobName' in dialog.nimKVPs:
                fileHandle.write( EncodeAsUTF16String( "ExtraInfo1=%s\n" % dialog.nimKVPs['nim_jobName'] ) )

            if 'nim_showName' in dialog.nimKVPs:
                fileHandle.write( EncodeAsUTF16String( "ExtraInfo2=%s\n" % dialog.nimKVPs['nim_showName'] ) )

            if 'nim_shotName' in dialog.nimKVPs:
                fileHandle.write( EncodeAsUTF16String( "ExtraInfo3=%s\n" % dialog.nimKVPs['nim_shotName'] ) )

            if 'nim_description' in dialog.nimKVPs:
                fileHandle.write( EncodeAsUTF16String( "ExtraInfo4=%s\n" % dialog.nimKVPs['nim_description'] ) )

            if 'nim_user' in dialog.nimKVPs:
                fileHandle.write( EncodeAsUTF16String( "ExtraInfo5=%s\n" % dialog.nimKVPs['nim_user'] ) )

            #dump the rest in as KVPs
            for key in dialog.nimKVPs:
                fileHandle.write( EncodeAsUTF16String( "ExtraInfoKeyValue%d=%s=%s\n" % (extraKVPIndex, key, dialog.nimKVPs[key]) ) )
                extraKVPIndex += 1

            if dialog.draftCreateMovie.value():
                fileHandle.write( EncodeAsUTF16String( "ExtraInfoKeyValue%s=Draft_CreateNimMovie=True\n" % (extraKVPIndex) ) )
                extraKVPIndex += 1
                groupBatch = True
    else:

        for i in range (0, 6):
            fileHandle.write( EncodeAsUTF16String( "ExtraInfo%d=%s\n" % ( i, extraInfo[ i ] ) ) )

    for i in range (6, 10):
        fileHandle.write( EncodeAsUTF16String( "ExtraInfo%d=%s\n" % ( i, extraInfo[ i ] ) ) )

    #Draft stuff
    if dialog.submitDraftJob.value():
        draftNode = node
        #TODO: Need to figure out if we want to do something else in this case (all write nodes being submitted in one job)
        if node == None:
            draftNode = writeNodes[0]

        if dialog.useQuickDraft.value():
            fileHandle.write( EncodeAsUTF16String( "ExtraInfoKeyValue%d=SubmitQuickDraft=True\n" % (extraKVPIndex) ) )
            extraKVPIndex += 1
            fileHandle.write( EncodeAsUTF16String( "ExtraInfoKeyValue%d=DraftExtension=%s\n" % (extraKVPIndex, FormatsDict[dialog.draftFormat.value()][0]) ) )
            extraKVPIndex += 1
            fileHandle.write( EncodeAsUTF16String( "ExtraInfoKeyValue%d=DraftType=%s\n" % (extraKVPIndex, FormatsDict[dialog.draftFormat.value()][1]) ) )
            extraKVPIndex += 1
            fileHandle.write( EncodeAsUTF16String( "ExtraInfoKeyValue%d=DraftResolution=%s\n" % (extraKVPIndex, ResolutionsDict[dialog.draftResolution.value()]) ) )
            extraKVPIndex += 1
            fileHandle.write( EncodeAsUTF16String( "ExtraInfoKeyValue%d=DraftCodec=%s\n" % (extraKVPIndex, dialog.draftCodec.value() ) ) )
            extraKVPIndex += 1
            fileHandle.write( EncodeAsUTF16String( "ExtraInfoKeyValue%d=DraftQuality=%s\n" % (extraKVPIndex, dialog.draftQuality.value() ) ) )
            extraKVPIndex += 1
            fileHandle.write( EncodeAsUTF16String( "ExtraInfoKeyValue%d=DraftFrameRate=%s\n" % (extraKVPIndex, dialog.draftFrameRate.value() ) ) )
            extraKVPIndex += 1
        else:
            fileHandle.write( EncodeAsUTF16String( "ExtraInfoKeyValue%d=DraftTemplate=%s\n" % (extraKVPIndex, dialog.templatePath.value() ) ) )
            extraKVPIndex += 1
            fileHandle.write( EncodeAsUTF16String( "ExtraInfoKeyValue%d=DraftUsername=%s\n" % (extraKVPIndex, dialog.draftUser.value() ) ) )
            extraKVPIndex += 1
            fileHandle.write( EncodeAsUTF16String( "ExtraInfoKeyValue%d=DraftEntity=%s\n" % (extraKVPIndex, dialog.draftEntity.value()) ) )
            extraKVPIndex += 1
            fileHandle.write( EncodeAsUTF16String( "ExtraInfoKeyValue%d=DraftVersion=%s\n" % (extraKVPIndex, dialog.draftVersion.value()) ) )
            extraKVPIndex += 1
            fileHandle.write( EncodeAsUTF16String( "ExtraInfoKeyValue%d=DraftFrameWidth=%s\n" % (extraKVPIndex, draftNode.width()) ) )
            extraKVPIndex += 1
            fileHandle.write( EncodeAsUTF16String( "ExtraInfoKeyValue%d=DraftFrameHeight=%s\n" % (extraKVPIndex, draftNode.height()) ) )
            extraKVPIndex += 1
            fileHandle.write( EncodeAsUTF16String( "ExtraInfoKeyValue%d=DraftExtraArgs=%s\n" % (extraKVPIndex, dialog.draftExtraArgs.value()) ) )
            extraKVPIndex += 1

        if dialog.projectManagementCombo.value() == "Shotgun":
            fileHandle.write( EncodeAsUTF16String( "ExtraInfoKeyValue%d=DraftUploadToShotgun=%s\n" % (extraKVPIndex, str(dialog.uploadToShotgun.enabled() and dialog.uploadToShotgun.value())) ) )
            extraKVPIndex += 1
        elif dialog.projectManagementCombo.value() == "FTrack":
            fileHandle.write( EncodeAsUTF16String( "ExtraInfoKeyValue%d=FT_DraftUploadMovie=%s\n" % (extraKVPIndex, str(dialog.uploadToShotgun.enabled() and dialog.uploadToShotgun.value())) ) )
            extraKVPIndex += 1
        elif dialog.projectManagementCombo.value() == "NIM":
            fileHandle.write( EncodeAsUTF16String( "ExtraInfoKeyValue%d=DraftUploadToNim=%s\n" % (extraKVPIndex, str(dialog.uploadToShotgun.enabled() and dialog.uploadToShotgun.value())) ) )
            extraKVPIndex += 1

        groupBatch = True

    if groupBatch or dialog.separateJobs.value():
        fileHandle.write( EncodeAsUTF16String( "BatchName=%s\n" % batchName ) )

    fileHandle.close()

    # Update task progress
    progressTask.setMessage("Creating Plugin Info File")
    progressTask.setProgress(10)

    # Create the plugin info file
    pluginInfoFile = unicode(deadlineTemp, "utf-8") + (u"/nuke_plugin_info%d.job" % jobCount)
    fileHandle = open( pluginInfoFile, "w" )
    if not dialog.submitScene.value():
        fileHandle.write( EncodeAsUTF16String( "SceneFile=%s\n" % root.name() ) )

    fileHandle.write( EncodeAsUTF16String( "Version=%s.%s\n" % (nuke.env[ 'NukeVersionMajor' ], nuke.env['NukeVersionMinor']) ) )
    fileHandle.write( EncodeAsUTF16String( "Threads=%s\n" % dialog.threads.value() ) )
    fileHandle.write( EncodeAsUTF16String( "RamUse=%s\n" % dialog.memoryUsage.value() ) )
    fileHandle.write( EncodeAsUTF16String( "BatchMode=%s\n" % dialog.batchMode.value()) )
    fileHandle.write( EncodeAsUTF16String( "BatchModeIsMovie=%s\n" % tempIsMovie ) )

    if dialog.separateJobs.value():
        #we need the fullName of the node here, otherwise write nodes that are embedded in groups won't work
        fileHandle.write( EncodeAsUTF16String( "WriteNode=%s\n" % node.fullName() ) )
    elif dialog.separateTasks.value():
        fileHandle.write( EncodeAsUTF16String( "WriteNodesAsSeparateJobs=True\n" ) )

        writeNodeIndex = 0
        for tempNode in writeNodes:
            if not tempNode.knob( 'disable' ).value():
                enterLoop = True
                if dialog.readFileOnly.value() and tempNode.knob( 'reading' ):
                    enterLoop = enterLoop and tempNode.knob( 'reading' ).value()
                if dialog.selectedOnly.value():
                    enterLoop = enterLoop and IsNodeOrParentNodeSelected(tempNode)

                if enterLoop:
                    #we need the fullName of the node here, otherwise write nodes that are embedded in groups won't work
                    fileHandle.write( EncodeAsUTF16String( "WriteNode%s=%s\n" % (writeNodeIndex,tempNode.fullName()) ) )

                    if dialog.useNodeRange.value() and tempNode.knob( 'use_limit' ).value():
                        startFrame = int(tempNode.knob('first').value())
                        endFrame = int(tempNode.knob('last').value())
                    else:
                        startFrame = nuke.Root().firstFrame()
                        endFrame = nuke.Root().lastFrame()
                        if dialog.frameListMode.value() == "Input":
                            try:
                                activeInput = nuke.activeViewer().activeInput()
                                startFrame = nuke.activeViewer().node().input(activeInput).frameRange().first()
                                endFrame = nuke.activeViewer().node().input(activeInput).frameRange().last()
                            except:
                                pass

                    fileHandle.write( EncodeAsUTF16String( "WriteNode%sStartFrame=%s\n" % (writeNodeIndex,startFrame) ) )
                    fileHandle.write( EncodeAsUTF16String( "WriteNode%sEndFrame=%s\n" % (writeNodeIndex,endFrame) ) )
                    writeNodeIndex += 1
    else:
        if dialog.readFileOnly.value() or dialog.selectedOnly.value():
            writeNodesStr = ""

            for tempNode in writeNodes:
                if not tempNode.knob( 'disable' ).value():
                    enterLoop = True
                    if dialog.readFileOnly.value() and tempNode.knob( 'reading' ):
                        enterLoop = enterLoop and tempNode.knob( 'reading' ).value()
                    if dialog.selectedOnly.value():
                        enterLoop = enterLoop and IsNodeOrParentNodeSelected(tempNode)

                    if enterLoop:
                        #we need the fullName of the node here, otherwise write nodes that are embedded in groups won't work
                        writeNodesStr += ("%s," % tempNode.fullName())

            writeNodesStr = writeNodesStr.strip( "," )
            fileHandle.write( EncodeAsUTF16String( "WriteNode=%s\n" % writeNodesStr ) )

    fileHandle.write( EncodeAsUTF16String( "NukeX=%s\n" % dialog.useNukeX.value() ) )

    if int(nuke.env[ 'NukeVersionMajor' ]) >= 7:
        fileHandle.write( EncodeAsUTF16String( "UseGpu=%s\n" % dialog.useGpu.value() ) )

    fileHandle.write( EncodeAsUTF16String( "RenderMode=%s\n" % dialog.renderMode.value() ) )
    fileHandle.write( EncodeAsUTF16String( "EnforceRenderOrder=%s\n" % dialog.enforceRenderOrder.value() ) )
    fileHandle.write( EncodeAsUTF16String( "ContinueOnError=%s\n" % dialog.continueOnError.value() ) )

    if int(nuke.env[ 'NukeVersionMajor' ]) >= 9:
        fileHandle.write( EncodeAsUTF16String( "PerformanceProfiler=%s\n" % dialog.performanceProfiler.value() ) )
        fileHandle.write( EncodeAsUTF16String( "PerformanceProfilerDir=%s\n" % dialog.performanceProfilerPath.value() ) )

    if dialog.chooseViewsToRender.value():
        fileHandle.write( EncodeAsUTF16String( "Views=%s\n" % ','.join(viewsToRender) ) )
    else:
        fileHandle.write( EncodeAsUTF16String( "Views=\n" ) )

    fileHandle.write( EncodeAsUTF16String( "StackSize=%s\n" % dialog.stackSize.value() ))

    fileHandle.close()

    # Update task progress
    progressTask.setMessage("Submitting Job %d to Deadline" % jobCount)
    progressTask.setProgress(30)

    # Submit the job to Deadline
    args = []
    args.append( jobInfoFile.encode(locale.getpreferredencoding() ) )
    args.append( pluginInfoFile.encode(locale.getpreferredencoding() ) )
    if dialog.submitScene.value():
        args.append( root.name() )

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

def FindNodesHasNoRenderOrder(nodes):
    noRenderOrderNodes = filter( lambda node:'render_order' not in node.knobs(), nodes ) # loop through all nodes find all nodes doesn't have 'render_order'
    noRenderOrderNodesNames = map( lambda node:node.name(), noRenderOrderNodes ) # loop through nodes in the list created in previous line and collect all names
    return ','.join(noRenderOrderNodesNames), len(noRenderOrderNodesNames) # return the names of nodes in one string and number of nodes

# The main submission function.
def SubmitToDeadline( ):
    global dialog
    global deadlineHome

    # DeadlineGlobals contains initial values for the submission dialog. These can be modified
    # by an external sanity scheck script.
    import DeadlineGlobals

    # Get the root node.
    root = nuke.Root()
    studio = False
    noRoot = False
    if 'studio' in nuke.env.keys() and nuke.env[ 'studio' ]:
        studio = True
    # If the Nuke script hasn't been saved, its name will be 'Root' instead of the file name.
    if root.name() == "Root":
        noRoot = True
        if not studio:
            nuke.message( "The Nuke script must be saved before it can be submitted to Deadline." )
            return

    nuke_projects = []
    valid_projects = []

    if studio:
        #Get the projects and check if we have any comps in any of them
        nuke_projects = hcore.projects()
        if len(nuke_projects) < 1 and not noRoot:
            nuke.message("The Nuke script or Nuke project must be saved before it can be submitted to Deadline.")
            return

        if len(nuke_projects) > 0:
            foundScripts = False
            for project in nuke_projects:
                sequences = project.sequences()
                for sequence in sequences:
                    tracks = sequence.binItem().activeItem().items()
                    for track in tracks:
                        items = track.items()
                        for item in items:
                            if item.isMediaPresent():
                                source = item.source()
                                name = source.mediaSource().filename()
                                if ".nk" in name:
                                    foundScripts = True
                                    break
                        if foundScripts:
                            break
                    if foundScripts:
                        break
                if foundScripts:
                    foundScripts = False
                    valid_projects.append(project)

            if len(valid_projects) < 1 and noRoot:
                nuke.message("The current Nuke project contains no saved comps that can be rendered. Please save any existing Nuke scripts before submitting to Deadline.")
                return

    # If the Nuke script has been modified, then save it.
    if root.modified() and not noRoot:
        if root.name() != "Root":
            nuke.scriptSave( root.name() )

    # Get the current user Deadline home directory, which we'll use to store settings and temp files.
    deadlineHome = CallDeadlineCommand( ["-GetCurrentUserHomeDirectory",] )

    deadlineHome = deadlineHome.replace( "\n", "" ).replace( "\r", "" )
    deadlineSettings = deadlineHome + "/settings"
    deadlineTemp = deadlineHome + "/temp"

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
    initCustomFrameList = None

    # Set initial settings for submission dialog.
    if noRoot:
        DeadlineGlobals.initJobName = "Untitled"
    else:
        DeadlineGlobals.initJobName = os.path.basename( nuke.Root().name() )
    DeadlineGlobals.initComment = ""

    DeadlineGlobals.initDepartment = ""
    DeadlineGlobals.initPool = "none"
    DeadlineGlobals.initSecondaryPool = " "
    DeadlineGlobals.initGroup = "none"
    DeadlineGlobals.initPriority = 50
    DeadlineGlobals.initTaskTimeout = 0
    DeadlineGlobals.initAutoTaskTimeout = False
    DeadlineGlobals.initConcurrentTasks = 1
    DeadlineGlobals.initLimitConcurrentTasks = True
    DeadlineGlobals.initMachineLimit = 0
    DeadlineGlobals.initIsBlacklist = False
    DeadlineGlobals.initMachineList = ""
    DeadlineGlobals.initLimitGroups = ""
    DeadlineGlobals.initDependencies = ""
    DeadlineGlobals.initOnComplete = "Nothing"
    DeadlineGlobals.initSubmitSuspended = False
    DeadlineGlobals.initChunkSize = 10
    DeadlineGlobals.initThreads = 0
    DeadlineGlobals.initMemoryUsage = 0
    DeadlineGlobals.initSeparateJobs = False
    DeadlineGlobals.initSeparateJobDependencies = False
    DeadlineGlobals.initSeparateTasks = False
    DeadlineGlobals.initUseNodeRange = True
    DeadlineGlobals.initReadFileOnly = False
    DeadlineGlobals.initSelectedOnly = True
    DeadlineGlobals.initSubmitScene = True
    DeadlineGlobals.initBatchMode = True
    DeadlineGlobals.initContinueOnError = False
    DeadlineGlobals.initUseGpu = False
    DeadlineGlobals.initEnforceRenderOrder = False
    DeadlineGlobals.initStackSize = 0
    DeadlineGlobals.initRenderMode = "Use Scene Settings"
    DeadlineGlobals.initPerformanceProfiler = False
    DeadlineGlobals.initReloadPlugin = False
    DeadlineGlobals.initPerformanceProfilerPath = ""
    DeadlineGlobals.initPrecompFirst = False
    DeadlineGlobals.initPrecompOnly = False
    DeadlineGlobals.initExtraInfo0 = ""
    DeadlineGlobals.initExtraInfo1 = ""
    DeadlineGlobals.initExtraInfo2 = ""
    DeadlineGlobals.initExtraInfo3 = ""
    DeadlineGlobals.initExtraInfo4 = ""
    DeadlineGlobals.initExtraInfo5 = ""
    DeadlineGlobals.initExtraInfo6 = ""
    DeadlineGlobals.initExtraInfo7 = ""
    DeadlineGlobals.initExtraInfo8 = ""
    DeadlineGlobals.initExtraInfo9 = ""

    DeadlineGlobals.initUseNukeX = False
    if nuke.env[ 'nukex' ]:
        DeadlineGlobals.initUseNukeX = True

    DeadlineGlobals.initUseDraft = False
    DeadlineGlobals.initDraftQuick = "Quick"
    DeadlineGlobals.initDraftCodec = "mjpeg"
    DeadlineGlobals.initDraftFormat = "JPEG (jpg)"
    DeadlineGlobals.initDraftFrameRate = "24"
    DeadlineGlobals.initDraftResolution = "Full"
    DeadlineGlobals.initDraftQuality = 85
    DeadlineGlobals.initDraftTemplate = ""
    DeadlineGlobals.initDraftUser = ""
    DeadlineGlobals.initDraftEntity = ""
    DeadlineGlobals.initDraftVersion = ""
    DeadlineGlobals.initDraftExtraArgs = ""
    DeadlineGlobals.initProjectManagement = "Shotgun" #Default to Shotgun

    # Read In Sticky Settings
    configFile = deadlineSettings + "/nuke_py_submission.ini"
    print "Reading sticky settings from %s" % configFile
    try:
        if os.path.isfile( configFile ):
            config = ConfigParser.ConfigParser()
            config.read( configFile )

            if config.has_section( "Sticky" ):
                if config.has_option( "Sticky", "FrameListMode" ):
                    initFrameListMode = config.get( "Sticky", "FrameListMode" )
                if config.has_option( "Sticky", "CustomFrameList" ):
                    initCustomFrameList = config.get( "Sticky", "CustomFrameList" )

                if config.has_option( "Sticky", "Department" ):
                    DeadlineGlobals.initDepartment = config.get( "Sticky", "Department" )
                if config.has_option( "Sticky", "Pool" ):
                    DeadlineGlobals.initPool = config.get( "Sticky", "Pool" )
                if config.has_option( "Sticky", "SecondaryPool" ):
                    DeadlineGlobals.initSecondaryPool = config.get( "Sticky", "SecondaryPool" )
                if config.has_option( "Sticky", "Group" ):
                    DeadlineGlobals.initGroup = config.get( "Sticky", "Group" )
                if config.has_option( "Sticky", "Priority" ):
                    DeadlineGlobals.initPriority = config.getint( "Sticky", "Priority" )
                if config.has_option( "Sticky", "MachineLimit" ):
                    DeadlineGlobals.initMachineLimit = config.getint( "Sticky", "MachineLimit" )
                if config.has_option( "Sticky", "IsBlacklist" ):
                    DeadlineGlobals.initIsBlacklist = config.getboolean( "Sticky", "IsBlacklist" )
                if config.has_option( "Sticky", "MachineList" ):
                    DeadlineGlobals.initMachineList = config.get( "Sticky", "MachineList" )
                if config.has_option( "Sticky", "LimitGroups" ):
                    DeadlineGlobals.initLimitGroups = config.get( "Sticky", "LimitGroups" )
                if config.has_option( "Sticky", "SubmitSuspended" ):
                    DeadlineGlobals.initSubmitSuspended = config.getboolean( "Sticky", "SubmitSuspended" )
                if config.has_option( "Sticky", "ChunkSize" ):
                    DeadlineGlobals.initChunkSize = config.getint( "Sticky", "ChunkSize" )
                if config.has_option( "Sticky", "ConcurrentTasks" ):
                    DeadlineGlobals.initConcurrentTasks = config.getint( "Sticky", "ConcurrentTasks" )
                if config.has_option( "Sticky", "LimitConcurrentTasks" ):
                    DeadlineGlobals.initLimitConcurrentTasks = config.getboolean( "Sticky", "LimitConcurrentTasks" )
                if config.has_option( "Sticky", "Threads" ):
                    DeadlineGlobals.initThreads = config.getint( "Sticky", "Threads" )
                if config.has_option( "Sticky", "SubmitScene" ):
                    DeadlineGlobals.initSubmitScene = config.getboolean( "Sticky", "SubmitScene" )
                if config.has_option( "Sticky", "BatchMode" ):
                    DeadlineGlobals.initBatchMode = config.getboolean( "Sticky", "BatchMode" )
                if config.has_option( "Sticky", "ContinueOnError" ):
                    DeadlineGlobals.initContinueOnError = config.getboolean( "Sticky", "ContinueOnError" )
                if config.has_option( "Sticky", "UseNodeRange" ):
                    DeadlineGlobals.initUseNodeRange = config.getboolean( "Sticky", "UseNodeRange" )
                if config.has_option( "Sticky", "UseGpu" ):
                    DeadlineGlobals.initUseGpu = config.getboolean( "Sticky", "UseGpu" )
                if config.has_option( "Sticky", "EnforceRenderOrder" ):
                    DeadlineGlobals.initEnforceRenderOrder = config.getboolean( "Sticky", "EnforceRenderOrder" )
                if config.has_option( "Sticky", "RenderMode" ):
                    DeadlineGlobals.initRenderMode = config.get( "Sticky", "RenderMode" )
                if config.has_option( "Sticky", "PerformanceProfiler" ):
                    DeadlineGlobals.initPerformanceProfiler = config.getboolean( "Sticky", "PerformanceProfiler")
                if config.has_option( "Sticky", "ReloadPlugin" ):
                    DeadlineGlobals.initReloadPlugin = config.getboolean( "Sticky", "ReloadPlugin" )
                if config.has_option( "Sticky", "PerformanceProfilerPath" ):
                    DeadlineGlobals.initPerformanceProfilerPath = config.get( "Sticky", "PerformanceProfilerPath" )
                if config.has_option( "Sticky", "PrecompFirst" ):
                    DeadlineGlobals.initPrecompFirst = config.getboolean( "Sticky", "PrecompFirst")
                if config.has_option( "Sticky", "PrecompOnly" ):
                    DeadlineGlobals.initPrecompOnly = config.get( "Sticky", "PrecompOnly" )
                if config.has_option( "Sticky", "UseDraft" ):
                    DeadlineGlobals.initUseDraft = config.getboolean( "Sticky", "UseDraft" )
                if config.has_option( "Sticky", "DraftQuick" ):
                    DeadlineGlobals.initDraftQuick = config.get( "Sticky", "DraftQuick" )
                if config.has_option( "Sticky", "DraftCodec" ):
                    DeadlineGlobals.initDraftCodec = config.get( "Sticky", "DraftCodec" )
                if config.has_option( "Sticky", "DraftFormat" ):
                    DeadlineGlobals.initDraftFormat = config.get( "Sticky", "DraftFormat" )
                if config.has_option( "Sticky", "DraftFrameRate" ):
                    DeadlineGlobals.initDraftFrameRate = config.get( "Sticky", "DraftFrameRate" )
                if config.has_option( "Sticky", "DraftResolution" ):
                    DeadlineGlobals.initDraftResolution = config.get( "Sticky", "DraftResolution" )
                if config.has_option( "Sticky", "DraftQuality" ):
                    DeadlineGlobals.initDraftQuality = config.getint( "Sticky", "DraftQuality" )
                if config.has_option( "Sticky", "DraftTemplate" ):
                    DeadlineGlobals.initDraftTemplate = config.get( "Sticky", "DraftTemplate" )
                if config.has_option( "Sticky", "DraftUser" ):
                    DeadlineGlobals.initDraftUser = config.get( "Sticky", "DraftUser" )
                if config.has_option( "Sticky", "DraftEntity" ):
                    DeadlineGlobals.initDraftEntity = config.get( "Sticky", "DraftEntity" )
                if config.has_option( "Sticky", "DraftVersion" ):
                    DeadlineGlobals.initDraftVersion = config.get( "Sticky", "DraftVersion" )
                if config.has_option( "Sticky", "DraftExtraArgs"):
                    DeadlineGlobals.initDraftExtraArgs = config.get( "Sticky", "DraftExtraArgs" )
                if config.has_option( "Sticky", "ProjectManagement" ):
                    DeadlineGlobals.initProjectManagement = config.get( "Sticky", "ProjectManagement" )
    except:
        print( "Could not read sticky settings")
        print traceback.format_exc()

    shotgunKVPs = {}
    ftrackKVPs = {}
    nimKVPs = {}

    try:
                root = nuke.Root()
                if "FrameListMode" in root.knobs():
                    initFrameListMode = ( root.knob( "FrameListMode" ) ).value()

                if "CustomFrameList" in root.knobs():
                    initCustomFrameList = ( root.knob( "CustomFrameList" ) ).value()

                if "Department" in root.knobs():
                    DeadlineGlobals.initDepartment = ( root.knob( "Department" ) ).value()

                if "Pool" in root.knobs():
                    DeadlineGlobals.initPool = ( root.knob( "Pool" ) ).value()

                if "SecondaryPool" in root.knobs():
                    DeadlineGlobals.initSecondaryPool = ( root.knob( "SecondaryPool" ) ).value()

                if "Group" in root.knobs():
                    DeadlineGlobals.initGroup = ( root.knob( "Group" ) ).value()

                if "Priority" in root.knobs():
                    DeadlineGlobals.initPriority = int( ( root.knob( "Priority" ) ).value() )

                if "MachineLimit" in root.knobs():
                    DeadlineGlobals.initMachineLimit = int( ( root.knob( "MachineLimit" ) ).value() )

                if "IsBlacklist" in root.knobs():
                    DeadlineGlobals.initIsBlacklist = StrToBool( ( root.knob( "IsBlacklist" ) ).value() )

                if "MachineList" in root.knobs():
                    DeadlineGlobals.initMachineList = ( root.knob( "MachineList" ) ).value()

                if "LimitGroups" in root.knobs():
                    DeadlineGlobals.initLimitGroups = ( root.knob( "LimitGroups" ) ).value()

                if "SubmitSuspended" in root.knobs():
                    DeadlineGlobals.initSubmitSuspended = StrToBool( ( root.knob( "SubmitSuspended" ) ).value() )

                if "ChunkSize" in root.knobs():
                    DeadlineGlobals.initChunkSize = int( ( root.knob( "ChunkSize" ) ).value() )

                if "ConcurrentTasks" in root.knobs():
                    DeadlineGlobals.initConcurrentTasks = int( ( root.knob( "ConcurrentTasks" ) ).value() )

                if "LimitConcurrentTasks" in root.knobs():
                    DeadlineGlobals.initLimitConcurrentTasks = StrToBool( ( root.knob( "LimitConcurrentTasks" ) ).value() )

                if "Threads" in root.knobs():
                    DeadlineGlobals.initThreads = int( ( root.knob( "Threads" ) ).value() )

                if "SubmitScene" in root.knobs():
                    DeadlineGlobals.initSubmitScene = StrToBool( ( root.knob( "SubmitScene" ) ).value() )

                if "BatchMode" in root.knobs():
                    DeadlineGlobals.initBatchMode = StrToBool( ( root.knob( "BatchMode" ) ).value() )

                if "ContinueOnError" in root.knobs():
                    DeadlineGlobals.initContinueOnError = StrToBool( ( root.knob( "ContinueOnError" ) ).value() )

                if "UseNodeRange" in root.knobs():
                    DeadlineGlobals.initUseNodeRange = StrToBool( ( root.knob( "UseNodeRange" ) ).value() )

                if "UseGpu" in root.knobs():
                    DeadlineGlobals.initUseGpu = StrToBool( ( root.knob( "UseGpu" ) ).value() )

                if "EnforceRenderOrder" in root.knobs():
                    DeadlineGlobals.initEnforceRenderOrder = StrToBool( ( root.knob( "EnforceRenderOrder" ) ).value() )

                if "DeadlineRenderMode" in root.knobs():
                    DeadlineGlobals.initRenderMode = ( root.knob( "DeadlineRenderMode" ) ).getText()

                if "PerformanceProfiler" in root.knobs():
                    DeadlineGlobals.initPerformanceProfiler = StrToBool( ( root.knob( "PerformanceProfiler" ) ).value() )

                if "ReloadPlugin" in root.knobs():
                    DeadlineGlobals.initReloadPlugin = StrToBool( ( root.knob( "ReloadPlugin" ) ).value() )

                if "PerformanceProfilerPath" in root.knobs():
                    DeadlineGlobals.initPerformanceProfilerPath = ( root.knob( "PerformanceProfilerPath" ) ).value()

                if "PrecompFirst" in root.knobs():
                    DeadlineGlobals.initPrecompFirst = ( root.knob( "PrecompFirst" ) ).value()

                if "PrecompOnly" in root.knobs():
                    DeadlineGlobals.initPrecompOnly = ( root.knob( "PrecompOnly" ) ).value()

                if "UseDraft" in root.knobs():
                    DeadlineGlobals.initUseDraft = StrToBool( ( root.knob( "UseDraft" ) ).value() )

                if "DraftQuick" in root.knobs():
                    DeadlineGlobals.initDraftQuick = ( root.knob( "DraftQuick" ) ).value()

                if "DraftCodec" in root.knobs():
                    DeadlineGlobals.initDraftCodec = ( root.knob( "DraftCodec" ) ).value()

                if "DraftFormat" in root.knobs():
                    DeadlineGlobals.initDraftFormat = ( root.knob( "DraftFormat" ) ).value()

                if "DraftFrameRate" in root.knobs():
                    DeadlineGlobals.initDraftFrameRate = ( root.knob( "DraftFrameRate" ) ).value()

                if "DraftResolution" in root.knobs():
                    DeadlineGlobals.initDraftResolution = ( root.knob( "DraftResolution" ) ).value()

                if "DraftQuality" in root.knobs():
                    DeadlineGlobals.initDraftQuality = int( ( root.knob( "DraftQuality" ) ).value() )

                if "DraftTemplate" in root.knobs():
                    DeadlineGlobals.initDraftTemplate = ( root.knob( "DraftTemplate" ) ).value()

                if "DraftUser" in root.knobs():
                    DeadlineGlobals.initDraftUser = ( root.knob( "DraftUser" ) ).value()

                if "DraftEntity" in root.knobs():
                    DeadlineGlobals.initDraftEntity = ( root.knob( "DraftEntity" ) ).value()

                if "DraftVersion" in root.knobs():
                    DeadlineGlobals.initDraftVersion = ( root.knob( "DraftVersion" ) ).value()

                if "DraftExtraArgs" in root.knobs():
                    DeadlineGlobals.initDraftExtraArgs = ( root.knob( "DraftExtraArgs" ) ).value()

                if "ProjectManagement" in root.knobs():
                    DeadlineGlobals.initProjectManagement = ( root.knob( "ProjectManagement" ) ).value()

                if "DeadlineSGData" in root.knobs():
                    sgDataKnob = root.knob( "DeadlineSGData" )
                    shotgunKVPs = ast.literal_eval( sgDataKnob.toScript() )

                if "DeadlineFTData" in root.knobs():
                    ftDataKnob = root.knob( "DeadlineFTData" )
                    ftrackKVPs = ast.literal_eval( ftDataKnob.toScript() )

                if "DeadlineNIMData" in root.knobs():
                    nimDataKnob = root.knob( "DeadlineNIMData" )
                    nimKVPs = ast.literal_eval( nimDataKnob.toScript() )

    except:
        print "Could not read knob settings."
        print traceback.format_exc()

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

        if startFrame == endFrame:
            DeadlineGlobals.initFrameList = str(startFrame)
        else:
            DeadlineGlobals.initFrameList = str(startFrame) + "-" + str(endFrame)
    else:
        if initCustomFrameList == None or initCustomFrameList.strip() == "":
            startFrame = nuke.Root().firstFrame()
            endFrame = nuke.Root().lastFrame()
            if startFrame == endFrame:
                DeadlineGlobals.initFrameList = str(startFrame)
            else:
                DeadlineGlobals.initFrameList = str(startFrame) + "-" + str(endFrame)
        else:
            DeadlineGlobals.initFrameList = initCustomFrameList.strip()

    # Run the sanity check script if it exists, which can be used to set some initial values.
    sanityCheckFile = GetRepositoryPath("submission/Nuke/Main") + "/CustomSanityChecks.py"
    if os.path.isfile( sanityCheckFile ):
        print( "Running sanity check script: " + sanityCheckFile )
        try:
            import CustomSanityChecks
            sanityResult = CustomSanityChecks.RunSanityCheck()
            if not sanityResult:
                print( "Sanity check returned false, exiting" )
                return
        except:
            print( "Could not run CustomSanityChecks.py script" )
            print( traceback.format_exc() )

    if DeadlineGlobals.initPriority > maximumPriority:
        DeadlineGlobals.initPriority = (maximumPriority / 2)

    # Both of these can't be enabled!
    if DeadlineGlobals.initSeparateJobs and DeadlineGlobals.initSeparateTasks:
        DeadlineGlobals.initSeparateTasks = False

    extraInfo = [ "" ] * 10
    extraInfo[ 0 ] = DeadlineGlobals.initExtraInfo0
    extraInfo[ 1 ] = DeadlineGlobals.initExtraInfo1
    extraInfo[ 2 ] = DeadlineGlobals.initExtraInfo2
    extraInfo[ 3 ] = DeadlineGlobals.initExtraInfo3
    extraInfo[ 4 ] = DeadlineGlobals.initExtraInfo4
    extraInfo[ 5 ] = DeadlineGlobals.initExtraInfo5
    extraInfo[ 6 ] = DeadlineGlobals.initExtraInfo6
    extraInfo[ 7 ] = DeadlineGlobals.initExtraInfo7
    extraInfo[ 8 ] = DeadlineGlobals.initExtraInfo8
    extraInfo[ 9 ] = DeadlineGlobals.initExtraInfo9


    # Check for potential issues and warn user about any that are found.
    warningMessages = ""
    nodeClasses = [ "Write", "DeepWrite", "WriteGeo" ]
    writeNodes = RecursiveFindNodes( nodeClasses, nuke.Root() )
    precompWriteNodes = RecursiveFindNodesInPrecomp( nodeClasses, nuke.Root() )

    print "Found a total of %d write nodes" % len( writeNodes )
    print "Found a total of %d write nodes within precomp nodes" % len( precompWriteNodes )

    # Check all the output filenames if they are local or not padded (non-movie files only).
    outputCount = 0

    for node in writeNodes:
        reading = False
        if node.knob( 'reading' ):
            reading = node.knob( 'reading' ).value()

        # Need at least one write node that is enabled, and not set to read in as well.
        if not node.knob( 'disable' ).value() and not reading:
            outputCount = outputCount + 1

            # if root.proxy() and node.knob( 'proxy' ).value() != "":
                # filename = node.knob( 'proxy' ).value()
            # else:
                # filename = node.knob( 'file' ).value()

            #nuke.filename will evaluate embedded TCL, but leave the frame padding
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

    # Create an instance of the submission dialog.
    if len(valid_projects) > 0:
        dialog = DeadlineContainerDialog( maximumPriority, pools, secondaryPools, groups, valid_projects, not noRoot )
    else:
        dialog = DeadlineDialog( maximumPriority, pools, secondaryPools, groups )

    # Set the initial values.
    dialog.jobName.setValue( DeadlineGlobals.initJobName )
    dialog.comment.setValue( DeadlineGlobals.initComment )
    dialog.department.setValue( DeadlineGlobals.initDepartment )

    dialog.pool.setValue( DeadlineGlobals.initPool )
    dialog.secondaryPool.setValue( DeadlineGlobals.initSecondaryPool )
    dialog.group.setValue( DeadlineGlobals.initGroup )
    dialog.priority.setValue( DeadlineGlobals.initPriority )
    dialog.taskTimeout.setValue( DeadlineGlobals.initTaskTimeout )
    dialog.autoTaskTimeout.setValue( DeadlineGlobals.initAutoTaskTimeout )
    dialog.concurrentTasks.setValue( DeadlineGlobals.initConcurrentTasks )
    dialog.limitConcurrentTasks.setValue( DeadlineGlobals.initLimitConcurrentTasks )
    dialog.machineLimit.setValue( DeadlineGlobals.initMachineLimit )
    dialog.isBlacklist.setValue( DeadlineGlobals.initIsBlacklist )
    dialog.machineList.setValue( DeadlineGlobals.initMachineList )
    dialog.limitGroups.setValue( DeadlineGlobals.initLimitGroups )
    dialog.dependencies.setValue( DeadlineGlobals.initDependencies )
    dialog.onComplete.setValue( DeadlineGlobals.initOnComplete )
    dialog.submitSuspended.setValue( DeadlineGlobals.initSubmitSuspended )

    dialog.frameListMode.setValue( initFrameListMode )
    dialog.frameList.setValue( DeadlineGlobals.initFrameList )
    dialog.chunkSize.setValue( DeadlineGlobals.initChunkSize )
    dialog.threads.setValue( DeadlineGlobals.initThreads )
    dialog.memoryUsage.setValue( DeadlineGlobals.initMemoryUsage )
    dialog.separateJobs.setValue( DeadlineGlobals.initSeparateJobs )
    dialog.separateJobDependencies.setValue( DeadlineGlobals.initSeparateJobDependencies )
    dialog.separateTasks.setValue( DeadlineGlobals.initSeparateTasks )
    dialog.readFileOnly.setValue( DeadlineGlobals.initReadFileOnly )
    dialog.selectedOnly.setValue( DeadlineGlobals.initSelectedOnly )
    dialog.submitScene.setValue( DeadlineGlobals.initSubmitScene )
    dialog.useNukeX.setValue( DeadlineGlobals.initUseNukeX )
    dialog.continueOnError.setValue( DeadlineGlobals.initContinueOnError )
    dialog.batchMode.setValue( DeadlineGlobals.initBatchMode )
    dialog.useNodeRange.setValue( DeadlineGlobals.initUseNodeRange )
    dialog.useGpu.setValue( DeadlineGlobals.initUseGpu )
    dialog.enforceRenderOrder.setValue( DeadlineGlobals.initEnforceRenderOrder )
    dialog.renderMode.setValue( DeadlineGlobals.initRenderMode )
    dialog.performanceProfiler.setValue( DeadlineGlobals.initPerformanceProfiler )
    dialog.reloadPlugin.setValue( DeadlineGlobals.initReloadPlugin )
    dialog.performanceProfilerPath.setValue( DeadlineGlobals.initPerformanceProfilerPath )
    dialog.precompFirst.setValue( DeadlineGlobals.initPrecompFirst )
    dialog.precompOnly.setValue( DeadlineGlobals.initPrecompOnly )
    #dialog.viewsToRender.setValue( DeadlineGlobals.initViews )
    dialog.stackSize.setValue( DeadlineGlobals.initStackSize )

    dialog.separateJobs.setEnabled( len( writeNodes ) > 0 )
    dialog.separateTasks.setEnabled( len( writeNodes ) > 0 )

    dialog.separateJobDependencies.setEnabled( dialog.separateJobs.value() )
    dialog.useNodeRange.setEnabled( dialog.separateJobs.value() or dialog.separateTasks.value() )
    dialog.precompFirst.setEnabled( dialog.separateJobs.value() or dialog.separateTasks.value() )
    dialog.precompOnly.setEnabled( dialog.separateJobs.value() or dialog.separateTasks.value() )
    dialog.frameList.setEnabled( not (dialog.separateJobs.value() and dialog.useNodeRange.value()) and not dialog.separateTasks.value() )

    dialog.submitDraftJob.setValue( DeadlineGlobals.initUseDraft )
    dialog.useQuickDraft.setValue( DeadlineGlobals.initDraftQuick )
    dialog.draftFormat.setValue( DeadlineGlobals.initDraftFormat )
    dialog.AdjustCodecs()
    dialog.draftCodec.setValue( DeadlineGlobals.initDraftCodec )
    dialog.AdjustFrameRates()
    dialog.draftFrameRate.setValue( DeadlineGlobals.initDraftFrameRate )
    dialog.draftResolution.setValue( DeadlineGlobals.initDraftResolution )
    dialog.AdjustQuality()
    dialog.draftQuality.setValue( DeadlineGlobals.initDraftQuality )
    dialog.templatePath.setValue( DeadlineGlobals.initDraftTemplate )
    dialog.draftUser.setValue( DeadlineGlobals.initDraftUser )
    dialog.draftEntity.setValue( DeadlineGlobals.initDraftEntity )
    dialog.draftVersion.setValue( DeadlineGlobals.initDraftVersion )
    dialog.draftExtraArgs.setValue( DeadlineGlobals.initDraftExtraArgs )

    dialog.EnableDraftKnobs()

    dialog.shotgunKVPs = shotgunKVPs
    dialog.ftrackKVPs = ftrackKVPs
    dialog.nimKVPs = nimKVPs

    dialog.projectManagementCombo.setValue( DeadlineGlobals.initProjectManagement )
    ChangeProjectManager( DeadlineGlobals.initProjectManagement )

    # Show the dialog.
    success = False
    while not success:
        success = dialog.ShowDialog()
        if not success:
            WriteStickySettings( dialog, configFile )
            return

        errorMessages = ""
        warningMessages = ""

        # Check that frame range is valid.
        if dialog.frameList.value().strip() == "":
            errorMessages = errorMessages + "No frame list has been specified.\n\n"

        # If submitting separate write nodes, make sure there are jobs to submit
        if dialog.readFileOnly.value() or dialog.selectedOnly.value():
            validNodeFound = False
            if not dialog.precompOnly.value():
                for node in writeNodes:
                    if not node.knob( 'disable' ).value():
                        validNodeFound = True
                        if dialog.readFileOnly.value():
                            if node.knob( 'reading' ) and not node.knob( 'reading' ).value():
                                validNodeFound = False
                        if dialog.selectedOnly.value() and not IsNodeOrParentNodeSelected(node):
                            validNodeFound = False

                        if validNodeFound:
                            break
            else:
                for node in precompWriteNodes:
                    if not node.knob( 'disable' ).value():
                        validNodeFound = True
                        if dialog.readFileOnly.value():
                            if node.knob( 'reading' ) and not node.knob( 'reading' ).value():
                                validNodeFound = False
                        if dialog.selectedOnly.value() and not IsNodeOrParentNodeSelected(node):
                            validNodeFound = False

                        if validNodeFound:
                            break

            if not validNodeFound:
                if dialog.readFileOnly.value() and dialog.selectedOnly.value():
                    errorMessages = errorMessages + "There are no selected write nodes with 'Read File' enabled, so there are no jobs to submit.\n\n"
                elif dialog.readFileOnly.value():
                    errorMessages = errorMessages + "There are no write nodes with 'Read File' enabled, so there are no jobs to submit.\n\n"
                elif dialog.selectedOnly.value():
                    errorMessages = errorMessages + "There are no selected write nodes, so there are no jobs to submit.\n\n"

        # Check if at least one view has been selected.
        if dialog.chooseViewsToRender.value():
            viewCount = 0
            for vk in dialog.viewToRenderKnobs:
                if vk[0].value():
                    viewCount = viewCount + 1

            if viewCount == 0:
                errorMessages = errorMessages + "There are no views selected.\n\n"

        if len(valid_projects) > 0:
            #We need to check if there is a root comp, or if sequences have been specified
            if noRoot and not dialog.submitSequenceJobs.value():
                errorMessages = errorMessages + "There is no saved comp selected in the node graph and Sequence Job Submission is disabled.\n\n"

            elif noRoot and dialog.chooseCompsToRender.value():
                #Check if any sequences were selected
                found = False
                for knob in dialog.sequenceKnobs:
                    if knob[0].value() and knob[1][1] == dialog.studioProject.value():
                        found = True
                        break

                if not found:
                    errorMessages = errorMessages + "Sequence Job Submission and Choose Sequences To Render are enabled but no sequences have been selected. Please select some sequences to render or disable Choose Sequences To Render.\n\n"

        # Check if proxy mode is enabled and Render using Proxy Mode is disabled, then warn the user.
        if root.proxy() and dialog.renderMode.value() == "Use Scene Settings":
            warningMessages = warningMessages + "Proxy Mode is enabled and the scene is being rendered using scene settings, which may cause problems when rendering through Deadline.\n\n"

        # Check if the script file is local and not being submitted to Deadline.
        if not dialog.submitScene.value():
            if IsPathLocal( root.name() ):
                warningMessages = warningMessages + "Nuke script path is local and is not being submitted to Deadline:\n" + root.name() + "\n\n"

        # Check Performance Profile Path
        if dialog.performanceProfiler.value():
            if not os.path.exists( dialog.performanceProfilerPath.value() ):
                errorMessages += "Performance Profiler is enabled, but an XML directory has not been selected (or it does not exist). Either select a valid network path, or disable Performance Profiling.\n\n"

        # Check Draft template path
        if dialog.submitDraftJob.value() and not dialog.useQuickDraft.value():
            if not os.path.exists( dialog.templatePath.value() ):
                errorMessages += "Draft job submission is enabled, but a Draft template has not been selected (or it does not exist). Either select a valid template, or disable Draft job submission.\n\n"

        if dialog.separateTasks.value() and dialog.frameListMode.value() == "Custom" and not dialog.useNodeRange.value():
            errorMessages += "Custom frame list is not supported when submitting write nodes as separate tasks. Please choose Global or Input, or enable Use Node's Frame List.\n\n"

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
                WriteStickySettings( dialog, configFile )
                return


    #Save sticky settings
    WriteStickySettings( dialog, configFile )

    tempJobName = dialog.jobName.value()
    tempDependencies = dialog.dependencies.value()
    tempFrameList = dialog.frameList.value().strip()
    tempChunkSize = dialog.chunkSize.value()
    tempIsMovie = False
    semaphore = threading.Semaphore()

    if len(valid_projects) > 0 and dialog.submitSequenceJobs.value():
        SubmitSequenceJobs(dialog, deadlineTemp, tempDependencies, semaphore, extraInfo)
    else:
        # Check if we should be submitting a separate job for each write node.
        if dialog.separateJobs.value():
            jobCount = 0
            previousJobId = ""
            submitThreads = []

            tempwriteNodes = []

            if dialog.selectedOnly.value():
                writeNodes = filter( IsNodeOrParentNodeSelected, writeNodes )

            nodeNames, num = FindNodesHasNoRenderOrder( writeNodes )

            if num > 0 and not nuke.ask( 'No render order nodes found: %s \n\n' % (nodeNames) +
                                        'Do you still wish to submit this job to Deadline?' ):
                return

            if dialog.precompOnly.value():
                tempWriteNodes = sorted( precompWriteNodes, key = lambda node: node['render_order'].value() )
            elif dialog.precompFirst.value():
                tempWriteNodes = sorted( precompWriteNodes, key = lambda node: node['render_order'].value() )

                additionalNodes = [item for item in writeNodes if item not in precompWriteNodes]
                additionalNodes = sorted( additionalNodes, key = lambda node: node['render_order'].value() )
                tempWriteNodes.extend(additionalNodes)
            else:
                tempWriteNodes = sorted( writeNodes, key = lambda node: node['render_order'].value() )

            for node in tempWriteNodes:
                print "Now processing %s" % node.name()
                #increment job count -- will be used so not all submissions try to write to the same .job files simultaneously
                jobCount += 1

                # Check if we should enter the loop for this node.
                enterLoop = False
                if not node.knob( 'disable' ).value():
                    enterLoop = True
                    if dialog.readFileOnly.value() and node.knob( 'reading' ):
                        enterLoop = enterLoop and node.knob( 'reading' ).value()
                    if dialog.selectedOnly.value():
                        enterLoop = enterLoop and IsNodeOrParentNodeSelected(node)

                if enterLoop:
                    tempJobName = dialog.jobName.value() + " - " + node.name()

                    # Check if the write node is overriding the frame range
                    if dialog.useNodeRange.value() and node.knob( 'use_limit' ).value():
                        tempFrameList = str(int(node.knob('first').value())) + "-" + str(int(node.knob('last').value()))
                    else:
                        tempFrameList = dialog.frameList.value().strip()

                    if IsMovie( node.knob( 'file' ).value() ):
                        tempChunkSize = 1000000
                        tempIsMovie = True
                    else:
                        tempChunkSize = dialog.chunkSize.value()
                        tempIsMovie = False

                    #if creating sequential dependencies, parse for JobId to be used for the next Job's dependencies
                    if dialog.separateJobDependencies.value():
                        if jobCount > 1 and not tempDependencies == "":
                            tempDependencies = tempDependencies + "," + previousJobId
                        elif tempDependencies == "":
                            tempDependencies = previousJobId

                        submitJobResults = SubmitJob( dialog, root, node, tempWriteNodes, deadlineTemp, tempJobName, tempFrameList, tempDependencies, tempChunkSize, tempIsMovie, jobCount, semaphore, extraInfo )
                        for line in submitJobResults.splitlines():
                            if line.startswith("JobID="):
                                previousJobId = line[6:]
                                break
                        tempDependencies = dialog.dependencies.value() #reset dependencies
                    else: #Create a new thread to do the submission
                        print "Spawning submission thread #%d..." % jobCount
                        submitThread = threading.Thread( None, SubmitJob, args = ( dialog, root, node, tempWriteNodes, deadlineTemp, tempJobName, tempFrameList, tempDependencies, tempChunkSize, tempIsMovie, jobCount, semaphore, extraInfo ) )
                        submitThread.start()
                        submitThreads.append( submitThread )

            if not dialog.separateJobDependencies.value():
                print "Spawning results thread..."
                resultsThread = threading.Thread( None, WaitForSubmissions, args = ( submitThreads, ) )
                resultsThread.start()

        elif dialog.separateTasks.value():
            #Create a new thread to do the submission
            tempWriteNodes = []
            if dialog.precompOnly.value():
                tempWriteNodes = sorted( precompWriteNodes, key = lambda node: node['render_order'].value() )
            elif dialog.precompFirst.value():
                tempWriteNodes = sorted( precompWriteNodes, key = lambda node: node['render_order'].value() )
                additionalNodes = [item for item in writeNodes if item not in precompWriteNodes]
                additionalNodes = sorted( additionalNodes, key = lambda node: node['render_order'].value() )
                tempWriteNodes = tempWriteNodes.extend(additionalNodes)
            else:
                tempWriteNodes = sorted( writeNodes, key = lambda node: node['render_order'].value() )

            print "Spawning submission thread..."
            submitThread = threading.Thread( None, SubmitJob, None, ( dialog, root, None, tempWriteNodes, deadlineTemp, tempJobName, tempFrameList, tempDependencies, tempChunkSize, tempIsMovie, 1, None, extraInfo ) )
            submitThread.start()
        else:
            for tempNode in writeNodes:
                if not tempNode.knob( 'disable' ).value():
                    enterLoop = True
                    if dialog.readFileOnly.value() and tempNode.knob( 'reading' ):
                        enterLoop = enterLoop and tempNode.knob( 'reading' ).value()
                    if dialog.selectedOnly.value():
                        enterLoop = enterLoop and IsNodeOrParentNodeSelected(tempNode)

                    if enterLoop:
                        if IsMovie( tempNode.knob( 'file' ).value() ):
                            tempChunkSize = 1000000
                            tempIsMovie = True
                            break

            #Create a new thread to do the submission
            print "Spawning submission thread..."
            submitThread = threading.Thread( None, SubmitJob, None, ( dialog, root, None, writeNodes, deadlineTemp, tempJobName, tempFrameList, tempDependencies, tempChunkSize, tempIsMovie, 1, None, extraInfo ) )
            submitThread.start()

    print "Main Deadline thread exiting"

def IsNodeOrParentNodeSelected( node ):
    if node.isSelected():
        return True

    parentNode = nuke.toNode( '.'.join( node.fullName().split('.')[:-1] ) )
    if parentNode:
        return IsNodeOrParentNodeSelected( parentNode )

    return False

def WaitForSubmissions( submitThreads ):
    for thread in submitThreads:
        thread.join()

    results = "Job submission complete. See the Script Editor output window for more information."
    nuke.executeInMainThread( nuke.message, results )

    print "Results thread exiting"

def GetRepositoryPath(subdir = None):
    # On OSX, we look for the DEADLINE_PATH file. On other platforms, we use the environment variable.
    if os.path.exists( "/Users/Shared/Thinkbox/DEADLINE_PATH" ):
        with open( "/Users/Shared/Thinkbox/DEADLINE_PATH" ) as f: deadlineBin = f.read().strip()
        deadlineCommand = deadlineBin + "/deadlinecommand"
    else:
        try:
            deadlineBin = os.environ['DEADLINE_PATH']
        except KeyError:
            return ""

        if os.name == 'nt':
            deadlineCommand = deadlineBin + "\\deadlinecommand.exe"
        else:
            deadlineCommand = deadlineBin + "/deadlinecommand"

    startupinfo = None
    if os.name == 'nt':
        # Python 2.6 has subprocess.STARTF_USESHOWWINDOW, and Python 2.7 has subprocess._subprocess.STARTF_USESHOWWINDOW, so check for both.
        if hasattr( subprocess, '_subprocess' ) and hasattr( subprocess._subprocess, 'STARTF_USESHOWWINDOW' ):
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess._subprocess.STARTF_USESHOWWINDOW
        elif hasattr( subprocess, 'STARTF_USESHOWWINDOW' ):
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

    args = [deadlineCommand, "-GetRepositoryPath "]
    if subdir != None and subdir != "":
        args.append(subdir)

    proc = subprocess.Popen(args, cwd=deadlineBin, stdout=subprocess.PIPE, startupinfo=startupinfo)

    path = proc.stdout.read()
    path = path.replace("\n","").replace("\r","")
    return path

################################################################################
## DEBUGGING
################################################################################

#~ # Get the repository root
#~ path = GetRepositoryRoot()
#~ if path != "":
    #~ path += "/submission/Nuke/Main"
    #~ path = path.replace( "\\", "/" )

    #~ # Add the path to the system path
    #~ if path not in sys.path :
        #~ print "Appending \"" + path + "\" to system path to import SubmitNukeToDeadline module"
        #~ sys.path.append( path )

    #~ # Call the main function to begin job submission.
    #~ SubmitToDeadline( path )
#~ else:
    #~ nuke.message( "The SubmitNukeToDeadline.py script could not be found in the Deadline Repository. Please make sure that the Deadline Client has been installed on this machine, that the Deadline Client bin folder is set in the DEADLINE_PATH environment variable, and that the Deadline Client has been configured to point to a valid Repository." )
