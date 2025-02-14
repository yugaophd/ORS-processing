import numpy as np
import pandas as pd
import xarray as xr

def remove_spikes(data, window_size=12, std_dev_factor=3):
    """
    Removes spikes from a given data series based on a rolling mean and standard deviation.
    
    Parameters:
    - data (pd.Series): The data series from which to remove spikes.
    - window_size (int): The size of the rolling window, in number of data points.
    - std_dev_factor (int): The number of standard deviations to use as a threshold for spike detection.
    
    Returns:
    - pd.Series: Cleaned data with spikes replaced by NaN.
    - int: The number of spikes removed.
    """
    rolling_mean = data.rolling(time=window_size, center=True).mean()
    rolling_std = data.rolling(time=window_size, center=True).std()
    
    # Define spikes as points where the deviation from the mean exceeds the threshold
    spike_mask = np.abs(data - rolling_mean) > std_dev_factor * rolling_std
    data_cleaned = data.where(~spike_mask, np.nan)  # Replace spikes with NaN

    # Calculate the number of spikes removed
    num_spikes_removed = spike_mask.sum()
    
    return data_cleaned, num_spikes_removed


import xarray as xr
import numpy as np
import pandas as pd

def compute_diff_stats(ds0, ds1, variables):
    """
    Computes the mean and standard deviation of the difference between two datasets
    for specified variables.
    
    Parameters:
    - ds0 (xarray.Dataset): First dataset
    - ds1 (xarray.Dataset): Second dataset
    - variables (list): List of variable names to compare
    
    Returns:
    - dict: Dictionary with variable names as keys and tuples of (mean_diff, std_diff) as values
    """
    results = {}
    
    for var in variables:
        if var in ds0 and var in ds1:
            # Convert xarray DataArrays to pandas Series
            data1 = ds0[var].to_series()
            data2 = ds1[var].to_series()
            
            # Compute differences for non-NaN values
            valid_mask = ~data1.isna() & ~data2.isna()
            differences = data1[valid_mask] - data2[valid_mask]
            
            mean_diff = differences.mean()
            std_diff = differences.std()
            
            results[var] = (mean_diff, std_diff)
        else:
            print(f"Warning: Variable '{var}' not found in both datasets.")
    
    return results

import pandas as pd
import os

def export_diff_stats(sensor1_data, sensor2_data, instrument_number1, instrument_number2,
                    output_dir, project_name, project_number):
    """
    Export sensor statistics and their differences as LaTeX tables.
    
    Parameters:
        sensor1_data (dict): Dictionary containing data for sensor 1 (mean, std).
        sensor2_data (dict): Dictionary containing data for sensor 2 (mean, std).
        instrument (str): Identifier for the instrument.
        output_dir (str): Directory path to save the LaTeX files.
    """
    # Ensure the output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    # Create DataFrames
    df1 = pd.DataFrame(sensor1_data)
    df2 = pd.DataFrame(sensor2_data)
    
    # Calculate differences
    diff_means = df1['mean'] - df2['mean']
    diff_stds = (df1['std']**2 + df2['std']**2)**0.5  # Combined standard deviation
    qc_threshold = 3 * diff_stds  # Quality control threshold

    # Prepare LaTeX output
    tex_path = os.path.join(output_dir, f'diff_stats.tex')
    with open(tex_path, 'w') as f:
        # Table 1: Statistics for individual sensors
        f.write("\\begin{table}[h]\n\\centering\n")
        f.write("\\begin{tabular}{|c|c|c|c|c|}\n\\hline\n")
        f.write(f"Variable & \\multicolumn{{2}}{{c|}}{{SN {instrument_number1}}} & \\multicolumn{{2}}{{c|}}{{SN {instrument_number2}}} \\\\\n")

        f.write("& Mean & Std Dev & Mean & Std Dev \\\\\n\\hline\n")
        for var in df1.index:
            f.write(f"{var} & {df1.at[var, 'mean']:.5f} & {df1.at[var, 'std']:.5f} & {df2.at[var, 'mean']:.5f} & {df2.at[var, 'std']:.5f} \\\\\n")
        f.write("\\hline\n\\end{tabular}\n")
        f.write(f"\\caption{{Statistics for individual sensors on {project_name} {project_number}}}\n")

        f.write("\\end{table}\n\n")

        # Table 2: Difference statistics
        f.write("\\begin{table}[h]\n\\centering\n")
        f.write("\\begin{tabular}{|c|c|c|c|}\n\\hline\n")
        f.write("Variable & Mean Diff & Std Diff & QC Threshold \\\\\n\\hline\n")
        for var in diff_means.index:
            f.write(f"{var} & {diff_means[var]:.5f} & {diff_stds[var]:.5f} & {qc_threshold[var]:.5f} \\\\\n")
        f.write("\\hline\n\\end{tabular}\n")
        # f.write(f"\\caption{{Difference statistics for the two sensors on {project_name} {project_number}. 
        #         The mean difference between instruments is a measure of expected accuracy (systematic bias). 
        #         The standard deviation of the difference is a measure of precision (random variability). 
        #         The QC Threshold is set at 3 times the precision value for outlier detection.}}\n")
        f.write(
        f"\\caption{{Difference statistics for the two sensors on {project_name} {project_number}. The mean difference between instruments is a measure of expected accuracy (systematic bias). The standard deviation of the difference is a measure of precision (random variability). The QC Threshold is set at 3 times the precision value for outlier detection.}}\n"
)

        f.write("\\end{table}\n")
    
    print(f"LaTeX tables exported to {tex_path}")


import matplotlib.pyplot as plt
import xarray as xr
import numpy as np

