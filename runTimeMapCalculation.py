"""
TimeMapRasterVector.py

J.M. Jones, jmjones@usgs.gov
initial version:  May 2012 (v1), updated Oct 2017 (v1.1), updated Jul 2022 (python3), updated Jun 2023 (v2)

Description:
Takes the least cost time surface(s) and reclassifies into an integer raster at 1-minute increment bands.
Then raster is converted to polygons for additional analysis with the population layers.

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
def genTimesRasterVector( ingdb, scenario, evacs, safezoneV, buildings, vename=""):
    try:
        arcpy.env.overwriteOutput = True
        arcpy.env.workspace = ingdb

        # get file names
        timemapR = util.getPEATfileName('timemapR')
        timemapV = util.getPEATfileName('timemapV')
        elevation = util.getRasterStorage(ingdb,util.getPEATfileName( 'elevation' ),names.ROOT)
        studyareaR = util.getRasterStorage(ingdb,util.getPEATfileName( 'studyareaR' ),names.ROOT)

        # Set environment variables based on dem and study area
        arcpy.env.extent = arcpy.Describe(studyareaR).Extent
        arcpy.env.snapRaster = elevation
        cellsize, demsr = util.getRasterCellAndSR( elevation )
        arcpy.env.outputCoordinateSystem = demsr
        arcpy.env.cellSize = cellsize

        # Convert the float time map into integer, rounding up to the nearest whole number.  Then convert the raster
        # into a vector.
        rastermaps = []
        featuremaps = []
        arcpy.CheckOutExtension("Spatial")
        for evac_surface in evacs:
            arcpy.AddMessage("Processing evacuation surface {0}".format(evac_surface))
            nused,speedval = util.getTravelSpeed(evac_surface)

            #Round up all decimal values in the time raster to the next whole number
            # and convert to an integer.
            if vename == "":
                fileRname = "{0}_{1}_{2}".format(timemapR, scenario, speedval)
                fileVname = "{0}_{1}_{2}".format(timemapV,scenario,speedval)
                timeMapR = util.getRasterStorage(ingdb, fileRname, names.TIMEMAP, scenario)
            else:
                fileRname = "{0}_{1}_{2}_{3}".format(timemapR, scenario, vename, speedval)
                fileVname = "{0}_{1}_{2}_{3}".format(timemapV,scenario,vename, speedval)
                timeMapR = util.getRasterStorage(ingdb, fileRname, names.VEMAP, scenario,speedval,vename)

            evac_round = util.getRasterStorage(ingdb,"evac_round",names.SCRATCH)
            util.cleanUpIntermediateFiles([evac_round,timeMapR])
            outRoundUp = arcpy.sa.RoundUp( evac_surface )
            outRoundUp.save(evac_round)
            outInt = arcpy.sa.Int( evac_round )
            outInt.save(timeMapR)
            util.cleanUpIntermediateFiles([evac_round])

            # If buildings entered, fill in any structure NoData holes in the map for population processing
            #  The holes are barriers to travel that were used in the path distance
            #  calculations, but now that the times are determined the NoData areas
            #  can be filled in with nearby values.  This will prevent the loss of any
            #  population data in case a pop point falls over a NoData area.
            #  Use structure polys in zonal fill to indicate areas to be filled in with
            #  surrounding values from the time map.  The final conditional
            #  inserts the filled in areas into the original surface.

            if buildings:
                if vename == "":
                    filledRname = "{0}_filled_{1}_{2}".format(timemapR,scenario,speedval)
                    filledVname = "{0}_filled_{1}_{2}".format(timemapV,scenario,speedval)
                    timefilledR = util.getRasterStorage(ingdb, filledRname, names.TIMEMAP, scenario)
                    timefilledV = util.getFeatureStorage(ingdb, filledVname, names.TIMEMAP, scenario,demsr)
                else:
                    filledRname = "{0}_filled_{1}_{2}_{3}".format(timemapR,scenario,vename, speedval)
                    filledVname = "{0}_filled_{1}_{2}_{3}".format(timemapV,scenario,vename,speedval)
                    timefilledR = util.getRasterStorage(ingdb,filledRname,names.VEMAP,scenario,speedval,vename)
                    timefilledV = util.getFeatureStorage(ingdb,filledVname, names.VEMAP,scenario,demsr)

                rastermaps.append(timefilledR)
                featuremaps.append(timefilledV)
                # Erase the safe zone so buildings are only added
                # back within the inundation area, and dissolve to merge overlapping footprints.
                erasebuildings = util.getFeatureStorage(ingdb,"erasebuildings",names.SCRATCH,spatialref=demsr)
                dissolvebuildings = util.getFeatureStorage(ingdb,"dissolvebuildings",names.SCRATCH,spatialref=demsr)
                splitpolys = util.getFeatureStorage(ingdb,"splitpolys",names.SCRATCH,spatialref=demsr)
                buildraster = util.getRasterStorage(ingdb,"buildraster",names.SCRATCH)
                util.cleanUpIntermediateFiles([buildraster])
                arcpy.Erase_analysis( buildings, safezoneV, erasebuildings )
                arcpy.Dissolve_management( erasebuildings, dissolvebuildings )
                arcpy.MultipartToSinglepart_management( dissolvebuildings, splitpolys )
                arcpy.PolygonToRaster_conversion( splitpolys, arcpy.Describe(splitpolys).OIDFieldName,
                                                  buildraster,"CELL_CENTER","#", cellsize)
                util.cleanUpIntermediateFiles([erasebuildings,dissolvebuildings,splitpolys])

                #  The next 3 steps just create a raster to point to the locations where the zonal
                #  values are to be inserted into the original time map.  The result will be a surface
                #  with the same shape as the study area raster, with 1s where the buildings are
                #  and 0s everywhere else.
                nullmap = util.getRasterStorage(ingdb,"nullmap",names.SCRATCH)
                trimmap = util.getRasterStorage(ingdb,"trimmap",names.SCRATCH)
                clipmap = util.getRasterStorage(ingdb,"clipmap",names.SCRATCH)
                util.cleanUpIntermediateFiles([nullmap,trimmap,clipmap])
                outIsNull = arcpy.sa.IsNull(buildraster)
                outIsNull.save(nullmap)
                outCon = arcpy.sa.Con( studyareaR, nullmap )
                outCon.save(trimmap)
                outCon = arcpy.sa.Con( trimmap, 0, 1 )
                outCon.save(clipmap)
                util.cleanUpIntermediateFiles([nullmap,trimmap])

                timefillers = util.getRasterStorage(ingdb,"timefillers",names.SCRATCH)
                util.cleanUpIntermediateFiles([timefillers])
                outZonal = arcpy.sa.ZonalFill( buildraster, timeMapR )
                outZonal.save(timefillers)
                outCon = arcpy.sa.Con( clipmap, timefillers, timeMapR )
                outCon.save(timefilledR)
                util.cleanUpIntermediateFiles([buildraster,timefillers,clipmap])
                arcpy.CalculateStatistics_management( timefilledR )
                arcpy.BuildRasterAttributeTable_management( timefilledR, overwrite=True)
                arcpy.BuildPyramids_management( timefilledR )
                arcpy.AddMessage("Timemap raster (filled) has been stored at {0}".format(timefilledR))

                tempfilled = util.getFeatureStorage(ingdb,"tempfilled",names.SCRATCH,spatialref=demsr)
                filldice = util.getFeatureStorage(ingdb,"filldice",names.SCRATCH,spatialref=demsr)
                arcpy.RasterToPolygon_conversion( timefilledR, tempfilled, "NO_SIMPLIFY", "VALUE",
                                                  max_vertices_per_feature=100000 )
                arcpy.RecalculateFeatureClassExtent_management(tempfilled)
                arcpy.RepairGeometry_management( tempfilled, "DELETE_NULL" )
                arcpy.Dissolve_management( tempfilled, filldice, "GRIDCODE" )
                arcpy.AddField_management(filldice,"Travel_time","LONG",field_alias="Travel time (minutes)")
                arcpy.CalculateField_management(filldice,"Travel_time",'!GRIDCODE!',"PYTHON3")
                arcpy.Dice_management(filldice,timefilledV,vertex_limit=100000)
                util.cleanUpIntermediateFiles([tempfilled,filldice])

                arcpy.AddMessage("Timemap vector (filled) has been stored at {0}".format(os.path.join(ingdb,timefilledV)))

            else:  # no buildings used to fill in time map
                if vename == "":
                    timeMapV = util.getFeatureStorage(ingdb,fileVname,names.TIMEMAP,scenario,demsr)
                else:
                    timeMapV = util.getFeatureStorage(ingdb, fileVname, names.VEMAP, scenario,demsr)
                rastermaps.append(timeMapR)
                featuremaps.append(timeMapV)

                arcpy.CalculateStatistics_management( timeMapR )
                arcpy.BuildRasterAttributeTable_management( timeMapR, overwrite=True)
                arcpy.BuildPyramids_management( timeMapR )
                arcpy.AddMessage("Timemap raster has been stored at {0}".format(timeMapR))

                # Convert the raster to a vector, then dissolve the polygons on the Gridcode values to condense
                #  the number of different polygons, but sometimes this fails due to improper polygon construction from
                # the RasterToPolygon tool.  A RepairGeometry step is done before the dissolve
                # to try and correct the problems.
                timetemp = util.getFeatureStorage(ingdb,"timetemp",names.SCRATCH,spatialref=demsr)
                timedice = util.getFeatureStorage(ingdb,"timedice",names.SCRATCH,spatialref=demsr)
                arcpy.RasterToPolygon_conversion( timeMapR, timetemp, "NO_SIMPLIFY", "VALUE",
                                                  max_vertices_per_feature=100000 )
                arcpy.RepairGeometry_management( timetemp, "DELETE_NULL" )
                arcpy.RecalculateFeatureClassExtent_management(timetemp)
                arcpy.Dissolve_management( timetemp, timedice, "GRIDCODE" )
                arcpy.AddField_management(timedice,"Travel_time","LONG",field_alias="Travel time (minutes)")
                arcpy.CalculateField_management(timedice,"Travel_time",'!GRIDCODE!',"PYTHON3")
                arcpy.Dice_management(timedice,timeMapV,vertex_limit=100000)
                util.cleanUpIntermediateFiles([timetemp,timedice])

                arcpy.AddMessage("Timemap vector has been stored at {0}".format(os.path.join(ingdb,timeMapV)))

        arcpy.CheckInExtension("Spatial")
        return rastermaps,featuremaps

    except arcpy.ExecuteError:
        arcpy.AddError(arcpy.GetMessages(2))
        raise
    except util.JustExit:
        raise
    except Exception:
        arcpy.AddError(traceback.format_exc())
        raise
    
