import pandas as pd
from pathlib import Path
from typing import Optional, Tuple
from docker.types import Mount

from egg_helpers import docker_utils
from . import utils

def run(image: Path, truth: Path, query: Path, reference: Path, out_dir: Path, panel_regions: Optional[Path], *mounts: Mount) -> Path:
    cmd, stats = sompy_command(truth, query, reference, out_dir, panel_regions, *mounts)
    docker_utils.run_container(image, cmd, *mounts)
    return stats

@docker_utils.make_io_relative_to_container
def sompy_command(truth: Path, query: Path, reference: Path, out_dir: Path, panel_regions: Optional[Path], *mounts: Mount) -> Tuple[list[str], str]:
    truth_sample = utils.remove_vcf_extension(truth)
    query_sample = utils.remove_vcf_extension(query)
    samples = f"{truth_sample}_{query_sample}"
    stats = out_dir / samples
    base_cmd = [
        "/opt/hap.py/bin/som.py",
        "--no-count-unk",
        "--no-fixchr-truth",
        "--no-fixchr-query",
        "--include-nonpass",
        "-o", str(stats)
    ]
    if panel_regions:
        base_cmd += ["--restrict-regions", str(panel_regions)]
    sompy_inputs = [
        "--reference", str(reference),
        str(truth),
        str(query)
    ]
    return base_cmd + sompy_inputs, stats

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