"""Cross-check WHOI technical report .tex files against the dataset.

Reads per-deployment macros, diff_stats.tex, spike_stats.tex,
deployment_distance.tex and compares them with the actual NetCDF files
stored under /Users/Shared/ORS/DEEP_TS/{STRATUS,NTAS}.

Prints a structured discrepancy report.
"""
from __future__ import annotations

import math
import os
import re
from pathlib import Path

import numpy as np
import xarray as xr

DEEP_TS = Path("/Users/Shared/ORS/DEEP_TS")
REPORT_DIR = {
    "stratus": Path("/Users/yugao/UOP/ORS-processing/doc/stratus/WHOI_technical_report"),
    "ntas": Path("/Users/yugao/UOP/ORS-processing/doc/NTAS/WHOI_technical_report"),
}
DATA_BASE = {
    "stratus": DEEP_TS / "STRATUS",
    "ntas": DEEP_TS / "NTAS",
}

DEPLOYMENTS = {
    "stratus": list(range(12, 23)),
    "ntas": list(range(11, 21)),
}

# Map (project, deployment) -> (sn1, sn2) discovered from the file system below.

VARS = [
    "sea_water_temperature",
    "sea_water_practical_salinity",
    "sea_water_absolute_salinity",
    "sea_water_electrical_conductivity",
    "sea_water_pressure",
]


# ----------------- helpers ----------------------------------------------------
def parse_macros(path: Path) -> dict[str, str]:
    """Parse \\renewcommand{\\Name}{value} style entries."""
    if not path.exists():
        return {}
    text = path.read_text()
    out: dict[str, str] = {}
    pattern = re.compile(r"\\renewcommand\{\\(\w+)\}\{([^}]*)\}")
    for m in pattern.finditer(text):
        out[m.group(1)] = m.group(2).strip()
    return out


def list_truncated(project: str, dep: int) -> list[Path]:
    """Return list of truncated .nc files for a deployment, sorted by SN."""
    pn = "stratus" if project == "stratus" else "ntas"
    folder = DATA_BASE[project] / f"{pn}{dep}" / "v1"
    if not folder.exists():
        return []
    files = sorted(folder.glob(f"{pn}{dep}_*_truncated.nc"))
    # exclude *_v1 truncated variants if a plain truncated exists
    out = []
    for f in files:
        if f.name.endswith("_truncated_v1.nc"):
            continue
        out.append(f)
    return out


def list_cleaned(project: str, dep: int) -> list[Path]:
    pn = "stratus" if project == "stratus" else "NTAS"
    folder = DATA_BASE[project] / f"{pn.lower()}{dep}" / "v1"
    if not folder.exists():
        return []
    return sorted(folder.glob(f"{pn}{dep}_*_cleaned.nc"))


def sn_from_path(p: Path) -> str:
    m = re.search(r"_(\d+)_(?:truncated|cleaned)", p.name)
    return m.group(1) if m else ""


def haversine_km(lat1, lon1, lat2, lon2) -> float:
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def safe_open(path: Path) -> xr.Dataset:
    return xr.open_dataset(path, decode_times=False)


def has_real_pressure(ds: xr.Dataset) -> bool:
    if "sea_water_pressure" not in ds.data_vars:
        return False
    arr = ds["sea_water_pressure"].values
    arr = arr[arr != -99999.0]
    if arr.size == 0:
        return False
    return not np.all(np.isnan(arr))


def stats_single(ds: xr.Dataset, var: str) -> tuple[float, float]:
    if var not in ds.data_vars:
        return float("nan"), float("nan")
    a = ds[var].values.astype(float)
    a = np.where(a == -99999.0, np.nan, a)
    return float(np.nanmean(a)), float(np.nanstd(a))


def stats_diff(ds1: xr.Dataset, ds2: xr.Dataset, var: str) -> tuple[float, float]:
    if var not in ds1.data_vars or var not in ds2.data_vars:
        return float("nan"), float("nan")
    # Align on time
    a1 = ds1[var].copy()
    a2 = ds2[var].copy()
    # Replace fill
    a1 = a1.where(a1 != -99999.0)
    a2 = a2.where(a2 != -99999.0)
    try:
        a1i, a2i = xr.align(a1, a2, join="inner")
    except Exception:
        return float("nan"), float("nan")
    diff = (a1i - a2i).values.astype(float)
    if diff.size == 0 or np.all(np.isnan(diff)):
        return float("nan"), float("nan")
    return float(np.nanmean(diff)), float(np.nanstd(diff))


