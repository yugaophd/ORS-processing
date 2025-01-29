# %%
# time check, interpolate time and truncate the temp, cond, and press. 

import numpy as np
import xarray as xr
import matplotlib.pyplot as plt
import os, sys
import json
import scipy.io
import cftime
import pandas as pd

os.chdir('/Users/yugao/UOP/ORS-processing/src')
from metadata import create_json, process_attributes_direct
from netcdf_sbe37 import read_mat_file
from util import create_xarray_dataset, process_attributes_direct, fill_or_create_variables 

# %%
# required input: case name, water depth and spike time
case_name = 'stratus17'
data_path = '/Users/yugao/UOP/ORS-processing/data/processed'

# from diagram
water_depth_from_mooring_diagram = 4540     # from mooring diagram

# from mooring log
water_depth_from_ship_uncorrected = np.nan     # uncorrected water depth, depth recorder reading
water_depth_from_ship_corrected = 4565       # corrected water depth, best water depth
instrument_height_above_bottom =  39   

#  Anchor (1) + chain (5) + nystron (20) + chain (5) + releases (1) + chain (5) 
# + 6 terminations at 0.25 ea (1.5) 
# + distance from termination on SBE cage to sensor (0.5) = 39 m

# %%
# spike time
deployment_spike_times_start = pd.to_datetime('04/06/2018 14:11')
deployment_spike_times_end = pd.to_datetime('04/06/2018 14:33')
recovery_spike_times_start = pd.to_datetime('04/23/2019 21:36')
recovery_spike_times_end = pd.to_datetime('04/23/2019 22:52')


# %%
# file input
mat_file_path1 = f'/Users/Shared/ORS/Stratus/{case_name}/data/sbe37/{case_name}_sbe37_11394.mat'
mat_file_path2 = f'/Users/Shared/ORS/Stratus/{case_name}/data/sbe37/{case_name}_sbe37_12257.mat'
mat_data1 = read_mat_file(mat_file_path1)
mat_data2 = read_mat_file(mat_file_path2)


# %%
# Convert the MATLAB file to an xarray dataset
ds = create_xarray_dataset(mat_data1)
ds2 = create_xarray_dataset(mat_data2)


# %%
# Process the metadata
processed_attributes = process_attributes_direct(mat_data1)
processed_attributes2 = process_attributes_direct(mat_data2)
ds.attrs.update(processed_attributes)
ds2.attrs.update(processed_attributes2)

# For ds (using mat data)
ds.attrs['latitude_anchor_survey'] = mat_data1['latitude']
ds.attrs['longitude_anchor_survey'] = mat_data1['longitude']

# For ds2 (using mat2 data)
ds2.attrs['latitude_anchor_survey'] = mat_data2['latitude']
ds2.attrs['longitude_anchor_survey'] = mat_data2['longitude']

# %%
# change the time attributes
ds['time'].attrs['units'] = 'days since 0001-01-01'
ds2['time'].attrs['units'] = 'days since 0001-01-01'

# Convert time data to account for MATLAB's year zero
decoded_time = xr.decode_cf(ds, use_cftime=True).time
decoded_time2 = xr.decode_cf(ds2, use_cftime=True).time

# Since MATLAB's year zero is not recognized, and it is treated as a leap year,
# we need to subtract one year (366 days) from the converted times
adjusted_dates = np.array([date - pd.Timedelta(days=365) for date in decoded_time.values])
adjusted_dates2 = np.array([date - pd.Timedelta(days=365) for date in decoded_time2.values])
# Assign the corrected time back to the dataset
ds['time'] = adjusted_dates
ds2['time'] = adjusted_dates2

#%%
# Print the first few datetime objects to verify
print(adjusted_dates)
print(adjusted_dates2)
ds['time'] = adjusted_dates
ds2['time'] = adjusted_dates2

# %%
# Truncate with anchor over time and release time
anchor_over_time =   pd.to_datetime(ds.attrs['platform_anchor_over_time'])
release_fired_time = pd.to_datetime(ds.attrs['platform_anchor_release_time'])
anchor_over_time2 =   pd.to_datetime(ds2.attrs['platform_anchor_over_time'])
release_fired_time2 = pd.to_datetime(ds2.attrs['platform_anchor_release_time'])


##### Truncation starts #####

# %%
# Truncate the dataset using the anchor time and 4 hours after
valid_time_window = ds.sel(time=slice(anchor_over_time + pd.Timedelta(hours=4), release_fired_time))
valid_time_window2 = ds2.sel(time=slice(anchor_over_time2 + pd.Timedelta(hours=4), release_fired_time2))


# %%
# update the attributes
time_coverage_start_str = str(anchor_over_time + pd.Timedelta(hours=4))
time_coverage_start_str2 = str(anchor_over_time2 + pd.Timedelta(hours=4))
print(f'time_coverage_start:' , time_coverage_start_str)
print(f'time_coverage_start2:' , time_coverage_start_str2)
valid_time_window.attrs['platform_data_start_time'] = time_coverage_start_str
valid_time_window2.attrs['platform_data_start_time'] = time_coverage_start_str2


# %%
# carry forward time series for all 5 variables (temp, cond, sal, abs sal, press) 
# even if they don’t exist (e.g. set to NaN or -999)
# Fill missing data or create non-existent variables in an xarray Dataset.

fill_or_create_variables(valid_time_window, ['temp', 'cond', 'sal', 'abssal', 'press'])
fill_or_create_variables(valid_time_window2, ['temp', 'cond', 'sal', 'abssal', 'press'])

