# -*- coding: utf-8 -*-
"""Python toolbox wrapper for the Pedestrian Evacuation Analyst tools."""
import arcpy
from typing import Callable, List

from addResultToMap import addResultToMap
from CheckForTimeOutliers import findTimeOutliers
from CreateEvacuationBasins import createBasins
from CreateEvacuationSurface import createEvacuationSurface
from CreateSpeedMap import genSpeedMap
from CreateTimeMap import genTimes
from CreateVertEvacMaps import generateVEmaps
from DeleteScenario import deleteScenario
from PreprocessDEM import preDEM
from PreprocessHazard import preHazard
from PreprocessLandCover import preLandCover
from PreprocessSafezone import preSafezone


_OUTPUT_FLAG = {
    "display": "Succeeded",
    "name": "succeeded",
    "type": "GPBoolean",
    "parameterType": "Derived",
    "direction": "Output",
}


def _build_parameters(specs: List[dict]) -> List[arcpy.Parameter]:
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

    label: str = ""
    description: str = ""
    canRunInBackground = False
    _param_spec: List[dict] = []
    _func: Callable[..., object]
    _arg_count: int = 0

    def getParameterInfo(self) -> List[arcpy.Parameter]:
        return _build_parameters(self._param_spec)

    def execute(self, parameters: List[arcpy.Parameter], messages: arcpy.messages) -> None:
        args = [p.valueAsText for p in parameters[: self._arg_count]]
        result = self._func(*args)
        if parameters:
            parameters[-1].value = result is not None


class Toolbox(object):
    def __init__(self):
        self.label = "Pedestrian Evacuation Analyst"
        self.alias = "PEAT"
        self.tools = [
            PreprocessDEMTool,
            PreprocessHazardTool,
            PreprocessLandCoverTool,
            PreprocessSafezoneTool,
            CreateEvacuationSurfaceTool,
            CreateTimeMapTool,
            CreateSpeedMapTool,
            CreateVertEvacMapsTool,
            CheckForTimeOutliersTool,
            CreateEvacuationBasinsTool,
            DeleteScenarioTool,
            AddResultToMapTool,
        ]


class PreprocessDEMTool(_BasePEATTool):
    label = "Preprocess DEM"
    description = "Prepare elevation and study area inputs for subsequent PEAT processing."
    _func = preDEM
    _arg_count = 3
    _param_spec = [
        {"display": "Project Workspace", "name": "workspace", "type": "DEWorkspace"},
        {"display": "Elevation Raster", "name": "elevation", "type": "GPRasterLayer"},
        {"display": "Study Area", "name": "study_area", "type": "GPFeatureLayer", "parameterType": "Optional"},
        _OUTPUT_FLAG,
    ]


class PreprocessHazardTool(_BasePEATTool):
    label = "Preprocess Hazard"
    description = "Project hazard polygons, clip to the study area, and build a preliminary safe zone."
    _func = preHazard
    _arg_count = 2
    _param_spec = [
        {"display": "Project Workspace", "name": "workspace", "type": "DEWorkspace"},
        {"display": "Hazard Zone", "name": "hazard", "type": "GPFeatureLayer"},
        _OUTPUT_FLAG,
    ]


class PreprocessLandCoverTool(_BasePEATTool):
    label = "Preprocess Landcover"
    description = "Create landcover cost rasters and supporting layers for a scenario."
    _func = preLandCover
    _arg_count = 7
    _param_spec = [
        {"display": "Project Workspace", "name": "workspace", "type": "DEWorkspace"},
        {"display": "Scenario Name", "name": "scenario", "type": "GPString"},
        {"display": "Base Landcover Layer", "name": "base_layer", "type": "GPString"},
        {"display": "Base Landcover Field", "name": "base_field", "type": "GPString"},
        {"display": "Base SCV Values", "name": "base_values", "type": "GPString"},
        {"display": "Feature Add-ons", "name": "feature_addons", "type": "GPString", "parameterType": "Optional"},
        {"display": "Raster Add-ons", "name": "raster_addons", "type": "GPString", "parameterType": "Optional"},
        _OUTPUT_FLAG,
    ]


class PreprocessSafezoneTool(_BasePEATTool):
    label = "Preprocess Safe Zone"
    description = "Validate and store the edited safe zone polygons."
    _func = preSafezone
    _arg_count = 2
    _param_spec = [
        {"display": "Project Workspace", "name": "workspace", "type": "DEWorkspace"},
        {"display": "Safe Zone", "name": "safe_zone", "type": "GPFeatureLayer"},
        _OUTPUT_FLAG,
    ]


