from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from ngio import (
    OmeZarrContainer,
    OmeZarrPlate,
    create_empty_plate,
    create_ome_zarr_from_array,
    open_ome_zarr_container,
    open_ome_zarr_plate,
)
from ngio.tables import FeatureTable

from fractal_hcs_qc.consolidate_tables_task import (
    consolidate_tables_task,
)

NGFF_VERSION = "0.5"


def get_label_array(
    shape: tuple[int, int],
    labeled_regions: list[tuple[int, int, int, int]],
) -> np.ndarray:
    """Generate a label image array with distinct labels."""
    label_array = np.zeros(shape, dtype=np.uint16)
    for i, (x_start, x_end, y_start, y_end) in enumerate(labeled_regions, start=1):
        label_array[y_start:y_end, x_start:x_end] = i
    return label_array


def generate_feature_table(
    label_values: list[int],
    feature_columns: list[str],
    well_name: str,
    reference_label_column: str | None = None,
) -> FeatureTable:
    """Generate a feature table with specified values."""
    num_rows = len(label_values)
    if num_rows == 0:
        # Return an empty table with the correct columns
        columns = ["label", "well_name", *feature_columns]
        if reference_label_column is not None:
            columns.append(reference_label_column)
        return FeatureTable(
            table_data=pd.DataFrame(columns=columns), reference_label="object"
        )
    data = {
        "label": np.arange(1, num_rows + 1),
        "well_name": [well_name] * num_rows,
    }
    # put random values for features
    for feature in feature_columns:
        data[feature] = np.random.rand(num_rows) * 100
    if reference_label_column is not None:
        data[reference_label_column] = data["label"] + 100
    return FeatureTable(table_data=pd.DataFrame(data), reference_label="object")


def load_feature_table(
    well_name: str,
    table_name: str,
    reference_label: str,
) -> FeatureTable:
    """Helper function to generate a FeatureTable from a csv in data/resources."""
    table_path = Path("tests/resources") / f"{well_name}_{table_name}.csv"
    return FeatureTable(
        table_data=pd.read_csv(table_path), reference_label=reference_label
    )


@pytest.fixture
def tmp_plate_zarr_path(tmp_path: Path) -> Path:
    """Fixture to create a temporary path for the OME-Zarr plate."""
    return tmp_path / "test_plate.zarr"


