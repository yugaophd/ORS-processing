import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator
import matplotlib.dates as mdates
import numpy as np
from geopy.distance import geodesic
import xarray as xr

# Function to convert time to naive datetime for comparisons
def to_naive_datetime(dt):
    if dt is None:
        return None
        
    # Convert string to datetime if needed
    if isinstance(dt, str):
        dt = pd.to_datetime(dt)
        
    # Remove timezone info if present
    if hasattr(dt, 'tzinfo') and dt.tzinfo is not None:
        dt = dt.replace(tzinfo=None)
        
    return dt
    
def find_var(ds, var_list):
    for var in var_list:
        if var in ds.variables:
            return var
    return None

# Function to safely convert dataset times to datetime
def safe_convert_dataset_times(ds):
    if len(ds.time) == 0:
        return []
        
    times = []
    for t in ds.time.values:
        if isinstance(t, np.datetime64):
            times.append(pd.Timestamp(t).to_pydatetime())
        elif hasattr(t, 'isoformat'):
            times.append(pd.to_datetime(t.isoformat()).to_pydatetime())
        else:
            times.append(pd.to_datetime(t).to_pydatetime())
    return times
    
def plot_spike_data(deployment_spike_data, 
                   recovery_spike_data, 
                   case_name, save_path, 
                   deployment_spike_start=None, 
                   deployment_spike_end=None, 
                   recovery_spike_start=None,
                   recovery_spike_end=None,
                   start_label="Spike starts", 
                   end_label="Spike ends"):
    """
    Plots temperature and salinity during deployment and recovery periods.
    """
    # Create figure
    plt.figure(figsize=(12, 10))
    
    # Handle None datasets and empty datasets
    deployment_empty = True  # Default to empty
    if deployment_spike_data is not None:
        deployment_empty = len(deployment_spike_data.time) == 0
    
    recovery_empty = True  # Default to empty
    if recovery_spike_data is not None:
        recovery_empty = len(recovery_spike_data.time) == 0
    
    # Normalize deployment and recovery times
    deployment_spike_start_naive = to_naive_datetime(deployment_spike_start)
    deployment_spike_end_naive = to_naive_datetime(deployment_spike_end)
    recovery_spike_start_naive = to_naive_datetime(recovery_spike_start)
    recovery_spike_end_naive = to_naive_datetime(recovery_spike_end)
    
    # Find temperature and salinity variable names in each dataset
    temp_vars = ['sea_water_temperature', 'temp']
    sal_vars = ['sea_water_practical_salinity', 'sea_water_salinity', 'sal']
    
    # Determine plot titles
    deployment_title = f'Temperature/Salinity During Deployment Spike Time - {case_name}'
    recovery_title = f'Temperature/Salinity During Recovery Spike Time - {case_name}'
    
    # Plot for deployment 
    ax1 = plt.subplot(211)
    
    # Only try to plot if we have both data and spike times
    if not deployment_empty and deployment_spike_start is not None:
        # Get variable names
        temp_var = find_var(deployment_spike_data, temp_vars)
        sal_var = find_var(deployment_spike_data, sal_vars)
        
        if temp_var:
            # Convert time values safely
            deployment_times = safe_convert_dataset_times(deployment_spike_data)
            
            # Plot temperature
            ax1.plot(deployment_times, deployment_spike_data[temp_var], 
                    color='blue', label='Temperature')
            
            # Only draw vertical lines if spike times are provided
            if deployment_spike_start_naive is not None and deployment_times:
                try:
                    # Draw start vertical line
                    ax1.axvline(x=deployment_spike_start_naive, 
                                color='green', 
                                linestyle='--',
                                alpha=0.7)
                    
                    # Format timestamp for display
                    time_str = deployment_spike_start_naive.strftime('%Y-%m-%d %H:%M')
                    
                    # Add start annotation with box (like in deployment_recovery)
                    y_pos = ax1.get_ylim()[0] + (ax1.get_ylim()[1] - ax1.get_ylim()[0]) * 0.6
                    ax1.annotate(
                        f"{start_label}\n{time_str}", 
                        xy=(deployment_spike_start_naive, y_pos),
                        xytext=(-80, 0), textcoords="offset points",
                        arrowprops=dict(arrowstyle="-", connectionstyle="arc3,rad=0", color="green"),
                        bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="green", alpha=0.8),
                        fontsize=10
                    )
                    
                    # Only attempt to draw end line if end time is also provided
                    if deployment_spike_end_naive is not None:
                        # Draw end vertical line
                        ax1.axvline(x=deployment_spike_end_naive, 
                                    color='Red', 
                                    linestyle='--',
                                    alpha=0.7)
                        
                        # Format end timestamp
                        end_time_str = deployment_spike_end_naive.strftime('%Y-%m-%d %H:%M')
                        
                        # Add end annotation with box (like in deployment_recovery)
                        y_pos = ax1.get_ylim()[0] + (ax1.get_ylim()[1] - ax1.get_ylim()[0]) * 0.8
                        ax1.annotate(
                            f"{end_label}\n{end_time_str}", 
                            xy=(deployment_spike_end_naive, y_pos),
                            xytext=(20, 0), textcoords="offset points",
                            arrowprops=dict(arrowstyle="-", connectionstyle="arc3,rad=0", color="red"),
                            bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="red", alpha=0.8),
                            fontsize=10
                        )
                        
                        # Calculate and display spike duration
                        duration = deployment_spike_end_naive - deployment_spike_start_naive
                        hours, remainder = divmod(duration.total_seconds(), 3600)
                        minutes, _ = divmod(remainder, 60)
                        
                        # Add box with spike duration
                        textstr = f"Spike duration: {int(hours)}h {int(minutes)}m"
                        props = dict(boxstyle="round,pad=0.3", facecolor="lightyellow", alpha=0.8)
                        ax1.text(0.5, 0.98, textstr, transform=ax1.transAxes, fontsize=10,
                               verticalalignment="top", bbox=props)
                        
                except Exception as e:
                    print(f"Error adding deployment lines: {e}")
            
            # Always plot salinity if available, regardless of spike times
            if sal_var:
                ax2 = ax1.twinx()
                ax2.plot(deployment_times, deployment_spike_data[sal_var], 
                        color='Orange', label='Salinity')
                ax2.set_ylabel('Salinity (psu)')
                ax2.legend(loc='upper right')
                
            ax1.grid(True, alpha=0.3)
            ax1.xaxis.set_major_locator(MaxNLocator(10))
            ax1.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %H:%M'))
            ax1.legend(loc='center left')
    else:
        message = 'No deployment spike times available' if deployment_spike_start is None else 'No deployment data available'
        ax1.text(0.5, 0.5, message, ha='center', va='center', transform=ax1.transAxes)
    
    ax1.set_title(deployment_title, fontsize=14)
    ax1.set_xlabel('Time')
    ax1.set_ylabel('Temperature (°C)')
    
    # Plot for recovery 
    ax3 = plt.subplot(212)
    
    # Only try to plot if we have both data and spike times
    if not recovery_empty and recovery_spike_start is not None:
        # Get variable names
        temp_var = find_var(recovery_spike_data, temp_vars)
        sal_var = find_var(recovery_spike_data, sal_vars)
        
        if temp_var:
            # Convert time values safely
            recovery_times = safe_convert_dataset_times(recovery_spike_data)
            
            # Plot temperature (always)
            ax3.plot(recovery_times, recovery_spike_data[temp_var], 
                    color='blue', label='Temperature')
            
            # Only add vertical lines if spike times are provided
            if recovery_spike_start_naive is not None and recovery_times:
                try:
                    # Draw start vertical line
                    ax3.axvline(x=recovery_spike_start_naive, 
                              color='green', 
                              linestyle='--',
                              alpha=0.7)
                    
                    # Format timestamp for display
                    time_str = recovery_spike_start_naive.strftime('%Y-%m-%d %H:%M')
                    
                    # Add start annotation with box (like in deployment_recovery)
                    y_pos = ax3.get_ylim()[0] + (ax3.get_ylim()[1] - ax3.get_ylim()[0]) * 0.6
                    ax3.annotate(
                        f"{start_label}\n{time_str}", 
                        xy=(recovery_spike_start_naive, y_pos),
                        xytext=(-80, 0), textcoords="offset points",
                        arrowprops=dict(arrowstyle="-", connectionstyle="arc3,rad=0", color="green"),
                        bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="green", alpha=0.8),
                        fontsize=10
                    )
                    
                    # Only attempt to draw end line if end time is also provided
                    if recovery_spike_end_naive is not None:
                        # Draw end vertical line
                        ax3.axvline(x=recovery_spike_end_naive, 
                                      color='red', 
                                      linestyle='--',
                                      alpha=0.7)
                        
                        # Format end timestamp
                        end_time_str = recovery_spike_end_naive.strftime('%Y-%m-%d %H:%M')
                        
                        # Add end annotation with box (like in deployment_recovery)
                        y_pos = ax3.get_ylim()[0] + (ax3.get_ylim()[1] - ax3.get_ylim()[0]) * 0.8
                        ax3.annotate(
                            f"{end_label}\n{end_time_str}", 
                            xy=(recovery_spike_end_naive, y_pos),
                            xytext=(20, 0), textcoords="offset points",
                            arrowprops=dict(arrowstyle="-", connectionstyle="arc3,rad=0", color="red"),
                            bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="red", alpha=0.8),
                            fontsize=10
                        )
                        
                        # Calculate and display spike duration
                        duration = recovery_spike_end_naive - recovery_spike_start_naive
                        hours, remainder = divmod(duration.total_seconds(), 3600)
                        minutes, _ = divmod(remainder, 60)
                        
                        # Add box with spike duration
                        textstr = f"Spike duration: {int(hours)}h {int(minutes)}m"
                        props = dict(boxstyle="round,pad=0.3", facecolor="lightyellow", alpha=0.8)
                        ax3.text(0.5, 0.98, textstr, transform=ax3.transAxes, fontsize=10,
                               verticalalignment="top", bbox=props)
                        
                except Exception as e:
                    print(f"Error adding recovery lines: {e}")
            
            # Always plot salinity if available, regardless of spike times
            if sal_var:
                ax4 = ax3.twinx()
                ax4.plot(recovery_times, recovery_spike_data[sal_var], 
                        color='Orange', label='Salinity')
                ax4.set_ylabel('Salinity (psu)')
                ax4.legend(loc='upper right')
            
            ax3.grid(True, alpha=0.3)
            ax3.xaxis.set_major_locator(MaxNLocator(10))
            ax3.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %H:%M'))
            ax3.legend(loc='upper left')
    else:
        message = 'No recovery spike times available' if recovery_spike_start is None else 'No recovery data available'
        ax3.text(0.5, 0.5, message, ha='center', va='center', transform=ax3.transAxes)
    
    ax3.set_title(recovery_title, fontsize=14)
    ax3.set_xlabel('Time')
    ax3.set_ylabel('Temperature (°C)')
    
    plt.tight_layout()
    plt.savefig(f'{save_path}', dpi=300)
    plt.close()
