"""
runFlowAccumulation.py

J.M. Jones, jmjones@usgs.gov

initial version:  Oct 2017 (v1.1), updated Jul 2022 (python3), updated Jun 2023 (v2)

Description:
Calls the flow accumulation tool with the flow direction raster and the weight file.

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

def getFlowAccumulation( ingdb, scenario, pathdist, weightfile ):
    try:
        arcpy.env.overwriteOutput = True
        arcpy.env.workspace = ingdb
        arcpy.AddMessage("Calculating flow accumulation...")

        # get needed file names
        elevation = util.getRasterStorage(ingdb,util.getPEATfileName( 'elevation' ),names.ROOT)
        studyareaR = util.getRasterStorage(ingdb,util.getPEATfileName( 'studyareaR' ),names.ROOT)

        # Set environment variables based on dem and study area
        arcpy.env.extent = arcpy.Describe(studyareaR).Extent
        arcpy.env.snapRaster = elevation
        cellsize, demsr = util.getRasterCellAndSR( elevation )
        arcpy.env.outputCoordinateSystem = demsr
        arcpy.env.cellSize = cellsize

        #create a raster of accumulated flow into each cell
        outflow = util.getRasterStorage(ingdb,"{0}_{1}".format(util.getPEATfileName( 'flowaccR' ),scenario),
                                        names.BASIN,scenario)
        flowdir = util.getRasterStorage(ingdb,"{0}_{1}".format(util.getPEATfileName( 'flowdir' ),scenario),
                                        names.BASIN,scenario)
        util.cleanUpIntermediateFiles([outflow,flowdir])
        arcpy.CheckOutExtension("Spatial")
        outflowdir = arcpy.sa.FlowDirection(pathdist)
        outflowdir.save(flowdir)
        outflowacc = arcpy.sa.FlowAccumulation(flowdir,weightfile,"FLOAT")
        outflowacc.save(outflow)

        #create flow lines for symbolizing the flow direction
        tempdirection = util.getRasterStorage(ingdb,"tempflow",names.SCRATCH)
        tempint = util.getRasterStorage(ingdb,"tempint",names.SCRATCH)
        nullint = util.getRasterStorage(ingdb,"nullint",names.SCRATCH)
        util.cleanUpIntermediateFiles([tempdirection,tempint,nullint])
        result = arcpy.sa.RoundUp(outflow)
        result.save(tempdirection)
        result = arcpy.sa.Int(tempdirection)
        result.save(tempint)
        outnull = arcpy.sa.SetNull(tempint, tempint, "VALUE = 0")
        outnull.save(nullint)
        arcpy.CheckInExtension("Spatial")
        flowlines = util.getFeatureStorage(ingdb,"{0}_{1}".format(util.getPEATfileName("flowaccV"),scenario),
                                           names.BASIN,scenario,demsr)
        arcpy.RasterToPolyline_conversion(nullint,flowlines,"NODATA")
        util.cleanUpIntermediateFiles([tempdirection,tempint,nullint])

        return outflow, flowlines, flowdir

    except arcpy.ExecuteError:
        arcpy.AddError(arcpy.GetMessages(2))
        raise
    except Exception:
        arcpy.AddError(traceback.format_exc())
        raise
