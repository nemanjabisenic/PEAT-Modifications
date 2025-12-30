"""
CalcSpeedMap.py

written by: JM Jones, jmjones@usgs.gov
initial version:  May 2012 (v1), updated Oct 2017 (v1.1), updated Jul 2022 (python3), updated Jun 2023 (v2)

Usage:  genSpeeds( ingdb, scenario, timemapin, event_arrival, delay_time )

Required Arguments:   ingdb - local database workspace (existing file geodatabase)
                      lc_scenario - string (text) of a scenario name that has been appended to an existing
                                      cost inverse raster (lc_cost_inverse_<scenarioname>.tif)
                      time_maps - string (text) of time map names, separated by ';'
                                  expected format: 'timemap1;timemap2;timemap3'
                                  the name should not contain the path or the file extension
                      arrival - time in  minutes (integer) of expected event arrival

Optional Arguments:   delay - time in minutes (integer) of expected delay after event arrival and before evacuation
                              starts

Returns:  One raster and one feature speed map are created from the input time maps, and the speed maps are stored
          in the project raster and feature storage.
          The raster speed map (integer) contains the speeds multiplied by 100, with cells beyond safe evacuation
          at any of the input speeds set to the value 999.  The vector speed map has a column in the attribute
          table called 'SPEED' which shows the original speed values and 999 if needed.

Description:
Takes selected input time map rasters generated with different travel speeds and converts each to a speed map, then
merges all maps together, converts to polygons for additional analysis with the population layers.

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

codeblock = """def getDiv(a):
    if a < 900:
        return a/100.0
    else:
        return a"""

# Inputs are screened for existence and appropriate data type in the ArcPro tool window parameter settings.
def genSpeeds( ingdb, scenario, timemapin, event_arrival, delay_time ):
    try:
        arcpy.env.overwriteOutput = True
        arcpy.env.workspace = ingdb

        # get gdb file names and check that needed files are in the gdb
        elevation = util.checkForTheFile(ingdb, 'elevation', filetype='raster' )
        studyareaR = util.checkForTheFile(ingdb, 'studyareaR', filetype='raster' )
        speedmapR = util.getPEATfileName('speedmapR')
        speedmapV = util.getPEATfileName('speedmapV')

        # Set environment variables based on dem and study area
        arcpy.env.extent = arcpy.Describe(studyareaR).Extent
        arcpy.env.snapRaster = elevation
        cellsize, demsr = util.getRasterCellAndSR( elevation )
        arcpy.env.outputCoordinateSystem = demsr
        arcpy.env.cellSize = cellsize

        # Split the time map entries and turn into a list.
        timemaps = [util.getRasterStorage(ingdb,name,names.TIMEMAP,scenario) for name in timemapin.split(";")]

        # Determine the limit for safe evacuation by subtracting an optional delay time from the expected event
        # arrival time.  The delay time makes allowances for people who may take a few minutes before starting
        # to move.  Another minute is also subtracted to make sure evacuation can be completed successfully.
        if not delay_time:
            delay_time = "0"
        travel_limit = int(event_arrival) - int(delay_time) - 1
        if travel_limit <= 0:
            arcpy.AddError("The event arrival time must be greater than the delay time")
            raise util.JustExit

        arcpy.AddMessage("Event arrival: {0}, delay: {1}".format(event_arrival,delay_time))

        relayers = []
        for ind, inlayer in enumerate(timemaps):
            arcpy.AddMessage("Processing time map {0}".format(inlayer))
            inspeed, nused = util.getTravelSpeed(inlayer)
            numspeed = int(float(inspeed) * 100)
            relayer = util.getRasterStorage(ingdb, "respd_{0}".format(str(ind)),names.SCRATCH)
            util.cleanUpIntermediateFiles([relayer])

            # Reclassify each raster for the expected travel time, setting every value within the travel limit
            # to the map's speed.  All other values get set to 999.
            arcpy.CheckOutExtension("Spatial")
            remaprg =  arcpy.sa.RemapRange([[0,travel_limit,numspeed],[travel_limit,999,999]])
            outreclass = arcpy.sa.Reclassify(inlayer, 'Value', remaprg)
            outreclass.save(relayer)
            arcpy.CheckInExtension("Spatial")
            relayers.append(relayer)

        # mosaic all reclassed rasters into one raster, choosing the slowest valid speed for each cell.
        speed_display = []
        speedR = util.getRasterStorage(ingdb,"{0}_{1}_{2}_{3}".format(speedmapR,scenario,event_arrival,delay_time),
                                       names.SPEEDMAP,scenario)
        speedV = util.getFeatureStorage(ingdb,"{0}_{1}_{2}_{3}".format(speedmapV,scenario,event_arrival,delay_time),
                                        names.SPEEDMAP,scenario,demsr)
        speed_display.append(speedR)
        speed_display.append(speedV)
        if len(relayers) > 1:
            arcpy.Mosaic_management( relayers, relayers[0], mosaic_type="MINIMUM" )
        arcpy.CalculateStatistics_management( relayers[0])
        arcpy.BuildRasterAttributeTable_management( relayers[0], overwrite=True)

        # Make sure that 0 values are set to NoData
        result = arcpy.sa.SetNull(relayers[0],relayers[0],"VALUE = 0")
        result.save(speedR)
        util.cleanUpIntermediateFiles(relayers)
        arcpy.CalculateStatistics_management( speedR )
        arcpy.BuildPyramids_management( speedR )
        arcpy.AddMessage("Speed map raster has been stored at {0}".format(speedR))

        # Convert raster to vector on Value, using the integer version of the raster for conversion
        tempspeed = util.getFeatureStorage(ingdb,"tempspeed",names.SCRATCH,spatialref=demsr)
        dicespeed = util.getFeatureStorage(ingdb,"dicespeed",names.SCRATCH,spatialref=demsr)
        arcpy.RasterToPolygon_conversion( speedR, tempspeed, "NO_SIMPLIFY", "VALUE",
                                          max_vertices_per_feature=100000)
        arcpy.RecalculateFeatureClassExtent_management(tempspeed)
        arcpy.RepairGeometry_management( tempspeed, "DELETE_NULL" )
        arcpy.Dissolve_management( tempspeed, dicespeed, "GRIDCODE" )
        arcpy.Dice_management(dicespeed,speedV,vertex_limit=100000)
        util.cleanUpIntermediateFiles([tempspeed,dicespeed])

        # Add a field for the decimal speed value and calculate by dividing gridcode by 100.  If gridcode is 999,
        # leave this value in for final speed (for areas outside of reach before event arrival).
        speedfield = "SPEED"
        arcpy.AddField_management( speedV, speedfield, "DOUBLE", 8,4)
        expression = "getDiv(!GRIDCODE!)"
        arcpy.CalculateField_management( speedV, speedfield, expression, "PYTHON3", codeblock)
        arcpy.DeleteField_management(speedV,"GRIDCODE")
        arcpy.AddMessage("Speed map polygon has been stored at {0}".format(os.path.join(ingdb,speedV)))

        return speed_display

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
        start_timemaps = arcpy.GetParameterAsText(2)
        start_arrival = arcpy.GetParameterAsText(3)
        start_delay = arcpy.GetParameterAsText(4)
        end_display = genSpeeds( start_gdb, start_scenario, start_timemaps, start_arrival, start_delay )
        util.addLayerToMap(start_gdb,end_display[1],"speed_map")
        util.addLayerToMap(start_gdb,end_display[0],"speed_map")
        arcpy.SetParameterAsText(0, True)
    except Exception:
        arcpy.SetParameterAsText(0, False)
