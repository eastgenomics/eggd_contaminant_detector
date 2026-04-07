import pytest
from pathlib import Path

import contaminant_detector._fs as fs


def test_setup_reference_with_tar(tmp_path: Path, ref_genome_tar_gz: Path) -> None:
    expected_reference_genome = tmp_path / "reference" / "genome.fa"
    expected_ref_index = tmp_path / "reference" / "genome.fa.fai"

    fs.setup_reference(ref_genome_tar_gz)

    assert expected_reference_genome.is_file()
    assert expected_reference_genome.exists()
    assert expected_ref_index.is_file()
    assert expected_ref_index.exists()


def test_setup_reference_moves_index(tmp_path: Path) -> None:
    in_dir = tmp_path / "in"
    reference = in_dir / "reference" / "reference.fa"
    reference.parent.mkdir(parents=True, exist_ok=True)
    reference.touch()

    ref_index = in_dir / "ref_index" / "reference.fa.fai"
    ref_index.parent.mkdir(parents=True, exist_ok=True)
    ref_index.touch()

    expected_index_path = in_dir / "reference" / "reference.fa.fai"
    fs.setup_reference(reference, ref_index)
    assert expected_index_path.exists()
    assert expected_index_path.is_file()


def test_extract_ref_tar(tmp_path: Path, ref_genome_tar_gz: Path) -> None:
    expected_reference_genome = tmp_path / "reference" / "genome.fa"
    expected_ref_index = tmp_path / "reference" / "genome.fa.fai"

    fs.extract_ref_tar(ref_genome_tar_gz, ref_genome_tar_gz.parent)
    assert expected_reference_genome.is_file()
    assert expected_reference_genome.exists()
    assert expected_ref_index.is_file()
    assert expected_reference_genome.exists()


def test_extract_ref_tar_nested(tmp_path: Path, nested_ref_genome_tar_gz: Path) -> None:
    expected_reference_genome = tmp_path / "reference" / "genome.fa"
    expected_ref_index = tmp_path / "reference" / "genome.fa.fai"

    fs.extract_ref_tar(nested_ref_genome_tar_gz, nested_ref_genome_tar_gz.parent)
    assert expected_reference_genome.is_file()
    assert expected_reference_genome.exists()
    assert expected_ref_index.is_file()
    assert expected_reference_genome.exists()


def test_extract_snvs(sompy_csv_dir: Path) -> None:
    snv_df = fs.extract_snvs(sompy_csv_dir)
    # 2 contam * 3 cand
    assert len(snv_df) == 6
    assert snv_df["type"].unique() == "SNVs"


@pytest.mark.parametrize(
    "vcf, expected",
    [
        ("sample.sorted.vcf.gz", "sample"),
        ("sample.g.vcf.gz", "sample"),
        ("sample.vcf", "sample"),
        ("sample.vcf.gz", "sample"),
        ("sample.gvcf.gz", "sample"),
        (
            "123456789-25001K0001-25PCAN1-10001-U.vcf.gz",
            "123456789-25001K0001-25PCAN1-10001-U",
        ),
        (Path("path/to/file.vcf"), "file"),
    ],
)
def test_remove_vcf_extension(vcf: str, expected: str) -> None:
    assert fs.remove_vcf_extension(vcf) == expected


def test_read_csvs(sompy_csv_dir: Path) -> None:
    df = fs.read_csvs(sompy_csv_dir, pattern="**/*.stats.csv")
    # 2 contam * 3 cand * 3 row types (snvs, indels, records)
    assert len(df) == 18
