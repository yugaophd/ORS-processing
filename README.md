# ORS-processing project

Create merged deep temperature for three ORS sites: Stratus, NTAS and WHOTS.

## To-Do List

- [ ] Refactor the `mat_to_xarray` function to handle metadata more gracefully.
- [ ] Implement unit tests for data processing functions.
- [ ] Optimize the data visualization module for larger datasets.
- [ ] Update the documentation to include new visualization features.
- [ ] Write a new script to filter out the T/S during deployment, keep the deep T/S data.

# Architecture of the Code

- `src/netcdf.py` contains functions for reading .mat files, incorporating metadata, converting to NetCDF format, and saving the output.
- `src/pre-process_stratusXX.py` is the main file that uses the funcstions in `src/netcdf.py` to pre-process the data.
- `src/qc_stratusXX.py` quality control, including spike removal and difference analysis.
- `src/merge_stratusXX.py` merge and analyze the overlapping observational datasets from neighboring Stratus missions to ensure seamless continuity and data integrity.
- `environment.yml` can be used to create a mamba/conda environment:
  ```bash
  mamba env create -f environment.yml -n ors
  ```
  This will create a new mamba environment named `ors`.

If you're using mamba, the process for setting up your Jupyter Lab environment to access the ors environment is as follows:

bash
Copy code
mamba activate ors
mamba install ipykernel
python -m ipykernel install --user --name=ors --display-name="Python (ors)"

After running these commands:

Activate your environment with mamba activate ors to switch to the ors environment.
Install ipykernel using mamba to ensure that Jupyter can use this environment as a kernel. mamba is a faster alternative to conda and can be used interchangeably for installing packages.
Register the environment with Jupyter by adding it as a new kernel. This is done with the python -m ipykernel install command, which makes your ors environment available as a kernel option in Jupyter notebooks and Jupyter Lab.
Once you've registered the ors environment as a kernel, restart Jupyter Lab. You should then be able to select "Python (ors)" from the kernel options, ensuring that your notebooks have access to the packages and environment you've set up for your project. This step is crucial for maintaining reproducibility and consistency across development environments, especially when working with data processing and analysis pipelines.

## Data Directory Structure

- `data/` will contain all data files for this project.
- `data/external` contains the raw data files collected from the deployment.
- `data/metadata` contains the JSON files used for variable attributes.
- `data/processed` contains the processed netCDF output file.

## Images Directory

- `img/` will contain plots and other images used for data visualization.

## Creating Metadata from MATLAB Files

This repository provides a Python script to extract metadata from MATLAB files and convert it into a structured JSON format. Metadata extraction is essential for organizing and documenting scientific data, enabling better data management, sharing, and interoperability.

### Step-by-Step Guide

1. **Pre-processing:**
   - Use the `pre-process_stratusXX.py` time check, interpolate time and truncate the temp, cond, and press. 
   - Produce truncated datasets: StratusXX_instrument_truncated.py at '/Users/yugao/UOP/ORS-processing/data/processed/StratusXX/'

2. **Quality Control:**
   - Use `qc_stratus17.py` Quality Control and deployment catalog for all variables:{'temp', 'cond', 'sal', 'abs_sal', 'press'}
   - Produce truncated datasets: StratusXX_instrument_cleaned.py at '/Users/yugao/UOP/ORS-processing/data/processed/StratusXX/'
   - Create Human In the Loop catalog in /Users/yugao/UOP/ORS-processing/img

3. **Merge datasets:**
   - Use `merge_stratus17.py` merge and analyze the overlapping observational datasets from neighboring Stratus missions to ensure seamless continuity and data integrity.


This concise guide outlines the essential steps for creating metadata from MATLAB files using Python. Adjust and expand each step as needed for your project's requirements.

### Usage

