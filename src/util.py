import xarray as xr
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import cftime
import os
from scipy.io.matlab import mat_struct
import scipy

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
    temp_std = ds['temp'].rolling(time=12, center=True).std()
    sal_std = ds['sal'].rolling(time=12, center=True).std()
    cond_std = ds['cond'].rolling(time=12, center=True).std()

    # Range Constraints
    valid_temp_range = (ds['temp'] >= temp_range[0]) & (ds['temp'] <= temp_range[1])
    valid_sal_range = (ds['sal'] >= sal_range[0]) & (ds['sal'] <= sal_range[1])
    valid_cond_range = (ds['cond'] >= cond_range[0]) & (ds['cond'] <= cond_range[1])

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

def create_xarray_dataset(mat_data):
    """
    Create an xarray dataset from a MATLAB data dictionary.
    """
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


