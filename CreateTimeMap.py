"""
TimeMapSurface.py

written by: JM Jones, jmjones@usgs.gov
initial version:  May 2012 (v1), updated Oct 2017 (v1.1), updated Jul 2022 (python3), updated Jun 2023 (v2)

Usage:  genTimes( ingdb, lc_scenario, inevacs, buildings)

Required Arguments:   ingdb - local database workspace (existing file geodatabase)
                      lc_scenario - string (text) of a scenario name that has been appended to an existing
                                      cost inverse raster (lc_cost_inverse_<scenarioname>.tif)
                      inevacs - string (text) of existing evacuation surfaces for the given scenario, separated by ';'
                                  expected format: "evacsurf1;evacsurf2"
                                  the name should not contain the path or the file extension

Optional Arguments:   buildings - polygon feature class representing building locations to be filled in the time map,
                                  this should be the same polygon layer that was entered during landcover preprocessing
                                  with an scv value of 0.0

Returns:  A raster and feature time map are created for each evacuation surface selected,
              and they are written to the project feature class and raster storage
          These maps are in units of minutes of travel times (rounded up to the nearest integer)

Description:
Takes the evacuation surface(s) and converts them to integer values at 1-minute increments.
These are saved as both raster and vector. If building outlines are entered,
the time maps are generated with the building footprints filled in with surrounding values.
This filling creates a smooth surface for use when using population points to extract travel times.

This software has been approved for release by the U.S. Geological Survey (USGS).
Although the software has been subjected to rigorous review, the USGS reserves the
right to update the software as needed pursuant to further analysis and review. No
warranty, expressed or implied, is made by the USGS or the U.S. Government as to the
functionality of the software and related material nor shall the fact of release
constitute any such warranty. Furthermore, the software is released on condition that
neither the USGS nor the U.S. Government shall be held liable for any damages resulting
from its authorized or unauthorized use.
"""
import os, traceback, arcpy
from PEATutil import EvacUtilities as util
from PEATutil import PEATnames as names
import runTimeMapCalculation as tmrv

# Inputs are screened for existence and appropriate data type in the ArcPro tool window parameter settings.
def genTimes( ingdb, scenario, inevacs, inbuildings):
    try:
        arcpy.env.overwriteOutput = True
        arcpy.env.workspace = ingdb

        # get gdb file names
        elevation = util.checkForTheFile(ingdb, 'elevation', filetype='raster' )
        studyareaR = util.checkForTheFile(ingdb, 'studyareaR', filetype='raster' )
        studyareaV = util.checkForTheFile(ingdb, 'studyareaV', filetype='vector' )
        safezoneV = util.checkForTheFile(ingdb,'safezoneV', filetype='vector')
        buildings = util.getFeatureStorage(ingdb,util.getPEATfileName('buildings'),names.ROOT)

        # Set environment variables based on dem and study area
        arcpy.env.extent = arcpy.Describe(studyareaR).Extent
        arcpy.env.snapRaster = elevation
        cellsize, demsr = util.getRasterCellAndSR( elevation )
        arcpy.env.outputCoordinateSystem = demsr
        arcpy.env.cellSize = cellsize

        # Split the surface entries and turn into a list and check for buildings
        evacs = [util.getRasterStorage(ingdb,name,names.EVACSURF,scenario) for name in inevacs.split(";")]

        if inbuildings:
            util.screenInputVector(ingdb,inbuildings,demsr,studyareaV,buildings)
            arcpy.AddMessage("Buildings layer for fill: {0}".format(os.path.join(ingdb,buildings)))
        else:
            buildings = ""

        #Generate the time map raster surface and vector files from the evacuation surfaces
        rastermaps,featuremaps = tmrv.genTimesRasterVector( ingdb, scenario, evacs, safezoneV, buildings)
        return rastermaps,featuremaps

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
        start_scenario = arcpy.GetParameterAsText(1)
        start_surface = arcpy.GetParameterAsText(2)
        start_buildings = arcpy.GetParameterAsText(3)
        end_rastermaps,end_featuremaps = genTimes( start_gdb, start_scenario, start_surface, start_buildings )
        for end_each in end_rastermaps:
            util.addLayerToMap(start_gdb,end_each,"time_map")
        for end_each in end_featuremaps:
            util.addLayerToMap(start_gdb,end_each,"time_map")
        arcpy.SetParameterAsText(0, True)
    except Exception:
        arcpy.SetParameterAsText(0, False)