def plot_deployment_recovery(deployment_spike_data, 
                           recovery_spike_data, 
                           case_name, save_path, 
                           deployment_time=None, recovery_time=None,
                           deployment_label="Deployment", 
                           recovery_label="Recovery"):
    """
    Plots temperature and salinity during deployment and recovery periods.

    Parameters:
    - deployment_spike_data (xarray.Dataset): Dataset slice for the deployment period.
    - recovery_spike_data (xarray.Dataset): Dataset slice for the recovery period.
    - case_name (str): Case name used for saving the plots.
    - save_path (str): Path to save the plotted figures.
    - deployment_time (datetime or str): Time of deployment to mark with vertical line
    - recovery_time (datetime or str): Time of recovery to mark with vertical line
    - deployment_label (str): Label for the deployment vertical line
    - recovery_label (str): Label for the recovery vertical line
    """
    # Create figure
    plt.figure(figsize=(12, 10))
    
    # Handle empty datasets
    deployment_empty = len(deployment_spike_data.time) == 0
    recovery_empty = len(recovery_spike_data.time) == 0
    
    # Normalize deployment and recovery times
    deployment_time_naive = to_naive_datetime(deployment_time)
    recovery_time_naive = to_naive_datetime(recovery_time)
    
    # Find temperature and salinity variable names in each dataset
    temp_vars = ['sea_water_temperature', 'temp']
    sal_vars = ['sea_water_practical_salinity', 'sea_water_salinity', 'sal']
    
    # Determine plot titles
    deployment_title = f'Temperature/Salinity During Deployment - {case_name}'
    recovery_title = f'Temperature/Salinity During Recovery - {case_name}'
    
    # Plot for deployment 
    ax1 = plt.subplot(211)
    
    if not deployment_empty:
        # Get variable names
        temp_var = find_var(deployment_spike_data, temp_vars)
        sal_var = find_var(deployment_spike_data, sal_vars)
        
        if temp_var:
            # Convert time values safely
            deployment_times = safe_convert_dataset_times(deployment_spike_data)
            
            # Plot temperature
            ax1.plot(deployment_times, deployment_spike_data[temp_var], 
                    color='blue', label='Temperature')
            
            # Add deployment time vertical line if provided
            if deployment_time_naive is not None:
                try:
                    # Check if the time is within range (approximately)
                    if len(deployment_times) > 0:
                        time_min = min(deployment_times)
                        time_max = max(deployment_times)
                        
                        # Only draw line if it's reasonably close to the data range
                        # Using a buffer of 30 days to account for different time ranges
                        buffer = pd.Timedelta(days=30)
                        if (time_min - buffer) <= deployment_time_naive <= (time_max + buffer):
                            # Draw vertical line
                            ax1.axvline(x=deployment_time_naive, color='green', linestyle='--', 
                                      linewidth=1.5, label='Deployment Time', alpha=0.7)
                            
                            # Format timestamp for display
                            time_str = deployment_time_naive.strftime('%Y-%m-%d %H:%M')
                            
                            # Add label with better positioning and background
                            y_pos = ax1.get_ylim()[0] + (ax1.get_ylim()[1] - ax1.get_ylim()[0]) * 0.65
                            ax1.annotate(
                                f"{deployment_label}\n{time_str}", 
                                xy=(deployment_time_naive, y_pos),
                                xytext=(-80, 0), textcoords="offset points",
                                arrowprops=dict(arrowstyle="-", connectionstyle="arc3,rad=0", color="green"),
                                bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="green", alpha=0.8),
                                fontsize=9
                            )
                except Exception as e:
                    print(f"Error adding deployment start line: {e}")
            
            # Add salinity plot if available
            if sal_var:
                ax2 = ax1.twinx()
                ax2.plot(deployment_times, deployment_spike_data[sal_var], 
                        color='Orange', label='Salinity')
                ax2.set_ylabel('Salinity (psu)')
                ax2.legend(loc='upper right')
                
            ax1.grid(True, alpha=0.3)
            ax1.xaxis.set_major_locator(MaxNLocator(10))
            ax1.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %H:%M'))
            ax1.legend(loc='upper left')
    else:
        ax1.text(0.5, 0.5, 'No deployment data available', 
                ha='center', va='center', transform=ax1.transAxes)
    
    ax1.set_title(deployment_title, fontsize=14)
    ax1.set_xlabel('Time')
    ax1.set_ylabel('Temperature (°C)')
    
    # Plot for recovery 
    ax3 = plt.subplot(212)
    
    if not recovery_empty:
        # Get variable names
        temp_var = find_var(recovery_spike_data, temp_vars)
        sal_var = find_var(recovery_spike_data, sal_vars)
        
        if temp_var:
            # Convert time values safely
            recovery_times = safe_convert_dataset_times(recovery_spike_data)
            
            # Plot temperature
            ax3.plot(recovery_times, recovery_spike_data[temp_var], 
                    color='blue', label='Temperature')
            
            # Add recovery time vertical line if provided
            if recovery_time_naive is not None:
                try:
                    # Check if the time is within range (approximately)
                    if len(recovery_times) > 0:
                        time_min = min(recovery_times)
                        time_max = max(recovery_times)
                        
                        # Only draw line if it's reasonably close to the data range
                        # Using a buffer of 30 days to account for different time ranges
                        buffer = pd.Timedelta(days=30)
                        if (time_min - buffer) <= recovery_time_naive <= (time_max + buffer):
                            # Draw vertical line
                            ax3.axvline(x=recovery_time_naive, color='red', linestyle='--', 
                                      linewidth=1.5, label='Recovery Time', alpha=0.7)
                            
                            # Format timestamp for display
                            time_str = recovery_time_naive.strftime('%Y-%m-%d %H:%M')
                            
                            # Add label with better positioning and background
                            y_pos = ax3.get_ylim()[0] + (ax3.get_ylim()[1] - ax3.get_ylim()[0]) * 0.65
                            ax3.annotate(
                                f"{recovery_label}\n{time_str}", 
                                xy=(recovery_time_naive, y_pos),
                                xytext=(20, 0), textcoords="offset points",
                                arrowprops=dict(arrowstyle="-", connectionstyle="arc3,rad=0", color="red"),
                                bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="red", alpha=0.8),
                                fontsize=9
                            )
                except Exception as e:
                    print(f"Error adding recovery line: {e}")
            
            # Add salinity plot if available
            if sal_var:
                ax4 = ax3.twinx()
                ax4.plot(recovery_times, recovery_spike_data[sal_var], 
                        color='Orange', label='Salinity')
                ax4.set_ylabel('Salinity (psu)')
                ax4.legend(loc='upper right')
            
            ax3.grid(True, alpha=0.3)
            ax3.xaxis.set_major_locator(MaxNLocator(10))
            ax3.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %H:%M'))
            ax3.legend(loc='upper left')
    else:
        ax3.text(0.5, 0.5, 'No recovery data available', 
                ha='center', va='center', transform=ax3.transAxes)
    
    ax3.set_title(recovery_title, fontsize=14)
    ax3.set_xlabel('Time')
    ax3.set_ylabel('Temperature (°C)')
    
    plt.tight_layout()
    plt.savefig(f'{save_path}', dpi=300)
    plt.close()


