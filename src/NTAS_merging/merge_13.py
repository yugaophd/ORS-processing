# %%
# Found overlap between the two datasets
# merge at the point where the two datasets have minimal differences in the overlapping period
# Chose NTAS12-1877 and NTAS13-2323 for merging

# Load necessary libraries
import os
import pandas as pd
import xarray as xr
import matplotlib.pyplot as plt
from qc_function import remove_spikes, compute_diff_stats

# Define case names and instrument serial numbers

version = 'v1'

# store the results in the doc folder of the latter case
project_name = 'NTAS'
project_number = 12 # the project number of the last merged dataset

# store the results in the doc folder of the latter case
case_name0 = f'{project_name}{project_number}'
instrument0_1 = '1877' # last merged dataset

case_name1 = f'{project_name}{project_number+1}'
instrument1_1 = '2323'
instrument1_2 = '2324'

# store the results in the doc folder of the latter case

doc = f'/Users/yugao/UOP/ORS-processing/doc/{project_name}/{project_number+1}'
img = f'/Users/yugao/UOP/ORS-processing/img'

print(f'Examining overlap between {case_name0} and {case_name1}')

# %%
# merged dataset
merged_dir = '/Users/Shared/ORS/DEEP_TS/NTAS/merged_NTAS'
ds0_instrument1 = xr.open_dataset(f'{merged_dir}/merged_NTAS11_to_NTAS{project_number}.nc')

# NTAS 13
processed_dir = '/Users/Shared/ORS/DEEP_TS/NTAS'
ds1_instrument1 = xr.open_dataset(f'{processed_dir}/{case_name1}/{version}/{case_name1}_{instrument1_1}_cleaned.nc')
ds1_instrument2 = xr.open_dataset(f'{processed_dir}/{case_name1}/{version}/{case_name1}_{instrument1_2}_cleaned.nc')

# %%
# No resample/average NTAS 13
# NTAS 13 and 14 have different sampling frequency
# so we need to resample/average NTAS 14 to assess the difference

# Upsample NTAS 13 using linear interpolation
ds1_resampled1 = ds1_instrument1 #.resample(time='30min').mean()
ds1_resampled2 = ds1_instrument2 #.resample(time='30min').mean()
# ds0_instrument1['time'] = ds0_instrument1.time.dt.round('30min')

# %%

# Determine overlap window and extend by 2 hours
variable = 'sea_water_temperature'  # Specify variable to compare

overlap_start = max(ds0_instrument1.time.min(), ds1_resampled2.time.min(), ds1_resampled1.time.min())
overlap_end = min(ds0_instrument1.time.max(), ds1_resampled2.time.max(), ds1_resampled1.time.max())

if overlap_start >= overlap_end:
    print('No overlap between the two datasets.')
    
    # Select data from each dataset up to and including the optimal merging time point
    ds0_merge = ds0_instrument1
    ds1_merge = ds1_resampled1
    
    # no overlap, the merge point is the start of the second dataset
    # Get the timestamp from the first time value of the second dataset
    merge_point = pd.to_datetime(ds1_merge.time[0].values).strftime('%Y-%m-%dT%H:%M:%SZ')
    
    # Define min_mean_time for plotting (this is the missing line)
    min_mean_time = pd.to_datetime(merge_point)

    # Merge the datasets aligning by 'time' dimension and filling gaps with NaNs
    merged_dataset = xr.concat([ds0_merge, ds1_merge], dim="time")
    merged_dataset = merged_dataset.sortby("time")
    
    # no overlap, the merge point is the start of the second dataset
    # Get the timestamp from the first time value of the second dataset
    merge_point = pd.to_datetime(ds1_merge.time[0].values).strftime('%Y-%m-%dT%H:%M:%SZ')


    # Plotting
    extended_start = overlap_start - pd.Timedelta(hours=120)
    extended_end = overlap_end + pd.Timedelta(hours=120)

    # Select data for plotting
    sel0_1 = ds0_instrument1.sel(time=slice(extended_start, extended_end))[variable]
    sel1_1 = ds1_resampled1.sel(time=slice(extended_start, extended_end))[variable]
    sel1_2 = ds1_resampled2.sel(time=slice(extended_start, extended_end))[variable]

    # Define figure and subplots
    fig, ax1 = plt.subplots(1, 1, figsize=(10, 8))  # Two subplots in one column

    # Plotting on the first subplot
    ax1.plot(sel0_1.time, sel0_1, label=f'{case_name0} - {instrument0_1}')
    ax1.plot(sel1_1.time, sel1_1, label=f'{case_name1} - {instrument1_1}')
    ax1.plot(sel1_2.time, sel1_2, label=f'{case_name1} - {instrument1_2}')
    ax1.set_title('Overlapping Observations with Context')
    ax1.set_xlabel('Time')
    ax1.set_ylabel(variable)
    ax1.legend()
    ax1.grid(True)  # Optionally add grid for better readability

    # Save the figure
    plt.tight_layout()  # Adjust subplots to fit into figure area nicely
    plt.savefig(f'{img}/overlap_{case_name0}_and_{case_name1}.png')
    
