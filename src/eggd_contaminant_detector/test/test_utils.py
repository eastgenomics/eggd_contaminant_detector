import pytest
import pandas as pd
from pathlib import Path
from string import ascii_lowercase, ascii_uppercase
from eggd_contaminant_detector.utils import get_file_id, read_csvs, shorten
from eggd_contaminant_detector.types import DXFileID, DXProjectID, DXLink

@pytest.fixture
def csv_dfs() -> dict[str, pd.DataFrame]:
    return {
        "A": pd.DataFrame({"id": [0], "value": ["A"]}),
        "B": pd.DataFrame({"id": [0], "value": ["B"]}),
        "C": pd.DataFrame({"id": [0], "value": ["C"]}),
    }

@pytest.fixture()
def flat_csv_dir(csv_dfs: list[pd.DataFrame], tmp_path: Path) -> Path:
    d = tmp_path / "data"
    d.mkdir(parents=True, exist_ok=True)
    for key in csv_dfs:
        csv_dfs[key].to_csv(d / f"{key}.csv", index=False)
    return d

@pytest.fixture()
def nested_csv_dir(csv_dfs: list[pd.DataFrame], tmp_path: Path) -> Path:
    d = tmp_path / "subdir" / "data"
    d.mkdir(parents=True, exist_ok=True)
    for key in csv_dfs:
        csv_dfs[key].to_csv(d / f"{key}.csv", index=False)
    return d

def test_get_file_id() -> None:
    file_id: DXFileID = f"file-{ascii_lowercase}"
    project_id: DXProjectID = f"project-{ascii_lowercase}"
    flat_link: DXLink = {"$dnanexus_link": file_id}
    nested_link: DXLink = {"$dnanexus_link": {"id": file_id, "project": project_id}}

    flat_test = get_file_id(flat_link)
    nested_test = get_file_id(nested_link)
    assert flat_test == file_id
    assert nested_test == file_id

def test_shorten() -> None:
    epic_name = "123456789-26001Z0001-26NGSHO01-1234-U-98765432"
    epic_name_shortened = "26001Z0001-26NGSHO01"
    non_epic_name = "haemonc_sim_HCC1187"

    assert shorten(epic_name) == epic_name_shortened
    assert shorten(non_epic_name) == non_epic_name

def test_read_csvs_concatenates_correctly(flat_csv_dir: Path) -> None:
    result = read_csvs(flat_csv_dir, "*.csv")
    
    assert len(result) == 3
    assert set(result["value"]) == {"A", "B", "C"}
    assert isinstance(result, pd.DataFrame)

def test_read_csvs_concatenates_data_correctly(nested_csv_dir: Path) -> None:
    result = read_csvs(nested_csv_dir, "**/*.csv")
    
    assert len(result) == 3
    assert set(result["value"]) == {"A", "B", "C"}
    assert isinstance(result, pd.DataFrame)

def test_read_csvs_with_no_matches(flat_csv_dir: Path) -> None:
    with pytest.raises(ValueError, match="No objects to concatenate"):
        read_csvs(flat_csv_dir, "*.xlsx")