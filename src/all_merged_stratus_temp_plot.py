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

def plot_temperature_and_distance(merged_dataset_path, output_path):
    """
    Plot temperature time series and cumulative distance between deployments.
    
    Parameters:
    merged_dataset_path (str): Path to the merged NetCDF file
    output_path (str): Path where to save the plot
    """
    
    # Load the merged dataset
    ds = xr.open_dataset(merged_dataset_path)
    
    # Extract deployment information from attributes
    deployments = ds.attrs.get('deployment', '').split(', ')
    latitudes = [float(lat.strip()) for lat in ds.attrs.get('latitude_anchor_survey', '').split(', ')]
    longitudes = [float(lon.strip()) for lon in ds.attrs.get('longitude_anchor_survey', '').split(', ')]
    
    # Calculate distances from Stratus 12 (reference point)
    reference_lat, reference_lon = latitudes[0], longitudes[0]
    distances_from_ref = []
    
    for i, (lat, lon) in enumerate(zip(latitudes, longitudes)):
        if i == 0:
            # Stratus 12 is the reference point, so distance is 0
            distances_from_ref.append(0.0)
        else:
            dist_km, _ = haversine_distance(reference_lat, reference_lon, lat, lon)
            distances_from_ref.append(dist_km)
    
    # Debug: Print the distances
    print(f"Debug: Distances from Stratus 12:")
    for i, (dep, dist) in enumerate(zip(deployments, distances_from_ref)):
        print(f"  S{dep}: {dist:.2f} km")
    
    # Create figure with two subplots with shared x-axis
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10), sharex=True)
    
    # Plot 1: Temperature time series
    ax1.plot(ds.time, ds.sea_water_temperature, 'b-', linewidth=0.8, alpha=0.8)
    ax1.set_xlabel('Time', fontsize=12)
    ax1.set_ylabel('Temperature (°C)', fontsize=12)
    ax1.set_title('Deep Ocean Temperature Time Series (Stratus 12-22)', fontsize=14, fontweight='bold')
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
                merge_time = pd.to_datetime(point.strip())
                print(f"Debug: Plotting merge point {i}: {merge_time}")
                ax1.axvline(x=merge_time, color='red', linestyle='--', alpha=0.7, linewidth=1)
            except Exception as e:
                print(f"Error processing merge point {i}: {point}, Error: {e}")
    
    # Plot 2: Distance from Stratus 12
    # Create time points for each deployment location
    deployment_times = []
    
    # Corrected interpretation: 
    # S12 starts at dataset beginning
    # S13 starts at merge point 2, S14 starts at merge point 3, etc.
    # (Merge point 1 is transition/end of S12 period)
    
    # S12: Starts at dataset beginning
    deployment_times.append(pd.to_datetime(ds.time.min().values))
    
    # S13-S22: Each starts at merge point (i+1) - skip first merge point
    if 'merge_point' in ds.attrs and ds.attrs['merge_point'] != 'None':
        merge_points = ds.attrs['merge_point'].split(', ')
        # Skip first merge point, start from second merge point for S13
        for i in range(1, len(merge_points)):
            try:
                deployment_times.append(pd.to_datetime(merge_points[i].strip()))
            except:
                continue
    
    # Debug: Print the mapping
    print(f"Debug: Found {len(deployment_times)} deployment times")
    print(f"Debug: Found {len(distances_from_ref)} distances")  
    print(f"Debug: Found {len(deployments)} deployments")
    print(f"Debug: Deployment mapping:")
    for i, (dep, time) in enumerate(zip(deployments, deployment_times[:len(deployments)])):
        print(f"  S{dep}: starts at {time}")
    
    # Ensure arrays match - we should have exactly 11 points for 11 deployments
    deployment_times = deployment_times[:len(deployments)]
    
    ax2.plot(deployment_times, distances_from_ref, 'ro-', linewidth=2, markersize=8, markerfacecolor='red', 
            markeredgecolor='darkred', markeredgewidth=1)
    ax2.set_xlabel('Time', fontsize=12)
    ax2.set_ylabel('Distance from Stratus 12 (km)', fontsize=12)
    ax2.set_title('Distance from Stratus 12 Deployment Site', fontsize=14, fontweight='bold')
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
            
        ax2.annotate(f'S{deployment.strip()}', 
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
    print(f"Time coverage: {pd.to_datetime(ds.time.min().values).strftime('%Y-%m-%d')} to {pd.to_datetime(ds.time.max().values).strftime('%Y-%m-%d')}")
    print(f"Maximum distance from Stratus 12: {max_dist:.2f} km")
    print(f"Total deployments: {len(deployments)}")

def plot_temperature_only(merged_dataset_path, output_path):
    """
    Plot only the temperature time series (single panel).
    """
    # Load the merged dataset
    ds = xr.open_dataset(merged_dataset_path)
    
    # Extract deployment information
    deployments = ds.attrs.get('deployment', '').split(', ')
    
    # Create single panel figure
    fig, ax = plt.subplots(1, 1, figsize=(14, 6))
    
    # Plot temperature time series
    ax.plot(ds.time, ds.sea_water_temperature, 'b-', linewidth=0.8, alpha=0.8)
    ax.set_xlabel('Time', fontsize=12)
    ax.set_ylabel('Temperature (°C)', fontsize=12)
    ax.set_title('Deep Ocean Temperature Time Series (Stratus 12-22)', fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.tick_params(axis='both', labelsize=10)
    
    # Add vertical lines for deployment boundaries
    if 'merge_point' in ds.attrs and ds.attrs['merge_point'] != 'None':
        merge_points = ds.attrs['merge_point'].split(', ')
        for i, point in enumerate(merge_points):
            try:
                merge_time = pd.to_datetime(point.strip())
                ax.axvline(x=merge_time, color='red', linestyle='--', alpha=0.7, linewidth=1)
                # Add deployment labels
                if i < len(deployments) - 1:
                    ax.text(merge_time, ax.get_ylim()[1] * 0.95, f'Stratus {deployments[i+1]}', 
                            rotation=90, verticalalignment='top', fontsize=8, color='red')
            except Exception as e:
                print(f"Error processing merge point {i}: {point}, Error: {e}")
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='white')
    plt.close()
    
    print(f"Temperature-only plot saved to: {output_path}")

if __name__ == "__main__":
    # Define paths
    merged_data_path = '/Users/yugao/UOP/ORS-processing/data/processed/merged_stratus/merged_stratus12_to_stratus22.nc'
    output_dir = '/Users/yugao/UOP/ORS-processing/img'
    
    # Create the temperature and distance plot
    plot_temperature_and_distance(
        merged_data_path, 
        f'{output_dir}/temperature_and_distance_stratus12_to_22.png'
    )