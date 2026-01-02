"""
EvacUtilities.py

written by: JM Jones, jmjones@usgs.gov
initial version:  May 2012 (v1), updated Oct 2017 (v1.1), updated Jul 2022 (python3), updated Jun 2023 (v2)

Description: Miscellaneous utilities for the Pedestrian Evacuation Analyst geoprocessing code.

This software has been approved for release by the U.S. Geological Survey (USGS).
Although the software has been subjected to rigorous review, the USGS reserves the
right to update the software as needed pursuant to further analysis and review. No
warranty, expressed or implied, is made by the USGS or the U.S. Government as to the
functionality of the software and related material nor shall the fact of release
constitute any such warranty. Furthermore, the software is released on condition that
neither the USGS nor the U.S. Government shall be held liable for any damages resulting
from its authorized or unauthorized use.
"""
import os, traceback, csv, re
import arcpy
import PEATutil.PEATnames as names

class JustExit( Exception ): pass

def getTextNumber( innum ):
    """
    Converts the cell size to a string, with values like 10.0 returned as "10" and values like 10.5 returned as "10p5"
    """
    outname = str(innum)
    if outname.count('.'):
        dpt = outname.find('.')
        frac = outname[dpt+1:]
        if int(frac) == 0:
            outname = outname[:dpt]
        else:
            outname = outname.replace('.','p')
    return outname


def getIntSCV( scv ):
    """
    Returns a string version of the scv value after it has been converted to an integer.
    The 10,000 value here preserves 4 decimal places in the floating point number.  The floating pt. number
    is shifted left 4 places and converted to integer in order to reclassify the values since reclass only works on
    integers.  In later processing the raster is divided by 10,000 to return it to floating  pt. for the
    path distance tool.
    """
    NoData = -9999
    if (int(float(scv)) != NoData) and ((float(scv)) > 0.0):
        scv_out = str(int(float(scv)*10000))
    else:
        scv_out = "0"
    return scv_out

def buildLandCoverRemap(remapvals ):
    """
    Builds the SCV remap table used to reclassify the land cover raster, using the format expected by the tool.
    """
    try:
        newvals = [[a,getIntSCV(b)] for a,b in remapvals]
        remap = arcpy.sa.RemapValue(newvals)
        return remap
    except Exception:
        arcpy.AddError(traceback.format_exc())
        raise

def buildDisplayRemap(remapvals ):
    """
    Builds a display version of the SCV remap table so it can be printed in the tool message window.
    """
    try:
        display_remap = ""
        for value, scv in remapvals:
            display_remap = "{0} {1} {2};".format(display_remap,value,scv)
        return display_remap
    except Exception:
        arcpy.AddError(traceback.format_exc())
        raise

def writeOutFile( results, intable ):
    """
    Writes out a Python list of lists to the output csv file name
    """
    try:
        csvfile = open(results, "wt", newline='')
        writer = csv.writer(csvfile, dialect='excel' )
        writer.writerows( intable )
        csvfile.close()
    except Exception:
        arcpy.AddError("Unable to open or write to {0}".format(results))
        raise

def readInFile( intable, starttable ):
    """
    Reads in a csv file into a python list. Returns a list of lists, with each row being a csv table row.
    """
    try:
        csvfile = open(intable, "rt", newline='')
        tableData = csv.reader(csvfile, dialect='excel')
        for row in tableData:
            starttable.append(row)
        csvfile.close()
    except Exception:
        arcpy.AddError("Unable to open or read from {0}".format(intable))
        raise


def get_linear_unit_conversion( linear_name ):
    """
    Gets the conversion factor between one meter and the linear units of the study area file spatial reference.
    Conversion was determined from esri's projected_coordinate_systems.pdf doc, Table 1, Linear units and conversion values.
    The values have been simplified to 6 significant digits.  The names included here were determined by first
    getting a list of all projected coordinate systems with arcpy.ListSpatialReference(<only projected>), ArcPro 2.9.1.
    This returned almost 6000 projections.  The names of the linear units for these projections were put into a set to
    identify the 17 unique linear unit names, with several having the same conversion factor within 6 significant digits.
    A return value of 0 indicates no match with any spatial reference.
    12/15/2023, removed table entry  "150_Kilometers" : 150000, since it returned 50000 instead of 150000 in testing.
    """
    try:
        conversion = 0.0
        unit_table = {
            "Meter" : 1.00,
            "Foot" : 0.3048,
            "50_Kilometers" : 50000,
            "Chain" : 20.1168,
            "Yard" : 0.9144,
            "Link" : 0.201168
        }
        for each in unit_table.keys():
            if linear_name.count(each):
                conversion = unit_table[each]
                break

        return conversion
    except Exception:
        arcpy.AddError((traceback.format_exc()))
        raise