def _build_gap_masked_series(da, gap_threshold_hours=48):
    """
    Return (times, values) arrays with np.nan inserted immediately after any time gap
    larger than gap_threshold_hours so matplotlib does not draw a connecting line.
    """
    import numpy as np, pandas as pd
    times = pd.to_datetime(da.time.values)
    vals  = da.values.copy().astype(float)
    # Replace fill values with NaN
    vals[vals == -99999.0] = np.nan

    diffs_h = np.diff(times.astype('int64')) / 1e9 / 3600  # seconds -> hours
    insert_indices = np.where(diffs_h > gap_threshold_hours)[0] + 1  # insert before these

    if len(insert_indices) == 0:
        return times, vals

    # Insert NaN rows at each gap boundary
    out_times = np.insert(times, insert_indices, times[insert_indices])
    out_vals  = np.insert(vals,  insert_indices, np.nan)
    return out_times, out_vals


def plot_merge_points(dataset, axes, color='gray', linestyle='--', linewidth=1.5, 
                     alpha=0.7, annotate=False):
    """
    Add vertical lines for merge points to a plot.
    
    Parameters:
    -----------
    dataset : xarray.Dataset
        Dataset containing merge_point attribute
    axes : list or array of matplotlib.axes
        Axes to add vertical lines to
    color : str
        Color for the merge point lines (now defaults to gray)
    linestyle : str
        Line style for merge point lines
    linewidth : float
        Width of merge point lines
    alpha : float
        Transparency of merge point lines
    annotate : bool
        Whether to add text annotations for merge points
    
    Returns:
    --------
    list of Line2D objects
    """
    merge_points_str = dataset.attrs.get('merge_point', None)
    if not merge_points_str or merge_points_str == 'None':
        print("No merge points found in dataset attributes")
        return None
    
    merge_points = []
    for point in merge_points_str.split(', '):
        # Skip NaT values - these cause the error
        if point and point.lower() != 'none' and point.lower() != 'nat':
            try:
                dt_point = pd.to_datetime(point)
                if pd.notna(dt_point):  # Skip NaT values after conversion
                    merge_points.append(dt_point)
            except Exception as e:
                print(f"Could not parse merge point: {point} - {e}")
    
    lines = []
    if not merge_points:
        print("No valid merge points found to plot")
        return lines
    
    # Make sure axes is iterable
    if not hasattr(axes, '__len__'):
        axes = [axes]
    
    for ax in axes:
        for i, point in enumerate(merge_points):
            # Only label the first axis to avoid duplicate legend entries
            label = 'Merge Point' if (i == 0 and ax == axes[0]) else None
            line = ax.axvline(point, color=color, linestyle=linestyle, 
                            linewidth=linewidth, alpha=alpha, label=label)
            lines.append(line)
            
            # Add annotation if requested
            if annotate:
                ymin, ymax = ax.get_ylim()
                y_pos = ymin + 0.95 * (ymax - ymin)  # 95% up the axis
                ax.text(point, y_pos, f'Merge {i+1}', 
                       rotation=90, verticalalignment='top', 
                       color=color, fontsize=9, alpha=alpha)
    
    return lines
