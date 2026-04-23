"""
OceanSITES Metadata Merger

This module defines which standardized OceanSITES metadata attributes to append
from source datasets, and which attributes to delete during merging operations.
Focused specifically on the Stratus Ocean Reference Station datasets.
"""

# Standard OceanSITES attributes to append from source datasets
attrs_to_append = [
    # Core identification attributes
    # 'site_code',
    'deployment',
    'platform_code',
    
    # Deployment information
    # 'platform_type',
    'platform_anchor_over_time',
    'platform_buoy_recovery_time',
    'platform_deployment_cruise_name',
    'platform_recovery_cruise_name',
    
    # Location attributes
    'latitude_anchor_survey',
    'longitude_anchor_survey',
    'water_depth_from_ship_uncorrected_m',
    'water_depth_from_ship_corrected_m',
    'water_depth_from_mooring_diagram_m',
    'instrument_depth',
    
    # Instrument attributes
    'instrument_model',
    'instrument_SN',
    # 'instrument_manufacturer',
    # 'instrument_mount',
    # 'instrument_height_above_bottom_m',
    
    # Time coverage attributes
    'time_coverage_start',
    'time_coverage_end',
    
    # Geospatial attributes
    'geospatial_lat_min',
    'geospatial_lat_max',
    'geospatial_lat_units',
    'geospatial_lon_min',
    'geospatial_lon_max',
    'geospatial_lon_units',
    'geospatial_vertical_min',
    'geospatial_vertical_max',
    # 'geospatial_vertical_positive',
    # 'geospatial_vertical_units',
    
    # Identification attributes
    # 'wmo_platform_code'
    # 'merge_point',
    # 'merge_point_comment',
]

# Attributes to delete from datasets
attrs_to_delete = [
    'platform_deployment_number',
    'platform_anchor_release_time',
    'platform_data_start',
    'platform_adrift_time',
    'platform_data_end_time',
    'platform_duration',
    'platform_days_on_station',
    'platform_deploymentcruise',
    'platform_recoverycruise',
    'global_wmo_platform_code',
    # 'platform_buoy_recovery_time',
    # 'platform_anchor_over_time'
]

# Alternative attribute names and their standard versions
attr_alternatives = {
    'platform_deployment_cruise': 'platform_deploymentcruise',
    'platform_recovery_cruise': 'platform_recoverycruise',
    'instrument_reference': 'instrument_reference_url',
    'platform_duration_days': 'platform_duration',
    'instrument_model': 'instrument_type',
    'platform_water_depth_m': 'platform_water_depth',
}


"""
Update Geospatial Bounds for Merged Datasets

This module provides functions to correctly calculate and update geospatial bounds
for merged oceanographic datasets, ensuring they accurately reflect the true
spatial extent of all combined data.
"""

def extract_float_value(value_str):
    """
    Extract float values from attribute strings, handling comma-separated values.
    
    Parameters:
    -----------
    value_str : str
        String containing one or more numeric values
        
    Returns:
    --------
    list
        List of float values extracted from the string
    """
    if not value_str:
        return []
        
    # Remove any whitespace and split by commas
    values = [v.strip() for v in str(value_str).split(',')]
    
    # Convert to float, filtering out non-numeric values
    float_values = []
    for v in values:
        try:
            float_values.append(float(v))
        except ValueError:
            pass
            
    return float_values

