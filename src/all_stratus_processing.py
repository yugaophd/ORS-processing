# %%
# Stratus deployment processing script
# Regular script format for Jupyter notebooks

import numpy as np
import xarray as xr
import matplotlib.pyplot as plt
import os, sys
import json
import scipy.io
import cftime
import pandas as pd
import re
import glob

# Import your custom modules
os.chdir('/Users/yugao/UOP/ORS-processing/src')
from metadata import create_json, process_attributes_direct, standardize_attribute_names, \
                     ensure_standard_attributes, validate_attributes, add_geospatial_attributes, \
                     reorder_oceansites_attributes
from netcdf_sbe37 import read_mat_file
from util import create_xarray_dataset, process_attributes_direct, fill_or_create_variables
import gsw  # Add this import for TEOS-10 calculations
from plot_function import plot_spike_data, plot_deployment_recovery
# %%
# Configuration: specify the deployment config file
config_file = 'stratus12_config.json'  # Edit this path as needed
data_path = '/Users/yugao/UOP/ORS-processing/data/processed'
version = 'v1'  # Specify version

# %%
# Load deployment configuration
with open(config_file, 'r') as f:
    config = json.load(f)

case_name = config['case_name']
print(f"Processing deployment: {case_name}")
print(f"Version: {version}")

# %%
# Extract case number from case_name
case_number = re.search(r'\d+', case_name).group()

# Get water depth information from config
water_depth_from_mooring_diagram = config['water_depth']['from_mooring_diagram']
water_depth_from_ship_uncorrected = config['water_depth']['from_ship_uncorrected']
water_depth_from_ship_corrected = config['water_depth']['from_ship_corrected']

# Calculate instrument depth using height above bottom
instrument_height_above_bottom = config['instruments'][0]['height_above_bottom']  # Assuming same for all instruments
instrument_depth = water_depth_from_ship_corrected - instrument_height_above_bottom
# print(f"Instrument depth: instrument depth (using corrected water depth of {water_depth_from_ship_corrected} m)")

# %%
# Load metadata configuration from the same directory
metadata_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "stratus_metadata.json")
try:
    with open(metadata_file, 'r') as f:
        metadata_config = json.load(f)
    print(f"Loaded metadata from: {metadata_file}")
except FileNotFoundError:
    raise FileNotFoundError(f"Required metadata file not found: {metadata_file}")

# %%
# Process each instrument
processed_datasets = []

