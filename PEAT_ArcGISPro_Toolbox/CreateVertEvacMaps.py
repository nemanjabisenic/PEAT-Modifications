"""
CreateVertEvacMaps.py

written by: JM Jones, jmjones@usgs.gov
initial version:  May 2012 (v1), updated Oct 2017 (v1.1), updated Jul 2022 (python3), updated Jun 2023 (v2)

Usage:  createVertEvacs( ingdb, lc_scenario, Base_map, VE_features, VE_number_field )

Required Arguments:   ingdb - local database workspace (existing file geodatabase)
                      lc_scenario - string (text) of a scenario name that has been appended to an existing
                                      cost inverse raster (lc_cost_inverse_<scenarioname>.tif)
                      Base_map - string (text) name of an existing time map for the selected scenario
                      VE_features - polygon feature class
                      VE_number_field - attribute column name in the VE_features file that contains unique
                                          identifying integers for the VE (Vertical Evacuation) structures

Optional Arguments:   none

Returns:  raster time maps and feature time maps are written to the project storage
          raster version of the safe zone used for each VE run is written to the raster project storage

Description:
Creates the vertical evacuation time maps by creating a new safe zone (by merging the original safe zone with
a VE polygon) and runs the distance accumulation, evacuation surface, and time map processing.

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
from runTimeMapCalculation import genTimesRasterVector

# Inputs are screened for existence and appropriate data type in the ArcPro tool window parameter settings.
def createVertEvacs( ingdb, scenario, basemap, vertinput, colname ):
    try:
        arcpy.env.overwriteOutput = True
        arcpy.env.workspace = ingdb

        # get gdb file names
        elevation = util.checkForTheFile(ingdb, 'elevation', filetype='raster' )
        studyareaR = util.checkForTheFile(ingdb, 'studyareaR', filetype='raster' )
        studyareaV = util.checkForTheFile(ingdb,'studyareaV', filetype='vector' )
        safezoneV = util.checkForTheFile(ingdb, 'safezoneV', filetype='vector' )
        costinv = util.checkForTheFile(ingdb,"costinv",'raster',scenario)

        # Set environment variables based on dem and study area
        arcpy.env.extent = arcpy.Describe(studyareaR).Extent
        arcpy.env.snapRaster = elevation
        cellsize, demsr = util.getRasterCellAndSR( elevation )
        arcpy.env.outputCoordinateSystem = demsr
        arcpy.env.cellSize = cellsize

        # Get buildings name if it exists
        buildings = util.getFeatureStorage(ingdb,util.getPEATfileName("buildings"),names.ROOT)
        if not arcpy.Exists(buildings):
            buildings = ""

        # Check if a buildings layer was used during the cost inverse processing
        if basemap.count('filled') and buildings:
            arcpy.AddMessage("Buildings feature class from GDB: {0}".format(buildings))
        else:
            buildings = ""

        # get speed and conversion factor
        textspeed,speedname = util.getTravelSpeed(basemap)
        study_unit = demsr.linearUnitName
        conversion = util.get_linear_unit_conversion( study_unit )

        # screen VE file and check for duplicates
        screenedVEs = util.getFeatureStorage(ingdb,"screenedVEs",names.SCRATCH,spatialref=demsr)
        util.screenInputVector(ingdb,vertinput,demsr,studyareaV,screenedVEs)
        startVEs = [row[0] for row in arcpy.da.SearchCursor(screenedVEs,colname)]
        VElist = list(set(startVEs))
        if len(startVEs) > len(VElist):
            arcpy.AddError("Duplicate vertical evacuation structure names found in input file {0}".format(vertinput))
            raise util.JustExit

        vertlayer = "layer"
        arcpy.MakeFeatureLayer_management(screenedVEs,vertlayer)

        rasterVEs = []
        featureVEs = []
        for oneVE in VElist:
            arcpy.AddMessage("processing VE {0}".format(oneVE))
            # Create a new safe zone from the original safe zone and the current VE polygon
            newsafeR, venum = makeNewSafeZone(ingdb, vertlayer, safezoneV, cellsize, vertinput, colname, oneVE,
                                              speedname, scenario)

            # Call distance accumulation
            pathdist = util.getRasterStorage(ingdb,"{0}_{1}_{2}".format(util.getPEATfileName("pathdist"),scenario,venum),
                                                names.VEMAP,scenario,speedname,venum)
            backlink = util.getRasterStorage(ingdb, "{0}_{1}_{2}".format(util.getPEATfileName("backlink"),scenario,venum),
                                                names.VEMAP,scenario,speedname,venum)
            runDistAcc( ingdb, newsafeR, costinv, pathdist, backlink)

            # Build the time surface
            evactimes = util.getRasterStorage(ingdb,
                                 "{0}_{1}_{2}_{3}".format(util.getPEATfileName("evacsurf"),scenario,venum,speedname),
                                              names.VEMAP,scenario,speedname,venum)
            buildEvacSurface( ingdb, pathdist, textspeed, conversion, evactimes)

            # Create the time map
            rastermaps,featuremaps = genTimesRasterVector(ingdb,scenario,[evactimes],safezoneV,buildings,venum)

            rasterVEs.append(rastermaps[0])
            featureVEs.append(featuremaps[0])

        util.cleanUpIntermediateFiles([screenedVEs,vertlayer])
        return rasterVEs, featureVEs

    except arcpy.ExecuteError:
        arcpy.AddError(arcpy.GetMessages(2))
        raise
    except util.JustExit:
        raise
    except Exception:
        arcpy.AddError(traceback.format_exc())
        raise


def makeNewSafeZone(ingdb, inlayer, origsafe, cellsize, vertin, vertcol, vertnum, textspeed, scenario ):
    """ Select the VE polygon, copy into a new feature class, merge with the original safe zone, and create a
    new raster version of the safe zone """
    try:
        arcpy.env.overwriteOutput = True
        newsafe = util.getFeatureStorage(ingdb,"newsafe",names.SCRATCH)
        tempras = util.getRasterStorage(ingdb,"tempras",names.SCRATCH)
        singleve = util.getFeatureStorage(ingdb,"singleve",names.SCRATCH)
        whereclause = """{0} = {1}""".format(arcpy.AddFieldDelimiters(vertin, vertcol),vertnum)
        arcpy.SelectLayerByAttribute_management(inlayer, "NEW_SELECTION", whereclause)
        arcpy.CopyFeatures_management(inlayer, singleve)
        arcpy.Merge_management([origsafe,singleve],newsafe)
        arcpy.PolygonToRaster_conversion(newsafe, arcpy.Describe(newsafe).OIDFieldName,
                                         tempras,"CELL_CENTER","#", cellsize)

        venum = "VE{0}".format(vertnum)
        arcpy.CheckOutExtension("Spatial")
        outSlice = arcpy.sa.Slice(tempras, 1,"EQUAL_INTERVAL")
        newsafeR = util.getRasterStorage(ingdb,"safezone_{0}".format(venum),names.VEMAP,scenario,textspeed,venum)
        outSlice.save(newsafeR)
        arcpy.CheckInExtension("Spatial")

        arcpy.Delete_management([singleve,newsafe,tempras])
        return newsafeR, venum

    except arcpy.ExecuteError:
        arcpy.AddError(arcpy.GetMessages(2))
        raise
    except Exception:
        arcpy.AddError(traceback.format_exc())
        raise

if __name__ == "__main__":
    try:
        start_gdb = arcpy.GetParameterAsText(0)
        start_scenario = arcpy.GetParameterAsText(1)
        start_basemap = arcpy.GetParameterAsText(2)
        start_vertinput = arcpy.GetParameterAsText(3)
        start_colname = arcpy.GetParameterAsText(4)

        end_rasterVEs, end_featureVEs = createVertEvacs( start_gdb, start_scenario, start_basemap,
                                                         start_vertinput, start_colname )
        for endve in end_rasterVEs:
            util.addLayerToMap(start_gdb,endve,"time_map")
        for endve in end_featureVEs:
            util.addLayerToMap(start_gdb,endve,"time_map")

        arcpy.SetParameterAsText(0, True)
    except Exception:
        arcpy.SetParameterAsText(0, False)
