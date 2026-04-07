import pytest
from pathlib import Path

import sompy._paths  # type: ignore


def test_make_mounts_str(
    tmp_path: Path, bindmounts: list[dict[str, str | bool]]
) -> None:
    in_dir = str(tmp_path / "in")
    out_dir = str(tmp_path / "out")
    actual_mounts = sompy._paths.make_mounts(in_dir, out_dir)
    assert actual_mounts == bindmounts


def test_make_mounts_path(
    tmp_path: Path, bindmounts: list[dict[str, str | bool]]
) -> None:
    in_dir = tmp_path / "in"
    out_dir = tmp_path / "out"
    actual_mounts = sompy._paths.make_mounts(in_dir, out_dir)
    assert actual_mounts == bindmounts


def test_resolve_in_dir(tmp_path) -> None:
    truth = tmp_path / "in" / "truth" / "truth.vcf.gz"
    query = tmp_path / "in" / "query" / "query.vcf.gz"
    panel = tmp_path / "in" / "panel" / "panel.bed"
    expected = tmp_path / "in"
    assert sompy._paths.resolve_in_dir(truth, query, panel=panel) == expected


def test_resolve_in_dir_one_file(tmp_path) -> None:
    truth = tmp_path / "in" / "truth" / "truth.vcf.gz"
    expected = tmp_path / "in" / "truth"
    assert sompy._paths.resolve_in_dir(truth) == expected


def test_resolve_in_dir_as_kwargs(tmp_path) -> None:
    test_kwargs = {
        "truth": tmp_path / "in" / "truth" / "truth.vcf.gz",
        "query": tmp_path / "in" / "query" / "query.vcf.gz",
        "panel": tmp_path / "in" / "panel" / "panel.bed",
    }
    expected = tmp_path / "in"
    assert sompy._paths.resolve_in_dir(**test_kwargs) == expected


def test_resolve_in_dir_as_mix_of_args_and_kwargs(tmp_path) -> None:
    test_args = [
        tmp_path / "in" / "truth" / "truth.vcf.gz",
        tmp_path / "in" / "query" / "query.vcf.gz",
    ]
    test_kwargs = {"panel": tmp_path / "in" / "panel" / "panel.bed"}
    expected = tmp_path / "in"
    assert sompy._paths.resolve_in_dir(*test_args, **test_kwargs) == expected


def test_get_output_paths_one(tmp_path) -> None:
    expected_path = tmp_path / "test.txt"
    expected_path.touch()
    actual_path = sompy._paths.get_output_path(tmp_path, "test.txt")
    assert actual_path == expected_path


def test_get_output_paths_many(tmp_path) -> None:
    one = tmp_path / "test_1.txt"
    one.touch()
    two = tmp_path / "test_2.txt"
    two.touch()
    actual_path = sompy._paths.get_output_path(tmp_path, "test_*.txt")
    assert actual_path == tmp_path