for instrument in config['instruments']:
    print(f"Processing instrument SN {instrument['serial_number']}")
    
    # Read MATLAB file
    mat_data = read_mat_file(instrument['mat_file'])
    
    # Create xarray dataset
    ds = create_xarray_dataset(mat_data)
    
    # Process metadata
    processed_attributes = process_attributes_direct(mat_data)
    ds.attrs.update(processed_attributes)
    
    # Add anchor survey coordinates
    ds.attrs['latitude_anchor_survey'] = mat_data['latitude']
    ds.attrs['longitude_anchor_survey'] = mat_data['longitude']
    
    # Process time coordinates
    ds['time'].attrs['units'] = 'days since 0001-01-01'
    decoded_time = xr.decode_cf(ds, use_cftime=True).time
    adjusted_dates = np.array([date - pd.Timedelta(days=365) for date in decoded_time.values])
    ds['time'] = adjusted_dates
    
    # Truncate dataset
    # Get time attribute keys from config or use defaults
    time_attr_keys = config.get('time_attribute_keys', {})
    anchor_over_time_key = time_attr_keys.get('anchor_over_time', 'platform_anchor_over_time')
    release_fired_time_key = time_attr_keys.get('release_fired_time', 'platform_buoy_recovery_time')
    anchor_over_time = pd.to_datetime(ds.attrs[anchor_over_time_key])
    release_fired_time = pd.to_datetime(ds.attrs[release_fired_time_key])
    
    hours_after_deployment = config['processing_params']['truncation_hours_after_deployment']
    time_coverage_start = anchor_over_time + pd.Timedelta(hours=hours_after_deployment)
    
    valid_time_window = ds.sel(time=slice(time_coverage_start, release_fired_time))
    time_coverage_start_str = str(time_coverage_start)
    valid_time_window.attrs['time_coverage_start'] = time_coverage_start_str
    valid_time_window.attrs['time_coverage_end'] = str(release_fired_time)
    
    # Apply CF standard names for non-computed variables only
    valid_time_window = valid_time_window.rename({
        'temp': 'sea_water_temperature',
        'press': 'sea_water_pressure',
        'cond': 'sea_water_electrical_conductivity'
    })

    # Store original salinity values temporarily for comparison (not saved)
    original_practical_salinity = None
    original_absolute_salinity = None
    if 'sal' in valid_time_window:
        original_practical_salinity = valid_time_window['sal'].copy(deep=True)
    if 'abssal' in valid_time_window:
        original_absolute_salinity = valid_time_window['abssal'].copy(deep=True)

    # Calculate pressure from instrument depth for salinity calculations
    lat = float(valid_time_window.attrs['latitude_anchor_survey'])
    z = -1 * instrument_depth  # negative because depth is positive downward
    calculated_pressure = gsw.p_from_z(z, lat)

    print(f"Using calculated pressure of {calculated_pressure:.3f} dbar for salinity calculations")

    # Store the original pressure data temporarily
    original_pressure = None
    if 'sea_water_pressure' in valid_time_window:
        original_pressure = valid_time_window['sea_water_pressure'].copy(deep=True)

    # Create temporary array for calculated pressure (not stored in dataset)
    pressure_values = np.full_like(valid_time_window['sea_water_temperature'].values, calculated_pressure)

    # Compute practical salinity using TEOS-10/GSW with calculated pressure
    conductivity_mS_cm = valid_time_window['sea_water_electrical_conductivity'] * 10
    practical_salinity = gsw.SP_from_C(conductivity_mS_cm, 
                                      valid_time_window['sea_water_temperature'],
                                      pressure_values)  # Use the calculated pressure values directly

    # Create the practical salinity variable with explicit coordinates
    valid_time_window['sea_water_practical_salinity'] = (('time'), practical_salinity.values)
    valid_time_window['sea_water_practical_salinity'].attrs['units'] = 'psu'
    valid_time_window['sea_water_practical_salinity'].attrs['long_name'] = 'sea water practical salinity'
    # valid_time_window['sea_water_practical_salinity'].attrs['comment'] = 'Practical salinity calculated using the TEOS-10 sw_sal algorithm at the fixed instrument deployment depth.'

    # Compute absolute salinity using TEOS-10/GSW
    lon = float(valid_time_window.attrs['longitude_anchor_survey'])
    lat = float(valid_time_window.attrs['latitude_anchor_survey'])
    absolute_salinity = gsw.SA_from_SP(practical_salinity, 
                                     pressure_values,
                                     lon, lat)

    # Create the absolute salinity variable with explicit coordinates
    valid_time_window['sea_water_absolute_salinity'] = (('time'), absolute_salinity.values)
    valid_time_window['sea_water_absolute_salinity'].attrs['units'] = 'g/kg'
    valid_time_window['sea_water_absolute_salinity'].attrs['long_name'] = 'sea water absolute salinity'
    # valid_time_window['sea_water_absolute_salinity'].attrs['comment'] = 'Absolute salinity derived from practical salinity measurements at instrument depth using the TEOS-10 sw_sal conversion algorithm.'

    # Explicitly set encoding for these variables
    valid_time_window['sea_water_practical_salinity'].encoding = {
        '_FillValue': metadata_config.get("default_fill_value", -99999.0),
        'dtype': 'float32'
    }
    valid_time_window['sea_water_absolute_salinity'].encoding = {
        '_FillValue': metadata_config.get("default_fill_value", -99999.0),
        'dtype': 'float32'
    }

    # Add a print statement to verify the variables exist and contain data
    print(f"Practical salinity stats: min={practical_salinity.min().values:.3f}, max={practical_salinity.max().values:.3f}, mean={practical_salinity.mean().values:.3f}")
    print(f"Absolute salinity stats: min={absolute_salinity.min().values:.3f}, max={absolute_salinity.max().values:.3f}, mean={absolute_salinity.mean().values:.3f}")

    # Compare computed with original values (for QC and logging only)
    if original_practical_salinity is not None:
        diff_practical = valid_time_window['sea_water_practical_salinity'] - original_practical_salinity
        mean_diff_practical = diff_practical.mean().values
        std_diff_practical = diff_practical.std().values
        print(f"Practical salinity comparison - Mean difference: {mean_diff_practical:.6f}, STD: {std_diff_practical:.6f}")

    if original_absolute_salinity is not None:
        diff_absolute = valid_time_window['sea_water_absolute_salinity'] - original_absolute_salinity
        mean_diff_absolute = diff_absolute.mean().values
        std_diff_absolute = diff_absolute.std().values
        print(f"Absolute salinity comparison - Mean difference: {mean_diff_absolute:.6f}, STD: {std_diff_absolute:.6f}")

    # Remove original variables if they exist to ensure they're not saved
    if 'sal' in valid_time_window:
        valid_time_window = valid_time_window.drop_vars('sal')
    if 'abssal' in valid_time_window:
        valid_time_window = valid_time_window.drop_vars('abssal')
    
    # Apply metadata standards
    valid_time_window = standardize_attribute_names(valid_time_window)
    valid_time_window = ensure_standard_attributes(valid_time_window)
    
    # Apply metadata from configuration
    valid_time_window.attrs['version'] = version  # Add version to attributes
    
    # Add water depth information
    valid_time_window.attrs['water_depth_from_ship_uncorrected_m'] = water_depth_from_ship_uncorrected
    valid_time_window.attrs['water_depth_from_ship_corrected_m'] = water_depth_from_ship_corrected
    valid_time_window.attrs['water_depth_from_mooring_diagram_m'] = water_depth_from_mooring_diagram
    valid_time_window.attrs['instrument_height_above_bottom_m'] = instrument['height_above_bottom']
    
    # Calculate instrument depth
    instrument_depth = water_depth_from_ship_corrected - instrument['height_above_bottom']
    valid_time_window.attrs['instrument_depth'] = instrument_depth
    valid_time_window.attrs['instrument_depth_comment'] = 'water depth from ship corrected minus instrument height above bottom'
    
    # Add geospatial and time attributes
    valid_time_window = reorder_oceansites_attributes(valid_time_window)
    valid_time_window = add_geospatial_attributes(valid_time_window)
    
    # Map existing attributes to standard names
    for old_name, new_name in metadata_config.get("attribute_mapping", {}).items():
        if old_name in valid_time_window.attrs:
            valid_time_window.attrs[new_name] = valid_time_window.attrs[old_name]
    
    # Add fixed attributes
    for attr_name, attr_value in metadata_config.get("fixed_attributes", {}).items():
        valid_time_window.attrs[attr_name] = attr_value
    
    # Add dynamic attributes
    for attr_name, attr_template in metadata_config.get("dynamic_attributes", {}).items():
        valid_time_window.attrs[attr_name] = attr_template.format(case_number=case_number)
    
    # Apply variable attributes
    for var_name, attrs in metadata_config.get("variable_attributes", {}).items():
        if var_name in valid_time_window:
            # Clear existing attributes first
            for attr in list(valid_time_window[var_name].attrs.keys()):
                del valid_time_window[var_name].attrs[attr]
            
            # Apply new attributes 
            for attr_name, attr_template in attrs.items():
                if isinstance(attr_template, str) and '{depth}' in attr_template:
                    # Always use the calculated instrument depth from corrected water depth
                    depth = instrument_depth
                    
                    # Format the template with the depth
                    valid_time_window[var_name].attrs[attr_name] = attr_template.format(depth=depth)
                else:
                    valid_time_window[var_name].attrs[attr_name] = attr_template
            
            # Add debug output - also inside the loop to see each variable's attributes
            print(f"Applied attributes to {var_name}: {valid_time_window[var_name].attrs}")
    
    # Set fill values
    default_fill_value = metadata_config.get("default_fill_value", -99999.0)
    for var_name in valid_time_window.variables:
        if var_name != 'time':
            valid_time_window[var_name].encoding['_FillValue'] = default_fill_value
    
    # Validate attributes
    is_valid, issues = validate_attributes(valid_time_window)
    if not is_valid:
        print(f"Warning: Issues with dataset for SN {instrument['serial_number']}:")
        for issue in issues:
            print(f"  - {issue}")
    
    # Save dataset with version in filename
    output_dir = os.path.join(data_path, case_name, version)
    os.makedirs(output_dir, exist_ok=True)
    
    output_file = os.path.join(output_dir, f'{case_name}_{instrument["serial_number"]}_truncated.nc')
    valid_time_window.to_netcdf(output_file)
    print(f"Saved processed data to {output_file}")
    
    processed_datasets.append({
        'serial_number': instrument['serial_number'],
        'dataset': valid_time_window,
        'output_file': output_file
    })
    