def plot_merged_dataset(dataset, save_path, case_name0=None, case_name1=None, figsize=(12, 12),
                      variables=None, colors=None, titles=None, add_merge_points=True,
                      annotate_merge_points=False):
    """
    Plot merged dataset with multiple variables and optional merge point lines.
    Includes a panel showing distance from Stratus 12 and between consecutive sites.
    """
    # Default variables to plot if not specified
    if variables is None:
        variables = [
            'sea_water_temperature',
            # 'sea_water_practical_salinity', 
            # 'sea_water_pressure',
            # 'sea_water_electrical_conductivity',
            # 'sea_water_absolute_salinity'
        ]
    
    # Default colors if not specified
    if colors is None:
        colors = ['red', 'green', 'purple', 'blue', 'orange']
    
    # Default titles if not specified
    if titles is None:
        titles = [
            'Temperature ',
            'Practical Salinity ',
            'Pressure ',
            'Conductivity ',
            'Absolute Salinity '
        ]
    
    # Extract available variables from the dataset
    available_vars = []
    for var in variables:
        if var in dataset:
            available_vars.append(var)
        else:
            print(f"Warning: Variable '{var}' not found in dataset.")
    
    # Add one more row for the distance panel
    n_plots = len(available_vars) + 1
    
    # Create figure with appropriate number of subplots
    if n_plots == 0:
        print("No variables to plot. Check that your dataset contains the specified variables.")
        return None
        
    fig, axs = plt.subplots(n_plots, 1, figsize=figsize, sharex=True)
    
    # Handle case of single subplot
    if n_plots == 1:
        axs = [axs]
    
    # Plot each variable (use only n_plots-1 axes for variables)
    for i, var in enumerate(available_vars):
        if i >= n_plots - 1:  # Skip if we've run out of axes
            break
            
        idx = variables.index(var)  # Get original index for color and title
        _t, _v = _build_gap_masked_series(dataset[var])
        axs[i].plot(_t, _v,
                  label=var.replace('_', ' ').title(), 
                  color=colors[idx % len(colors)])
        axs[i].set_title(titles[idx] if idx < len(titles) else var.replace('_', ' ').title())
        axs[i].set_ylabel(dataset[var].attrs.get('units', ''))
        axs[i].legend()
        axs[i].grid(True)
    
    # Calculate distances
    distance_da = calculate_distance_from_reference(dataset)
    consecutive_distance_da = calculate_consecutive_distances(dataset)

    # Derive reference label from dataset attributes
    _platform = dataset.attrs.get('platform_code', '').split(',')[0].strip()
    _first_deploy = dataset.attrs.get('deployment', '').split(',')[0].strip()
    _ref_label = f"{_platform} {_first_deploy}" if _first_deploy else _platform

    if distance_da is not None:
        # Use the last axis for distance
        dist_ax = axs[-1]
        dist_ax.plot(distance_da.time, distance_da, color='darkred', drawstyle='steps-post', 
                   linewidth=2, label=f'Distance from {_ref_label}')
        dist_ax.set_title(f'{_platform} Site Distances')
        dist_ax.set_ylabel(f'Distance from {_ref_label} (km)')
        dist_ax.grid(True)
        dist_ax.legend(loc='upper left')
        
        # Add second axis for consecutive distances
        if consecutive_distance_da is not None:
            dist_ax2 = dist_ax.twinx()  # Create a second y-axis 
            dist_ax2.plot(consecutive_distance_da.time, consecutive_distance_da, 
                          color='navy', drawstyle='steps-post', linewidth=1.8, 
                          linestyle='-', label='Distance from previous deployment site')
            dist_ax2.set_ylabel('Distance from previous deployment site (km)', color='navy')
            dist_ax2.tick_params(axis='y', colors='navy')
            dist_ax2.legend(loc='center left')
    else:
        axs[-1].text(0.5, 0.5, 'Distance data not available',
                    ha='center', va='center', transform=axs[-1].transAxes)
    
    # Add merge points if requested
    if add_merge_points:
        merge_line = plot_merge_points(dataset, axs, annotate=annotate_merge_points)
    
    # Set common X-axis label
    axs[-1].set_xlabel('Time')
    
    # Add time coverage information
    # if 'time_coverage_start' in dataset.attrs and 'time_coverage_end' in dataset.attrs:
    #     time_start = pd.to_datetime(dataset.attrs['time_coverage_start']).strftime('%Y-%m-%d')
    #     time_end = pd.to_datetime(dataset.attrs['time_coverage_end']).strftime('%Y-%m-%d')
    #     fig.suptitle(f"Time Series Data: {time_start} to {time_end}", fontsize=12)
    # Add time coverage information (derive from coordinates instead of attrs)
    if "time" in dataset.coords:
        t = pd.to_datetime(dataset["time"].values)
        time_start = pd.Timestamp(t.min()).strftime("%Y-%m-%d")
        time_end   = pd.Timestamp(t.max()).strftime("%Y-%m-%d")
        fig.suptitle(f"Time Series Data: {time_start} to {time_end}", fontsize=12)

    
    # Adjust layout
    plt.tight_layout()
    if 'time_coverage_start' in dataset.attrs:
        plt.subplots_adjust(top=0.95)
    
    # Save figure
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    print(f"Figure saved to {save_path}")
    
    return fig
