import xarray as xr
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import math

def haversine_distance(lat1, lon1, lat2, lon2):
    """
    Calculate the great circle distance between two points 
    on the earth (specified in decimal degrees)
    """
    # Convert decimal degrees to radians
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    
    # Haversine formula
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    r = 6371  # Radius of earth in kilometers
    distance_km = r * c
    distance_nm = distance_km / 1.852  # Convert km to nautical miles
    
    return distance_km, distance_nm

def deployment_range_label(site_code, deployments):
    cleaned_deployments = [deployment.strip() for deployment in deployments if deployment.strip()]
    if not cleaned_deployments:
        return site_code

    return f"{site_code} {cleaned_deployments[0]}-{cleaned_deployments[-1]}"

def to_naive_datetime(values):
    datetime_values = pd.to_datetime(values, utc=True)
    return datetime_values.tz_localize(None)

def add_line_breaks_for_time_gaps(time, values, gap_factor=10):
    """
    Insert NaNs after large time-coordinate gaps so line plots do not connect
    the last valid point before a gap to the first valid point after it.
    """
    time_index = to_naive_datetime(np.asarray(time))
    values_array = np.asarray(values, dtype=float)

    if len(time_index) < 2:
        return time_index, values_array, pd.Timedelta(0), 0

    time_deltas = time_index[1:] - time_index[:-1]
    valid_deltas = time_deltas[time_deltas > pd.Timedelta(0)]
    if len(valid_deltas) == 0:
        return time_index, values_array, pd.Timedelta(0), 0

    sample_interval = valid_deltas.median()
    gap_threshold = sample_interval * gap_factor
    gap_after_indices = set(np.flatnonzero(time_deltas > gap_threshold))

    if not gap_after_indices:
        return time_index, values_array, gap_threshold, 0

    plot_times = []
    plot_values = []
    for i, (time_value, data_value) in enumerate(zip(time_index, values_array)):
        plot_times.append(time_value)
        plot_values.append(data_value)

        if i in gap_after_indices:
            plot_times.append(time_value + time_deltas[i] / 2)
            plot_values.append(np.nan)

    return to_naive_datetime(plot_times), np.asarray(plot_values), gap_threshold, len(gap_after_indices)

def add_line_breaks_for_missing_deployments(times, values, deployments):
    """
    Insert NaNs where deployment numbers skip, e.g. NTAS 14 to NTAS 16.
    """
    times = to_naive_datetime(times)
    values = np.asarray(values, dtype=float)
    deployment_numbers = []

    for deployment in deployments:
        try:
            deployment_numbers.append(int(deployment.strip()))
        except ValueError:
            deployment_numbers.append(None)

    if len(times) < 2:
        return times, values, 0

    plot_times = []
    plot_values = []
    missing_deployment_gaps = 0

    for i, (time_value, data_value) in enumerate(zip(times, values)):
        plot_times.append(time_value)
        plot_values.append(data_value)

        if i >= len(times) - 1:
            continue

        current_deployment = deployment_numbers[i]
        next_deployment = deployment_numbers[i + 1]
        if (
            current_deployment is not None
            and next_deployment is not None
            and next_deployment > current_deployment + 1
        ):
            plot_times.append(time_value + (times[i + 1] - time_value) / 2)
            plot_values.append(np.nan)
            missing_deployment_gaps += 1

    return to_naive_datetime(plot_times), np.asarray(plot_values), missing_deployment_gaps

