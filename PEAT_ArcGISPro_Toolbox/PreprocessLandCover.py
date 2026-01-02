"""
preprocessLandCover.py

written by: JM Jones, jmjones@usgs.gov
initial version:  May 2012 (v1), updated Oct 2017 (v1.1), updated Jul 2022 (python3), updated Jun 2023 (v2)

Usage:  prepareSafezone( ingdb, lc_scenario, base_layer, base_field, basevalues, addons )

Required Arguments:   ingdb - local database workspace (existing file geodatabase)
                      lc_scenario - string (text) for a unique name to append to folder and file names
                      base_layer - feature class or raster
                      base_field - attribute table field name (integer or string/text)
                      base_values - string/text containing remap values for the base layer, with each pair separated
                                    by a ';', within each pair the processing order and scv value are separated by a space
                                      (expected format: "1 0.6667;2 0.8333" or
                                      "'sand or wetlands' 0.5556;'roads and trails' 1.0;water 0.0")

Optional Arguments:   addons - string/text containing each added feature class or raster information, separated by ';'
                               filename, processing order, and scv value within each entry separated by spaces
                               (expected format - "filename 1 0.0;filename 2 1.0")

Note: scv values are restricted to a range of 0 to 1 inclusive, input files can be feature classes or rasters, and
      the processing order is restricted to an integer between 1 and 20.  Processing order 0 is used for the base
      layer, processing order 1 is the next layer to be burned on top of the base layer, processing order 2 goes on
      top of the combined base and layer 1, etc.

Returns:    The landcover cost inverse raster, stored in the project raster storage

Description:
Take all input land cover layers, preprocess, and combine into the cost inverse raster.  Input layers can be either
raster or vector and may or may not have land cover values in their attribute tables.  One layer will be the base
layer and all the rest are ancillary.  Each layer is clipped/masked to the study area, checked for cell size if raster
and converted to raster if vector.  Then the raster values are reclassed to the input SCV values.  All layers are
combined and scv values of 0 are reclassed to NoData.  Finally, the computation for cost inverse is done.

This software has been approved for release by the U.S. Geological Survey (USGS).
Although the software has been subjected to rigorous review, the USGS reserves the
right to update the software as needed pursuant to further analysis and review. No
warranty, expressed or implied, is made by the USGS or the U.S. Government as to the
functionality of the software and related material nor shall the fact of release
constitute any such warranty. Furthermore, the software is released on condition that
neither the USGS nor the U.S. Government shall be held liable for any damages resulting
from its authorized or unauthorized use.
"""
import traceback, re
import arcpy
from PEATutil import EvacUtilities as util
from PEATutil import PEATnames as names

