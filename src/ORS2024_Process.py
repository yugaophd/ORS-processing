from netcdf import read_mat_file, read_metadata_json, mat_to_xarray, save_to_netcdf

def process_dataset(mat_filepath, metadata_filepath, output_filepath):
    mat_data = read_mat_file(mat_filepath)
    metadata = read_metadata_json(metadata_filepath)
    ds = mat_to_xarray(mat_data, metadata)
    save_to_netcdf(ds, output_filepath)

if __name__ == "__main__":
    # Define paths (consider using argparse or similar for flexibility)
    mat_filepath = 'data/external/example.mat'
    metadata_filepath = 'data/metadata/example_metadata.json'
    output_filepath = 'data/processed/processed_data.nc'
    
    process_dataset(mat_filepath, metadata_filepath, output_filepath)
