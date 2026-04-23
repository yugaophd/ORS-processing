from datetime import datetime, timedelta
import numpy as np
import scipy.io

def matlab_datenum_to_datetime(datenum):
    """Convert MATLAB datenum to Python datetime."""
    days = datenum % 1
    hours = days % 1 * 24
    minutes = hours % 1 * 60
    seconds = minutes % 1 * 60
    return datetime.fromordinal(int(datenum)) + timedelta(days=int(days), hours=int(hours), minutes=int(minutes), seconds=int(seconds)) - timedelta(days=366)

def process_attributes_direct(mat_data):
    """Process attributes directly from MATLAB data, handling nested structures and direct attributes."""
    attributes = {}

    # Ensure 'meta' is available and has the expected structure
    meta = mat_data.get('meta', None)
    if meta is None or not isinstance(meta, np.ndarray):
        print("No 'meta' data found or 'meta' is not in the expected format.")
        return attributes

    # Function to parse the 'global' attribute
    def parse_global_attribute(global_str):
        global_elements = global_str.strip("()").split(", ")
        attributes['institution'] = global_elements[0].strip("'")
        attributes['project'] = global_elements[1].strip("'")
        # Extend this logic to handle all elements appropriately

    # Function to parse the 'platform' attribute
    def parse_platform_attribute(platform_str):
        platform_elements = platform_str.strip("()").split(", ")
        attributes['platform_type'] = platform_elements[0].strip("'")
        attributes['platform_year'] = platform_elements[1].strip("'")
        # Extend this logic to handle all elements appropriately

    # Direct keys to extract from 'meta'
    direct_keys = ['site', 'deployment', 'experiment', 'principal_investigator']

    # Process structured array 'meta' to extract direct keys
    try:
        for name in direct_keys:
            if name in meta.dtype.names:
                attr_value = meta[name][()]
                attributes[name] = attr_value if isinstance(attr_value, (int, float, str)) else str(attr_value)

        # Handle 'global' and 'platform' with special parsing
        if 'global' in meta.dtype.names:
            parse_global_attribute(str(meta['global'][()]))
        if 'platform' in meta.dtype.names:
            parse_platform_attribute(str(meta['platform'][()]))
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

import datetime
import pandas as pd
from collections import OrderedDict

def get_all_oceansites_standard_attributes():
    """
    Returns a complete list of all valid OceanSITES attributes
    This includes both the standard defaults and other valid attributes
    """
    # Start with our standard defaults
    all_attrs = get_standard_oceansites_attributes()
    
    # Add deployment-specific attributes that are valid
    valid_deployment_attrs = [
        "deployment",
        "platform_code",
        "platform_anchor_over_time",
        "platform_buoy_recovery_time",
        "platform_deployment_cruise_name",
        "platform_recovery_cruise_name",
        "latitude_anchor_survey",
        "longitude_anchor_survey",
        "water_depth_from_ship_uncorrected_m",
        "water_depth_from_ship_corrected_m",
        "water_depth_from_mooring_diagram_m",
        "comments"  # Add comments attribute
    ]
    
    # Add instrument-specific attributes that are valid
    valid_instrument_attrs = [
        "instrument_model",
        "instrument_SN",
        "instrument_manufacturer",
        # "instrument_reference",
        "instrument_mount",
        "instrument_height_above_bottom_m"
    ]
    
    # Add time-coverage attributes that are valid
    valid_time_attrs = [
        "time_coverage_start",
        "time_coverage_end",
        # "time_coverage_duration",
        # "time_coverage_resolution"
    ]
    
    # add geospatial attributes that are valid
    valid_geospatial_attrs = [
        "geospatial_lat_min",
        "geospatial_lat_max",
        "geospatial_lat_units",
        "geospatial_lon_min",
        "geospatial_lon_max",
        "geospatial_lon_units",
        "geospatial_vertical_min",
        "geospatial_vertical_max",
        "geospatial_vertical_positive",
        "geospatial_vertical_units",
    ]
    
    # Add all valid attributes to our dictionary with empty defaults
    for attr in valid_deployment_attrs + valid_instrument_attrs + valid_time_attrs:
        if attr not in all_attrs:
            all_attrs[attr] = ""
    
    return all_attrs