class CreateEvacuationSurfaceTool(_BasePEATTool):
    label = "Create Evacuation Surface"
    description = "Generate evacuation surfaces for a scenario using landcover speeds."
    _func = createEvacuationSurface
    _arg_count = 3
    _param_spec = [
        {"display": "Project Workspace", "name": "workspace", "type": "DEWorkspace"},
        {"display": "Scenario Name", "name": "scenario", "type": "GPString"},
        {"display": "Walking Speeds", "name": "speeds", "type": "GPString"},
        _OUTPUT_FLAG,
    ]


class CreateTimeMapTool(_BasePEATTool):
    label = "Create Time Maps"
    description = "Convert evacuation surfaces into raster and feature time maps."
    _func = genTimes
    _arg_count = 4
    _param_spec = [
        {"display": "Project Workspace", "name": "workspace", "type": "DEWorkspace"},
        {"display": "Scenario Name", "name": "scenario", "type": "GPString"},
        {"display": "Evacuation Surfaces", "name": "surfaces", "type": "GPString"},
        {"display": "Buildings", "name": "buildings", "type": "GPFeatureLayer", "parameterType": "Optional"},
        _OUTPUT_FLAG,
    ]


class CreateSpeedMapTool(_BasePEATTool):
    label = "Create Speed Map"
    description = "Calculate travel-speed rasters from time maps and arrival settings."
    _func = genSpeedMap
    _arg_count = 5
    _param_spec = [
        {"display": "Project Workspace", "name": "workspace", "type": "DEWorkspace"},
        {"display": "Scenario Name", "name": "scenario", "type": "GPString"},
        {"display": "Time Map Surfaces", "name": "time_maps", "type": "GPString"},
        {"display": "Arrival Time", "name": "arrival_time", "type": "GPDouble"},
        {"display": "Departure Delay", "name": "delay", "type": "GPDouble", "parameterType": "Optional"},
        _OUTPUT_FLAG,
    ]


class CreateVertEvacMapsTool(_BasePEATTool):
    label = "Create Vertical Evacuation Maps"
    description = "Build vertical evacuation maps using inputs such as towers or safe structures."
    _func = generateVEmaps
    _arg_count = 5
    _param_spec = [
        {"display": "Project Workspace", "name": "workspace", "type": "DEWorkspace"},
        {"display": "Scenario Name", "name": "scenario", "type": "GPString"},
        {"display": "Base Map", "name": "basemap", "type": "GPString", "parameterType": "Optional"},
        {"display": "Vertical Evacuation Features", "name": "vertical_features", "type": "GPFeatureLayer"},
        {"display": "Capacity Field", "name": "capacity_field", "type": "GPString"},
        _OUTPUT_FLAG,
    ]


class CheckForTimeOutliersTool(_BasePEATTool):
    label = "Check for Time Outliers"
    description = "Identify locations where computed travel times exceed a threshold."
    _func = findTimeOutliers
    _arg_count = 3
    _param_spec = [
        {"display": "Project Workspace", "name": "workspace", "type": "DEWorkspace"},
        {"display": "Scenario Name", "name": "scenario", "type": "GPString"},
        {"display": "Maximum Travel Time", "name": "max_time", "type": "GPDouble"},
        _OUTPUT_FLAG,
    ]


class CreateEvacuationBasinsTool(_BasePEATTool):
    label = "Create Evacuation Basins"
    description = "Trace road networks to build evacuation basins and population summaries."
    _func = createBasins
    _arg_count = 4
    _param_spec = [
        {"display": "Project Workspace", "name": "workspace", "type": "DEWorkspace"},
        {"display": "Road Lines", "name": "road_lines", "type": "GPFeatureLayer"},
        {"display": "Population Layer", "name": "population", "type": "GPFeatureLayer"},
        {"display": "Population Field", "name": "population_field", "type": "GPString"},
        _OUTPUT_FLAG,
    ]


class DeleteScenarioTool(_BasePEATTool):
    label = "Delete Scenario"
    description = "Remove a scenario and its stored outputs from the project workspace."
    _func = deleteScenario
    _arg_count = 2
    _param_spec = [
        {"display": "Project Workspace", "name": "workspace", "type": "DEWorkspace"},
        {"display": "Scenario Name", "name": "scenario", "type": "GPString"},
        _OUTPUT_FLAG,
    ]


class AddResultToMapTool(_BasePEATTool):
    label = "Add Result to Map"
    description = "Add an existing PEAT output layer to the current ArcGIS Pro map."
    _func = addResultToMap
    _arg_count = 4
    _param_spec = [
        {"display": "Project Workspace", "name": "workspace", "type": "DEWorkspace"},
        {"display": "Scenario Name", "name": "scenario", "type": "GPString"},
        {"display": "PEAT Output Type", "name": "peat_type", "type": "GPString"},
        {"display": "Input Layer", "name": "input_layer", "type": "GPString"},
        _OUTPUT_FLAG,
    ]
