"""Regenerate diff_stats.tex, spike_stats.tex, and deployment_distance.tex for
each deployment chapter to match the current cleaned/truncated NetCDF datasets.

Also fixes ``pressureavailable`` in macros.tex when the data has real pressure
records.

This script is idempotent: re-running it just rewrites the files with the same
content (assuming the data hasn't changed).
"""
from __future__ import annotations

import math
import re
from pathlib import Path

import numpy as np
import xarray as xr

REPORT_DIR = {
    "stratus": Path("/Users/yugao/UOP/ORS-processing/doc/stratus/WHOI_technical_report"),
    "ntas": Path("/Users/yugao/UOP/ORS-processing/doc/NTAS/WHOI_technical_report"),
}
DATA_BASE = {
    "stratus": Path("/Users/Shared/ORS/DEEP_TS/STRATUS"),
    "ntas": Path("/Users/Shared/ORS/DEEP_TS/NTAS"),
}
DEPLOYMENTS = {
    "stratus": list(range(12, 23)),
    "ntas": list(range(11, 21)),
}
DISPLAY = {"stratus": "Stratus", "ntas": "NTAS"}

VARS = [
    "sea_water_temperature",
    "sea_water_practical_salinity",
    "sea_water_absolute_salinity",
    "sea_water_electrical_conductivity",
    "sea_water_pressure",
]

FILL = -99999.0


def fname_prefix(project: str) -> str:
    return "stratus" if project == "stratus" else "ntas"


def cleaned_files(project: str, dep: int) -> list[Path]:
    pn = fname_prefix(project)
    folder = DATA_BASE[project] / f"{pn}{dep}" / "v1"
    if not folder.exists():
        return []
    pat = f"{pn.upper() if project=='ntas' else pn}{dep}_*_cleaned.nc"
    return sorted(folder.glob(pat))


def truncated_files(project: str, dep: int) -> list[Path]:
    pn = fname_prefix(project)
    folder = DATA_BASE[project] / f"{pn}{dep}" / "v1"
    if not folder.exists():
        return []
    files = sorted(folder.glob(f"{pn}{dep}_*_truncated.nc"))
    return [f for f in files if not f.name.endswith("_truncated_v1.nc")]


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


def open_ds(path: Path) -> xr.Dataset:
    return xr.open_dataset(path, decode_times=False)


def single_stats(ds: xr.Dataset, var: str) -> tuple[float, float]:
    if var not in ds.data_vars:
        return float("nan"), float("nan")
    a = ds[var].values.astype(float)
    a = np.where(a == FILL, np.nan, a)
    if np.all(np.isnan(a)):
        return float("nan"), float("nan")
    return float(np.nanmean(a)), float(np.nanstd(a))


def diff_stats(ds1: xr.Dataset, ds2: xr.Dataset, var: str) -> tuple[float, float]:
    if var not in ds1.data_vars or var not in ds2.data_vars:
        return float("nan"), float("nan")
    a1 = ds1[var].where(ds1[var] != FILL)
    a2 = ds2[var].where(ds2[var] != FILL)
    try:
        a1, a2 = xr.align(a1, a2, join="inner")
    except Exception:
        return float("nan"), float("nan")
    diff = (a1 - a2).values.astype(float)
    if diff.size == 0 or np.all(np.isnan(diff)):
        return float("nan"), float("nan")
    return float(np.nanmean(diff)), float(np.nanstd(diff))


def has_real_pressure(ds: xr.Dataset) -> bool:
    if "sea_water_pressure" not in ds.data_vars:
        return False
    arr = ds["sea_water_pressure"].values.astype(float)
    arr = arr[arr != FILL]
    if arr.size == 0:
        return False
    return not np.all(np.isnan(arr))


def fmt(x: float) -> str:
    if math.isnan(x):
        return "nan"
    return f"{x:.5f}"


# ----- regeneration -----

