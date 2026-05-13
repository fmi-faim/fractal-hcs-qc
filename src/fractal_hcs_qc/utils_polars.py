"""Common utils for manipulating Polars dataframes."""

import polars as pl
import polars.selectors as cs


def aggregate_mean_sum_first(
    df: pl.DataFrame | pl.LazyFrame,
    group_columns: str | list[str],
) -> pl.DataFrame | pl.LazyFrame:
    """Aggregate input dataframe.

    Numeric columns are aggregated by 'mean',
    or, if they end on '_sum' or '_area', by 'sum'.
    Categorical and String columns are aggregated by 'first'.

    If df has null dtype columns, the (likely empty) input dataframe is returned.
    """
    if any(dtype == pl.Null for dtype in df.lazy().collect_schema().dtypes()):
        print(
            """Warning: DataFrame contains null dtype columns.
            Returning input DataFrame without aggregation."""
        )
        return df.with_columns(
            pl.lit(None).alias("count")
        )  # add count column for consistency, filled with None

    sum_cols = cs.numeric() & cs.ends_with("_area", "_sum")
    mean_cols = cs.numeric() & ~cs.ends_with("_area", "_sum")
    cat_cols = cs.categorical() | cs.string()

    # Exclude the group column(s) from all selectors
    exclude_cols = cs.by_name(group_columns)

    # Add group size as "count" column
    aggregation_expressions = [
        (mean_cols & ~exclude_cols).mean(),
        (sum_cols & ~exclude_cols).sum(),
        (cat_cols & ~exclude_cols).first(),
        pl.len().alias("count"),
    ]

    return df.group_by(group_columns).agg(aggregation_expressions)


def aggregate_mean_std_sum_first(
    df: pl.DataFrame | pl.LazyFrame,
    group_columns: str | list[str],
) -> pl.DataFrame | pl.LazyFrame:
    """Aggregate input dataframe.

    Numeric columns are aggregated by 'mean' and 'std',
    or, if they end on '_sum' or '_area', by 'sum'.
    Categorical and String columns are aggregated by 'first'.


    """
    sum_cols = cs.numeric() & cs.ends_with("_area", "_sum")
    mean_cols = cs.numeric() & ~cs.ends_with("_area", "_sum")
    cat_cols = cs.categorical() | cs.string()

    # Exclude the group column(s) from all selectors
    exclude_cols = cs.by_name(group_columns) | cs.by_name("label")

    # Add group size as "count" column
    aggregation_expressions = [
        pl.col("label").first(),
        (mean_cols & ~exclude_cols).mean().name.suffix("_mean"),
        (mean_cols & ~exclude_cols).std().name.suffix("_std"),
        (sum_cols & ~exclude_cols).sum().name.suffix("_sum"),
        (cat_cols & ~exclude_cols).first(),
        pl.len().alias("count"),
    ]

    return df.group_by(group_columns).agg(aggregation_expressions)


def remove_prefix_from_columns(
    df: pl.DataFrame | pl.LazyFrame, prefix: str
) -> pl.DataFrame | pl.LazyFrame:
    """Remove prefix from column names in a Polars DataFrame or LazyFrame."""
    return df.rename(
        {col: col.removeprefix(prefix) for col in df.collect_schema().names()}
    )