from collections import OrderedDict

def get_standard_oceansites_attributes():
    """
    Returns standard default attributes for OceanSITES compliance
    """
    return OrderedDict([
        ("site_code", "Stratus"),
        ("data_type", "OceanSITES time-series data"),
        ("format_version", "1.4"),
        ("principal_investigator", "Robert Weller"),
        ("experiment", "Stratus Ocean Reference Station"),
        ("platform_type", "moored surface buoy"),
        ("institution", "WHOI"),
        ("data_assembly_center", "WHOI-UOP"),
        ("source", "Mooring observation"),
        ("naming_authority", "OceanSITES"),
        ("cdm_data_type", "Station"),
        ("wmo_platform_code", "38400"),
        ("network", "OceanSITES"),
        ("platform_code", ""),
        ("principal_investigator_email", "rweller@whoi.edu"),
    ])

def ensure_standard_attributes(dataset):
    """
    Ensures all standard OceanSITES attributes exist in the dataset
    """
    # Get the standard attributes in the correct order
    standard_attrs = get_standard_oceansites_attributes()
    
    # Create a new OrderedDict with the standard attributes first
    final_attrs = OrderedDict()
    
    # First add all standard attributes (preserving their values if they exist)
    for key, default_value in standard_attrs.items():
        if key in dataset.attrs:
            final_attrs[key] = dataset.attrs[key]
        else:
            final_attrs[key] = default_value
    
    # Then add any remaining attributes that aren't part of standard_attrs
    for key, value in dataset.attrs.items():
        if key not in final_attrs:
            final_attrs[key] = value
    
    # Replace the dataset attributes with our ordered version
    dataset.attrs = final_attrs
    return dataset

def get_attribute_mapping():
    """
    Returns mapping from legacy attribute names to standardized OceanSITES names
    """
    return OrderedDict([
        ('platform_deploymentcruise', 'platform_deployment_cruise_name'),
        ('platform_recoverycruise', 'platform_recovery_cruise_name'),
        ('platform_deployment_cruise', 'platform_deployment_cruise_name'),
        ('platform_recovery_cruise', 'platform_recovery_cruise_name'),
        ('Institution', 'institution'),
        ('global_institution', 'institution'),
        ('global_data_assembly_center', 'data_assembly_center'),
        ('global_source', 'source'),
        ('global_naming_authority', 'naming_authority'),
        ('global_cdm_data_type', 'cdm_data_type'),
        ('global_wmo_platform_code', 'wmo_platform_code'),
        ('instrument_reference_url', 'instrument_reference'),
        ('instrument_type', 'instrument_model'),
        ('platform_anchor_release_time', 'platform_buoy_recovery_time') # platform_anchor_release_time
        
    ])

