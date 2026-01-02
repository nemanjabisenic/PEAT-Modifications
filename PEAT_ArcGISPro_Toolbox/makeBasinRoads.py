"""
MakeBasinRoads.py

J.M. Jones, jmjones@usgs.gov
initial version:  Oct 2017 (v1.1), updated Jul 2022 (python3), updated Jun 2023 (v2)

Description:
 MakeBasinRoads is called during roads-only basin creation scenarios that are using population
 points in the basin creation and for flow accumulation.  In order to connect population points to the road network
 for path distance, lines are created from each pop point to the nearest road line.  These lines are merged
 with the original road lines and a new cost inverse raster is created.  This new cost inverse raster (with
 value of 1) is used with path distance for basins.  The population points are also converted to raster to
 be used as weights for flow accumulation.  In case the pop values are floating pt. instead of integer, the
 pop value is multiplied by 10,000 to preserve 4 significant digits before conversion to integer.

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
from makePopulationLines import makePopulationLines
from runDistanceAccumulation import runDistAcc
from PEATutil import EvacUtilities as util
from PEATutil import PEATnames as names

def makeRoadsForBasins( ingdb, scenario, inroads, population, inpopcol ):
    try:
        arcpy.env.overwriteOutput = True
        arcpy.env.workspace = ingdb

        # get gdb file names and check that the files are in the project gdb
        elevation = util.getRasterStorage(ingdb, util.getPEATfileName('elevation' ),names.ROOT)
        studyareaR = util.getRasterStorage(ingdb, util.getPEATfileName('studyareaR'), names.ROOT)
        safezoneR = util.getRasterStorage(ingdb, util.getPEATfileName('safezoneR'),names.ROOT)
        costinv = util.getRasterStorage(ingdb, "{0}_{1}".format(util.getPEATfileName("costinv"),scenario),
                                        names.BASIN,scenario)
        pathdist = util.getRasterStorage(ingdb,"{0}_{1}".format(util.getPEATfileName("pathdist"),scenario),
                                         names.BASIN,scenario)
        backlink = util.getRasterStorage(ingdb,"{0}_{1}".format(util.getPEATfileName("backlink"),scenario),
                                         names.BASIN,scenario)

        # Set environment variables based on dem and study area
        arcpy.env.extent = arcpy.Describe(studyareaR).Extent
        arcpy.env.snapRaster = elevation
        cellsize, demsr = util.getRasterCellAndSR( elevation )
        arcpy.env.outputCoordinateSystem = demsr
        arcpy.env.cellSize = cellsize

        # Get the population layer ready
        popraster = util.getRasterStorage(ingdb, "pop_raster",names.SCRATCH)
        util.cleanUpIntermediateFiles([popraster])
        arcpy.AddField_management(population, "POPINT", "FLOAT")
        arcpy.CalculateField_management(population, "POPINT", "!{0}!".format(inpopcol))
        arcpy.PointToRaster_conversion(population, "POPINT", popraster, "SUM", "", cellsize)

        # Use the population file and the roads file to make connector roads from each pop point to the nearest road
        connectlines = makePopulationLines(ingdb, inroads, population)

        # Merge the roadlines and connectors into one file, then convert to a raster
        arcpy.CalculateField_management(inroads, "CONNECT", 1, "PYTHON3", field_type="SHORT")
        fieldnames = [field.name for field in arcpy.ListFields(inroads) if not field.required]
        fieldnames.remove("CONNECT")
        if len(fieldnames) > 0:
            arcpy.DeleteField_management(inroads,fieldnames,method="DELETE_FIELDS")
        allroads = util.getFeatureStorage(ingdb, "allroads",names.SCRATCH,spatialref=demsr)
        arcpy.Merge_management([inroads,connectlines],allroads)
        arcpy.PolylineToRaster_conversion(allroads, "CONNECT", costinv, "MAXIMUM_LENGTH",cellsize=cellsize)
        arcpy.CalculateStatistics_management(costinv)
        util.cleanUpIntermediateFiles([connectlines,allroads])

        # Run Distance Accumulation to create a path distance raster for flow accumulation
        runDistAcc(ingdb, safezoneR, costinv, pathdist, backlink)

        return pathdist, popraster

    except arcpy.ExecuteError:
        arcpy.AddError(arcpy.GetMessages(2))
        raise
    except util.JustExit:
        raise
    except Exception:
        arcpy.AddError(traceback.format_exc())
        raise