# Inputs are screened for existence and appropriate data type in the ArcPro tool window parameter settings.
def preLandCover( ingdb, inscenario, baselayer, basefield, basevalues, addons ):
    try:
        arcpy.env.overwriteOutput = True
        arcpy.env.workspace = ingdb

        # get gdb file names
        scenario, testflag = util.cleanScenarioName(ingdb,inscenario)
        if testflag == 'inuse':
            arcpy.AddWarning("Scenario {0} is already in use and will be overwritten".format(scenario))
        elif testflag == 'reserved':
            arcpy.AddError("Scenario name {0} is reserved for PEAT tool use".format(scenario))
            arcpy.AddError("Please pick a different scenario name")
            raise util.JustExit

        elevation = util.checkForTheFile(ingdb, 'elevation', filetype='raster' )
        studyareaV = util.checkForTheFile(ingdb, 'studyareaV', filetype='vector')
        studyareaR = util.checkForTheFile(ingdb, 'studyareaR', filetype='raster' )
        costinv = util.getRasterStorage(ingdb, "{0}_{1}".format(util.getPEATfileName("costinv"),scenario),
                                        names.SCENARIO,scenario)

        # Set environment variables based on dem and study area
        arcpy.env.extent = arcpy.Describe(studyareaR).Extent
        arcpy.env.snapRaster = elevation
        cellsize, demsr = util.getRasterCellAndSR( elevation )
        arcpy.env.outputCoordinateSystem = demsr
        arcpy.env.cellSize = cellsize

        # Screen the input land cover files and build the processing dataset
        lcInfo = screenTheLCData(baselayer, basefield, basevalues, addons)

        #The numbers identifying the order of the input layers are stored as dictionary keys.
        #Get a list of the keys and sort them since dictionary key order is unsorted
        layerSet = [int(key) for key in sorted( lcInfo.keys())]

        #go through each input layer, starting with the base layer, to build the cost inverse raster
        arcpy.CheckOutExtension("Spatial")
        layerOrder = []
        for each in layerSet:
            currentlayer = lcInfo[str(each)]  # Get the parameter dictionary for the current layer
            processedlayer = util.getRasterStorage(ingdb, 'lcproc_{0}'.format(str(each)),names.SCRATCH)
            util.cleanUpIntermediateFiles([processedlayer])
            arcpy.AddMessage("Processing layer {1}: {0}".format(currentlayer['name'],each))

            #Get each layer into the proper format.  If it's raster, adjust cell size and mask by study area.
            # If it's vector, clip by study area and convert to a raster.
            lc_raster =  util.getRasterStorage(ingdb, 'lc_raster_{0}'.format(str(each)),names.SCRATCH)
            util.cleanUpIntermediateFiles([lc_raster])
            if currentlayer['israster']:
                util.screenInputRaster(ingdb,currentlayer['name'],demsr,cellsize,studyareaR,lc_raster)
            else:
                cliplc = util.getFeatureStorage(ingdb,"cliplc",names.SCRATCH,spatialref=demsr)
                util.screenInputVector(ingdb,currentlayer['name'],demsr,studyareaV,cliplc)
                if currentlayer['fieldname'] != 'None':
                    fieldname = currentlayer['fieldname']
                else:
                    fieldname = arcpy.Describe(cliplc).OIDFieldName
                arcpy.RepairGeometry_management(cliplc)
                arcpy.FeatureToRaster_conversion( cliplc, fieldname, lc_raster, str(cellsize))
                util.cleanUpIntermediateFiles([cliplc])

            arcpy.BuildRasterAttributeTable_management( lc_raster )
            arcpy.CalculateStatistics_management( lc_raster )

            #Now the layer is a raster if it started as a vector and is at the proper cell size,
            #projection, and extent.  If only one scv value, then slice and reclass.
            if len(currentlayer['remap']) < 2:
                lc_remapped = util.getRasterStorage(ingdb, 'lc_remap',names.SCRATCH)
                util.cleanUpIntermediateFiles([lc_remapped])
                #slice to all one value in case input raster had multiple values
                outSlice = arcpy.sa.Slice( lc_raster, 1, "EQUAL_INTERVAL", base_output_zone=1 )
                outSlice.save(lc_remapped)
                arcpy.BuildRasterAttributeTable_management( lc_remapped )
                arcpy.CalculateStatistics_management( lc_remapped )
                #reclass NODATA away in ancillary files but leave for first layer
                reclassfield = "VALUE"
                scv = currentlayer['remap'][0][1]
                intscv = util.getIntSCV(scv)
                remap = "1 {0}".format(intscv) if currentlayer['isbase'] else "1 {0};NODATA -100".format(intscv)
                reclassifyTheLayer(lc_remapped,reclassfield,remap,processedlayer)
                util.cleanUpIntermediateFiles([lc_remapped])
            else:
                remap = util.buildLandCoverRemap(currentlayer['remap'])
                display_remap = util.buildDisplayRemap(currentlayer['remap'])
                arcpy.AddMessage("Layer values remapped to {0}".format(display_remap))
                reclassfield = currentlayer['fieldname']
                reclassifyTheLayer(lc_raster,reclassfield,remap,processedlayer)

            arcpy.BuildRasterAttributeTable_management( processedlayer )
            arcpy.CalculateStatistics_management( processedlayer )
            layerOrder.append(processedlayer)
            util.cleanUpIntermediateFiles([lc_raster])

        cleanup = []
        if len(layerOrder) > 1:
            arcpy.AddMessage("Merging landcover layers ...")
            #Merge all ancillary rasters with the main land cover in the proper order
            test = "VALUE > -100"
            currentlc = layerOrder[0]
            for ctr, each in enumerate(layerOrder):
                newlc = util.getRasterStorage(ingdb, 'nextlc_{0}'.format(str(ctr+1)),names.SCRATCH)
                util.cleanUpIntermediateFiles([newlc])
                cleanup.append(newlc)
                outCon = arcpy.sa.Con(each, each, currentlc, test)
                outCon.save(newlc)
                currentlc = newlc
            reclass_lc = currentlc
        else:
            reclass_lc = layerOrder[0]

        #finish the cost inverse processing by readjusting values back to
        # floating point values
        lc_divide = util.getRasterStorage(ingdb, "lcm_divide",names.SCRATCH)
        divConstant = util.getRasterStorage(ingdb, "divConstant",names.SCRATCH)
        divFloat = util.getRasterStorage(ingdb, "divFloat",names.SCRATCH)
        util.cleanUpIntermediateFiles([lc_divide,divConstant,divFloat])
        DIVVAL = 10000
        divExtent = arcpy.Describe(studyareaR).Extent
        outCreate = arcpy.sa.CreateConstantRaster( DIVVAL, "INTEGER", cellsize, divExtent )
        outCreate.save(divConstant)
        outFloat = arcpy.sa.Float(divConstant )
        outFloat.save(divFloat)

        #Before division, reclassify any 0 values to NODATA
        cleaned_lc = util.getRasterStorage(ingdb, 'cleaned_lc',names.SCRATCH)
        util.cleanUpIntermediateFiles([cleaned_lc])
        reclassRange = "0 0 NODATA"
        outReclass = arcpy.sa.Reclassify( reclass_lc, "VALUE", reclassRange, "DATA")
        outReclass.save(cleaned_lc)
        #Divide landcover cost raster by 10,000.00 to convert integers back to floats
        #Then invert the values (1/value) to get inverse cost raster
        arcpy.AddMessage("Dividing landcover cost raster for final format...")
        outDivide = arcpy.sa.Divide(cleaned_lc, divFloat)
        outDivide.save(lc_divide)
        ONEVAL = 1.0
        outDivide = arcpy.sa.Divide(ONEVAL,lc_divide)
        outDivide.save(costinv)
        arcpy.CheckInExtension("Spatial")
        util.cleanUpIntermediateFiles(layerOrder)
        if len(cleanup) > 0:
            util.cleanUpIntermediateFiles(cleanup)
        util.cleanUpIntermediateFiles([lc_divide,divConstant,divFloat,reclass_lc,cleaned_lc])
        arcpy.CalculateStatistics_management( costinv )
        arcpy.BuildPyramids_management( costinv )

        arcpy.AddMessage("Cost inverse raster has been stored at {0}".format(costinv))
        return costinv

    except arcpy.ExecuteError:
        arcpy.AddError(arcpy.GetMessages(2))
        raise
    except util.JustExit:
        raise
    except Exception:
        arcpy.AddError(traceback.format_exc())
        raise