else:
    print(f'Overlap between the two datasets found from {overlap_start} to {overlap_end}.')
    extended_start = overlap_start #- pd.Timedelta(hours=1)
    extended_end = overlap_end #- pd.Timedelta(hours=1)

    # Select data for plotting
    sel0_1 = ds0_instrument1.sel(time=slice(extended_start, extended_end))[variable]

    sel1_1 = ds1_resampled1.sel(time=slice(extended_start, extended_end))[variable]
    sel1_2 = ds1_instrument2.sel(time=slice(extended_start, extended_end))[variable]

    # assess the difference between the two datasets

    difference1 = sel0_1 - sel1_1
    difference2 = sel0_1 - sel1_2
    label1 = f'difference between {case_name0} - {instrument1_1} and {case_name1} - {instrument0_1}'
    label2 = f'difference between {case_name0} - {instrument1_2} and {case_name1} - {instrument0_1}'

    # Plotting
    # Define figure and subplots
    fig, (ax1) = plt.subplots(1, 1, figsize=(10, 10))  # Two subplots in one column

    # Plotting on the first subplot
    ax1.plot(sel0_1.time, sel0_1, label=f'{case_name0} - {instrument0_1}')
    ax1.plot(sel1_2.time, sel1_2, label=f'{case_name0} - {instrument1_2}')
    ax1.plot(sel1_1.time, sel1_1, label=f'{case_name1} - {instrument1_1}')
    ax1.set_title('Overlapping Observations with Context')
    ax1.set_xlabel('Time')
    ax1.set_ylabel(variable)
    ax1.legend()
    ax1.grid(True)  # Optionally add grid for better readability
    
    # Save the figure
    plt.tight_layout()  # Adjust subplots to fit into figure area nicely
    plt.savefig(f'{img}/overlap_{case_name0}_and_{case_name1}.png')

    difference = ds0_instrument1[variable] - ds1_resampled1[variable]

    # Convert to DataFrame for easier manipulation
    diff_df = difference.to_dataframe(name='temp_difference')

    # Calculate rolling statistics with a window of 24 hours
    rolling_stats = diff_df['temp_difference'].rolling('6h').agg(['mean', 'std', 'median'])

    # Optionally, find the time point with the minimum mean or median absolute deviation
    min_mean_time = rolling_stats['mean'].idxmin()
    merge_point = min_mean_time

    print(f"Optimal merging time point based on minimum mean is: {min_mean_time}")

    # Select data from each dataset up to and including the optimal merging time point

    ds0_merge = ds0_instrument1.sel(time=slice(None, min_mean_time))
    ds1_merge = ds1_resampled1.sel(time=slice(min_mean_time, None))

    # Concatenate the two datasets at the merging point
    merged_dataset = xr.concat([ds0_merge, ds1_merge], dim='time')

    # Optionally, sort by time in case of any misalignment
    merged_dataset = merged_dataset.sortby('time')


# %%
# data attributes

# Copy attributes from the first dataset and prepare to modify them
merged_dataset.attrs = ds0_merge.attrs.copy()

# Data source is the second dataset
ds_source = ds1_merge
if ds_source.attrs['platform_buoy_recovery_time'] == '':
    ds_source.attrs['platform_buoy_recovery_time'] = 'missing'
    
if ds_source.attrs['platform_anchor_over_time'] == '':
    ds_source.attrs['platform_anchor_over_time'] = 'missing'
# Standardize the new merge point timestamp
merge_point = pd.to_datetime(min_mean_time).strftime('%Y-%m-%dT%H:%M:%SZ')

# Get existing merge points if any
existing = merged_dataset.attrs.get('merge_point', None)

if existing is None or existing == 'None':
    merged_dataset.attrs['merge_point'] = merge_point
else:
    # Standardize all timestamps in the existing merge points
    points = existing.split(', ')
    standardized = [pd.to_datetime(p).strftime('%Y-%m-%dT%H:%M:%SZ') for p in points if p != 'None']
    standardized.append(merge_point)
    merged_dataset.attrs['merge_point'] = ', '.join(standardized)
# Define attributes to be appended from the second dataset
from metadata_merger import attrs_to_append, attrs_to_delete, attr_alternatives

# Append new values from the second dataset
for attr in attrs_to_append:
    # get the value from the alternative attribute name
    existing = str(merged_dataset.attrs.get(attr))
    value = ds_source.attrs.get(attr)
    merged_dataset.attrs[attr] = f"{existing}, {value}" if existing else value
    
        # use alternative attribute name if the original attribute is not found
    if value is None:
        for alt_attr, standard_attr in attr_alternatives.items():
            if alt_attr in ds_source.attrs:
                merged_dataset.attrs[attr] = f"{existing}, {ds_source.attrs[alt_attr]}" if existing else ds_source.attrs[alt_attr]

# %%
# Append variable attributes from the source dataset to the merged dataset
from util import append_variable_attributes

merged_dataset = append_variable_attributes(ds_source, merged_dataset)

# Update time attributes based on the time coverage of the merged dataset
merged_dataset.attrs['time_coverage_start'] = pd.to_datetime(merged_dataset.time.min().values).strftime('%Y-%m-%dT%H:%M:%SZ')
merged_dataset.attrs['time_coverage_end'] = pd.to_datetime(merged_dataset.time.max().values).strftime('%Y-%m-%dT%H:%M:%SZ')

# update geospatial bounds
from metadata_merger import update_geospatial_bounds

# Update the geospatial bounds to get the true min/max values
merged_dataset = update_geospatial_bounds(merged_dataset)

merged_dataset.attrs


#%%
# Save the merged dataset
merged_dataset.attrs['platform_code'] = f"NTAS"
merged_data_dir = '/Users/yugao/UOP/ORS-processing/data/processed/merged_NTAS'
merged_dataset.to_netcdf(f'{merged_data_dir}/merged_NTAS11_to_{case_name1}.nc')

print(f"Merging completed. Dataset saved to merged_NTAS11_to_{case_name1}.nc")



# %%
# plot the merged dataset
from plot_function import plot_merged_dataset

# Define the image directory
img = '/Users/yugao/UOP/ORS-processing/img/'
# After merging datasets, use the function to create the plot
plot_merged_dataset(
    merged_dataset, 
    f'{img}/merged_dataset_{case_name0}_and_{case_name1}.png',
    case_name0=case_name0,
    case_name1=case_name1
)


# %%
# check continuous time range
merged_dataset