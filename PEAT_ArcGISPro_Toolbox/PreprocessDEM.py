"""
preprocessDEM.py

written by: JM Jones, jmjones@usgs.gov
initial version:  May 2012 (v1), updated Oct 2017 (v1.1), updated Jul 2022 (python3), updated Jun 2023 (v2)

Usage:  preDEM( ingdb, elevation, study_area)

Required Arguments:   ingdb - local database workspace (existing file geodatabase)
                      elevation - raster

Optional Arguments:   study_area - polygon feature class

Returns:   The elevation raster (trimmed to study area if needed) is stored in the project raster storage, and
          the study area (projected if needed) is stored in both polygon and raster format use in for subsequent
          processing.

Description:
  This is the first tool in the processing sequence.  The input dem defines the projection
  and the cell size for the processing.  If a study area is provided, the dem will be
  masked to the study area size.  If the study area is at a different projection from the dem,
  it will be reprojected to the dem spatial reference.  If no study area is provided, the dem
  outline is used to define the processing study area.

This software has been approved for release by the U.S. Geological Survey (USGS).
Although the software has been subjected to rigorous review, the USGS reserves the
right to update the software as needed pursuant to further analysis and review. No
warranty, expressed or implied, is made by the USGS or the U.S. Government as to the
functionality of the software and related material nor shall the fact of release
constitute any such warranty. Furthermore, the software is released on condition that
neither the USGS nor the U.S. Government shall be held liable for any damages resulting
from its authorized or unauthorized use.
"""
import os,traceback
import arcpy
from PEATutil import EvacUtilities as util
from PEATutil import PEATnames as names

# Inputs are screened for existence and appropriate data type in the ArcPro tool window parameter settings.
def preDEM( ingdb, DEMinput, studyArea ):
    try:
        arcpy.env.overwriteOutput = True

        # Set environment variables based on dem
        arcpy.env.workspace = ingdb
        arcpy.env.snapRaster = DEMinput
        cellsize, demsr = util.getRasterCellAndSR( DEMinput )
        arcpy.env.outputCoordinateSystem = demsr
        arcpy.env.cellSize = cellsize

        # Get the output file names for the project gdb
        elevation = util.getRasterStorage(ingdb, util.getPEATfileName( 'elevation' ),names.ROOT)
        studyareaV = util.getPEATfileName( 'studyareaV' )
        studyareaR = util.getRasterStorage(ingdb, util.getPEATfileName( 'studyareaR'),names.ROOT)

        #check for study area vector and create one if necessary
        if studyArea == '':
            #no study area vector given so create one from the dem, also save dem in gdb
            arcpy.AddMessage("Creating study area vector and raster from DEM")
            arcpy.CheckOutExtension("Spatial")
            outSlice = arcpy.sa.Slice( DEMinput, 1, "EQUAL_INTERVAL", base_output_zone=1)
            outSlice.save(studyareaR)
            arcpy.CheckInExtension("Spatial")
            arcpy.RasterToPolygon_conversion(studyareaR, studyareaV,"NO_SIMPLIFY",max_vertices_per_feature=100000)
            arcpy.CopyRaster_management(DEMinput,elevation)
        else:  # studyArea provided
            arcpy.AddMessage("Creating study area raster from input study area and masking DEM")
            # First check the projection of the input study area and project to DEM SR if needed
            studysr = arcpy.Describe(studyArea).SpatialReference
            if studysr.Name != demsr.Name:
                util.projectFeatureClass(studyArea, demsr, studyareaV, ingdb)
            else:  # copy the study area into the project gdb
                arcpy.CopyFeatures_management(studyArea, studyareaV)

            # Convert the study area feature class into a raster with all values set to 1, then mask the input
            # dem by the study area raster
            tempraster = util.getRasterStorage(ingdb,'temp_studyr',names.SCRATCH)
            util.cleanUpIntermediateFiles([tempraster])
            OIDFieldName = arcpy.Describe(studyareaV).OIDFieldName
            arcpy.CheckOutExtension("Spatial")
            arcpy.PolygonToRaster_conversion(studyareaV,OIDFieldName,tempraster,"CELL_CENTER",cellsize=cellsize)
            outSlice = arcpy.sa.Slice(tempraster, 1, "EQUAL_INTERVAL", base_output_zone=1 )
            outSlice.save(studyareaR)
            util.cleanUpIntermediateFiles([tempraster])
            outExtract = arcpy.sa.ExtractByMask(DEMinput, studyareaR)
            outExtract.save(elevation)
            arcpy.CheckInExtension("Spatial")

        arcpy.CalculateStatistics_management( studyareaR )
        arcpy.CalculateStatistics_management( elevation )
        arcpy.BuildPyramids_management( studyareaR )
        arcpy.BuildPyramids_management( elevation )
        arcpy.AddMessage("Elevation raster has been stored at {0}".format(elevation))
        arcpy.AddMessage("Study area raster has been stored at {0}".format(studyareaR))
        arcpy.AddMessage("Study area vector has been stored at {0}".format(os.path.join(ingdb,studyareaV)))
        return elevation

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
        start_dem = arcpy.GetParameterAsText(1)
        start_study = arcpy.GetParameterAsText(2)
        end_dem = preDEM( start_gdb, start_dem, start_study )
        util.addLayerToMap(start_gdb,end_dem,"elevation")
        arcpy.SetParameterAsText(0, True)
    except Exception:
        arcpy.SetParameterAsText(0, False)