def calculate_distance_timeseries(dataset):
    """
    Calculate the distance in kilometers from the Stratus 12 reference position
    for each time point based on merge points.
    
    Returns a DataArray with distance values.
    """
    # Extract anchor survey coordinates
    lat_str = dataset.attrs.get('latitude_anchor_survey', '')
    lon_str = dataset.attrs.get('longitude_anchor_survey', '')
    
    # if not lat_str or not lon_str:
    #     print("Warning: Missing anchor survey coordinates")
    #     return None
        
    # Parse coordinates into lists
    try:
        lats = [float(x.strip()) for x in lat_str.split(',')]
        lons = [float(x.strip()) for x in lon_str.split(',')]
        
        # Stratus 12 is the reference position (first in the list)
        ref_lat, ref_lon = lats[0], lons[0]
        
        # Create a dictionary of positions for each deployment
        positions = []
        for i in range(len(lats)):
            dist = geodesic((ref_lat, ref_lon), (lats[i], lons[i])).kilometers
            positions.append((lats[i], lons[i], dist))
            print(f"Deployment {i+12} position: ({lats[i]}, {lons[i]}), Distance from Stratus 12: {dist:.2f} km")
    except Exception as e:
        print(f"Error parsing coordinates: {e}")
        return None
    
    # Get merge points
    merge_points_str = dataset.attrs.get('merge_point', '')
    if not merge_points_str:
        print("Warning: No merge points found")
        return None
        
    # Parse merge points
    merge_times = []
    for point in merge_points_str.split(', '):
        if point and point.lower() != 'none':
            try:
                merge_times.append(pd.to_datetime(point))
            except Exception as e:
                print(f"Could not parse merge point: {point} - {e}")
                
    # Add dataset start time as first point
    start_time = pd.to_datetime(dataset.attrs.get('time_coverage_start'))
    all_times = [start_time] + merge_times
    
    # Create distance array
    times = dataset.time.values
    distances = np.zeros(len(times))
    
    # First segment (Stratus 12)
    distances[:] = positions[0][2]  # Distance is 0 for Stratus 12
    
    # Update distance for each segment
    for i in range(1, len(all_times)):
        if i <= len(positions):
            # Find indices for this time segment
            if i < len(all_times)-1:
                mask = (times >= np.datetime64(all_times[i])) & (times < np.datetime64(all_times[i+1]))
            else:
                mask = (times >= np.datetime64(all_times[i]))
            
            # Set distance for this segment
            distances[mask] = positions[i][2]
    
    # Create a DataArray with the distances
    distance_da = xr.DataArray(
        distances,
        coords={'time': dataset.time},
        dims=['time'],
        attrs={
            'long_name': 'Distance from Stratus 12 reference position',
            'units': 'kilometers',
            'reference_latitude': ref_lat,
            'reference_longitude': ref_lon
        }
    )
    
    return distance_da

