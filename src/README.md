# Stratus Ocean Reference Station Dataset (2012-2023)

## Coordinate Information

The coordinates in this dataset vary with time due to different mooring deployment locations:

| Coordinate | Range | Units |
|------------|-------|-------|
| Latitude | -22.52° to -19.43° | degrees North |
| Longitude | -85.82° to -84.74° | degrees East |
| Depth | ~4200 to ~4600 | meters |

## Temporal Coverage

This dataset spans from **May 2012 to March 2023** covering Stratus mooring deployments 12 through 22.

## Data Structure

This dataset follows [CF Conventions 1.8](https://cfconventions.org/Data/cf-conventions/cf-conventions-1.8/cf-conventions.html) using the `timeSeries` feature type. Each variable has these associated coordinates:

- **time**: The primary dimension for all measurements
- **latitude**, **longitude**, **depth**: Auxiliary coordinates attached to each variable

## For Modelers

The coordinates are accessible as auxiliary coordinates in standard analysis packages in python:

import xarray as xr

# Open the dataset
ds = xr.open_dataset('stratus_cf_compliant_2012_2023.nc')

# Access coordinates
times = ds.time
lats = ds.latitude  # varies with time
lons = ds.longitude  # varies with time
depths = ds.depth  # varies with time

# Access temperature data
temp = ds.sea_water_temperature