def spike_pct(truncated: Path, cleaned: Path, var: str) -> float:
    """Percent of points removed (-99999 or NaN in cleaned that were finite in
    truncated)."""
    if not truncated.exists() or not cleaned.exists():
        return float("nan")
    dt = safe_open(truncated)
    dc = safe_open(cleaned)
    if var not in dt.data_vars or var not in dc.data_vars:
        return float("nan")
    # Align on time index
    try:
        t_da, c_da = xr.align(dt[var], dc[var], join="inner")
    except Exception:
        return float("nan")
    t = t_da.values
    c = c_da.values
    t_valid = (t != -99999.0) & ~np.isnan(t)
    c_valid = (c != -99999.0) & ~np.isnan(c)
    n_valid_in_t = int(t_valid.sum())
    if n_valid_in_t == 0:
        return float("nan")
    removed = int(np.sum(t_valid & ~c_valid))
    return 100.0 * removed / n_valid_in_t


# ----------------- parsing diff_stats/spike_stats/deployment_distance ----------
def parse_diff_stats(path: Path) -> dict:
    """Returns dict with single_sn1, single_sn2 (var->(mean,std)) and diff (var->(mean,std))."""
    if not path.exists():
        return {}
    text = path.read_text()
    out = {"single": {}, "diff": {}, "sn1": None, "sn2": None}
    # SNs from header
    snm = re.search(r"SN\s+(\S+)\s*\}.*?SN\s+(\S+)\s*\}", text, re.S)
    if snm:
        out["sn1"] = snm.group(1)
        out["sn2"] = snm.group(2)
    # Split into table 1 (single) and table 2 (diff)
    parts = text.split("\\begin{table}")
    for p in parts[1:]:
        is_diff = "Mean Diff" in p
        for line in p.splitlines():
            line = line.strip()
            if not line.startswith("sea_water") and not line.startswith("sea\\_water"):
                continue
            # strip latex escape
            cells = [c.strip() for c in line.replace("\\\\", "").split("&")]
            if not cells:
                continue
            var = cells[0].replace("\\_", "_").strip()
            try:
                vals = [float(c) if c.lower() != "nan" else float("nan") for c in cells[1:]]
            except ValueError:
                continue
            if is_diff:
                # cols: mean, std, threshold
                if len(vals) >= 2:
                    out["diff"][var] = (vals[0], vals[1])
            else:
                # cols: mean1, std1, mean2, std2 (or only mean1, std1 if single)
                if len(vals) >= 4:
                    out["single"][var] = (vals[0], vals[1], vals[2], vals[3])
                elif len(vals) >= 2:
                    out["single"][var] = (vals[0], vals[1], float("nan"), float("nan"))
    return out


def parse_spike_stats(path: Path) -> dict:
    if not path.exists():
        return {}
    text = path.read_text()
    out: dict = {"data": {}, "sn_cols": []}
    # capture header SNs
    hdr = re.search(r"Variable\s*&\s*SN\s+(\S+)\s*\(\\%\)\s*&\s*SN\s+(\S+)\s*\(\\%\)", text)
    if hdr:
        out["sn_cols"] = [hdr.group(1), hdr.group(2)]
    for line in text.splitlines():
        line = line.strip()
        if not (line.startswith("sea_water") or line.startswith("sea\\_water")):
            continue
        cells = [c.strip() for c in line.replace("\\\\", "").split("&")]
        var = cells[0].replace("\\_", "_").strip()
        try:
            v1 = float(cells[1])
            v2 = float(cells[2])
        except (ValueError, IndexError):
            continue
        out["data"][var] = (v1, v2)
    return out


