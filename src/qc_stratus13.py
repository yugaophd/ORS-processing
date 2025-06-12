# %%
# Quality Control and deployment catalog
import os
os.chdir('/Users/yugao/UOP/ORS-processing/src')

import xarray as xr
import glob
from qc_function import remove_spikes, compute_diff_stats

case_name = 'stratus13'
project_name = 'stratus'
project_number = "13"
version = 'v1'

print(f'{project_name}{project_number}')

# %%
# Load the dataset
data_path = f'/Users/yugao/UOP/ORS-processing/data/processed/{project_name}{project_number}/{version}/'

# Construct the file pattern to search for
file_pattern = os.path.join(data_path, f'{project_name}{project_number}_*truncated.nc')

# Use glob to find all files matching the pattern
files = glob.glob(file_pattern)

# Optionally, print the list of files found

print(files)

# %%
# open dataset
ds0 = xr.open_dataset(files[0]).isel(time=slice(0, -1))
ds1 = xr.open_dataset(files[1]).isel(time=slice(0, -1))

# %%
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

fig.suptitle(f'Comparison within {project_name}{project_number} Data\n \
            Anchor location: ({formatted_latitude}$, {formatted_longitude}$)', fontsize=16)

plt.tight_layout(rect=[0, 0.03, 1, 0.95])

plot_path = '../../img/'
if not os.path.exists(plot_path):
    os.makedirs(plot_path)

plot_filename = os.path.join(plot_path, f"{project_name}{project_number}_{instrument_SN}_vs_{instrument_SN2}_no_spike.png")
plt.savefig(plot_filename)
print(f'Plot saved as {plot_filename}')


# %%
# human in the loop (HITL) to check the data quality
# open dataset
ds0_original = xr.open_dataset(files[0]).isel(time=slice(0, -1))
ds1_original = xr.open_dataset(files[1]).isel(time=slice(0, -1))

# %%
# Create HITL catalog for the two datasets
from qc_function import create_hitl_catalog

create_hitl_catalog(ds0_original, ds0, case_name, instrument_SN)
create_hitl_catalog(ds1_original, ds1, case_name, instrument_SN2)

# %%
# Compute the difference statistics

from qc_function import export_diff_stats, compute_diff_stats

# Compute the mean and standard deviation of the difference between the two datasets
# Example dataset setup (assuming ds0 and ds1 are your xarray datasets)

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

# Specify output directory, which can depend on your project structure
output_dir = f'../doc/{project_name}/{project_number}'

# Call the function to export LaTeX tables
export_diff_stats(sensor1_data, sensor2_data, instrument_number1,instrument_number2, 
                    output_dir, project_name, project_number)

# %%
# the last data point is abnormal
# ds0.sea_water_temperature[-10:].data

# # %%
# plt.plot(ds0.sea_water_temperature.time[-10:], ds0.sea_water_temperature[-10:], 'x')
# plt.plot(ds1.sea_water_temperature.time[-10:], ds0.sea_water_temperature[-10:], '*')
# # %%
# plt.plot(ds0.sea_water_practical_salinity.time[-10:], ds0.sea_water_practical_salinity[-10:], 'x')
# plt.plot(ds0.sea_water_practical_salinity.time[-10:], ds0.sea_water_practical_salinity[-10:], '*')

# %%
# # remove the last data point
# ds0 = ds0.isel(time=slice(0, -1))
# ds1 = ds1.isel(time=slice(0, -1))

# # %%
# # Add sensor stats to variables
# from qc_function import add_sensor_stats_to_variables

# # Add sensor stats to variables
# ds0, ds1 = add_sensor_stats_to_variables(ds0, ds1, variables)


# # %%
# # export the cleaned data
ds0.to_netcdf(f'{data_path}/{project_name}{project_number}_{instrument_SN}_cleaned.nc')
ds1.to_netcdf(f'{data_path}/{project_name}{project_number}_{instrument_SN2}_cleaned.nc')
ds0_original.to_netcdf(f'{data_path}/{project_name}{project_number}_{instrument_SN}_original.nc')
ds1_original.to_netcdf(f'{data_path}/{project_name}{project_number}_{instrument_SN2}_original.nc')

# %%
import matplotlib.dates as mdates
from util import convert_cftime_to_matplotlib 
from datetime import datetime
import numpy.ma as ma
variables = ['sea_water_temperature', 
            'sea_water_practical_salinity', 
            'sea_water_absolute_salinity', 
            'sea_water_electrical_conductivity', 
            'sea_water_pressure']
labels = ['Temperature (°C)', 
        'Salinity (psu)', 
        'Absolute Salinity (g/kg)', 
        'Conductivity (S/m)', 
        'Pressure (dbar)']
panel_titles = ['Temperature', 
                'Practical Salinity', 
                'Absolute Salinity', 
                'Conductivity', 
                'Pressure']

colors = ['blue', 'green', 'red', 'purple', 'black']
colors2 = ['cyan', 'lightgreen', 'pink', 'violet', 'gray']
    