def calculate_distance_from_reference(dataset):
    """Calculate distance from reference position for a merged dataset."""
    try:
        # Get latitude and longitude from dataset attributes
        lat_str = dataset.attrs.get('latitude_anchor_survey', '')
        lon_str = dataset.attrs.get('longitude_anchor_survey', '')
        
        if not lat_str or not lon_str:
            print("Missing coordinate attributes for distance calculation")
            return None
        
        # Parse comma-separated coordinates
        try:
            latitudes = [float(lat.strip()) for lat in lat_str.split(',')]
            longitudes = [float(lon.strip()) for lon in lon_str.split(',')]
        except ValueError as e:
            print(f"Error parsing coordinates: {e}")
            return None
            
        # Use first point as reference
        ref_lat = latitudes[0]
        ref_lon = longitudes[0]
        
        # Create times and distance array
        times = dataset.time.values
        distances = np.full(len(times), np.nan)  # Using NaN for the first segment
        
        # Get merge points for segmentation
        merge_points_str = dataset.attrs.get('merge_point', '')
        merge_points = []
        
        if merge_points_str:
            for point in merge_points_str.split(','):
                point = point.strip()
                if point and point.lower() != 'none' and point.lower() != 'nat':
                    try:
                        dt_point = to_naive_datetime(point)
                        if dt_point is not None:
                            merge_points.append(dt_point)
                    except Exception as e:
                        print(f"Could not parse merge point: {point} - {e}")
                        continue
        
        # Add a check to ensure we have proper ordering
        merge_points = sorted(merge_points)
        
        # Calculate distances by properly segmenting the time series
        for i, time in enumerate(times):
            time_i = to_naive_datetime(time)
            
            # Determine which segment this time belongs to
            segment_idx = 0  # Default to segment 0 (First site)
            for j, merge_point in enumerate(merge_points[1:], 1):  # Skip first merge point
                if time_i >= merge_point:
                    segment_idx = j
            
            # Segment 0 is NaN, all others get distance calculated
            if segment_idx == 0:
                continue  # Keep as NaN
            elif segment_idx < len(latitudes):
                lat2 = latitudes[segment_idx]  # Use appropriate position
                lon2 = longitudes[segment_idx]
                # USE THE SAME FUNCTION FOR BOTH DISTANCES
                distances[i] = geodesic((ref_lat, ref_lon), (lat2, lon2)).kilometers
        
        return xr.DataArray(
            data=distances,
            dims=["time"],
            coords={"time": dataset.time},
            attrs={"units": "km", "long_name": "Distance from reference position"}
        )
        
    except Exception as e:
        print(f"Error calculating distances: {e}")
        return None

