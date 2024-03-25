import xarray as xr
import matplotlib.pyplot as plt

def plot_data_from_netcdf(netcdf_filepath, plot_output_path):
    ds = xr.open_dataset(netcdf_filepath)
    # Example: Plotting temperature
    ds['temperature'].mean(dim='time').plot()
    plt.savefig(plot_output_path)