def update_geospatial_bounds(merged_dataset):
    """
    Update geospatial bounds attributes in a merged dataset to accurately 
    reflect the bounds of all constituent datasets.
    
    Parameters:
    -----------
    merged_dataset : xarray.Dataset
        The merged dataset with potentially concatenated geospatial bounds
        
    Returns:
    --------
    xarray.Dataset
        Dataset with correctly calculated geospatial bounds
    """
    # Extract values from lat attributes
    lat_min_values = extract_float_value(merged_dataset.attrs.get('geospatial_lat_min', ''))
    lat_max_values = extract_float_value(merged_dataset.attrs.get('geospatial_lat_max', ''))
    
    # Extract values from lon attributes
    lon_min_values = extract_float_value(merged_dataset.attrs.get('geospatial_lon_min', ''))
    lon_max_values = extract_float_value(merged_dataset.attrs.get('geospatial_lon_max', ''))
    
    # Extract values from vertical bounds
    vert_min_values = extract_float_value(merged_dataset.attrs.get('geospatial_vertical_min', ''))
    vert_max_values = extract_float_value(merged_dataset.attrs.get('geospatial_vertical_max', ''))
    
    # Update latitude bounds if values exist
    if lat_min_values:
        merged_dataset.attrs['geospatial_lat_min'] = str(min(lat_min_values))
    if lat_max_values:
        merged_dataset.attrs['geospatial_lat_max'] = str(max(lat_max_values))
        
    # Update longitude bounds if values exist
    if lon_min_values:
        merged_dataset.attrs['geospatial_lon_min'] = str(min(lon_min_values))
    if lon_max_values:
        merged_dataset.attrs['geospatial_lon_max'] = str(max(lon_max_values))
        
    # Update vertical bounds if values exist
    if vert_min_values:
        merged_dataset.attrs['geospatial_vertical_min'] = str(min(vert_min_values))
    if vert_max_values:
        merged_dataset.attrs['geospatial_vertical_max'] = str(max(vert_max_values))
    
    # Ensure units are consistent
    if 'geospatial_lat_units' in merged_dataset.attrs:
        merged_dataset.attrs['geospatial_lat_units'] = 'degree_north'
    if 'geospatial_lon_units' in merged_dataset.attrs:
        merged_dataset.attrs['geospatial_lon_units'] = 'degree_east'
    if 'geospatial_vertical_units' in merged_dataset.attrs:
        merged_dataset.attrs['geospatial_vertical_units'] = 'm'
    if 'geospatial_vertical_positive' in merged_dataset.attrs:
        merged_dataset.attrs['geospatial_vertical_positive'] = 'down'
        
    return merged_dataset


def calculate_bounds_from_datasets(datasets):
    """
    Calculate correct geospatial bounds from a list of datasets.
    
    Parameters:
    -----------
    datasets : list
        List of xarray.Dataset objects
        
    Returns:
    --------
    dict
        Dictionary containing the correct geospatial bounds
    """
    # Initialize with empty lists
    lat_mins = []
    lat_maxs = []
    lon_mins = []
    lon_maxs = []
    vert_mins = []
    vert_maxs = []
    
    # Extract values from each dataset
    for ds in datasets:
        lat_mins.extend(extract_float_value(ds.attrs.get('geospatial_lat_min', '')))
        lat_maxs.extend(extract_float_value(ds.attrs.get('geospatial_lat_max', '')))
        lon_mins.extend(extract_float_value(ds.attrs.get('geospatial_lon_min', '')))
        lon_maxs.extend(extract_float_value(ds.attrs.get('geospatial_lon_max', '')))
        vert_mins.extend(extract_float_value(ds.attrs.get('geospatial_vertical_min', '')))
        vert_maxs.extend(extract_float_value(ds.attrs.get('geospatial_vertical_max', '')))
        
        # Also extract from latitude_anchor_survey and longitude_anchor_survey
        lat_anchor = extract_float_value(ds.attrs.get('latitude_anchor_survey', ''))
        lon_anchor = extract_float_value(ds.attrs.get('longitude_anchor_survey', ''))
        
        lat_mins.extend(lat_anchor)
        lat_maxs.extend(lat_anchor)
        lon_mins.extend(lon_anchor)
        lon_maxs.extend(lon_anchor)
    
    # Calculate bounds, handling empty lists
    bounds = {}
    if lat_mins:
        bounds['geospatial_lat_min'] = str(min(lat_mins))
    if lat_maxs:
        bounds['geospatial_lat_max'] = str(max(lat_maxs))
    if lon_mins:
        bounds['geospatial_lon_min'] = str(min(lon_mins))
    if lon_maxs:
        bounds['geospatial_lon_max'] = str(max(lon_maxs))
    if vert_mins:
        bounds['geospatial_vertical_min'] = str(min(vert_mins))
    if vert_maxs:
        bounds['geospatial_vertical_max'] = str(max(vert_maxs))
        
    # Set consistent units
    bounds['geospatial_lat_units'] = 'degree_north'
    bounds['geospatial_lon_units'] = 'degree_east'
    bounds['geospatial_vertical_units'] = 'm'
    bounds['geospatial_vertical_positive'] = 'down'
    
    return bounds