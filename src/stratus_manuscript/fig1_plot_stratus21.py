#%%
# plot temperature only for Stratus 21

import os
import xarray as xr
import matplotlib.pyplot as plt
import numpy as np
img_dir = "/Users/yugao/UOP/ORS-processing/img/stratus_manuscript"
# make sure the image directory exists
if not os.path.exists(img_dir):
    os.makedirs(img_dir)

datafile1 = "/Users/yugao/UOP/ORS-processing/data/processed/stratus21/v1/stratus21_11379_cleaned.nc"
datafile2 = "/Users/yugao/UOP/ORS-processing/data/processed/stratus21/v1/stratus21_11394_cleaned.nc"

ds1 = xr.open_dataset(datafile1)
ds2 = xr.open_dataset(datafile2)

#%%
# Extract temperature data
temperature1 = ds1['sea_water_temperature']
temperature2 = ds2['sea_water_temperature']

#%%
# Plot temperature data
plt.figure(figsize=(12, 6))
plt.plot(temperature1['time'], temperature1, label='Stratus 21 - 11379')
plt.plot(temperature2['time'], temperature2, label='Stratus 21 - 11394')
plt.xlabel('Time', fontsize=13)
plt.ylabel('Sea Water Temperature (°C)', fontsize=13)
# inlcude location and depth information: 22.5042 W and 85.82 S | depth 4199m 
# include degree sign safely using mathtext
plt.title(r"Sea Water Temperature for Stratus 21 (22.50$^\circ$W, 85.82$^\circ$S | depth 4199 m)", fontsize=16)

plt.tick_params(axis='both', labelsize=11)
plt.legend(fontsize=11)
plt.tight_layout()
plt.savefig(f"{img_dir}/sea_water_temperature_stratus21.png")
# %%
