import xarray as xr
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import cftime
import os
from scipy.io.matlab import mat_struct
import scipy
from datetime import datetime  # Add this import at the top

def convert_cftime_to_pandas_timestamp(ds, start_date):
    """
    Convert cftime.DatetimeGregorian objects to pandas.Timestamp objects,
    using the provided start date as the reference start date.
    
    Parameters:
    ds (xarray.Dataset): Dataset with a 'time' variable containing cftime.DatetimeGregorian objects.
    start_date (str): Start date in ISO format (e.g., '2012-05-14T00:59:59Z').
    
    Returns:
    numpy.ndarray: Array of pandas.Timestamp objects representing the dataset's time points.
    """
    # Convert the start date string to a pandas.Timestamp
    reference_date = pd.to_datetime(start_date)
    
    # Calculate the time offsets in hours from the reference start date
    # Use the first time point in the dataset as the base for offsets
    first_time_point = ds.time.values[0]
    base_offset_hours = cftime.date2num([first_time_point], units="hours since 2000-01-01", calendar='gregorian')[0]
    
    # Calculate offsets for all time points in the dataset relative to the first time point
    time_offsets_hours = cftime.date2num(ds.time.values, units="hours since 2000-01-01", calendar='gregorian') - base_offset_hours
    
    # Apply the offsets to the reference date to get pandas.Timestamp objects
    regular_time_array = np.array([reference_date + pd.Timedelta(hours=offset) for offset in time_offsets_hours])
    
    return regular_time_array

def convert_cftime_to_matplotlib(cftime_dates):
    """
    Convert datetime objects to matplotlib-compatible datetime objects
    
    Parameters:
    -----------
    cftime_dates : array
        Array of datetime objects (cftime, numpy.datetime64, or others)
    
    Returns:
    --------
    list
        List of matplotlib-compatible datetime objects
    """
    result = []
    for t in cftime_dates:
        if hasattr(t, 'year') and hasattr(t, 'month'):
            # It's a cftime object with direct attributes
            result.append(datetime(t.year, t.month, t.day, t.hour, t.minute, t.second))
        elif isinstance(t, np.datetime64):
            # It's a numpy.datetime64 object - convert through pandas
            result.append(pd.Timestamp(t).to_pydatetime())
        else:
            # Try a generic approach for other datetime types
            try:
                result.append(pd.to_datetime(t).to_pydatetime())
            except Exception as e:
                print(f"Warning: Couldn't convert time object of type {type(t)}: {e}")
                # Use a fallback value or None
                result.append(None)
    
    # Filter out None values if any conversion failed
    return [t for t in result if t is not None]
    
import pandas as pd

def truncate_valid_hourly_data(ds):
    """
    Truncate valid hourly oceanographic data based on multiple criteria including temperature, salinity,
    and conductivity data.

    Parameters:
    ds (xarray.Dataset): The input dataset containing temperature, salinity, and conductivity data.

    Returns:
    xarray.Dataset: The truncated dataset.
    """
    # Define criteria thresholds
    temp_range = (0, 30)  # Acceptable temperature range
    sal_range = (33, 35)  # Acceptable salinity range
    cond_range = (3, 4)   # Hypothetical acceptable conductivity range (specific units assumed)
    min_observation_duration = pd.Timedelta(days=180)  # Minimum observation duration

    # Temporal Consistency: Rolling window standard deviation
    temp_std = ds['sea_water_temperature'].rolling(time=12, center=True).std()
    sal_std = ds['sea_water_practical_salinity'].rolling(time=12, center=True).std()
    cond_std = ds['sea_water_electrical_conductivity'].rolling(time=12, center=True).std()

    # Range Constraints
    valid_temp_range = (ds['sea_water_temperature'] >= temp_range[0]) & (ds['sea_water_temperature'] <= temp_range[1])
    valid_sal_range = (ds['sea_water_practical_salinity'] >= sal_range[0]) & (ds['sea_water_practical_salinity'] <= sal_range[1])
    valid_cond_range = (ds['sea_water_electrical_conductivity'] >= cond_range[0]) & (ds['sea_water_electrical_conductivity'] <= cond_range[1])

    # Temporal Duration
    observation_duration = pd.Timedelta(ds['time'].values[-1] - ds['time'].values[0])
    valid_duration = observation_duration >= min_observation_duration

    # Combine criteria
    valid_criteria = valid_temp_range & valid_sal_range & valid_cond_range & \
                    (temp_std < 1) & (sal_std < 0.5) & (cond_std < 0.2) & valid_duration

    # Truncate data based on criteria
    truncated_ds = ds.where(valid_criteria, drop=True)

    return truncated_ds

