"""
preprocessSafezone.py

written by: JM Jones, jmjones@usgs.gov
initial version:  May 2012 (v1), updated Oct 2017 (v1.1), updated Jul 2022 (python3), updated Aug 2023 (v2)

Usage:  prepareSafezone( ingdb, safezone )

Required Arguments:   ingdb - local database workspace (existing file geodatabase)
                      safezone - polygon feature class

Optional Arguments:   none

Returns:   The safezone entered as an argument is stored in the project storage in both polygon and raster format.
          This becomes the safezone used in subsequent processing.

Description:
Makes a project copy of a validated safe zone. The user can input a new file here that is known to be correct, or
point to the preliminary safe zone in the project gdb that has been edited to remove slivers.

This software has been approved for release by the U.S. Geological Survey (USGS).
Although the software has been subjected to rigorous review, the USGS reserves the
right to update the software as needed pursuant to further analysis and review. No
warranty, expressed or implied, is made by the USGS or the U.S. Government as to the
functionality of the software and related material nor shall the fact of release
constitute any such warranty. Furthermore, the software is released on condition that
neither the USGS nor the U.S. Government shall be held liable for any damages resulting
from its authorized or unauthorized use.
"""
import os, traceback
import arcpy
from PEATutil import EvacUtilities as util
from PEATutil import PEATnames as names

# Inputs are screened for existence and appropriate data type in the ArcPro tool window parameter settings.
def prepareSafezone( ingdb, safezone ):
    try:
        arcpy.env.overwriteOutput = True

        arcpy.env.workspace = ingdb
        elevation = util.checkForTheFile(ingdb, 'elevation', filetype='raster' )
        studyareaV = util.checkForTheFile(ingdb, 'studyareaV', filetype='vector' )
        studyareaR = util.checkForTheFile(ingdb, 'studyareaR', filetype='raster' )

        # Set up the environment for raster processing
        arcpy.env.extent = arcpy.Describe(studyareaR).Extent
        arcpy.env.snapRaster = elevation
        cellsize, demsr = util.getRasterCellAndSR( elevation )
        arcpy.env.outputCoordinateSystem = demsr
        arcpy.env.cellSize = cellsize

        # Get new file names
        safezoneV = util.getFeatureStorage(ingdb,util.getPEATfileName( 'safezoneV' ), names.ROOT)
        safezoneR = util.getRasterStorage(ingdb, util.getPEATfileName( 'safezoneR' ), names.ROOT)

        # Check projection, clip to the study area and store it as the project safe zone.
        util.screenInputVector(ingdb,safezone,demsr,studyareaV,safezoneV)

        #make a raster copy of the safe zone
        saferaster = util.getRasterStorage(ingdb, 'saferaster',names.SCRATCH)
        util.cleanUpIntermediateFiles([saferaster])
        oidname = arcpy.Describe(safezoneV).OIDFieldName
        arcpy.PolygonToRaster_conversion(safezoneV,oidname,saferaster,"CELL_CENTER","#",cellsize)
        arcpy.CheckOutExtension("Spatial")
        outSlice = arcpy.sa.Slice(saferaster, 1,"EQUAL_INTERVAL")
        outSlice.save(safezoneR)
        arcpy.CheckInExtension("Spatial")
        util.cleanUpIntermediateFiles([saferaster])

        arcpy.AddMessage("Safe zone raster has been stored at {0}".format(safezoneR))
        arcpy.AddMessage("Safe zone vector has been stored at {0}".format(os.path.join(ingdb, safezoneV)))

    except arcpy.ExecuteError:
        arcpy.AddError(arcpy.GetMessages(2))
        raise
    except util.JustExit:
        raise
    except Exception:
        arcpy.AddError(traceback.format_exc())
        raise

if __name__ == "__main__":
    try:
        start_gdb = arcpy.GetParameterAsText(0)
        start_safezone = arcpy.GetParameterAsText(1)
        prepareSafezone( start_gdb, start_safezone )
        arcpy.SetParameterAsText(0, True)
    except Exception:
        arcpy.SetParameterAsText(0, False)