def projectFeatureClass( infile, outCS, outfile, projgdb):
    """
    Projects a feature class to the given spatial reference,preserving shape for polygons and lines.  Uses the output
    file name parameter to store the projected feature class.  Added functionality to handle cases where the input
    feature class is within a Topology, in which case the feature class must
    first be projected to a shapefile before it can be copied into another gdb.
    """
    try:
        arcpy.env.overwriteOutput = True
        inCS = arcpy.Describe(infile).spatialReference
        extent = arcpy.Describe(infile).extent
        transformations = arcpy.ListTransformations(inCS, outCS, extent)
        transform = transformations[0] if len(transformations) > 0 else ""

        try:
            arcpy.Project_management( infile, outfile, outCS, transform, preserve_shape="PRESERVE_SHAPE")
        except Exception:
            gdbfolder = os.path.dirname(projgdb)
            tempshape = os.path.join(gdbfolder,"peat_temp.shp")
            arcpy.Project_management(infile, tempshape, outCS, transform, preserve_shape="PRESERVE_SHAPE")
            arcpy.CopyFeatures_management(tempshape,outfile)
            arcpy.Delete_management(tempshape)
    except Exception:
        arcpy.AddError((traceback.format_exc()))
        raise

def projectRasterFile( infile, insize, outCS, outfile):
    """
    Projects a raster to the given spatial reference and cell size.  Uses the output file name parameter to store
    the projected raster.
    """
    try:
        arcpy.env.overwriteOutput = True
        inCS = arcpy.Describe(infile).spatialReference
        extent = arcpy.Describe(infile).extent
        transformations = arcpy.ListTransformations(inCS, outCS, extent)
        transform = transformations[0] if len(transformations) > 0 else ""
        arcpy.ProjectRaster_management( infile, outfile, outCS, resampling_type="NEAREST",cell_size=insize,
                                        geographic_transform=transform)
    except Exception:
        arcpy.AddError((traceback.format_exc()))
        raise

def getPEATfileName( lookupname ):
    """
    Keeps one level of separation between the output file names in the project gdb and the code, in case the output
    names need to change.
    """
    
    try:
        outname = 'None'
        lookuptab = { 'studyareaV':'study_area_polygon',
                      'studyareaR':'study_area_raster',
                      'elevation':'dem',
                      'hazardV':'hazard',
                      'prelim_safe':'prelim_safe_zone',
                      'safezoneV':'safe_zone_polygon',
                      'safezoneR':'safe_zone_raster',
                      'costinv':'lc_cost_inverse',
                      'backlink':'backlink',
                      'flowdir':'flowdir',
                      'pathdist':'path_distance',
                      'evacsurf':'evac_surface',
                      'timemapR':'time_map_raster',
                      'timemapV':'time_map_polygon',
                      'speedmapR':'speed_map_raster',
                      'speedmapV':'speed_map_polygon',
                      'buildings':'buildings',
                      'population':'population_points',
                      'roadlines':'roads_lines',
                      'reblink':'backlink_reclass',
                      'pourpointsR':'pourpoints_raster',
                      'pourpointsV':'pourpoints_points',
                      'watershedsR':'watersheds_raster',
                      'watershedsV':'watersheds_polygon',
                      'watershedsbounding':'watersheds_bounding_polygon',
                      'flowaccR':'flow_accumulation_raster',
                      'flowaccV':'flow_accumulation_lines'}

        if lookupname in lookuptab.keys():
            outname = lookuptab[lookupname]
        return outname
    except Exception:
        arcpy.AddError((traceback.format_exc()))
        raise

