from datetime import datetime, timedelta
import numpy as np

def matlab_datenum_to_datetime(matlab_datenum):
    """Convert MATLAB datenum to Python datetime."""
    return datetime.fromordinal(int(matlab_datenum)) + timedelta(days=matlab_datenum % 1) - timedelta(days=366)

def process_attributes_direct(mat_data):
    """Process attributes directly from MATLAB data, handling nested structures and direct attributes."""
    attributes = {}

    # Ensure 'meta' is available and has the expected structure
    meta = mat_data.get('meta', None)
    if meta is None or not isinstance(meta, np.ndarray):
        print("No 'meta' data found or 'meta' is not in the expected format.")
        return attributes

    # Direct keys to extract from 'meta'
    direct_keys = ['site', 'deployment', 'experiment', 'principal_investigator', 'platform', 'global']

    # Process structured array 'meta' to extract direct keys
    try:
        for name in direct_keys:
            if name in meta.dtype.names:
                # Direct attributes from 'meta'
                attr_value = meta[name][()]
                attributes[name] = attr_value if isinstance(attr_value, (int, float, str)) else str(attr_value)
    except Exception as e:
        print(f"Failed to process 'meta' for direct keys: {e}")

    # Handle latitude, longitude, depth, and mday with existing logic
    latitude = mat_data.get('latitude', np.nan)
    longitude = mat_data.get('longitude', np.nan)
    depth = mat_data.get('depth', np.nan)
    mday = mat_data.get('mday', np.array([]))

    if mday.size > 0:
        start_datetime = matlab_datenum_to_datetime(mday[0])
        end_datetime = matlab_datenum_to_datetime(mday[-1])
        attributes['time_coverage_start'] = start_datetime.strftime('%Y-%m-%dT%H:%M:%SZ')
        attributes['time_coverage_end'] = end_datetime.strftime('%Y-%m-%dT%H:%M:%SZ')
        attributes['time_coverage_duration'] = f'P{(end_datetime - start_datetime).days}D'
    else:
        attributes['time_coverage_start'] = 'unknown'
        attributes['time_coverage_end'] = 'unknown'
        attributes['time_coverage_duration'] = 'unknown'
        print("Warning: 'mday' data not in expected format or not found.")

    # Update geospatial and time coverage attributes directly
    attributes.update({
        'latitude_anchor_survey':latitude,
        'longitude_anchor_survey':longitude,
        'geospatial_lat_min': latitude,
        'geospatial_lat_max': latitude,
        'geospatial_lon_min': longitude,
        'geospatial_lon_max': longitude,
        'geospatial_vertical_min': depth,
        'geospatial_vertical_max': depth,
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