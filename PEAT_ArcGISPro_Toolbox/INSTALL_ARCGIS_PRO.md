# Install in ArcGIS Pro

1. Copy the entire `PEAT_ArcGISPro_Toolbox/` folder to a local location (keep the folder contents together).
2. In ArcGIS Pro, open the **Catalog** pane.
3. Right-click **Toolboxes** → **Add Toolbox…**
4. Select `Pedestrian_Evacuation_Analyst.pyt` from inside the copied `PEAT_ArcGISPro_Toolbox/` folder.

## Notes on licensing

- This toolbox wrapper does **not** implement a custom `isLicensed()` gate.
- Tools that use Spatial Analyst call `arcpy.CheckOutExtension("Spatial")` at runtime; if Spatial Analyst is available/active in ArcGIS Pro, the tools will run normally.

## If ArcGIS Pro still can’t add the toolbox

ArcGIS Pro will refuse to add a `.pyt` if it raises an exception during import.
To see the exact error, open **View → Python Window** and run:

```python
import traceback
try:
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "PEAT_PYT",
        r"<FULL_PATH>\PEAT_ArcGISPro_Toolbox\Pedestrian_Evacuation_Analyst.pyt",
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    print("Loaded OK")
except Exception:
    print(traceback.format_exc())
```


