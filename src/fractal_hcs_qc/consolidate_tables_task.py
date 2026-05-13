"""This is the Python module for consolidate_tables_task."""

from functools import reduce

import polars as pl
import polars.selectors as cs
from loguru import logger
from ngio import open_ome_zarr_container
from ngio.tables import FeatureTable, GenericTable
from pydantic import validate_call

from fractal_hcs_qc.utils_polars import (
    aggregate_mean_std_sum_first,
    aggregate_mean_sum_first,
    merge_feature_columns,
    remove_prefix_from_columns,
    split_feature_names,
)

CHILD_OBJECT_INCLUDE_FEATURES = [
    "area",
    "mean_intensity",
    "max_intensity",
    "min_intensity",
    "count",
]

FEATURE_PREFIXES_TO_REMOVE = [
    "Intensity_",
    "Morphology_",
    "Texture_",
    "Population_",
]


def remove_common_prefixes(
    df: pl.DataFrame | pl.LazyFrame, column_name: str
) -> pl.DataFrame | pl.LazyFrame:
    """Remove common prefixes from feature names in a Polars DataFrame or LazyFrame."""
    expr = reduce(
        lambda acc, prefix: acc.str.strip_prefix(prefix),
        FEATURE_PREFIXES_TO_REMOVE,
        pl.col(column_name),
    )
    return df.with_columns(expr.alias(column_name))


