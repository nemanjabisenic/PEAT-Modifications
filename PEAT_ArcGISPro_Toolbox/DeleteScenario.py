"""
DeleteScenario.py

written by: JM Jones, jmjones@usgs.gov
initial version:  May 2012 (v1), updated Oct 2017 (v1.1), updated Jul 2022 (python3), updated Jun 2023 (v2)

Usage:  checkForOutliers( ingdb, lc_scenario, maxtimes )

Required Arguments:   ingdb - local database workspace (existing file geodatabase)
                      lc_scenario - string (text) of an existing scenario name to be deleted

Optional Arguments:   none

Returns:   All files associated with the scenario are removed from the geodatabase and the raster folder.  The DEM,
study area, and safe zones are project-level files and don't get deleted by this tool

Description:
This tool is OPTIONAL and is meant as a convenience tool for the user. The storage of the files in the gdb and raster
folder follows a certain pattern, and this tool will clean out all files, feature datasets, and raster folders that
are associated with the scenario.

This software has been approved for release by the U.S. Geological Survey (USGS).
Although the software has been subjected to rigorous review, the USGS reserves the
right to update the software as needed pursuant to further analysis and review. No
warranty, expressed or implied, is made by the USGS or the U.S. Government as to the
functionality of the software and related material nor shall the fact of release
constitute any such warranty. Furthermore, the software is released on condition that
neither the USGS nor the U.S. Government shall be held liable for any damages resulting
from its authorized or unauthorized use.
"""
import traceback, arcpy, os, shutil
from PEATutil import EvacUtilities as util

def deleteTheScenario( ingdb, scenario ):
    try:
        arcpy.env.overwriteOutput = True
        arcpy.env.workspace = ingdb

        # Find all the feature datasets created for this scenario and delete
        allsets = arcpy.ListDatasets("{0}*".format(scenario),feature_type="Feature")
        if len(allsets) > 0:
            arcpy.Delete_management(allsets)
        else:
            arcpy.AddMessage("No feature classes to delete for scenario {0}".format(scenario))

        # Get the path to the scenario directory and delete it and all its contents
        toppath = os.path.dirname(ingdb)
        gdbname = os.path.basename(ingdb).replace(".gdb","")
        foldername = os.path.join(toppath,"{0}_rasters".format(gdbname))
        sfolder = os.path.join(foldername,scenario)
        if os.path.isdir(sfolder):
            shutil.rmtree(sfolder)

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
        deleteTheScenario( start_gdb, start_scenario )
        arcpy.SetParameterAsText(0, True)
    except Exception:
        arcpy.SetParameterAsText(0, False)
