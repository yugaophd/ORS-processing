# %%
# No overlap between the two datasets
# merge directly stratus 12 and stratus 13 in time
# fill in the gaps with Nans.

# Load necessary libraries
import os
import pandas as pd
import xarray as xr
import matplotlib.pyplot as plt
from qc_function import remove_spikes, compute_diff_stats

# Define case names and instrument serial numbers


case_name0 = 'stratus12'
instrument0_1 = '1876' # Chosen for merging
instrument0_2 = '1879' 

case_name1 = 'stratus13'
instrument1_1 = '1873'
instrument1_2 = '1875' # chosen for merging


# store the results in the doc folder of the latter case
project_name = 'stratus'
project_number = '13'
doc = f'/Users/yugao/UOP/ORS-processing/doc/{project_name}/{project_number}'

print(f'Examining overlap between {case_name0} and {case_name1}')

# %%
# Set working directory and load datasets
os.chdir('/Users/yugao/UOP/ORS-processing/src')
ds0_instrument1 = xr.open_dataset(f'/Users/yugao/UOP/ORS-processing/data/processed/{case_name0}/{case_name0}_{instrument0_1}_cleaned.nc')
ds0_instrument2 = xr.open_dataset(f'/Users/yugao/UOP/ORS-processing/data/processed/{case_name0}/{case_name0}_{instrument0_2}_cleaned.nc')
ds1_instrument1 = xr.open_dataset(f'/Users/yugao/UOP/ORS-processing/data/processed/{case_name1}/{case_name1}_{instrument1_1}_cleaned.nc')
ds1_instrument2 = xr.open_dataset(f'/Users/yugao/UOP/ORS-processing/data/processed/{case_name1}/{case_name1}_{instrument1_2}_cleaned.nc')

ds0_instrument1

# %%

# Determine overlap window and extend by 2 hours
variable = 'temp'  # Specify variable to compare
overlap_start = max(ds0_instrument1.time.min(), ds0_instrument2.time.min(), ds1_instrument1.time.min(), ds1_instrument2.time.min())
overlap_end = min(ds0_instrument1.time.max(), ds0_instrument2.time.max(), ds1_instrument1.time.max(), ds1_instrument2.time.max())
extended_start = overlap_start - pd.Timedelta(hours=4)
extended_end = overlap_end + pd.Timedelta(hours=4)

# Select data for plotting
sel0_1 = ds0_instrument1.sel(time=slice(extended_start, extended_end))[variable]
sel0_2 = ds0_instrument2.sel(time=slice(extended_start, extended_end))[variable]
sel1_1 = ds1_instrument1.sel(time=slice(extended_start, extended_end))[variable]
sel1_2 = ds1_instrument2.sel(time=slice(extended_start, extended_end))[variable]
# %%
# merge after assessing the stats stratus 13 and stratus 14 in time
# Ensure both datasets cover the same time period for a fair comparison

# Determine overlap window and extend by 2 hours
variable = 'temp'  # Specify variable to compare

overlap_start = max(ds0_instrument1.time.min(), ds1_instrument2.time.min(), ds1_instrument1.time.min())
overlap_end = min(ds0_instrument1.time.max(), ds1_instrument2.time.max(), ds1_instrument1.time.max())


if overlap_start >= overlap_end:
    print('No overlap between the two datasets. Exiting...')
    # extend the time window by 24 hours
else:
    print(f'Overlap between {case_name0} and {case_name1} from {overlap_start} to {overlap_end}')


# %%
# Plotting
extended_start = overlap_start - pd.Timedelta(hours=120)
extended_end = overlap_end + pd.Timedelta(hours=120)

# Select data for plotting
sel0_1 = ds0_instrument1.sel(time=slice(extended_start, extended_end))[variable]
sel0_2 = ds0_instrument2.sel(time=slice(extended_start, extended_end))[variable]

sel1_1 = ds1_instrument1.sel(time=slice(extended_start, extended_end))[variable]
sel1_2 = ds1_instrument2.sel(time=slice(extended_start, extended_end))[variable]