def getRasterCellAndSR( inraster ):
    """
    Checks the properties of the input raster and returns its cell size and spatial reference
    """
    try:
        ras_sr = arcpy.Describe(inraster).SpatialReference
        resultprop = arcpy.GetRasterProperties_management(inraster,property_type="CELLSIZEX")
        try:
            ras_cell = int(resultprop.getOutput(0))
        except Exception:
            ras_cell = float(resultprop.getOutput(0))
        return ras_cell, ras_sr
    except Exception:
        arcpy.AddError((traceback.format_exc()))
        raise

def checkTheDataType(layer):
    """
    Returns string 'isvector' or 'israster' depending on the input layer data type
    """
    try:
        datatype = arcpy.Describe(layer).datasetType
        if datatype == "FeatureClass":
            return 'isvector'
        elif datatype == "RasterDataset":
            return "israster"
        else:
            return datatype
    except Exception:
        arcpy.AddError((traceback.format_exc()))
        raise

def cleanScenarioName(ingdb, inname):
    """
    Since the scenario name is used in file, folder, and gdb dataset names, it is checked for invalid characters.
    If the name doesn't begin with a letter, an 'S' is inserted at the start.  If it doesn't end with a letter, an 's'
    is inserted at the end.  If it contains any special characters except a number, a letter, and an underscore, those
    special characters are replaced with an underscore.  Finally, if any replacements caused more than one underscore
    in a row, the multiple underscores are replaced with a single underscore.
    """
    try:
        validstart = re.match(r"^[a-zA-Z]",inname)
        startname = "S{0}".format(inname) if (validstart is None) else inname
        if not startname.isalnum():
            checkname = re.sub("\W+","_",startname)
            endname = re.sub("_{2,}","_",checkname)
        else:
            endname = startname
        outname = "{0}s".format(endname) if endname.endswith('_') else endname
        flag = ""
        if outname in ['scratch','PEATbasin']:
            flag = 'reserved'
        else:
            toppath = os.path.dirname(ingdb)
            gdbname = os.path.basename(ingdb).replace(".gdb","")
            foldername = os.path.join(toppath,"{0}_rasters".format(gdbname))
            contents = os.listdir(foldername)
            for name in contents:
                if name == outname:
                    flag = 'inuse'
                    break
                else:
                    flag = 'new'

        return outname, flag
    except Exception:
        arcpy.AddError((traceback.format_exc()))
        raise

def sampleOrAggregate( inraster, in_cell_size, rastype, outraster ):
    """
    Compares the input raster cell size against the processing cell size and samples or aggregates the input raster
    to match the processing cell size.  If the input raster is the dem, the resampling type is BILINEAR, otherwise it
    is "NEAREST". Will return a new raster (with the name in outraster) that has been resampled, aggregated, or copied
    into the output raster (in the case that no change in cell size is needed).
    """
    try:
        #Find cell size of input raster
        result = arcpy.GetRasterProperties_management( inraster, "CELLSIZEX" )
        LCcellX = result.getOutput(0)
        studyval = float(in_cell_size)
        LCval = float(LCcellX)
        resamptype = "BILINEAR" if rastype == 'dem' else "NEAREST"

        # Check cell size and sample or aggregate as necessary
        if (LCval - studyval) > 0.05:        #sample
            #The resample function will produce an output raster with the cell size specified in in_cell_size
            arcpy.Resample_management(inraster, outraster, in_cell_size, resamptype)
        elif (studyval - LCval) > 0.05:      #aggregate
            #A cell factor of 1 is used here since the environment variable cellSize is set in the calling function.
            #When arcpy.env.cellSize is set to an integer value (and not max or min of inputs), the output raster's
            # resolution is the product of the cell_factor and arcpy.env.cellSize.  In PEAT's case, the environment
            #already defines the output cell size so the aggregate will result in the correct final cell size.
            cell_factor = 1
            outAggregate = arcpy.sa.Aggregate(inraster, str(cell_factor),"MAXIMUM", "EXPAND", "DATA")
            outAggregate.save(outraster)
        else:
            arcpy.CopyRaster_management(inraster, outraster)

    except arcpy.ExecuteError:
        arcpy.AddError((arcpy.GetMessages(2)))
        raise
    except Exception:
        arcpy.AddError((traceback.format_exc()))
        raise

