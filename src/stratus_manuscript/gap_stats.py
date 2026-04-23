import os
import xarray as xr
import matplotlib.pyplot as plt
from matplotlib import dates as mdates
import numpy as np

# Input dataset (temperature-only CF dataset)
temp_ds_path = '/Users/yugao/UOP/ORS-processing/data/processed/merged_stratus/stratus_temperature_2012_2023.nc'

# Output figure path (slide-friendly)
out_dir = '/Users/yugao/UOP/ORS-processing/img/stratus_manuscript'
os.makedirs(out_dir, exist_ok=True)
out_png = os.path.join(out_dir, 'fig2a_temp_slide.png')

# Load temperature-only dataset
ds = xr.open_dataset(temp_ds_path)

# Determine primary temperature variable
var_name = 'sea_water_temperature'

var = ds[var_name]

# Resolve fill value sentinel
fill_val = None
if '_FillValue' in var.encoding:
	fill_val = var.encoding.get('_FillValue')
elif '_FillValue' in var.attrs:
	fill_val = var.attrs.get('_FillValue')
if fill_val is None:
	fill_val = -99999.0

# Percentage of fill values across all elements
missing_elem = var.isnull()
if fill_val is not None and not np.isnan(fill_val):
	missing_elem = missing_elem | (var == fill_val)

total_count = int(np.prod(var.shape))
missing_count = int(missing_elem.sum().item())
percent_fill = (missing_count / total_count) * 100.0 if total_count > 0 else 0.0

# Longest continuous gap over time where all sensors are missing
times = ds['time'].values

# Determine sampling-based longest gap (accounts for missing periods with no timestamps)
if times.size == 0:
	longest_gap_seconds = 0.0
	gap_start = None
	gap_end = None
	cadence_seconds = 0.0
else:
	tdiff = np.diff(times)
	# Convert time deltas to seconds robustly
	def to_seconds(td):
		try:
			return float(td / np.timedelta64(1, 's'))
		except Exception:
			# Fallback for datetime.timedelta-like objects
			return float(getattr(td, 'total_seconds', lambda: 0.0)())

	tdiff_sec = np.array([to_seconds(d) for d in tdiff])
	if tdiff_sec.size == 0:
		cadence_seconds = 0.0
		longest_gap_seconds = 0.0
		gap_start = None
		gap_end = None
	else:
		cadence_seconds = float(np.median(tdiff_sec))
		# Identify gaps where the interval is larger than expected cadence
		# Use a tolerance factor to avoid floating rounding issues
		tol = 1.5
		large_gap_idx = np.where(tdiff_sec > tol * cadence_seconds)[0]
		if large_gap_idx.size == 0:
			longest_gap_seconds = 0.0
			gap_start = None
			gap_end = None
		else:
			# Gap length = observed interval minus expected cadence
			gap_lengths = tdiff_sec[large_gap_idx] - cadence_seconds
			max_i = int(np.argmax(gap_lengths))
			idx = int(large_gap_idx[max_i])
			longest_gap_seconds = float(gap_lengths[max_i])
			gap_start = times[idx]
			gap_end = times[idx + 1]

longest_gap_hours = longest_gap_seconds / 3600.0
longest_gap_days = longest_gap_seconds / 86400.0

print(f"Variable: {var_name}")
print(f"Fill value sentinel: {fill_val}")
print(f"Percentage of fill values: {percent_fill:.2f}% ({missing_count}/{total_count})")
if gap_start is not None and gap_end is not None:
	print(f"Expected cadence: {cadence_seconds/3600.0:.2f} hours")
	print(f"Longest gap: {longest_gap_hours:.2f} hours ({longest_gap_days:.2f} days) between {gap_start} and {gap_end}")
else:
	print("Expected cadence: N/A")
	print("Longest gap: 0 hours (no detected sampling gaps)")

# Plot a zoomed view around the longest gap to confirm
if gap_start is not None and gap_end is not None:
	pad_days = 2
	start_window = gap_start - np.timedelta64(pad_days, 'D')
	end_window = gap_end + np.timedelta64(pad_days, 'D')

	dims_without_time = [d for d in var.dims if d != 'time']
	var_for_plot = var
	if dims_without_time:
		try:
			var_for_plot = var.mean(dim=dims_without_time)
		except Exception:
			# Fallback: take the first slice along extra dims
			sel_indexers = {d: 0 for d in dims_without_time}
			var_for_plot = var.isel(**sel_indexers)

	sel_var = var_for_plot.sel(time=slice(start_window, end_window))
	# Mask fill values and NaNs for cleaner plotting
	sel_var_plot = sel_var.where(~(sel_var.isnull() | ((fill_val is not None and not np.isnan(fill_val)) and (sel_var == fill_val))))

	fig, ax = plt.subplots(figsize=(10, 4))
	ax.plot(sel_var_plot['time'].values, sel_var_plot.values, lw=0.8, color='tab:blue')
	ax.axvline(gap_start, color='red', linestyle='--', label='gap start')
	ax.axvline(gap_end, color='red', linestyle='--', label='gap end')
	ax.set_title(f"Longest gap ~ {longest_gap_hours:.2f} h (cadence ~ {cadence_seconds/3600.0:.2f} h)")
	ax.set_xlabel('Time')
	ax.set_ylabel('Sea water temperature')
	ax.legend(loc='upper right')
	fig.autofmt_xdate()
	plt.tight_layout()
	plt.savefig(out_png, dpi=200)
	plt.close(fig)
	print(f"Saved confirmation plot to: {out_png}")