# %%
# Create comparison plot using the saved NetCDF files instead of in-memory datasets
if len(processed_datasets) >= 2:
    import matplotlib.dates as mdates
    from datetime import datetime
    import numpy.ma as ma
    
    # Read the saved NetCDF files
    output_file1 = processed_datasets[0]['output_file']
    output_file2 = processed_datasets[1]['output_file']
    
    # Load datasets from disk
    truncated_ds = xr.open_dataset(output_file1)
    truncated_ds2 = xr.open_dataset(output_file2)
    
    instrument_SN = processed_datasets[0]['serial_number']
    instrument_SN2 = processed_datasets[1]['serial_number']
    
    variables = ['sea_water_temperature', 
                'sea_water_practical_salinity', 
                'sea_water_absolute_salinity', 
                'sea_water_electrical_conductivity', 
                'sea_water_pressure']
    labels = ['Temperature (°C)', 
            'Salinity (psu)', 
            'Absolute Salinity (g/kg)', 
            'Conductivity (S/m)', 
            'Pressure (dbar)']
    panel_titles = ['Temperature', 
                   'Practical Salinity', 
                   'Absolute Salinity', 
                   'Conductivity', 
                   'Pressure']
    
    colors = ['blue', 'green', 'red', 'purple', 'black']
    colors2 = ['cyan', 'lightgreen', 'pink', 'violet', 'gray']
    
    fig, axs = plt.subplots(len(variables), 1, figsize=(12, 15), sharex=True)
    
    def convert_cftime_to_matplotlib(time_values):
        result = []
        for t in time_values:
            if isinstance(t, np.datetime64):
                # Convert numpy.datetime64 to Python datetime
                t_datetime = pd.Timestamp(t).to_pydatetime()
                result.append(t_datetime)
            else:
                # Handle cftime objects
                result.append(datetime(t.year, t.month, t.day, t.hour, t.minute, t.second))
        return result
    
    # Simply use the truncated datasets directly
    ds1_common = truncated_ds
    ds2_common = truncated_ds2
    
    for i, var in enumerate(variables):
        ax = axs[i]
        has_data = False
        
        if var in ds1_common.variables:
            time_data = convert_cftime_to_matplotlib(ds1_common[var].time.values)
            var_data = ds1_common[var].values
            var_mask = np.isnan(var_data)
            
            if hasattr(ds1_common[var], 'encoding') and '_FillValue' in ds1_common[var].encoding:
                fill_val = ds1_common[var].encoding['_FillValue']
                var_mask = np.logical_or(var_mask, var_data == fill_val)
            
            masked_data = ma.masked_array(var_data, mask=var_mask)
            ax.plot(time_data, masked_data, 
                    label=f'SBE {instrument_SN}', color=colors[i])
            has_data = True
        
        if var in ds2_common.variables:
            time_data2 = convert_cftime_to_matplotlib(ds2_common[var].time.values)
            var_data = ds2_common[var].values
            var_mask = np.isnan(var_data)
            
            if hasattr(ds2_common[var], 'encoding') and '_FillValue' in ds2_common[var].encoding:
                fill_val = ds2_common[var].encoding['_FillValue']
                var_mask = np.logical_or(var_mask, var_data == fill_val)
            
            masked_data2 = ma.masked_array(var_data, mask=var_mask)
            ax.plot(time_data2, masked_data2, 
                    label=f'SBE {instrument_SN2}', color=colors2[i])
            has_data = True
        
        # Compute statistics between datasets if both are available
        if var in ds1_common.variables and var in ds2_common.variables:
            try:
                # We can't easily calculate diff statistics without aligning the data
                # So we'll just calculate correlation if both datasets have enough points
                if len(masked_data.compressed()) > 2 and len(masked_data2.compressed()) > 2:
                    # Note: this is only meaningful if the time ranges overlap significantly
                    try:
                        correlation = np.corrcoef(
                            masked_data.compressed()[:min(len(masked_data.compressed()), len(masked_data2.compressed()))], 
                            masked_data2.compressed()[:min(len(masked_data.compressed()), len(masked_data2.compressed()))]
                        )[0, 1]
                        ax.legend(title=f'Correlation: {correlation:.3f}')
                    except:
                        ax.legend()
                else:
                    ax.legend()
            except Exception as e:
                print(f"Error calculating statistics for {var}: {e}")
                ax.legend()
        elif has_data:
            ax.legend()
        
        ax.set_title(panel_titles[i])
        ax.set_ylabel(labels[i])
        
        # Add gridlines for better readability
        ax.grid(True, alpha=0.3)
    
    axs[-1].set_xlabel('Time')
    
    # Format x-axis to show dates
    date_form = mdates.DateFormatter("%Y-%m-%d")
    axs[-1].xaxis.set_major_formatter(date_form)
    axs[-1].xaxis.set_major_locator(mdates.MonthLocator())
    plt.gcf().autofmt_xdate()
    
    # Get deployment metadata
    latitude = truncated_ds.latitude_anchor_survey if hasattr(truncated_ds, 'latitude_anchor_survey') else 0
    longitude = truncated_ds.longitude_anchor_survey if hasattr(truncated_ds, 'longitude_anchor_survey') else 0
    
    # Format latitude and longitude
    if float(latitude) < 0:
        formatted_latitude = f"{abs(float(latitude)):.4f}°S"
    else:
        formatted_latitude = f"{float(latitude):.4f}°N"
    
    if float(longitude) < 0:
        formatted_longitude = f"{abs(float(longitude)):.4f}°W"
    else:
        formatted_longitude = f"{float(longitude):.4f}°E"
    
    # Create a more informative title
    instrument_depth = truncated_ds.attrs.get('instrument_depth', 'Unknown')
    
    fig.suptitle(
        f'Comparison within {case_name} Data\n'
        f'Location: ({formatted_latitude}, {formatted_longitude}) | '
        f'Depth: {instrument_depth}m | V{version}', 
        fontsize=16
    )
    
    plt.tight_layout(rect=[0, 0.03, 1, 0.95])
    
    plot_path = '../img/'
    os.makedirs(plot_path, exist_ok=True)
    plot_filename = os.path.join(plot_path, f"{case_name}_{instrument_SN}_vs_{instrument_SN2}_comparison.png")
    plt.savefig(plot_filename, dpi=150)
    print(f'Plot saved as {plot_filename}')
    
    # Close datasets to release file handles
    truncated_ds.close()
    truncated_ds2.close()


