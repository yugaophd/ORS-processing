import json
import scipy.io
import xarray as xr
import numpy as np

def read_mat_file(filepath):
    """Reads a .mat file and returns its content."""
    return scipy.io.loadmat(filepath, squeeze_me=True)  # squeeze_me for simplicity

def mat_to_xarray_old(mat_data):
    ds = xr.Dataset()
    
    # Assuming 'mday' represents the time dimension for your measurements
    time_dim = 'time'  # Naming the time dimension
    ds[time_dim] = xr.DataArray(data=mat_data['mday'], dims=[time_dim], attrs={'units': 'days since 1900-01-01'})  # Example unit

    # Adding measurement variables (assuming they share the time dimension)
    for var in ['temp', 'cond', 'sal', 'sal_sbe']:
        if var in mat_data:
            ds[var] = xr.DataArray(
                data=mat_data[var],
                dims=[time_dim],
                attrs={'units': 'units_placeholder'}  # Replace 'units_placeholder' with actual units
            )

    # Handling 'depth' as a static or metadata attribute (assuming it's a singular value for the dataset)
    ds.attrs['depth'] = mat_data['depth']

    # Adding additional metadata attributes
    ds.attrs['latitude'] = mat_data['latitude']
    ds.attrs['longitude'] = mat_data['longitude']

    return ds

def save_to_netcdf(ds, output_filepath):
    """Saves an xarray DataSet to a NetCDF file."""
    ds.to_netcdf(output_filepath)

def mat_to_xarray(mat_data):
    import xarray as xr
    import numpy as np

    ds = xr.Dataset()
    time_dim = 'time'
    ds[time_dim] = xr.DataArray(data=mat_data['mday'], dims=[time_dim], attrs={'units': 'days since 1900-01-01'})

    # Assuming 'meta' is correctly a structured array and variables are directly accessible
    for var in ['temp', 'cond', 'sal', 'sal_sbe']:
        if var in mat_data:
            var_info = mat_data['meta'][0][var][0]  # Updated to access the structured array correctly
            units = var_info['units'].item() if 'units' in var_info.dtype.fields else 'unknown units'
            long_name = var_info['long_name'].item() if 'long_name' in var_info.dtype.fields else var.capitalize()

            if 'cal' in var_info.dtype.fields:
                cal_data = var_info['cal'].item()
                calibrated_data = mat_data[var] * float(cal_data['G'].item()) + float(cal_data['H'].item())
            else:
                calibrated_data = mat_data[var]

            ds[var] = xr.DataArray(
                data=calibrated_data,
                dims=[time_dim],
                attrs={'units': units, 'long_name': long_name}
            )

    ds.attrs['depth'] = mat_data['depth']
    ds.attrs['latitude'] = mat_data['latitude']
    ds.attrs['longitude'] = mat_data['longitude']

    return ds

def mat_to_xarray_sbe16(mat_data):
    ds = xr.Dataset()
    
    # Assuming 'mday' represents the time dimension for your measurements
    time_dim = 'time'  # Naming the time dimension
    ds[time_dim] = xr.DataArray(data=mat_data['mday'], dims=[time_dim], attrs={'units': 'days since 1900-01-01'})  # Example unit

    # Adding measurement variables (assuming they share the time dimension)
    for var in ['temp', 'cond', 'sal', 'sal_sbe']:
        if var in mat_data:
            ds[var] = xr.DataArray(
                data=mat_data[var],
                dims=[time_dim],
                attrs={'units': 'units_placeholder'}  # Replace 'units_placeholder' with actual units
            )

    # Handling 'depth' as a static or metadata attribute (assuming it's a singular value for the dataset)
    ds.attrs['depth'] = mat_data['depth']

    # Adding additional metadata attributes
    ds.attrs['latitude'] = mat_data['latitude']
    ds.attrs['longitude'] = mat_data['longitude']

    return ds




