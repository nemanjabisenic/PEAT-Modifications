# -*- coding: utf-8 -*-
"""
Pedestrian_Evacuation_Analyst.pyt

ArcGIS Pro Python toolbox wrapper for the PEAT v2 scripts (copied into the same folder).

Design goals:
- Be easy for ArcGIS Pro to load ("Add Toolbox…") by avoiding import-time failures.
- Avoid any custom licensing gate (`isLicensed`) that blocks execution when Pro already
  has the necessary licenses/extensions active.
"""

import os
import sys

import arcpy


def _ensure_toolbox_on_path():
    """Make sure the toolbox folder is importable for subsequent imports."""
    try:
        toolbox_dir = os.path.dirname(__file__)
    except Exception:
        toolbox_dir = os.getcwd()
    if toolbox_dir and toolbox_dir not in sys.path:
        sys.path.insert(0, toolbox_dir)


_OUTPUT_FLAG = {
    "display": "Succeeded",
    "name": "succeeded",
    "type": "GPBoolean",
    "parameterType": "Derived",
    "direction": "Output",
}


def _build_parameters(specs):
    params = []
    for spec in specs:
        param = arcpy.Parameter(
            displayName=spec["display"],
            name=spec["name"],
            datatype=spec["type"],
            parameterType=spec.get("parameterType", "Required"),
            direction=spec.get("direction", "Input"),
        )
        if spec.get("multiValue"):
            param.multiValue = True
        if "category" in spec:
            param.category = spec["category"]
        params.append(param)
    return params


class _BasePEATTool(object):
    """Base class that handles parameter creation and execution."""

    label = ""
    description = ""
    canRunInBackground = False
    _param_spec = []
    _func_name = ""
    _module_name = ""
    _arg_count = 0

    def getParameterInfo(self):
        return _build_parameters(self._param_spec)

    def _load_func(self):
        _ensure_toolbox_on_path()
        mod = __import__(self._module_name, fromlist=[self._func_name])
        return getattr(mod, self._func_name)

    def execute(self, parameters, messages):
        args = [(p.valueAsText or "") for p in parameters[: self._arg_count]]
        func = self._load_func()
        func(*args)
        # If we include the derived output flag, mark success when no exception was raised.
        if parameters and parameters[-1].direction == "Output":
            parameters[-1].value = True

    # Keep these no-ops for ArcGIS Pro compatibility.
    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        return


class Toolbox(object):
    def __init__(self):
        self.label = "Pedestrian Evacuation Analyst (PEAT)"
        self.alias = "PEAT"
        self.tools = [
            PreprocessDEMTool,
            PreprocessHazardTool,
            PreprocessLandCoverTool,
            PreprocessSafeZoneTool,
            CreateEvacuationSurfaceTool,
            CreateTimeMapsTool,
            CreateSpeedMapTool,
            CreateVerticalEvacuationMapsTool,
            CheckForTimeOutliersTool,
            CreateEvacuationBasinsTool,
            DeleteScenarioTool,
            AddLayerToMapTool,
        ]


class PreprocessDEMTool(_BasePEATTool):
    label = "Preprocess DEM"
    description = "Set up the project DEM and study area."
    _module_name = "PreprocessDEM"
    _func_name = "preDEM"
    _arg_count = 3
    _param_spec = [
        {"display": "Project Workspace (File GDB)", "name": "workspace", "type": "DEWorkspace"},
        {"display": "Elevation Raster (DEM)", "name": "elevation", "type": "GPRasterLayer"},
        {"display": "Study Area (optional)", "name": "study_area", "type": "GPFeatureLayer", "parameterType": "Optional"},
        _OUTPUT_FLAG,
    ]