def extract_sensor_name(file_path):
    
    # Split the file path by '/' to isolate the filename
    
    filename = file_path.split('/')[-1]
    
    # Remove the file extension by splitting on '.' and taking the first part
    filename_without_extension = filename.split('.')[0]
    
    # Now split the cleaned filename by '_' and take the relevant parts to form the sensor name
    parts = filename_without_extension.split('_')
    
    # Assuming the sensor name is always the second and third parts combined
    sensor_name = '_'.join(parts[1:3])
    
    return sensor_name


def read_mat_file(file_path):
    """
    Read a MATLAB file and return the contents as a dictionary.
    """
    return scipy.io.loadmat(file_path, struct_as_record=False, squeeze_me=True)

def create_xarray_dataset(mat_data, fill_value = -99999.0):
    """
    Create an xarray dataset from a MATLAB data dictionary.
    """
    ds = xr.Dataset()

    # Handling time-series data with 'mday' as the time dimension
    if 'mday' in mat_data:
        time_dim = 'time'
        ds[time_dim] = xr.DataArray(data=np.squeeze(mat_data['mday']), dims=[time_dim], 
                                    attrs={'units': 'days since 0000-01-01 00:00:00', 
                                    'calendar': 'gregorian'})

        # Define metadata for variables
        variables = ['temp', 'cond', 'sal', 'abssal', 'press']
        units = {'temp': '°C', 
                'cond': 'psu', 
                'sal': 'g/kg', 
                'abssal': 'S/m', 
                'press': 'dbar'}
        long_names = {
            'temp': 'sea water temperature',
            'cond': 'sea water conductivity',
            'sal': 'sea water practical salinity',
            'abssal': 'sea water absolute salinity',
            'press': 'sea water pressure'
        }

        # Add other variables if they exist
        for var_name in variables:
            if var_name in mat_data:
                print(f"Adding variable: {var_name}")
                print(f"Adding variable: {long_names[var_name]}")
                ds[var_name] = xr.DataArray(
                    data=np.squeeze(mat_data[var_name]),
                    dims=[time_dim],
                    attrs={'units': units[var_name], 
                        'long_name': long_names[var_name],
                        # '_FillValue': fill_value
                        }
                )
                # Assign `_FillValue` in encoding
                ds[var_name].encoding["_FillValue"] = fill_value
                
            if var_name not in mat_data:
                # fill the variables with fill value
                # Create the variable with fill_value if it does not exist
                print(f"Creating variable: {var_name}")
                ds[var_name] = xr.full_like(ds['temp'], 
                                    fill_value, 
                                    dtype=type(fill_value))  # Ensure type consistency
                # ds[var_name].attrs['info'] = f'Variable created with fill value {fill_value} due to non-existence'
                ds[var_name].attrs['long_name'] = long_names[var_name]  
                # ds[var_name].attrs['_FillValue'] = fill_value  
                ds[var_name].attrs['units'] = units[var_name] 
                
                # Assign `_FillValue` in encoding
                ds[var_name].encoding["_FillValue"] = fill_value
    

    return ds

