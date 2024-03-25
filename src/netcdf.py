import json
import scipy.io
import xarray as xr
import numpy as np

def read_mat_file(filepath):
    """Reads a .mat file and returns its content."""
    return scipy.io.loadmat(filepath, squeeze_me=True)  # squeeze_me for simplicity

def read_metadata_json(filepath):
    """Reads a metadata JSON file."""
    with open(filepath, 'r') as f:
        metadata = json.load(f)
    return metadata

def save_preserved_info_from_json(original_file_path, new_file_path):
    """
    Extracts preserved information from a JSON file and saves it to a new file.

    Parameters:
    - original_file_path: Path to the original JSON file.
    - new_file_path: Path where the new JSON file with preserved info will be saved.
    """
    with open(original_file_path, 'r') as file:
        data = json.load(file)

    preserved_info = {
        "metadata": data.get("attributes", {}),
        "quality_control_flags": data.get("quality_control_flags", {}),
        "instrument_details": data.get("instrument_details", {})
    }

    with open(new_file_path, 'w') as new_file:
        json.dump(preserved_info, new_file, indent=4)

def mat_to_xarray(mat_data):
    """Converts data from .mat format to an xarray DataSet, including metadata."""
    ds = xr.Dataset()
        # Example, adjust based on actual data structure and metadata
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
