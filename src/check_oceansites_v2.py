#!/usr/bin/env python3
"""Validate OceanSITES v2 NetCDF filenames and metadata."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import netCDF4 as nc

from create_oceansites_v2 import (
    COMMON_GLOBAL_ATTRS,
    NTAS_ROOT,
    SITE_GLOBAL_ATTRS,
    STRATUS_ROOT,
    VARIABLE_STANDARD_NAMES,
    VARIABLE_UNITS,
)


FILENAME_RE = re.compile(
    r"^OS_(?P<site>NTAS|Stratus)_(?P<year>\d{4}(?:-10)?)_D_deepTS-"
    r"(?P<ctd>SBE16|SBE37WP)-(?P<sn>\d+)\.nc$"
)
DATE_CREATED_RE = re.compile(r"^2026-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
NTAS_YEAR_EXCEPTIONS = {"18": "2020", "19": "2020-10"}


def attr_text(dataset: nc.Dataset, name: str) -> str:
    if name not in dataset.ncattrs():
        return ""
    value = getattr(dataset, name)
    if isinstance(value, bytes):
        return value.decode("utf-8")
    return str(value)


def deployment_from_path(path: Path) -> str:
    match = re.search(r"(?:ntas|stratus)(\d+)", path.as_posix(), flags=re.IGNORECASE)
    return match.group(1) if match else ""


def site_from_path(path: Path) -> str:
    if "/ntas" in path.as_posix().lower() or path.name.startswith("OS_NTAS_"):
        return "NTAS"
    return "Stratus"


def expected_title(site: str, deployment: str) -> str:
    return f"Ocean salinity data from deep sensors on surface mooring {site} deployment {deployment}"


def check_file(path: Path) -> list[str]:
    issues: list[str] = []
    filename_match = FILENAME_RE.match(path.name)
    if not filename_match:
        issues.append(f"{path}: filename does not match OS_SITE_YEAR_D_deepTS-CTDTYPE-SN.nc")
        return issues

    filename_site = filename_match.group("site")
    filename_year = filename_match.group("year")
    path_site = site_from_path(path)
    deployment = deployment_from_path(path)

    if filename_site != path_site:
        issues.append(f"{path.name}: SITE disagrees with path site {path_site}")

    if filename_site == "NTAS" and deployment in NTAS_YEAR_EXCEPTIONS:
        expected_year = NTAS_YEAR_EXCEPTIONS[deployment]
        if filename_year != expected_year:
            issues.append(f"{path.name}: YEAR={filename_year}, expected {expected_year}")

    with nc.Dataset(path) as dataset:
        if len(dataset.dimensions.get("time", [])) == 0:
            issues.append(f"{path.name}: time length is 0")

        for var_name, standard_name in {"time": "time", **VARIABLE_STANDARD_NAMES}.items():
            if var_name not in dataset.variables:
                issues.append(f"{path.name}: missing variable {var_name}")
                continue
            actual = getattr(dataset.variables[var_name], "standard_name", "")
            if actual != standard_name:
                issues.append(f"{path.name}: {var_name}.standard_name={actual!r}, expected {standard_name!r}")

        if "time" in dataset.variables:
            actual_axis = getattr(dataset.variables["time"], "axis", "")
            if actual_axis != "T":
                issues.append(f"{path.name}: time.axis={actual_axis!r}, expected 'T'")

        for var_name, expected_unit in VARIABLE_UNITS.items():
            if var_name not in dataset.variables:
                continue
            actual_unit = getattr(dataset.variables[var_name], "units", "")
            if actual_unit != expected_unit:
                issues.append(f"{path.name}: {var_name}.units={actual_unit!r}, expected {expected_unit!r}")

        for attr_name, expected_value in COMMON_GLOBAL_ATTRS.items():
            actual = attr_text(dataset, attr_name)
            if actual != expected_value:
                issues.append(f"{path.name}: {attr_name}={actual!r}, expected {expected_value!r}")

        for attr_name, expected_value in SITE_GLOBAL_ATTRS[filename_site].items():
            actual = attr_text(dataset, attr_name)
            if actual != expected_value:
                issues.append(f"{path.name}: {attr_name}={actual!r}, expected {expected_value!r}")

        title = attr_text(dataset, "title")
        title_expected = expected_title(filename_site, attr_text(dataset, "deployment") or deployment)
        if title != title_expected:
            issues.append(f"{path.name}: title={title!r}, expected {title_expected!r}")

        date_created = attr_text(dataset, "date_created")
        if not DATE_CREATED_RE.match(date_created):
            issues.append(f"{path.name}: date_created={date_created!r}, expected 2026 timestamp ending in Z")

        version = attr_text(dataset, "version")
        if version != "v2":
            issues.append(f"{path.name}: version={version!r}, expected 'v2'")

    return issues


def files_for_site(site: str, stratus_root: Path, ntas_root: Path) -> list[Path]:
    files: list[Path] = []
    if site in ("all", "stratus"):
        files.extend(stratus_root.glob("stratus*/v2/OS_*.nc"))
    if site in ("all", "ntas"):
        files.extend(ntas_root.glob("ntas*/v2/OS_*.nc"))
    return sorted(files)


def main() -> None:
    parser = argparse.ArgumentParser(description="Check OceanSITES v2 NetCDF files.")
    parser.add_argument("--site", choices=("all", "stratus", "ntas"), default="all")
    parser.add_argument("--stratus-root", type=Path, default=STRATUS_ROOT)
    parser.add_argument("--ntas-root", type=Path, default=NTAS_ROOT)
    args = parser.parse_args()

    files = files_for_site(args.site, args.stratus_root, args.ntas_root)
    issues: list[str] = []
    for path in files:
        issues.extend(check_file(path))

    if issues:
        print(f"Checked {len(files)} v2 file(s): FAILED with {len(issues)} issue(s)")
        for issue in issues:
            print(f"- {issue}")
        raise SystemExit(1)

    counts = {
        "Stratus": sum(1 for path in files if site_from_path(path) == "Stratus"),
        "NTAS": sum(1 for path in files if site_from_path(path) == "NTAS"),
    }
    print(
        f"Checked {len(files)} v2 file(s): OK "
        f"({counts['Stratus']} Stratus, {counts['NTAS']} NTAS)"
    )


if __name__ == "__main__":
    main()
