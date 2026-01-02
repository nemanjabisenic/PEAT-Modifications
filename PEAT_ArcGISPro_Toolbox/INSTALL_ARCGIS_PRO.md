# Install in ArcGIS Pro

1. Copy the entire `PEAT_ArcGISPro_Toolbox/` folder to a local location (keep the folder contents together).
2. In ArcGIS Pro, open the **Catalog** pane.
3. Right-click **Toolboxes** → **Add Toolbox…**
4. Select `Pedestrian_Evacuation_Analyst.pyt` from inside the copied `PEAT_ArcGISPro_Toolbox/` folder.

## Notes on licensing

- This toolbox wrapper does **not** implement a custom `isLicensed()` gate.
- Tools that use Spatial Analyst call `arcpy.CheckOutExtension("Spatial")` at runtime; if Spatial Analyst is available/active in ArcGIS Pro, the tools will run normally.