def screenInputRaster(ingdb,inraster,insr,cellsize,instudy,outraster):
    """
    Checks an input raster for correct projection, trims to study area, and samples or aggregates if cell size
    doesn't match dem cell size. Returns a new raster containing the adjusted input raster. This is set up for land cover
    files (categorical data) and will use the 'NEAREST' option in the Resample tool if resampling is necessary.
    """
    try:
        projectedras = getRasterStorage(ingdb, "projectedras", ['scratch'])
        adjustedras = getRasterStorage(ingdb, "adjustedras", ['scratch'])
        cleanUpIntermediateFiles([projectedras,adjustedras])
        if insr.Name != arcpy.Describe(inraster).spatialReference.Name:
            projectRasterFile(inraster,cellsize,insr,projectedras)
            sampleOrAggregate(projectedras, cellsize, "landcover",adjustedras)
        else:
            sampleOrAggregate(inraster, cellsize, "landcover", adjustedras )

        #Extract by Mask - mask land cover by study zone
        outExtract = arcpy.sa.ExtractByMask( adjustedras, instudy)
        outExtract.save(outraster)
        arcpy.BuildRasterAttributeTable_management( outraster )
        arcpy.CalculateStatistics_management( outraster )
        cleanUpIntermediateFiles([projectedras,adjustedras])
    except Exception:
        arcpy.AddError((traceback.format_exc()))
        raise

def screenInputVector(ingdb,invector,insr,instudy,outvector):
    """
    Checks an input feature class for correct projection, trims to study area, and returns the result.
    """
    try:
        projectedv = getFeatureStorage(ingdb,"projectedvector",['scratch'])
        dicedv = getFeatureStorage(ingdb, "dicedvector",['scratch'])
        if insr.Name != arcpy.Describe(invector).spatialReference.Name:
            projectFeatureClass( invector, insr, projectedv, ingdb)
        else:
            arcpy.CopyFeatures_management(invector,projectedv)

        #This check is to prevent clip failure with very large polygons.  Then clip input by study area.
        if arcpy.Describe(projectedv).shapeType == "Polygon":
            arcpy.Dice_management(projectedv, dicedv, 100000 )
            arcpy.Clip_analysis(dicedv, instudy, outvector)
        else:
            arcpy.Clip_analysis(projectedv,instudy,outvector)

        cleanUpIntermediateFiles([projectedv, dicedv])

    except Exception:
        arcpy.AddError((traceback.format_exc()))
        raise

def getTravelSpeed(layer):
    """
    Extracts the text speed value from the end of the input file (i.e. 0p89) and 
    replaces the 'p' with a period so the text value can be converted to a number.
    """
    try:
        justname = os.path.splitext(layer)[0]
        speed = justname.split("_")[-1]
        outnum = speed.replace('p','.')
        return outnum,speed
    except Exception:
        arcpy.AddError((traceback.format_exc()))
        raise

def getRasterStorage( ingdb, inras, processpath, scenario="", speed="", venum="" ):
    """
    Sets up all rasters to be stored as tifs in a folder.  Rasters in file geodatabases
    occasionally get corrupted and the only recourse is to delete the gdb and rebuild.  
    Folder storage for rasters may be more robust.  Process paths include root, scratch, 
    scenario, costinv, pathdist, evacsurf, timemap, speedmap, vemap, basin. Backlink uses 
    the pathdist folder.  Multiple paths can appear in sequence in the processpath list.
    """
    try:
        toppath = os.path.dirname(ingdb)
        gdbname = os.path.basename(ingdb).replace(".gdb","")
        foldername = os.path.join(toppath,"{0}_rasters".format(gdbname))
        if not os.path.isdir(foldername):
            os.mkdir(foldername)

        if 'root' in processpath:  # processpath = names.ROOT and scenario not used
            outname = os.path.join(foldername,"{0}.tif".format(inras))

        elif 'scratch' in processpath:  # processpath = names.SCRATCH and scenario not used
            subfolder = "scratch"
            if not os.path.isdir(os.path.join(foldername,subfolder)):
                os.mkdir(os.path.join(foldername,subfolder))
            outname = os.path.join(foldername,subfolder,"{0}.tif".format(inras))

        elif 'basin' in processpath: #processpath = names.BASIN and scenario has basin folder name
            subfolder = scenario
            if not os.path.isdir(os.path.join(foldername,subfolder)):
                os.mkdir(os.path.join(foldername,subfolder))
            outname = os.path.join(foldername, subfolder, "{0}.tif".format(inras))

        elif 'scenario' in processpath: # processpath contains 'scenario' and scenario name is provided
            if not os.path.isdir(os.path.join(foldername,scenario)):
                os.mkdir(os.path.join(foldername,scenario))
            if 'base' in processpath: # processpath = ['scenario','base']
                outname = os.path.join(foldername, scenario, "{0}.tif".format(inras))
            elif 'vemap' in processpath:  # processpath = ['scenario','vemap']
                subfolder = "vemap_{0}".format(speed)
                if not os.path.isdir(os.path.join(foldername,scenario,subfolder)):
                    os.mkdir(os.path.join(foldername,scenario,subfolder))
                nextfolder = venum
                if not os.path.isdir(os.path.join(foldername, scenario, subfolder, nextfolder)):
                    os.mkdir(os.path.join(foldername, scenario, subfolder, nextfolder))
                outname = os.path.join(foldername, scenario, subfolder, nextfolder, "{0}.tif".format(inras))
            else: # processpath = ['scenario','evacsurf'] or ['scenario','timemap'] or ['scenario','speedmap']
                nextfolder = processpath[1]
                if not os.path.isdir(os.path.join(foldername, scenario, nextfolder)):
                    os.mkdir(os.path.join(foldername, scenario, nextfolder))
                outname = os.path.join(foldername, scenario, nextfolder, "{0}.tif".format(inras))
        else:
            outname = ""

        return outname
    except Exception:
        arcpy.AddError((traceback.format_exc()))
        raise

