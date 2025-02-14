# %%
# Quality Control and deployment catalog
# For all variables:{'temp', 'cond', 'sal', 'abs_sal', 'press'}
import os
os.chdir('/Users/yugao/UOP/ORS-processing/src')

import xarray as xr
import glob
from qc_function import remove_spikes, compute_diff_stats

case_name = 'stratus16'
project_name = 'stratus'
project_number = "16"

print(f'{project_name}{project_number}')

# %%
# Load the dataset
data_path = f'/Users/yugao/UOP/ORS-processing/data/processed/{project_name}{project_number}'

# Construct the file pattern to search for
file_pattern = os.path.join(data_path, f'{project_name}{project_number}_*truncated.nc')

# Use glob to find all files matching the pattern
files = glob.glob(file_pattern)

# Optionally, print the list of files found

print(files)

# %%
# open dataset
ds0 = xr.open_dataset(files[0])
ds1 = xr.open_dataset(files[1])

# %%
# Apply spike removal to each variable

variables = ['temp', 'cond', 'sal', 'abssal', 'press']

# Apply spike removal to each variable
cleaned_variables = {}
for ds in [ds0, ds1]:
    for var in variables:
        if var in ds.data_vars:
            # Convert xarray DataArray to pandas Series for spike removal processing
            ds[var], spikes_count = remove_spikes(ds[var])
            # Store cleaned data back in a dictionary, can also convert back to DataArray if needed
            # cleaned_variables[var] = ds[var]
            print(spikes_count)

# %%
# compare stats of two instruments when the data are valid

# ds0, ds1

import matplotlib.pyplot as plt
import numpy as np

# Construct the file path
instrument_SN = ds0.attrs.get('instrument_SN', 'unknown')  # Default to 'unknown' if not present
instrument_SN2 = ds1.attrs.get('instrument_SN', 'unknown')  # Default to 'unknown' if not present

variables = ['temp', 'sal', 'abssal', 'cond', 'press']
labels = ['Temperature (°C)', 'Salinity', 'Absolute Salinity', 'Conductivity (S/m)', 'Pressure']
panel_titles = ['Temperature Profile', 'Salinity Measurements', 'Absolute Salinity', 'Conductivity Levels', 'Pressure Profile']

colors = ['blue', 'green', 'red', 'purple', 'black']
colors2 = ['cyan', 'lightgreen', 'pink', 'violet', 'gray']

fig, axs = plt.subplots(len(variables), 1, figsize=(12, 15), sharex=True)

for i, var in enumerate(variables):
    if var in ds0.variables:
        print(f'plotting {var} 1')
        axs[i].plot(ds0[var].time, ds0[var].values, 
                    label=f'{var} (SBE {instrument_SN})', color=colors[i])
    
    if var in ds1.variables:
        print(f'plotting {var} 2')
        axs[i].plot(ds1[var].time, ds1[var].values, 
                    label=f'{var} (SBE {instrument_SN2})', color=colors2[i])
    
    if var in ds0.variables and var in ds1.variables:
        print(f'plotting {var} correlation')
        correlation = np.corrcoef(ds0[var].values, ds1[var].values)[0, 1]
        axs[i].legend(title=f'Correlation: {correlation:.2f}')
    else:
        axs[i].legend()
    
    axs[i].set_title(panel_titles[i])
    axs[i].set_ylabel(labels[i])

axs[-1].set_xlabel('Time')

latitude = ds0.latitude_anchor_survey if hasattr(ds0, 'latitude_anchor_survey') else 0
longitude = ds0.longitude_anchor_survey if hasattr(ds0, 'longitude_anchor_survey') else 0
formatted_latitude = f"{-1 * latitude:.2f}"
formatted_longitude = f"{-1 * longitude:.2f}"

fig.suptitle(f'Comparison within {project_name}{project_number} Data\nAnchor location: ({formatted_latitude}$^\circ$S, {formatted_longitude}$^\circ$W)', fontsize=16)

plt.tight_layout(rect=[0, 0.03, 1, 0.95])

plot_path = '../../img/'
if not os.path.exists(plot_path):
    os.makedirs(plot_path)

plot_filename = os.path.join(plot_path, f"{project_name}{project_number}_{instrument_SN}_vs_{instrument_SN2}_no_spike.png")
plt.savefig(plot_filename)
print(f'Plot saved as {plot_filename}')


# %% save the cleaned data

# ds0.to_netcdf(f'{data_path}/{project_name}{project_number}_{instrument_SN}_cleaned.nc')
# ds1.to_netcdf(f'{data_path}/{project_name}{project_number}_{instrument_SN2}_cleaned.nc')

# %%
# human in the loop (HITL) to check the data quality
# open dataset
ds0_original = xr.open_dataset(files[0])
ds1_original = xr.open_dataset(files[1])

# %%
# Create HITL catalog for the two datasets
from qc_function import create_hitl_catalog

create_hitl_catalog(ds0_original, ds0, "stratus16", instrument_SN)
create_hitl_catalog(ds1_original, ds1, "stratus16", instrument_SN2)


# %%
# Compute the difference statistics

from qc_function import export_diff_stats, compute_diff_stats

# Compute the mean and standard deviation of the difference between the two datasets


# Example dataset setup (assuming ds0 and ds1 are your xarray datasets)
variables = ['temp', 'cond', 'sal', 'abssal', 'press']

# Initialize dictionaries to store sensor data for each dataset
sensor1_data = {'mean': {}, 'std': {}}
sensor2_data = {'mean': {}, 'std': {}}

# Collect data for sensor 1 (ds0)
for var in variables:
    if var in ds0:
        sensor1_data['mean'][var] = float(ds0[var].mean().values)  # Ensure conversion to standard Python float
        sensor1_data['std'][var] = float(ds0[var].std().values)

# Collect data for sensor 2 (ds1)
for var in variables:
    if var in ds1:
        sensor2_data['mean'][var] = float(ds1[var].mean().values)
        sensor2_data['std'][var] = float(ds1[var].std().values)

# Specify instrument number or identifier (assuming it's stored in dataset attributes or is known)
instrument_number1 = ds0.attrs.get('instrument_SN', 'unknown')  # Use the same for ds1 if it's the same instrument
instrument_number2 = ds1.attrs.get('instrument_SN', 'unknown')


# Store mean and std separately as attributes without JSON
for var, value in sensor1_data["mean"].items():
    ds0.attrs[f"sensor_mean_{var}"] = value
for var, value in sensor1_data["std"].items():
    ds0.attrs[f"sensor_std_{var}"] = value

for var, value in sensor2_data["mean"].items():
    ds1.attrs[f"sensor_mean_{var}"] = value
for var, value in sensor2_data["std"].items():
    ds1.attrs[f"sensor_std_{var}"] = value

# Store metadata
ds0.attrs.update({
    "instrument_SN": instrument_number1,
    "error_characterization_info": "Mean and standard deviation stored as separate attributes."
})

ds1.attrs.update({
    "instrument_SN": instrument_number2,
    "error_characterization_info": "Mean and standard deviation stored as separate attributes."
})

# %% save the cleaned data

ds0.to_netcdf(f'{data_path}/{project_name}{project_number}_{instrument_SN}_cleaned.nc')
ds1.to_netcdf(f'{data_path}/{project_name}{project_number}_{instrument_SN2}_cleaned.nc')

# Specify output directory, which can depend on your project structure
output_dir = f'../doc/{project_name}/{project_number}'

# Call the function to export LaTeX tables
export_diff_stats(sensor1_data, sensor2_data, instrument_number1,instrument_number2, 
                    output_dir, project_name, project_number)