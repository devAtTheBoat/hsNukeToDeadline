# -*- coding: utf-8 -*-

import sys, os
import Draft
import DraftParamParser
import datetime

from DraftParamParser import ReplaceFilenameHashesWithNumber # For reading frames when encoding

#
#   expectedTypes example
#
#['/Users/frank/Library/Application Support/Thinkbox/Deadline8/slave/lady-rainicorn/jobsData/576ad1fb6333cb65237a2fe6/draftTemplate.py',
# 'username=kimda',
# 'entity=upload_version',
# 'version=draft_v5',
# 'width=1920',
# 'height=1080',
# 'frameList=1000-1005',
# 'startFrame=1000',
# 'endFrame=1005',
# 'inFile=/Volumes/MASTER_02/theboat/testfolder/deadline_test_render/Draft_v5/Draft_v4.####.dpx',
# 'outFile=/Volumes/MASTER_02/theboat/testfolder/deadline_test_render/Draft_v5/Draft/Draft_v4.mov',
# 'outFolder=/Volumes/MASTER_02/theboat/testfolder/deadline_test_render/Draft_v5/Draft',
# 'deadlineJobID=576ad1bd6333cb648c12d0d8',
# 'deadlineRepository=/theboat/_repo',
# 'taskStartFrame=1000',
# 'taskEndFrame=1005'
#]

expectedTypes = {
    "frameList" : '<string>',
    "inFile"    : '<string>',
    "outFile"   : '<string>',
    "outFolder" : '<string>',
    "width"     : '<string>',
    "height"    : '<string>',
    "version"   : '<string>',
    "entity"    : '<string>',
    "projectRatio"  : '<float>',
    "projectName"   : '<string>',
    "projectDesc"   : '<string>'
}

params = DraftParamParser.ParseCommandLine( expectedTypes, sys.argv )
frames = DraftParamParser.FrameRangeToFrames( params['frameList'] )

inputPath = params['inFile']
outWidth = int(params['width'])
outHeight = int(params['height'])

# Encode the slate frames at the start of the video
toCodec = "H264"

#
# Create the anotations
#

# Set text's color and point size
annotationInfo = Draft.AnnotationInfo()
annotationInfo.Color = Draft.ColorRGBA( 0.0, 0.1, 0.3, 1.0 )
annotationInfo.PointSize = int( outHeight * 0.045 )

#
# Creating the burn in data
#
print "Creating the burn in data"
# Set up the text for the slate frame
slateText = [("JOB", params["projectName"]), ("SHOT", params["entity"]), ("VERSION", params['version']), ("FRAMES", params['frameList']), ("ARTIST", params['username']), ("DATE", datetime.datetime.now().strftime("%m/%d/%Y") )]

slateAbsolutePath = os.path.join('/theboat/_config/scripts/deadline/draft/slateBackground.dpx')
slateFrame = Draft.Image.ReadFromFile( slateAbsolutePath )

## For the composite operations
compOperation = Draft.CompositeOperator.OverCompositeOp


for i in range( 0, len( slateText ) ):
    txtImg = Draft.Image.CreateAnnotation( slateText[i][0] + ": ", annotationInfo )
    slateFrame.CompositeWithPositionAndAnchor( txtImg, 0.18, 0.7 - (i * 0.06), Draft.Anchor.SouthEast, compOperation )

    txtImg = Draft.Image.CreateAnnotation( slateText[i][1], annotationInfo )
    slateFrame.CompositeWithPositionAndAnchor( txtImg, 0.18, 0.7 - (i * 0.06), Draft.Anchor.SouthWest, compOperation )

#
# Initialize the video encoder.
#
print "Creating {3} video encoder ({0}x{1} @ {2}fps)".format( outWidth, outHeight, 24,  toCodec)
#encoder = Draft.VideoEncoder( params['outFile'] , 24, width=outWidth, height=outHeight, codec=toCodec )
encoder = Draft.VideoEncoder( params['outFile'], fps=24, width=outWidth, height=outHeight, quality=80, codec=toCodec )

#
# Create the slate frame
#
print "Creating the slate frame"
# Hold for 1 frame @ 24fps
#numberOfSlateFrames = 1
#for i in range( 0, numberOfSlateFrames ):
encoder.EncodeNextFrame( slateFrame )

#
# Create semi transparent mask
#

print "Creating semi transparent mask"

# Create the semi-transparent mask
ratio = float(params['projectRatio']) # The value 2.35 can be adjusted to fit your project's needs
maskRectHeight = int( round( ( outHeight - outWidth / ratio ) / 2 ) )
maskRect = Draft.Image.CreateImage( outWidth, maskRectHeight )
maskRect.SetChannel( 'A', 0.3 ) # The value 0.3 can be adjusted, higher the value, darker the mask

mask = Draft.Image.CreateImage( outWidth, outHeight )
mask.SetChannel( 'A', 0 )

# Upper mask
mask.CompositeWithAnchor( maskRect, Draft.Anchor.North, compOperation )
# Lower mask
mask.CompositeWithAnchor( maskRect, Draft.Anchor.South, compOperation )

# progress calculation var
progressCounter = 0
lastPercentage = -1

#
# Mask Anotations
#
annotationInfo.Color = Draft.ColorRGBA( 1.0, 1.0, 1.0, 1.0 )
annotationInfo.PointSize = int( outHeight * 0.020 ) # font size
#annotationInfo.FontType = "Helvetica"
annotationOffset = int( outHeight * 0.020 )*2;

