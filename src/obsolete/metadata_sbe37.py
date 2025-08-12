from datetime import datetime, timedelta
import numpy as np
import scipy.io

# Adjust the function to handle sbe-37 as an array properly

def matlab_datenum_to_datetime(matlab_datenum):
    """Convert MATLAB datenum to Python datetime."""
    return datetime.fromordinal(int(matlab_datenum)) + timedelta(days=matlab_datenum % 1) - timedelta(days=366)


def process_attributes_direct(mat_data):

    attributes = {}

    # Extract latitude, longitude, and depth
    latitude = mat_data.get('latitude', np.nan)
    longitude = mat_data.get('longitude', np.nan)
    depth = mat_data.get('depth', np.nan)

    # Extract and handle 'mday' for time coverage
    mday = mat_data.get('mday', np.array([]))
    if mday.size > 0:
        start_datetime = matlab_datenum_to_datetime(mday[0])
        end_datetime = matlab_datenum_to_datetime(mday[-1])
        attributes.update({
            'time_coverage_start': start_datetime.strftime('%Y-%m-%dT%H:%M:%SZ'),
            'time_coverage_end': end_datetime.strftime('%Y-%m-%dT%H:%M:%SZ'),
            'time_coverage_duration': f'P{(end_datetime - start_datetime).days}D'
        })
    else:
        attributes.update({
            'time_coverage_start': 'unknown',
            'time_coverage_end': 'unknown',
            'time_coverage_duration': 'unknown'
        })

    # Update geospatial and time coverage attributes
    attributes.update({
        'latitude_anchor_survey': latitude,
        'longitude_anchor_survey': longitude,
        'geospatial_lat_min': latitude,
        'geospatial_lat_max': latitude,
        'geospatial_lon_min': longitude,
        'geospatial_lon_max': longitude,
        'geospatial_vertical_min': depth,
        'geospatial_vertical_max': depth,
        'time_coverage_resolution': 'PT1H',  # Assuming hourly resolution
    })

    return attributes


def extract_detailed_metadata(meta):
    detailed_metadata = {}
    if hasattr(meta, 'dtype'):
        for name in meta.dtype.names:
            attr_value = getattr(meta, name)
            if isinstance(attr_value, scipy.io.matlab.mio5_params.mat_struct):  # Check if it's another nested structure
                # Recursively extract nested metadata
                detailed_metadata[name] = extract_detailed_metadata(attr_value)
            elif isinstance(attr_value, np.ndarray) and attr_value.size == 1:
                detailed_metadata[name] = attr_value.item()
            else:
                detailed_metadata[name] = attr_value
    return detailed_metadata


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