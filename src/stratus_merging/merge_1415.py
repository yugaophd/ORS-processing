# %%
# merge stratus 12 to stratus 15
# stratus 14-10600 was chosen for closer match  with stratus 15-12257
# assess the overlap/difference between the stratus 14-10600 and 15-12257.

# Load necessary libraries
import os

# Set working directory and load datasets
os.chdir('/Users/yugao/UOP/ORS-processing/src')

import pandas as pd
import xarray as xr
import matplotlib.pyplot as plt
from qc_function import remove_spikes, compute_diff_stats

# %%
# Define case names and instrument serial numbers
version = 'v1'
project_name = 'stratus'
project_number = 14 # the project number of the last merged dataset

case_name0 = f'{project_name}{project_number}'
instrument0_1 = '10600'

case_name1 = f'{project_name}{project_number+1}'
instrument1_1 = '11394'
instrument1_2 = '12257'

# store the results in the doc folder of the latter case

doc = f'/Users/yugao/UOP/ORS-processing/doc/{project_name}/{project_number+1}'
img = f'/Users/yugao/UOP/ORS-processing/img'
print(f'Examining overlap between {case_name0} and {case_name1}')

# %%
# merged dataset
ds0_instrument1 = xr.open_dataset(f'/Users/yugao/UOP/ORS-processing/data/processed/merged_stratus/merged_stratus12_to_stratus{project_number}.nc')

# stratus 15
ds1_instrument1 = xr.open_dataset(f'/Users/yugao/UOP/ORS-processing/data/processed/{case_name1}/{version}/{case_name1}_{instrument1_1}_cleaned.nc')
ds1_instrument2 = xr.open_dataset(f'/Users/yugao/UOP/ORS-processing/data/processed/{case_name1}/{version}/{case_name1}_{instrument1_2}_cleaned.nc')


# %%
# merge after assessing the stats stratus 13 and stratus 14 in time
# Ensure both datasets cover the same time period for a fair comparison

# Determine overlap window and extend by 2 hours
variable = 'sea_water_temperature'  # Specify variable to compare
overlap_start = max(ds0_instrument1.time.min(), ds1_instrument2.time.min(), ds1_instrument1.time.min())
overlap_end = min(ds0_instrument1.time.max(), ds1_instrument2.time.max(), ds1_instrument1.time.max())

extended_start = overlap_start - pd.Timedelta(hours=4)
extended_end = overlap_end - pd.Timedelta(hours=4)

# Select data for plotting
sel0_1 = ds0_instrument1.sel(time=slice(extended_start, extended_end))[variable]
sel1_2 = ds1_instrument2.sel(time=slice(extended_start, extended_end))[variable]
sel1_1 = ds1_instrument1.sel(time=slice(extended_start, extended_end))[variable]

# %%
# resample/average stratus 14
# stratus 15 and merged dataset have different sampling frequency
# so we need to resample/average stratus 14 to assess the difference

# Average higher sampling rate data 
ds1_1_upsampled = ds1_instrument1.resample(time='30min').mean()
ds1_2_upsampled = ds1_instrument2.resample(time='30min').mean()

# %%
# Ensure that all data are aligned and cover the same duration
# select the data for merge point calculation
sel1_1_upsampled = ds1_1_upsampled.sel(time=slice(extended_start, extended_end))
sel1_2_upsampled = ds1_2_upsampled.sel(time=slice(extended_start, extended_end))
sel0_1_aligned = sel0_1.sel(time=slice(extended_start, extended_end))

difference1 = sel1_1_upsampled - sel0_1_aligned
difference2 = sel1_2_upsampled - sel0_1_aligned
label1 = f'difference between {case_name0} - {instrument0_1} and {case_name1} - {instrument1_1}'
label2 = f'difference between {case_name0} - {instrument0_1} and {case_name1} - {instrument1_2}'

# %%
# Plotting
# Define figure and subplots
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))  # Two subplots in one column