def parse_deployment_distance(path: Path) -> dict:
    if not path.exists():
        return {}
    text = path.read_text()
    out = {}
    m = re.search(r"distance between [\w\s]+ and [\w\s]+ deployments is\s+([0-9.]+)\s+kilometers\s+\(([0-9.]+)\s+nautical miles", text)
    if m:
        out["km"] = float(m.group(1))
        out["nmi"] = float(m.group(2))
    # extract lat/lon table
    rows = re.findall(r"([A-Za-z]+\s+\d+)\s*&\s*([0-9.]+)\s*°([NS])\s*&\s*([0-9.]+)\s*°([EW])", text)
    out["coords"] = []
    for name, lat, ns, lon, ew in rows:
        latv = float(lat) * (1 if ns == "N" else -1)
        lonv = float(lon) * (1 if ew == "E" else -1)
        out["coords"].append((name, latv, lonv))
    return out


# ----------------- main -------------------------------------------------------
def close_enough(a: float, b: float, tol: float) -> bool:
    if math.isnan(a) and math.isnan(b):
        return True
    if math.isnan(a) or math.isnan(b):
        return False
    return abs(a - b) <= tol


def cross_check_project(project: str) -> list[str]:
    issues: list[str] = []
    rdir = REPORT_DIR[project]
    pn = project
    pn_disp = "Stratus" if project == "stratus" else "NTAS"

    prev_lat: float | None = None
    prev_lon: float | None = None
    prev_label: str | None = None

    for dep in DEPLOYMENTS[project]:
        chap_dir = rdir / f"{dep}"
        if not chap_dir.exists():
            continue
        macros = parse_macros(chap_dir / "macros.tex")
        truncated = list_truncated(project, dep)
        cleaned = list_cleaned(project, dep)

        # Build header
        label = f"[{pn_disp} {dep}]"

        # If no data, note
        if not truncated:
            issues.append(f"{label} no truncated NetCDF files found on disk -- skipping data checks")
            continue

        sns = [sn_from_path(p) for p in truncated]
        # macros instrument SNs
        m_sn1 = macros.get("FirstInstrument", "")
        m_sn2 = macros.get("SecondInstrument", "")
        m_type1 = macros.get("FirstInstrumentType", "")
        m_type2 = macros.get("SecondInstrumentType", "")

        if m_sn1 and m_sn1 not in sns:
            issues.append(f"{label} macros FirstInstrument={m_sn1} not found in data files {sns}")
        if m_sn2 and m_sn2 not in sns:
            issues.append(f"{label} macros SecondInstrument={m_sn2} not found in data files {sns}")

        # previouscasenumber
        prev = macros.get("previouscasenumber", "")
        if prev and int(prev) != dep - 1:
            issues.append(f"{label} previouscasenumber={prev} but expected {dep-1}")

        # instrument types
        ds_first = safe_open(truncated[0]) if truncated else None
        ds_second = safe_open(truncated[1]) if len(truncated) > 1 else None

        def _norm_model(m: str) -> str:
            return m.replace("-", "").upper()

        if ds_first is not None and m_type1:
            model = str(ds_first.attrs.get("instrument_model", ""))
            if _norm_model(model) != _norm_model(m_type1):
                issues.append(f"{label} FirstInstrumentType macro={m_type1} but data instrument_model={model}")
        if ds_second is not None and m_type2:
            model = str(ds_second.attrs.get("instrument_model", ""))
            if _norm_model(model) != _norm_model(m_type2):
                issues.append(f"{label} SecondInstrumentType macro={m_type2} but data instrument_model={model}")

        # pressureavailable
        ma_pressure = macros.get("pressureavailable", "")
        if ds_first is not None:
            real_p = has_real_pressure(ds_first) or (ds_second is not None and has_real_pressure(ds_second))
            ma_yes = ma_pressure.lower() == "yes"
            if ma_pressure and (real_p != ma_yes):
                issues.append(f"{label} pressureavailable macro={ma_pressure} but data has_real_pressure={real_p}")

        # diff stats vs computed
        diff_path = chap_dir / "diff_stats.tex"
        diff_doc = parse_diff_stats(diff_path)
        if diff_doc and ds_first is not None and ds_second is not None:
            # compute single sensor stats from cleaned files (the report says
            # "computed after spike removal")
            sn1_path = None
            sn2_path = None
            for c in cleaned:
                if sn_from_path(c) == diff_doc["sn1"]:
                    sn1_path = c
                if sn_from_path(c) == diff_doc["sn2"]:
                    sn2_path = c
            if sn1_path is None or sn2_path is None:
                issues.append(f"{label} diff_stats SNs {diff_doc['sn1']},{diff_doc['sn2']} not matched in cleaned files {[c.name for c in cleaned]}")
            else:
                dc1 = safe_open(sn1_path)
                dc2 = safe_open(sn2_path)
                for var in VARS:
                    if var in diff_doc["single"]:
                        em1, es1, em2, es2 = diff_doc["single"][var]
                        cm1, cs1 = stats_single(dc1, var)
                        cm2, cs2 = stats_single(dc2, var)
                        tol = 1e-3 if "salinity" in var or var == "sea_water_temperature" else 1e-3
                        if not close_enough(em1, cm1, tol) or not close_enough(es1, cs1, tol):
                            issues.append(f"{label} single-sensor {var} SN {diff_doc['sn1']}: table=({em1:.5f},{es1:.5f}) data=({cm1:.5f},{cs1:.5f})")
                        if not close_enough(em2, cm2, tol) or not close_enough(es2, cs2, tol):
                            issues.append(f"{label} single-sensor {var} SN {diff_doc['sn2']}: table=({em2:.5f},{es2:.5f}) data=({cm2:.5f},{cs2:.5f})")
                    if var in diff_doc["diff"]:
                        em, es = diff_doc["diff"][var]
                        cm, cs = stats_diff(dc1, dc2, var)
                        tol = 1e-3
                        if not close_enough(em, cm, tol) or not close_enough(es, cs, tol):
                            issues.append(f"{label} diff {var}: table=({em:.5f},{es:.5f}) data=({cm:.5f},{cs:.5f})")

        # spike stats vs computed
        spike_path = chap_dir / "spike_stats.tex"
        spike_doc = parse_spike_stats(spike_path)
        if spike_doc and truncated and cleaned:
            for c in cleaned:
                sn = sn_from_path(c)
                tpath = None
                for t in truncated:
                    if sn_from_path(t) == sn:
                        tpath = t
                        break
                if tpath is None:
                    continue
                if sn in spike_doc.get("sn_cols", []):
                    col_idx = spike_doc["sn_cols"].index(sn)
                else:
                    col_idx = 0 if sn == sns[0] else 1
                for var, pcts in spike_doc["data"].items():
                    expected = pcts[col_idx]
                    actual = spike_pct(tpath, c, var)
                    if math.isnan(expected) and math.isnan(actual):
                        continue
                    if not close_enough(expected, actual, 0.01):
                        issues.append(f"{label} spike% {var} SN {sn}: table={expected:.4f}% data={actual:.4f}%")

        # deployment_distance
        dist_path = chap_dir / "deployment_distance.tex"
        dist_doc = parse_deployment_distance(dist_path)
        # data anchors
        cur_lat = float(ds_first.attrs.get("latitude_anchor_survey", "nan"))
        cur_lon = float(ds_first.attrs.get("longitude_anchor_survey", "nan"))
        if dist_doc and "coords" in dist_doc and len(dist_doc["coords"]) >= 2:
            for name, lat, lon in dist_doc["coords"]:
                if name.endswith(str(dep)):
                    if not close_enough(lat, cur_lat, 1e-3) or not close_enough(lon, cur_lon, 1e-3):
                        issues.append(f"{label} deployment_distance coords for {name}: table=({lat},{lon}) data=({cur_lat},{cur_lon})")
            if prev_lat is not None and prev_lon is not None:
                km_real = haversine_km(prev_lat, prev_lon, cur_lat, cur_lon)
                nmi_real = km_real / 1.852
                if "km" in dist_doc and not close_enough(dist_doc["km"], km_real, 0.1):
                    issues.append(f"{label} deployment_distance km: table={dist_doc['km']} computed={km_real:.2f}")
                if "nmi" in dist_doc and not close_enough(dist_doc["nmi"], nmi_real, 0.1):
                    issues.append(f"{label} deployment_distance nmi: table={dist_doc['nmi']} computed={nmi_real:.2f}")

        prev_lat, prev_lon = cur_lat, cur_lon

    return issues


if __name__ == "__main__":
    for project in ("stratus", "ntas"):
        print(f"\n##### {project.upper()} #####")
        issues = cross_check_project(project)
        if not issues:
            print("  (no issues detected)")
        else:
            for i in issues:
                print("  -", i)
