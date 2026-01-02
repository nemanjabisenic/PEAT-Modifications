"""
runEvacuationCalculation.py

written by: JM Jones, jmjones@usgs.gov
initial version:  May 2012 (v1), updated Oct 2017 (v1.1), updated Jul 2022 (python3), updated Jun 2023 (v2)

Description:
Creates the evacuation surface from the distance accumulation raster and the input speed

This software has been approved for release by the U.S. Geological Survey (USGS).
Although the software has been subjected to rigorous review, the USGS reserves the
right to update the software as needed pursuant to further analysis and review. No
warranty, expressed or implied, is made by the USGS or the U.S. Government as to the
functionality of the software and related material nor shall the fact of release
constitute any such warranty. Furthermore, the software is released on condition that
neither the USGS nor the U.S. Government shall be held liable for any damages resulting
from its authorized or unauthorized use.
"""
import traceback
import arcpy
from PEATutil import EvacUtilities as util
from PEATutil import PEATnames as names

# Inputs are screened by the calling function.
def buildEvacSurface(ingdb, pathdist, textspeed, conversion, evactimes ):
    try:
        arcpy.env.overwriteOutput = True
        arcpy.env.workspace = ingdb

        # get needed file names
        elevation = util.getRasterStorage(ingdb,util.getPEATfileName( 'elevation' ),names.ROOT)
        studyareaR = util.getRasterStorage(ingdb,util.getPEATfileName( 'studyareaR' ),names.ROOT)

        # Set environment variables based on dem and study area
        arcpy.env.extent = arcpy.Describe(studyareaR).Extent
        arcpy.env.snapRaster = elevation
        cellsize, demsr = util.getRasterCellAndSR( elevation )
        arcpy.env.outputCoordinateSystem = demsr
        arcpy.env.cellSize = cellsize

        #Convert metric speed to local linear unit speed (if already metric, speed won't change)
        metric_speed = float(textspeed)
        speed = metric_speed / conversion
        aniso_seconds = util.getRasterStorage(ingdb,"aniso_seconds",names.SCRATCH)
        util.cleanUpIntermediateFiles([aniso_seconds])
        seconds_to_minutes = 60.0

        # Create the least evacuation time surface
        inv_speed = 1.0 / speed
        arcpy.CheckOutExtension("Spatial")
        outTimes = arcpy.sa.Times( pathdist, inv_speed )
        outTimes.save(aniso_seconds)
        outDivide = arcpy.sa.Divide( aniso_seconds, seconds_to_minutes )
        outDivide.save(evactimes)
        arcpy.CheckInExtension("Spatial")
        util.cleanUpIntermediateFiles([aniso_seconds])
        arcpy.CalculateStatistics_management( evactimes )
        arcpy.BuildPyramids_management( evactimes )
        arcpy.AddMessage("Evacuation surface raster has been stored at {0}".format(evactimes))

    except arcpy.ExecuteError:
        arcpy.AddError(arcpy.GetMessages(2))
        raise
    except util.JustExit:
        raise
    except Exception:
        arcpy.AddError(traceback.format_exc())
        raise