def extract_captions(path: Path) -> list[str]:
    """Extract caption bodies, handling nested braces."""
    if not path.exists():
        return []
    text = path.read_text()
    out: list[str] = []
    i = 0
    needle = "\\caption{"
    while True:
        j = text.find(needle, i)
        if j < 0:
            break
        k = j + len(needle)
        depth = 1
        start = k
        while k < len(text) and depth > 0:
            c = text[k]
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    out.append(text[start:k])
                    break
            k += 1
        i = k + 1
    return out


def regen_diff_stats(project: str, dep: int, existing: Path) -> str | None:
    cleaned = cleaned_files(project, dep)
    if not cleaned:
        return None
    # Preserve existing captions when present
    captions = extract_captions(existing)
    disp_lc = "stratus" if project == "stratus" else "NTAS"
    lines: list[str] = []
    if len(cleaned) == 1:
        ds = open_ds(cleaned[0])
        sn = sn_from_path(cleaned[0])
        cap = (
            captions[0]
            if captions
            else f"Statistics for SN {sn} on {disp_lc} {dep}. "
            "Only one instrument returned valid data for this deployment."
        )
        lines.append("\\begin{table}[h]\n\\centering")
        lines.append("\\begin{tabular}{|c|c|c|}\n\\hline")
        lines.append(f"Variable & \\multicolumn{{2}}{{c|}}{{SN {sn}}} \\\\")
        lines.append("& Mean & Std Dev \\\\\n\\hline")
        for v in VARS:
            m, s = single_stats(ds, v)
            ev = v.replace("_", "\\_")
            lines.append(f"{ev} & {fmt(m)} & {fmt(s)} \\\\")
        lines.append("\\hline\n\\end{tabular}")
        lines.append(f"\\caption{{{cap}}}")
        lines.append("\\end{table}")
        return "\n".join(lines) + "\n"
    ds1, ds2 = open_ds(cleaned[0]), open_ds(cleaned[1])
    sn1, sn2 = sn_from_path(cleaned[0]), sn_from_path(cleaned[1])
    cap1 = captions[0] if len(captions) >= 1 else f"Statistics for individual sensors on {disp_lc} {dep}"
    cap2 = captions[1] if len(captions) >= 2 else f"Statistics for difference between sensors on {disp_lc} {dep}"
    lines.append("\\begin{table}[h]\n\\centering")
    lines.append("\\begin{tabular}{|c|c|c|c|c|}\n\\hline")
    lines.append(
        f"Variable & \\multicolumn{{2}}{{c|}}{{SN {sn1}}} & "
        f"\\multicolumn{{2}}{{c|}}{{SN {sn2}}} \\\\"
    )
    lines.append("& Mean & Std Dev & Mean & Std Dev \\\\\n\\hline")
    for v in VARS:
        m1, s1 = single_stats(ds1, v)
        m2, s2 = single_stats(ds2, v)
        ev = v.replace("_", "\\_")
        lines.append(f"{ev} & {fmt(m1)} & {fmt(s1)} & {fmt(m2)} & {fmt(s2)} \\\\")
    lines.append("\\hline\n\\end{tabular}")
    lines.append(f"\\caption{{{cap1}}}")
    lines.append("\\end{table}\n")
    lines.append("\\begin{table}[h]\n\\centering")
    lines.append("\\begin{tabular}{|c|c|c|c|}\n\\hline")
    lines.append("Variable & Mean Diff & Std Diff & QC Threshold \\\\\n\\hline")
    for v in VARS:
        md, sd = diff_stats(ds1, ds2, v)
        thr = 3 * sd if not math.isnan(sd) else float("nan")
        ev = v.replace("_", "\\_")
        lines.append(f"{ev} & {fmt(md)} & {fmt(sd)} & {fmt(thr)} \\\\")
    lines.append("\\hline\n\\end{tabular}")
    lines.append(f"\\caption{{{cap2}}}")
    lines.append("\\end{table}")
    return "\n".join(lines) + "\n"


def extract_label(path: Path) -> str | None:
    if not path.exists():
        return None
    m = re.search(r"\\label\{([^}]+)\}", path.read_text())
    return m.group(1) if m else None