def calculate_consecutive_distances(dataset):
    """Calculate distances between consecutive deployment sites."""
    try:
        # Get latitude and longitude from dataset attributes
        lat_str = dataset.attrs.get('latitude_anchor_survey', '')
        lon_str = dataset.attrs.get('longitude_anchor_survey', '')
        
        if not lat_str or not lon_str:
            print("Missing coordinate attributes for consecutive distance calculation")
            return None
        
        # Parse comma-separated coordinates
        try:
            latitudes = [float(lat.strip()) for lat in lat_str.split(',')]
            longitudes = [float(lon.strip()) for lon in lon_str.split(',')]
        except ValueError as e:
            print(f"Error parsing coordinates for consecutive distances: {e}")
            return None
            
        # Create times and distance array
        times = dataset.time.values
        distances = np.full(len(times), np.nan)  # Using NaN for the first segment
        
        # Get merge points for segmentation
        merge_points_str = dataset.attrs.get('merge_point', '')
        merge_points = []
        
        if merge_points_str:
            for point in merge_points_str.split(','):
                point = point.strip()
                if point and point.lower() != 'none' and point.lower() != 'nat':
                    try:
                        dt_point = to_naive_datetime(point)
                        if dt_point is not None:
                            merge_points.append(dt_point)
                    except Exception as e:
                        print(f"Could not parse merge point: {point} - {e}")
                        continue
        
        # Skip if we don't have enough merge points or sites
        if len(merge_points) < 2 or len(latitudes) < 2:
            print("Not enough merge points or sites for consecutive distance calculation")
            return None
            
        # Sort merge points
        merge_points = sorted(merge_points)
        
        # Calculate distances between consecutive sites
        for i, time in enumerate(times):
            time_i = to_naive_datetime(time)
            
            # Determine which segment this time belongs to
            segment_idx = 0  # Default to segment 0 (Stratus 12)
            for j, merge_point in enumerate(merge_points[1:], 1):  # Skip first merge point
                if time_i >= merge_point:
                    segment_idx = j
            
            # Skip first segment (keep as NaN)
            if segment_idx == 0:
                continue
            elif segment_idx < len(latitudes):
                # Calculate distance between THIS site and PREVIOUS site
                current_idx = segment_idx
                previous_idx = segment_idx - 1
                
                lat1 = latitudes[previous_idx]
                lon1 = longitudes[previous_idx]
                lat2 = latitudes[current_idx]  
                lon2 = longitudes[current_idx]
                
                # USE THE SAME FUNCTION FOR BOTH DISTANCES
                distances[i] = geodesic((lat1, lon1), (lat2, lon2)).kilometers
        
        return xr.DataArray(
            data=distances,
            dims=["time"],
            coords={"time": dataset.time},
            attrs={"units": "km", "long_name": "Distance between consecutive deployment sites"}
        )
        
    except Exception as e:
        print(f"Error calculating consecutive distances: {e}")
        return None
