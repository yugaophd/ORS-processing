import xarray as xr
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator
import matplotlib.dates as mdates
import numpy as np

def plot_spike_data(deployment_spike_data, recovery_spike_data, case_name, save_path):
    """
    Plots temperature and salinity during deployment and recovery spike times using provided data segments.

    Parameters:
    - deployment_spike_data (xarray.Dataset): Dataset slice for the deployment spike period.
    - recovery_spike_data (xarray.Dataset): Dataset slice for the recovery spike period.
    - case_name (str): Case name used for saving the plots.
    - save_path (str): Path to save the plotted figures.
    """
    # Function to convert cftime to numpy.datetime64, assuming time data uses cftime
    def convert_cftime_to_datetime64(times):
        return np.array([np.datetime64(time.isoformat()) for time in times])

    deployment_times = convert_cftime_to_datetime64(deployment_spike_data['temp'].time.values)
    recovery_times = convert_cftime_to_datetime64(recovery_spike_data['temp'].time.values)

    plt.figure(figsize=(12, 10))

    # Plot for deployment spike
    ax1 = plt.subplot(211)
    ax1.plot(deployment_times, deployment_spike_data['temp'], color='blue', label='Temperature')
    ax1.set_title('Temperature/Salinity During Deployment Spike Time')
    ax1.set_xlabel('Time')
    ax1.set_ylabel('Temperature (°C)')
    ax1.grid(True)
    ax1.xaxis.set_major_locator(MaxNLocator(10))
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %H:%M'))

    ax2 = ax1.twinx()
    ax2.plot(deployment_times, deployment_spike_data['sal'], color='red', label='Salinity')
    ax2.set_ylabel('Salinity (psu)')
    ax1.legend(loc='upper left')
    ax2.legend(loc='upper right')

    # Plot for recovery spike
    ax3 = plt.subplot(212)
    ax3.plot(recovery_times, recovery_spike_data['temp'], color='blue', label='Temperature')
    ax3.set_title('Temperature/Salinity During Recovery Spike Time')
    ax3.set_xlabel('Time')
    ax3.set_ylabel('Temperature (°C)')
    ax3.grid(True)
    ax3.xaxis.set_major_locator(MaxNLocator(10))
    ax3.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %H:%M'))

    ax4 = ax3.twinx()
    ax4.plot(recovery_times, recovery_spike_data['sal'], color='red', label='Salinity')
    ax4.set_ylabel('Salinity (psu)')
    ax3.legend(loc='upper left')
    ax4.legend(loc='upper right')

    plt.tight_layout()
    plt.savefig(f'{save_path}')
    # plt.close()



def plot_spike_data_multi(deployment_spike_data1, recovery_spike_data1, 
                             deployment_spike_data2, recovery_spike_data2, 
                             instrument_name1, instrument_name2, 
                             case_name, save_path):
    """
    Plots temperature and salinity during deployment and recovery spike times for two datasets overlaid on the same plots.

    Parameters:
    - deployment_spike_data1, recovery_spike_data1 (xarray.Dataset): Dataset slices for the deployment and recovery spike period for the first instrument.
    - deployment_spike_data2, recovery_spike_data2 (xarray.Dataset): Dataset slices for the deployment and recovery spike period for the second instrument.
    - instrument_name1, instrument_name2 (str): Instrument names for legend labeling.
    - case_name (str): Case name used for saving the plots.
    - save_path (str): Path to save the plotted figures.
    """
    def convert_cftime_to_datetime64(times):
        return np.array([np.datetime64(time.isoformat()) for time in times])

    # Convert times for both datasets
    deployment_times1 = convert_cftime_to_datetime64(deployment_spike_data1['temp'].time.values)
    recovery_times1 = convert_cftime_to_datetime64(recovery_spike_data1['temp'].time.values)
    deployment_times2 = convert_cftime_to_datetime64(deployment_spike_data2['temp'].time.values)
    recovery_times2 = convert_cftime_to_datetime64(recovery_spike_data2['temp'].time.values)

    plt.figure(figsize=(12, 10))

    # Combined plot for deployment
    ax1 = plt.subplot(211)
    ax1.plot(deployment_times1, deployment_spike_data1['temp'], label=f'Temperature - {instrument_name1}', color='blue')
    ax1.plot(deployment_times2, deployment_spike_data2['temp'], label=f'Temperature - {instrument_name2}', color='red')
    ax1.set_title('Temperature During Deployment Spike Time')
    ax1.set_xlabel('Time')
    ax1.set_ylabel('Temperature (°C)')
    ax1.grid(True)
    ax1.legend(loc='upper left')
    ax1.xaxis.set_major_locator(MaxNLocator(10))
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %H:%M'))

    # Combined plot for recovery
    ax2 = plt.subplot(212)
    ax2.plot(recovery_times1, recovery_spike_data1['temp'], label=f'Temperature - {instrument_name1}', color='blue')
    ax2.plot(recovery_times2, recovery_spike_data2['temp'], label=f'Temperature - {instrument_name2}', color='red')
    ax2.set_title('Temperature During Recovery Spike Time')
    ax2.set_xlabel('Time')
    ax2.set_ylabel('Temperature (°C)')
    ax2.grid(True)
    ax2.legend(loc='upper left')
    ax2.xaxis.set_major_locator(MaxNLocator(10))
    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %H:%M'))

    plt.tight_layout()
    plt.savefig(f'{save_path}')
    # plt.close()