class PreprocessHazardTool(_BasePEATTool):
    label = "Preprocess Hazard"
    description = "Project/clip hazard polygons and create a preliminary safe zone."
    _module_name = "PreprocessHazard"
    _func_name = "preHazard"
    _arg_count = 2
    _param_spec = [
        {"display": "Project Workspace (File GDB)", "name": "workspace", "type": "DEWorkspace"},
        {"display": "Hazard Zone", "name": "hazard", "type": "GPFeatureLayer"},
        _OUTPUT_FLAG,
    ]


class PreprocessLandCoverTool(_BasePEATTool):
    label = "Preprocess Landcover"
    description = "Create landcover cost inverse raster for a scenario."
    _module_name = "PreprocessLandCover"
    _func_name = "preLandCover"
    _arg_count = 6
    _param_spec = [
        {"display": "Project Workspace (File GDB)", "name": "workspace", "type": "DEWorkspace"},
        {"display": "Scenario Name", "name": "scenario", "type": "GPString"},
        # Use GPString here to avoid toolbox-load failures from ambiguous datatypes.
        # The underlying script accepts a path or layer name.
        {"display": "Base Landcover Layer (path/layer name)", "name": "base_layer", "type": "GPString"},
        {"display": "Base Landcover Field", "name": "base_field", "type": "GPString"},
        {"display": "Base Remap Values", "name": "base_values", "type": "GPString"},
        {"display": "Add-on Layers (optional)", "name": "addons", "type": "GPString", "parameterType": "Optional"},
        _OUTPUT_FLAG,
    ]


class PreprocessSafeZoneTool(_BasePEATTool):
    label = "Preprocess Safe Zone"
    description = "Validate/store the safe zone polygon and create a raster version."
    _module_name = "PreprocessSafezone"
    _func_name = "prepareSafezone"
    _arg_count = 2
    _param_spec = [
        {"display": "Project Workspace (File GDB)", "name": "workspace", "type": "DEWorkspace"},
        {"display": "Safe Zone (polygon)", "name": "safe_zone", "type": "GPFeatureLayer"},
        _OUTPUT_FLAG,
    ]


class CreateEvacuationSurfaceTool(_BasePEATTool):
    label = "Create Evacuation Surface"
    description = "Run Distance Accumulation and generate evacuation time surfaces for one or more walking speeds."
    _module_name = "CreateEvacuationSurface"
    _func_name = "createEvacSurface"
    _arg_count = 3
    _param_spec = [
        {"display": "Project Workspace (File GDB)", "name": "workspace", "type": "DEWorkspace"},
        {"display": "Scenario Name", "name": "scenario", "type": "GPString"},
        {"display": "Walking Speeds (semicolon-separated)", "name": "speeds", "type": "GPString"},
        _OUTPUT_FLAG,
    ]


class CreateTimeMapsTool(_BasePEATTool):
    label = "Create Time Maps"
    description = "Convert evacuation surfaces into integer raster and polygon time maps (optionally filled over buildings)."
    _module_name = "CreateTimeMap"
    _func_name = "genTimes"
    _arg_count = 4
    _param_spec = [
        {"display": "Project Workspace (File GDB)", "name": "workspace", "type": "DEWorkspace"},
        {"display": "Scenario Name", "name": "scenario", "type": "GPString"},
        {"display": "Evacuation Surfaces (semicolon-separated names)", "name": "surfaces", "type": "GPString"},
        {"display": "Buildings (optional)", "name": "buildings", "type": "GPFeatureLayer", "parameterType": "Optional"},
        _OUTPUT_FLAG,
    ]


class CreateSpeedMapTool(_BasePEATTool):
    label = "Create Speed Map"
    description = "Create raster and polygon speed maps from one or more time maps and an event arrival time."
    _module_name = "CreateSpeedMap"
    _func_name = "genSpeeds"
    _arg_count = 5
    _param_spec = [
        {"display": "Project Workspace (File GDB)", "name": "workspace", "type": "DEWorkspace"},
        {"display": "Scenario Name", "name": "scenario", "type": "GPString"},
        {"display": "Time Maps (semicolon-separated names)", "name": "time_maps", "type": "GPString"},
        {"display": "Event Arrival Time (minutes)", "name": "arrival_time", "type": "GPLong"},
        {"display": "Delay Time (minutes, optional)", "name": "delay_time", "type": "GPLong", "parameterType": "Optional"},
        _OUTPUT_FLAG,
    ]


