import os
import sys
import subprocess
import traceback

import nuke
import nukescripts

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

    proc = subprocess.Popen(args, cwd=deadlineBin, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, startupinfo=startupinfo)
    proc.stdin.close()
    proc.stderr.close()

    path = proc.stdout.read()
    path = path.replace("\n","").replace("\r","")
    return path

def main():
    # Get the repository path
    path = GetRepositoryPath("submission/Nuke/Main")
    if path != "":
        path = path.replace( "\\", "/" )

        # Add the path to the system path
        if path not in sys.path :
            print "Appending \"" + path + "\" to system path to import ReserveFrameServerSlaves module"
            sys.path.append( path )
        else:
            print( "\"%s\" is already in the system path" % path )

        # Import the script and call the main() function
        try:
            import ReserveFrameServerSlaves
            ReserveFrameServerSlaves.SubmitToDeadline( path )
        except:
            print traceback.format_exc()
            nuke.message( traceback.format_exc() + "The ReserveFrameServerSlaves.py script could not be found in the Deadline Repository. Please make sure that the Deadline Client has been installed on this machine, that the Deadline Client bin folder is set in the DEADLINE_PATH environment variable, and that the Deadline Client has been configured to point to a valid Repository." )
    else:
        nuke.message( "The ReserveFrameServerSlaves.py script could not be found in the Deadline Repository. Please make sure that the Deadline Client has been installed on this machine, that the Deadline Client bin folder is set in the DEADLINE_PATH environment variable, and that the Deadline Client has been configured to point to a valid Repository." )
