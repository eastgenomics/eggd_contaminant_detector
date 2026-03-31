from pathlib import Path
from typing import TypeAlias

import pytest

import sompy._paths # type: ignore

def test_make_mounts_str(tmp_path: Path, bindmounts: list[dict[str, str | bool]]) -> None:
    in_dir = str(tmp_path / "in")
    out_dir = str(tmp_path / "out")
    actual_mounts = sompy._paths._make_mounts(in_dir, out_dir)
    assert actual_mounts == bindmounts


def test_make_mounts_path(tmp_path: Path, bindmounts: list[dict[str, str | bool]]) -> None:
    in_dir = tmp_path / "in"
    out_dir = tmp_path / "out"
    actual_mounts = sompy._paths._make_mounts(in_dir, out_dir)
    assert actual_mounts == bindmounts


def test_get_host_out_dir(bindmounts: list[dict[str, str | bool]], tmp_path: Path) -> None:
    out_dir = sompy._paths._get_out_dir(*bindmounts, key="Source") # type: ignore
    assert out_dir == tmp_path / "out"


def test_get_container_out_dir(bindmounts: list[dict[str, str | bool]]) -> None:
    out_dir = sompy._paths._get_out_dir(*bindmounts, key="Target") # type: ignore
    assert out_dir == Path("/out")


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
    assert sompy._paths._remove_vcf_extension(vcf) == expected


@pytest.mark.parametrize(
    "paths, expected",
    [
        (
            [
                Path(p)
                for p in [
                    "./in/truth/truth.vcf.gz",
                    "./in/query/query.vcf.gz",
                    "./in/reference/reference.fa",
                ]
            ],
            str(Path.cwd() / "in"),
        ),
        (
            [
                Path(p)
                for p in [
                    "./in/files/vcfs/1.vcf.gz",
                    "./in/files/vcfs/2.vcf.gz",
                    "./in/files/panels/1.bed",
                ]
            ],
            str(Path.cwd() / "in" / "files"),
        ),
    ],
)
def test_resolve_common_parent(paths: list[Path], expected: Path) -> None:
    assert sompy._paths._resolve_common_parent(paths) == expected


def test_resolve_in_dir() -> None:
    truth = Path("./in/truth/truth.vcf.gz")
    query = Path("./in/query/query.vcf.gz")
    panel = Path("./in/panel/panel.bed")
    expected = Path.cwd() / "in"
    assert sompy._paths._resolve_in_dir(truth, query, panel=panel) == expected


def test_resolve_in_dir_as_kwargs() -> None:
    test_kwargs = {
        "truth": Path("./in/truth/truth.vcf.gz"),
        "query": Path("./in/query/query.vcf.gz"),
        "panel": Path("./in/panel/panel.bed"),
    }
    expected = Path.cwd() / "in"
    assert sompy._paths._resolve_in_dir(**test_kwargs) == expected


def test_resolve_in_dir_as_mix_of_args_and_kwargs() -> None:
    test_args = [Path("./in/truth/truth.vcf.gz"), Path("./in/query/query.vcf.gz")]
    test_kwargs = {"panel": Path("./in/panel/panel.bed")}
    expected = Path.cwd() / "in"
    assert sompy._paths._resolve_in_dir(*test_args, **test_kwargs) == expected


def test_get_next_in_tree() -> None:
    expected = "/in/files"
    assert (
        sompy._paths._get_next_in_tree(
            [Path("./in/files/truth.vcf.gz"), Path("./in/files/query.vcf.gz")]
        )
        == expected
    )