def regen_spike_stats(project: str, dep: int, existing: Path) -> str | None:
    truncated = truncated_files(project, dep)
    cleaned = cleaned_files(project, dep)
    if not truncated or not cleaned:
        return None
    sn_to_t = {sn_from_path(t): t for t in truncated}
    sn_to_c = {sn_from_path(c): c for c in cleaned}
    sns = sorted(set(sn_to_t) & set(sn_to_c))
    if not sns:
        return None
    pn = "str" if project == "stratus" else "ntas"
    proj_macro = "\\displayprojectname" if project == "stratus" else "\\projectname"
    existing_caps = extract_captions(existing)
    existing_label = extract_label(existing)
    cap = existing_caps[0] if existing_caps else f"Spike removal statistics for {proj_macro}{{}} \\casenumber{{}}"
    label = existing_label or f"tab:{pn}{dep}_spike_stats"
    if len(sns) == 1:
        sn = sns[0]
        dt = open_ds(sn_to_t[sn])
        dc = open_ds(sn_to_c[sn])
        lines = [
            "\\begin{table}[h]",
            "\\centering",
            f"\\caption{{{cap}}}",
            f"\\label{{{label}}}",
            "\\begin{tabular}{|l|c|}",
            "\\hline",
            f"Variable & SN {sn} (\\%) \\\\",
            "\\hline",
        ]
        for v in sorted(VARS):
            ev = v.replace("_", "\\_")
            p = spike_percent(dt, dc, v)
            lines.append(f"{ev} & {fmt_pct(p)} \\\\")
        lines += ["\\hline", "\\end{tabular}", "\\end{table}"]
        return "\n".join(lines) + "\n"
    sn1, sn2 = sns[0], sns[1]
    dt1, dt2 = open_ds(sn_to_t[sn1]), open_ds(sn_to_t[sn2])
    dc1, dc2 = open_ds(sn_to_c[sn1]), open_ds(sn_to_c[sn2])
    lines = [
        "\\begin{table}[h]",
        "\\centering",
        f"\\caption{{{cap}}}",
        f"\\label{{{label}}}",
        "\\begin{tabular}{|l|c|c|}",
        "\\hline",
        f"Variable & SN {sn1} (\\%) & SN {sn2} (\\%) \\\\",
        "\\hline",
    ]
    for v in sorted(VARS):
        ev = v.replace("_", "\\_")
        p1 = spike_percent(dt1, dc1, v)
        p2 = spike_percent(dt2, dc2, v)
        lines.append(f"{ev} & {fmt_pct(p1)} & {fmt_pct(p2)} \\\\")
    lines += ["\\hline", "\\end{tabular}", "\\end{table}"]
    return "\n".join(lines) + "\n"


def fmt_pct(p: float) -> str:
    if math.isnan(p):
        return "nan"
    return f"{p:.4f}"


def spike_percent(dt: xr.Dataset, dc: xr.Dataset, var: str) -> float:
    if var not in dt.data_vars or var not in dc.data_vars:
        return float("nan")
    try:
        t, c = xr.align(dt[var], dc[var], join="inner")
    except Exception:
        return float("nan")
    tv = t.values.astype(float)
    cv = c.values.astype(float)
    t_valid = (tv != FILL) & ~np.isnan(tv)
    c_valid = (cv != FILL) & ~np.isnan(cv)
    n = int(t_valid.sum())
    if n == 0:
        return float("nan")
    removed = int(np.sum(t_valid & ~c_valid))
    return 100.0 * removed / n


def regen_deployment_distance(project: str, dep: int, anchors: dict[int, tuple[float, float]]) -> str | None:
    if dep - 1 not in anchors or dep not in anchors:
        return None
    lat0, lon0 = anchors[dep - 1]
    lat1, lon1 = anchors[dep]
    km = haversine_km(lat0, lon0, lat1, lon1)
    nmi = km / 1.852
    disp = DISPLAY[project]
    def fmt_coord(lat: float, lon: float) -> str:
        return (
            f"{abs(lat):.4f}°{'N' if lat >= 0 else 'S'} & "
            f"{abs(lon):.4f}°{'E' if lon >= 0 else 'W'}"
        )
    out = [
        f"% {disp} mooring deployment distance information",
        "",
        f"The distance between {disp} {dep-1} and {disp} {dep} deployments is "
        f"{km:.2f} kilometers ({nmi:.2f} nautical miles).",
        "",
        "\\begin{table}[ht]",
        "\\centering",
        "\\caption{Deployment coordinates}",
        "\\begin{tabular}{lcc}",
        "\\hline",
        "\\textbf{Deployment} & \\textbf{Latitude} & \\textbf{Longitude} \\\\",
        "\\hline",
        f"{disp} {dep-1} & {fmt_coord(lat0, lon0)} \\\\",
        f"{disp} {dep} & {fmt_coord(lat1, lon1)} \\\\",
        "\\hline",
        "\\end{tabular}",
        "\\end{table}",
        "",
    ]
    return "\n".join(out)


