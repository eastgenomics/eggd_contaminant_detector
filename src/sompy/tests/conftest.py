from pathlib import Path
from typing import TypeAlias

import pandas as pd
import pytest

MountConfig: TypeAlias = list[dict[str, str | bool]]
CommandConfig: TypeAlias = dict[str, str | Path | MountConfig]


@pytest.fixture(name="bindmounts")
def mock_bindmounts(tmp_path: Path) -> MountConfig:
    return [
        {
            "Target": "/in",
            "Source": str(tmp_path / "in"),
            "Type": "bind",
            "ReadOnly": False,
        },
        {
            "Target": "/out",
            "Source": str(tmp_path / "out"),
            "Type": "bind",
            "ReadOnly": False,
        },
    ]


@pytest.fixture(name="bcftools_sort_args")
def mock_sort_inputs(tmp_path: Path, bindmounts: MountConfig) -> CommandConfig:
    return {"vcf": tmp_path / "in" / "test.vcf.gz", "mounts": bindmounts}


@pytest.fixture(name="bcftools_norm_args")
def mock_norm_inputs(tmp_path: Path, bcftools_sort_args: CommandConfig) -> CommandConfig:
    bcftools_sort_args.update({"reference": tmp_path / "in" / "test_reference.fa"})
    return bcftools_sort_args


@pytest.fixture(name="sompy_args_without_regions")
def mock_sompy_inputs_without_regions(
    tmp_path: Path, bindmounts: MountConfig
) -> CommandConfig:
    return {
        "truth": tmp_path / "in" / "truth.vcf.gz",
        "query": tmp_path / "in" / "query.vcf.gz",
        "reference": tmp_path / "in" / "reference.fa",
        "mounts": bindmounts,
    }


@pytest.fixture(name="sompy_args_with_regions")
def mock_sompy_inputs_with_regions(
    tmp_path: Path, sompy_args_without_regions: CommandConfig
) -> CommandConfig:
    sompy_args_without_regions.update({"panel_regions": tmp_path / "in" / "panel.bed"})
    return sompy_args_without_regions


@pytest.fixture(name="sompy_df")
def mock_sompy_df() -> pd.DataFrame:
    groups = ["a", "b", "c", "d", "e"]
    suffices = ["vcf.gz", "vcf", "g.vcf.gz", "gvcf", "gvcf.gz"]
    truths = [f"/in/truth_{group}.{suffix}" for group, suffix in zip(groups, suffices)]
    querys = [f"/in/query_{group}.{suffix}" for group, suffix in zip(groups, suffices)]

    core_cmd = "/opt/hap.py/bin/som.py --no-count-unk --no-fixchr-truth --no-fixchr-query --include-nonpass"
    reference_arg = "--reference /in/reference.fa"
    commands = [
        " ".join(
            [
                core_cmd,
                f"-o /out/{truth[4:11]}_{query[4:11]}",
                reference_arg,
                truth,
                query,
            ]
        )
        for truth, query in zip(truths, querys)
    ]
    pd_data = list(zip(truths, querys, commands))
    return pd.DataFrame(pd_data, columns=("truth", "query", "sompycmd"))
