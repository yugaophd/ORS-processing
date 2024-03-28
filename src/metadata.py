import numpy as np
import json
from datetime import datetime, timedelta

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


def matlab_datenum_to_datetime(matlab_datenum):
    """Convert MATLAB datenum to Python datetime."""
    return datetime.fromordinal(int(matlab_datenum)) + timedelta(days=matlab_datenum % 1) - timedelta(days=366)

def process_attributes_direct(mat_data):
    """Process attributes directly from MATLAB data."""
    
    # Initialize an empty dict for attributes
    attributes = {}
    # meta data from matlab file
    
    meta = mat_data.get('meta', {})  # Fallback to empty dict if 'meta' does not exist
    
    # Extract the 'instrument' array from the provided 'meta' data
    instrument_data = meta['instrument']
    
    if instrument_data is not None:
        # Access the structured array within the numpy object array
        try:
            # Attempt to directly access the structured array
            structured_array = instrument_data.item()
            
            # Iterate through each field in the structured array and add to attributes
            for field in structured_array.dtype.names:
                value = structured_array[field].item()
                attributes[f'instrument_{field}'] = str(value)
        except ValueError:
            # Handle the case where .item() fails due to the structure not being as expected
            print("Unexpected structure within 'instrument_data', cannot extract fields.")


    # Handle other direct values like latitude, longitude, depth, and time
    latitude = mat_data.get('latitude', np.nan)
    longitude = mat_data.get('longitude', np.nan)
    depth = mat_data.get('depth', np.nan)
    mday = mat_data.get('mday', np.array([]))
    
    # Convert mday to datetime, handling empty array scenario
    if mday.size > 0:
        start_datetime = matlab_datenum_to_datetime(mday[0])
        end_datetime = matlab_datenum_to_datetime(mday[-1])
        start_date_iso = start_datetime.strftime('%Y-%m-%dT%H:%M:%SZ')
        end_date_iso = end_datetime.strftime('%Y-%m-%dT%H:%M:%SZ')
        duration_days = (end_datetime - start_datetime).days
    else:
        start_date_iso = end_date_iso = 'unknown'
        duration_days = 'unknown'
        print("Warning: 'instrument' data not in expected format or not found.")

    # Update attributes with processed values
    attributes.update({
        'geospatial_lat_min': latitude,
        'geospatial_lat_max': latitude,
        'geospatial_lon_min': longitude,
        'geospatial_lon_max': longitude,
        'geospatial_vertical_min': depth,
        'geospatial_vertical_max': depth,
        'time_coverage_start': start_date_iso,
        'time_coverage_end': end_date_iso,
        'time_coverage_duration': f'P{duration_days}D',
        'time_coverage_resolution': 'PT1H',  # Assuming hourly resolution
    })

    return attributes




def create_json(mat_data, depth_parameters):
    
    """
    Combines dimensions, variables, attributes, and depth parameters into a final JSON structure.

    Args:
        mat_data: The MATLAB data loaded as a dictionary.
        depth_parameters: A dictionary containing depth-related parameters.

    Returns:
        A dictionary representing the final JSON structure, including depth parameters.
    """
    
    # Process dimensions
    # dimensions = process_dimensions(mat_data)
    
    # Process variables
    # variables = process_variables(mat_data)
    
    # Process attributes (assuming this function already exists and extracts other relevant attributes)
    attributes = process_attributes_direct(mat_data)

    # Combine everything into a final structure
    final_structure = {
        # 'dimensions': dimensions,
        # 'variables': variables,
        'attributes': attributes,
        'depth parameters': depth_parameters
    }

    
    return final_structure


