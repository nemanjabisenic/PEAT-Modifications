"""
CreateEvacuationSurface.py

written by: JM Jones, jmjones@usgs.gov
initial version:  May 2012 (v1), updated Oct 2017 (v1.1), updated Jul 2022 (python3), updated Jun 2023 (v2)

Usage:  createEvacSurface( ingdb, lc_scenario, speed_values )

Required Arguments:   ingdb - local database workspace (existing file geodatabase)
                      lc_scenario - string (text) of a scenario name that has been appended to an existing
                                      cost inverse raster (lc_cost_inverse_<scenarioname>.tif)
                      speed_values - string/text containing the decimal speed values separated by ';'
                                      example format: "0.89;1.2;1.52"
                                      the Pro tool window has these values restricted to positive decimals

Optional Arguments:   none

Returns:  For each speed entered, an evacuation surface is created and stored in the project raster storage
              These sufaces are in travel units of minutes (decimal values)

Description:
Checks for the needed rasters in the project gdb and then runs the Pro Distance Accumulation tool. After the
distance raster is calculated, a speed surface is generated for every input speed.

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
from runEvacuationCalculation import buildEvacSurface
from runDistanceAccumulation import runDistAcc

# Inputs are screened for existence and appropriate data type in the ArcPro tool window parameter settings.
def createEvacSurface( ingdb, scenario, speeds ):
    try:
        arcpy.env.overwriteOutput = True
        arcpy.env.workspace = ingdb

        # get gdb file names
        elevation = util.checkForTheFile(ingdb, 'elevation', filetype='raster' )
        studyareaR = util.checkForTheFile(ingdb, 'studyareaR', filetype='raster' )
        safezoneR = util.checkForTheFile(ingdb, 'safezoneR', filetype='raster' )
        costinv = util.checkForTheFile(ingdb,'costinv','raster',scenario )
        pathdist = util.getRasterStorage(ingdb,"{0}_{1}".format(util.getPEATfileName("pathdist"),scenario),
                                        names.SCENARIO,scenario)
        backlink = util.getRasterStorage(ingdb,"{0}_{1}".format(util.getPEATfileName("backlink"),scenario),
                                        names.SCENARIO,scenario)

        # Set environment variables based on dem and study area
        arcpy.env.extent = arcpy.Describe(studyareaR).Extent
        arcpy.env.snapRaster = elevation
        cellsize, demsr = util.getRasterCellAndSR( elevation )
        arcpy.env.outputCoordinateSystem = demsr
        arcpy.env.cellSize = cellsize

        # Break apart input speed table into a list of text speed values.
        speedvalues = speeds.split(";")

        # Set up the linear unit info for processing and screen for invalid coordinate system
        study_unit = demsr.linearUnitName
        conversion = util.get_linear_unit_conversion( study_unit )
        if conversion == 0.0:
            arcpy.AddError("Unable to determine the linear units for {0}".format(demsr.name))
            arcpy.AddError("Check DEM projection for a valid projected (not geodesic) coordinate system")
            raise util.JustExit

        # Run the Distance Accumulation tool to create the path distance raster
        runDistAcc( ingdb, safezoneR, costinv, pathdist, backlink)

        # Now use the speed values(s) to create evacuation time surfaces
        evaclist = []
        for textspeed in speedvalues:
            speedname = util.getTextNumber(textspeed)
            evactimes = util.getRasterStorage(ingdb,"{0}_{1}_{2}".format(util.getPEATfileName('evacsurf'),scenario,speedname),
                                              names.EVACSURF,scenario)
            evaclist.append(evactimes)
            arcpy.AddMessage("Generating evacuation surface for speed {0}".format(textspeed))

            buildEvacSurface(ingdb, pathdist, textspeed, conversion, evactimes )

        return evaclist

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
        start_speeds = arcpy.GetParameterAsText(2)
        end_evaclist = createEvacSurface( start_gdb, start_scenario, start_speeds )
        for end_each in end_evaclist:
            util.addLayerToMap( start_gdb, end_each, "evac_surface" )
        arcpy.SetParameterAsText(0, True)
    except Exception:
        arcpy.SetParameterAsText(0, False)

