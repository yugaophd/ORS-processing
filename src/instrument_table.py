import os
import xarray as xr
import pandas as pd
import numpy as np
from pathlib import Path
import glob

def is_variable_observed(da, fill_value=-99999.0):
    """
    Check if a variable contains actual observations or is all fill values.
    
    Parameters:
    da (xr.DataArray): The data array to check
    fill_value (float): The fill value to check against
    
    Returns:
    bool: True if variable has real observations, False if all fill values
    """
    # Check for standard fill values
    if hasattr(da, '_FillValue'):
        fill_val = da._FillValue
    elif 'missing_value' in da.attrs:
        fill_val = da.attrs['missing_value']
    else:
        fill_val = fill_value
    
    # Check if all values are fill values or NaN
    if np.isnan(fill_val):
        is_all_fill = np.isnan(da.values).all()
    else:
        is_all_fill = (da.values == fill_val).all()
    
    # Also check for all NaN
    is_all_nan = np.isnan(da.values).all()
    
    # Check for very small variance (essentially constant)
    try:
        variance = np.nanvar(da.values)
        is_constant = variance < 1e-10
    except:
        is_constant = False
    
    return not (is_all_fill or is_all_nan or is_constant)

def get_sampling_frequency(ds):
    """
    Calculate sampling frequency from time coordinate with debugging.
    
    Parameters:
    ds (xr.Dataset): The dataset
    
    Returns:
    str: Sampling interval description
    """
    if 'time' not in ds.coords:
        return "Unknown"
    
    time_vals = ds.time.values
    if len(time_vals) < 2:
        return "Insufficient data"
    
    # Debug: Print first few time values
    print(f"First 5 time values: {time_vals[:5]}")
    
    # Calculate time differences
    try:
        # Convert to pandas datetime if not already
        if hasattr(time_vals[0], 'astype'):
            # This handles numpy datetime64
            time_series = pd.to_datetime(time_vals)
        else:
            time_series = pd.to_datetime(time_vals)
        
        time_diffs = time_series.diff().dropna()
        
        # Debug: Print first few differences
        print(f"First 5 time differences: {time_diffs.head()}")
        
        # Get the most common time difference (mode)
        mode_diff = time_diffs.mode()
        if len(mode_diff) == 0:
            return "Irregular"
        
        # Get the most frequent interval
        most_common_diff = mode_diff.iloc[0]
        
        # Convert to minutes
        interval_seconds = most_common_diff.total_seconds()
        interval_minutes = interval_seconds / 60
        
        # Debug: Print calculated intervals
        print(f"Interval: {interval_seconds} seconds = {interval_minutes} minutes")
        
        if interval_minutes < 1:
            return f"{interval_seconds:.0f} sec"
        elif interval_minutes < 60:
            return f"{interval_minutes:.0f} min"
        else:
            interval_hours = interval_minutes / 60
            return f"{interval_hours:.1f} hr"
            
    except Exception as e:
        print(f"Error calculating sampling frequency: {e}")
        return f"Error: {str(e)}"

def extract_variables_from_netcdf_files(base_path):
    """
    Extract variables from all processed NetCDF files, checking for actual observations.
    """
    pattern = os.path.join(base_path, "*/v1/*_truncated.nc")
    nc_files = glob.glob(pattern)
    
    results = []
    
    for file_path in sorted(nc_files):
        try:
            path_parts = Path(file_path).parts
            deployment = path_parts[-3]  # e.g., 'stratus12'
            filename = Path(file_path).stem
            
            # Extract instrument serial number
            parts = filename.split('_')
            if len(parts) >= 2:
                instrument_sn = parts[1]
            else:
                instrument_sn = "unknown"
            
            # Open the NetCDF file
            with xr.open_dataset(file_path) as ds:
                # Get sampling frequency
                sampling_freq = get_sampling_frequency(ds)
                
                # Check each data variable for actual observations
                observed_vars = []
                all_vars = []
                
                for var_name in ds.data_vars:
                    all_vars.append(var_name)
                    if is_variable_observed(ds[var_name]):
                        observed_vars.append(var_name)
                
                # Create human-readable variable names
                observed_readable = []
                for var in observed_vars:
                    if 'temperature' in var.lower():
                        observed_readable.append('Temperature')
                    elif 'conductivity' in var.lower():
                        observed_readable.append('Conductivity')
                    elif 'pressure' in var.lower():
                        observed_readable.append('Pressure')
                    elif 'salinity' in var.lower():
                        observed_readable.append('Salinity')
                    else:
                        # Use long_name if available
                        if 'long_name' in ds[var].attrs:
                            observed_readable.append(ds[var].attrs['long_name'])
                        else:
                            observed_readable.append(var)
                
                # Get coordinate info
                coords = list(ds.coords.keys())
                
                results.append({
                    'Deployment': deployment.upper(),
                    'Instrument_SN': instrument_sn,
                    'Sampling_Frequency': sampling_freq,
                    'All_Variables': ', '.join(all_vars),
                    'Observed_Variables': ', '.join(observed_vars),
                    'Observed_Readable': ', '.join(observed_readable),
                    'Coordinates': ', '.join(coords),
                    'Total_Variables': len(all_vars),
                    'Observed_Count': len(observed_vars),
                    'File_Size_MB': round(os.path.getsize(file_path) / (1024*1024), 2),
                    'File_Path': file_path
                })
                
        except Exception as e:
            print(f"Error processing {file_path}: {e}")
            results.append({
                'Deployment': Path(file_path).parts[-3].upper(),
                'Instrument_SN': 'ERROR',
                'Sampling_Frequency': 'ERROR',
                'All_Variables': f'ERROR: {str(e)}',
                'Observed_Variables': 'ERROR',
                'Observed_Readable': 'ERROR',
                'Coordinates': '',
                'Total_Variables': 0,
                'Observed_Count': 0,
                'File_Size_MB': 0,
                'File_Path': file_path
            })
    
    return pd.DataFrame(results)

