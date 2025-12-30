"""
runDistanceAccumulation.py

written by: JM Jones, jmjones@usgs.gov
initial version:  May 2012 (v1), updated Oct 2017 (v1.1), updated Jul 2022 (python3), updated Jun 2023 (v2)

Description:
Sets up and runs the Distance accumulation tool.

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

# Inputs are screened in the calling function.
def runDistAcc( ingdb, saferaster, costinv, pathdist, backlink ):
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

        # get the location of the code, since the Tobler file is stored in the same folder
        codepath = os.path.dirname(__file__)
        verticalFactor = os.path.join( codepath, "Tobler.txt" )

        # Generate the least cost path surface
        arcpy.AddMessage("running distance accumulation...")
        arcpy.CheckOutExtension("Spatial")

        outdist = arcpy.sa.DistanceAccumulation(in_source_data=saferaster,
                                                in_surface_raster=elevation,
                                                in_cost_raster=costinv,
                                                in_vertical_raster=elevation,
                                                vertical_factor=arcpy.sa.VfTable(verticalFactor),
                                                horizontal_factor=arcpy.sa.HfBinary(1.0, 45),
                                                out_back_direction_raster=backlink,
                                                distance_method="PLANAR")
        outdist.save(pathdist)

        arcpy.CheckInExtension("Spatial")
        arcpy.CalculateStatistics_management( pathdist )
        arcpy.AddMessage("Distance accumulation raster has been stored at {0}".format(pathdist))

    except arcpy.ExecuteError:
        arcpy.AddError(arcpy.GetMessages(2))
        raise
    except util.JustExit:
        raise
    except Exception:
        arcpy.AddError(traceback.format_exc())
        raise
