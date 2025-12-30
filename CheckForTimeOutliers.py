"""
CheckForTimeOutliers.py

written by: JM Jones, jmjones@usgs.gov
initial version:  May 2012 (v1), updated Oct 2017 (v1.1), updated Jul 2022 (python3), updated Jun 2023 (v2)

Usage:  checkForOutliers( ingdb, lc_scenario, maxtimes )

Required Arguments:   ingdb - local database workspace (existing file geodatabase)
                      lc_scenario - string (text) of a scenario name that has been appended to an existing
                                      cost inverse raster (lc_cost_inverse_<scenarioname>.tif)
                      maxtimes - string (text) of evacuation surfaces and max times, separated by ';'
                                  evacuation surfaces are existing rasters for the input scenario and max times
                                  are decimal numbers representing minutes of travel time
                                  expected format: "filename1 80;filename2 94.5"
                                  the name should not contain the path or the file extension
Optional Arguments:   none

Returns:   The original evacuation surfaces with new max times are reclassed and stored in their original location
          in the project raster storage.

Description:
This tool is OPTIONAL and is not required to be run during the evacuation processing.
Takes the evacuation surface(s) and screens for maximum. The maximum value in each input raster
is evaluated and compared against the input maximum time.  If the input time is greater than the maximum, all
values in the raster greater than the maximum time are reclassed to the maximum time.

This software has been approved for release by the U.S. Geological Survey (USGS).
Although the software has been subjected to rigorous review, the USGS reserves the
right to update the software as needed pursuant to further analysis and review. No
warranty, expressed or implied, is made by the USGS or the U.S. Government as to the
functionality of the software and related material nor shall the fact of release
constitute any such warranty. Furthermore, the software is released on condition that
neither the USGS nor the U.S. Government shall be held liable for any damages resulting
from its authorized or unauthorized use.
"""
import traceback, arcpy, math
from PEATutil import EvacUtilities as util
from PEATutil import PEATnames as names

# Inputs are screened for existence and appropriate data type in the ArcPro tool window parameter settings.
def checkForOutliers( ingdb, scenario, maxtimes ):
    try:
        arcpy.env.overwriteOutput = True
        arcpy.env.workspace = ingdb

        # get gdb file names
        elevation = util.checkForTheFile(ingdb, 'elevation', filetype='raster' )
        studyareaR = util.checkForTheFile(ingdb, 'studyareaR', filetype='raster' )

        # Set environment variables based on dem and study area
        arcpy.env.extent = arcpy.Describe(studyareaR).Extent
        arcpy.env.snapRaster = elevation
        cellsize, demsr = util.getRasterCellAndSR( elevation )
        arcpy.env.outputCoordinateSystem = demsr
        arcpy.env.cellSize = cellsize

        # Preprocess the evacuation time surface(s) to remove out-of-range peak values.
        # These are values greater than max-time that appear in areas of steep elevation change.
        # First, check that the max value in the raster is greater than max-time.  If not,
        # just skip over it.
        maxsurface = {}
        inevaclist = maxtimes.split(";")
        for each in inevaclist:
            evacname = util.getRasterStorage(ingdb,each.split(" ")[0],names.EVACSURF,scenario)
            maxevactime = int(each.split(" ")[1])
            if maxevactime > 0:
                maxsurface[evacname] = maxevactime

        display_surface = []
        arcpy.CheckOutExtension("Spatial")
        for evac_surface in maxsurface.keys():
            max_time = maxsurface[evac_surface]
            result = arcpy.GetRasterProperties_management( evac_surface, "MAXIMUM" )
            maxval = int(math.ceil(float(result.getOutput(0))))
            if maxval > max_time:
                arcpy.AddMessage("For {0}, reclassing max time from {2} to {1}".format(evac_surface,max_time,maxval))
                testfor = "VALUE > %s" %max_time
                outCon = arcpy.sa.Con(evac_surface, max_time, evac_surface, testfor)
                outCon.save(evac_surface)
                arcpy.CalculateStatistics_management(evac_surface)
                arcpy.BuildPyramids_management(evac_surface)
                display_surface.append(evac_surface)
                arcpy.AddMessage("Evacuation surface raster has been updated at {0}".format(evac_surface))
            else:
                arcpy.AddMessage("No max time adjustment needed for {0}".format(evac_surface))

        arcpy.CheckInExtension("Spatial")
        return display_surface

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
        start_maxtime = arcpy.GetParameterAsText(2)
        fordisplay = checkForOutliers( start_gdb, start_scenario, start_maxtime )
        for end_each in fordisplay:
            util.addLayerToMap( start_gdb, end_each, "evac_surface" )
        arcpy.SetParameterAsText(0, True)
    except Exception:
        arcpy.SetParameterAsText(0, False)
