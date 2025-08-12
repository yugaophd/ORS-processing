# plot distance from STRATUS 12 and distance from previous site
import xarray as xr
import matplotlib.pyplot as plt
import numpy as np
import os
from matplotlib.ticker import FuncFormatter
from adjustText import adjust_text
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

def format_coordinate(value, is_lat=True):
    """Format coordinate values with appropriate precision and direction"""
    # Use 4 decimal places for coordinates (about 10m precision)
    formatted = f"{abs(value):.4f}"
    
    if is_lat:
        direction = "S" if value < 0 else "N"
    else:
        direction = "W" if value < 0 else "E"
        
    return f"{formatted}°{direction}"

def plot_deployment_locations():
    """
    Create cumulative plots of STRATUS mooring deployment locations.
    Each figure shows locations from STRATUS 12 up to the specified deployment.
    Also calculates distance between consecutive deployments.
    """
    # Load the merged dataset
    merged_data_dir = '/Users/yugao/UOP/ORS-processing/data/processed/merged_stratus'
    ds = xr.open_dataset(f'{merged_data_dir}/merged_stratus12_to_stratus22.nc')
    
    # Parse deployment numbers
    deployments = ds.attrs.get('deployment', '').split(', ')
    
    # Parse latitude and longitude strings into lists
    latitudes = [float(lat.strip()) for lat in ds.attrs.get('latitude_anchor_survey', '').split(', ')]
    longitudes = [float(lon.strip()) for lon in ds.attrs.get('longitude_anchor_survey', '').split(', ')]
    
    # Create output directories
    img_dir = '/Users/yugao/UOP/ORS-processing/img/deployment_maps'
    os.makedirs(img_dir, exist_ok=True)
    
    # Format tick labels
    def format_lon_ticks(x, pos):
        return f'{abs(x):.2f}°W' if x < 0 else f'{x:.2f}°E'
        
    def format_lat_ticks(x, pos):
        return f'{abs(x):.2f}°S' if x < 0 else f'{x:.2f}°N'
    
    # Plot cumulatively
    for i in range(2, len(deployments) + 1):  # Start with at least 2 deployments
        fig, ax = plt.subplots(figsize=(12, 10))  # Increased figure size
        
        # Plot each deployment marker with high contrast colors
        # Create a list of high-contrast colors instead of using viridis
        high_contrast_colors = [
            '#1f77b4',  # Blue
            '#ff7f0e',  # Orange
            '#d62728',  # Red
            '#2ca02c',  # Green
            '#9467bd',  # Purple
            '#8c564b',  # Brown
            '#e377c2',  # Pink
            '#17becf',  # Cyan
            '#bcbd22',  # Olive
            '#ff9896',  # Light red
            '#aec7e8',  # Light blue
            '#ffbb78',  # Light orange
            '#98df8a',  # Light green
            '#c5b0d5',  # Light purple
            '#7f7f7f',  # Gray
        ]

        for j in range(i):
            deployment_num = deployments[j].strip()
            color_idx = j % len(high_contrast_colors)  # Cycle through colors
            scatter = ax.scatter(longitudes[j], latitudes[j], 
                     s=180,  # Keep the increased marker size
                     marker='o',
                     c=high_contrast_colors[color_idx],  # Use high contrast color
                     edgecolor='black', 
                     linewidth=1.5,
                     alpha=0.85,  # Slightly increased opacity for better contrast
                     label=f'STRATUS {deployment_num}',
                     zorder=2)
        
        # Adjust plot limits with padding
        padding = 0.05  # degrees
        lat_min = min(latitudes[:i]) - padding
        lat_max = max(latitudes[:i]) + padding
        lon_min = min(longitudes[:i]) - padding
        lon_max = max(longitudes[:i]) + padding
        
        # Add reasonable padding 
        lon_range = lon_max - lon_min
        lat_range = lat_max - lat_min
        ax.set_xlim(lon_min - lon_range*0.1, lon_max + lon_range*0.1)
        ax.set_ylim(lat_min - lat_range*0.1, lat_max + lat_range*0.1)
        
        # Format axis ticks
        ax.xaxis.set_major_formatter(FuncFormatter(format_lon_ticks))
        ax.yaxis.set_major_formatter(FuncFormatter(format_lat_ticks))
        
        # Add title with larger font
        start_deployment = deployments[0].strip()
        end_deployment = deployments[i-1].strip()
        ax.set_title(f'STRATUS Deployment Locations (STRATUS {start_deployment} to {end_deployment})', 
                    fontsize=18)  # Increased font size
        
        # Add labels with larger font
        ax.set_xlabel('Longitude', fontsize=16)  # Increased font size
        ax.set_ylabel('Latitude', fontsize=16)  # Increased font size
        
        # Increase tick label sizes
        ax.tick_params(axis='both', which='major', labelsize=14)  # Larger tick labels
        ax.tick_params(axis='both', which='minor', labelsize=12)  # Larger minor tick labels
        
        # Add finer grid with both major and minor gridlines
        ax.grid(True, which='major', linestyle='-', alpha=0.6)
        ax.grid(True, which='minor', linestyle=':', alpha=0.4)
        ax.minorticks_on()  # Enable minor ticks
        
        # Set minor tick frequency
        from matplotlib.ticker import AutoMinorLocator
        ax.xaxis.set_minor_locator(AutoMinorLocator(5))  # 5 minor ticks between major ticks
        ax.yaxis.set_minor_locator(AutoMinorLocator(5))
        
        # Add legend with deployments in chronological order and larger font
        handles, labels = ax.get_legend_handles_labels()
        ax.legend(handles, labels, loc='lower right', title='Deployments', 
                ncol=2, fontsize=14, title_fontsize=16)  # Increased font sizes
        
        # Save figure
        plt.tight_layout()
        plt.savefig(f'{img_dir}/stratus{start_deployment}_to_stratus{end_deployment}_locations.png', 
                   dpi=300, bbox_inches='tight')
        print(f"Created map for Stratus {start_deployment} to {end_deployment}")
        plt.close()
        
        # Calculate distance between consecutive deployments - FIX: Now works for i >= 2
        if i >= 2:  # Changed from i >= 3
            last_idx = i - 1
            second_last_idx = i - 2
            
            # Get deployment numbers for generating correct path
            last_deployment = deployments[last_idx].strip()
            second_last_deployment = deployments[second_last_idx].strip()
            
            # Calculate the distance
            dist_km, dist_nm = haversine_distance(
                latitudes[last_idx], longitudes[last_idx],
                latitudes[second_last_idx], longitudes[second_last_idx]
            )
            
            # Create the documentation directory if it doesn't exist
            doc_dir = f'/Users/yugao/UOP/ORS-processing/doc/stratus/{last_deployment}'
            os.makedirs(doc_dir, exist_ok=True)
            
            # Format coordinates properly
            lat1_str = format_coordinate(latitudes[second_last_idx], is_lat=True) 
            lon1_str = format_coordinate(longitudes[second_last_idx], is_lat=False)
            lat2_str = format_coordinate(latitudes[last_idx], is_lat=True)
            lon2_str = format_coordinate(longitudes[last_idx], is_lat=False)
            
            # Create LaTeX file
            with open(f'{doc_dir}/deployment_distance.tex', 'w') as f:
                f.write("% STRATUS mooring deployment distance information\n\n")
                
                # Simple sentence about the distance
                f.write(f"The distance between STRATUS {second_last_deployment} and STRATUS {last_deployment} ")
                f.write(f"deployments is {dist_km:.2f} kilometers ({dist_nm:.2f} nautical miles).\n\n")
                
                # Keep the coordinates table
                f.write("\\begin{table}[ht]\n")
                f.write("\\centering\n")
                f.write("\\caption{Deployment coordinates}\n")
                f.write("\\begin{tabular}{lcc}\n")
                f.write("\\hline\n")
                f.write("\\textbf{Deployment} & \\textbf{Latitude} & \\textbf{Longitude} \\\\\n")
                f.write("\\hline\n")
                f.write(f"STRATUS {second_last_deployment} & {lat1_str} & {lon1_str} \\\\\n")
                f.write(f"STRATUS {last_deployment} & {lat2_str} & {lon2_str} \\\\\n")
                f.write("\\hline\n")
                f.write("\\end{tabular}\n")
                f.write("\\end{table}\n")
            
            print(f"Distance information saved to {doc_dir}/deployment_distance.tex")

if __name__ == "__main__":
    plot_deployment_locations()