def getFeatureStorage( ingdb, infeature, processpath, scenario="", spatialref="" ):
    """
    Sets up vectors to be stored in the project gdb, either at the root level or 
    within a dataset.  Processpath is a list that contains the secquence for storage 
    and can include root, scratch, scenario, timemap, speedmap, vemap, basin.
    """
    try:
        if 'root' in processpath:
            outname = os.path.join(ingdb,infeature)
        elif 'scratch' in processpath:
            dataset = "scratch"
            if not arcpy.Exists(os.path.join(ingdb,dataset)):
                arcpy.CreateFeatureDataset_management(ingdb,dataset,spatialref)
            outname = os.path.join(ingdb,dataset,infeature)
        elif 'scenario' in processpath and len(processpath) > 1:
            dataset = "{0}_{1}".format(scenario,processpath[1])
            if not arcpy.Exists(os.path.join(ingdb,dataset)):
                arcpy.CreateFeatureDataset_management(ingdb,dataset,spatialref)
            outname = os.path.join(ingdb,dataset,infeature)
        elif 'basin' in processpath:
            dataset = scenario
            if not arcpy.Exists(os.path.join(ingdb, dataset)):
                arcpy.CreateFeatureDataset_management(ingdb, dataset,spatialref)
            outname = os.path.join(ingdb, dataset, infeature)
        else:
            outname = ""

        return outname
    except Exception:
        arcpy.AddError((traceback.format_exc()))
        raise

def cleanUpIntermediateFiles(invals):
    """
    This was added to handle cases where a tool failed to complete and left intermediate 
    files behind, especially in the case of rasters.  Sometimes the rasters get corrupted 
    and prevent rerunning of the tool.
    """
    if isinstance(invals,list):
        for intermed in invals:
            if arcpy.Exists(intermed):
                arcpy.Delete_management(intermed)
    else:
        if arcpy.Exists(invals):
            arcpy.Delete_management(invals)

def checkForTheFile(projgdb, filename, filetype, scenario=""):
    """
    Allows the data-checking code to be contained within the utilites in one place.  
    This function calls one of the following 'check' functions.  The dem, study 
    area, and safe zone filenames can be used as-is, but the cost inverse
    raster needs the scenario name added before checking for existence.
    """

    namelookup = { getPEATfileName( 'elevation' ): checkdem,
                   getPEATfileName( 'studyareaV' ): checkstudyvector,
                   getPEATfileName( 'studyareaR' ): checkstudyraster,
                   getPEATfileName( 'safezoneV' ): checksafevector,
                   getPEATfileName( 'safezoneR' ): checksaferaster,
                   getPEATfileName( 'costinv' ): checkcostinverse}
    try:
        arcpy.env.workspace = projgdb
        peatname = getPEATfileName(filename)

        if scenario:
            scenarioname = "{0}_{1}".format(peatname,scenario)
            outname = getRasterStorage(projgdb, scenarioname, names.SCENARIO, scenario)
        else:
            if filetype == 'vector':
                outname = getFeatureStorage(projgdb,peatname,names.ROOT)
            else:
                outname = getRasterStorage(projgdb, peatname, names.ROOT)

        namelookup[peatname](outname)
        return outname

    except JustExit:
        raise JustExit
    except Exception:
        arcpy.AddError("Unknown filename {0}, unable to check if file exists in project gdb or folder".format(filename))
        raise

