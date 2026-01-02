"""
addResultToMap.py

written by: JM Jones, jmjones@usgs.gov
initial version:  May 2012 (v1), updated Oct 2017 (v1.1), updated Jul 2022 (python3), updated Jun 2023 (v2)

Description: utility tool to help with testing

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

def addLayerToMap( ingdb, infile, inpeattype ):
    try:
        arcpy.env.overwriteOutput = True
        arcpy.env.workspace = ingdb

        if inpeattype.count("feature"):
            peattype = inpeattype.replace(" feature","")
        elif inpeattype.count("raster"):
            peattype = inpeattype.replace(" raster", "")
        else:
            peattype = inpeattype

        util.addLayerToMap(ingdb,infile,peattype)

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
        start_peattype = arcpy.GetParameterAsText(2)
        start_infile = arcpy.GetParameterAsText(3)
        arcpy.AddMessage("infile: {0}".format(start_infile))
        addLayerToMap( start_gdb, start_infile, start_peattype )
        arcpy.SetParameterAsText(0, True)
    except Exception:
        arcpy.SetParameterAsText(0, False)