# Checks the input data and builds the lcParms data structure for landcover processing.
def screenTheLCData( blayer, bfield, bvalues, addon_layers):
    try:
        arcpy.env.overwriteOutput = True
        lcParms = {}

        # Prepare the base layer
        lcParms['0'] = {}
        arcpy.AddMessage("Input base land cover layer: {0}".format(blayer))

        # Define the tags for the base layer, including name, field name, and data type.
        lcParms["0"]["isbase"] = True
        lcParms["0"]["name"] = blayer
        lcParms["0"]["fieldname"] = bfield

        datatype = util.checkTheDataType(blayer)
        if datatype == "isvector":
            lcParms["0"]["israster"] = False
        else:  # datatype == "israster":
            lcParms["0"]["israster"] = True

        # Get the remap values for the base layer - incoming format: "1 0.6667;2 0.8333" or
        # "'sand or wetlands' 0.5556;'roads and trails' 1.0;water 0.0"
        sections = bvalues.split(';')
        remap = []
        for each in sections:
            if each.count("'"):
                onemap = each.split("' ")
                attrval = "{0}'".format(onemap[0])
                landval = onemap[1]
            else:
                onemap = each.split(" ")
                attrval = "'{0}'".format(onemap[0]) if re.search('[a-zA-Z]',onemap[0]) else onemap[0]
                landval = onemap[1]
            remap.append((attrval,landval))
        lcParms["0"]["remap"] = remap

        # Load the additional layers into the data structure, skipping over this if no additional layers entered
        # Incoming format - "filename 1 0.0;filename 2 1.0"
        addlayers = addon_layers.split(";") if len(addon_layers) > 0 else []

        for each in addlayers:
            sections = each.split(" ")
            filename = sections[0]
            proc_order = sections[1]
            remapval = sections[2]
            if proc_order in lcParms.keys():
                arcpy.AddError("Processing order value {0} already used for layer {1}".format(proc_order,
                                                                                lcParms[proc_order]['name']))
                arcpy.AddError("Layer {0} and {1} cannot have the same processing order value".format(filename,
                                                                                lcParms[proc_order]['name']))
                raise util.JustExit

            lcParms[proc_order] = {}
            arcpy.AddMessage("Additional land cover layer: {0}".format(filename))

            # Check the data type of the layer
            datatype = util.checkTheDataType(filename)
            if datatype == "isvector":
                lcParms[proc_order]["israster"] = False
            else: # datatype == "israster":
                lcParms[proc_order]["israster"] = True

            # Fill in remaining parms
            lcParms[proc_order]["isbase"] = False
            lcParms[proc_order]["name"] = filename
            lcParms[proc_order]["fieldname"] = "None"
            lcParms[proc_order]["remap"] = [("notused",remapval)]

        return lcParms
    except arcpy.ExecuteError:
        arcpy.AddError(arcpy.GetMessages(2))
        raise
    except util.JustExit:
        raise
    except Exception:
        arcpy.AddError(traceback.format_exc())
        raise

