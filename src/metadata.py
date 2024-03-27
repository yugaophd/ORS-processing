import numpy as np
import json

def extract_basic_info(mat_data):
    """
    Extract basic information like latitude, longitude, etc.
    """
    basic_info = {
        'latitude': mat_data.get('latitude', None),
        'longitude': mat_data.get('longitude', None),
        'depth': mat_data.get('depth', None)
    }
    return basic_info

def process_dimensions(mat_data):
    """
    Calculate dimensions for the dataset.
    """
    dimensions = {
        'TIME': len(mat_data['mday']),  # Assuming mday represents time and is a 1D array
        'DEPTH': 1,  # Assuming a single depth for simplicity; adjust if your data varies
        'LATITUDE': 1,  # Fixed value for the dataset
        'LONGITUDE': 1  # Fixed value for the dataset
    }
    return dimensions

def process_variables(mat_data):
    '''prcess variable metadata'''
    variables_metadata = {
        'TEMP': {
            'dims': ('TIME', 'DEPTH'),
            'data_type': 'float64',
            'attrs': {
                'long_name': 'Sea water temperature',
                'units': 'degree_Celsius',
                'reference_scale': 'ITS-90',
                'valid_min': min(mat_data['temp']),
                'valid_max': max(mat_data['temp']),
                'QC_indicator': 1.0,
                'QC_procedure': 6.0,
                'instrument': 'SBE-16',
                'comment': 'In-situ measurement, quality controlled'
            }
        },
        'CNDC': {
            'dims': ('TIME', 'DEPTH'),
            'data_type': 'float64',
            'attrs': {
                'long_name': 'Sea water electrical conductivity',
                'units': 'S m-1',
                'valid_min': min(mat_data['cond']),
                'valid_max': max(mat_data['cond']),
                'QC_indicator': 1.0,
                'instrument': 'SBE-16',
                'comment': 'In-situ measurement, quality controlled'
            }
        },
        'PSAL': {
            'dims': ('TIME', 'DEPTH'),
            'data_type': 'float64',
            'attrs': {
                'long_name': 'Sea water practical salinity',
                'units': '1',
                'valid_min': min(mat_data['sal']),
                'valid_max': max(mat_data['sal']),
                'QC_indicator': 1.0,
                'instrument': 'SBE-16',
                'comment': 'Computed from conductivity, quality controlled'
            }
        },
        'sal_sbe': {
            'dims': ('TIME', 'DEPTH'),
            'data_type': 'float64',
            'attrs': {
                'long_name': 'Sea water salinity measured by SBE',
                'units': '1',
                'valid_min': min(mat_data['sal_sbe']),
                'valid_max': max(mat_data['sal_sbe']),
                'QC_indicator': 1.0,
                'instrument': 'SBE-16',
                'comment': 'Direct measurement by SBE, quality controlled'
            }
        }
    }

    # Adjust the above metadata as necessary for accuracy and completeness

    return variables_metadata

from datetime import datetime, timedelta

def process_attributes_direct(mat_data):
# Convert MATLAB datenum to Python datetime
    def matlab_datenum_to_datetime(matlab_datenum):
        python_datetime = datetime.fromordinal(int(matlab_datenum)) + timedelta(days=matlab_datenum%1) - timedelta(days=366)
        return python_datetime

    # Direct extraction of latitude, longitude, and time (mday) values
    latitude = mat_data['latitude']
    longitude = mat_data['longitude']
    mday = mat_data['mday']

    # Convert the first and last MATLAB datenum to Python datetime
    start_datetime = matlab_datenum_to_datetime(mday[0])
    end_datetime = matlab_datenum_to_datetime(mday[-1])

    # Format start and end datetime to ISO format
    start_date_iso = start_datetime.strftime('%Y-%m-%dT%H:%M:%SZ')
    end_date_iso = end_datetime.strftime('%Y-%m-%dT%H:%M:%SZ')

    # Calculate duration in days (approximation)
    duration_days = (end_datetime - start_datetime).days
    duration_iso = f'P{duration_days}D'

    # Prepare the attributes dictionary
    attributes = {
        'geospatial_lat_min': latitude,
        'geospatial_lat_max': latitude,
        'geospatial_lon_min': longitude,
        'geospatial_lon_max': longitude,
        'geospatial_lat_units': 'degrees_north',
        'geospatial_lon_units': 'degrees_east',
        'geospatial_vertical_min': 0.78,  # Assuming this is constant; adjust as necessary
        'geospatial_vertical_max': 70.0,  # Assuming this is constant; adjust as necessary
        'geospatial_vertical_units': 'meters',
        'geospatial_vertical_positive': 'down',
        'time_coverage_start': start_date_iso,
        'time_coverage_end': end_date_iso,
        'time_coverage_duration': duration_iso,
        'time_coverage_resolution': 'PT1H',  # Assuming hourly resolution; adjust as necessary
    }

    return attributes

def create_json(mat_data):
    """
    Combines dimensions, variables, and attributes into a final JSON structure.

    Args:
        mat_data: The MATLAB data loaded as a dictionary.

    Returns:
        A dictionary representing the final JSON structure.
    """
    # Process dimensions
    dimensions = process_dimensions(mat_data)
    
    # Process variables
    variables = process_variables(mat_data)
    
    # Process attributes
    attributes = process_attributes_direct(mat_data)

    # Combine everything into a final structure
    final_structure = {
        'dimensions': dimensions,
        'variables': variables,
        'attributes': attributes
    }
    
    return final_structure