# Anchor Points
northWest = {"x" : annotationOffset, "y" : annotationOffset}
southWest = {"x" : annotationOffset, "y" : outHeight-annotationOffset}
northEast = {"x" : outWidth - annotationOffset, "y" : annotationOffset}
southEast = {"x" : outWidth - annotationOffset, "y" : outHeight-annotationOffset}
#
## North West annotation
#projectNameAnnotation = Draft.Image.CreateAnnotation( params['projectName'] , annotationInfo)
#dateAnnotation = Draft.Image.CreateAnnotation(  datetime.datetime.now().strftime("%m/%d/%Y"), annotationInfo )
#
## North East annotation
#studioNameAnnotation = Draft.Image.CreateAnnotation( "VFXBOAT", annotationInfo ) # we should put the logo here
#
## South West annotation
## filaname - size => this annotation is made in the for loop
#descriptionAnnotation = Draft.Image.CreateAnnotation( params['projectDesc'] , annotationInfo)
#
## South East annotation
## frame number => this annotation is made up in the for loop
#artistAnnotation = Draft.Image.CreateAnnotation( params['username'], annotationInfo )

# North West annotation
projectNameAndDateAnnotation = Draft.Image.CreateAnnotation( params['projectName'] +"\n"+ datetime.datetime.now().strftime("%m/%d/%Y"), annotationInfo)

# North East annotation
studioNameAnnotation = Draft.Image.CreateAnnotation( "VFXBOAT", annotationInfo ) # we should put the logo here

# South West annotation
# filaname - size => this annotation is made in the for loop
descriptionAnnotation = Draft.Image.CreateAnnotation( params['projectDesc'] , annotationInfo)

# South East annotation
# frame number => this annotation is made up in the for loop
artistAnnotation = Draft.Image.CreateAnnotation( params['username'], annotationInfo )

#
# Processing the input images
#
print "Processing the input images"

for frameNum in frames:
    inFile = ReplaceFilenameHashesWithNumber( inputPath, frameNum )
    frame = Draft.Image.ReadFromFile( inFile )

    # Resize the frame if bigger than the out file size
    if frame.width != outWidth or frame.height != outHeight:
        ratio = float(frame.width) / float(frame.height)
        outWidth = int( round( 0.5 * ratio * outHeight ) * 2 ) # round width to nearest even number
        print "WARNING: Resizing image from {0}x{1} to {2}x{3}".format( frame.width, frame.height, outWidth, outHeight )
        frame.Resize( outWidth, outHeight, 'height' )

    # Add the semi-transparent mask
    print "Add the semi-transparent mask"
    frame.Composite( mask, 0, 0, compOperation )

    # Add burn ins
    # North West
    print "Add burn ins: North West"
    frame.CompositeWithAnchor( projectNameAndDateAnnotation , Draft.Anchor.NorthWest, compOperation )

    # North East
    print "Add burn ins: North East"
    frame.CompositeWithAnchor( studioNameAnnotation  , Draft.Anchor.NorthEast, compOperation )

    # South West annotation
    print "Add burn ins: South West"
    filenameAndSizeAnnotation = Draft.Image.CreateAnnotation( ("%s - %sx%s\n" % (inFile, frame.width, frame.height)), annotationInfo ) # added a \n for line break
    frame.CompositeWithAnchor( filenameAndSizeAnnotation, Draft.Anchor.SouthWest, compOperation )
    frame.CompositeWithAnchor( descriptionAnnotation , Draft.Anchor.SouthWest, compOperation )

    # South East annotation
    print "Add burn ins: South East"
    frameNumAnnotation = Draft.Image.CreateAnnotation( ("%s\n" % (frameNum) ), annotationInfo ) # added a \n for line break
    frame.CompositeWithAnchor( frameNumAnnotation  , Draft.Anchor.SouthEast, compOperation )
    frame.CompositeWithAnchor( artistAnnotation  , Draft.Anchor.SouthEast, compOperation )
#
#    # Add burn ins
#    # North West
#    print "Add burn ins: North West"
#    frame.CompositeWithPositionAndAnchor( projectNameAnnotation     , northWest["x"], northWest["y"], Draft.Anchor.North, compOperation )
#    frame.CompositeWithPositionAndAnchor( dateAnnotation            , northWest["x"], northWest["y"], Draft.Anchor.South, compOperation )
#
#    # North East
#    print "Add burn ins: North East"
#    frame.CompositeWithPositionAndAnchor( studioNameAnnotation      , northEast["x"], northEast["y"], Draft.Anchor.NorthEast, compOperation )
#
#    # South West annotation
#    print "Add burn ins: South West"
#    filenameAndSizeAnnotation = Draft.Image.CreateAnnotation( ("%s - %sx%s" % (inFile, frame.width, frame.height)), annotationInfo )
#    frame.CompositeWithPositionAndAnchor( filenameAndSizeAnnotation ,southWest["x"], southWest["y"], Draft.Anchor.North, compOperation )
#    frame.CompositeWithPositionAndAnchor( descriptionAnnotation     ,southWest["x"], southWest["y"], Draft.Anchor.South, compOperation )
#
#    # South East annotation
#    print "Add burn ins: South East"
#    frameNumAnnotation = Draft.Image.CreateAnnotation( ("%s" % (frameNum) ), annotationInfo )
#    frame.CompositeWithPositionAndAnchor( frameNumAnnotation        ,southEast["x"], southEast["y"], Draft.Anchor.NorthEast, compOperation )
#    frame.CompositeWithPositionAndAnchor( artistAnnotation          ,southEast["x"], southEast["y"], Draft.Anchor.SouthEast, compOperation )
#
    encoder.EncodeNextFrame( frame )

    progressCounter = progressCounter + 1
    percentage = progressCounter * 100 / len( frames )

    if percentage != lastPercentage:
        lastPercentage = percentage
        print "Encoding Progress: {0}%".format( percentage )

print "Finalizing encoding..."
encoder.FinalizeEncoding()
print "Done!"
