# %%
# Quality Control and deployment catalog
# For all variables:{'temp', 'cond', 'sal', 'abs_sal', 'press'}
import os
os.chdir('/Users/yugao/UOP/ORS-processing/src')

import xarray as xr
import glob
from qc_function import remove_spikes, compute_diff_stats
import numpy as np


# Define project names - keep lowercase for file paths
project_name = 'stratus'
project_number = "12"
case_name = f'{project_name}{project_number}'
version = 'v1'

# Create display versions for plots and visualization
project_name_display = 'STRATUS'  # All caps for display
case_name_display = f'{project_name_display}{project_number}'

print(f'case_name: {project_name}{project_number}')
print(f'display name: {case_name_display}')

# %%
# Load the dataset
data_path = f'/Users/yugao/UOP/ORS-processing/data/processed/{project_name}{project_number}/{version}/'

# Construct the file pattern to search for
file_pattern = os.path.join(data_path, f'{project_name}{project_number}_*truncated_{version}.nc')

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

variables = ['sea_water_temperature', 
            'sea_water_practical_salinity', 
            'sea_water_absolute_salinity', 
            'sea_water_electrical_conductivity', 
            'sea_water_pressure']

# Initialize dictionary for spike percentages
spike_percentages = {'ds0': {}, 'ds1': {}}

# Apply spike removal to each variable
for i, ds in enumerate([ds0, ds1]):
    ds_name = f"ds{i}"
    print(f"\nProcessing {ds_name} - Instrument SN: {ds.attrs.get('instrument_SN', 'unknown')}")
    
    for var in variables:
        if var in ds.data_vars:
            # Get total number of data points before cleaning
            total_points = ds[var].size
            non_nan_points = np.sum(~np.isnan(ds[var].values))
            
            # Keep original for spike counting
            original_values = ds[var].copy(deep=True)
            
            # Apply spike removal
            ds[var], spikes_count = remove_spikes(ds[var])
            
            # Calculate percentage of spikes
            if non_nan_points > 0:  # Avoid division by zero
                spike_percentage = (spikes_count / non_nan_points) * 100
            else:
                spike_percentage = 0
                
            # Store spike percentage in the dictionary
            spike_percentages[ds_name][var] = spike_percentage
            
            print(f"  {var}: {spikes_count} spikes removed ({spike_percentage:.4f}% of valid data points)")

# %%
# compare stats of two instruments when the data are valid

# ds0, ds1

import matplotlib.pyplot as plt
import numpy as np

# Construct the file path
instrument_SN = ds0.attrs.get('instrument_SN', 'unknown')  # Default to 'unknown' if not present
instrument_SN2 = ds1.attrs.get('instrument_SN', 'unknown')  # Default to 'unknown' if not present

labels = ['Temperature (°C)', 'Salinity', 'Absolute Salinity', 'Conductivity (S/m)', 'Pressure']
panel_titles = ['Temperature Profile', 'Salinity Measurements', 'Absolute Salinity', 'Conductivity Levels', 'Pressure Profile']

colors = ['blue', 'green', 'red', 'purple', 'black']
colors2 = ['cyan', 'lightgreen', 'pink', 'violet', 'gray']

fig, axs = plt.subplots(len(variables), 1, figsize=(12, 15), sharex=True)

for i, var in enumerate(variables):
    if var in ds0.variables:
        print(f'plotting {var} 1')
        axs[i].plot(ds0[var].time, ds0[var].values, 
                    label=f'{var} (SBE {instrument_SN}, {project_name_display})', color=colors[i])
    
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
# For latitude (negative = South, positive = North)
if float(latitude) < 0:
    formatted_latitude = f"{abs(float(latitude))} °S"
else:
    formatted_latitude = f"{latitude} °N"

# For longitude (negative = West, positive = East)
if float(longitude) < 0:
    formatted_longitude = f"{abs(float(longitude))} °W"
else:
    formatted_longitude = f"{longitude} °E"

# For plot titles
fig.suptitle(f'Comparison within {case_name_display} Data\n \
            Anchor location: ({formatted_latitude}$, {formatted_longitude}$)', fontsize=16)

plt.tight_layout(rect=[0, 0.03, 1, 0.95])

plot_path = '../../img/'
if not os.path.exists(plot_path):
    os.makedirs(plot_path)

# For filenames, keep using lowercase version
plot_filename = os.path.join(plot_path, f"{project_name}{project_number}_{instrument_SN}_vs_{instrument_SN2}_no_spike.png")
plt.savefig(plot_filename)
print(f'Plot saved as {plot_filename}')


# %%
# human in the loop (HITL) to check the data quality
# open dataset
ds0_original = xr.open_dataset(files[0])
ds1_original = xr.open_dataset(files[1])

# %%
# Create HITL catalog for the two datasets
from qc_function import create_hitl_catalog

# When creating HITL catalog
create_hitl_catalog(ds0_original, ds0, case_name, instrument_SN, display_name=case_name_display)
create_hitl_catalog(ds1_original, ds1, case_name, instrument_SN2)

# %%
# Compute the difference statistics
from qc_function import export_diff_stats


# Initialize dictionaries to store sensor data for each dataset
sensor1_data = {'mean': {}, 'std': {}}
sensor2_data = {'mean': {}, 'std': {}}

# Collect data for sensor 1 (ds0)
for var in variables:
    if var in ds0:
        sensor1_data['mean'][var] = float(ds0[var].mean().values)  # Ensure conversion to standard Python float
        sensor1_data['std'][var] = float(ds0[var].std().values)
    if var in ds1:
        sensor2_data['mean'][var] = float(ds1[var].mean().values)
        sensor2_data['std'][var] = float(ds1[var].std().values)

# Specify instrument number or identifier (assuming it's stored in dataset attributes or is known)
instrument_number1 = ds0.attrs.get('instrument_SN', 'unknown')  # Use the same for ds1 if it's the same instrument
instrument_number2 = ds1.attrs.get('instrument_SN', 'unknown')

# %%
# Add sensor stats to variables
from qc_function import add_sensor_stats_to_variables

# Add sensor stats to variables
ds0, ds1 = add_sensor_stats_to_variables(ds0, ds1, variables)

# %% save the cleaned data

ds0.to_netcdf(f'{data_path}/{project_name}{project_number}_{instrument_SN}_cleaned.nc')
ds1.to_netcdf(f'{data_path}/{project_name}{project_number}_{instrument_SN2}_cleaned.nc')

# %%
# Specify output directory, which can depend on your project structure
output_dir = f'../doc/{project_name}/{project_number}'

# Call the function to export LaTeX tables
export_diff_stats(sensor1_data, sensor2_data, instrument_number1,instrument_number2, 
                    output_dir, project_name, project_number)

# After calculating spike percentages:
from qc_function import export_spike_stats

# Format the spike data for export
spike_data = {
    f'instrument_{instrument_SN}': spike_percentages['ds0'],
    f'instrument_{instrument_SN2}': spike_percentages['ds1']
}

# Export to LaTeX file in the doc directory
doc_dir = f'/Users/yugao/UOP/ORS-processing/doc/{project_name}/{project_number}'
export_spike_stats(
    spike_data, 
    [instrument_SN, instrument_SN2],  # List of instrument numbers
    doc_dir,                          # Output directory
    project_name,                     # Project name (stratus)
    project_number                    # Project number (12)
)
