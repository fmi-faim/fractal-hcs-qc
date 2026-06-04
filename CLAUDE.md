# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**fractal-hcs-qc** is a Fractal task package that consolidates measurement tables in High-Content Screening (HCS) plate zarrs. It reads feature tables from nucleus, cytoplasm, and child object segmentations in OME-Zarr containers, aggregates measurements by cell ID, and produces consolidated feature tables split by imaging channel.

**Key Technologies:**
- Polars for data manipulation
- NGIO for OME-Zarr I/O
- Fractal Task Tools for task integration
- Python 3.11+

## Build & Development Setup

### Initial Setup
```bash
pixi install --with dev
pixi run init-tasks
```

This installs dependencies, pre-commit hooks, formats code, and validates the Fractal manifest in one go.

### Common Commands

**Format code:**
```bash
pixi run -e dev format-code     # ruff format
pixi run -e dev format-imports  # ruff check with isort
```

**Linting/validation:**
- Pre-commit runs automatically on commit (ruff lint and pyproject validation)
- Manual validation: `pre-commit run --all-files`
- Fractal manifest: `pixi run -e dev create-manifest` (re-validates schema)

**Testing:**
```bash
pixi run -e dev test                              # Full suite with coverage report
pytest tests/test_consolidate_tables_task.py      # Single test file
pytest tests/test_utils_polars.py::test_aggregate_mean_sum_first  # Single test
pytest --cov=src --cov-report=html                # HTML coverage report
```

**Run the task (for debugging):**
```bash
python src/fractal_hcs_qc/consolidate_tables_task.py
```

## Architecture

### Core Components

**1. Main Task: `consolidate_tables_task()`** (`consolidate_tables_task.py`)
- Entry point for the Fractal task framework
- Iterates over zarr_urls (one per well)
- Orchestrates the consolidation pipeline:
  - Load nucleus & cytoplasm feature tables
  - Aggregate measurements (mean/sum/first by cell ID)
  - Unpivot to long format (one row per feature per cell)
  - Add child object measurements (e.g., RNA speckles) with compartment assignment
  - Split feature names into {feature, channel, statistic}
  - Output consolidated table (all channels merged) + channel-specific tables

**2. Utility Functions: `utils_polars.py`**
- `aggregate_mean_sum_first()`: Group measurements by cell ID; numeric features → mean (or sum if ending in `_area`/`_sum`), categorical → first value
- `aggregate_mean_std_sum_first()`: Like above but also computes std deviation
- `remove_prefix_from_columns()`: Strip reference label prefix (e.g., "Nucleus_") from column names
- `split_feature_names()`: Parse feature names into {feature, channel, statistic} components using regex
- `merge_feature_columns()`: Reconstruct feature names from separated components

**3. Task Registration: `dev/task_list.py`**
- Defines metadata (CPU, memory, task name, category) for Fractal scheduler
- Uses `fractal-manifest create` to generate `__FRACTAL_MANIFEST__.json`

### Data Flow

1. **Input**: OME-Zarr container per well with feature tables (CSV-backed)
2. **Load & Clean**: Remove reference label prefixes; nucleus/cytoplasm tables indexed by cell ID
3. **Aggregate**: Combine measurements per cell (handles polynucleated cells by grouping on overlap label)
4. **Unpivot**: Convert wide feature format to long format
5. **Merge**: Combine nucleus + cytoplasm rows; append child object measurements
6. **Split**: Parse feature names into structured columns
7. **Output**: 
   - `consolidated_table` (all channels, CSV)
   - `{channel}_features_consolidated` for each channel (FeatureTable, CSV)

### Key Design Patterns

**Feature Name Parsing:**
Feature names follow a pattern: `{feature_type}_{channel}_{statistic}`
- Example: `mean_intensity_GFP_mean` → {feature: `mean_intensity`, channel: `GFP`, stat: `mean`}
- Channel extraction uses dynamic regex built from image channel labels
- Only features matching CHILD_OBJECT_INCLUDE_FEATURES are retained from child objects (area, mean_intensity, max_intensity, min_intensity, count)

**Prefix Removal:**
Common prefixes (`Intensity_`, `Morphology_`, `Texture_`, `Population_`) are stripped before consolidation to simplify feature names.

**Lazy Evaluation:**
Most operations use Polars LazyFrame to defer computation; `.collect()` called only when needed.

## Testing

**Test Structure:**
- `test_consolidate_tables_task.py`: End-to-end integration test with synthetic OME-Zarr plate fixture (4 wells, 2 channels, multiple feature tables)
- `test_utils_polars.py`: Unit tests for individual utility functions with sample DataFrames
- `test_valid_manifest.py`: JSON schema validation against Fractal manifest spec

**Test Data:**
- `tests/resources/`: CSV files for nucleus, cytoplasm, speckle features (well C03, C04, D03, D04)
- Fixture `plate_dataset()` creates temporary OME-Zarr structure on each test run

**Running Tests:**
- First install dev environment: `pixi install --with dev`
- `pixi run -e dev test` includes coverage report (shows coverage gaps)

## Configuration & Files

**pyproject.toml:**
- Package metadata, Python version constraints (3.11–3.14)
- Ruff config (88-char line length, Google docstring style, strict linting)
- Pixi config (conda-forge channels, workspace with dev/jupyter environments)
- Hatch build backend with VCS versioning

**pixi.toml:** Not a separate file; all Pixi config is in pyproject.toml

**Pre-commit:** Ruff (lint + format) + pyproject validation on every commit

**CI/CD (.github/workflows/build_and_test.yml):**
- Runs on push/PR/tags (Ubuntu 22.04, macOS)
- Tests on Python 3.11, 3.12, 3.13
- Validates manifest schema
- Deploys to PyPI on tag (currently disabled with `if: false`)

## Common Pitfalls & Notes

1. **Empty Tables**: Functions check for Null dtype (empty DataFrames) and return early with None counts to avoid aggregation errors.

2. **Polars LazyFrame vs DataFrame**: Most internal functions work with both; use `.collect()` explicitly when needed (e.g., before pivot operations).

3. **Compartment Assignment**: Child object tables are linked to nucleus/cytoplasm via label prefixes (e.g., `Nucleus_label`, `Cytoplasm_label`).

4. **Channel Filtering**: After splitting features, tables are filtered by channel; non-channel-specific features are preserved in all channel tables.

5. **Manifest Regeneration**: If task metadata changes (in `task_list.py`), run `pixi run -e dev create-manifest` before committing; this updates `__FRACTAL_MANIFEST__.json`.

## Dependencies

**Core:**
- `fractal-task-tools>=0.4.0`: Fractal task framework
- `ngio>=0.5.7`: OME-Zarr I/O
- `loguru>=0.7.3`: Logging
- `polars`: Data manipulation (imported in utils_polars.py)

**Dev:**
- `pytest`, `pytest-cov`: Testing
- `ruff`: Linting & formatting
- `pre-commit`: Git hooks
- `hatch`: Build system

See `pyproject.toml` for complete dependency tree and version constraints.

## Authors

Jan Eglinger (jan.eglinger@fmi.ch), Niklas Khoss (niklas.khoss@fmi.ch) — FMI Basel

Licensed under BSD 3-Clause.