def plot_deployment_locations():
    """
    Plots the locations of deployments on a map, coloring by deployment number.
    """
    # Extract unique deployments
    deployments = list(set([dep.strip() for dep in 
                            ', '.join([ds.attrs.get('deployment'), ds.attrs.get('merge_point')]).split(', ') 
                            if dep and dep != 'None']))
    
    # Sort deployments numerically
    deployments.sort(key=lambda x: int(x.split()[-1]))
    
    # Create a figure
    plt.figure(figsize=(12, 10))
    
    # Define color map
    cmap = plt.get_cmap("tab10", len(deployments))  # Use tab10 colormap, limited to number of deployments
    
    # Plot each deployment location
    for i, deployment in enumerate(deployments):
        # Extract latitude and longitude for this deployment
        lat_str = dataset.attrs.get(f'latitude_{deployment}', '')
        lon_str = dataset.attrs.get(f'longitude_{deployment}', '')
        
        if lat_str and lon_str:
            try:
                lat = float(lat_str)
                lon = float(lon_str)
                
                # Plot the location
                plt.scatter(lon, lat, 
                            color=cmap(i),  # Use colormap
                            s=100,  # Increased size for visibility
                            label=deployment,
                            edgecolor='black', linewidth=1.5)
            except ValueError as e:
                print(f"Error plotting deployment {deployment}: {e}")
                continue
    
    # Add labels and legend
    plt.title('Deployment Locations', fontsize=16)
    plt.xlabel('Longitude')
    plt.ylabel('Latitude')
    plt.legend(title='Deployments', bbox_to_anchor=(1.05, 1), loc='upper left')
    
    # Show grid
    plt.grid(True, linestyle='--', alpha=0.7)
    
    # Adjust layout
    plt.tight_layout()
    
    # Save the figure
    plt.savefig('deployment_locations.png', dpi=300)
    plt.close()
