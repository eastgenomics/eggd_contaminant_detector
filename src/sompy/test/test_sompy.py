import pytest
import pandas as pd
from pathlib import Path
from unittest.mock import MagicMock, patch
from sompy.sompy import run, parse_samples, remove_vcf_extension

@pytest.mark.parametrize("filename, expected", [
    ("HG002.vcf.gz", "HG002"),
    ("sample.g.vcf", "sample"),
    ("clinical_id.gvcf.gz", "clinical_id"),
    ("path/to/my_file.vcf", "my_file"),
])
def test_remove_vcf_extension(filename: str, expected: str) -> None:
    assert remove_vcf_extension(filename) == expected

def test_parse_samples() -> None:
    data = {"sompycmd": ["som.py -o out/S1_S2 --ref r.fa truth.vcf query.vcf"]}
    df = pd.DataFrame(data)
    result = parse_samples(df)
    assert result["truth"].iloc[0] == "truth"
    assert result["query"].iloc[0] == "query"

@patch("sompy.sompy.docker_utils")
def test_run_sompy_success(mock_utils: MagicMock, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Tests that run_image_from_archive is called by run_sompy"""
    # Setup: Redirect working directory to sandbox
    monkeypatch.chdir(tmp_path)
    
    # Create input files in sandbox
    truth = tmp_path / "truth_set.vcf"
    query = tmp_path / "query_set.vcf"
    ref = tmp_path / "genome.fa"
    bed = tmp_path / "regions.bed"
    for f in [truth, query, ref]: f.touch()

    # Mock Docker interactions
    mock_container = MagicMock()
    mock_container.wait.return_value = {"StatusCode": 0}
    mock_utils.run_image_from_archive.return_value = mock_container

    # Simulate the tool creating the output file in the dynamic folder
    # Folder name follows the logic: out_{truth}_{query}
    expected_out_dir = tmp_path / "out_truth_set_query_set"
    expected_out_dir.mkdir()
    stats_file = expected_out_dir / "truth_set_query_set.stats.csv"
    stats_file.touch()

    # Act
    result = run(Path("docker_image.tar.gz"), truth, query, ref, bed)

    # Assert
    assert result == stats_file.resolve()
    mock_utils.run_image_from_archive.assert_called_once()
    mock_container.remove.assert_called_once()

@patch("sompy.sompy.docker_utils")
def test_run_sompy_failure(mock_utils: MagicMock, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that RuntimeError is raised when run_image_from_archive fails"""
    monkeypatch.chdir(tmp_path)
    
    # Setup: Touch minimal files to get past initialization
    truth = tmp_path / "truth.vcf"
    query = tmp_path / "query.vcf"
    ref = tmp_path / "ref.fa"
    bed = tmp_path / "regions.bed"
    for f in [truth, query, ref]: f.touch()

    # Simulate a crash (StatusCode 1)
    mock_container = MagicMock()
    mock_container.wait.return_value = {"StatusCode": 1}
    mock_container.logs.return_value = b"Error: Out of memory"
    mock_utils.run_image_from_archive.return_value = mock_container

    with pytest.raises(RuntimeError, match="Sompy failed with exit code 1"):
        run(Path("img.gz"), truth, query, ref, bed)