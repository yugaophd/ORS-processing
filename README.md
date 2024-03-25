# ORS-processing project

Create merged deep temperature for three ORS sites: Stratus, NTAS and WHOTS.

# Architecture of the Code

- `src/netcdf.py` contains functions for reading .mat files, incorporating metadata, converting to NetCDF format, and saving the output.
- `src/ORS2024_Process.py` is the main file that uses the funcstions in `src/netcdf.py` to process the data.
- `src/plot.py` contain functions visualizing the data from your NetCDF files. This module can import the processed data and create plots, which can be saved in the img/ directory.
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

