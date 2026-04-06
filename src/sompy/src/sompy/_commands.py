from pathlib import Path

import ambergris
from docker.types import Mount

from . import _paths


@ambergris.make_io_relative_to_container
def _sompy(
    truth: Path,
    query: Path,
    reference: Path,
    panel_regions: Path | None = None,
    mounts: list[Mount] = [],
) -> tuple[str, Path]:
    truth_sample = _paths._remove_vcf_extension(truth)
    query_sample = _paths._remove_vcf_extension(query)
    samples = f"{truth_sample}_{query_sample}"
    stats_file = f"{samples}.stats.csv"
    h_out = _paths._get_out_dir(*mounts, key="Source")
    c_out = _paths._get_out_dir(*mounts, key="Target")
    base_cmd = [
        "/opt/hap.py/bin/som.py",
        "--no-count-unk",
        "--no-fixchr-truth",
        "--no-fixchr-query",
        "--include-nonpass",
        "-o",
        str(c_out / samples),
    ]
    if panel_regions:
        base_cmd += ["--restrict-regions", str(panel_regions)]
    sompy_inputs = ["--reference", str(reference), str(truth), str(query)]
    return " ".join(base_cmd + sompy_inputs), h_out / stats_file


@ambergris.make_io_relative_to_container
def _bcftools_sort(vcf: Path, mounts: list[Mount] = []) -> tuple[str, Path]:
    vcf_name = _paths._remove_vcf_extension(vcf)
    sorted_vcf = f"{vcf_name}.sorted.vcf.gz"
    h_out = _paths._get_out_dir(*mounts, key="Source")
    c_out = _paths._get_out_dir(*mounts, key="Target")
    cmd = " ".join(
        ["bcftools", "sort", "-W=tbi", "-Oz", "-o", str(c_out / sorted_vcf), str(vcf)]
    )
    return cmd, h_out / sorted_vcf


@ambergris.make_io_relative_to_container
def _bcftools_norm(
    vcf: Path, reference: Path, mounts: list[Mount] = []
) -> tuple[str, Path]:
    vcf_name = _paths._remove_vcf_extension(vcf)
    normalised_vcf = f"{vcf_name}.normalised.vcf.gz"
    h_out = _paths._get_out_dir(*mounts, key="Source")
    c_out = _paths._get_out_dir(*mounts, key="Target")
    cmd = " ".join(
        [
            "bcftools",
            "norm",
            "-f",
            str(reference),
            "-m-any",
            "-d",
            "any",
            "-W=tbi",
            "-Oz",
            "-o",
            str(c_out / normalised_vcf),
            str(vcf)
        ]
    )
    return cmd, h_out / normalised_vcf