# Plotting on the first subplot
ax1.plot(sel0_1.time, sel0_1, label=f'{case_name0} - {instrument0_1}')
ax1.plot(sel1_1_upsampled.time, sel1_1_upsampled.sea_water_temperature, label=f'{case_name1} - {instrument1_1}')
ax1.plot(sel1_2_upsampled.time, sel1_2_upsampled.sea_water_temperature, label=f'{case_name1} - {instrument1_2}')
ax1.set_title('Overlapping Observations')
ax1.set_xlabel('Time')
ax1.set_ylabel(variable)
ax1.legend()
ax1.grid(True)  # Optionally add grid for better readability

# Plotting on the second subplot
ax2.plot(difference1.time, difference1.sea_water_temperature, '*', color = 'magenta', label=label1)
ax2.plot(difference2.time, difference2.sea_water_temperature, 'x', color = 'black', label=label2)
ax2.set_title(f'Difference Comparison')  # Title for the difference comparison
ax2.set_xlabel('Time')
ax2.set_ylabel(f'Difference in {variable}')
ax2.legend()
ax2.grid(True)

# Save the figure
plt.tight_layout()  # Adjust subplots to fit into figure area nicely
plt.savefig(f'{img}/overlap_{case_name0}_and_{case_name1}.png')

# %%
# the unsampled stratus 15 should have the sampling frequency as 12/13
# determine the optimal merging time point based on the minimum standard deviation
# of the difference between the two datasets Calculate differences
if difference1.time.size >0:
    
    difference = sel0_1_aligned - sel1_2_upsampled
    
    # Convert to DataFrame for easier manipulation
    diff_df = difference.sea_water_temperature.to_dataframe(name='temp_difference')

    # Calculate rolling statistics with a window of 24 hours
    rolling_stats = diff_df['temp_difference'].rolling('6h').agg(['mean', 'std', 'median'])

    # find the time point with the minimum mean absolute deviation
    min_mean_time = rolling_stats['mean'].idxmin()
    merge_point = min_mean_time

    print(f"Optimal merging time point based on minimum mean is: {min_mean_time}")

    # Select data from each dataset up to and including the optimal merging time point

    ds0_merge = ds0_instrument1.sel(time=slice(None, min_mean_time))
    ds1_merge = ds1_2_upsampled.sel(time=slice(min_mean_time, None))

    # Concatenate the two datasets at the merging point
    merged_dataset = xr.concat([ds0_merge, ds1_merge], dim='time')


# %%
# data attributes

# Copy attributes from the first dataset and prepare to modify them
merged_dataset.attrs = ds0_merge.attrs.copy()

# Data source is the second dataset
ds_source = ds1_merge

# append the merging point to the merged dataset
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
merged_data_dir = '/Users/yugao/UOP/ORS-processing/data/processed/merged_stratus'
merged_dataset.to_netcdf(f'{merged_data_dir}/merged_stratus12_to_{case_name1}.nc')

print(f"Merging completed. Dataset saved to merged_stratus12_to_{case_name1}.nc")

# %%
# verify the merging point
temperature = merged_dataset['sea_water_temperature'].sel(time=slice(extended_start, extended_end))[:100]

# Plotting
fig, ax = plt.subplots(figsize=(12, 6))

# Plot temperature data
temperature.plot(ax=ax, color='blue', label='Merged Temperature')

# Highlight the merging point
# min_mean_time = '2024-01-01T12:00'  # Update this with the actual merging time
ax.axvline(x=min_mean_time, color='red', linestyle='--', linewidth=2, label='Merging Point')

# Add title and labels
ax.set_title('Temperature Data Before and After Merging')
ax.set_xlabel('Time')
ax.set_ylabel('Temperature (°C)')

# Add legend
ax.legend()

# Show grid
ax.grid(True)

# save the plot
plt.tight_layout()
plt.savefig(f'{img}/merge_point_{case_name0}_and_{case_name1}.png')


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
