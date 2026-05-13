import polars as pl
import pytest
from polars.testing import assert_frame_equal

from fractal_hcs_qc.utils_polars import (
    aggregate_mean_std_sum_first,
    aggregate_mean_sum_first,
    remove_prefix_from_columns,
)


@pytest.fixture
def sample_dataframe() -> pl.DataFrame:
    return pl.DataFrame(
        data={
            "label": [1, 2, 3, 4],  # Int64
            "Nucleus_Intensity_mean_intensity_GFP": [0.5, 1.5, 2.5, 3.5],
            "Nucleus_Intensity_mean_intensity_DAPI": [2.4, 3.4, 4.4, 5.4],
            "Nucleus_Morphology_area": [15.0, 25.0, 35.0, 45.0],
            "well_name": ["A01", "A01", "A01", "A01"],
            "reference_label": [1, 1, 1, 2],
        },
        schema={
            "label": pl.Int64,
            "Nucleus_Intensity_mean_intensity_GFP": pl.Float64,
            "Nucleus_Intensity_mean_intensity_DAPI": pl.Float64,
            "Nucleus_Morphology_area": pl.Float64,
            "well_name": pl.Categorical,
            "reference_label": pl.Int32,
        },
    )


def test_aggregate_mean_sum_first(sample_dataframe: pl.DataFrame):
    result = aggregate_mean_sum_first(
        sample_dataframe, group_columns="reference_label"
    ).sort("reference_label")

    expected = pl.DataFrame(
        data={
            "reference_label": [1, 2],
            "label": [2.0, 4.0],  # mean
            "Nucleus_Intensity_mean_intensity_GFP": [1.5, 3.5],
            "Nucleus_Intensity_mean_intensity_DAPI": [3.4, 5.4],
            "Nucleus_Morphology_area": [75.0, 45.0],  # sum
            "well_name": ["A01", "A01"],  # first
            "count": [3, 1],
        },
        schema={
            "reference_label": pl.Int32,
            "label": pl.Float64,  # mean of Int64 -> Float64
            "Nucleus_Intensity_mean_intensity_GFP": pl.Float64,
            "Nucleus_Intensity_mean_intensity_DAPI": pl.Float64,
            "Nucleus_Morphology_area": pl.Float64,
            "well_name": pl.Categorical,
            "count": pl.UInt32,
        },
    )

    assert_frame_equal(result, expected)


def test_aggregate_mean_std_sum_first(sample_dataframe: pl.DataFrame):
    result = aggregate_mean_std_sum_first(
        sample_dataframe, group_columns="reference_label"
    ).sort("reference_label")

    expected = pl.DataFrame(
        data={
            "reference_label": [1, 2],
            "label": [1, 4],  # first
            "Nucleus_Intensity_mean_intensity_GFP_mean": [1.5, 3.5],
            "Nucleus_Intensity_mean_intensity_DAPI_mean": [3.4, 5.4],
            "Nucleus_Intensity_mean_intensity_GFP_std": [1.0, None],
            "Nucleus_Intensity_mean_intensity_DAPI_std": [1.0, None],
            "Nucleus_Morphology_area_sum": [75.0, 45.0],  # sum
            "well_name": ["A01", "A01"],  # first
            "count": [3, 1],
        },
        schema={
            "reference_label": pl.Int32,
            "label": pl.Int64,
            "Nucleus_Intensity_mean_intensity_GFP_mean": pl.Float64,
            "Nucleus_Intensity_mean_intensity_DAPI_mean": pl.Float64,
            "Nucleus_Intensity_mean_intensity_GFP_std": pl.Float64,
            "Nucleus_Intensity_mean_intensity_DAPI_std": pl.Float64,
            "Nucleus_Morphology_area_sum": pl.Float64,
            "well_name": pl.Categorical,
            "count": pl.UInt32,
        },
    )

    assert_frame_equal(result, expected)


def test_remove_prefix_from_columns(sample_dataframe: pl.DataFrame):
    prefix = "Nucleus_"
    result = remove_prefix_from_columns(sample_dataframe, prefix)

    expected_columns = [
        "label",
        "Intensity_mean_intensity_GFP",
        "Intensity_mean_intensity_DAPI",
        "Morphology_area",
        "well_name",
        "reference_label",
    ]

    assert result.columns == expected_columns


def test_remove_prefix_from_columns_empty_dataframe():
    df = pl.DataFrame(
        schema={
            "label": pl.Int64,
            "Nucleus_Intensity_mean_intensity_GFP": pl.Float64,
            "Nucleus_Intensity_mean_intensity_DAPI": pl.Float64,
            "Nucleus_Morphology_area": pl.Float64,
            "well_name": pl.Categorical,
        },
    )

    prefix = "Nucleus_"
    result = remove_prefix_from_columns(df, prefix)

    expected_columns = [
        "label",
        "Intensity_mean_intensity_GFP",
        "Intensity_mean_intensity_DAPI",
        "Morphology_area",
        "well_name",
    ]

    assert result.columns == expected_columns
