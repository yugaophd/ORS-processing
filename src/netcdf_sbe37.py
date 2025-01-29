import json
import scipy.io
import xarray as xr
import numpy as np
import datetime
import scipy.io
import numpy as np

def read_mat_file(filepath):
    """Reads a .mat file and returns its content, ensuring it handles struct_as_record."""
    return scipy.io.loadmat(filepath, struct_as_record=False, squeeze_me=True)

def extract_metadata(mat_data):
    """Extracts specified metadata from MATLAB data."""
    attributes = {}
    
    # Assuming the metadata is stored in a 'meta' struct or directly accessible
    meta = mat_data.get('meta', {})
    if isinstance(meta, np.ndarray) and meta.dtype.names:
        # Extract fields if they exist in 'meta'
        fields = [
            'site', 'deployment', 'principal_investigator', 'institution', 'project',
            'platform_type', 'platform_year', 'time_coverage_start', 'time_coverage_end',
            'time_coverage_duration', 'latitude_anchor_survey', 'longitude_anchor_survey',
            'geospatial_lat_min', 'geospatial_lat_max', 'geospatial_lon_min', 'geospatial_lon_max',
            'geospatial_vertical_min', 'geospatial_vertical_max', 'time_coverage_resolution'
        ]
        for field in fields:
            if field in meta.dtype.names:
                attributes[field] = meta[field].item() if np.isscalar(meta[field]) else meta[field].tolist()
    
    # Additional depth parameters
    depth_params = [
        'water_depth_from_mooring_diagram', 'water_depth_from_ship_uncorrected', 'water_depth_from_ship_corrected',
        'instrument_depth_from_mooring_diagram', 'instrument_depth_from_mooring_log', 'instrument_height_above_bottom'
    ]
    for param in depth_params:
        if param in meta.dtype.names:
            attributes[param] = meta[param].item() if np.isscalar(meta[param]) else meta[param].tolist()

    return attributes



def create_xarray_dataset(mat_data, attributes, depth_parameters):
    """Creates an xarray dataset from MATLAB data, attributes, and depth parameters."""
    ds = xr.Dataset()
    
    # Handling time-series data with 'mday' as the time dimension
    if 'mday' in mat_data:
        ds['time'] = xr.DataArray(data=np.array(mat_data['mday']), dims=['time'], attrs={'units': 'MATLAB datenum'})

    # Add other measurement variables assuming they share the time dimension
    for var in ['temp', 'cond', 'sal', 'sal_sbe']:
        if var in mat_data:
            ds[var] = xr.DataArray(
                data=np.array(mat_data[var]),
                dims=['time'],
                attrs={'units': 'units_placeholder'}  # Replace 'units_placeholder' with actual units
            )

    # Adding attributes and depth parameters to the dataset
    for key, value in attributes.items():
        ds.attrs[key] = value
    for key, value in depth_parameters.items():
        ds.attrs[key] = value

    return ds




def add_metadata_to_dataset(dataset, metadata, path=None):
    """Adds flattened metadata to an xarray dataset."""
    if isinstance(metadata, dict):
        for key, value in metadata.items():
            new_path = f"{path}{key}_" if path else f"{key}_"
            add_metadata_to_dataset(dataset, value, new_path)
    elif isinstance(metadata, list):
        # Concatenate list items into a string if it's a list of non-dictionaries
        if all(not isinstance(item, dict) for item in metadata):
            dataset.attrs[path.rstrip('_')] = ', '.join(map(str, metadata))
        else:
            for i, item in enumerate(metadata):
                add_metadata_to_dataset(dataset, item, f"{path}{i}_")
    else:
        dataset.attrs[path.rstrip('_')] = metadata


def mat_to_xarray(mat_data, depth=None):
    """Converts MATLAB data to an xarray Dataset, including complex metadata."""
    ds = xr.Dataset()
    time_dim = 'time'
    ds[time_dim] = xr.DataArray(data=mat_data['mday'], dims=[time_dim], attrs={'units': 'days since 1900-01-01'})

    # Adding measurement variables (assuming they share the time dimension)
    meta = mat_data.get('meta', {})
    if isinstance(meta, np.ndarray) and meta.dtype.names:
        for var in ['temp', 'cond', 'sal', 'sal_sbe']:
            if var in meta.dtype.names:
                var_info = meta[var][0] if np.isscalar(meta[var]) else meta[var]
                units = var_info['units'] if 'units' in var_info.dtype.names else 'unknown units'
                long_name = var_info['long_name'] if 'long_name' in var_info.dtype.names else var.capitalize()
                ds[var] = xr.DataArray(data=mat_data[var], dims=[time_dim], attrs={'units': units, 'long_name': long_name})

    # Extract and flatten all metadata
    if 'meta' in mat_data:
        full_metadata = flatten_attribute(mat_data['meta'])
        add_metadata_to_dataset(ds, full_metadata)

    # Adding basic attributes
    ds.attrs.update({
        'depth': depth if depth is not None else mat_data.get('depth', np.nan),
        'latitude': mat_data.get('latitude', np.nan),
        'longitude': mat_data.get('longitude', np.nan)
    })

    return ds



def save_to_netcdf(ds, output_filepath):
    """Saves an xarray DataSet to a NetCDF file."""
    ds.to_netcdf(output_filepath)

