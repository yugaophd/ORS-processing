#!/usr/bin/env python3
"""Create OceanSITES v2 NetCDF products from reviewed v1 cleaned files."""

from __future__ import annotations

import argparse
import re
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import netCDF4 as nc


STRATUS_ROOT = Path("/Users/Shared/ORS/DEEP_TS/STRATUS")
NTAS_ROOT = Path("/Users/Shared/ORS/DEEP_TS/NTAS")

VARIABLE_STANDARD_NAMES = {
    "sea_water_temperature": "sea_water_temperature",
    "sea_water_electrical_conductivity": "sea_water_electrical_conductivity",
    "sea_water_pressure": "sea_water_pressure",
    "sea_water_practical_salinity": "sea_water_practical_salinity",
    "sea_water_absolute_salinity": "sea_water_absolute_salinity",
}

VARIABLE_UNITS = {
    "sea_water_temperature": "degree_C",
    "sea_water_electrical_conductivity": "S m-1",
    "sea_water_practical_salinity": "1",
    "sea_water_absolute_salinity": "g kg-1",
}

COMMON_GLOBAL_ATTRS = {
    "data_mode": "D",
    "data_assembly_center": "Upper Ocean Processes Group at Woods Hole Oceanographic",
    "institution": "Woods Hole Oceanographic Institution",
    "QC_indicator": "good data",
    "processing_level": "Data manually reviewed, clocks checked",
}

SITE_GLOBAL_ATTRS = {
    "Stratus": {
        "site_code": "Stratus",
        "platform_code": "Stratus",
        "principal_investigator": "Robert Weller",
        "principal_investigator_email": "rweller@whoi.edu",
        "principal_investigator_id": "https://orcid.org/0000-0001-8001-6886",
        "experiment": "Stratus Ocean Reference Station",
        "wmo_platform_code": "38400",
        "citation": (
            "Data from the Stratus Ocean Reference Station were made available by "
            "Dr. Robert Weller of the Woods Hole Oceanographic Institution, with "
            "support from the Global Ocean Monitoring and Observing (GOMO) Program "
            "of the National Oceanic and Atmospheric Administration, U.S. Department "
            "of Commerce. These data are made freely available by the OceanSITES "
            "project and the national programs that contribute to it."
        ),
        "acknowledgement": (
            "Support for this research was provided by the Global Ocean Monitoring "
            "and Observing (GOMO) Program, formerly the Ocean Observing and Monitoring "
            "Division, Climate Program Office (FundRef number 100007298), of the "
            "National Oceanic and Atmospheric Administration, U.S. Department of "
            "Commerce, under grant NA14OAR4320158."
        ),
    },
    "NTAS": {
        "site_code": "NTAS",
        "platform_code": "NTAS",
        "principal_investigator": "A. Plueddemann",
        "principal_investigator_email": "aplueddemann@whoi.edu",
        "principal_investigator_id": "https://orcid.org/0000-0003-0228-9795",
        "experiment": "NTAS Ocean Reference Station",
        "wmo_platform_code": "48401",
        "citation": (
            "Data from the NTAS Ocean Reference Station were collected and published "
            "by Dr. Albert Plueddemann of the Woods Hole Oceanographic Institution. "
            "The data is made freely available by the OceanSITES project and by the "
            "national programs that contribute to it."
        ),
        "acknowledgement": (
            "This project is funded by the Global Ocean Monitoring and Observing "
            "(GOMO) Program, formerly the Ocean Observing and Monitoring Division, "
            "Climate Program Office (FundRef number 100007298), National Oceanic "
            "and Atmospheric Administration, U.S. Department of Commerce, under grant "
            "NA14OAR4320158."
        ),
    },
}

SPECIAL_YEAR_LABELS = {
    ("NTAS", "18"): "2020",
    ("NTAS", "19"): "2020-10",
}


@dataclass(frozen=True)
class V2Product:
    source: Path
    destination: Path
    site: str
    deployment: str
    serial_number: str
    year_label: str
    ctd_type: str
    time_length: int


def utc_now_label() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def source_files(root: Path, site: str) -> list[Path]:
    prefix = "stratus" if site == "Stratus" else "ntas"
    return sorted(root.glob(f"{prefix}*/v1/*_cleaned.nc"))


def attr_text(dataset: nc.Dataset, name: str, default: str = "") -> str:
    if name not in dataset.ncattrs():
        return default
    value = getattr(dataset, name)
    if isinstance(value, bytes):
        return value.decode("utf-8")
    return str(value)


def deployment_from_path(path: Path, site: str) -> str:
    match = re.search(rf"{site.lower()}(\d+)", path.as_posix(), flags=re.IGNORECASE)
    if not match:
        raise ValueError(f"Cannot infer deployment from path: {path}")
    return match.group(1)


def serial_from_path(path: Path) -> str:
    match = re.search(r"_(\d+)_cleaned\.nc$", path.name, flags=re.IGNORECASE)
    if not match:
        raise ValueError(f"Cannot infer serial number from file name: {path.name}")
    return match.group(1)


def year_label(site: str, deployment: str, dataset: nc.Dataset) -> str:
    special = SPECIAL_YEAR_LABELS.get((site, deployment))
    if special:
        return special

    for attr_name in ("time_coverage_start", "platform_anchor_over_time"):
        match = re.search(r"\b(\d{4})\b", attr_text(dataset, attr_name))
        if match:
            return match.group(1)

    raise ValueError(f"Cannot infer deployment year for {site}{deployment}")


def normalize_ctd_type(instrument_model: str) -> str:
    model = re.sub(r"[^A-Z0-9]", "", instrument_model.upper())
    if "SBE16" in model:
        return "SBE16"
    if "SBE37" in model:
        return "SBE37WP"
    raise ValueError(f"Unsupported instrument model for CTDTYPE: {instrument_model!r}")