def collect_anchors(project: str) -> dict[int, tuple[float, float]]:
    out: dict[int, tuple[float, float]] = {}
    for dep in DEPLOYMENTS[project]:
        cleaned = cleaned_files(project, dep)
        if not cleaned:
            continue
        ds = open_ds(cleaned[0])
        try:
            lat = float(ds.attrs.get("latitude_anchor_survey", "nan"))
            lon = float(ds.attrs.get("longitude_anchor_survey", "nan"))
        except (TypeError, ValueError):
            continue
        if math.isfinite(lat) and math.isfinite(lon):
            out[dep] = (lat, lon)
    return out


def fix_pressureavailable_macro(macro_path: Path, real_pressure: bool) -> bool:
    if not macro_path.exists():
        return False
    text = macro_path.read_text()
    new_val = "yes" if real_pressure else "no"
    m = re.search(r"\\renewcommand\{\\pressureavailable\}\{([^}]*)\}", text)
    if m is None:
        return False
    current = m.group(1).strip()
    if current == new_val:
        return False
    new_text = re.sub(
        r"\\renewcommand\{\\pressureavailable\}\{[^}]*\}",
        f"\\\\renewcommand{{\\\\pressureavailable}}{{{new_val}}}",
        text,
        count=1,
    )
    # Toggle the pressurenote consistency: when "yes" remove the auto note text
    if new_val == "yes":
        new_text = re.sub(
            r"\\renewcommand\{\\pressurenote\}\{[^}]*\}",
            "\\\\renewcommand{\\\\pressurenote}{}",
            new_text,
        )
    macro_path.write_text(new_text)
    return True


def main() -> None:
    summary: list[str] = []
    for project in ("stratus", "ntas"):
        rdir = REPORT_DIR[project]
        anchors = collect_anchors(project)
        for dep in DEPLOYMENTS[project]:
            chap_dir = rdir / f"{dep}"
            if not chap_dir.exists():
                continue
            # diff_stats
            new_diff = regen_diff_stats(project, dep, chap_dir / "diff_stats.tex")
            if new_diff is not None:
                (chap_dir / "diff_stats.tex").write_text(new_diff)
                summary.append(f"wrote {chap_dir/'diff_stats.tex'}")
            # spike_stats
            new_spike = regen_spike_stats(project, dep, chap_dir / "spike_stats.tex")
            if new_spike is not None:
                (chap_dir / "spike_stats.tex").write_text(new_spike)
                summary.append(f"wrote {chap_dir/'spike_stats.tex'}")
            # deployment_distance
            new_dist = regen_deployment_distance(project, dep, anchors)
            if new_dist is not None:
                (chap_dir / "deployment_distance.tex").write_text(new_dist)
                summary.append(f"wrote {chap_dir/'deployment_distance.tex'}")
            # macros pressureavailable
            cleaned = cleaned_files(project, dep)
            if cleaned:
                ds = open_ds(cleaned[0])
                rp = has_real_pressure(ds)
                if len(cleaned) > 1:
                    rp = rp or has_real_pressure(open_ds(cleaned[1]))
                if fix_pressureavailable_macro(chap_dir / "macros.tex", rp):
                    summary.append(f"updated pressureavailable in {chap_dir/'macros.tex'} -> {'yes' if rp else 'no'}")
    for s in summary:
        print(s)


if __name__ == "__main__":
    main()
