from netcdf import read_mat_file, read_metadata_json, mat_to_xarray, save_to_netcdf
from metadata_processing import create_json

def process_dataset(mat_filepath, metadata_filepath, output_filepath):
    """
    Process the dataset by reading MATLAB data, creating metadata, converting to xarray, and saving to NetCDF.

    Args:
        mat_filepath: Path to the MATLAB data file.
        metadata_filepath: Path to the metadata JSON file.
        output_filepath: Path to save the processed NetCDF file.
    """
    # Read MATLAB data
    mat_data = read_mat_file(mat_filepath)
    
    # Create metadata
    metadata = create_json(mat_data)
    
    # Read metadata JSON
    metadata_json = read_metadata_json(metadata_filepath)
    
    # Combine metadata (optional, depending on usage)
    combined_metadata = {**metadata, **metadata_json}
    
    # Convert MATLAB data to xarray dataset
    ds = mat_to_xarray(mat_data)
    
    # Save to NetCDF
    save_to_netcdf(ds, output_filepath, metadata=combined_metadata)

if __name__ == "__main__":
    # Define file paths
    mat_filepath = 'data/external/example.mat'
    metadata_filepath = 'data/metadata/example_metadata.json'
    output_filepath = 'data/processed/processed_data.nc'
    
    # Process the dataset
    process_dataset(mat_filepath, metadata_filepath, output_filepath)
