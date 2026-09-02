# %%
# Compare statistics of overlapping time periods between adjacent NTAS deployments.
#
# For each pair of adjacent deployments, find the time window where both
# deployments' instruments were recording simultaneously, then check whether
# the mean difference between instruments is no larger than the natural
# temporal variability (std) of each sensor over that overlap window.
#
# NTAS15 is skipped: the deployment returned no usable data (see merge_15_missing.py).

import os
import numpy as np
import pandas as pd
import xarray as xr

DATA_ROOT = '/mnt/VAST_UOP/ORS/DEEP_TS/NTAS'
DOC_ROOT = '/mnt/VAST_UOP/ORS/DEEP_TS/ORS-processing/doc/NTAS'
VARIABLE = 'sea_water_temperature'
RESAMPLE_FREQ = '30min'  # matches the sampling grid used to build the merged NTAS dataset

# deployment number -> list of instrument serial numbers
DEPLOYMENTS = {
    11: ['2323', '2324'],
    12: ['1877'],
    13: ['2323', '2324'],
    14: ['11392', '11393'],
    16: ['11392', '11393'],
    17: ['11380', '11381'],
    18: ['11392', '11393'],
    19: ['12246', '12247'],
    20: ['11392', '11393'],
}

DEPLOYMENT_ORDER = [11, 12, 13, 14, 16, 17, 18, 19, 20]


def cleaned_path(dep, serial):
    return os.path.join(DATA_ROOT, f'ntas{dep}', 'v1', f'NTAS{dep}_{serial}_cleaned.nc')


def load_series(dep, serial, variable=VARIABLE):
    ds = xr.open_dataset(cleaned_path(dep, serial))
    da = ds[variable].resample(time=RESAMPLE_FREQ).mean()
    da['time'] = da.time.dt.round(RESAMPLE_FREQ)  # snap to a common grid, as done when building the merged dataset
    ds.close()
    return da


def compare_pair(dep0, dep1, variable=VARIABLE):
    """Compare overlap-period statistics between all instrument combos of two adjacent deployments."""
    rows = []
    for serial0 in DEPLOYMENTS[dep0]:
        da0 = load_series(dep0, serial0, variable)
        for serial1 in DEPLOYMENTS[dep1]:
            da1 = load_series(dep1, serial1, variable)

            overlap_start = max(da0.time.min().values, da1.time.min().values)
            overlap_end = min(da0.time.max().values, da1.time.max().values)

            row = {
                'deployment0': f'NTAS{dep0}', 'serial0': serial0,
                'deployment1': f'NTAS{dep1}', 'serial1': serial1,
                'overlap_start': None, 'overlap_end': None,
                'n_points': 0, 'mean_diff': np.nan,
                'std0': np.nan, 'std1': np.nan,
                'within_uncertainty': None,
            }

            if overlap_start >= overlap_end:
                rows.append(row)
                continue

            sel0 = da0.sel(time=slice(overlap_start, overlap_end))
            sel1 = da1.sel(time=slice(overlap_start, overlap_end))
            sel0, sel1 = xr.align(sel0, sel1, join='inner', copy=False)
            diff = (sel0 - sel1).dropna('time')

            if diff.time.size == 0:
                rows.append(row)
                continue

            mean_diff = float(diff.mean())
            std0 = float(sel0.std())
            std1 = float(sel1.std())
            # "within uncertainty" if the mean bias is smaller than each sensor's own natural variability
            within = bool(abs(mean_diff) < std0 and abs(mean_diff) < std1)

            row.update({
                'overlap_start': pd.Timestamp(overlap_start),
                'overlap_end': pd.Timestamp(overlap_end),
                'n_points': int(diff.time.size),
                'mean_diff': mean_diff,
                'std0': std0,
                'std1': std1,
                'within_uncertainty': within,
            })
            rows.append(row)
    return rows


def write_latex_table(df, path, variable=VARIABLE):
    def esc(x):
        return str(x).replace('_', '\\_')

    with open(path, 'w') as f:
        f.write('\\begin{table}[h]\n\\centering\n')
        f.write('\\begin{tabular}{|c|c|c|c|c|c|c|}\n\\hline\n')
        f.write('Deployment 0 & SN0 & Deployment 1 & SN1 & Mean Diff & Std0 / Std1 & Within Uncertainty \\\\\n\\hline\n')
        for _, row in df.iterrows():
            if pd.isna(row['mean_diff']):
                f.write(f"{esc(row['deployment0'])} & {esc(row['serial0'])} & {esc(row['deployment1'])} & "
                        f"{esc(row['serial1'])} & \\multicolumn{{3}}{{c|}}{{no overlap}} \\\\\n")
            else:
                verdict = 'Yes' if row['within_uncertainty'] else 'No'
                f.write(f"{esc(row['deployment0'])} & {esc(row['serial0'])} & {esc(row['deployment1'])} & "
                        f"{esc(row['serial1'])} & {row['mean_diff']:.4f} & "
                        f"{row['std0']:.4f} / {row['std1']:.4f} & {verdict} \\\\\n")
        f.write('\\hline\n\\end{tabular}\n')
        f.write(f"\\caption{{Overlap-period statistics between adjacent NTAS deployments for {variable.replace('_', ' ')}. "
                 "The mean difference is compared against each sensor's own temporal standard deviation during the overlap window.}\n")
        f.write('\\end{table}\n')


def main():
    all_rows = []
    for dep0, dep1 in zip(DEPLOYMENT_ORDER[:-1], DEPLOYMENT_ORDER[1:]):
        print(f'Comparing NTAS{dep0} vs NTAS{dep1} ({VARIABLE})...')
        for row in compare_pair(dep0, dep1):
            all_rows.append(row)
            if row['overlap_start'] is None:
                print(f"  SN{row['serial0']} vs SN{row['serial1']}: no overlap")
            else:
                verdict = 'OK' if row['within_uncertainty'] else 'EXCEEDS UNCERTAINTY'
                print(f"  SN{row['serial0']} vs SN{row['serial1']}: "
                      f"mean_diff={row['mean_diff']:.4f}, std0={row['std0']:.4f}, "
                      f"std1={row['std1']:.4f}, n={row['n_points']} -> {verdict}")

    df = pd.DataFrame(all_rows)

    csv_path = os.path.join(DOC_ROOT, 'NTAS_overlap_stats.csv')
    df.to_csv(csv_path, index=False)
    print(f'\nSaved summary to {csv_path}')

    tex_path = os.path.join(DOC_ROOT, 'NTAS_overlap_stats.tex')
    write_latex_table(df, tex_path)
    print(f'Saved LaTeX table to {tex_path}')

    return df


if __name__ == '__main__':
    main()