@pytest.fixture
def plate_dataset(tmp_plate_zarr_path: Path) -> OmeZarrPlate:
    """Fixture to create a synthetic OME-Zarr HCS plate dataset for testing."""
    rows = ["C", "D"]
    columns = ["3", "4"]
    common_shape = (2, 64, 64)  # (C, Y, X)
    levels = ["s0"]
    plate = create_empty_plate(
        store=tmp_plate_zarr_path,
        name="Test Plate",
        ngff_version=NGFF_VERSION,
        overwrite=True,
    )

    # add images to plate and keep well paths
    well_paths = []
    for row in rows:
        for column in columns:
            well_paths.append(
                plate.add_image(
                    row=row,
                    column=column,
                    image_path="fov0",
                )
            )

    well_containers: list[OmeZarrContainer] = []
    # random uint8 data for each well
    # set seed
    np.random.seed(42)
    for well_path in well_paths:
        image_array = np.random.randint(0, 256, size=common_shape, dtype=np.uint8)
        well_containers.append(
            create_ome_zarr_from_array(
                store=tmp_plate_zarr_path / well_path,
                array=image_array,
                axes_names="cyx",
                channels_meta=[
                    "RNA",
                    "DNA",
                ],
                levels=levels,
                pixelsize=0.5,
                ngff_version=NGFF_VERSION,
                overwrite=True,
            )
        )

    # create distinct label images for each well
    label_image_C03 = well_containers[0].derive_label(
        "object", ngff_version=NGFF_VERSION
    )
    label_image_C03.set_array(
        get_label_array((64, 64), [(32, 48, 8, 24), (8, 16, 48, 56)])
    )
    label_image_C04 = well_containers[1].derive_label(
        "object", ngff_version=NGFF_VERSION
    )
    label_image_C04.set_array(get_label_array((64, 64), []))
    label_image_D03 = well_containers[2].derive_label(
        "object", ngff_version=NGFF_VERSION
    )
    label_image_D03.set_array(get_label_array((64, 64), [(0, 64, 0, 64)]))
    label_image_D04 = well_containers[3].derive_label(
        "object", ngff_version=NGFF_VERSION
    )
    label_image_D04.set_array(get_label_array((64, 64), [(16, 48, 16, 48)]))

    # add tables to each well

    well_containers[0].add_table(
        name="Nucleus_features_apx",
        table=load_feature_table("C03", "Nucleus_features_apx", "Nucleus_cellpose"),
        backend="csv",
    )
    well_containers[0].add_table(
        name="Cytoplasm_features_apx",
        table=load_feature_table("C03", "Cytoplasm_features_apx", "Cytoplasm"),
        backend="csv",
    )
    well_containers[0].add_table(
        name="Speckle_features_apx",
        table=load_feature_table("C03", "Speckle_features_apx", "RNA_Speckles"),
        backend="csv",
    )

    well_containers[1].add_table(
        name="Nucleus_features_apx",
        table=load_feature_table("C04", "Nucleus_features_apx", "Nucleus_cellpose"),
        backend="csv",
    )
    well_containers[1].add_table(
        name="Cytoplasm_features_apx",
        table=load_feature_table("C04", "Cytoplasm_features_apx", "Cytoplasm"),
        backend="csv",
    )
    well_containers[1].add_table(
        name="Speckle_features_apx",
        table=load_feature_table("C04", "Speckle_features_apx", "RNA_Speckles"),
        backend="csv",
    )

    well_containers[2].add_table(
        name="Nucleus_features_apx",
        table=load_feature_table("D03", "Nucleus_features_apx", "Nucleus_cellpose"),
        backend="csv",
    )
    well_containers[2].add_table(
        name="Cytoplasm_features_apx",
        table=load_feature_table("D03", "Cytoplasm_features_apx", "Cytoplasm"),
        backend="csv",
    )
    well_containers[2].add_table(
        name="Speckle_features_apx",
        table=load_feature_table("D03", "Speckle_features_apx", "RNA_Speckles"),
        backend="csv",
    )

    well_containers[3].add_table(
        name="Nucleus_features_apx",
        table=load_feature_table("D04", "Nucleus_features_apx", "Nucleus_cellpose"),
        backend="csv",
    )
    well_containers[3].add_table(
        name="Cytoplasm_features_apx",
        table=load_feature_table("D04", "Cytoplasm_features_apx", "Cytoplasm"),
        backend="csv",
    )
    well_containers[3].add_table(
        name="Speckle_features_apx",
        table=load_feature_table("D04", "Speckle_features_apx", "RNA_Speckles"),
        backend="csv",
    )

    return plate


@pytest.fixture
def empty_well_plate(tmp_path: Path) -> tuple[OmeZarrPlate, Path]:
    """Plate with one empty well (no objects) and one normal well."""
    store = tmp_path / "empty_well_plate.zarr"
    plate = create_empty_plate(
        store=store,
        name="Empty Well Test Plate",
        ngff_version=NGFF_VERSION,
        overwrite=True,
    )
    common_shape = (2, 64, 64)
    np.random.seed(0)

    for row, col in [("A", "1"), ("A", "2")]:
        well_path = plate.add_image(row=row, column=col, image_path="fov0")
        container = create_ome_zarr_from_array(
            store=store / well_path,
            array=np.random.randint(0, 256, size=common_shape, dtype=np.uint8),
            axes_names="cyx",
            channels_meta=["RNA", "DNA"],
            levels=["s0"],
            pixelsize=0.5,
            ngff_version=NGFF_VERSION,
            overwrite=True,
        )
        is_empty = col == "1"
        n = 0 if is_empty else 2
        well_name = f"{row}{col}"
        nucleus_data = pd.DataFrame({
            "label": np.arange(1, n + 1),
            "well_name": [well_name] * n,
            "Nucleus_cellpose_Intensity_mean_intensity_RNA_mean": np.random.rand(n),
            "Cells_RNA_label": np.arange(101, n + 101),
        })
        cytoplasm_data = pd.DataFrame({
            "label": np.arange(1, n + 1),
            "well_name": [well_name] * n,
            "Cytoplasm_Intensity_mean_intensity_RNA_mean": np.random.rand(n),
            "Cells_RNA_label": np.arange(101, n + 101),
        })
        container.add_table(
            name="Nucleus_features_apx",
            table=FeatureTable(nucleus_data, reference_label="Nucleus_cellpose"),
            backend="csv",
        )
        container.add_table(
            name="Cytoplasm_features_apx",
            table=FeatureTable(cytoplasm_data, reference_label="Cytoplasm"),
            backend="csv",
        )

    return plate, store


