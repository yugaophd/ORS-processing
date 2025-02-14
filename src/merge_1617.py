# %%
# merge stratus 12 to stratus 17
# chose stratus 16-10600 for smaller difference with stratus 15-11394
# assess the overlap/difference between the stratus 16-10600 and 17-11394, 12257.
# No overlap between the stratus 16-10600 and 17-11394, 12257.
# Chose 17-12257 for closer match with 18-10600.

# Load necessary libraries
import os
import pandas as pd
import xarray as xr
import matplotlib.pyplot as plt
from qc_function import remove_spikes, compute_diff_stats

# Set working directory and load datasets
os.chdir('/Users/yugao/UOP/ORS-processing/src')

# %%
# Define case names and instrument serial numbers
project_name = 'stratus'
project_number = 16 # the project number of the last merged dataset

case_name0 = f'{project_name}{project_number}'
instrument0_1 = '10600'

case_name1 = f'{project_name}{project_number+1}'
instrument1_1 = '11394'
instrument1_2 = '12257'

# store the results in the doc folder of the latter case
project_name = 'stratus'
doc = f'/Users/yugao/UOP/ORS-processing/doc/{project_name}/{project_number+1}'

print(f'Examining overlap between {case_name0} and {case_name1}')

# %%
# load datasets
# merged dataset
merged_dir = '/Users/yugao/UOP/ORS-processing/data/processed/merged_stratus'
ds0_instrument1 = xr.open_dataset(f'{merged_dir}/merged_stratus12_to_stratus{project_number}.nc')
# to be merged dataset
processed_dir = '/Users/yugao/UOP/ORS-processing/data/processed'
ds1_instrument1 = xr.open_dataset(f'{processed_dir}/{case_name1}/{case_name1}_{instrument1_1}_cleaned.nc')
ds1_instrument2 = xr.open_dataset(f'{processed_dir}/{case_name1}/{case_name1}_{instrument1_2}_cleaned.nc')

# Average higher sampling rate data to match the lower sampling rate data
ds1_resampled1 = ds1_instrument1.resample(time='30min').mean()
ds1_resampled2 = ds1_instrument2.resample(time='30min').mean()

# %%
# merge after assessing the stats 
# Ensure both datasets cover the same time period for a fair comparison

# Determine overlap window and extend by 2 hours
variable = 'temp'  # Specify variable to compare

overlap_start = max(ds0_instrument1.time.min(), ds1_resampled2.time.min(), ds1_resampled1.time.min())
overlap_end = min(ds0_instrument1.time.max(), ds1_resampled2.time.max(), ds1_resampled1.time.max())

if overlap_start >= overlap_end:
    print('No overlap between the two datasets.')
    
    # Select data from each dataset up to and including the optimal merging time point
    ds0_merge = ds0_instrument1
    ds1_merge = ds1_resampled1

    # Merge the datasets aligning by 'time' dimension and filling gaps with NaNs
    merged_ds = xr.concat([ds0_merge, ds1_merge], dim="time")
    merged_ds = merged_ds.sortby("time")
    
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
    plt.savefig(f'{doc}/overlap_{case_name0}_and_{case_name1}.png')
    
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
    plt.savefig(f'{doc}/overlap_{case_name0}_and_{case_name1}.png')

    difference = ds0_instrument1[variable] - ds1_resampled1[variable]

    # Convert to DataFrame for easier manipulation
    diff_df = difference.to_dataframe(name='temp_difference')

    # Calculate rolling statistics with a window of 24 hours
    rolling_stats = diff_df['temp_difference'].rolling('6h').agg(['mean', 'std', 'median'])

    # Optionally, find the time point with the minimum mean or median absolute deviation
    min_mean_time = rolling_stats['mean'].idxmin()

    print(f"Optimal merging time point based on minimum mean is: {min_mean_time}")

    # Select data from each dataset up to and including the optimal merging time point

    ds0_merge = ds0_instrument1.sel(time=slice(None, min_mean_time))
    ds1_merge = ds1_resampled1.sel(time=slice(min_mean_time, None))

    # Concatenate the two datasets at the merging point
    merged_ds = xr.concat([ds0_merge, ds1_merge], dim='time')

    # Optionally, sort by time in case of any misalignment
    merged_ds = merged_ds.sortby('time')