def flatten_dict(d, parent_key='', sep='_'):
    """
    Flatten a nested dictionary.
    """
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

def process_attributes_direct(mat_data):
    """
    Process the attributes from the MATLAB data and return a dictionary.
    """
    # Investigate the contents of the 'meta' field to see what additional metadata it contains
    meta_data = mat_data['meta']

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

    # Flatten the useful_info dictionary further
    flattened_info = flatten_dict(useful_info)

    # Flatten the 'global' dictionary further
    flattened_global = flatten_dict(useful_info['global'], parent_key='global')

    # Flatten the 'instrument' dictionary further
    flattened_instrument = flatten_dict(useful_info['instrument'], parent_key='instrument')

    # Flatten the 'history' dictionary further, excluding 'history_decode'
    flattened_history = flatten_dict({k: v for k, v in useful_info['history'].items() if k != 'decode'}, parent_key='history')

    # Update the attributes with the flattened dictionaries
    processed_attributes = {}
    processed_attributes.update(flattened_info)
    processed_attributes.update(flattened_global)
    processed_attributes.update(flattened_instrument)
    processed_attributes.update(flattened_history)

    return processed_attributes


import xarray as xr

def fill_or_create_variables(ds, variables, fill_value=-99999.0):
    """
    Fill missing data or create non-existent variables in an xarray Dataset.

    Parameters:
    - ds (xr.Dataset): The xarray Dataset to modify.
    - variables (list): A list of variable names to check and fill or create.
    - fill_value (int or float): The value to use for filling or creating variables. Defaults to -999.

    Returns:
    - None: Modifies the dataset in-place.
    """
    for var in variables:
        if var in ds.variables:
            # Forward fill missing values
            ds[var] = ds[var].ffill(dim='time', limit=None)
            # Ensure there is an info attribute and append to it if it exists
            if 'info' in ds[var].attrs:
                ds[var].attrs['info'] += '; Forward filled missing values.'
            else:
                ds[var].attrs['info'] = 'Forward filled missing values.'
        else:
            # Create the variable with fill_value if it does not exist
            ds[var] = xr.full_like(ds['temp'].data, 
                                fill_value, dtype=type(fill_value))  # Ensure type consistency
            ds[var].attrs['info'] = f'Variable created with fill value {fill_value} due to non-existence'
            # ds[var].attrs['long_name'] = ds[var].long_name  # Copy long name from temperature
            # ds[var].attrs['units'] = ds[var].units  # Copy units from temperature
            
        # Assign `_FillValue` in encoding
        # ds[var].encoding["_FillValue"] = fill_value

        # explicitly set missing values in attributes
        # ds[var].attrs["missing_value"] = fill_value  # Older convention
        # ds[var].attrs["_FillValue"] = fill_value  # needed for compatibility


def create_subset_dataset(ds, variables, fill_value=-99999.0):
    """
    Creates a new xarray Dataset containing only specified variables from the original dataset,
    filling missing data or creating non-existent variables with a specified fill value.
    The new dataset retains the structure, attributes, and coordinates of the original dataset.

    Parameters:
    - ds (xr.Dataset): The original xarray Dataset.
    - variables (list): A list of variable names to include in the new dataset.
    - fill_value (int or float): The value to use for filling or creating variables. Defaults to -999.

    Returns:
    - xr.Dataset: A new dataset containing the specified variables, with global attributes and coordinates preserved.
    """
    new_ds = xr.Dataset(attrs=ds.attrs)  # Start with a new dataset, copying global attributes
    for var in variables:
        if var in ds.data_vars:
            # Forward fill missing values and copy over variable attributes and coordinates
            new_var = ds[var].ffill(dim='time', limit=None)
            new_var.attrs['info'] = 'Forward filled missing values.' if 'info' not in new_var.attrs else new_var.attrs['info'] + '; Forward filled missing values.'
            new_ds[var] = new_var
        else:
            # Create the variable with fill_value if it does not exist in the original dataset
            reference_var = next(iter(ds.data_vars))  # Use the first variable to copy dimensions and coordinates
            new_ds[var] = xr.full_like(ds[reference_var], fill_value, dtype=type(fill_value))
            new_ds[var].attrs['info'] = f'Variable created with fill value {fill_value} due to non-existence'

    # Ensure that the new dataset has all necessary coordinates from the original dataset
    for coord in ds.coords:
        if coord not in new_ds.coords:
            new_ds.coords[coord] = ds.coords[coord]

    return new_ds