# %%
# save the truncated and filled dataset to data_path

# mkdir if the path does not exist
# Construct the directory path
directory_path = os.path.join(data_path, case_name)

# Check if the directory exists, and create it if it does not
if not os.path.exists(directory_path):
    os.makedirs(directory_path)

# Construct the file path
instrument_SN = ds.attrs.get('instrument_SN', 'unknown')  # Default to 'unknown' if not present
instrument_SN2 = ds2.attrs.get('instrument_SN', 'unknown')  # Default to 'unknown' if not present

file_path = os.path.join(directory_path, f'{case_name}_{instrument_SN}_truncated.nc')
file_path2 = os.path.join(directory_path, f'{case_name}_{instrument_SN2}_truncated.nc')

valid_time_window.to_netcdf(file_path)  # Save the modified dataset
valid_time_window2.to_netcdf(file_path2)  # Save the modified dataset




# %%
# Check spike start and end time
from plot_function import plot_spike_data

deployment_spike_data = ds.sel(time=slice(deployment_spike_times_start - pd.Timedelta(hours=.5), 
                                deployment_spike_times_end + pd.Timedelta(hours=.5)))

recovery_spike_data = ds.sel(time=slice(recovery_spike_times_start - pd.Timedelta(hours=.5), 
                            recovery_spike_times_end + pd.Timedelta(hours=.5)))

img_path = f'/Users/yugao/UOP/ORS-processing/img/{case_name}_spikes.png'

plot_spike_data(deployment_spike_data, recovery_spike_data, case_name, img_path)



# %%
# plot the deployment and recovery phases
deployment_spike_data = ds.sel(time=slice(anchor_over_time - pd.Timedelta(hours=6), 
                                anchor_over_time + pd.Timedelta(hours=4)))

recovery_spike_data = ds.sel(time=slice(release_fired_time - pd.Timedelta(hours=1), 
                            release_fired_time + pd.Timedelta(hours=180)))

recovery_spike_data = ds.isel(time=slice(-100, None))

img_path = f'/Users/yugao/UOP/ORS-processing/img/{case_name}_deployment_recovery.png'

plot_spike_data(deployment_spike_data, recovery_spike_data, case_name, img_path)

# %%
# plot the comparison between two instruments 

import matplotlib.dates as mdates
from datetime import datetime

truncated_ds, truncated_ds2 = valid_time_window, valid_time_window2

variables = ['temp', 'sal', 'abssal', 'cond', 'press']
labels = ['Temperature (°C)', 'Salinity', 'Absolute Salinity', 'Conductivity (S/m)', 'Pressure']
panel_titles = ['Temperature Profile', 'Salinity Measurements', 'Absolute Salinity', 'Conductivity Levels', 'Pressure Profile']

colors = ['blue', 'green', 'red', 'purple', 'black']
colors2 = ['cyan', 'lightgreen', 'pink', 'violet', 'gray']

fig, axs = plt.subplots(len(variables), 1, figsize=(12, 15), sharex=True)

def convert_cftime_to_matplotlib(cftime_times):
    return [datetime(t.year, t.month, t.day, t.hour, t.minute, t.second) for t in cftime_times]

for i, var in enumerate(variables):
    if var in truncated_ds.variables:
        print(f'plotting {var} 1')
        time_data = convert_cftime_to_matplotlib(truncated_ds[var].time.values)
        axs[i].plot(time_data, truncated_ds[var].values, 
                    label=f'{var} (SBE {instrument_SN})', color=colors[i])
    
    if var in truncated_ds2.variables:
        print(f'plotting {var} 2')
        time_data2 = convert_cftime_to_matplotlib(truncated_ds2[var].time.values)
        axs[i].plot(time_data2, truncated_ds2[var].values, 
                    label=f'{var} (SBE {instrument_SN2})', color=colors2[i])
    
    if var in truncated_ds.variables and var in truncated_ds2.variables:
        print(f'plotting {var} correlation')
        correlation = np.corrcoef(truncated_ds[var].values, truncated_ds2[var].values)[0, 1]
        axs[i].legend(title=f'Correlation: {correlation:.2f}')
    else:
        axs[i].legend()
    
    axs[i].set_title(panel_titles[i])
    axs[i].set_ylabel(labels[i])

axs[-1].set_xlabel('Time')

# Format x-axis to show dates
date_form = mdates.DateFormatter("%Y-%m-%d")
axs[-1].xaxis.set_major_formatter(date_form)
plt.gcf().autofmt_xdate()  # Rotate and align the tick labels

latitude = truncated_ds.latitude_anchor_survey if hasattr(truncated_ds, 'latitude_anchor_survey') else 0
longitude = truncated_ds.longitude_anchor_survey if hasattr(truncated_ds, 'longitude_anchor_survey') else 0
formatted_latitude = f"{abs(latitude):.2f}"
formatted_longitude = f"{abs(longitude):.2f}"

fig.suptitle(f'Comparison within {case_name} Data\nAnchor location: ({formatted_latitude}°S, {formatted_longitude}°W)', 
            fontsize=16)
plt.tight_layout(rect=[0, 0.03, 1, 0.95])

plot_path = '../../img/'
os.makedirs(plot_path, exist_ok=True)
plot_filename = os.path.join(plot_path, f"{case_name}_{instrument_SN}_vs_{instrument_SN2}_comparison.png")
plt.savefig(plot_filename)
print(f'Plot saved as {plot_filename}')

# %%
