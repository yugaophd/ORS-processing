# %%
# Load necessary libraries
import os
import pandas as pd
import xarray as xr
import matplotlib.pyplot as plt
from qc_function import remove_spikes, compute_diff_stats

# Define case names and instrument serial numbers
case_name0 = 'stratus14'
instrument0_1 = '10600'
instrument0_2 = '10601'
case_name1 = 'stratus15'
instrument1_1 = '11394'
instrument1_2 = '12257'

print(f'Examining overlap between {case_name0} and {case_name1}')

# %%
# Set working directory and load datasets
os.chdir('/Users/yugao/UOP/ORS-processing/src')
ds0_instrument1 = xr.open_dataset(f'/Users/yugao/UOP/ORS-processing/data/processed/{case_name0}/{case_name0}_{instrument0_1}_cleaned.nc')
ds0_instrument2 = xr.open_dataset(f'/Users/yugao/UOP/ORS-processing/data/processed/{case_name0}/{case_name0}_{instrument0_2}_cleaned.nc')
ds1_instrument1 = xr.open_dataset(f'/Users/yugao/UOP/ORS-processing/data/processed/{case_name1}/{case_name1}_{instrument1_1}_cleaned.nc')
ds1_instrument2 = xr.open_dataset(f'/Users/yugao/UOP/ORS-processing/data/processed/{case_name1}/{case_name1}_{instrument1_2}_cleaned.nc')

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
# Plotting

difference1 = ds0_instrument1.sel(time=slice(extended_start, extended_end))[variable] - ds1_instrument1.sel(time=slice(extended_start, extended_end))[variable]
difference2 = ds0_instrument1.sel(time=slice(extended_start, extended_end))[variable] - ds1_instrument2.sel(time=slice(extended_start, extended_end))[variable]
label1 = f'difference between {case_name0} - {instrument0_1} and {case_name1} - {instrument1_1}'
label2 = f'difference between {case_name0} - {instrument0_2} and {case_name1} - {instrument1_1}'


# Define figure and subplots
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))  # Two subplots in one column

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

# Plotting on the second subplot
ax2.plot(difference1.time, difference1, color = 'magenta', label=label1)
ax2.plot(difference2.time, difference2, color = 'black', label=label2)
ax2.set_title(f'Difference Comparison')  # Title for the difference comparison
ax2.set_xlabel('Time')
ax2.set_ylabel(f'Difference in {variable}')
ax2.legend()
ax2.grid(True)

# Save the figure
plt.tight_layout()  # Adjust subplots to fit into figure area nicely
plt.savefig(f'../img/overlap_{case_name0}_and_{case_name1}.png')
plt.show()  # Show plot after saving to avoid a blank image

# %%
# determine the optimal merging time point based on the minimum standard deviation
# of the difference between the two datasets Calculate differences
difference = ds0_instrument1[variable] - ds1_instrument1[variable]

# Convert to DataFrame for easier manipulation
diff_df = difference.to_dataframe(name='temp_difference')

# Calculate rolling statistics with a window of 24 hours
rolling_stats = diff_df['temp_difference'].rolling('6H').agg(['mean', 'std', 'median'])

# Find the time point with the minimum standard deviation
# min_std_time = rolling_stats['std'].idxmin()
# print(f"Optimal merging time point based on minimum standard deviation is: {min_std_time}")

# Optionally, find the time point with the minimum mean or median absolute deviation
min_mean_time = rolling_stats['mean'].idxmin()
# min_median_time = rolling_stats['median'].idxmin()

print(f"Optimal merging time point based on minimum mean is: {min_mean_time}")
# print(f"Optimal merging time point based on minimum median is: {min_median_time}")

# %%
# Select data from each dataset up to and including the optimal merging time point

ds0_merge = ds0_instrument1.sel(time=slice(None, min_mean_time))
ds1_merge = ds1_instrument1.sel(time=slice(min_mean_time, None))

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

# Define attributes to be deleted
attrs_to_delete = [
    # 'platform_anchor_over_time', 'platform_anchor_release_time',
    'platform_duration', 'instrument_firmware_version', 'inputfileheader']

# Perform deletions
for attr in attrs_to_delete:
    merged_dataset.attrs.pop(attr, None)

# Define attributes to be appended from the second dataset
attrs_to_append = ['deployment', 'instrument_SN', 'instrument_model',
                    'latitude_anchor_survey', 'longitude_anchor_survey', 
                    'global_wmo_platform_code', 'platform_start_year',
                    'platform_water_depth_m', 'platform_watch_circle_nm',
                    'platform_deck_height_cm', 'platform_anchor_times',
                    'platform_data_start_time', 'platform_data_end_time', 
                    'platform_anchor_over_time', 'platform_anchor_release_time',
                    'platform_deployment_number']

# Append new values from the second dataset
for attr in attrs_to_append:
    value = ds_source.attrs.get(attr, 'Unknown')
    existing = str(merged_dataset.attrs.get(attr, 'Unknown'))
    merged_dataset.attrs[attr] = f"{existing}, {value}" if existing else value

# Update time attributes based on the time coverage of the merged dataset
merged_dataset.attrs['time_coverage_start'] = pd.to_datetime(merged_dataset.time.min().values).strftime('%Y-%m-%dT%H:%M:%SZ')
merged_dataset.attrs['time_coverage_end'] = pd.to_datetime(merged_dataset.time.max().values).strftime('%Y-%m-%dT%H:%M:%SZ')

merged_dataset.attrs

# Add to the existing attribute 
# if 'instrument_SN' in merged_dataset.attrs:
#     # Append to the existing attribute
    
#     merged_dataset.attrs['deployment'] += f', {case_name0}, {case_name1}'
# else:
#     # Create a new attribute if it doesn't exist
#     merged_dataset.attrs['instrument_SN'] = f'{case_name0}-{instrument0_1}, {case_name1}-{instrument1_1}'


#%%
# Save the merged dataset
merged_data_dir = '/Users/yugao/UOP/ORS-processing/data/processed/merged_stratus'
merged_dataset.to_netcdf(f'{merged_data_dir}/merged_{case_name0}_to_{case_name1}')

print(f"Merging completed. Dataset saved to merged_{case_name0}_to_{case_name1}.nc")

# %%
# verify the merging point
temperature = merged_dataset['temp'].sel(time=slice(extended_start, extended_end))[:100]

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
plt.savefig(f'../img/merged_{case_name0}_and_{case_name1}.png')

# Show the plot
# plt.show()

# %%