def iso8601_format(date_str):
    """
    Convert various date formats to ISO8601 format with UTC timezone
    
    Parameters:
    -----------
    date_str : str, int, float, datetime, pandas.Timestamp
        Date/time to convert
    
    Returns:
    --------
    str
        Date in ISO8601 format with Z timezone (e.g., '2012-05-28T02:03:04Z')
    """
    # Skip if already in ISO format with Z
    if isinstance(date_str, str) and 'T' in date_str and date_str.endswith('Z'):
        return date_str
    
    # Skip non-date strings like cruise names
    if isinstance(date_str, str) and any(x in date_str for x in ['RB', 'MV', 'cruise']):
        return date_str
        
    # Handle different input types
    try:
        # For numeric inputs (like year)
        if isinstance(date_str, (int, float)):
            # If it's just a year
            if date_str < 10000:  # Assume it's a year if < 10000
                return f"{int(date_str)}-01-01T00:00:00Z"
            
            # Handle MATLAB datenum format (days since 0000-01-00)
            # Convert to days since 1970-01-01 for datetime
            try:
                # Matlab date numbers: days since 0000-00-00
                # Need to adjust by 719529 days to get days since 1970-01-01
                days_since_epoch = float(date_str) - 719529
                dt = datetime.datetime(1970, 1, 1) + datetime.timedelta(days=days_since_epoch)
                return dt.strftime('%Y-%m-%dT%H:%M:%SZ')
            except:
                # If conversion fails, continue to other methods
                pass
                
        # For pandas Timestamp or datetime objects
        if isinstance(date_str, (pd.Timestamp, datetime.datetime)):
            return date_str.strftime('%Y-%m-%dT%H:%M:%SZ')
        
        # Handle list/array of dates (like platform_anchor_times)
        if isinstance(date_str, (list, tuple)) or (isinstance(date_str, str) and date_str.startswith('[')):
            # If it's a string representation of a list, try to evaluate it
            if isinstance(date_str, str):
                try:
                    import ast
                    date_list = ast.literal_eval(date_str)
                except:
                    # If we can't parse it as a list, treat it as a regular string
                    date_list = [date_str]
            else:
                date_list = date_str
                
            # Convert each item in the list
            iso_dates = []
            for date_item in date_list:
                try:
                    iso_date = iso8601_format(date_item)  # Recursive call
                    iso_dates.append(iso_date)
                except:
                    iso_dates.append(str(date_item))  # Keep original if conversion fails
                    
            return str(iso_dates)  # Return as string representation of list
        
        # For string dates, try multiple formats
        if isinstance(date_str, str):
            # Strip any timezone info for consistent processing
            if '+' in date_str:
                date_str = date_str.split('+')[0]
            
            # Try parsing with various formats
            formats_to_try = [
                '%Y-%m-%d %H:%M:%S',    # '2012-05-28 02:03:04'
                '%d-%b-%Y %H:%M:%S',    # '27-May-2012 22:03:04'
                '%m/%d/%Y %H:%M',       # '04/26/2015 17:00'
                '%m/%d/%Y %H:%M:%S',    # '04/26/2015 17:00:00'
                '%Y-%m-%d',             # '2012-05-28'
                '%Y%m%d',               # '20120528'
                '%Y'                    # '2012'
            ]
            
            for fmt in formats_to_try:
                try:
                    dt = datetime.datetime.strptime(date_str, fmt)
                    return dt.strftime('%Y-%m-%dT%H:%M:%SZ')
                except ValueError:
                    continue
        
        # If none of the specific formats match, try pandas flexible parser
        dt = pd.to_datetime(date_str)
        return dt.strftime('%Y-%m-%dT%H:%M:%SZ')
        
    except Exception as e:
        print(f"Warning: Could not convert '{date_str}' to ISO8601 format: {e}")
        return date_str  # Return original if conversion fails

def standardize_attribute_names(ds):
    """
    Convert legacy attribute names to standardized OceanSITES names
    
    Parameters:
    -----------
    ds : xarray.Dataset
        Dataset with attributes to standardize
    
    Returns:
    --------
    xarray.Dataset
        Dataset with standardized attribute names
    """
    mapping = get_attribute_mapping()
    
    # Create a new attributes dictionary
    new_attrs = {}
    
    # Process each existing attribute
    for old_name, value in ds.attrs.items():
        # If the attribute name is in our mapping, use the new name
        if old_name in mapping:
            new_name = mapping[old_name]
            new_attrs[new_name] = value
        else:
            # Otherwise keep the old name
            new_attrs[old_name] = value
    
    # Replace the dataset's attributes with our new ones
    ds.attrs = new_attrs
    
    return ds

