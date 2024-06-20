# %%
import numpy as np
import xarray as xr
import matplotlib.pyplot as plt
import os, sys
import json
import scipy.io
import cftime
sys.path.append('/Users/yugao/UOP/ORS-processing/src')
from metadata import create_json, process_attributes_direct
from netcdf_sbe37 import read_mat_file, mat_to_xarray, save_to_netcdf, create_xarray_dataset, extract_metadata

# %%
# required input: case name and water depth 
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


# %%
# file input
mat_file_path = f'/Users/Shared/ORS/Stratus/{case_name}/data/sbe37/{case_name}_sbe37_10601.mat'
# mat_file_path = f'/Users/Shared/ORS/Stratus/{case_name}/data/sbe37/{case_name}_sbe37_10600.mat'
mat_data = read_mat_file(mat_file_path)
# Inspect the structure of mat_data
# print(mat_data.keys()) 
netcdf_path = f'/Users/yugao/UOP/ORS-processing/data/processed/stratus/{case_name}' + mat_file_path[-16:-4] + '.nc'
json_path = '/Users/yugao/UOP/ORS-processing/data/metadata/stratus_OS_NTAS_2016_D_TS.json'

# %% 
# convert the matlab file to netcdf
mat_data = scipy.io.loadmat(mat_file_path, struct_as_record=False, squeeze_me=True)

# Extract and display basic information safely
print(mat_data.keys())
for key in mat_data.keys():
    if not key.startswith('__'):
        data = mat_data[key]
        data_type = type(data)
        data_shape = data.shape if hasattr(data, 'shape') else 'Scalar'
        print(f"{key}: {data_type}, shape: {data_shape}")

# Initialize an empty xarray dataset
ds = xr.Dataset()

# Handling time-series data with 'mday' as the time dimension
if 'mday' in mat_data:
    time_dim = 'time'
    ds[time_dim] = xr.DataArray(data=np.squeeze(mat_data['mday']), dims=[time_dim], attrs={'units': 'days since 0000-01-01 00:00:00', 'calendar': 'gregorian'})

    # Define metadata for variables
    variables = ['abssal', 'cond', 'sal', 'temp', 'press']
    units = {'temp': '°C', 'sal': 'psu', 'abssal': 'g/kg', 'cond': 'S/m', 'press': 'dbar'}
    long_names = {
        'temp': 'sea water temperature',
        'sal': 'practical salinity',
        'abssal': 'absolute salinity',
        'cond': 'sea water conductivity',
        'press': 'sea water pressure'
    }

    # Add other variables if they exist
    for var_name in variables:
        if var_name in mat_data:
            ds[var_name] = xr.DataArray(
                data=np.squeeze(mat_data[var_name]),
                dims=[time_dim],
                attrs={'units': units[var_name], 'long_name': long_names[var_name]}
            )
print(ds)



# %%
# processing meta data
# Investigate the contents of the 'meta' field to see what additional metadata it contains
meta_data = mat_data['meta']

# Import mat_struct from scipy.io.matlab
from scipy.io.matlab import mat_struct

# Initialize an empty dictionary to store the extracted useful information
useful_info = {}

# Iterate over the fields of the MATLAB structure object
for field_name in meta_data._fieldnames:
    # Skip the 'data' field
    if field_name == 'data':
        continue
    # Extract the value of the current field
    field_value = getattr(meta_data, field_name)
    # If the field value is another mat_struct, extract useful information recursively
    if isinstance(field_value, mat_struct):
        nested_info = {}
        # Iterate over the fields of the nested mat_struct
        for nested_field_name in field_value._fieldnames:
            nested_field_value = getattr(field_value, nested_field_name)
            nested_info[nested_field_name] = nested_field_value
        useful_info[field_name] = nested_info
    # If the field value is not a mat_struct, simply store it in the dictionary
    else:
        useful_info[field_name] = field_value

# add depth parameter
depth_parameters = {
    # consult mooring diagram
    'water_depth_from_mooring_diagram': water_depth_from_mooring_diagram,  
     # uncorrected water depth
    'water_depth_from_ship_uncorrected': water_depth_from_ship_uncorrected,
    # Replace with actual value, best water depth
    'water_depth_from_ship_corrected': water_depth_from_ship_corrected,        
    # instrument_depth_from_mooring_diagram = diagram depth  - height above bottom 
    'instrument_depth_from_mooring_diagram': water_depth_from_mooring_diagram - instrument_height_above_bottom,  
    # instrument_depth_from_mooring_log = corrected depth (4538.97 m) - height above bottom (39 m) 
    'instrument_depth_from_mooring_log': water_depth_from_ship_corrected - instrument_height_above_bottom,  
    'instrument_height_above_bottom': 39
}
# Initialize an empty dictionary to store the flattened attributes
attributes_flat = {}