def create_latex_table(df):
    """
    Create LaTeX table based on actual observations.
    """
    # Group by deployment to get consensus info
    deployment_info = {}
    
    for _, row in df.iterrows():
        deployment = row['Deployment']
        if deployment not in deployment_info:
            deployment_info[deployment] = {
                'variables': set(),
                'sampling_freq': row['Sampling_Frequency'],
                'instrument_model': 'SBE37' if 'sbe37' in row['File_Path'].lower() else 'SBE16'
            }
        
        # Add observed variables
        if row['Observed_Readable'] != 'ERROR' and row['Observed_Readable']:
            deployment_info[deployment]['variables'].update(
                [v.strip() for v in row['Observed_Readable'].split(',')]
            )
    
    # Extract year from deployment name
    def get_year(deployment):
        num = ''.join(filter(str.isdigit, deployment))
        if num:
            year_offset = int(num)
            return 2012 + year_offset - 12  # Stratus 12 started in 2012
        return "Unknown"
    
    # Print LaTeX table
    print("\\begin{table}[ht]")
    print("\\centering")
    print("\\caption{Instrumentation used in each deployment, including sensor model, depth, sampling interval, and measured parameters. All sensors were manufactured by Sea-Bird Scientific\\protect\\footnotemark.}")
    print("\\label{tab:instruments}")
    print("\\begin{tabular}{llllll}")
    print("\\toprule")
    print("\\textbf{Deployment} & \\textbf{Year} & \\textbf{Model} & \\textbf{Depth (m)} & \\textbf{Interval} & \\textbf{Variables observed} \\\\")
    print("\\midrule")
    
    for deployment in sorted(deployment_info.keys()):
        info = deployment_info[deployment]
        year = get_year(deployment)
        model = info['instrument_model']
        sampling = info['sampling_freq']
        variables = ', '.join(sorted(info['variables']))
        
        # You'll need to add depth info from your config files
        depth = "XXXX"  # Placeholder - extract from config
        
        print(f"{deployment} & {year} & {model} & {depth} & {sampling} & {variables} \\\\")
    
    print("\\bottomrule")
    print("\\end{tabular}")
    print("\\footnotetext{\\url{https://www.seabird.com}}")
    print("\\end{table}")

# Main execution
if __name__ == "__main__":
    base_path = "/Users/yugao/UOP/ORS-processing/data/processed"
    
    print("Scanning NetCDF files for actual observations...")
    df = extract_variables_from_netcdf_files(base_path)
    
    print(f"\nFound {len(df)} NetCDF files")
    print("\n" + "="*100)
    print("DETAILED OBSERVATION INVENTORY")
    print("="*100)
    
    # Display detailed results
    for _, row in df.iterrows():
        print(f"\nDeployment: {row['Deployment']}")
        print(f"Instrument SN: {row['Instrument_SN']}")
        print(f"Sampling Frequency: {row['Sampling_Frequency']}")
        print(f"All Variables: {row['All_Variables']}")
        print(f"OBSERVED Variables: {row['Observed_Variables']}")
        print(f"Observed (Readable): {row['Observed_Readable']}")
        print(f"File size: {row['File_Size_MB']} MB")
        print("-" * 80)
    
    # Save detailed results
    output_file = "/Users/yugao/UOP/ORS-processing/doc/netcdf_observation_inventory.csv"
    df.to_csv(output_file, index=False)
    print(f"\nDetailed inventory saved to: {output_file}")
    
    # Create LaTeX table
    print("\n" + "="*100)
    print("LATEX TABLE WITH ACTUAL OBSERVATIONS")
    print("="*100)
    create_latex_table(df)
    
    # Summary by deployment
    print("\n" + "="*100)
    print("SUMMARY BY DEPLOYMENT")
    print("="*100)
    
    summary = df.groupby('Deployment').agg({
        'Sampling_Frequency': 'first',
        'Observed_Readable': lambda x: ', '.join(set(' '.join(x).split(', '))),
        'Observed_Count': 'mean'
    }).round(1)
    
    print(summary.to_string())