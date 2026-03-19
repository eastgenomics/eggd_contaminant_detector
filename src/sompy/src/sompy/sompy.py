import pandas as pd
from pathlib import Path
from typing import Optional
from docker.types import Mount

from egg_helpers import docker_utils
from . import sort, utils

def run(sompy_image: Path, bcftools_image: Path, in_mount: Mount, out_mount: Mount, truth: Path, query: Path, reference: Path, panel_regions: Optional[Path], sort_vcf: Optional[bool]=True) -> Path:
    if sort_vcf:
        truth_vcf = sort.run_bcftools_sort(bcftools_image, truth, in_mount, out_mount)
        query_vcf = sort.run_bcftools_sort(bcftools_image, query, in_mount, out_mount)
    else:
        truth_vcf = truth
        query_vcf = query
    stats = _run_sompy(sompy_image, in_mount, out_mount, truth_vcf, query_vcf, reference, panel_regions)
    return stats

def make_sompy_mounts(in_dir: Path, out_dir: Path) -> list[Mount, Mount]:
    host_in = in_dir
    cont_in = Path("/in")
    host_out = out_dir
    host_out.mkdir(parents=True, exist_ok=True)
    cont_out = Path("/out")
    mounts = docker_utils.make_bindmounts((host_in, cont_in), (host_out, cont_out))
    return mounts

def _run_sompy(image, in_mount, out_mount, truth_vcf, query_vcf, reference, panel_regions):
    host_out = Path(out_mount["Source"])
    command = _mounted_sompy_cmd(in_mount, out_mount, truth_vcf, query_vcf, reference, panel_regions)
    container = docker_utils.run_from_archive(image=image, command=command, mounts=[in_mount, out_mount])
    try:
        result = container.wait()
        if result.get("StatusCode") != 0:
            print(container.logs().decode())
            raise RuntimeError(f"Sompy failed with exit code {result['StatusCode']}")
        return next(host_out.glob("*.stats.csv")).resolve()
    finally:
        container.remove()

def _mounted_sompy_cmd(in_mount: Path, out_mount: Path, truth: Path, query: Path, reference: Path, panel_regions: Optional[Path]) -> list[str]:
    cont_out = Path(out_mount["Target"])

    c_truth = utils.get_container_path(truth, in_mount, out_mount)
    c_query = utils.get_container_path(query, in_mount, out_mount)
    c_ref   = utils.get_container_path(reference, in_mount, out_mount)
    
    if panel_regions:
        c_panel = utils.get_container_path(panel_regions, in_mount, out_mount)
    else:
        c_panel = None

    command = _make_relative_sompy_cmd(c_truth, c_query, c_ref, cont_out, c_panel)
    return command

def _make_relative_sompy_cmd(truth: Path, query: Path, reference: Path, out_dir: Path, panel_regions: Optional[Path]) -> str:
    truth_sample = utils.remove_vcf_extension(truth)
    query_sample = utils.remove_vcf_extension(query)
    samples = f"{truth_sample}_{query_sample}"
    base_cmd = [
        "/opt/hap.py/bin/som.py",
        "--no-count-unk",
        "--no-fixchr-truth",
        "--no-fixchr-query",
        "--include-nonpass",
        "-o", str(out_dir / samples)
    ]
    if panel_regions:
        base_cmd += ["--restrict-regions", str(panel_regions)]
    sompy_inputs = [
        "--reference", str(reference),
        str(truth),
        str(query)
    ]
    return base_cmd + sompy_inputs

def parse_samples(df: pd.DataFrame) -> pd.DataFrame:
    """Parses the 'sompycmd' column to extract and add sample names.

    Sompy embeds the original file paths in the 'sompycmd' column. This function
    extracts the truth and query filenames and parses them into clean sample names.

    Args:
        df: A DataFrame containing a 'sompycmd' column.

    Returns:
        pd.DataFrame: The modified DataFrame with added 'truth' and 'query' columns.
    """
    vcf_pattern = r'[^\s]+\.(?:g\.)?g?vcf(?:\.gz)?'
    matches = df["sompycmd"].str.findall(vcf_pattern)
    df["truth"] = matches.str[0].apply(utils.remove_vcf_extension)
    df["query"] = matches.str[1].apply(utils.remove_vcf_extension)
    return df