def verify_spike_time(time_data, temperature_data, recorded_spike_time):
    """
    Verify if the deployment spike time in the given time series data matches the recorded spike time.

    Parameters:
        time_data (np.array): Array of cftime.DatetimeGregorian timestamps.
        temperature_data (np.array): Corresponding temperature readings.
        recorded_spike_time (cftime.DatetimeGregorian): The documented time of the deployment spike.

    Returns:
        None: Prints out the verification result and time difference.
    """
    # Calculate the time differences in minutes
    time_differences = [abs((td - recorded_spike_time).total_seconds()) / 60.0 for td in time_data]

    # Find the minimum time difference
    min_time_difference = np.min(time_differences)

    # # Check if the minimum offset is 5 minutes or less
    # if min_time_difference <= 5:
    #     print(f"The spike time matches the record. Minimum time difference: {min_time_difference:.2f} minutes")
    # else:
    #     print(f"The spike time does not match the record. Minimum time difference: {min_time_difference:.2f} minutes")

    # Print extracted spike data for reference
    print("recorded spike time", recorded_spike_time)
    print("Time Data for Deployment Spike:", time_data)
    print("Temperature Data for Deployment Spike:", temperature_data)
    
import re
def extract_instrument_name(file_path):
    return re.search(r'_sbe37_(\d+)', file_path).group(1)

## append variable attributes in the merged dataset

def append_variable_attributes(ds_source, merged_dataset):
    
    """
    Append variable attributes from the source dataset to the merged dataset.
    Parameters:
    - ds_source (xarray.Dataset): The source dataset containing the new attributes.
    - ds_merge (xarray.Dataset): The merged dataset to which attributes will be appended.
    - merged_dataset (xarray.Dataset): The final merged dataset.
    """        
    
    variables = ['sea_water_temperature', 
                'sea_water_practical_salinity', 
                'sea_water_absolute_salinity', 
                'sea_water_electrical_conductivity', 
                'sea_water_pressure']

    # List of statistical attributes to handle
    stat_attrs = [
        'std_single_sensor',
        'std_sensor_diff',
        'mean_sensor_diff'
    ]

    # List of comment attributes to preserve (not append)
    comment_attrs = [
        'std_single_sensor_comment',
        'std_sensor_diff_comment',
        'mean_sensor_diff_comment'
    ]
    # Store attributes before merging
    stored_attrs = {}
    for var in variables:
        if var in merged_dataset:
            stored_attrs[var] = {
                attr:  merged_dataset[var].attrs[attr] 
                for attr in stat_attrs 
                if attr in  merged_dataset[var].attrs
            }

    # Append/restore attributes
    for var in variables:
        if var in stored_attrs and var in ds_source:
            # Append statistical values
            for attr in stat_attrs:
                if attr in stored_attrs[var] and attr in ds_source[var].attrs:
                    merged_dataset[var].attrs[attr] = f"{stored_attrs[var][attr]}, {ds_source[var].attrs[attr]}"
            # # Preserve comments (take from either dataset)
            # for comment in comment_attrs:
            #     if comment in stored_attrs[var]:
            #         merged_dataset[var].attrs[comment] = stored_attrs[var][comment]
            #     elif comment in ds_merge[var].attrs:
            #         merged_dataset[var].attrs[comment] = ds_source[var].attrs[comment]
        
    return merged_dataset
