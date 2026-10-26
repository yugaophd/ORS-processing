"""Apply the Deep TS review corrections to source and final deliverables."""

from pathlib import Path
from shutil import copyfile
from datetime import datetime, timezone
from zipfile import ZIP_DEFLATED, ZipFile

import numpy as np
import xarray as xr
from netCDF4 import Dataset, num2date

from create_sp30m import create_product


ROOT = Path("/mnt/VAST_UOP/ORS/DEEP_TS")
NTAS_ARCHIVE = ROOT / "NTAS/merged_NTAS/archive"
STRATUS_ARCHIVE = ROOT / "STRATUS/merged_stratus/archive"
NTAS_OUTPUT = ROOT / "NTAS/merged_NTAS"
STRATUS_OUTPUT = ROOT / "STRATUS/merged_stratus"

NTAS_TEMP_COMMENT = (
    "Temperature data have been quality controlled according to the process "
    "described in WHOI Technical Report WHOI-2026-04. Dataset DOI: "
    "https://doi.org/10.26027/DATATLTM44."
)
STRATUS_TEMP_COMMENT = (
    "Temperature data have been quality controlled according to the process "
    "described in WHOI Technical Report WHOI-2026-05. Dataset DOI: "
    "https://doi.org/10.26027/DATAKX5CQK."
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
    "coordinate_reference_frame": "urn:ogc:def:crs:EPSG::5831",
    "axis": "Z",
    "comment": "approximate instrument depth",
    "QC_indicator": "probably good data",
}
# WGS84 lat/lon attributes matching the OceanSITES CDL reference for surveyed anchor positions.
LATITUDE_ATTRS = {
    "reference": "WGS84",
    "coordinate_reference_frame": "urn:ogc:def:crs:EPSG::4326",
    "uncertainty": 0.01,
    "axis": "Y",
    "comment": "surveyed anchor position",
    "QC_indicator": "probably good data",
}
LONGITUDE_ATTRS = {
    "reference": "WGS84",
    "coordinate_reference_frame": "urn:ogc:def:crs:EPSG::4326",
    "uncertainty": 0.01,
    "axis": "X",
    "comment": "surveyed anchor position",
    "QC_indicator": "probably good data",
}
PROCESSING_LEVEL = "Data verified against model or other contextual information"
TIME_COORDINATE_ATTRS = {
    "standard_name": "time",
    "long_name": "Time",
    "axis": "T",
    "QC_indicator": "probably good data",
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
            finite_temperature = np.asarray(temperature[:], dtype=float)
            finite_temperature = finite_temperature[np.isfinite(finite_temperature)]
            if finite_temperature.size:
                temperature.setncatts({
                    "reference_scale": "ITS-90",
                    "valid_min": float(np.min(finite_temperature)),
                    "valid_max": float(np.max(finite_temperature)),
                })

        time_var = ds.variables.get("time")
        if time_var is not None:
            time_var.setncatts({
                "axis": "T",
                "valid_min": float(np.min(time_var[:])),
                "valid_max": float(np.max(time_var[:])),
                "QC_indicator": "probably good data",
            })
            if "_FillValue" in time_var.ncattrs():
                time_var.delncattr("_FillValue")

        latitude_var = ds.variables.get("latitude")
        if latitude_var is not None:
            finite_latitude = np.asarray(latitude_var[:], dtype=float)
            finite_latitude = finite_latitude[np.isfinite(finite_latitude)]
            attrs = dict(LATITUDE_ATTRS)
            if finite_latitude.size:
                attrs["valid_min"] = float(np.min(finite_latitude))
                attrs["valid_max"] = float(np.max(finite_latitude))
            latitude_var.setncatts(attrs)
            if "_FillValue" in latitude_var.ncattrs():
                latitude_var.delncattr("_FillValue")

        longitude_var = ds.variables.get("longitude")
        if longitude_var is not None:
            finite_longitude = np.asarray(longitude_var[:], dtype=float)
            finite_longitude = finite_longitude[np.isfinite(finite_longitude)]
            attrs = dict(LONGITUDE_ATTRS)
            if finite_longitude.size:
                attrs["valid_min"] = float(np.min(finite_longitude))
                attrs["valid_max"] = float(np.max(finite_longitude))
            longitude_var.setncatts(attrs)
            if "_FillValue" in longitude_var.ncattrs():
                longitude_var.delncattr("_FillValue")

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
            if not np.all(np.isfinite(finite_depth)):
                raise ValueError(f"Coordinate depth contains missing/non-finite values: {path}")
            finite_depth = finite_depth[np.isfinite(finite_depth)]
            depth.setncatts({
                "valid_min": float(np.min(finite_depth)),
                "valid_max": float(np.max(finite_depth)),
            })
            if "_FillValue" in depth.ncattrs():
                depth.delncattr("_FillValue")

        for name, attrs in (
            ("latitude", LATITUDE_ATTRS),
            ("longitude", LONGITUDE_ATTRS),
        ):
            if name not in ds.variables:
                continue
            variable = ds.variables[name]
            values = np.asarray(variable[:], dtype=float)
            if not np.all(np.isfinite(values)):
                raise ValueError(f"Coordinate {name} contains missing/non-finite values: {path}")
            bounds = {"valid_min": float(np.min(values)), "valid_max": float(np.max(values))}
            variable.setncatts(attrs | bounds)
            if "_FillValue" in variable.ncattrs():
                variable.delncattr("_FillValue")

        if "time" in ds.variables:
            time = ds.variables["time"]
            values = np.asarray(time[:], dtype=float)
            if not np.all(np.isfinite(values)):
                raise ValueError(f"Coordinate time contains missing/non-finite values: {path}")
            time.setncatts(TIME_COORDINATE_ATTRS | {
                "valid_min": float(np.min(values)),
                "valid_max": float(np.max(values)),
            })
            units = str(time.units)
            if " since " in units:
                unit, reference = units.split(" since ", 1)
                reference = reference.replace(" ", "T")
                if not reference.endswith("Z"):
                    reference += "Z"
                time.setncattr("units", f"{unit} since {reference}")
            if "_FillValue" in time.ncattrs():
                time.delncattr("_FillValue")

        for name, variable in ds.variables.items():
            if name in {"time", "latitude", "longitude", "depth"}:
                variable.setncattr("processing_level", PROCESSING_LEVEL)
                if name != "time":
                    variable.setncattr("QC_indicator", "probably good data")
                continue
            variable.setncattr("coordinates", "time depth latitude longitude")
            if "data_mode" in variable.ncattrs():
                variable.delncattr("data_mode")
            variable.setncattr("DM_indicator", "D")
            if name in {
                "sea_water_temperature",
                "sea_water_electrical_conductivity",
                "sea_water_pressure",
                "sea_water_practical_salinity",
                "sea_water_absolute_salinity",
            }:
                variable.setncattr("standard_name", name)
            variable_units = {
                "sea_water_temperature": "degree_C",
                "sea_water_electrical_conductivity": "S m-1",
                "sea_water_pressure": "dbar",
                "sea_water_practical_salinity": "1",
                "sea_water_absolute_salinity": "g kg-1",
            }
            if name in variable_units:
                variable.setncattr("units", variable_units[name])
            if name == "sea_water_temperature":
                variable.setncattr("processing_level", PROCESSING_LEVEL)
                variable.setncattr("QC_indicator", "probably good data")
                variable.setncattr("reference_scale", "ITS-90")
                finite = np.asarray(variable[:], dtype=float)
                finite = finite[np.isfinite(finite)]
                if finite.size:
                    variable.setncatts({"valid_min": float(np.min(finite)), "valid_max": float(np.max(finite))})
            else:
                variable.setncattr("processing_level", "Raw instrument data")
                variable.setncattr("QC_indicator", "unknown")

        if "coordinates_variables" in ds.ncattrs():
            ds.delncattr("coordinates_variables")

        if "processing_date" in ds.ncattrs():
            ds.delncattr("processing_date")

        ds.setncattr("processing_level", PROCESSING_LEVEL)
        ds.setncattr("update_interval", "void")
        ds.setncattr("time_coverage_resolution", "PT30M")
        ds.setncattr("data_mode", "D")
        ds.setncattr("format_version", "1.5")
        ds.setncattr("Conventions", "CF-1.8, OceanSITES-1.5, ACDD-1.3")
        ds.setncattr("date_created", datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
        if site == "STRATUS":
            ds.setncattr("site_code", "STRATUS")
            ds.setncattr("platform_code", "STRATUS")
            deployments = [value.strip() for value in str(getattr(ds, "deployment", "")).split(",")]
            if deployments:
                ds.setncattr(
                    "instrument_model",
                    ", ".join("SBE-16" if index == 0 else "SBE37" for index in range(len(deployments))),
                )
            ds.setncattr("institution", "Woods Hole Oceanographic Institution")
            ds.setncattr("version", "v2")
            if full_product:
                ds.setncattr("title", "Stratus Ocean Reference Station merged observations")
                ds.setncattr("summary", "Merged Stratus temperature, conductivity, salinity, and pressure observations.")
            else:
                ds.setncattr("title", "Stratus Ocean Reference Station temperature time series")
                ds.setncattr("summary", "Merged Stratus sea-water temperature observations from 2012 through 2025.")
        else:
            ds.setncattr("site_code", "NTAS")
            ds.setncattr("platform_code", "NTAS")
            ds.setncattr("title", "NTAS Ocean Reference Station merged observations")
            if full_product:
                ds.setncattr("summary", "Merged NTAS temperature, conductivity, salinity, and pressure observations from 2011 through 2022.")
            else:
                ds.setncattr("summary", "Merged NTAS sea-water temperature observations from 2011 through 2022.")
            ds.setncattr("institution", "Woods Hole Oceanographic Institution")
            ds.setncattr("version", "v2")
        if "principal_investigator" not in ds.ncattrs():
            ds.setncattr(
                "principal_investigator",
                "Albert Plueddemann" if site == "NTAS" else "Robert Weller",
            )

        if "time" in ds.variables:
            time = ds.variables["time"]
            dates = num2date(
                time[:],
                time.units,
                calendar=getattr(time, "calendar", "standard"),
                only_use_cftime_datetimes=False,
                only_use_python_datetimes=True,
            )
            ds.setncattr("time_coverage_start", dates[0].strftime("%Y-%m-%dT%H:%M:%SZ"))
            ds.setncattr("time_coverage_end", dates[-1].strftime("%Y-%m-%dT%H:%M:%SZ"))

        for attr in (
            "platform_anchor_over_time",
            "platform_buoy_recovery_time",
            "merge_point",
            "date_modified",
        ):
            if attr not in ds.ncattrs():
                continue
            parts = str(ds.getncattr(attr)).split(",")
            normalized = []
            for part in parts:
                value = part.strip()
                if value.lower() in {"missing", "none", "nat", ""}:
                    normalized.append(value)
                    continue
                try:
                    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
                    if parsed.tzinfo is None:
                        parsed = parsed.replace(tzinfo=timezone.utc)
                    normalized.append(parsed.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
                except ValueError:
                    normalized.append(value)
            ds.setncattr(attr, ", ".join(normalized))

        for coord, minimum, maximum, units in (
            ("latitude", "geospatial_lat_min", "geospatial_lat_max", "degrees_north"),
            ("longitude", "geospatial_lon_min", "geospatial_lon_max", "degrees_east"),
            ("depth", "geospatial_vertical_min", "geospatial_vertical_max", "meters"),
        ):
            if coord not in ds.variables:
                continue
            values = np.asarray(ds.variables[coord][:], dtype=float)
            ds.setncattr(minimum, str(float(np.min(values))))
            ds.setncattr(maximum, str(float(np.max(values))))
            if coord == "depth":
                ds.setncattr("geospatial_vertical_units", units)
                ds.setncattr("geospatial_vertical_positive", "down")
            else:
                ds.setncattr(f"{minimum.rsplit('_', 1)[0]}_units", units)

        comments = NTAS_TEMP_COMMENT if site == "NTAS" else STRATUS_TEMP_COMMENT
        if full_product:
            comments = f"{comments} {RAW_COMMENT}"
        ds.setncattr("comments", comments)
        ds.setncattr(
            "references",
            "https://doi.org/10.26027/DATATLTM44"
            if site == "NTAS"
            else "https://doi.org/10.26027/DATAKX5CQK",
        )
        existing_history = str(getattr(ds, "history", "")).strip()
        correction_history = (
            "Applied Stratus 20 SN 10601 October 2022 temperature mask; "
            "applied Stratus 21 SN 11394 conductivity and salinity mask. "
            "Source: merged Stratus 2012-2025 v1 products."
            if site == "STRATUS"
            else "Applied NTAS16 SN 11393 and NTAS19 SN 12247 masks. "
            "Source: merged NTAS11-NTAS20 v1 product; time and coordinates aligned to the reviewed temperature product."
        )
        if correction_history not in existing_history:
            ds.setncattr("history", f"{existing_history} {correction_history}".strip())
        if site == "STRATUS" and "instrument_SN" in ds.ncattrs():
            serials = [part.strip() for part in ds.getncattr("instrument_SN").split(",")]
            deployments = [part.strip() for part in ds.getncattr("deployment").split(",")]
            if "21" in deployments:
                serials[deployments.index("21")] = "11379"
                ds.setncattr("instrument_SN", ", ".join(serials))


def create_ntas_temperature_v2() -> Path:
    source = NTAS_OUTPUT / "NTAS_temperature_2011_to_2022_v1.nc"
    destination = NTAS_OUTPUT / "NTAS_temperature_2011_to_2022_v2.nc"
    copyfile(source, destination)
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


def apply_stratus_output_masks(path: Path, temperature_only: bool) -> None:
    variables = ["sea_water_temperature"] if temperature_only else [
        "sea_water_temperature",
        "sea_water_electrical_conductivity",
        "sea_water_practical_salinity",
        "sea_water_absolute_salinity",
        "sea_water_pressure",
    ]
    mask_interval(path, "2022-10-01", "2022-11-01", variables)
    if not temperature_only:
        mask_interval(
            path,
            "2023-02-28",
            "2023-12-09",
            [
                "sea_water_electrical_conductivity",
                "sea_water_practical_salinity",
                "sea_water_absolute_salinity",
            ],
        )


def fill_missing_coordinates_from_metadata(path: Path) -> None:
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
        merge_parts = str(ds.getncattr("merge_point")).split(",")
        merge_points = []
        for part in merge_parts:
            value = part.strip().replace("Z", "")
            try:
                merge_points.append(np.datetime64(value, "ns"))
            except ValueError:
                merge_points.append(None)

        attr_to_variable = {
            "latitude_anchor_survey": "latitude",
            "longitude_anchor_survey": "longitude",
            "instrument_depth": "depth" if "depth" in ds.variables else "DEPTH",
        }
        for attr, variable_name in attr_to_variable.items():
            if attr not in ds.ncattrs() or variable_name not in ds.variables:
                continue
            source_values = []
            for value in str(ds.getncattr(attr)).split(","):
                try:
                    source_values.append(float(value.strip()))
                except ValueError:
                    source_values.append(np.nan)
            if len(source_values) != len(merge_points):
                raise ValueError(f"{attr} and merge_point lengths differ in {path}")
            variable = ds.variables[variable_name]
            values = np.asarray(variable[:], dtype=float)
            missing = ~np.isfinite(values)
            for index in np.flatnonzero(missing):
                segment = max(
                    (position for position, point in enumerate(merge_points)
                     if point is not None and dates[index] >= point),
                    default=None,
                )
                if segment is not None and np.isfinite(source_values[segment]):
                    values[index] = source_values[segment]
            variable[:] = values


def remove_missing_ntas_deployment_slot(path: Path) -> None:
    list_attributes = (
        "platform_code",
        "instrument_model",
        "instrument_SN",
        "merge_point",
        "latitude_anchor_survey",
        "longitude_anchor_survey",
        "instrument_depth",
        "platform_anchor_over_time",
        "platform_buoy_recovery_time",
    )
    with Dataset(path, "r+") as ds:
        deployment_count = len(str(ds.getncattr("deployment")).split(","))
        for name in list_attributes:
            if name not in ds.ncattrs():
                continue
            values = [value.strip() for value in str(ds.getncattr(name)).split(",")]
            if len(values) == deployment_count + 1 and "missing" in values:
                missing_index = values.index("missing")
                values.pop(missing_index)
                ds.setncattr(name, ", ".join(values))


def align_ntas_full_to_temperature(full_path: Path, temperature_path: Path) -> None:
    with xr.open_dataset(full_path) as source, xr.open_dataset(temperature_path) as reference:
        source = source.load()
        reference = reference.load()
        _, keep = np.unique(source.time.values, return_index=True)
        source = source.isel(time=np.sort(keep))
        if source.sizes["time"] != reference.sizes["time"]:
            raise ValueError(
                "NTAS full and temperature products do not have the same unique-time count: "
                f"{source.sizes['time']} != {reference.sizes['time']}"
            )
        source_temperature = np.asarray(source["sea_water_temperature"].values, dtype=float)
        reference_temperature = np.asarray(reference["sea_water_temperature"].values, dtype=float)
        shared = np.isfinite(source_temperature) & np.isfinite(reference_temperature)
        if not np.allclose(source_temperature[shared], reference_temperature[shared], rtol=0, atol=1e-10):
            raise ValueError("NTAS full-product temperatures do not match the reference temperature product")

        if "DEPTH" in source and "depth" not in source:
            source = source.rename({"DEPTH": "depth"})
        source = source.assign_coords(time=reference.time)
        for coordinate in ("latitude", "longitude", "depth"):
            if coordinate not in source or coordinate not in reference:
                raise ValueError(f"Missing {coordinate} coordinate in an NTAS product")
            source = source.assign_coords({coordinate: reference[coordinate]})

        temporary = full_path.with_name(full_path.stem + ".aligned.tmp.nc")
        for variable in source.variables.values():
            variable.encoding = {}
        source.to_netcdf(temporary, format="NETCDF4")
    temporary.replace(full_path)


def ocean_sites_name(path: Path, platform: str, content: str) -> str:
    with Dataset(path) as ds:
        time = ds.variables["time"]
        dates = num2date(
            [time[0], time[-1]],
            time.units,
            calendar=getattr(time, "calendar", "standard"),
            only_use_cftime_datetimes=False,
            only_use_python_datetimes=True,
        )
        start_end = f"{dates[0]:%Y%m%d}-{dates[-1]:%Y%m%d}"
    return f"OS_{platform}_{start_end}_GRD_{content}30M.nc"


def create_stratus_2023_temperature(source: Path, destination: Path) -> None:
    with xr.open_dataset(source) as ds:
        subset = ds.sel(time=slice(None, "2023-12-31T23:59:59"))
        subset.load().to_netcdf(destination, format="NETCDF4")
    update_metadata(destination, "STRATUS", full_product=False)


def write_package(zip_path: Path, products: list[Path], readme: str) -> None:
    readme_path = zip_path.parent / "ReadMe_OceanSITES.txt"
    manifest_path = zip_path.parent / "MANIFEST.TXT"
    readme_path.write_text(readme.strip() + "\n", encoding="ascii")
    manifest_path.write_text(
        "\n".join([*(product.name for product in products), readme_path.name, "MANIFEST.TXT"]) + "\n",
        encoding="ascii",
    )
    with ZipFile(zip_path, "w", compression=ZIP_DEFLATED, compresslevel=6) as archive:
        for product in products:
            archive.write(product, arcname=product.name)
        archive.write(readme_path, arcname=readme_path.name)
        archive.write(manifest_path, arcname=manifest_path.name)


def set_history(path: Path, value: str) -> None:
    with Dataset(path, "r+") as ds:
        ds.setncattr("history", value)


def finalize_current_merged_products() -> list[Path]:
    ntas_temperature = NTAS_OUTPUT / "OS_NTAS_20111125-20221015_GRD_T30M.nc"
    update_metadata(ntas_temperature, "NTAS", full_product=False)
    set_history(
        ntas_temperature,
        "Source file: archive/NTAS_temperature_2011_to_2022_v1.nc (v1). "
        "Applied NTAS16 SN 11393 and NTAS19 SN 12247 temperature masks.",
    )

    ntas_full_source = NTAS_ARCHIVE / "merged_NTAS11_to_NTAS20.nc"
    ntas_full = NTAS_OUTPUT / ocean_sites_name(ntas_temperature, "NTAS", "TSP")
    copyfile(ntas_full_source, ntas_full)
    mask_interval(
        ntas_full,
        "2017-08-01",
        "2018-06-13",
        [
            "sea_water_temperature",
            "sea_water_electrical_conductivity",
            "sea_water_practical_salinity",
            "sea_water_absolute_salinity",
            "sea_water_pressure",
        ],
    )
    mask_interval(
        ntas_full,
        "2021-02-01",
        "2021-11-14",
        [
            "sea_water_temperature",
            "sea_water_electrical_conductivity",
            "sea_water_practical_salinity",
            "sea_water_absolute_salinity",
            "sea_water_pressure",
        ],
    )
    remove_missing_ntas_deployment_slot(ntas_full)
    align_ntas_full_to_temperature(ntas_full, ntas_temperature)
    update_metadata(ntas_full, "NTAS", full_product=True)
    with Dataset(ntas_full, "r+") as ds:
        ds.setncattr("version", "v2")
    set_history(
        ntas_full,
        "Source file: archive/merged_NTAS11_to_NTAS20.nc (v1). "
        "Applied NTAS16 SN 11393 and NTAS19 SN 12247 masks; deduplicated joins "
        "and aligned time and coordinates to the reviewed temperature product.",
    )

    stratus_full = STRATUS_OUTPUT / "stratus_2012_to_2025.nc"
    old_full = STRATUS_OUTPUT / "stratus_2012_to_2023.nc"
    if not stratus_full.exists() and old_full.exists():
        old_full.rename(stratus_full)
    if not stratus_full.exists():
        raise FileNotFoundError(stratus_full)
    apply_stratus_output_masks(stratus_full, temperature_only=False)
    update_metadata(stratus_full, "STRATUS", full_product=True)
    stratus_full_history = (
        "Source file: stratus_2012_to_2025.nc (v1). Applied Stratus 20 SN 10601 "
        "October 2022 mask and Stratus 21 SN 11394 conductivity/salinity mask."
    )
    set_history(stratus_full, stratus_full_history)

    legacy_full = STRATUS_OUTPUT / "merged_stratus12_to_stratus22.nc"
    copyfile(stratus_full, legacy_full)
    update_metadata(legacy_full, "STRATUS", full_product=True)
    set_history(legacy_full, stratus_full_history)

    stratus_temperature = STRATUS_OUTPUT / "stratus_temperature_2012_2025_v3.nc"
    apply_stratus_output_masks(stratus_temperature, temperature_only=True)
    update_metadata(stratus_temperature, "STRATUS", full_product=False)
    stratus_temperature_history = (
        "Source file: stratus_temperature_2012_2025_v3.nc (v1). "
        "Applied Stratus 20 SN 10601 October 2022 temperature mask."
    )
    set_history(stratus_temperature, stratus_temperature_history)

    legacy_temperature = STRATUS_OUTPUT / "stratus_temperature_2012_2023.nc"
    create_stratus_2023_temperature(stratus_temperature, legacy_temperature)
    set_history(legacy_temperature, stratus_temperature_history + " Truncated to 2012-2023 coverage.")

    ntas_products = [ntas_full, ntas_temperature]
    stratus_products = [
        STRATUS_OUTPUT / "OS_STRATUS_20120528-20250318_GRD_TSP30M.nc",
        STRATUS_OUTPUT / "OS_STRATUS_20120528-20250318_GRD_T30M.nc",
    ]
    for source, destination, content, full_product in (
        (stratus_full, stratus_products[0], "TSP", True),
        (stratus_temperature, stratus_products[1], "T", False),
    ):
        copyfile(source, destination)
        update_metadata(destination, "STRATUS", full_product=full_product)
        set_history(
            destination,
            stratus_full_history if full_product else stratus_temperature_history,
        )

    ntas_products.append(create_product(ntas_full, overwrite=True))
    stratus_products.append(create_product(stratus_products[0], overwrite=True))

    ntas_zip = NTAS_OUTPUT / "doi-10.26027-datatltm44.zip"
    stratus_zip = STRATUS_OUTPUT / "doi-10.26027-datakx5cqk.zip"
    write_package(
        ntas_zip,
        ntas_products,
        """NTAS merged gridded temperature and hydrographic products.

Files:
  OS_NTAS_20111125-20221015_GRD_TSP30M.nc  Merged temperature, conductivity, salinity, pressure.
  OS_NTAS_20111125-20221015_GRD_T30M.nc   Temperature-only product.
    OS_NTAS_20111125-20221015_GRD_SP30M.nc  Conductivity, salinity, pressure; temperature removed.

Nominal sampling interval: 30 minutes. Original timestamps are retained; small
approximately one-second timestamp offsets and deployment-transition gaps are
present. The two largest NTAS gaps are approximately 5.6 days and 361.5 days;
no interpolation was applied across gaps. NTAS16 SN 11393 and NTAS19 SN 12247
are blanked from the identified bad periods through the ends of their deployments.
Temperature is quality controlled; conductivity, salinity, and pressure are raw
instrument measurements and retain their documented caveats. Dataset DOI:
https://doi.org/10.26027/DATATLTM44.""",
    )
    write_package(
        stratus_zip,
        stratus_products,
        """Stratus merged gridded temperature and hydrographic products.

Files:
  OS_STRATUS_20120528-20250318_GRD_TSP30M.nc  Merged temperature, conductivity, salinity, pressure.
  OS_STRATUS_20120528-20250318_GRD_T30M.nc   Temperature-only product.
    OS_STRATUS_20120528-20250318_GRD_SP30M.nc  Conductivity, salinity, pressure; temperature removed.

Nominal sampling interval: 30 minutes. Original timestamps are retained; there
are deployment-transition gaps, with the longest approximately 4.4 days. No
interpolation was applied across gaps. Stratus 20 SN 10601 is blanked for
October 2022. Stratus 21 uses SN 11379; SN 11394 conductivity and salinity are
blanked for its deployment. Temperature is quality controlled; conductivity,
salinity, and pressure are raw instrument measurements with documented caveats.
Dataset DOI: https://doi.org/10.26027/DATAKX5CQK.""",
    )
    return [*ntas_products, *stratus_products]


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