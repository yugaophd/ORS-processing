"""
Fig. 2a (slide-ready): Upper panel — merged temperature time series

Requirements:
- Single panel: sea_water_temperature vs time
- Time axis along the bottom
- Black line instead of red
- Larger tick marks and axis labels
- No upper label/suptitle
"""

import os
import xarray as xr
import matplotlib.pyplot as plt
from matplotlib import dates as mdates

# Input dataset (temperature-only CF dataset)
temp_ds_path = '/Users/yugao/UOP/ORS-processing/data/processed/merged_stratus/stratus_temperature_2012_2023.nc'

# Output figure path (slide-friendly)
out_dir = '/Users/yugao/UOP/ORS-processing/img/stratus_manuscript'
os.makedirs(out_dir, exist_ok=True)
out_png = os.path.join(out_dir, 'fig2a_temp_slide.png')

# Load temperature-only dataset
ds = xr.open_dataset(temp_ds_path)

# Prepare figure
fig, ax = plt.subplots(figsize=(16, 6), dpi=200)

# Plot temperature as a black line
ax.plot(ds['time'].values, ds['sea_water_temperature'].values, color='black', linewidth=1.5)

# Axis labels (bigger for slides)
ax.set_ylabel('Sea Water Temperature (°C)', fontsize=18)
ax.set_xlabel('Time', fontsize=18)

# Date formatting on x-axis
ax.xaxis.set_major_locator(mdates.YearLocator(base=1))
ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
ax.xaxis.set_minor_locator(mdates.MonthLocator(bymonth=(1, 7)))

# Larger ticks
ax.tick_params(axis='both', which='major', labelsize=16, length=7, width=1.5)
ax.tick_params(axis='both', which='minor', length=4, width=1.0)

# Clean style: enable subtle gridlines for readability on slides
ax.set_axisbelow(True)
ax.grid(True, which='both', axis='both', linestyle=':', linewidth=0.8, alpha=0.4)

# Tight layout and save
fig.tight_layout()
fig.savefig(out_png, bbox_inches='tight')
plt.close(fig)

print(f'Saved slide-friendly temperature figure to: {out_png}')
