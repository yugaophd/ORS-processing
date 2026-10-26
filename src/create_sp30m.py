"""Create SP30M products by removing temperature from current TSP30M files."""

import argparse
from datetime import datetime, timezone
from pathlib import Path

import netCDF4 as nc
import numpy as np


TEMPERATURE = "sea_water_temperature"
DATA_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SOURCES = (
    DATA_ROOT / "NTAS/merged_NTAS/OS_NTAS_20111125-20221015_GRD_TSP30M.nc",
    DATA_ROOT / "STRATUS/merged_stratus/OS_STRATUS_20120528-20250318_GRD_TSP30M.nc",
)


def validate_product(source_path, output_path):
    with nc.Dataset(source_path) as source, nc.Dataset(output_path) as output:
        assert set(output.variables) == set(source.variables) - {TEMPERATURE}
        assert set(output.dimensions) == set(source.dimensions)
        for name, dimension in source.dimensions.items():
            assert len(output.dimensions[name]) == len(dimension), name
            assert output.dimensions[name].isunlimited() == dimension.isunlimited(), name
        for name, variable in output.variables.items():
            original = source.variables[name]
            original.set_auto_maskandscale(False)
            variable.set_auto_maskandscale(False)
            assert variable.dtype == original.dtype, name
            assert variable.dimensions == original.dimensions, name
            assert set(variable.ncattrs()) == set(original.ncattrs()), name
            for attribute in original.ncattrs():
                np.testing.assert_equal(variable.getncattr(attribute), original.getncattr(attribute))
            np.testing.assert_equal(variable[:], original[:], err_msg=name)


def create_product(source_path, overwrite=False):
    source_path = Path(source_path)
    if not source_path.name.endswith("_TSP30M.nc"):
        raise ValueError(f"Expected a *_TSP30M.nc source: {source_path}")
    output_path = source_path.with_name(source_path.name.replace("_TSP30M.nc", "_SP30M.nc"))
    if output_path.exists() and not overwrite:
        raise FileExistsError(output_path)
    with nc.Dataset(source_path) as source:
        if TEMPERATURE not in source.variables:
            raise ValueError(f"Missing {TEMPERATURE}: {source_path}")
        with nc.Dataset(output_path, "w", format=source.data_model) as output:
            output.setncatts({name: source.getncattr(name) for name in source.ncattrs()})
            for name, dimension in source.dimensions.items():
                output.createDimension(name, None if dimension.isunlimited() else len(dimension))
            for name, variable in source.variables.items():
                if name == TEMPERATURE:
                    continue
                attributes = {key: variable.getncattr(key) for key in variable.ncattrs()}
                options = {}
                if "_FillValue" in attributes:
                    options["fill_value"] = attributes.pop("_FillValue")
                filters = variable.filters() or {}
                for key in ("zlib", "complevel", "shuffle", "fletcher32"):
                    if key in filters:
                        options[key] = filters[key]
                chunks = variable.chunking()
                if isinstance(chunks, list):
                    options["chunksizes"] = chunks
                elif chunks == "contiguous":
                    options["contiguous"] = True
                copied = output.createVariable(name, variable.dtype, variable.dimensions, **options)
                copied.setncatts(attributes)
                variable.set_auto_maskandscale(False)
                copied.set_auto_maskandscale(False)
                copied[:] = variable[:]
            timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            output.summary = str(getattr(source, "summary", "")).replace("temperature, ", "")
            output.history = (
                str(getattr(source, "history", "")).rstrip()
                + f"\n{timestamp}: Created {output_path.name} from {source_path.name} "
                + f"by removing {TEMPERATURE}; all other variables are unchanged."
            )
            for attribute in ("id", "file_name"):
                if attribute in source.ncattrs():
                    output.setncattr(attribute, str(source.getncattr(attribute)).replace("_TSP30M", "_SP30M"))
            output.date_modified = timestamp
    validate_product(source_path, output_path)
    print(f"Validated {output_path}: all non-temperature variables and attributes unchanged.")
    return output_path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sources", nargs="*", type=Path, help="Input *_TSP30M.nc files")
    parser.add_argument("--overwrite", action="store_true", help="Replace existing SP30M products")
    arguments = parser.parse_args()
    for source_path in arguments.sources or DEFAULT_SOURCES:
        create_product(source_path, overwrite=arguments.overwrite)


if __name__ == "__main__":
    main()