# Define figure and subplots
fig, ax1 = plt.subplots(1, 1, figsize=(12, 10))  # Two subplots in one column

# Plotting on the first subplot
ax1.plot(sel0_1.time, sel0_1, label=f'{case_name0} - {instrument0_1}')
ax1.plot(sel0_2.time, sel0_2, label=f'{case_name0} - {instrument0_2}')
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

# %%
ds0_merge = ds0_instrument1
ds1_merge = ds1_instrument2

# Merge the datasets aligning by 'time' dimension and filling gaps with NaNs
# merged_dataset = xr.concat([ds0_merge, ds1_merge], dim="time")
# Step 1: Concatenate and sort datasets
merged_dataset = xr.concat([ds0_merge, ds1_merge], dim="time")
merged_dataset = merged_dataset.sortby("time")


# %%
# Data source is the second dataset
ds_source = ds1_merge
# Copy attributes from the first dataset and prepare to modify them
merged_dataset.attrs = ds0_merge.attrs.copy()

# %%
# attribute merging point
# If there is no overlap, 
# define the "merge point" as the starting time of the subsequent deployment.
if overlap_end < overlap_start:
    merge_point = pd.to_datetime(ds1_merge.time[0].values).strftime('%Y-%m-%dT%H:%M:%SZ')
    merged_dataset.attrs['merge_point'] = f'{merge_point}'
    merged_dataset.attrs['merge_point_comment'] = f'If no overlap between the two datasets, merge at the start of the second dataset.'
    print(f"No overlap between the two datasets. Merging at the start of the second dataset.")  


# Define attributes to be appended from the second dataset
attrs_to_append = ['deployment', 'instrument_SN', 'instrument_model',
                    'latitude_anchor_survey', 'longitude_anchor_survey', 
                    'global_wmo_platform_code', 'platform_start_year',
                    'platform_water_depth_m', 'platform_watch_circle_nm',
                    'platform_deck_height_cm', 'platform_anchor_times',
                    'platform_data_start_time', 
                    'platform_anchor_over_time', 
                    # 'platform_anchor_release_time'
                    ]

# Append new values from the second dataset
for attr in attrs_to_append:
    value = ds_source.attrs.get(attr, 'Unknown')
    existing = str(merged_dataset.attrs.get(attr, 'Unknown'))
    merged_dataset.attrs[attr] = f"{existing}, {value}" if existing else value

# Define attributes to be deleted
attrs_to_delete = ['platform_deployment_number', 'platform_anchor_release_time',
    'platform_deployment_number', 'platform_data_end_time'
    'platform_duration', 'instrument_firmware_version', 'inputfileheader']

# Perform deletions
for attr in attrs_to_delete:
    merged_dataset.attrs.pop(attr, None)

# %%
# Append variable attributes from the source dataset to the merged dataset
from util import append_variable_attributes

merged_dataset = append_variable_attributes(ds_source, merged_dataset)

# Update time attributes based on the time coverage of the merged dataset
merged_dataset.attrs['time_coverage_start'] = pd.to_datetime(merged_dataset.time.min().values).strftime('%Y-%m-%dT%H:%M:%SZ')
merged_dataset.attrs['time_coverage_end'] = pd.to_datetime(merged_dataset.time.max().values).strftime('%Y-%m-%dT%H:%M:%SZ')

#%%
# Save the merged dataset
merged_data_dir = '/Users/yugao/UOP/ORS-processing/data/processed/merged_stratus'
merged_dataset.to_netcdf(f'{merged_data_dir}/merged_{case_name0}_to_{case_name1}.nc')

print(f"Merging completed. Dataset saved to merged_{case_name0}_to_{case_name1}.nc")

# %%
# verify the merging point
temperature = merged_dataset['temp'].sel(time=slice(extended_start, extended_end))[:100]

# Plotting
fig, ax = plt.subplots(figsize=(12, 6))

# Plot temperature data
temperature.plot(ax=ax, color='blue', label='Merged Temperature')

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
