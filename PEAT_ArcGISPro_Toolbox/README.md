<h3>The Pedestrian Evacuation Analyst Tool (PEAT)</h3>

<h4>GIS toolbox for evacuation modeling using Esri's ArcPro software</h4>

<h5>IPDS number</h5><p>IP-161737</p>

<h5>Author</h5><p>Jeanne Jones, jmjones@usgs.gov</p>

<h5>Citation</h5><p>Jones, J.M., 2024, Pedestrian Evacuation Analyst software source code, v1.0.0: U.S. Geological Survey Software Release, https://doi.org/10.5066/P1WACACF (IP-161737) 

<h5>Summary</h5>
<p>The Pedestrian Evacuation Analyst is an ArcGIS Pro toolbox that estimates how long it would take for someone to travel on foot out of a hazardous area that was threatened by a sudden event such as a tsunami, flash flood, or volcanic lahar. It takes into account the elevation changes and the different types of landcover that a person would encounter along the way.</p>

<h5>Description</h5>
<p>PEAT is a toolbox that gets added to the ArcPro catalog window and contains tools for preprocessing data, running the evacuation modeling to create the travel time maps, and performing additional analyses for vertical evacuation structures and evacuation pathways. The tools rely on user-supplied data for a study area, and simplify the process of creating the various geospatial products.</p>

<h5>Toolbox Location</h5>
<p>The toolbox and user guide are available for download on Sciencebase <strong><a href="https://www.sciencebase.gov/catalog/item/58ebc531e4b0b4d95d320186?community=Hazards+Vulnerability+Analysis">here</a></strong>.  The user guide is a 19-page pdf explaining how to install the toolbox and run each tool. It contains a reference section at the end with citations for many publications by USGS authors and collaborators describing the methodology behind the modeling and the value of the different geospatial products. The zipped toolbox contains the ArcPro toolbox and accompanying Python code.</p>

<h5>Usage</h5>
<p>The toolbox is designed to be run in Esri's ArcGIS Pro software application. The user should be comfortable using Pro, loading toolboxes, running tools, and navigating the catalog.</p>
<p>The software is designed to manage the storage of input and output files. The user only needs to create a folder for the toolbox and another for the processing storage. The user creates a file geodatabase in the processing storage folder and PEAT takes care of creating the tool data structure.</p>
<p>Esri's Distance Accumulation and Flow Accumulation tools can take several minutes to run depending on the size of the input Digital Elevation Model and the capacity of the machine it is running on. Most tools will complete within a few minutes or less.  However, some types of processing over larger areas can take up to an hour.</p>

<h5>Tool Structure</h5>
<p>PEAT is a fairly lightweight toolbox designed to run on user-supplied data. Python code in the repository beginning with a capital letter (e.g.CreateTimeMap.py) contain the top-level code for each tool. Code beginning with a small letter (e.g. makePopulationLines.py) contain functions called by the top-level code.</p>

