# %%
# Script to plot all merged {project} datasets from {project} 12 to the latest deployment.
# Creates individual plots for each merged dataset and optionally a summary plot.

import os
import xarray as xr
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from plot_function import plot_merged_dataset


def _gap_masked_line(time_values, data_values, gap_factor=10):
    """Insert NaNs at large temporal gaps so matplotlib does not connect them."""
    t = pd.to_datetime(np.asarray(time_values), utc=True).tz_localize(None)
    y = np.asarray(data_values, dtype=float)

    if len(t) < 2:
        return t, y

    dt = t[1:] - t[:-1]
    positive_dt = dt[dt > pd.Timedelta(0)]
    if len(positive_dt) == 0:
        return t, y

    threshold = positive_dt.median() * gap_factor
    break_indices = set(np.flatnonzero(dt > threshold))
    if not break_indices:
        return t, y

    out_t = []
    out_y = []
    for i, (ti, yi) in enumerate(zip(t, y)):
        out_t.append(ti)
        out_y.append(yi)
        if i in break_indices:
            out_t.append(ti + dt[i] / 2)
            out_y.append(np.nan)

    out_t = pd.to_datetime(np.asarray(out_t), utc=True).tz_localize(None)
    return out_t, np.asarray(out_y)

# %%
# Set working directory and path definitions
os.chdir('/Users/yugao/UOP/ORS-processing/src')

project = 'STRATUS'

data_dir = f'/Users/Shared/ORS/DEEP_TS/{project}/merged_{project}'  # Updated path based on your listing
img_dir = f'/Users/yugao/UOP/ORS-processing/img/{project}'

# Ensure output directories exist
os.makedirs(img_dir, exist_ok=True)

# Function to load and process all merged datasets
def load_all_merged_datasets():
    """Load all available merged {project} datasets."""
    all_datasets = []
    all_ranges = []
    
    # Search for merged files
    for file in sorted(os.listdir(data_dir)):
        if file.endswith('.nc') and file.startswith('merged'):
            try:
                # Extract case range from filename (merged_{project}XX_to_{project}XX.nc)
                parts = file.replace('.nc', '').split('_')
                if len(parts) >= 4 and parts[2] == 'to':
                    start_case = parts[1]  # {project}XX
                    end_case = parts[3]    # {project}XX
                    
                    # Load the dataset
                    ds = xr.open_dataset(os.path.join(data_dir, file))
                    print(f"Loaded merged dataset: {file}")
                    
                    all_datasets.append(ds)
                    all_ranges.append((start_case, end_case))
            except Exception as e:
                print(f"Error loading {file}: {e}")
    
    return all_datasets, all_ranges

# Plot individual merged datasets
def plot_all_merged_datasets():
    """Generate plots for all merged datasets."""
    datasets, ranges = load_all_merged_datasets()
    
    if not datasets:
        print("No merged datasets found.")
        return
    
    # Plot each individual merged dataset
    for i, (ds, case_range) in enumerate(zip(datasets, ranges)):
        start_case, end_case = case_range
        output_path = f'{img_dir}/merged_dataset_{start_case}_to_{end_case}.png' #
        # merged_dataset_{case_name0}_and_{case_name1}.png
        
        print(f"Plotting {start_case} to {end_case} merged data...")
        try:
            plot_merged_dataset(
                ds, 
                output_path,
                case_name0=start_case,
                case_name1=end_case
            )
        except Exception as e:
            print(f"Error plotting {start_case} to {end_case}: {e}")
    
    # Create a summary plot showing key variables from the latest merged dataset
    if datasets:
        create_latest_summary_plot(datasets[-1], ranges[-1])

# Create a comprehensive plot of the latest merged dataset
def create_latest_summary_plot(dataset, case_range):
    """Create a summary plot of the latest merged dataset with all deployments."""
    start_case, end_case = case_range
    output_path = f'{img_dir}/latest_merged_summary_{end_case}.png'
    
    try:
        # Create a special plot with annotated merge points
        plot_merged_dataset(
            dataset, 
            output_path,
            case_name0=start_case,
            case_name1=end_case,
            figsize=(15, 25),  # Larger figure for better visibility
            annotate_merge_points=True  # Show merge point labels
        )
        print(f"Latest summary plot saved to {output_path}")
    except Exception as e:
        print(f"Error creating latest summary plot: {e}")

# Optional function to create a composite plot comparing key variables across different merged sets
def create_comparison_plots(datasets, ranges):
    """Create comparison plots of temperature and salinity across different merged datasets."""
    if not datasets:
        return
        
    # Variables to compare
    variables = ['sea_water_temperature']
    titles = ['Sea Water Temperature']
    units = ['°C']
    
    # Create a plot for each variable
    for var_idx, var_name in enumerate(variables):
        if var_name not in datasets[-1]:
            print(f"Variable {var_name} not found in datasets")
            continue
            
        fig, ax = plt.subplots(figsize=(14, 8))
        
        # Plot the variable from selected merged datasets (e.g., every other one to reduce clutter)
        for i in range(0, len(datasets), 2):  # Plot every other dataset to reduce clutter
            ds = datasets[i]
            start_case, end_case = ranges[i]
            if var_name in ds:
                label = f"{end_case}"
                plot_t, plot_v = _gap_masked_line(ds.time.values, ds[var_name].values)
                ax.plot(plot_t, plot_v, label=label, linewidth=1.5)
        
        # Add the latest/most complete dataset
        label = f"{ranges[-1][1]} (Latest)"
        latest_t, latest_v = _gap_masked_line(datasets[-1].time.values, datasets[-1][var_name].values)
        ax.plot(latest_t, latest_v, 
                label=label, linewidth=2.5, color='black')
        
        # Set title and labels
        ax.set_title(f'{titles[var_idx]} Comparison Across Merged Datasets', fontsize=14)
        ax.set_xlabel('Time', fontsize=12)
        ax.set_ylabel(f'{titles[var_idx]} ({units[var_idx]})', fontsize=12)
        ax.grid(True, alpha=0.3)
        ax.legend(loc='best', fontsize=10)
        
        # Save figure
        comparison_path = f'{img_dir}/comparison_{var_name}.png'
        plt.tight_layout()
        plt.savefig(comparison_path, dpi=300, bbox_inches='tight')
        print(f"Comparison plot for {var_name} saved to {comparison_path}")
        plt.close()

if __name__ == "__main__":
    print("Plotting all merged {project} datasets...")
    datasets, ranges = load_all_merged_datasets()
    
    # Plot individual datasets
    plot_all_merged_datasets()
    
    # Create comparison plots
    create_comparison_plots(datasets, ranges)
    
    print("Done!")