def destination_for(source: Path, site: str, root: Path) -> V2Product | None:
    with nc.Dataset(source) as dataset:
        time_length = len(dataset.dimensions.get("time", []))
        deployment = attr_text(dataset, "deployment") or deployment_from_path(source, site)
        serial_number = attr_text(dataset, "instrument_SN") or serial_from_path(source)
        model = attr_text(dataset, "instrument_model")

        if time_length == 0:
            return None

        ctd_type = normalize_ctd_type(model)
        product_year = year_label(site, deployment, dataset)
        file_name = f"OS_{site}_{product_year}_D_deepTS-{ctd_type}-{serial_number}.nc"
        destination = root / f"{site.lower()}{deployment}" / "v2" / file_name

        return V2Product(
            source=source,
            destination=destination,
            site=site,
            deployment=deployment,
            serial_number=serial_number,
            year_label=product_year,
            ctd_type=ctd_type,
            time_length=time_length,
        )


def set_attrs(target: nc.Dataset, attrs: dict[str, str]) -> None:
    for name, value in attrs.items():
        setattr(target, name, value)


def patch_metadata(path: Path, product: V2Product, date_created: str) -> None:
    with nc.Dataset(path, "r+") as dataset:
        if "time" in dataset.variables:
            dataset.variables["time"].standard_name = "time"
            dataset.variables["time"].axis = "T"

        for var_name, standard_name in VARIABLE_STANDARD_NAMES.items():
            if var_name not in dataset.variables:
                continue
            variable = dataset.variables[var_name]
            variable.standard_name = standard_name
            if var_name in VARIABLE_UNITS:
                variable.units = VARIABLE_UNITS[var_name]

        title = (
            "Ocean salinity data from deep sensors on surface mooring "
            f"{product.site} deployment {product.deployment}"
        )
        set_attrs(
            dataset,
            {
                **COMMON_GLOBAL_ATTRS,
                **SITE_GLOBAL_ATTRS[product.site],
                "title": title,
                "date_created": date_created,
                "version": "v2",
            },
        )


def validate_product(path: Path, product: V2Product) -> list[str]:
    issues: list[str] = []
    with nc.Dataset(path) as dataset:
        for attr_name, expected in {
            "site_code": product.site,
            "data_mode": "D",
            "version": "v2",
            "date_created": attr_text(dataset, "date_created"),
        }.items():
            if not attr_text(dataset, attr_name):
                issues.append(f"{path.name}: missing global attr {attr_name}")
            elif expected and attr_text(dataset, attr_name) != expected:
                issues.append(f"{path.name}: {attr_name}={attr_text(dataset, attr_name)!r}, expected {expected!r}")

        if "time" not in dataset.variables:
            issues.append(f"{path.name}: missing time variable")
        else:
            time_var = dataset.variables["time"]
            if getattr(time_var, "standard_name", "") != "time":
                issues.append(f"{path.name}: time standard_name not set")
            if getattr(time_var, "axis", "") != "T":
                issues.append(f"{path.name}: time axis not set")

        for var_name, standard_name in VARIABLE_STANDARD_NAMES.items():
            if var_name not in dataset.variables:
                continue
            variable = dataset.variables[var_name]
            if getattr(variable, "standard_name", "") != standard_name:
                issues.append(f"{path.name}: {var_name} standard_name not set")
            expected_units = VARIABLE_UNITS.get(var_name)
            if expected_units and getattr(variable, "units", "") != expected_units:
                issues.append(f"{path.name}: {var_name} units={getattr(variable, 'units', '')!r}")

    return issues


def create_products(root: Path, site: str, date_created: str, overwrite: bool, dry_run: bool) -> tuple[int, int]:
    created = 0
    skipped = 0

    for source in source_files(root, site):
        product = destination_for(source, site, root)
        if product is None:
            print(f"SKIP no time data: {source}")
            skipped += 1
            continue

        if product.destination.exists() and not overwrite:
            print(f"SKIP exists: {product.destination}")
            skipped += 1
            continue

        print(f"{'DRY-RUN' if dry_run else 'WRITE'} {source} -> {product.destination}")
        if dry_run:
            created += 1
            continue

        product.destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(product.source, product.destination)
        patch_metadata(product.destination, product, date_created)
        issues = validate_product(product.destination, product)
        if issues:
            raise RuntimeError("\n".join(issues))
        created += 1

    return created, skipped


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create OceanSITES v2 files with reviewed metadata and OS_SITE_YEAR_D_deepTS-CTDTYPE-SN.nc names."
    )
    parser.add_argument("--site", choices=("all", "stratus", "ntas"), default="all")
    parser.add_argument("--stratus-root", type=Path, default=STRATUS_ROOT)
    parser.add_argument("--ntas-root", type=Path, default=NTAS_ROOT)
    parser.add_argument("--date-created", default=utc_now_label())
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    sites: list[tuple[str, Path]] = []
    if args.site in ("all", "stratus"):
        sites.append(("Stratus", args.stratus_root))
    if args.site in ("all", "ntas"):
        sites.append(("NTAS", args.ntas_root))

    total_created = 0
    total_skipped = 0
    for site, root in sites:
        created, skipped = create_products(
            root=root,
            site=site,
            date_created=args.date_created,
            overwrite=args.overwrite,
            dry_run=args.dry_run,
        )
        total_created += created
        total_skipped += skipped

    action = "would create" if args.dry_run else "created"
    print(f"Done: {action} {total_created} file(s), skipped {total_skipped} file(s).")


if __name__ == "__main__":
    main()
