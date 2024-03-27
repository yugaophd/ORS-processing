import json
import scipy.io
import xarray as xr
import numpy as np

def read_mat_file(filepath):
    """Reads a .mat file and returns its content."""
    return scipy.io.loadmat(filepath, squeeze_me=True)  # squeeze_me for simplicity

def mat_to_xarray(mat_data):
    """Converts data from .mat format to an xarray DataSet, including metadata."""
    print('this is the one')
    ds = xr.Dataset()
    for param in ['temp', 'sal', 'depth']:
            ds[param] = xr.DataArray(
                data=mat_data[param],
                dims=['time', 'depth'],
                attrs={'units': mat_data['variables'][param]['attrs']['units']}
            )
    for attr, value in mat_data['attributes'].items():
        ds.attrs[attr] = value
    return ds

def save_to_netcdf(ds, output_filepath):
    """Saves an xarray DataSet to a NetCDF file."""
    ds.to_netcdf(output_filepath)