# %%
# data attributes

# Copy attributes from the first dataset and prepare to modify them
merged_ds.attrs = ds0_merge.attrs.copy()

# Data source is the second dataset
ds_source = ds1_merge

# append the merging point to the merged dataset
# define the "merge point" as the starting time of the subsequent deployment.
if overlap_end < overlap_start:
    merge_point = pd.to_datetime(ds1_merge.time[0].values).strftime('%Y-%m-%dT%H:%M:%SZ')
    merged_ds.attrs['merge_point'] = f'{merge_point}'
    merged_ds.attrs['merge_point_comment'] = f'If no overlap between the two datasets, merge at the start of the second dataset.'
    print(f"No overlap between the two datasets. Merging at the start of the second dataset.")  
else:
    merge_point = min_mean_time
    existing = str(merged_ds.attrs.get('merge_point', 'NaT'))
    merged_ds.attrs['merge_point'] = f"{existing}, {merge_point}" if existing else merge_point

# Define attributes to be deleted
attrs_to_delete = [
    # 'platform_anchor_over_time', 'platform_anchor_release_time',
    'platform_duration', 'instrument_firmware_version', 'inputfileheader']

# Perform deletions
for attr in attrs_to_delete:
    merged_ds.attrs.pop(attr, None)

# Define attributes to be appended from the second dataset
attrs_to_append = ['deployment', 'instrument_SN', 'instrument_model',
                    'latitude_anchor_survey', 'longitude_anchor_survey', 
                    'global_wmo_platform_code', 'platform_start_year',
                    'platform_water_depth_m', 'platform_watch_circle_nm',
                    'platform_deck_height_cm', 'platform_anchor_times',
                    'platform_data_start_time', 'platform_data_end_time', 
                    'platform_anchor_over_time', 'platform_anchor_release_time',
                    'platform_anchor_release_time',
                    'sensor_mean_temp', 
                    'sensor_mean_cond',
                    'sensor_mean_sal',
                    'sensor_mean_abssal',
                    'sensor_mean_press',
                    'sensor_std_temp', 
                    'sensor_std_cond',
                    'sensor_std_sal',
                    'sensor_std_abssal',
                    'sensor_std_press']

# Append new values from the second dataset
for attr in attrs_to_append:
    value = ds_source.attrs.get(attr, 'Unknown')
    existing = str(merged_ds.attrs.get(attr, 'Unknown'))
    merged_ds.attrs[attr] = f"{existing}, {value}" if existing else value

# Update time attributes based on the time coverage of the merged dataset
merged_ds.attrs['time_coverage_start'] = pd.to_datetime(merged_ds.time.min().values).strftime('%Y-%m-%dT%H:%M:%SZ')
merged_ds.attrs['time_coverage_end'] = pd.to_datetime(merged_ds.time.max().values).strftime('%Y-%m-%dT%H:%M:%SZ')

merged_ds.attrs


#%%
# Save the merged dataset
merged_data_dir = '/Users/yugao/UOP/ORS-processing/data/processed/merged_stratus'
merged_ds.to_netcdf(f'{merged_data_dir}/merged_stratus12_to_{case_name1}.nc')

print(f"Merging completed. Dataset saved to merged_stratus12_to_{case_name1}.nc")



# %%
# plot the merged dataset
# Extract variables
cond = merged_ds['cond']
sal = merged_ds['sal']
temp = merged_ds['temp']
press = merged_ds['press']
abssal = merged_ds['abssal']

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
plt.savefig(f'{doc}/merged_ds_{case_name0}_and_{case_name1}.png')


# %%
# check continuous time range
temp_tmp = merged_ds.sel(time=slice(extended_start, extended_end))[variable]
temp_tmp.time.plot()