# remap the land cover by the scv values, which have been multiplied
# by 10,000 to preserve 4 decimal places of precision before converting to integer
def reclassifyTheLayer(inlayer,reclassfield,remap,outlayer):
    try:
        fieldlist = [field.name for field in arcpy.ListFields(inlayer)]
        if reclassfield not in fieldlist:
            reclassfield = "Value"
        outReclass = arcpy.sa.Reclassify(inlayer, reclassfield, remap, "DATA")
        outReclass.save(outlayer)
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
        start_baselayer = arcpy.GetParameterAsText(2)
        start_basefield = arcpy.GetParameterAsText(3)
        start_basevalues = arcpy.GetParameterAsText(4)
        start_feataddons = arcpy.GetParameterAsText(5)
        start_rasaddons = arcpy.GetParameterAsText(6)
        if (len(start_feataddons) > 0) and (len(start_rasaddons) > 0):
            start_addons = "{0};{1}".format(start_feataddons,start_rasaddons)
        elif len(start_feataddons) > 0:
            start_addons = start_feataddons
        elif len(start_rasaddons) > 0:
            start_addons = start_rasaddons
        else:
            start_addons = ""
        end_costinv = preLandCover( start_gdb, start_scenario, start_baselayer, start_basefield, start_basevalues,
                      start_addons)
        util.addLayerToMap( start_gdb, end_costinv, "cost_inverse" )
        arcpy.SetParameterAsText(0, True)
    except Exception:
        arcpy.SetParameterAsText(0, False)
