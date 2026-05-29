# fractal-hcs-qc

A **Fractal task** for consolidating measurement tables from High-Content Screening (HCS) plate experiments stored in OME-Zarr format.

## Overview

**fractal-hcs-qc** consolidates multiple measurement tables into unified, streamlined outputs that are easier to work with for downstream analysis and quality control.
It aggregates measurements across cell compartments, filters to relevant features, and produces both long-format (unpivoted) and wide-format (pivoted) outputs organized by channel.

## Installation

### For Fractal Users/Administrators

Build the wheel locally:
```bash
pixi run -e dev hatch build
```

Then register the task by uploading the .whl file in the Fractal web UI:


### For Development & Contributing

If you want to modify or extend this package:

1. **Clone the repository**:
   ```bash
   git clone https://github.com/fmi-faim/fractal-hcs-qc
   cd fractal-hcs-qc
   ```

2. **Install with Pixi** (recommended for reproducible development environments):
   ```bash
   pixi install -e dev
   pixi run install-pre-commit
   ```

   If you don't have Pixi, install it first from https://pixi.sh/.

3. **Run tests and linting** to verify your setup:
   ```bash
   pixi run test
   pixi run format-code
   ```

## How It Works

### Input

The task expects OME-Zarr containers (typically from an HCS plate) containing measurement tables in the following structure:

- **Parent tables** (usually one per compartment):
  - Nucleus measurements (e.g., `Nucleus_features_apx`)
  - Cytoplasm measurements (e.g., `Cytoplasm_features_apx`)
- **Child object tables** (optional):
  - Measurements for objects detected within compartments (e.g., RNA spots, vesicles)
  - Automatically associated with parent compartments

### Processing Steps

1. **Aggregation**: Nuclei belonging to the same cell (polynucleated cells) are aggregated by taking mean, sum, or first values as appropriate for each measurement type.

2. **Consolidation**: Nucleus and cytoplasm tables are combined into a single table with a "compartment" label, and child object measurements are added with appropriate filtering.

3. **Feature normalization**: Common measurement prefixes are removed (e.g., `Intensity_`, `Morphology_`) to standardize feature names across tables.

4. **Feature decomposition**: Measurement names are parsed to extract feature, channel, and statistic components.

5. **Output generation**:
   - **Consolidated table**: All features, compartments, and channels in long format for downstream processing
   - **Channel-specific tables**: Per-channel pivoted tables organized by compartment and feature, ready for analysis

### Output

For each input OME-Zarr container, the task produces:

- **`consolidated_table`** (`GenericTable`): A single unified table in long format containing all measurements, useful for filtering and custom analyses
- **`{channel}_features_consolidated`** (`FeatureTable`): One pivoted table per imaging channel, indexed by cell label and well name, with columns for each compartment-feature pair

All output tables are stored back into the OME-Zarr container in CSV format.

## Development

### Project Structure

- **`src/fractal_hcs_qc/`**: Main package
  - `consolidate_tables_task.py`: The Fractal task implementation
  - `utils_polars.py`: Reusable dataframe manipulation utilities
  - `dev/task_list.py`: Task metadata and Fractal manifest configuration

- **`tests/`**: Test suite
  - `test_consolidate_tables_task.py`: Main task tests
  - `test_utils_polars.py`: Utility function tests
  - `test_valid_manifest.py`: Manifest validation

### Common Development Tasks

- **Run all tests with coverage**:
  ```bash
  pixi run test
  ```

- **Run a specific test**:
  ```bash
  pixi run test -- tests/test_utils_polars.py::test_split_feature_names -v
  ```

- **Format code and imports**:
  ```bash
  pixi run format-code
  pixi run format-imports
  ```

- **Update the Fractal manifest** after task changes:
  ```bash
  pixi run create-manifest
  ```

### Code Quality

This project uses:

- **Ruff** for linting and code formatting (enforces PEP 8, type hints, Google-style docstrings)
- **Pre-commit** hooks to catch issues before commits
- **pytest** with coverage reporting for automated testing

For detailed information on architecture, conventions, and troubleshooting, see [`.github/copilot-instructions.md`](.github/copilot-instructions.md).

### Contributing

We welcome contributions! To contribute:

1. Fork the repository
2. Create a feature branch
3. Make your changes (ensure all tests pass and code is formatted)
4. Submit a pull request

Please ensure your code follows the project conventions and includes tests for new functionality.

## References

- **Fractal**: https://fractal-analytics-platform.github.io/

## License

This project is licensed under the **BSD-3-Clause License**. See [LICENSE](LICENSE) for details.

## Authors

- Jan Eglinger (FMI)
- Niklas Khoss (FMI)
