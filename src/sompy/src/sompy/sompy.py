import re
import pandas as pd
from pathlib import Path

from egg_helpers import docker_utils

def run_sompy(image: Path, truth: Path, query: Path, reference: Path) -> Path:
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
    command = [
        "/opt/hap.py/bin/som.py",
        "--no-count-unk",
        "--no-fixchr-truth", 
        "--include-nonpass", 
        "--no-fixchr-query", 
        "-o", str(cont_out / samples), 
        "--reference", str(cont_in / reference.relative_to(host_in)), 
        str(cont_in / truth.name), 
        str(cont_in / query.name)
        ]
    container = docker_utils.run_image_from_archive(image=image, command=command, mounts=mounts)
    result = container.wait()
    if result.get("StatusCode") != 0:
        print(container.logs().decode())
        raise RuntimeError(f"Sompy failed with exit code {result['StatusCode']}")
    stats_path = next(host_out.glob("*.stats.csv")).resolve()
    container.remove()
    return stats_path

def parse_samples(df: pd.DataFrame) -> pd.DataFrame:
    """Parses the 'sompycmd' column to extract and add sample names.

    Sompy embeds the original file paths in the 's:w
    ompycmd' column. This function
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