# %%
# Create spike plots for each instrument to analyze deployment and recovery
print("\nCreating spike plots for deployment and recovery periods...")

# Process the first two instruments using original MAT files
if len(processed_datasets) >= 2:
    # Get instrument information for the first two instruments
    instrument1 = config['instruments'][0]
    instrument2 = config['instruments'][1]
    sn1 = instrument1['serial_number']
    sn2 = instrument2['serial_number']
    
    # Read the original MAT files
    print(f"Reading original MAT file for instrument SN {sn1}")
    mat_data1 = read_mat_file(instrument1['mat_file'])
    
    print(f"Reading original MAT file for instrument SN {sn2}")
    mat_data2 = read_mat_file(instrument2['mat_file'])
    
    # Create xarray datasets from MAT files (without truncation)
    ds1 = create_xarray_dataset(mat_data1)
    ds2 = create_xarray_dataset(mat_data2)
    
    # Process metadata (just for reference timing)
    ds1.attrs.update(process_attributes_direct(mat_data1))
    ds2.attrs.update(process_attributes_direct(mat_data2))
    
    # Add anchor survey coordinates
    ds1.attrs['latitude_anchor_survey'] = mat_data1['latitude']
    ds1.attrs['longitude_anchor_survey'] = mat_data1['longitude']
    ds2.attrs['latitude_anchor_survey'] = mat_data2['latitude']
    ds2.attrs['longitude_anchor_survey'] = mat_data2['longitude']
    
    # Process time coordinates
    for ds in [ds1, ds2]:
        ds['time'].attrs['units'] = 'days since 0001-01-01'
        decoded_time = xr.decode_cf(ds, use_cftime=True).time
        adjusted_dates = np.array([date - pd.Timedelta(days=365) for date in decoded_time.values])
        ds['time'] = adjusted_dates
        
        # Also rename variables for consistency with processed data
        if 'temp' in ds:
            ds = ds.rename({'temp': 'sea_water_temperature'})
        if 'press' in ds:
            ds = ds.rename({'press': 'sea_water_pressure'})
        if 'cond' in ds:
            ds = ds.rename({'cond': 'sea_water_electrical_conductivity'})
    
    # Create directory for saving plots
    img_path = '../img/'
    os.makedirs(img_path, exist_ok=True)
    
    # Get deployment and recovery times from the config or MAT file attributes
    # For the first dataset - direct attribute access with correct keys
    print(f"Getting reference times for instrument SN {sn1}")
    time_attr_keys = config.get('time_attribute_keys', {})
    anchor_over_time_key = time_attr_keys.get('anchor_over_time', 'platform_anchor_over_time')
    release_fired_time_key = time_attr_keys.get('release_fired_time', 'platform_buoy_recovery_time')
    
    # Get these times from the MAT file attributes
    anchor_over_time1 = pd.to_datetime(ds1.attrs[anchor_over_time_key]).replace(tzinfo=None)
    release_fired_time1 = pd.to_datetime(ds1.attrs[release_fired_time_key]).replace(tzinfo=None)
    
    # For the second dataset
    print(f"Getting reference times for instrument SN {sn2}")
    anchor_over_time2 = pd.to_datetime(ds2.attrs[anchor_over_time_key]).replace(tzinfo=None)
    release_fired_time2 = pd.to_datetime(ds2.attrs[release_fired_time_key]).replace(tzinfo=None)
    
    # 1. Create spike plots for each instrument
    try:
        # Get spike times from config
        deployment_start = pd.to_datetime(config['deployment_spike_times']['start']).replace(tzinfo=None)
        deployment_end = pd.to_datetime(config['deployment_spike_times']['end']).replace(tzinfo=None)
        recovery_start = pd.to_datetime(config['recovery_spike_times']['start']).replace(tzinfo=None)
        recovery_end = pd.to_datetime(config['recovery_spike_times']['end']).replace(tzinfo=None)
        
        # Add buffer 
        buffer = pd.Timedelta(hours=2)
        
        # Process first instrument - use ORIGINAL MAT DATA for spikes
        ds1_deployment_spike = ds1.sel(time=slice(deployment_start - buffer, deployment_end + buffer))
        ds1_recovery_spike = ds1.sel(time=slice(recovery_start - buffer, recovery_end + buffer))
        
        # Plot first instrument spike data
        spike_img_path1 = os.path.join(img_path, f"{case_name}_{sn1}_spikes.png")
        plot_spike_data(ds1_deployment_spike, ds1_recovery_spike, case_name, spike_img_path1,
                        deployment_spike_start=deployment_start, 
                        deployment_spike_end=deployment_end, 
                        recovery_spike_start=recovery_start,
                        recovery_spike_end=recovery_end,
                        start_label="Spike starts", 
                        end_label="Spike ends")
        print(f"Spike plot saved as {spike_img_path1}")
        
        # Process second instrument - use ORIGINAL MAT DATA for spikes
        ds2_deployment_spike = ds2.sel(time=slice(deployment_start - buffer, deployment_end + buffer))
        ds2_recovery_spike = ds2.sel(time=slice(recovery_start - buffer, recovery_end + buffer))
        
        # Plot second instrument spike data
        spike_img_path2 = os.path.join(img_path, f"{case_name}_{sn2}_spikes.png")
        plot_spike_data(ds2_deployment_spike, ds2_recovery_spike, case_name, spike_img_path2,
                        deployment_spike_start=deployment_start, 
                        deployment_spike_end=deployment_end, 
                        recovery_spike_start=recovery_start,
                        recovery_spike_end=recovery_end,
                        start_label="Spike starts", 
                        end_label="Spike ends")
        print(f"Spike plot saved as {spike_img_path1}")
        
    except Exception as e:
        print(f"Error creating spike plots: {e}")
    
    # 2. Create deployment/recovery phase plots for each instrument
    try:
        # Process first instrument deployment/recovery phases
        ds1_deploy_phase = ds1.sel(time=slice(anchor_over_time1 - pd.Timedelta(hours=4), 
                                           anchor_over_time1 + pd.Timedelta(hours=4)))
        ds1_recovery_phase = ds1.sel(time=slice(release_fired_time1 - pd.Timedelta(hours=4), 
                                             release_fired_time1 + pd.Timedelta(hours=4)))
        
        # Plot first instrument deployment/recovery phases
        phase_img_path1 = os.path.join(img_path, f"{case_name}_{sn1}_deployment_recovery.png")
        plot_deployment_recovery(ds1_deploy_phase, ds1_recovery_phase, case_name, phase_img_path1,
                                deployment_time=anchor_over_time1, 
                                recovery_time=release_fired_time1,
                                deployment_label="Anchor dropped", 
                                recovery_label="Mooring released")
        print(f"Deployment and recovery phase plot saved as {phase_img_path1}")
        
        # Process second instrument deployment/recovery phases
        ds2_deploy_phase = ds2.sel(time=slice(anchor_over_time2 - pd.Timedelta(hours=4), 
                                    anchor_over_time2 + pd.Timedelta(hours=4)))
        ds2_recovery_phase = ds2.sel(time=slice(release_fired_time2 - pd.Timedelta(hours=4), 
                                    release_fired_time2 + pd.Timedelta(hours=4)))
        
        # Plot second instrument deployment/recovery phases
        phase_img_path2 = os.path.join(img_path, f"{case_name}_{sn2}_deployment_recovery.png")
        plot_deployment_recovery(ds2_deploy_phase, ds2_recovery_phase, case_name, phase_img_path2,
                                deployment_time=anchor_over_time2, 
                                recovery_time=release_fired_time2,
                                deployment_label="Anchor dropped", 
                                recovery_label="Mooring released")
        print(f"Deployment and recovery phase plot saved as {phase_img_path2}")
        
    except Exception as e:
        print(f"Error creating deployment/recovery phase plots: {e}")
    
    # No need to close datasets, they weren't read from files
else:
    print("Need at least two instruments to create comparison plots")

# %%