fig, axs = plt.subplots(len(variables), 1, figsize=(12, 15), sharex=True)
for i, var in enumerate(variables):
    ax = axs[i]
    has_data = False
    
    if var in ds1_original.variables:
        time_data = convert_cftime_to_matplotlib(ds1_original[var].time.values)
        var_data = ds1_original[var].values
        var_mask = np.isnan(var_data)
        
        if hasattr(ds1_original[var], 'encoding') and '_FillValue' in ds1_original[var].encoding:
            fill_val = ds1_original[var].encoding['_FillValue']
            var_mask = np.logical_or(var_mask, var_data == fill_val)
        
        masked_data = ma.masked_array(var_data, mask=var_mask)
        ax.plot(time_data, masked_data, 
                label=f'SBE {instrument_SN}', color=colors[i])
        has_data = True
    
    if var in ds0_original.variables:
        time_data2 = convert_cftime_to_matplotlib(ds0_original[var].time.values)
        var_data = ds0_original[var].values
        var_mask = np.isnan(var_data)
        
        if hasattr(ds0_original[var], 'encoding') and '_FillValue' in ds0_original[var].encoding:
            fill_val = ds0_original[var].encoding['_FillValue']
            var_mask = np.logical_or(var_mask, var_data == fill_val)
        
        masked_data2 = ma.masked_array(var_data, mask=var_mask)
        ax.plot(time_data2, masked_data2, 
                label=f'SBE {instrument_SN2}', color=colors2[i])
        has_data = True
    
    # Compute statistics between datasets if both are available
    if var in ds1_original.variables and var in ds0_original.variables:
        try:
            # We can't easily calculate diff statistics without aligning the data
            # So we'll just calculate correlation if both datasets have enough points
            if len(masked_data.compressed()) > 2 and len(masked_data2.compressed()) > 2:
                # Note: this is only meaningful if the time ranges overlap significantly
                try:
                    correlation = np.corrcoef(
                        masked_data.compressed()[:min(len(masked_data.compressed()), len(masked_data2.compressed()))], 
                        masked_data2.compressed()[:min(len(masked_data.compressed()), len(masked_data2.compressed()))]
                    )[0, 1]
                    ax.legend(title=f'Correlation: {correlation:.3f}')
                except:
                    ax.legend()
            else:
                ax.legend()
        except Exception as e:
            print(f"Error calculating statistics for {var}: {e}")
            ax.legend()
    elif has_data:
        ax.legend()
    
    ax.set_title(panel_titles[i])
    ax.set_ylabel(labels[i])
    
    # Add gridlines for better readability
    ax.grid(True, alpha=0.3)
    
axs[-1].set_xlabel('Time')

# Format x-axis to show dates
date_form = mdates.DateFormatter("%Y-%m-%d")
axs[-1].xaxis.set_major_formatter(date_form)
axs[-1].xaxis.set_major_locator(mdates.MonthLocator())
plt.gcf().autofmt_xdate()

# Get deployment metadata
latitude = ds0.latitude_anchor_survey if hasattr(ds0, 'latitude_anchor_survey') else 0
longitude = ds0.longitude_anchor_survey if hasattr(ds0, 'longitude_anchor_survey') else 0

# Format latitude and longitude
if float(latitude) < 0:
    formatted_latitude = f"{abs(float(latitude)):.4f}°S"
else:
    formatted_latitude = f"{float(latitude):.4f}°N"

if float(longitude) < 0:
    formatted_longitude = f"{abs(float(longitude)):.4f}°W"
else:
    formatted_longitude = f"{float(longitude):.4f}°E"

# Create a more informative title
instrument_depth = ds0.attrs.get('instrument_depth', 'Unknown')

fig.suptitle(
    f'Comparison within {case_name} Data\n'
    f'Location: ({formatted_latitude}, {formatted_longitude}) | '
    f'Depth: {instrument_depth}m | V{version}', 
    fontsize=16
)

plt.tight_layout(rect=[0, 0.03, 1, 0.95])

plot_path = '../img/'
os.makedirs(plot_path, exist_ok=True)
plot_filename = os.path.join(plot_path, f"{case_name}_{instrument_SN}_vs_{instrument_SN2}_comparison.png")
plt.savefig(plot_filename, dpi=150)
print(f'Plot saved as {plot_filename}')

# %%
# Export spike statistics to LaTeX
from qc_function import export_spike_stats

# Format the spike data for export
spike_data = {
    f'instrument_{instrument_SN}': spike_percentages['ds0'],
    f'instrument_{instrument_SN2}': spike_percentages['ds1']
}

# Export to LaTeX file in the doc directory
export_spike_stats(
    spike_data, 
    [instrument_SN, instrument_SN2],  # List of instrument numbers
    output_dir,                       # Using the same output_dir you defined earlier
    project_name,                     # Project name (stratus)
    project_number                    # Project number (13)
)

# %%