def plot_temperature_and_distance(merged_dataset_path, output_path):
    """
    Plot temperature time series and cumulative distance between deployments.
    
    Parameters:
    merged_dataset_path (str): Path to the merged NetCDF file
    output_path (str): Path where to save the plot
    """
    
    # Load the merged dataset
    ds = xr.open_dataset(merged_dataset_path)
    site_code = ds.attrs.get('site_code', 'NTAS')
    
    # Extract deployment information from attributes
    deployments = ds.attrs.get('deployment', '').split(', ')
    latitudes = [float(lat.strip()) for lat in ds.attrs.get('latitude_anchor_survey', '').split(', ')]
    longitudes = [float(lon.strip()) for lon in ds.attrs.get('longitude_anchor_survey', '').split(', ')]
    reference_deployment = deployments[0].strip()
    deployment_label = deployment_range_label(site_code, deployments)
    
    # Calculate distances from the first deployment site.
    reference_lat, reference_lon = latitudes[0], longitudes[0]
    distances_from_ref = []
    
    for i, (lat, lon) in enumerate(zip(latitudes, longitudes)):
        if i == 0:
            distances_from_ref.append(0.0)
        else:
            dist_km, _ = haversine_distance(reference_lat, reference_lon, lat, lon)
            distances_from_ref.append(dist_km)
    
    # Debug: Print the distances
    print(f"Debug: Distances from {site_code} {reference_deployment}:")
    for i, (dep, dist) in enumerate(zip(deployments, distances_from_ref)):
        print(f"  {site_code} {dep}: {dist:.2f} km")
    
    # Create figure with two subplots with shared x-axis
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10), sharex=True)
    
    # Plot 1: Temperature time series
    temperature_time, temperature_values, gap_threshold, gap_count = add_line_breaks_for_time_gaps(
        ds.time.values,
        ds.sea_water_temperature.values
    )
    ax1.plot(temperature_time, temperature_values, 'b-', linewidth=0.8, alpha=0.8)
    if gap_count:
        print(
            f"Debug: Inserted {gap_count} temperature line break(s) for time gaps "
            f"larger than {gap_threshold}."
        )
    ax1.set_xlabel('Time', fontsize=12)
    ax1.set_ylabel('Temperature (°C)', fontsize=12)
    ax1.set_title(f'Deep Ocean Temperature Time Series ({deployment_label})', fontsize=14, fontweight='bold')
    ax1.grid(True, alpha=0.3)
    ax1.tick_params(axis='both', labelsize=10)
    # Show x-axis labels on top panel too
    ax1.tick_params(axis='x', labelbottom=True)
    
    # Add vertical lines for deployment boundaries if merge points are available
    if 'merge_point' in ds.attrs and ds.attrs['merge_point'] != 'None':
        merge_points = ds.attrs['merge_point'].split(', ')
        print(f"Debug: Found {len(merge_points)} merge points: {merge_points}")
        print(f"Debug: Found {len(deployments)} deployments: {deployments}")
        
        for i, point in enumerate(merge_points):
            try:
                merge_time = to_naive_datetime(point.strip())
                print(f"Debug: Plotting merge point {i}: {merge_time}")
                ax1.axvline(x=merge_time, color='red', linestyle='--', alpha=0.7, linewidth=1)
            except Exception as e:
                print(f"Error processing merge point {i}: {point}, Error: {e}")
    
    # Plot 2: Distance from the reference deployment
    # Create time points for each deployment location
    deployment_times = []
    
    # The first deployment starts at dataset beginning.
    deployment_times.append(to_naive_datetime(ds.time.min().values))
    
    # Subsequent deployments start at the remaining merge points.
    if 'merge_point' in ds.attrs and ds.attrs['merge_point'] != 'None':
        merge_points = ds.attrs['merge_point'].split(', ')
        for i in range(1, len(merge_points)):
            try:
                deployment_times.append(to_naive_datetime(merge_points[i].strip()))
            except:
                continue
    
    # Debug: Print the mapping
    print(f"Debug: Found {len(deployment_times)} deployment times")
    print(f"Debug: Found {len(distances_from_ref)} distances")  
    print(f"Debug: Found {len(deployments)} deployments")
    print(f"Debug: Deployment mapping:")
    for i, (dep, time) in enumerate(zip(deployments, deployment_times[:len(deployments)])):
        print(f"  {site_code} {dep}: starts at {time}")
    
    # Ensure arrays match - we should have exactly 11 points for 11 deployments
    deployment_times = deployment_times[:len(deployments)]
    
    distance_times, distance_values, missing_deployment_gaps = add_line_breaks_for_missing_deployments(
        deployment_times,
        distances_from_ref,
        deployments
    )
    if missing_deployment_gaps:
        print(f"Debug: Inserted {missing_deployment_gaps} distance line break(s) for skipped deployments.")

    ax2.plot(distance_times, distance_values, 'ro-', linewidth=2, markersize=8, markerfacecolor='red', 
            markeredgecolor='darkred', markeredgewidth=1)
    ax2.set_xlabel('Time', fontsize=12)
    ax2.set_ylabel(f'Distance from {site_code} {reference_deployment} (km)', fontsize=12)
    ax2.set_title(f'Distance from {site_code} {reference_deployment} Deployment Site', fontsize=14, fontweight='bold')
    ax2.grid(True, alpha=0.3)
    ax2.tick_params(axis='both', labelsize=10)
    
    # Add deployment labels on distance plot with smart positioning to avoid overlap
    for i, (time_point, dist, deployment) in enumerate(zip(deployment_times, distances_from_ref, deployments)):
        # Smart positioning for different deployment groups
        if i == 0:
            # S12: standard position above (now well-separated from others)
            xytext = (0, 12)
            ha = 'center'
            va = 'bottom'
        elif i == 1:
            # S13: label above and to the right to avoid S12
            xytext = (10, 20)
            ha = 'left' 
            va = 'bottom'
        elif i <= 6:
            # S14-S17: alternate above/below for the clustered low-distance points
            if i % 2 == 0:
                xytext = (0, 15)
                va = 'bottom'
            else:
                xytext = (0, -15)
                va = 'top'
            ha = 'center'
        else:
            # S18-S22: standard position above for high-distance points
            xytext = (0, 10)
            ha = 'center'
            va = 'bottom'
            
        ax2.annotate(f'{site_code}{deployment.strip()}', 
                    (time_point, dist), 
                    textcoords="offset points", 
                    xytext=xytext, 
                    ha=ha, 
                    va=va,
                    fontsize=11,
                    bbox=dict(boxstyle="round,pad=0.3", facecolor='white', alpha=0.8))
    
    # Set reasonable y-axis limits for distance plot
    max_dist = max(distances_from_ref)
    ax2.set_ylim(-0.5, max_dist * 1.1)
    
    # Adjust layout and save
    plt.tight_layout()
    plt.subplots_adjust(hspace=0.3)
    plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='white')
    plt.close()
    
    print(f"Temperature and distance plot saved to: {output_path}")
    
    # Print some summary statistics
    print(f"\nSummary Statistics:")
    print(f"Temperature range: {ds.sea_water_temperature.min().values:.3f} to {ds.sea_water_temperature.max().values:.3f} °C")
    print(f"Time coverage: {to_naive_datetime(ds.time.min().values).strftime('%Y-%m-%d')} to {to_naive_datetime(ds.time.max().values).strftime('%Y-%m-%d')}")
    print(f"Maximum distance from {site_code} {reference_deployment}: {max_dist:.2f} km")
    print(f"Total deployments: {len(deployments)}")

