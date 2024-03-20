# ORS-processing project

Create merged deep temperature for three ORS sites: Stratus, NTAS and WHOTS.

# Architecture of the Code

- `src/ORS2023_Process.py` is the main file.
- `src/netcdf.py` and `src/plot.py` contain functions used in `ORS2023_Process.py`.
- `environment.yml` can be used to create a mamba/conda environment:
  ```bash
  mamba env create -f environment.yml -n ORS_process
  ```
  This will create a new mamba environment named `ORS_process`.

## Data Directory Structure

- `data/` will contain all data files for this project.
- `data/external` contains the raw data files collected from the deployment.
- `data/metadata` contains the JSON files used for variable attributes.
- `data/processed` contains the processed netCDF output file.

## Images Directory

- `img/` will contain plots and other images used for data visualization.

