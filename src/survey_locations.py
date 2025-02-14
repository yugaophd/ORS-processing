# plot the survey locations of stratus 12 - 18
# locations come from the data attributes
# use time as the colorbar?

# %%
import pandas as pd
import matplotlib.pyplot as plt
import xarray as xr

# Replace with your NetCDF file path
netcdf_file = "/Users/yugao/UOP/ORS-processing/data/processed/merged_stratus/merged_stratus12_to_stratus18.nc"
# Read the NetCDF file
ds = xr.open_dataset(netcdf_file)

# %%
latitude_anchor_survey = ds.attrs['latitude_anchor_survey'].split(',')
longitude_anchor_survey = ds.attrs['longitude_anchor_survey'].split(',')
latitude_anchor_survey, longitude_anchor_survey 

# %%
platform_data_start_time = ds.attrs['platform_data_start_time'].split(',')
platform_data_start_time

# %%
from datetime import datetime
import matplotlib.dates as mdates
from datetime import datetime
import numpy as np

# Convert string lists to float arrays
lat = [float(x) for x in latitude_anchor_survey]
lon = [float(x) for x in longitude_anchor_survey]
times = [datetime.strptime(t.strip(), '%Y-%m-%d %H:%M:%S') for t in platform_data_start_time]


# Create the figure and axis
fig, ax = plt.subplots(figsize=(8, 8))

# Create markers for different time periods
markers = ['o', 's', '^', 'D', 'v', '>', '<', 'p', 'h', '8']

site = ds.attrs['site']
deployment = ds.attrs['deployment'].split(',')
n_segments = len(deployment)  # Use up to 10 different markers
points_per_segment = len(times) // n_segments

# Plot each segment with different marker
for i in range(n_segments):
    start_idx = i * points_per_segment
    end_idx = start_idx + points_per_segment if i < n_segments-1 else len(times)
    
    ax.scatter(lon[start_idx:end_idx], 
              lat[start_idx:end_idx],
              marker=markers[i],
              s=120,
              label=f'{site} {deployment[i]}'
            #   label=f'{site} {deployment[i]} {times[i].strftime("%Y-%m-%d %H:%M:%S")}'
            )

# Customize the plot
plt.xlabel('Longitude', fontsize=14)
plt.ylabel('Latitude', fontsize=14)
plt.title('Survey Coordinates', fontsize=16)
ax.grid(True)

# Custom formatter for axis labels
def lon_formatter(x, pos):
    return f'{abs(x):.1f}°{"W" if x < 0 else "E"}'

def lat_formatter(x, pos):
    return f'{abs(x):.1f}°{"S" if x < 0 else "N"}'

ax.xaxis.set_major_formatter(plt.FuncFormatter(lon_formatter))
ax.yaxis.set_major_formatter(plt.FuncFormatter(lat_formatter))

# Increase font size for tick labels
plt.yticks(fontsize=14)  # Adjust fontsize parameter as needed
plt.xticks(fontsize=14)  # Adjust fontsize parameter as needed

# If you want to adjust all text elements at once, you can also use:
plt.rcParams.update({'font.size': 14})


# Add margin to the plot bounds
lon_margin = (max(lon) - min(lon)) * 0.1
lat_margin = (max(lat) - min(lat)) * 0.1
ax.set_xlim(min(lon) - lon_margin, max(lon) + lon_margin)
ax.set_ylim(min(lat) - lat_margin, max(lat) + lat_margin)

# Add legend
plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
#  larger symbols and larger fonts for the axes and legend
plt.legend(fontsize=14)


# Adjust layout to prevent legend cutoff
# plt.tight_layout()
# plt.show()
# Save the figure
plt.savefig('/Users/yugao/UOP/ORS-processing/img/survey_locations.jpeg', dpi=300, bbox_inches='tight')
