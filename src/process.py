# %%
import numpy as np
import xarray as xr
import matplotlib.pyplot as plt
import os, sys
import json
import scipy.io
import cftime
import pandas as pd

# from src.netcdf import mat_to_xarray
sys.path.append('/Users/yugao/UOP/ORS-processing/src')
from metadata import create_json, process_attributes_direct
from netcdf_sbe37 import read_mat_file
from util import create_xarray_dataset, process_attributes_direct  #, truncate_dataset

# %%
# required input: case name, water depth and spike time
case_name = 'stratus16'

# from diagram
water_depth_from_mooring_diagram = 4535

# from mooring log
water_depth_from_ship_uncorrected = 4510     # uncorrected water depth, depth recorder reading
water_depth_from_ship_corrected = 4534       # corrected water depth, best water depth

instrument_height_above_bottom =  39   

#  Anchor (1) + chain (5) + nystron (20) + chain (5) + releases (1) + chain (5) 
# + 6 terminations at 0.25 ea (1.5) 
# + distance from termination on SBE cage to sensor (0.5) = 39 m

# spike time

deployment_spike_times_start = pd.to_datetime('5/12/2017 22:36')
deployment_spike_times_end = pd.to_datetime('5/12/2017 22:42')

# %%
# file input
mat_file_path1 = f'/Users/Shared/ORS/Stratus/{case_name}/data/sbe37/{case_name}_sbe37_10601.mat'
mat_file_path2 = f'/Users/Shared/ORS/Stratus/{case_name}/data/sbe37/{case_name}_sbe37_10600.mat'
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

# %%
# process time
time_coverage_start_str = pd.to_datetime(ds.attrs['platform_data_start_time'])
# Parse the start date strings into cftime objects, assuming Gregorian calendar
time_ds = cftime.num2date(ds['time'][:] - ds['time'][0], 
                          units=f"days since {time_coverage_start_str}", calendar='gregorian')
time_ds2 = cftime.num2date(ds2['time'][:] - ds2['time'][0], 
                          units=f"days since {time_coverage_start_str}", calendar='gregorian')
ds['time'] = time_ds
ds2['time'] = time_ds2
print(time_ds)
print(time_ds2)

# %%
# anchor over time and release time
anchor_over_time =   pd.to_datetime(ds.attrs['platform_anchor_over_time'])
release_fired_time = pd.to_datetime(ds.attrs['platform_anchor_release_time'])
anchor_over_time2 =   pd.to_datetime(ds2.attrs['platform_anchor_over_time'])
release_fired_time2 = pd.to_datetime(ds2.attrs['platform_anchor_release_time'])

# %%
# Truncate the dataset
# Truncate the dataset using the anchor time and 2 hours after
valid_time_window = ds.sel(time=slice(anchor_over_time + pd.Timedelta(hours=2), release_fired_time))
valid_time_window2 = ds2.sel(time=slice(anchor_over_time2 + pd.Timedelta(hours=2), release_fired_time2))

# %% 
# Plot the temperature data around the anchor time
plt.figure(figsize=(10, 5))
valid_time_window['temp'].plot()
valid_time_window2['temp'].plot()
plt.title('Temperature - SBE37')
plt.xlabel('Time')
plt.ylabel('Temperature')
plt.grid(True)
plt.legend(['sbe37_10601', 'sbe37_10601'])
plt.show()
plt.savefig(f'{case_name}_temp_sbe37.png')

# %%
# update the attributes
time_coverage_start_str = str(anchor_over_time + pd.Timedelta(hours=2))
print(f'time_coverage_start:' , time_coverage_start_str)
valid_time_window.attrs['platform_data_start_time'] = time_coverage_start_str


# %%
# Check spike start and end time

spike_data = ds.sel(time=slice(deployment_spike_times_start - pd.Timedelta(days=12), 
                               deployment_spike_times_end + pd.Timedelta(days=12)))

plt.figure(figsize=(10, 5))
spike_data['temp'].plot()
plt.title('Temperature During Spike Time')
plt.xlabel('Time')
plt.ylabel('Temperature')
plt.grid(True)
plt.show()
# %%
