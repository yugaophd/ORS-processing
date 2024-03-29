import xarray as xr
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import cftime

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

def truncate_valid_hourly_data(ds):
    
    """
    Truncate valid hourly oceanographic data based on multiple criteria.

    Parameters:
    ds (xarray.Dataset): The input dataset containing temperature and salinity data.

    Returns:
    xarray.Dataset: The truncated dataset.
    """
    # Define criteria thresholds
    temp_range = (0, 30)  # Acceptable temperature range
    sal_range = (30, 40)  # Acceptable salinity range
    min_observation_duration = pd.Timedelta(days=365)  # Minimum observation duration

    # Temporal Consistency: Rolling window standard deviation
    temp_std = ds['temp'].rolling(time=24).std()
    sal_std = ds['sal'].rolling(time=24).std()

    # Range Constraints
    valid_temp_range = (ds['temp'] >= temp_range[0]) & (ds['temp'] <= temp_range[1])
    valid_sal_range = (ds['sal'] >= sal_range[0]) & (ds['sal'] <= sal_range[1])

    # Temporal Duration
    observation_duration = ds['time'][-1] - ds['time'][0]
    valid_duration = observation_duration >= min_observation_duration

    # Combine criteria
    valid_criteria = valid_temp_range & valid_sal_range & (temp_std < 5) & (sal_std < 2) & valid_duration

    # Truncate data based on criteria
    truncated_ds = ds.where(valid_criteria, drop=True)

    return truncated_ds