def plot_temperature_only(merged_dataset_path, output_path):
    """
    Plot only the temperature time series (single panel).
    """
    # Load the merged dataset
    ds = xr.open_dataset(merged_dataset_path)
    site_code = ds.attrs.get('site_code', 'NTAS')
    
    # Extract deployment information
    deployments = ds.attrs.get('deployment', '').split(', ')
    deployment_label = deployment_range_label(site_code, deployments)
    
    # Create single panel figure
    fig, ax = plt.subplots(1, 1, figsize=(14, 6))
    
    # Plot temperature time series
    temperature_time, temperature_values, _, _ = add_line_breaks_for_time_gaps(
        ds.time.values,
        ds.sea_water_temperature.values
    )
    ax.plot(temperature_time, temperature_values, 'b-', linewidth=0.8, alpha=0.8)
    ax.set_xlabel('Time', fontsize=12)
    ax.set_ylabel('Temperature (°C)', fontsize=12)
    ax.set_title(f'Deep Ocean Temperature Time Series ({deployment_label})', fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.tick_params(axis='both', labelsize=10)
    
    # Add vertical lines for deployment boundaries
    if 'merge_point' in ds.attrs and ds.attrs['merge_point'] != 'None':
        merge_points = ds.attrs['merge_point'].split(', ')
        for i, point in enumerate(merge_points):
            try:
                merge_time = to_naive_datetime(point.strip())
                ax.axvline(x=merge_time, color='red', linestyle='--', alpha=0.7, linewidth=1)
                # Add deployment labels
                if i < len(deployments) - 1:
                    ax.text(merge_time, ax.get_ylim()[1] * 0.95, f'{site_code} {deployments[i+1]}', 
                            rotation=90, verticalalignment='top', fontsize=8, color='red')
            except Exception as e:
                print(f"Error processing merge point {i}: {point}, Error: {e}")
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='white')
    plt.close()
    
    print(f"Temperature-only plot saved to: {output_path}")

if __name__ == "__main__":
    # Define paths
    project = 'NTAS'

    data_dir = f'/Users/Shared/ORS/DEEP_TS/{project}/merged_{project}' 
    merged_data_path = f'{data_dir}/merged_NTAS11_to_NTAS20.nc'
    output_dir = '/Users/yugao/UOP/ORS-processing/img'
    
    # Create the temperature and distance plot
    plot_temperature_and_distance(
        merged_data_path, 
        f'{output_dir}/temperature_and_distance_NTAS11_to_20.png'
    )