def ensure_standard_attributes(ds, remove_nonstandard=True):
    """
    Ensure all standard OceanSITES attributes exist in the dataset
    Optionally remove any attributes that aren't on the standard list
    
    Parameters:
    -----------
    ds : xarray.Dataset
        Dataset to modify
    remove_nonstandard : bool, optional
        If True, remove any attributes that aren't on the standard list
    
    Returns:
    --------
    xarray.Dataset
        Dataset with standardized attributes
    """
    # Get the standard attributes
    standard_attrs = get_all_oceansites_standard_attributes()
    
    # Create a copy of the dataset's attributes to modify
    attrs = dict(ds.attrs)
    
    # If we're removing non-standard attributes, create a new dict with only standard ones
    if remove_nonstandard:
        new_attrs = {}
        for name, value in attrs.items():
            if name in standard_attrs:
                new_attrs[name] = value
        attrs = new_attrs
    
    # Set default values for any missing standard attributes
    for name, default_value in standard_attrs.items():
        if name not in attrs:
            attrs[name] = default_value
    
    # Set platform_code based on site and deployment if not already set
    if not attrs.get('platform_code') and 'site_code' in attrs and 'deployment' in attrs:
        attrs['platform_code'] = f"{attrs['site_code']}-{attrs['deployment']}"
    
    # Special handling for platform_anchor_times to ensure it doesn't get format validation
    if 'platform_anchor_times' in attrs:
        # If it's a list of dates in ISO format, leave it as is
        if isinstance(attrs['platform_anchor_times'], str) and attrs['platform_anchor_times'].startswith('[') and 'T' in attrs['platform_anchor_times'] and 'Z' in attrs['platform_anchor_times']:
            pass
        # Otherwise, mark it for special handling
        else:
            # Just store it as a string - don't try to parse as dates
            if not isinstance(attrs['platform_anchor_times'], str):
                attrs['platform_anchor_times'] = str(attrs['platform_anchor_times'])
    
    # Special handling for cruise names
    cruise_name_attrs = ['platform_deployment_cruise_name', 'platform_recovery_cruise_name']
    for attr in cruise_name_attrs:
        if attr in attrs:
            # Make sure cruise names aren't processed as dates
            pass  # Just keep them as they are
    
    # Format date/time attributes to ISO8601 format
    date_time_keywords = ['time', 'date', '_start', '_end', '_over', '_recovery', '_fired', '_adrift']
    for name in list(attrs.keys()):  # Use list() to allow modifying during iteration
        if any(keyword in name.lower() for keyword in date_time_keywords) and attrs[name] and name not in cruise_name_attrs:
            # Convert to ISO8601
            attrs[name] = iso8601_format(attrs[name])
    
    # Ensure numeric attributes are stored as strings
    for name in attrs:
        if isinstance(attrs[name], (int, float)):
            attrs[name] = str(attrs[name])
    
    # Update the dataset with the modified attributes
    ds.attrs = attrs
    
    return ds

def validate_attributes(ds):
    """
    Validate that required OceanSITES attributes are present and correct
    
    Parameters:
    -----------
    ds : xarray.Dataset
        Dataset to validate
    
    Returns:
    --------
    tuple
        (is_valid, list_of_issues)
    """
    # List of required attributes 
    required_attrs = [
        "site_code", "platform_code", "data_type", "format_version",
        "principal_investigator", "institution", 
        "time_coverage_start", "time_coverage_end"
    ]
    
    # Check for missing required attributes
    missing_attrs = [attr for attr in required_attrs if attr not in ds.attrs]
    
    # Check for empty required attributes
    empty_attrs = [attr for attr in required_attrs 
                  if attr in ds.attrs and not ds.attrs[attr]]
    
    # Combine issues
    issues = []
    if missing_attrs:
        issues.append(f"Missing required attributes: {', '.join(missing_attrs)}")
    if empty_attrs:
        issues.append(f"Empty required attributes: {', '.join(empty_attrs)}")
    
    # Validate date formats
    date_time_keywords = ['time', 'date', '_start', '_end', '_over', '_recovery', '_fired', '_adrift']
    
    # List of attributes to skip date validation for
    non_date_attrs = [
        'platform_deployment_cruise_name', 
        'platform_recovery_cruise_name',
        'platform_anchor_times'  # Skip validation for this array of dates
    ]
    
    date_attrs = [attr for attr in ds.attrs 
                 if any(keyword in attr.lower() for keyword in date_time_keywords) 
                 and attr not in non_date_attrs]
    
    invalid_dates = []
    for attr in date_attrs:
        if attr in ds.attrs and ds.attrs[attr]:  # Only check non-empty attributes
            try:
                # Check if date is already in ISO8601 format with Z
                if not (isinstance(ds.attrs[attr], str) and 
                        'T' in ds.attrs[attr] and 
                        ds.attrs[attr].endswith('Z')):
                    invalid_dates.append(f"{attr} (value: {ds.attrs[attr]})")
            except:
                invalid_dates.append(f"{attr} (value: {ds.attrs[attr]})")
            
    if invalid_dates:
        issues.append(f"Non-ISO8601 date formats: {', '.join(invalid_dates)}")
    
    # Return validation result
    is_valid = len(issues) == 0
    return is_valid, issues

