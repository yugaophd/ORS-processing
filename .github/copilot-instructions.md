# AI Agent Guide: ORS-processing

## Big Picture
- Python pipeline for ORS (Stratus, NTAS): load MATLAB instrument files → standardize to CF/OceanSITES → compute salinity (TEOS-10) → QC/plots → merge adjacent deployments → publish LaTeX technical report.
- Focus modules: [src/util.py](src/util.py), [src/metadata.py](src/metadata.py), [src/netcdf_sbe37.py](src/netcdf_sbe37.py), [src/qc_function.py](src/qc_function.py), [src/plot_function.py](src/plot_function.py), [src/merge.py](src/merge.py).

## Architecture & Data Flow
- Per-deployment scripts: [src/all_stratus_processing.py](src/all_stratus_processing.py), [src/all_NTAS_processing.py](src/all_NTAS_processing.py).
  - Read `config` (e.g., [src/stratus22_config.json](src/stratus22_config.json), [src/NTAS14_config.json](src/NTAS14_config.json)) → `read_mat_file()` → `create_xarray_dataset()` → trim by `platform_anchor_over_time` and `platform_buoy_recovery_time` → rename variables to CF → compute salinity via `gsw` → standardize metadata → save `{case}_{serial}_truncated.nc`.
- Merge adjacent deployments: see [src/merge.py](src/merge.py) and outputs in `data/processed/merged_{project}`; attribute selection is defined in [src/metadata_merger.py](src/metadata_merger.py). Use `util.append_variable_attributes()` to keep sensor stats.
- Plotting: `plot_spike_data()`, `plot_deployment_recovery()` for phases; `plot_merged_dataset()` for full merged series with merge-point lines and distance panels. Batch plotting in [src/all_merged_plot.py](src/all_merged_plot.py).

## Conventions & Patterns
- Variables: rename `temp→sea_water_temperature`, `cond→sea_water_electrical_conductivity`, `press→sea_water_pressure`; compute and add `sea_water_practical_salinity`, `sea_water_absolute_salinity` via TEOS-10 `gsw` using instrument depth-derived pressure.
- Fill values: set `encoding['_FillValue'] = -99999.0`; prefer `dtype=float32` for computed salinity.
- Time: decode CF (`cftime`) then adjusted dates; for plotting convert with `util.convert_cftime_to_matplotlib()`.
- Metadata: call `metadata.standardize_attribute_names()` then `metadata.ensure_standard_attributes()`; reorder via `metadata.reorder_oceansites_attributes()`; add geospatial bounds with `metadata.add_geospatial_attributes()`; validate with `metadata.validate_attributes()`.
- Attributes often stored as comma-separated lists across deployments (e.g., `latitude_anchor_survey`, `merge_point`). Distance panels rely on these.

## Workflows (Commands)
- Env (conda/mamba): repo has [src/environment.yml](src/environment.yml) (`name: uop`).
  ```bash
  mamba env create -f src/environment.yml -n uop
  mamba activate uop
  mamba install gsw
  ```
- Process a deployment (edit `config_file` in the script):
  ```bash
  python src/all_stratus_processing.py   # or all_NTAS_processing.py
  ```
- Plot merged datasets:
  ```bash
  python src/all_merged_plot.py
  ```
- LaTeX report: follow [doc/stratus/WHOI_technical_report/README.md](doc/stratus/WHOI_technical_report/README.md).

## Integration Notes
- Paths are absolute (e.g., `/Users/yugao/UOP/ORS-processing`, `/Users/Shared/ORS`). Keep consistent or parameterize if relocating; many scripts `os.chdir('/Users/yugao/UOP/ORS-processing/src')`.
- TEOS-10 dependency `gsw` is required for salinity; computed pressure from `instrument_depth` via `gsw.p_from_z()` is the project standard (do not use raw `sea_water_pressure` for SA/SP).
- Config JSONs define `time_attribute_keys` to handle deployments with different key names; prefer reading times from dataset attrs, fallback to config overrides when present.

## Examples
- Append stats after merge:
  ```python
  merged = xr.concat([ds0, ds1], dim='time')
  merged = util.append_variable_attributes(ds1, merged)
  ```
- Validate metadata:
  ```python
  is_valid, issues = metadata.validate_attributes(ds)
  ```
- Plot merged with merge points and distances:
  ```python
  plot_function.plot_merged_dataset(ds, 'out.png', annotate_merge_points=True)
  ```

## Gotchas
- Ensure CF names before plotting/stats; many helpers expect `sea_water_*` names.
- `latitude_anchor_survey`/`longitude_anchor_survey` must cover all deployments (comma-separated) for distance panels to render.
- `merge_point` must be ISO8601 strings; `plot_function.plot_merge_points()` skips `None/NaT`.
- Root README mentions `ors` env; actual env file uses `uop`—prefer `uop`.
