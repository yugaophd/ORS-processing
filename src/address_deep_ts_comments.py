"""Apply the Deep TS review corrections to source and final deliverables."""

from pathlib import Path
from shutil import copy2

import numpy as np
from netCDF4 import Dataset, num2date


ROOT = Path("/mnt/VAST_UOP/ORS/DEEP_TS")
NTAS_ARCHIVE = ROOT / "NTAS/merged_NTAS/archive"
STRATUS_ARCHIVE = ROOT / "STRATUS/merged_stratus/archive"
NTAS_OUTPUT = ROOT / "NTAS/merged_NTAS"
STRATUS_OUTPUT = ROOT / "STRATUS/merged_stratus"

NTAS_TEMP_COMMENT = (
    "Temperature data have been quality controlled according to the process "
    "described in WHOI Technical Report WHOI-2026-04, DOI xxx."
)
STRATUS_TEMP_COMMENT = (
    "Temperature data have been quality controlled according to the process "
    "described in WHOI Technical Report WHOI-2026-05, DOI: xxxx."
)
RAW_COMMENT = (
    "Conductivity, salinity and pressure data are raw data direct from the "
    "instrument; no quality control has been applied. Conductivity and salinity "
    "have known data quality issues (jumps, biases and drifts). Pressure data "
    "has a known data quality issue related to drift at the start of the deployment."
)
DEPTH_ATTRS = {
    "long_name": "measurement depth",
    "standard_name": "depth",
    "units": "meters",
    "positive": "down",
    "reference": "mean_sea_level",
    "coordinate_reference_frame": "urn:ogc:crs:EPSG::5831",
    "axis": "Z",
    "comment": "approximate instrument depth",
}


def mask_interval(path: Path, start: str, end: str, variables: list[str]) -> None:
    with Dataset(path, "r+") as ds:
        time = ds.variables["time"]
        dates = np.asarray(
            num2date(
                time[:],
                time.units,
                calendar=getattr(time, "calendar", "standard"),
                only_use_cftime_datetimes=False,
                only_use_python_datetimes=True,
            ),
            dtype="datetime64[ns]",
        )
        selected = (dates >= np.datetime64(start)) & (dates < np.datetime64(end))
        for name in variables:
            if name in ds.variables:
                values = ds.variables[name][:]
                values[selected] = np.nan
                ds.variables[name][:] = values


def update_metadata(path: Path, site: str, full_product: bool) -> None:
    with Dataset(path, "r+") as ds:
        temperature = ds.variables.get("sea_water_temperature")
        if temperature is not None:
            temperature.setncattr(
                "comment", NTAS_TEMP_COMMENT if site == "NTAS" else STRATUS_TEMP_COMMENT
            )

        if full_product:
            for name in (
                "sea_water_electrical_conductivity",
                "sea_water_practical_salinity",
                "sea_water_absolute_salinity",
                "sea_water_pressure",
            ):
                if name in ds.variables:
                    ds.variables[name].setncattr("comment", RAW_COMMENT)

        if full_product and "latitude" not in ds.variables:
            time = ds.variables["time"]
            dates = np.asarray(
                num2date(
                    time[:],
                    time.units,
                    calendar=getattr(time, "calendar", "standard"),
                    only_use_cftime_datetimes=False,
                    only_use_python_datetimes=True,
                ),
                dtype="datetime64[ns]",
            )
            merge_points = [
                np.datetime64(value.strip().replace("Z", ""))
                for value in str(ds.getncattr("merge_point")).split(",")
                if value.strip() and value.strip().lower() not in {"missing", "none", "nat"}
            ]

            def values_for(name: str) -> list[float]:
                values = []
                for value in str(ds.getncattr(name)).split(","):
                    try:
                        values.append(float(value.strip()))
                    except ValueError:
                        values.append(np.nan)
                return values

            latitudes = values_for("latitude_anchor_survey")
            longitudes = values_for("longitude_anchor_survey")
            depths = values_for("instrument_depth")
            arrays = {
                "latitude": np.full(len(dates), np.nan),
                "longitude": np.full(len(dates), np.nan),
                "depth": np.full(len(dates), np.nan),
            }
            for index, date in enumerate(dates):
                segment = max(
                    (position for position, point in enumerate(merge_points) if date >= point),
                    default=0,
                )
                for name, values in (("latitude", latitudes), ("longitude", longitudes), ("depth", depths)):
                    if segment < len(values):
                        arrays[name][index] = values[segment]
            for name, values in arrays.items():
                variable = ds.createVariable(name, "f8", ("time",), fill_value=np.nan)
                variable[:] = values
                if name == "latitude":
                    variable.setncatts({"units": "degrees_north", "standard_name": "latitude", "long_name": "Latitude"})
                elif name == "longitude":
                    variable.setncatts({"units": "degrees_east", "standard_name": "longitude", "long_name": "Longitude"})
                else:
                    variable.setncatts(DEPTH_ATTRS)

        if "DEPTH" in ds.variables and "depth" not in ds.variables:
            ds.renameVariable("DEPTH", "depth")
        if "depth" in ds.variables:
            depth = ds.variables["depth"]
            for name, value in DEPTH_ATTRS.items():
                depth.setncattr(name, value)
            finite_depth = np.asarray(depth[:], dtype=float)
            finite_depth = finite_depth[np.isfinite(finite_depth)]
            depth.setncatts({
                "valid_min": float(np.min(finite_depth)),
                "valid_max": float(np.max(finite_depth)),
            })

        for name, variable in ds.variables.items():
            if name not in {"time", "latitude", "longitude", "depth"}:
                variable.setncattr("coordinates", "time depth")

            ds.setncattr("coordinates_variables", "latitude longitude depth")

        ds.setncattr(
            "comments",
            (
                (NTAS_TEMP_COMMENT if site == "NTAS" else STRATUS_TEMP_COMMENT)
                + " "
                + RAW_COMMENT
            ),
        )
        if site == "STRATUS" and "instrument_SN" in ds.ncattrs():
            serials = [part.strip() for part in ds.getncattr("instrument_SN").split(",")]
            deployments = [part.strip() for part in ds.getncattr("deployment").split(",")]
            if "21" in deployments:
                serials[deployments.index("21")] = "11379"
                ds.setncattr("instrument_SN", ", ".join(serials))


