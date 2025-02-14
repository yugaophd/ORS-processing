# %%
import xarray as xr
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Rectangle

# Replace with your NetCDF file path
netcdf_file = "/Users/yugao/UOP/ORS-processing/data/processed/merged_stratus/merged_stratus12_to_stratus14.nc"
# Read the NetCDF file
ds = xr.open_dataset(netcdf_file)

# %%
# Create figure with two subplots (temperature and depth)
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8, 8),
                              gridspec_kw={'height_ratios': [2, 1]},
                              sharex=True)

# Get standard deviations from attributes
std_devs = [float(std.strip()) for std in ds.temp.attrs['std_single_sensor'].split(',')]

# Plot temperature data with standard deviation bands
time_array = ds.time.values
temp_array = ds.temp.values

# Plot the main temperature line
ds.temp.plot(ax=ax1, color='black', linewidth=1, label='Temperature')

# Get merge points and create shaded regions for each segment
merge_points = [np.datetime64(date.strip().replace('Z', ''))
               for date in ds.attrs['merge_point'].split(',')]


# Add shading for each segment
instruments = ds.attrs['instrument_model']
instruments = instruments.replace('-', '') # remove the dash in SBE-16

# Get the instrument string and parse it
instruments = [instr.strip() for instr in instruments.split(',')]
colors = [ 'orange', 'purple', 'brown']

for i in range(len(merge_points) + 1):
    if i == 0:
        # First segment
        mask = time_array < merge_points[0]
    elif i == len(merge_points):
        # Last segment
        mask = time_array >= merge_points[-1]
    else:
        # Middle segments
        mask = (time_array >= merge_points[i-1]) & (time_array < merge_points[i])
    
    # Create shaded region for this segment
    segment_time = time_array[mask]
    segment_temp = temp_array[mask]
    ax1.fill_between(segment_time,
                    segment_temp - std_devs[i],
                    segment_temp + std_devs[i],
                    color=colors[i], alpha=0.2,
                    label=f'±1σ, {instruments[i]}')

# Add vertical lines at merge points
for merge_point in merge_points:
    ax1.axvline(merge_point, color='red', linestyle='--', alpha=0.7)
    ax2.axvline(merge_point, color='red', linestyle='--', alpha=0.7)

ax1.set_ylabel('Temperature (°C)')
ax1.grid(True, linestyle='--', alpha=0.7)
ax1.legend()

# Plot depth data
depths = [float(depth.strip()) for depth in ds.attrs['platform_water_depth_m'].split(',')]

# Create step function for depth
step_depth = np.full_like(time_array, depths[0], dtype=float)
for i in range(len(merge_points)):
    mask = time_array >= merge_points[i]
    step_depth[mask] = depths[i + 1]

# Add the step_depth to the dataset
ds['instrument_depth'] = xr.DataArray(step_depth, coords=[ds.time], dims=['time'])

# Plot depth data
ds.instrument_depth.plot(ax=ax2, color='blue', linewidth=1.5)

# 4505 to 4545
ax2.set_ylim(4500, 4550)

# Format x-axis
plt.xlabel('Time')

# Adjust layout
plt.tight_layout()

# save the figure
plt.savefig('/Users/yugao/UOP/ORS-processing/img/merged_stratus12_to_stratus14.jpeg',
            dpi=300)

# Display the plot
# plt.show()
# %%