def test_empty_well_is_skipped(empty_well_plate: tuple[OmeZarrPlate, Path]):
    """Empty wells (no objects) must be skipped without error; normal wells must succeed."""
    plate, store = empty_well_plate
    well_paths = [
        (store / p).as_posix() for p in plate.images_paths()
    ]

    consolidate_tables_task(
        zarr_urls=well_paths,
        zarr_dir="",
        overlap_label_prefix="Cells_RNA",
        nucleus_table_name="Nucleus_features_apx",
        cytoplasm_table_name="Cytoplasm_features_apx",
    )

    empty_well = open_ome_zarr_container(well_paths[0])
    assert "consolidated_table" not in empty_well.tables_container.list(), (
        "Empty well should have no output tables written"
    )

    normal_well = open_ome_zarr_container(well_paths[1])
    assert "consolidated_table" in normal_well.tables_container.list(), (
        "Normal well should have consolidated_table written"
    )


def test_ngio_open_plate_dataset_fixture(
    plate_dataset: OmeZarrPlate, tmp_plate_zarr_path: Path
):
    """Test that the plate dataset fixture can be opened and contains expected data."""
    # Open the plate dataset
    opened_plate = open_ome_zarr_plate(tmp_plate_zarr_path)
    assert isinstance(opened_plate, OmeZarrPlate), (
        "Opened object is not an OmeZarrPlate."
    )


def test_plate_dataset_fixture(plate_dataset: OmeZarrPlate):
    """Base test for the table consolidation task."""
    image_dict = plate_dataset.get_images()
    assert len(image_dict) == 4, "Expected 4 images in the plate dataset."

    # assert that all dict keys are present
    assert list(image_dict.keys()) == [
        "C/03/fov0",
        "C/04/fov0",
        "D/03/fov0",
        "D/04/fov0",
    ]

    # assert that C/03 has one label image containing two distinct label values.
    c_03_image = image_dict["C/03/fov0"]
    assert c_03_image.get_label("object").shape == (64, 64)
    # distinct label values should be 0, 1, and 2 (background and two objects)
    assert set(np.unique(c_03_image.get_label("object").get_array())) == {0, 1, 2}

    c_04_image = image_dict["C/04/fov0"]
    assert c_04_image.get_label("object").shape == (64, 64)
    # distinct label values should be 0 (background only)
    assert set(np.unique(c_04_image.get_label("object").get_array())) == {0}

    d_03_image = image_dict["D/03/fov0"]
    assert d_03_image.get_label("object").shape == (64, 64)
    # distinct label values should be 1 (full image object)
    assert set(np.unique(d_03_image.get_label("object").get_array())) == {1}

    d_04_image = image_dict["D/04/fov0"]
    assert d_04_image.get_label("object").shape == (64, 64)
    # distinct label values should be 0 and 1 (background and one object)
    assert set(np.unique(d_04_image.get_label("object").get_array())) == {0, 1}


def test_consolidate_tables_task(
    plate_dataset: OmeZarrPlate, tmp_plate_zarr_path: Path
):
    # Generate list of strings for wells
    well_path_list = [
        (tmp_plate_zarr_path / well_path).as_posix()
        for well_path in plate_dataset.images_paths()
    ]

    consolidate_tables_task(
        zarr_urls=well_path_list,
        zarr_dir="",
        overlap_label_prefix="Cells_RNA",
        nucleus_table_name="Nucleus_features_apx",
        cytoplasm_table_name="Cytoplasm_features_apx",
        child_object_table_names=["Speckle_features_apx"],
    )

    # C/03/fov0: non-empty well — assert tables were written with content
    c03 = open_ome_zarr_container(well_path_list[0])
    assert c03.get_table("consolidated_table") is not None

    rna_df = (
        c03.get_feature_table("RNA_features_consolidated").load_as_polars_lf().collect()
    )
    assert len(rna_df) > 0
    assert "label" in rna_df.columns
    assert "well_name" in rna_df.columns

    dna_df = (
        c03.get_feature_table("DNA_features_consolidated").load_as_polars_lf().collect()
    )
    assert len(dna_df) > 0

    # C/04/fov0: empty well — task must not crash, no output tables written
    c04 = open_ome_zarr_container(well_path_list[1])
    assert "consolidated_table" not in c04.tables_container.list()
    assert "RNA_features_consolidated" not in c04.tables_container.list()