def checkdem(demname):
    if not arcpy.Exists(demname):
        arcpy.AddError("Unable to find elevation (DEM) {0} in workspace".format(demname))
        arcpy.AddError("Run Preprocess DEM to input an elevation raster")
        raise JustExit
    arcpy.AddMessage("DEM: {0}".format(demname))

def checkstudyvector(studyv):
    if not arcpy.Exists(studyv):
        arcpy.AddError("Study area vector {0} not found in workspace".format(studyv))
        arcpy.AddError("Run Preprocess DEM to create or input a new study area")
        raise JustExit
    arcpy.AddMessage("Study area vector: {0}".format(studyv))

def checkstudyraster(studyr):
    if not arcpy.Exists(studyr):
        arcpy.AddError("Study area raster {0} not found in workspace".format(studyr))
        arcpy.AddError("Run Preprocess DEM to create or input a new study area")
        raise JustExit
    arcpy.AddMessage("Study area raster: {0}".format(studyr))

def checksafevector(safev):
    if not arcpy.Exists(safev):
        arcpy.AddError("Safe zone vector {0} not found in workspace".format(safev))
        arcpy.AddError("Run Preprocess Safezone to input a safe zone")
        raise JustExit
    arcpy.AddMessage("Safe zone vector: {0}".format(safev))

def checksaferaster(safer):
    if not arcpy.Exists(safer):
        arcpy.AddError("Safe zone raster {0} not found in workspace".format(safer))
        arcpy.AddError("Run Preprocess Safezone to input a safe zone")
        raise JustExit
    arcpy.AddMessage("Safe zone raster: {0}".format(safer))

def checkcostinverse(costinv):
    if not arcpy.Exists(costinv):
        arcpy.AddError("Preprocessed land cover cost inverse {0} not found in workspace".format(costinv))
        arcpy.AddError("Run Preprocess Landcover to create landcover cost inverse raster")
        raise JustExit
    arcpy.AddMessage("Cost inverse raster: {0}".format(costinv))

def addWithSymbology(ingdb, infile, peattype ):
    """
    Not used at this time but available if we want to add ability to symbolize 
    based on input layer file
    """
    try:
        arcpy.env.overwriteOutput = True
        topdir = os.path.dirname(ingdb)
        gdbname = os.path.basename(ingdb)
        layerdir = "{0}_layers".format(gdbname.replace(".gdb",""))
        layerfolder = os.path.join(topdir,layerdir)
        layertype = 'raster' if arcpy.Describe(infile).dataType == 'RasterDataset' else 'polygon'
        layername = os.path.join(layerfolder,"{0}_{1}.lyrx".format(peattype,layertype))
        if arcpy.Exists(layername):
            arcpy.ApplySymbologyFromLayer_management(infile,layername)
            maplayers = arcpy.mp.LayerFile(layername)
            maplayer = maplayers.listLayers()[0]
            aprx = arcpy.mp.ArcGISProject("CURRENT")
            currentmap = aprx.activeMap
            if currentmap:
                currentmap.addLayer(maplayer, "AUTO_ARRANGE")
            return True
        else:
            return False

    except Exception:
        arcpy.AddError((traceback.format_exc()))
        raise