def reorder_oceansites_attributes(dataset):
    """
    Reorder attributes according to OceanSITES conventions.
    Returns a new dataset with attributes in the specified order.
    """
    from collections import OrderedDict
    
    # Define the desired order for all possible OceanSITES attributes
    oceansites_attr_order = [
        "site_code",
        "deployment",        
        "data_type",
        "format_version",
        "principal_investigator",
        "principal_investigator_email",
        "experiment",
        "platform_type",
        "platform_code",
        "institution",
        "data_assembly_center",
        "source",
        "naming_authority",
        "cdm_data_type",
        "wmo_platform_code",
        "network",
        "platform_anchor_over_time",
        "platform_buoy_recovery_time",
        "platform_deployment_cruise_name",
        "platform_recovery_cruise_name",
        "latitude_anchor_survey",
        "longitude_anchor_survey",
        "version",
        "comments",  # Add comments attribute in appropriate position
        "water_depth_from_ship_uncorrected_m",
        "water_depth_from_ship_corrected_m",
        "water_depth_from_mooring_diagram_m",
        "instrument_model",
        "instrument_SN",
        "instrument_manufacturer",
        "instrument_reference",
        "instrument_mount",
        "instrument_height_above_bottom_m",
        "instrument_depth",
        "instrument_depth_comment",
        "time_coverage_start",
        "time_coverage_end",
        "geospatial_lat_min",
        "geospatial_lat_max",
        "geospatial_lat_units",
        "geospatial_lon_min",
        "geospatial_lon_max",
        "geospatial_lon_units",
        "geospatial_vertical_min",
        "geospatial_vertical_max",
        "geospatial_vertical_positive",
        "geospatial_vertical_units",
    ]
    
    # Create a strictly ordered dict with only the attributes in our order
    strict_ordered_attrs = OrderedDict()
    
    # Add only attributes that exist, in our exact order
    for attr in oceansites_attr_order:
        if attr in dataset.attrs:
            strict_ordered_attrs[attr] = dataset.attrs[attr]
    
    # Create a new dataset with strictly ordered attributes
    new_dataset = dataset.copy(deep=True)   
    new_dataset.attrs = strict_ordered_attrs
    
    return new_dataset

def add_geospatial_attributes(dataset):
    """
    Add geospatial attributes using min and max of existing depth attributes.
    """
    # Extract min/max latitude if it exists in dataset
    if 'latitude_anchor_survey' in dataset.attrs:
        lat_value = float(dataset.attrs['latitude_anchor_survey'])
        dataset.attrs['geospatial_lat_min'] = str(lat_value)
        dataset.attrs['geospatial_lat_max'] = str(lat_value)
        dataset.attrs['geospatial_lat_units'] = "degree_north"
    
    # Extract min/max longitude if it exists in dataset
    if 'longitude_anchor_survey' in dataset.attrs:
        lon_value = float(dataset.attrs['longitude_anchor_survey'])
        dataset.attrs['geospatial_lon_min'] = str(lon_value)
        dataset.attrs['geospatial_lon_max'] = str(lon_value)
        dataset.attrs['geospatial_lon_units'] = "degree_east"
    
    # Collect depths from all relevant attributes
    depth_values = []
    depth_attributes = [
        'water_depth_from_ship_uncorrected_m',
        'water_depth_from_ship_corrected_m',
        'water_depth_from_mooring_diagram_m'
    ]
    
    for attr in depth_attributes:
        if attr in dataset.attrs:
            try:
                depth_values.append(float(dataset.attrs[attr]))
            except (ValueError, TypeError):
                pass
    
    # If we have valid depth values, set the min and max
    if depth_values:
        min_depth = min(depth_values)
        max_depth = max(depth_values)
        
        dataset.attrs['geospatial_vertical_min'] = str(min_depth)
        dataset.attrs['geospatial_vertical_max'] = str(max_depth)
        dataset.attrs['geospatial_vertical_units'] = "m"
        dataset.attrs['geospatial_vertical_positive'] = "down"
    
    return dataset