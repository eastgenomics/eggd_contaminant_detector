import pandas as pd
from pathlib import Path
from typing import Optional
from docker.types import Mount

from egg_helpers import docker_utils
from . import utils

def run(image: Path, truth: Path, query: Path, reference: Path, panel_regions: Optional[Path], in_mount: Mount, out_mount: Mount):
    out_dir = Path(out_mount["Target"])
    command = sompy_command(truth, query, reference, out_dir, panel_regions, in_mount, out_mount)
    with docker_utils.run_container(image, command, [in_mount, out_mount]) as container:
        return next(out_dir.glob("*.stats.csv)"))

@docker_utils.make_io_relative_to_container
def sompy_command(truth: Path, query: Path, reference: Path, out_dir: Path, panel_regions: Optional[Path], *mounts: Mount) -> str:
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