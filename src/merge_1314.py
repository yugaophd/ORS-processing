# %%
# merge stratus 13 and stratus 14
# stratus 14-10600 was chosen for closer match  with stratus 15
# assess the overlap/difference between the stratus 14-10600 and 13-1873, 1875.

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
project_name = 'stratus'
project_number = 13 # the project number of the last merged dataset

case_name0 = f'{project_name}{project_number}'
instrument0_1 = '1875' # last merged dataset

case_name1 = f'{project_name}{project_number+1}'
instrument1_1 = '10600'
instrument1_2 = '10601'

# store the results in the doc folder of the latter case

doc = f'/Users/yugao/UOP/ORS-processing/doc/{project_name}/{project_number+1}'

print(f'Examining overlap between {case_name0} and {case_name1}')

# %%
# merged dataset
merged_dir = '/Users/yugao/UOP/ORS-processing/data/processed/merged_stratus'
ds0_instrument1 = xr.open_dataset(f'{merged_dir}/merged_stratus12_to_stratus{project_number}.nc')

# stratus 14 
processed_dir = '/Users/yugao/UOP/ORS-processing/data/processed'
ds1_instrument1 = xr.open_dataset(f'{processed_dir}/{case_name1}/{case_name1}_{instrument1_1}_cleaned.nc')
ds1_instrument2 = xr.open_dataset(f'{processed_dir}/{case_name1}/{case_name1}_{instrument1_2}_cleaned.nc')

# %%
# resample/average stratus 14
# stratus 13 and 14 have different sampling frequency
# so we need to resample/average stratus 14 to assess the difference

# Upsample Stratus 14 using linear interpolation
ds1_1_resampled = ds1_instrument1.resample(time='30min').mean()
ds1_2_resampled = ds1_instrument2.resample(time='30min').mean()
ds0_instrument1['time'] = ds0_instrument1.time.dt.round('30min')

# %%
# merge after assessing the stats stratus 13 and stratus 14 in time
# Ensure both datasets cover the same time period for a fair comparison

# Determine overlap window and extend by 2 hours
variable = 'temp'  # Specify variable to compare
overlap_start = max(ds0_instrument1.time.min(), ds1_instrument2.time.min(), ds1_instrument1.time.min())
overlap_end = min(ds0_instrument1.time.max(), ds1_instrument2.time.max(), ds1_instrument1.time.max())

extended_start = overlap_start  #- pd.Timedelta(hours=2)
extended_end = overlap_end #- pd.Timedelta(hours=2)

# %%
# Select data for plotting
sel0_1 = ds0_instrument1.sel(time=slice(extended_start, extended_end))[variable]
sel1_1 = ds1_1_resampled.sel(time=slice(extended_start, extended_end))[variable]
sel1_2 = ds1_2_resampled.sel(time=slice(extended_start, extended_end))[variable]

difference1 = sel1_1 - sel0_1
difference2 = sel1_2 - sel0_1
label1 = f'difference between {case_name0} - {instrument0_1} and {case_name1} - {instrument1_1}'
label2 = f'difference between {case_name0} - {instrument0_1} and {case_name1} - {instrument1_2}'

# %%
# Plotting
# Define figure and subplots
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))  # Two subplots in one column

# Plotting on the first subplot
ax1.plot(sel0_1.time, sel0_1, label=f'{case_name0} - {instrument0_1}')
ax1.plot(sel1_2.time, sel1_2, label=f'{case_name0} - {instrument1_2}')
ax1.plot(sel1_1.time, sel1_1, label=f'{case_name1} - {instrument1_1}')
ax1.set_title('Overlapping Observations with Context')
ax1.set_xlabel('Time')
ax1.set_ylabel(variable)
ax1.legend()
ax1.grid(True)  # Optionally add grid for better readability

# Plotting on the second subplot
ax2.plot(difference1.time, difference1, '*', color = 'magenta', label=label1)
ax2.plot(difference2.time, difference2, 'x', color = 'black', label=label2)
ax2.set_title(f'Difference Comparison')  # Title for the difference comparison
ax2.set_xlabel('Time')
ax2.set_ylabel(f'Difference in {variable}')
ax2.legend()
ax2.grid(True)

# Save the figure
plt.tight_layout()  # Adjust subplots to fit into figure area nicely
plt.savefig(f'{doc}/overlap_{case_name0}_and_{case_name1}.png')


# %%
# the unsampled stratus 14 should have the sampling frequency as 12/13
# determine the optimal merging time point based on the minimum standard deviation
# of the difference between the two datasets Calculate differences
if difference1.time.size > 0:
    difference = ds0_instrument1[variable] - ds1_1_resampled[variable]

    # Convert to DataFrame for easier manipulation
    diff_df = difference.to_dataframe(name='temp_difference')

    # Calculate rolling statistics with a window of 24 hours
    rolling_stats = diff_df['temp_difference'].rolling('6h').agg(['mean', 'std', 'median'])

    # Optionally, find the time point with the minimum mean or median absolute deviation
    min_mean_time = rolling_stats['mean'].idxmin()

    print(f"Optimal merging time point based on minimum mean is: {min_mean_time}")

    # Select data from each dataset up to and including the optimal merging time point

    ds0_merge = ds0_instrument1.sel(time=slice(None, min_mean_time))
    ds1_merge = ds1_1_resampled.sel(time=slice(min_mean_time, None))

    # Concatenate the two datasets at the merging point
    # Step 1: Concatenate and sort datasets
    merged_dataset = xr.concat([ds0_merge, ds1_merge], dim="time")
    merged_dataset = merged_dataset.sortby("time")