def create_ntas_temperature_v2() -> Path:
    source = NTAS_OUTPUT / "NTAS_temperature_2011_to_2022_v1.nc"
    destination = NTAS_OUTPUT / "NTAS_temperature_2011_to_2022_v2.nc"
    copy2(source, destination)
    mask_interval(
        destination,
        "2017-08-01",
        "2018-06-13",
        ["sea_water_temperature"],
    )
    mask_interval(
        destination,
        "2021-02-01",
        "2021-11-14",
        ["sea_water_temperature"],
    )
    update_metadata(destination, "NTAS", full_product=False)
    with Dataset(destination, "r+") as ds:
        ds.setncattr("version", "v2")
        ds.setncattr(
            "history",
            "v2: blanked NTAS16 SN 11393 from 2017-08-01 through deployment end "
            "and NTAS19 SN 12247 from 2021-02-01 through deployment end.",
        )
    return destination


def main() -> None:
    # Correct the per-sensor records before they are reused for future merges.
    source_masks = [
        (ROOT / "STRATUS/stratus20/v1/stratus20_10601_cleaned.nc", "2022-10-01", "2022-11-01", [
            "sea_water_temperature", "sea_water_electrical_conductivity", "sea_water_practical_salinity",
            "sea_water_absolute_salinity", "sea_water_pressure",
        ]),
        (ROOT / "STRATUS/stratus20/v1/stratus20_10601_truncated.nc", "2022-10-01", "2022-11-01", [
            "sea_water_temperature", "sea_water_electrical_conductivity", "sea_water_practical_salinity",
            "sea_water_absolute_salinity", "sea_water_pressure",
        ]),
        (ROOT / "STRATUS/stratus21/v1/stratus21_11394_cleaned.nc", "2023-02-28", "2023-12-09", [
            "sea_water_electrical_conductivity", "sea_water_practical_salinity", "sea_water_absolute_salinity",
        ]),
        (ROOT / "STRATUS/stratus21/v1/stratus21_11394_truncated.nc", "2023-02-28", "2023-12-09", [
            "sea_water_electrical_conductivity", "sea_water_practical_salinity", "sea_water_absolute_salinity",
        ]),
        (ROOT / "NTAS/ntas16/v1/NTAS16_11393_cleaned.nc", "2017-08-01", "2018-06-13", [
            "sea_water_temperature", "sea_water_electrical_conductivity", "sea_water_practical_salinity",
            "sea_water_absolute_salinity", "sea_water_pressure",
        ]),
        (ROOT / "NTAS/ntas19/v1/NTAS19_12247_cleaned.nc", "2021-02-01", "2021-11-14", [
            "sea_water_temperature", "sea_water_electrical_conductivity", "sea_water_practical_salinity",
            "sea_water_absolute_salinity", "sea_water_pressure",
        ]),
    ]
    for path, start, end, variables in source_masks:
        if path.exists():
            mask_interval(path, start, end, variables)

    ntas_outputs = [
        NTAS_OUTPUT / "merged_NTAS11_to_NTAS20.nc",
        NTAS_OUTPUT / "merged_NTAS_2011_to_2022.nc",
        NTAS_OUTPUT / "NTAS_temperature_2011_to_2022_v1.nc",
    ]
    stratus_outputs = [
        STRATUS_OUTPUT / "merged_stratus12_to_stratus22.nc",
        STRATUS_OUTPUT / "stratus_2012_to_2023.nc",
        STRATUS_OUTPUT / "stratus_temperature_2012_2023.nc",
        STRATUS_OUTPUT / "stratus_temperature_2012_2025_v3.nc",
    ]
    for path in ntas_outputs:
        update_metadata(path, "NTAS", "temperature" not in path.name.lower())
    for path in stratus_outputs:
        update_metadata(path, "STRATUS", "temperature" not in path.name.lower())


if __name__ == "__main__":
    main()