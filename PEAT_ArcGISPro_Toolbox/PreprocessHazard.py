"""
preprocessHazard.py

written by: JM Jones, jmjones@usgs.gov
initial version:  May 2012 (v1), updated Oct 2017 (v1.1), updated Jul 2022 (python3), updated Aug 2023 (v2)

Usage:  preHazard( ingdb, hazard )

Required Arguments:   ingdb - local database workspace (existing file geodatabase)
                      hazard - polygon feature class

Optional Arguments:   none

Returns:    A preliminary safe zone feature class for inspection and editing

Description:
 Takes the study area polygon, which is set to the projection for the study, and projects the hazard to the same
 projection if needed. Then the hazard zone is erased from the study area.
 Finally, Multipart to Singlepart is run to break up the potential safe zone into individual polygons for editing

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

# Inputs are screened for existence and appropriate data type in the ArcPro tool window parameter settings.
def preHazard( ingdb, hazard ):
    try:
        arcpy.env.overwriteOutput = True
        arcpy.env.workspace = ingdb
        studyareaV = util.checkForTheFile(ingdb, 'studyareaV', filetype='vector' )
        elevation = util.checkForTheFile(ingdb, 'elevation', filetype='raster' )
        studyareaR = util.checkForTheFile(ingdb, 'studyareaR', filetype='raster' )

        # Set environment variables based on dem and study area
        arcpy.env.extent = arcpy.Describe(studyareaR).Extent
        cellsize, demsr = util.getRasterCellAndSR( elevation )
        arcpy.env.outputCoordinateSystem = demsr

        # Get new file names
        hazardV = util.getFeatureStorage(ingdb,util.getPEATfileName('hazardV'),names.ROOT)
        prelim_safe = util.getFeatureStorage(ingdb,util.getPEATfileName( 'prelim_safe' ),names.ROOT)

        # Check the projection of the hazard zone and project if needed to the study area projection
        tempprj = util.getFeatureStorage(ingdb,'temp_hazard_prj',names.SCRATCH,spatialref=demsr)
        hazardsr = arcpy.Describe(hazard).SpatialReference
        if demsr.Name != hazardsr.Name:
            util.projectFeatureClass(hazard, demsr, tempprj, ingdb)
        else:
            arcpy.CopyFeatures_management(hazard, tempprj)

        # Clip, then erase the hazard area from the study area to determine the non-hazard areas
        # Then break up the polygons so erroneous ones can easily be removed by the user.
        temperase = util.getFeatureStorage(ingdb,'temp_hazard_erase',names.SCRATCH,spatialref=demsr)
        arcpy.Clip_analysis(tempprj, studyareaV, hazardV)
        arcpy.Erase_analysis(studyareaV, hazardV, temperase)
        arcpy.MultipartToSinglepart_management( temperase, prelim_safe )
        util.cleanUpIntermediateFiles([tempprj,temperase])

        arcpy.AddMessage("Safe zone ready for inspection")
        arcpy.AddMessage("Preliminary safe zone vector has been stored at {0}".format(os.path.join(ingdb,prelim_safe)))
        arcpy.AddMessage("Hazard zone vector has been stored at {0}".format(os.path.join(ingdb, hazardV)))

        return prelim_safe

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
        start_hazard = arcpy.GetParameterAsText(1)
        end_safe = preHazard( start_gdb, start_hazard )
        util.addLayerToMap(start_gdb,end_safe,"safe_zone")
        arcpy.SetParameterAsText(0, True)
    except Exception:
        arcpy.SetParameterAsText(0, False)