@validate_call
def consolidate_tables_task(
    *,
    # Fractal managed parameters
    zarr_urls: list[str],
    zarr_dir: str,
    # Input parameters
    overlap_label_prefix: str = "Cells_RNA",
    nucleus_table_name: str = "Nucleus_features_apx",
    cytoplasm_table_name: str = "Cytoplasm_features_apx",
    child_object_table_names: list[str] | None = None,
) -> None:
    """Consolidate tables within OME-Zarr containers (of an HCS plate).

    Args:
        zarr_urls (list[str]): URLs to the OME-Zarr containers.
        zarr_dir (str): Directory to store the OME-Zarr containers.
        overlap_label_prefix (str): Prefix for the overlap labels.
            Defaults to "Cells_RNA".
        nucleus_table_name (str): Name of the nucleus table (parent).
            Defaults to "Nucleus_features_apx".
        cytoplasm_table_name (str): Name of the cytoplasm table (parent).
            Defaults to "Cytoplasm_features_apx".
        child_object_table_names (list[str] | None): Names of the child object tables.
            Defaults to None.

    """
    # Loop over all OME-Zarr containers

    for zarr_url in zarr_urls:
        logger.info(f"{zarr_url=}")

        # Open the OME-Zarr container
        ome_zarr_container = open_ome_zarr_container(zarr_url)
        logger.info(f"{ome_zarr_container=}")

        # TODO fail fast if any provided table is not present in the OME-Zarr container

        # load tables and remove column prefixes (e.g. "Nucleus_", "Cytoplasm_")
        nucleus_table = ome_zarr_container.get_feature_table(nucleus_table_name)
        nucleus_table_df = remove_prefix_from_columns(
            nucleus_table.load_as_polars_lf(),
            prefix=nucleus_table.reference_label + "_",
        )
        cytoplasm_table = ome_zarr_container.get_feature_table(cytoplasm_table_name)
        cytoplasm_table_df = remove_prefix_from_columns(
            cytoplasm_table.load_as_polars_lf(),
            prefix=cytoplasm_table.reference_label + "_",
        )

        # globals
        channel_labels = ome_zarr_container.get_image().channel_labels
        overlap_label = overlap_label_prefix + "_label"
        nucleus_label_prefix = nucleus_table.reference_label + "_label"
        cytoplasm_label_prefix = cytoplasm_table.reference_label + "_label"
        # columns_to_merge_on: list[str] = [overlap_label, "well_name"]

        # Aggregate nucleus table to combine nuclei belonging to the same cell
        # (for polynucleated cells)
        # group by Cells_RNA_label (well, plate etc.) --> single-cell, non-poly nuclei
        nucleus_table_df = aggregate_mean_sum_first(
            nucleus_table_df,
            group_columns=overlap_label,
        )

        # rename overlap_label_prefix column to "label", remove previous "label" column
        nucleus_table_df = nucleus_table_df.drop("label").rename(
            {
                overlap_label: "label",
                "count": "nucleus_count",
            }
        )

        # completely unpivot both tables
        # id columns: label, well_name, ROI
        # all numeric features: feature_name, value
        nucleus_table_df = nucleus_table_df.with_columns(
            pl.lit("nucleus").alias("compartment")
        ).unpivot(
            on=cs.numeric() - cs.by_name("label"),  # exclude "label"
            index=["label", "well_name", "compartment"],
        )

        cytoplasm_table_df = cytoplasm_table_df.with_columns(
            pl.lit("cytoplasm").alias("compartment")
        ).unpivot(
            on=cs.numeric() - cs.by_name("label"),  # exclude "label"
            index=["label", "well_name", "compartment"],
        )

        if nucleus_table_df.limit(1).collect().is_empty():
            consolidated_df = cytoplasm_table_df
        else:
            consolidated_df = pl.concat(
                [nucleus_table_df, cytoplasm_table_df],
            )

        consolidated_df = remove_common_prefixes(
            consolidated_df,
            column_name="variable",
        )

        # TODO filter out unwanted feature names

        # Add child object tables to consolidated/concatenated table
        #   (on "Cells_RNA_label" AND compartment (Nucleus_label, Cytoplasm_label)))
        # 1 entry per compartment and existing channel
        if child_object_table_names is not None:
            for object_table_name in child_object_table_names:
                if object_table_name is not None:
                    object_table = ome_zarr_container.get_feature_table(
                        object_table_name
                    )

                    object_table_df = remove_prefix_from_columns(
                        object_table.load_as_polars_lf(),
                        prefix=object_table.reference_label + "_",
                    )

                    # skip if empty object table
                    if object_table_df.lazy().limit(1).collect().is_empty():
                        logger.warning(
                            f"Object table {object_table_name} is empty. Skipping."
                        )
                        continue

                    # add compartment=nucleus where nucleus_label is not null
                    # add compartment=cytoplasm where cytoplasm_label is not null
                    object_table_df = object_table_df.with_columns(
                        pl.when(pl.col(nucleus_label_prefix).is_not_null())
                        .then(pl.lit("nucleus"))
                        .when(pl.col(cytoplasm_label_prefix).is_not_null())
                        .then(pl.lit("cytoplasm"))
                        .otherwise(pl.lit(None))
                        .alias("compartment")
                    )

                    object_table_df = aggregate_mean_std_sum_first(
                        object_table_df,
                        group_columns=[overlap_label, "compartment"],
                    )

                    # rename overlap_label_prefix column to "label", remove previous
                    object_table_df = object_table_df.drop("label").rename(
                        {
                            overlap_label: "label",
                        }
                    )

                    # unpivot object table
                    object_table_df = object_table_df.unpivot(
                        on=cs.numeric() - cs.by_name("label"),
                        index=["label", "well_name", "compartment"],
                    )

                    object_table_df = remove_common_prefixes(
                        object_table_df,
                        column_name="variable",
                    )

                    # filter to include only feature names starting
                    #   with labels in CHILD_OBJECT_INCLUDE_FEATURES list
                    object_table_df = object_table_df.filter(
                        cs.by_name("variable").str.contains(
                            f"^({'|'.join(CHILD_OBJECT_INCLUDE_FEATURES)})"
                        )
                    )

                    # prefix variable with reference_label
                    object_table_df = object_table_df.with_columns(
                        (
                            pl.lit(object_table.reference_label + "_")
                            + (pl.col("variable"))
                        ).alias("variable")
                    )

                    # concatenate vertically with consolidated_df
                    consolidated_df = pl.concat([consolidated_df, object_table_df])

        # split feature_name into feature and channel
        consolidated_df = split_feature_names(
            consolidated_df,
            feature_name_column="variable",
            channel_names=channel_labels,
        )

        # # write consolidated table back to OME-Zarr container
        ome_zarr_container.add_table(
            name="consolidated_table",
            table=GenericTable(consolidated_df),
            backend="csv",
        )

        for channel in channel_labels:
            # keep non-channel-specific features, and features for current channel
            channel_df = consolidated_df.filter(
                (pl.col("channel").is_null()) | (pl.col("channel") == channel)
            ).drop("channel")

            # suffix 'stat' onto  'feature' if stat is not null
            channel_df = merge_feature_columns(
                channel_df,
                compartment_column_name="compartment",
                feature_column_name="feature",
                statistic_column_name="stat",
            )

            # pivot by compartment, feature, stat (and keep label, well_name)
            channel_df = channel_df.collect().pivot(
                "feature",
                values="value",
                index=["label", "well_name"],
            )

            # write channel-specific table back to OME-Zarr container
            ome_zarr_container.add_table(
                name=f"{channel}_features_consolidated",
                table=FeatureTable(
                    channel_df, reference_label=cytoplasm_table.reference_label
                ),
                backend="csv",
            )

    logger.info("Table consolidation complete.")


if __name__ == "__main__":
    from fractal_task_tools.task_wrapper import run_fractal_task

    run_fractal_task(task_function=consolidate_tables_task)