def create_hitl_catalog(original_ds, qc_ds, deployment_id, instrument_number, output_dir='../img'):
    """
    Create a catalog of original and QC plots for HITL quality control on the same panel.
    
    Parameters:
    - original_ds: xarray Dataset containing original data
    - qc_ds: xarray Dataset containing quality controlled data
    - deployment_id: string identifier for the deployment
    - output_dir: directory to save the plots
    """
    variables = ['temp', 'sal', 'abssal', 'cond', 'press']
    
    fig, axs = plt.subplots(5, 1, figsize=(15, 25))
    fig.suptitle(f"Deployment {deployment_id}: Original vs QC Data", fontsize=16)
    
    for i, var in enumerate(variables):
        # Plot original data
        original_ds[var].plot(ax=axs[i], label='Original', alpha=0.7)
        
        # Plot QC data
        qc_ds[var].plot(ax=axs[i], label='QC', alpha=0.7)
        
        # Highlight removed points
        mask = np.isnan(qc_ds[var]) & ~np.isnan(original_ds[var])
        if np.any(mask):
            axs[i].plot(original_ds[var].where(mask).time, original_ds[var].where(mask), 
                        'rx', label='Removed', markersize=4)
        
        axs[i].set_title(f"{var}")
        axs[i].legend()
        
        # Add textbox with statistics
        original_mean = original_ds[var].mean().values
        original_std = original_ds[var].std().values
        qc_mean = qc_ds[var].mean().values
        qc_std = qc_ds[var].std().values
        
        stats_text = f"Original Mean: {original_mean:.2f}, Std: {original_std:.2f}\n"
        stats_text += f"QC Mean: {qc_mean:.2f}, Std: {qc_std:.2f}\n"
        stats_text += f"% Removed: {(mask.sum() / mask.size * 100):.2f}%"
        
        axs[i].text(0.05, 0.95, stats_text, transform=axs[i].transAxes, 
                    verticalalignment='top', bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
    
    plt.tight_layout()
    plt.savefig(f"{output_dir}/{deployment_id}_{instrument_number}_hitl_catalog.png", dpi=300, bbox_inches='tight')
    plt.close()

import pandas as pd
import xarray as xr

def add_sensor_stats_to_variables(ds0, ds1, variables):
    
    """
    Add sensor statistics as attributes to specific variables in the datasets
    """
    
    for var in variables:
        # if var in df1.columns and var in df2.columns:
        print(f"Processing variable: {var}")
        # Calculate standard deviation for each sensor
        if var in ds0 and var in ds1:
            # Calculate statistics
            std0 = float(ds0[var].std())
            std1 = float(ds1[var].std())
            combined_std = float((std0**2 + std1**2)**0.5)
            mean_diff = float((ds0[var] - ds1[var]).mean())
            
            # Add attributes to ds0
            if var in ds0:
                ds0[var].attrs['std_single_sensor'] = std0
                ds0[var].attrs['std_single_sensor_comment'] = "Standard deviation of the time series obtained from a single sensor during the deployment."
                ds0[var].attrs['std_sensor_diff'] = combined_std
                ds0[var].attrs['std_sensor_diff_comment'] = "Standard deviation of the difference between two co-located sensors during the deployment."
                ds0[var].attrs['mean_sensor_diff'] = mean_diff
                ds0[var].attrs['mean_sensor_diff_comment'] = "Mean of the difference between two co-located sensors during the deployment."
            
            # Add attributes to ds1
            if var in ds1:
                ds1[var].attrs['std_single_sensor'] = std1
                ds1[var].attrs['std_single_sensor_comment'] = "Standard deviation of the time series obtained from a single sensor during the deployment."
                ds1[var].attrs['std_sensor_diff'] = combined_std
                ds1[var].attrs['std_sensor_diff_comment'] = "Standard deviation of the difference between two co-located sensors during the deployment."
                ds1[var].attrs['mean_sensor_diff'] = mean_diff
                ds1[var].attrs['mean_sensor_diff_comment'] = "Mean of the difference between two co-located sensors during the deployment."
    
    return ds0, ds1

def standardize_ocean_variables(ds):
    """
    Standardize oceanographic variable names and attributes following OceanSITES and CF conventions.
    
    Parameters
    ----------
    ds : xarray.Dataset
        Input dataset with original variable names
        
    Returns
    -------
    xarray.Dataset
        Dataset with standardized variable names and attributes
    """
    # Dictionary mapping original names to standard names and attributes
    var_standards = {
        'cond': {
            'name': 'CNDC',
            'standard_name': 'sea_water_electrical_conductivity',
            'units': 'S/m'
        },
        'sal': {
            'name': 'PSAL',
            'standard_name': 'sea_water_practical_salinity',
            'units': '1'
        },
        'temp': {
            'name': 'TEMP',
            'standard_name': 'sea_water_temperature',
            'units': 'degC'
        },
        'abssal': {
            'name': 'ASAL',
            'standard_name': 'sea_water_absolute_salinity',
            'units': 'g/kg'
        },
        'press': {
            'name': 'PRES',
            'standard_name': 'sea_water_pressure',
            'units': 'dbar'
        }
    }
    
    # Create a copy of the dataset to avoid modifying the original
    ds_standard = ds.copy()
    
    # Rename variables and add attributes
    rename_dict = {}
    for old_name, standards in var_standards.items():
        if old_name in ds:
            rename_dict[old_name] = standards['name']
    
    # Perform renaming
    ds_standard = ds_standard.rename(rename_dict)
    
    # Add attributes
    for old_name, standards in var_standards.items():
        if old_name in ds:
            new_name = standards['name']
            ds_standard[new_name].attrs['standard_name'] = standards['standard_name']
            ds_standard[new_name].attrs['units'] = standards['units']
    
    return ds_standard
