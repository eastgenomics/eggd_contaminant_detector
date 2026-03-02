from string import ascii_lowercase
from eggd_contaminant_detector.utils import get_file_id, shorten
from eggd_contaminant_detector.types import DXFileID, DXProjectID, DXLink

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