# %%
# Script to create a CF-compliant NetCDF file from the merged Stratus dataset
# Adds longitude, latitude, depth as coordinates for all variables
import os
import xarray as xr
import numpy as np
import pandas as pd
from datetime import datetime
import matplotlib.pyplot as plt

# Define input and output paths
input_file = '/Users/yugao/UOP/ORS-processing/data/processed/merged_stratus/merged_stratus12_to_stratus22.nc'
output_dir = '/Users/yugao/UOP/ORS-processing/data/processed/merged_stratus'
output_file = os.path.join(output_dir, 'stratus_2012_to_2023.nc')
temp_file = os.path.join(output_dir, 'stratus_temperature_2012_to_2023_v1.nc')
# Ensure output directory exists
os.makedirs(output_dir, exist_ok=True)

print(f"Loading merged dataset from: {input_file}")

try:
    # Load the original dataset
    ds = xr.open_dataset(input_file)
    
    # Extract location information
    lat_str = ds.attrs.get('latitude_anchor_survey', '')
    lon_str = ds.attrs.get('longitude_anchor_survey', '')
    depth_str = ds.attrs.get('instrument_depth', '')
    
    if not lat_str or not lon_str:
        print("Warning: Missing coordinate attributes for lat/lon")
        # Use default Stratus location if missing
        lat_str = '-20.0'  
        lon_str = '-85.5'
    
    # Parse coordinate strings
    latitudes = [float(lat.strip()) for lat in lat_str.split(',') if lat.strip()]
    longitudes = [float(lon.strip()) for lon in lon_str.split(',') if lon.strip()]
    depths = [float(d.strip()) for d in depth_str.split(',') if d.strip()]
    
    print(f"Found {len(latitudes)} latitude values, {len(longitudes)} longitude values, {len(depths)} depth values")
    
    # Get merge points for segmentation
    merge_points_str = ds.attrs.get('merge_point', '')
    merge_points = []
    
    if merge_points_str:
        # Define to_naive_datetime inline since we're not importing it
        def to_naive_datetime(time_str):
            try:
                dt = pd.to_datetime(time_str)
                return dt.replace(tzinfo=None).to_pydatetime()
            except:
                return None
        
        for point in merge_points_str.split(','):
            point = point.strip()
            if point and point.lower() != 'none' and point.lower() != 'nat':
                try:
                    dt_point = to_naive_datetime(point)
                    if dt_point is not None:
                        merge_points.append(dt_point)
                except Exception as e:
                    print(f"Could not parse merge point: {point} - {e}")
    
    print(f"Found {len(merge_points)} merge points")
    
    # Create coordinate arrays with the same length as time
    times = ds.time.values
    lat_array = np.full(len(times), np.nan)
    lon_array = np.full(len(times), np.nan)
    depth_array = np.full(len(times), np.nan)
    
    if len(merge_points) > 0 and len(latitudes) > 0:
        # Process coordinates by segment
        for i, time in enumerate(times):
            time_dt = pd.to_datetime(time).to_pydatetime().replace(tzinfo=None)
            
            # Determine which segment this time belongs to
            segment_idx = 0  # Default to segment 0
            for j, merge_point in enumerate(merge_points[1:], 1): 
                if time_dt >= merge_point:
                    segment_idx = j
            
            # Assign coordinates if we have that segment's values
            if segment_idx < len(latitudes):
                lat_array[i] = latitudes[segment_idx]
            elif latitudes:
                lat_array[i] = latitudes[0]  # Use first latitude as fallback
                
            if segment_idx < len(longitudes):
                lon_array[i] = longitudes[segment_idx]
            elif longitudes:
                lon_array[i] = longitudes[0]  # Use first longitude as fallback
                
            if segment_idx < len(depths):
                depth_array[i] = depths[segment_idx]
            elif depths:
                depth_array[i] = depths[0]  # Use first depth as fallback
                
        print("Assigned coordinates based on segments")
    else:
        # If no segments, use the first value for all points
        if latitudes:
            lat_array.fill(latitudes[0])
        if longitudes:
            lon_array.fill(longitudes[0])
        if depths:
            depth_array.fill(depths[0])
        print("Using constant coordinates (no segments found)")
    
    # Create a new dataset with all variables and explicit coordinates
    # Start with a copy of the original dataset
    cf_ds = ds.copy()
    
    # Create the time coordinate with proper CF formatting
    # Convert times to a pandas DatetimeIndex and ensure UTC
    time_index = pd.DatetimeIndex(times)

    # If times have timezone info (like Z suffix), convert to UTC then remove timezone info
    if time_index.tz is not None:
        time_index = time_index.tz_convert('UTC').tz_localize(None)
    
    # Remove microseconds for better CF compliance
    time_index = time_index.floor('S')  # Round down to seconds

    # Create new time variable with proper attributes
    time_var = xr.DataArray(
        time_index,
        dims=['time'],
        name='time',
        attrs={
            'standard_name': 'time',
            'long_name': 'Time',
        }
    )
    
    # Replace the time coordinate
    cf_ds = cf_ds.assign_coords({'time': time_var})
    
    # Add the other coordinate variables
    cf_ds = cf_ds.assign_coords({
        'latitude': ('time', lat_array, {
            'units': 'degrees_north',
            'standard_name': 'latitude',
            'long_name': 'Latitude'
        }),
        'longitude': ('time', lon_array, {
            'units': 'degrees_east',
            'standard_name': 'longitude',
            'long_name': 'Longitude'
        }),
        'depth': ('time', depth_array, {
            'units': 'm',
            'standard_name': 'depth',
            'positive': 'down',
            'long_name': 'Instrument depth'
        })
    })
    
    # Update attributes for all variables to ensure CF compliance
    for var_name in cf_ds.data_vars:
        # Skip if it's a coordinate variable
        if var_name in ['latitude', 'longitude', 'depth', 'time']:
            continue
        
        # Get current attributes
        attrs = cf_ds[var_name].attrs.copy()
        
        # Check for standard_name and units - these are crucial for CF compliance
        if 'standard_name' not in attrs:
            # Apply standard names for common oceanographic variables
            if 'temperature' in var_name:
                attrs['standard_name'] = 'sea_water_temperature'
            elif 'salinity' in var_name and 'practical' in var_name:
                attrs['standard_name'] = 'sea_water_practical_salinity'
            elif 'salinity' in var_name and 'absolute' in var_name:
                attrs['standard_name'] = 'sea_water_absolute_salinity'
            elif 'conductivity' in var_name:
                attrs['standard_name'] = 'sea_water_electrical_conductivity'
            elif 'pressure' in var_name:
                attrs['standard_name'] = 'sea_water_pressure'
        
        # Check for units
        if 'units' not in attrs:
            if 'temperature' in var_name:
                attrs['units'] = 'degree_C'
            elif 'salinity' in var_name and 'practical' in var_name:
                attrs['units'] = 'PSU'
            elif 'salinity' in var_name and 'absolute' in var_name:
                attrs['units'] = 'g/kg'
            elif 'conductivity' in var_name:
                attrs['units'] = 'S/m'
            elif 'pressure' in var_name:
                attrs['units'] = 'dbar'
        
        # Update the attributes
        cf_ds[var_name].attrs = attrs
        
    # Add global attributes for CF compliance
    cf_ds.attrs['Conventions'] = 'CF-1.8'
    # cf_ds.attrs['featureType'] = 'timeSeries'
    cf_ds.attrs['processing_date'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    cf_ds.attrs['processing_description'] = 'CF-compliant dataset with explicit coordinates'
    
    # Time coverage attributes
    if len(times) > 0:
        cf_ds.attrs['time_coverage_start'] = pd.to_datetime(times[0]).strftime('%Y-%m-%d %H:%M:%S')
        cf_ds.attrs['time_coverage_end'] = pd.to_datetime(times[-1]).strftime('%Y-%m-%d %H:%M:%S')
        
    # Geospatial attributes
    if len(latitudes) > 0:
        cf_ds.attrs['geospatial_lat_min'] = float(np.nanmin(lat_array))
        cf_ds.attrs['geospatial_lat_max'] = float(np.nanmax(lat_array))
    if len(longitudes) > 0:
        cf_ds.attrs['geospatial_lon_min'] = float(np.nanmin(lon_array))
        cf_ds.attrs['geospatial_lon_max'] = float(np.nanmax(lon_array))
    if len(depths) > 0:
        cf_ds.attrs['geospatial_vertical_min'] = float(np.nanmin(depth_array))
        cf_ds.attrs['geospatial_vertical_max'] = float(np.nanmax(depth_array))
    
    # Create proper encoding, including time
    # Define reference date for time units
    reference_date = pd.to_datetime(time_index[0]).strftime('%Y-%m-%d %H:%M:%S')
    
    # Set up encoding for all variables with compression
    encoding = {var: {'zlib': True, 'complevel': 4} for var in cf_ds.data_vars}
    
    # Special encoding for coordinates
    encoding.update({
        'time': {
            'units': f'seconds since {reference_date}',  # Explicit UTC
            'calendar': 'gregorian',
            'dtype': 'double',  # Use double instead of int32 for better compatibility
            'zlib': True, 
            'complevel': 4
        },
        'latitude': {'zlib': True, 'complevel': 4, '_FillValue': np.nan},
        'longitude': {'zlib': True, 'complevel': 4, '_FillValue': np.nan},
        'depth': {'zlib': True, 'complevel': 4, '_FillValue': np.nan}
    })
    
    # Make sure all variables have the proper coordinates
    for var_name in list(cf_ds.data_vars):
        if var_name not in ['latitude', 'longitude', 'depth']:
            # Add coordinate attributes to the variable
            cf_ds[var_name].attrs['coordinates'] = 'time latitude longitude depth'
            
            # If needed, you can also add the coordinates directly to the variable
            # This explicitly links the variable to the coordinate variables
            cf_ds[var_name] = cf_ds[var_name].assign_coords({
                'latitude': cf_ds.latitude,
                'longitude': cf_ds.longitude,
                'depth': cf_ds.depth
            })

    # For proper CF compliance, also add a coordinates global attribute
    cf_ds.attrs['coordinates_variables'] = 'latitude longitude depth'
    
    # Remove 'Z' from all time strings and standardize format
    for attr in ['platform_anchor_over_time', 'platform_buoy_recovery_time', 
                 'time_coverage_start', 'time_coverage_end', 'merge_point']:
        if attr in cf_ds.attrs:
            # Remove Z and standardize format
            if ',' in cf_ds.attrs[attr]:
                times = cf_ds.attrs[attr].split(',')
                cleaned_times = [t.strip().replace('Z', '') for t in times]
                cf_ds.attrs[attr] = ', '.join(cleaned_times)
            else:
                cf_ds.attrs[attr] = cf_ds.attrs[attr].replace('Z', '')
    
    # Add standardized access information
    cf_ds.attrs['site_code'] = 'STRATUS'
    cf_ds.attrs['platform_code'] = 'STRATUS'
    cf_ds.attrs['license'] = 'These data may be redistributed and used without restriction.'
    # cf_ds.attrs['acknowledgement'] = 'Please acknowledge the use of these data with: "Data provided by the Upper Ocean Processes Group at Woods Hole Oceanographic Institution"'
    # cf_ds.attrs['project'] = 'Stratus Ocean Reference Station'
    # cf_ds.attrs['references'] = 'https://uop.whoi.edu/projects/stratus/'
    # Add funding acknowledgment
    cf_ds.attrs['acknowledgement'] = 'The Stratus project is supported by the National Oceanic and Atmospheric Administration (NOAA) Global Ocean Monitoring and Observing (GOMO) Program through the Cooperative Institute for the North Atlantic Region (CINAR) under Cooperative Agreement NA14OAR4320158. NOAA CPO FundRef number (100007298).'

    # Fix CF compliance issues found by CF-checker

    # 2. Fix time monotonicity issues
    time_diffs = np.diff(cf_ds.time.values)
    if np.any(time_diffs <= np.timedelta64(0)):
        print("WARNING: Time values are not monotonic. Sorting and removing duplicates...")
        
        # Sort by time
        cf_ds = cf_ds.sortby('time')
        
        # Remove duplicate times if any
        _, index = np.unique(cf_ds.time.values, return_index=True)
        if len(index) < len(cf_ds.time):
            cf_ds = cf_ds.isel(time=index)
            print(f"Removed {len(cf_ds.time) - len(index)} duplicate time points")
    
    print(f"Saving CF-compliant dataset to: {output_file}")
    cf_ds.to_netcdf(output_file, encoding=encoding, format='NETCDF4')
    
    # Print information about saved file
    original_size_mb = os.path.getsize(input_file) / (1024 * 1024)
    new_size_mb = os.path.getsize(output_file) / (1024 * 1024)
    
    print(f"Successfully created CF-compliant dataset with {len(cf_ds.data_vars)} variables")
    print(f"Original file size: {original_size_mb:.2f} MB")
    print(f"CF-compliant file size: {new_size_mb:.2f} MB")
    print(f"Latitude range: {np.nanmin(lat_array):.4f} to {np.nanmax(lat_array):.4f}")
    print(f"Longitude range: {np.nanmin(lon_array):.4f} to {np.nanmax(lon_array):.4f}")
    print(f"Depth range: {np.nanmin(depth_array):.1f}m to {np.nanmax(depth_array):.1f}m")
    
except Exception as e:
    print(f"Error creating CF-compliant dataset: {e}")
    import traceback
    traceback.print_exc()

# %%
# CF checker
from cfchecker.cfchecks import CFChecker
checker = CFChecker()
checker.checker('/Users/yugao/UOP/ORS-processing/data/processed/merged_stratus/stratus_temperature_2012_2023.nc')

# %%
# Create temperature-only version
temp_only_ds = cf_ds.copy()

# Drop unwanted variables
del temp_only_ds['sea_water_practical_salinity']
del temp_only_ds['sea_water_absolute_salinity']
del temp_only_ds['sea_water_electrical_conductivity']
del temp_only_ds['sea_water_pressure']

# Update the dataset description
temp_only_ds.attrs['title'] = 'Stratus Ocean Reference Station - Temperature Only'
temp_only_ds.attrs['summary'] = 'Sea water temperature measurements from Stratus moorings 12-22 (2012-2023)'
temp_only_ds.attrs['processing_description'] = 'Temperature-only CF-compliant dataset with explicit coordinates'

# Create encoding for temperature-only dataset
temp_encoding = {
    'time': {
        'units': f'seconds since {reference_date}',
        'calendar': 'gregorian',
        'dtype': 'double',  # Force double precision
        'zlib': True, 
        'complevel': 4
    },
    'latitude': {'zlib': True, 'complevel': 4, '_FillValue': np.nan},
    'longitude': {'zlib': True, 'complevel': 4, '_FillValue': np.nan},
    'depth': {'zlib': True, 'complevel': 4, '_FillValue': np.nan},
    'sea_water_temperature': {'zlib': True, 'complevel': 4}
}

# Save the temperature-only dataset with proper encoding
temp_output_file = os.path.join(output_dir, 'stratus_temperature_2012_2023.nc')

print(f"Saving temperature-only dataset to: {temp_output_file}")
temp_only_ds.to_netcdf(temp_output_file, encoding=temp_encoding, format='NETCDF4')

print(f"Temperature-only dataset successfully saved with shape: {temp_only_ds.sea_water_temperature.shape}")
# %%
# check the saved temperature-only dataset with CF checker
checker.checker(temp_output_file)

# %%
