import re
import pandas as pd
from pathlib import Path
from typing import Optional

from egg_helpers import docker_utils

def run(image: Path, truth: Path, query: Path, reference: Path, panel_regions: Optional[Path]) -> Path:
    """Runs the Sompy comparison tool inside a Docker container.

    Sets up bind mounts between the host and the container, maps file paths 
    to the container's filesystem, and executes the `som.py` command. This 
    function assumes that truth, query, and reference files are located 
    within the same parent directory to simplify mounting.

    Args:
        image: Path to the Docker image tarball (.tar.gz).
        truth: Path to the ground-truth VCF on the host.
        query: Path to the query/evaluation VCF on the host.
        reference: Path to the reference FASTA on the host.
        panel_regions: Path to the panel-regions BED on the host.

    Returns:
        The absolute path to the generated '.stats.csv' file on the host.

    Raises:
        RuntimeError: If the Sompy container exits with a non-zero status code.
        StopIteration: If no '.stats.csv' file is found in the output directory 
            after the container finishes.

    Note:
        The function automatically handles internal Docker path mapping, 
        translating host paths into '/in' and '/out' container paths.
    """
    truth_sample = remove_vcf_extension(truth)
    query_sample = remove_vcf_extension(query)

    host_in = Path(truth).absolute().parent
    host_out = Path(f"out_{truth_sample}_{query_sample}").absolute()
    host_out.mkdir(parents=True, exist_ok=True)
    cont_in = Path("/in")
    cont_out = Path("/out")

    mounts = docker_utils.make_bindmounts((host_in, cont_in), (host_out, cont_out))
    samples = f"{truth_sample}_{query_sample}"

    base_cmd = [
        "/opt/hap.py/bin/som.py",
        "--no-count-unk",
        "--no-fixchr-truth",
        "--no-fixchr-query",
        "--include-nonpass",
        "-o", str(cont_out / samples)
    ]
    
    if panel_regions:
        cont_panel_path = cont_in / panel_regions.relative_to(host_in)
        base_cmd += ["--restrict-regions", str(cont_panel_path)]

    sompy_inputs = [
        "--reference", str(cont_in / reference.relative_to(host_in)),
        str(cont_in / truth.name), 
        str(cont_in / query.name)
    ]
    command = base_cmd + sompy_inputs
    container = docker_utils.run_image_from_archive(image=image, command=command, mounts=mounts)
    try:
        result = container.wait()
        if result.get("StatusCode") != 0:
            print(container.logs().decode())
            raise RuntimeError(f"Sompy failed with exit code {result['StatusCode']}")
        return next(host_out.glob("*.stats.csv")).resolve()
    finally:
        container.remove()

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
    df["truth"] = matches.str[0].apply(remove_vcf_extension)
    df["query"] = matches.str[1].apply(remove_vcf_extension)
    return df

def remove_vcf_extension(vcf: Path|str) -> str:
    """Extracts a clean sample name by stripping VCF-specific extensions.

    Removes suffixes including .vcf, .gvcf, .g.vcf, and their .gz compressed 
    variants from the filename.

    Args:
        vcf: The path to the VCF file.

    Returns:
        The filename as a string with the VCF extensions removed.
        
    Example:
        >>> clean_sample_name(Path("sample1.g.vcf.gz"))
        'sample1'
    """
    vcf = Path(vcf)
    return re.sub(r'\.(?:g\.)?g?vcf(?:\.gz)?$', "", vcf.name)
