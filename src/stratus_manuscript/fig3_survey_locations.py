# plot the survey locations of stratus 12 - 18
# locations come from the data attributes
# use time as the colorbar?

# %%
import pandas as pd
import matplotlib.pyplot as plt
import xarray as xr
import matplotlib.ticker as mticker

# Replace with your NetCDF file path
netcdf_file = "/Users/yugao/UOP/ORS-processing/data/processed/merged_stratus/merged_stratus12_to_stratus22.nc"
# Read the NetCDF file
ds = xr.open_dataset(netcdf_file)

# %%
latitude_anchor_survey = ds.attrs['latitude_anchor_survey'].split(',')
longitude_anchor_survey = ds.attrs['longitude_anchor_survey'].split(',')
latitude_anchor_survey, longitude_anchor_survey 

# %%
# platform_data_start_time is not required for plotting markers per deployment

# %%
from datetime import datetime
import numpy as np
import re
from collections import defaultdict

# Convert string lists to float arrays
lat = [float(x) for x in latitude_anchor_survey]
lon = [float(x) for x in longitude_anchor_survey]


# Create the figure and axis
fig, ax = plt.subplots(figsize=(8, 8))

# Create markers for different time periods
markers = ['o', 's', '^', 'D', 'v', '>', '<', 'p', 'h', '8']

site_code = ds.attrs.get('site_code', ds.attrs.get('site', 'Stratus'))

# Build deployment labels robustly
deployment_attr = ds.attrs.get('deployment')
deployment_list = None
if deployment_attr:
    deployment_list = [d.strip() for d in deployment_attr.split(',')]
else:
    m = re.search(r"stratus(\d+)_to_stratus(\d+)", netcdf_file, re.IGNORECASE)
    if m:
        start_num = int(m.group(1))
        end_num = int(m.group(2))
        deployment_list = [str(n) for n in range(start_num, end_num + 1)]

# Align number of plotted points to available data
n_points = min(len(lat), len(lon), len(deployment_list) if deployment_list else len(lat))

# Final labels per point
if deployment_list and len(deployment_list) >= n_points:
    labels = [f"{site_code} {deployment_list[i]}" for i in range(n_points)]
else:
    labels = [f"{site_code} {i+1}" for i in range(n_points)]

# Vary marker sizes subtly to improve differentiation
sizes = np.linspace(120, 180, num=n_points)

# Distinct colors per deployment for clearer differentiation
colors = plt.cm.tab20(np.linspace(0, 1, n_points))

# Cluster near-identical coordinates within a tolerance and spread overlaps
tolerance = 0.006  # degrees (~1 km); adjust if needed
clusters = []
visited = [False] * n_points
for i in range(n_points):
    if visited[i]:
        continue
    cluster = [i]
    visited[i] = True
    for j in range(i + 1, n_points):
        if not visited[j] and abs(lon[j] - lon[i]) <= tolerance and abs(lat[j] - lat[i]) <= tolerance:
            visited[j] = True
            cluster.append(j)
    clusters.append(cluster)

# Spread overlapping points around a small circle and use haloed hollow markers
base_radius = 0.04  # degrees; increased to reduce overlap for clustered points
for idxs in clusters:
    m = len(idxs)
    if m == 1:
        i = idxs[0]
        x, y = lon[i], lat[i]
        # White halo
        ax.scatter(x, y,
                   marker=markers[i % len(markers)],
                   s=sizes[i],
                   facecolors='none',
                   edgecolors='white',
                   linewidths=3.0,
                   zorder=3+i)
        # Colored edge
        ax.scatter(x, y,
                   marker=markers[i % len(markers)],
                   s=sizes[i],
                   facecolors='none',
                   edgecolors=colors[i],
                   linewidths=1.6,
                   alpha=0.95,
                   zorder=4+i,
                   label=labels[i])
    else:
        for j, i in enumerate(idxs):
            angle = 2 * np.pi * j / m
            dx = base_radius * np.cos(angle)
            dy = base_radius * np.sin(angle)
            x, y = lon[i] + dx, lat[i] + dy
            # White halo
            ax.scatter(x, y,
                       marker=markers[i % len(markers)],
                       s=sizes[i],
                       facecolors='none',
                       edgecolors='white',
                       linewidths=3.0,
                       zorder=3+i)
            # Colored edge
            ax.scatter(x, y,
                       marker=markers[i % len(markers)],
                       s=sizes[i],
                       facecolors='none',
                       edgecolors=colors[i],
                       linewidths=1.6,
                       alpha=0.95,
                       zorder=4+i,
                       label=labels[i])

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

# Reduce x-axis tick density to avoid crowded labels
ax.xaxis.set_major_locator(mticker.MaxNLocator(nbins=6))

# Increase font size for tick labels
plt.yticks(fontsize=14)  # Adjust fontsize parameter as needed
plt.xticks(fontsize=12)  # Slightly smaller to reduce crowding

# If you want to adjust all text elements at once, you can also use:
plt.rcParams.update({'font.size': 14})


# Add margin to the plot bounds
lon_margin = (max(lon) - min(lon)) * 0.1
lat_margin = (max(lat) - min(lat)) * 0.1
ax.set_xlim(min(lon) - lon_margin, max(lon) + lon_margin)
ax.set_ylim(min(lat) - lat_margin, max(lat) + lat_margin)

# Add legend with unique labels (no annotations)
handles, legend_labels = ax.get_legend_handles_labels()
unique = {}
for h, l in zip(handles, legend_labels):
    if l not in unique:
        unique[l] = h
ax.legend(unique.values(), unique.keys(), bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=14)


# Adjust layout to prevent legend cutoff
plt.tight_layout()
# plt.show()
# Save the figure
plt.savefig('/Users/yugao/UOP/ORS-processing/img/stratus_manuscript/survey_locations.jpeg', dpi=300, bbox_inches='tight')