# %%
# data attributes

# Copy attributes from the first dataset and prepare to modify them
merged_dataset.attrs = ds0_merge.attrs.copy()

# Data source is the second dataset
ds_source = ds1_merge

# append the merging point to the merged dataset
merge_point = min_mean_time
existing = str(merged_dataset.attrs.get('merge_point', 'NaT'))
merged_dataset.attrs['merge_point'] = f"{existing}, {merge_point}" if existing else merge_point

# Define attributes to be appended from the second dataset
attrs_to_append = ['deployment', 'instrument_SN', 'instrument_model',
                    'latitude_anchor_survey', 'longitude_anchor_survey', 
                    'global_wmo_platform_code', 'platform_start_year',
                    'platform_water_depth_m', 'platform_watch_circle_nm',
                    'platform_deck_height_cm', 'platform_anchor_times',
                    'platform_data_start_time',
                    'platform_anchor_over_time', 
                    'platform_anchor_release_time',
                    ]

# Append new values from the second dataset
for attr in attrs_to_append:
    value = ds_source.attrs.get(attr, 'Unknown')
    existing = str(merged_dataset.attrs.get(attr, 'Unknown'))
    merged_dataset.attrs[attr] = f"{existing}, {value}" if existing else value

# Define attributes to be deleted
attrs_to_delete = ['platform_deployment_number',
    'platform_deployment_number', 'platform_data_end_time'
    'platform_duration', 'instrument_firmware_version', 'inputfileheader']

# Perform deletions
for attr in attrs_to_delete:
    merged_dataset.attrs.pop(attr, None)

# Update time attributes based on the time coverage of the merged dataset
merged_dataset.attrs['time_coverage_start'] = pd.to_datetime(merged_dataset.time.min().values).strftime('%Y-%m-%dT%H:%M:%SZ')
merged_dataset.attrs['time_coverage_end'] = pd.to_datetime(merged_dataset.time.max().values).strftime('%Y-%m-%dT%H:%M:%SZ')

merged_dataset.attrs

#%%
# Save the merged dataset
merged_data_dir = '/Users/yugao/UOP/ORS-processing/data/processed/merged_stratus'
merged_dataset.to_netcdf(f'{merged_data_dir}/merged_stratus12_to_{case_name1}.nc')

print(f"Merging completed. Dataset saved to merged_stratus12_to_{case_name1}.nc")

# %%
# verify the merging point
temperature = merged_dataset['temp'].sel(time=slice(extended_start, extended_end))[:]

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
plt.savefig(f'{doc}/merge_point_{case_name0}_and_{case_name1}.png')

# Show the plot
# plt.show()

# %%
# plot the merged dataset
# Extract variables
cond = merged_dataset['cond']
sal = merged_dataset['sal']
temp = merged_dataset['temp']
press = merged_dataset['press']
abssal = merged_dataset['abssal']

# Create a figure with multiple subplots
fig, axs = plt.subplots(5, 1, figsize=(12, 20), sharex=True)  # Adjust figsize to better fit your screen or document

# Plot each variable
axs[0].plot(cond.time, cond, label='Conductivity', color='blue')
axs[1].plot(sal.time, sal, label='Salinity', color='green')
axs[2].plot(temp.time, temp, label='Temperature', color='red')
axs[3].plot(press.time, press, label='Pressure', color='purple')
axs[4].plot(abssal.time, abssal, label='Absolute Salinity', color='orange')

# Set titles for each subplot
axs[0].set_title('Conductivity Over Time')
axs[1].set_title('Salinity Over Time')
axs[2].set_title('Temperature Over Time')
axs[3].set_title('Pressure Over Time')
axs[4].set_title('Absolute Salinity Over Time')

# Add labels and grid
for ax in axs:
    ax.set_ylabel('Value')
    ax.legend()
    ax.grid(True)

# Set common X-axis label
axs[4].set_xlabel('Time')

# Show the plot
plt.tight_layout()  # Adjust subplots to fit into the figure area nicely

# save the figure
plt.savefig(f'{doc}/merged_dataset_{case_name0}_and_{case_name1}.png')


# %%
# verify the merged dataset
merged_data_dir = '/Users/yugao/UOP/ORS-processing/data/processed/merged_stratus'
merged_dataset = xr.open_dataset(f'{merged_data_dir}/merged_stratus12_to_{case_name1}.nc')

# %%
merged_dataset.time.plot()