# Function to flatten nested dictionaries
def flatten_dict(d, parent_key='', sep='_'):
    items = []
    for k, v in d.items():
        new_key = parent_key + sep + k if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        elif isinstance(v, np.ndarray):
            # Convert numpy array to list before adding to attributes
            items.append((new_key, v.tolist()))
        elif isinstance(v, scipy.io.matlab._mio5_params.mat_struct):
            # Convert mat_struct object to string representation
            continue
        else:
            items.append((new_key, v))
    return dict(items)


# Flatten the useful_info dictionary further
flattened_info = flatten_dict(useful_info)

# Flatten the 'global' dictionary further
flattened_global = flatten_dict(useful_info['global'], parent_key='global')

# Flatten the 'instrument' dictionary further
flattened_instrument = flatten_dict(useful_info['instrument'], parent_key='instrument')

# Flatten the 'history' dictionary further, excluding 'history_decode'
flattened_history = flatten_dict({k: v for k, v in useful_info['history'].items() if k != 'decode'}, parent_key='history')

# Update the attributes with the flattened dictionaries
attributes_flat.update(flattened_info)
# attributes_flat.update(flattened_platform)
attributes_flat.update(flattened_global)
attributes_flat.update(flattened_instrument)
attributes_flat.update(flattened_history)

# Update the attributes with the depth parameters
for key, value in depth_parameters.items():
    attributes_flat[f'depth_{key}'] = value
    

# %%
# Further process time and location attributes to make the data searchable
from metadata_sbe37 import process_attributes_direct
# Process the MATLAB data using the adjusted function
processed_attributes = process_attributes_direct(mat_data)
ds.attrs.update(processed_attributes)
time_coverage_start_str = ds.attrs['time_coverage_start']

# %%
# Update the attributes of the xarray Dataset with the flattened dictionary
ds.attrs.update(attributes_flat)


# %%
# processing time and truncate the dataset
# Parse the start date strings into cftime objects, assuming Gregorian calendar
# truncate 
time_ds = cftime.num2date(ds['time'][:] - ds['time'][0], units=f"days since {time_coverage_start_str}", calendar='gregorian')
ds['time'] = time_ds

# %%
# truncation: Use anchor over time + 2 hr as start time. 
# Use release fired time as end time.
anchor_over_time = pd.to_datetime('5/13/2017 19:40')
print(anchor_over_time)
# 5/13/2017 19:40 UTC

# If you need to find this time in your dataset
nearest_time = ds.sel(time=anchor_over_time, method='nearest').time
print(f"The nearest time in the dataset to the anchor is: {nearest_time.values}")

# Select data within a window around the anchor time
# time_window = ds.sel(time=slice(anchor_over_time - pd.Timedelta(minutes=10), 
                                # anchor_over_time + pd.Timedelta(minutes=10)))

time_window = ds.sel(time=slice(anchor_over_time , 
                                anchor_over_time + pd.Timedelta(hours=2)))

# Suppose we're plotting temperature
plt.figure(figsize=(10, 5))
time_window['temp'].plot()
plt.title('Temperature Around Anchor Time')
plt.xlabel('Time')
plt.ylabel('Temperature')
plt.grid(True)
plt.show()


# %%
# Check spike start and end time spreadsheet to apparent time in instrument. 
# If offset > about 1 min, linearly interpolate to new time base. 
# Goal is to get both instruments on the same time base.

# Creating a DataFrame for the spike times
spike_times = pd.DataFrame({
    'DATE': ['20170512'],
    'Start Time': ['22:36'],
    'End Time': ['22:42']
})

# Convert date and times to datetime format
spike_times['Start DateTime'] = pd.to_datetime(spike_times['DATE'] + ' ' + spike_times['Start Time'])
spike_times['End DateTime'] = pd.to_datetime(spike_times['DATE'] + ' ' + spike_times['End Time'])

print(spike_times[['Start DateTime', 'End DateTime']])

# Assuming 'ds' is your xarray Dataset with a 'time' coordinate
# Find nearest indices for spike start and end times
spike_start_index = ds.sel(time=spike_times['Start DateTime'][0], method='nearest') #.time
spike_end_index = ds.sel(time=spike_times['End DateTime'][0], method='nearest') #.time

print(f"Spike starts at index: {spike_start_index.values}")
print(f"Spike ends at index: {spike_end_index.values}")


# %%
# Select temperature data around the spike time
# Find nearest indices for spike start and end times
spike_start_time = ds.sel(time=spike_times['Start DateTime'][0], method='nearest').time
spike_end_time = ds.sel(time=spike_times['End DateTime'][0], method='nearest').time

temperature_data = ds['temp'].sel(time=slice(spike_start_time, spike_end_time))

# Plot the temperature data
plt.figure(figsize=(10, 5))
temperature_data.plot()
plt.title('Temperature During Spike Time')
plt.xlabel('Time')
plt.ylabel('Temperature')
plt.grid(True)
plt.show()

# %%
# Find nearest indices for spike start and end times
spike_start_time = ds.sel(time=spike_times['Start DateTime'][0], method='nearest').time
spike_end_time = ds.sel(time=spike_times['End DateTime'][0], method='nearest').time

# ds['temp'].sel(time=slice(spike_start_time, spike_end_time))

# %%