class CreateVerticalEvacuationMapsTool(_BasePEATTool):
    label = "Create Vertical Evacuation Maps"
    description = "Create vertical evacuation time maps for each structure in an input VE feature class."
    _module_name = "CreateVertEvacMaps"
    _func_name = "createVertEvacs"
    _arg_count = 5
    _param_spec = [
        {"display": "Project Workspace (File GDB)", "name": "workspace", "type": "DEWorkspace"},
        {"display": "Scenario Name", "name": "scenario", "type": "GPString"},
        {"display": "Base Time Map Raster (name)", "name": "basemap", "type": "GPString"},
        {"display": "Vertical Evacuation Features", "name": "vertical_features", "type": "GPFeatureLayer"},
        {"display": "VE ID Field", "name": "id_field", "type": "GPString"},
        _OUTPUT_FLAG,
    ]


class CheckForTimeOutliersTool(_BasePEATTool):
    label = "Check for Time Outliers"
    description = "Cap evacuation surface values above a maximum travel time threshold."
    _module_name = "CheckForTimeOutliers"
    _func_name = "checkForOutliers"
    _arg_count = 3
    _param_spec = [
        {"display": "Project Workspace (File GDB)", "name": "workspace", "type": "DEWorkspace"},
        {"display": "Scenario Name", "name": "scenario", "type": "GPString"},
        {"display": "Evacuation Surface + Max Times (e.g. \"evacsurf_... 80;evacsurf_... 94\")", "name": "max_times", "type": "GPString"},
        _OUTPUT_FLAG,
    ]


class CreateEvacuationBasinsTool(_BasePEATTool):
    label = "Create Evacuation Basins"
    description = "Generate evacuation pour points, flow lines, and watershed boundaries using roads (and optional population)."
    _module_name = "CreateEvacuationBasins"
    _func_name = "createTheBasins"
    _arg_count = 4
    _param_spec = [
        {"display": "Project Workspace (File GDB)", "name": "workspace", "type": "DEWorkspace"},
        {"display": "Road Lines", "name": "road_lines", "type": "GPFeatureLayer"},
        {"display": "Population Points (optional)", "name": "population", "type": "GPFeatureLayer", "parameterType": "Optional"},
        {"display": "Population Field (optional)", "name": "population_field", "type": "GPString", "parameterType": "Optional"},
        _OUTPUT_FLAG,
    ]


class DeleteScenarioTool(_BasePEATTool):
    label = "Delete Scenario"
    description = "Delete all stored outputs for the selected scenario."
    _module_name = "DeleteScenario"
    _func_name = "deleteTheScenario"
    _arg_count = 2
    _param_spec = [
        {"display": "Project Workspace (File GDB)", "name": "workspace", "type": "DEWorkspace"},
        {"display": "Scenario Name", "name": "scenario", "type": "GPString"},
        _OUTPUT_FLAG,
    ]


class AddLayerToMapTool(_BasePEATTool):
    label = "Add Layer to Map (utility)"
    description = "Add an existing raster/feature layer to the current map with PEAT symbology (where available)."
    _module_name = "addResultToMap"
    _func_name = "addLayerToMap"
    _arg_count = 3
    _param_spec = [
        {"display": "Project Workspace (File GDB)", "name": "workspace", "type": "DEWorkspace"},
        {"display": "Layer Path", "name": "layer_path", "type": "GPString"},
        {"display": "PEAT Output Type (e.g. \"time_map\", \"speed_map\")", "name": "peat_type", "type": "GPString"},
        _OUTPUT_FLAG,
    ]