def addLayerToMap( ingdb, infile, peattype ):
    """
    Loads layers to the current map according to a specific symbology
    """
    try:
        arcpy.env.overwriteOutput = True
        inlayer = os.path.basename(infile)
        topdir = os.path.dirname(ingdb)
        gdbname = os.path.basename(ingdb)
        layerdir = "{0}_layers".format(gdbname.replace(".gdb",""))
        # if the folder doesn't exist, create it
        layerfolder = os.path.join(topdir,layerdir)
        if not os.path.exists(layerfolder):
            os.mkdir(layerfolder)
        if arcpy.Describe(infile).dataType == 'RasterDataset':
            arcpy.MakeRasterLayer_management(infile,inlayer)
        else:
            arcpy.MakeFeatureLayer_management(infile,inlayer)
        inlyrx = os.path.join(layerfolder,"{0}.lyrx".format(inlayer))
        arcpy.SaveToLayerFile_management(inlayer,inlyrx, "ABSOLUTE")
        maplayers = arcpy.mp.LayerFile(inlyrx)
        maplayer = maplayers.listLayers()[0]
        aprx = arcpy.mp.ArcGISProject("CURRENT")
        currentmap = aprx.activeMap
        if currentmap:
            if maplayer.isRasterLayer:
                if peattype == 'elevation':
                    sym = maplayer.symbology
                    sym.colorizer.field = 'Value'
                    sym.updateColorizer("RasterStretchColorizer")
                    sym.colorizer.colorRamp = aprx.listColorRamps('Cyan to Purple')[0]
                    maplayer.symbology = sym
                elif peattype == 'speed_map':
                    sym = maplayer.symbology
                    sym.colorizer.field = 'Value'
                    sym.updateColorizer("RasterStretchColorizer")
                    sym.colorizer.colorRamp = aprx.listColorRamps('Cyan to Purple')[0]
                    maplayer.symbology = sym
                elif peattype == 'time_map' or peattype == 'evac_surface':
                    sym = maplayer.symbology
                    sym.colorizer.field = 'Value'
                    sym.updateColorizer("RasterStretchColorizer")
                    sym.colorizer.colorRamp = aprx.listColorRamps('Yellow to Red')[0]
                    maplayer.symbology = sym
                elif peattype == 'cost_inverse':
                    sym = maplayer.symbology
                    sym.colorizer.field = 'Value'
                    sym.updateColorizer("RasterStretchColorizer")
                    sym.colorizer.colorRamp = aprx.listColorRamps('Surface')[0]
                    maplayer.symbology = sym
                else:
                    # just add with default symbology
                    pass
            if maplayer.isFeatureLayer:
                if peattype == "speed_map":
                    sym = maplayer.symbology
                    sym.updateRenderer('UniqueValueRenderer')
                    sym.renderer.fields = ['SPEED']
                    sym.renderer.colorRamp = aprx.listColorRamps('Cyan to Purple')[0]
                    maplayer.symbology = sym
                elif peattype == 'time_map':
                    sym = maplayer.symbology
                    sym.updateRenderer('GraduatedColorsRenderer')
                    sym.renderer.fields = ['gridcode']
                    sym.renderer.colorRamp = aprx.listColorRamps('Yellow to Red')[0]
                    maplayer.symbology = sym
                elif peattype == 'watersheds':
                    sym = maplayer.symbology
                    sym.updateRenderer('UniqueValueRenderer')
                    sym.renderer.fields = ['Id']
                    sym.renderer.colorRamp = aprx.listColorRamps('Muted Pastels')[0]
                    maplayer.symbology = sym
                elif peattype == 'flowlines':
                    sym = maplayer.symbology
                    sym.updateRenderer('GraduatedSymbolsRenderer')
                    sym.renderer.classificationField = 'grid_code'
                    sym.renderer.minimumSymbolSize = 0.5
                    sym.renderer.maximumSymbolSize = 6.0
                    sym.renderer.colorRamp = aprx.listColorRamps('Plasma')[0]
                    maplayer.symbology = sym
                elif peattype == 'pourpoints':
                    sym = maplayer.symbology
                    sym.updateRenderer('SimpleRenderer')
                    sym.renderer.classificationField = 'grid_code'
                    sym.renderer.label = "Pour points"
                    sym.renderer.symbol.color = {'RGB': [0, 230, 169, 100]}
                    sym.renderer.symbol.outlineColor = {'RGB': [0, 0, 0, 100]}
                    sym.renderer.symbol.size = 6.0
                    maplayer.symbology = sym
                else:
                    # just add with default symbology
                    pass
            currentmap.addLayer(maplayer, "AUTO_ARRANGE")
        arcpy.Delete_management(inlyrx)
        os.rmdir(layerfolder)

    except Exception:
        arcpy.AddError((traceback.format_exc()))
        raise
