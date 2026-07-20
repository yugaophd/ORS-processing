"""Patch merged NetCDF attribute drift so per-deployment list-valued attrs all
have one entry per deployment. NTAS 15 has no data on disk, so its slot is
marked with the literal token ``missing``.
"""
from __future__ import annotations

from pathlib import Path

import netCDF4 as nc

LIST_ATTRS = [
    "platform_code",
    "instrument_model",
    "instrument_SN",
    "merge_point",
    "latitude_anchor_survey",
    "longitude_anchor_survey",
    "instrument_depth",
    "platform_anchor_over_time",
    "platform_buoy_recovery_time",
]


def split_csv(v: str) -> list[str]:
    return [s.strip() for s in v.split(",")]


def join_csv(parts: list[str]) -> str:
    return ", ".join(parts)


def patch_stratus(path: Path) -> None:
    with nc.Dataset(path, "r+") as ds:
        # Stratus merged covers stratus12..22 = 11 deployments
        target = 11
        for k in LIST_ATTRS:
            if k not in ds.ncattrs():
                continue
            v = ds.getncattr(k)
            parts = split_csv(str(v))
            if k == "platform_code":
                # one value or short list -> pad with last value
                pad = parts[0] if parts else "Stratus"
                parts = (parts + [pad] * target)[:target]
            elif k == "instrument_model":
                # known pattern: SBE-16, SBE37*10
                if len(parts) == target - 1:
                    # Append one trailing SBE37 to match SN list length
                    parts = parts + ["SBE37"]
                elif len(parts) < target:
                    parts = parts + [parts[-1]] * (target - len(parts))
            else:
                if len(parts) < target:
                    parts = parts + ["missing"] * (target - len(parts))
            ds.setncattr(k, join_csv(parts[:target]))
        print(f"patched {path}")


def patch_ntas(path: Path) -> None:
    # NTAS merged covers 10 deployments (NTAS 11..20). NTAS 15 has no data.
    # Existing arrays contain 9 entries in NTAS 11,12,13,14,16,17,18,19,20 order.
    # Insert "missing" at index 4 (between NTAS 14 and NTAS 16).
    target = 10
    missing_index = 4
    with nc.Dataset(path, "r+") as ds:
        for k in LIST_ATTRS:
            if k not in ds.ncattrs():
                continue
            v = ds.getncattr(k)
            parts = split_csv(str(v))
            if k == "platform_code":
                base = parts[0] if parts else "NTAS"
                parts = [base] * target
                parts[missing_index] = "missing"
            elif len(parts) == target - 1:
                parts = parts[:missing_index] + ["missing"] + parts[missing_index:]
            elif len(parts) < target:
                parts = parts + ["missing"] * (target - len(parts))
            ds.setncattr(k, join_csv(parts[:target]))
        print(f"patched {path}")


def main() -> None:
    stratus = [
        Path("/Users/Shared/ORS/DEEP_TS/STRATUS/merged_stratus/merged_stratus12_to_stratus22.nc"),
        Path("/Users/Shared/ORS/DEEP_TS/STRATUS/merged_stratus/stratus_2012_to_2023.nc"),
    ]
    ntas = [
        Path("/Users/Shared/ORS/DEEP_TS/NTAS/merged_NTAS/merged_NTAS11_to_NTAS20.nc"),
        Path("/Users/Shared/ORS/DEEP_TS/NTAS/merged_NTAS/merged_NTAS_2011_to_2022.nc"),
    ]
    for p in stratus:
        if p.exists():
            patch_stratus(p)
    for p in ntas:
        if p.exists():
            patch_ntas(p)


if __name__ == "__main__":
    main()
