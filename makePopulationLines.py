"""
makePopulationLines.py

J.M. Jones, jmjones@usgs.gov

initial version:  Oct 2017 (v1.1), updated Jul 2022 (python3), updated Jun 2023 (v2)

Description
Uses the Near analysis tool to find the closest point on the road network to each population point.
The population point and the near point are then stored in the same feature class with a field that
indicates the connection.  This feature class is used to create the lines from the population points
to the road network.

Note:
When making lines to pop points, it would help to have a roads layer that extends for some distance
into the safe zone.  This picks up points to roads for situations where the road is near to
a population point but inside the safe zone.

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

def makePopulationLines(ingdb, roads, population):
    try:
        arcpy.env.overwriteOutput = True
        arcpy.AddMessage("making population lines...")

        # Get the dem spatial reference
        elevation = util.checkForTheFile(ingdb, 'elevation', filetype='raster' )
        cellsize, demsr = util.getRasterCellAndSR( elevation )

        # make a layer of the pop layers to hold added attributes
        popnear = util.getFeatureStorage(ingdb, "population_near", names.SCRATCH,spatialref=demsr)
        pop = "pop"
        arcpy.MakeFeatureLayer_management(population, pop)

        # calculate the nearest point on the roads to each pop layer
        arcpy.Near_analysis(pop, roads, "", "LOCATION", "NO_ANGLE")
        arcpy.CopyFeatures_management(pop, popnear)
        arcpy.Delete_management(pop)

        # make a feature class of points for pop, and uniquely identify each line segment
        poppoints = util.getFeatureStorage(ingdb,"poppoints",names.SCRATCH,spatialref=demsr)
        arcpy.CreateFeatureclass_management(os.path.dirname(poppoints), os.path.basename(poppoints),
                                            "POINT", "", "", "", spatial_reference=demsr)
        arcpy.AddField_management(poppoints, "CONNECT", "LONG")

        # The point file created here gets an entry for the population or road point geometry and
        # a field to contain values showing which points are to be connected.
        linecursor = arcpy.da.InsertCursor(poppoints, ["SHAPE@XY", "CONNECT"])

        # extract the fid, pop point geometry and road point geometrey from the near file and
        # write into the point file in 2 separate rows, each with the same fid value
        with arcpy.da.SearchCursor(popnear, ["OID@", "SHAPE@XY", "NEAR_X", "NEAR_Y"]) as popcursor:
            for poprow in popcursor:
                linenum = popcursor[0]
                linecursor.insertRow([popcursor[1], linenum])
                xy = (popcursor[2], popcursor[3])
                linecursor.insertRow([xy, linenum])
        del linecursor

        # Create a feature class of lines from the points, using the CONNECT field as the field
        # to show which points belong to the same line
        poplines = util.getFeatureStorage(ingdb, "poplines",names.SCRATCH,spatialref=demsr)
        arcpy.PointsToLine_management(poppoints, poplines, "CONNECT")
        arcpy.CalculateField_management(poplines,"CONNECT",1,"PYTHON3",field_type="SHORT")
        fieldnames = [field.name for field in arcpy.ListFields(poplines) if not field.required]
        fieldnames.remove("CONNECT")
        if len(fieldnames) > 0:
            arcpy.DeleteField_management(poplines,fieldnames,method="DELETE_FIELDS")
        util.cleanUpIntermediateFiles([popnear,poppoints])

        return poplines

    except arcpy.ExecuteError:
        arcpy.AddError(arcpy.GetMessages(2))
        if 'linecursor' in locals():
            del linecursor
        raise
    except Exception:
        arcpy.AddError(traceback.format_exc())
        if 'linecursor' in locals():
            del linecursor
        raise

