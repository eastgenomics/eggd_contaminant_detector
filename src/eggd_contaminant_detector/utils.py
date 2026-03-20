import tarfile
from pathlib import Path
from typing import Tuple
from docker.types import Mount

import pandas as pd
import dxpy
from dxpy import DXJob
from .types import DXFileID, DXLink

from sompy import bcftools
from sompy.utils import make_mounts

def setup_env() -> Tuple[Path, Path, list[Mount, Mount]]:
    dxpy.download_all_inputs(parallel=True)
    in_dir = Path("/home/dnanexus/in")
    setup_reference(in_dir)
    sompy_image = next(Path("/image").glob("*happy*.tar.gz")).resolve()
    bcftools_image = next(Path("/image").glob("*bcftools*.tar.gz")).resolve()
    mounts = make_mounts(in_dir, "/home/dnanexus/out")
    return sompy_image, bcftools_image, mounts

def setup_reference(in_dir: Path) -> None:
    ref_dir = in_dir / "reference"
    ref_path = next(ref_dir.glob("*")).resolve()
    if ref_path.name.endswith((".tar", ".tar.gz", ".tgz")):
        extract_ref_tar(ref_path, ref_dir)
    else:
        index_path = Path("/home/dnanexus/in/ref_index")
        indices = [p for p in index_path.glob("*") if p.suffix in {".fai", ".gzi"}]
        if indices:
            for idx in indices:
                idx.rename(ref_dir / idx.name)

def extract_ref_tar(ref_path: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    destination_root = destination.resolve()
    with tarfile.open(ref_path) as tar:
        members = tar.getmembers()
        fasta_exts = (".fa", ".fasta", ".fna", ".fa.gz", ".fasta.gz")
        index_exts = (".fai", ".gzi")
        try:
            fasta_m = next(m for m in members if m.name.lower().endswith(fasta_exts))
            index_m = next(m for m in members if m.name.lower().endswith(index_exts))
        except StopIteration:
            raise FileNotFoundError(f"Tarball {ref_path.name} missing FASTA or index.")
        for member in [fasta_m, index_m]:
            # safety check (".."s in tar member names are unsafe)
            original_path = (destination_root / member.name).resolve()
            if not original_path.is_relative_to(destination_root):
                raise PermissionError(f"Unsafe path detected: {member.name}")
            # strip away the nesting from the Tarfile object names so we can extract them directly
            member.name = Path(member.name).name
        tar.extractall(members=[fasta_m, index_m], path=destination_root)

def prepare_sompy_inputs(in_dir, bcftools_image) -> dict[str, Path]:
    truth_vcf = preprocess(get_single_file(in_dir / "truth", "*.vcf.gz"), bcftools_image)
    query_vcf = preprocess(get_single_file(in_dir / "query", "*.vcf.gz"), bcftools_image)
    ref = get_single_file(in_dir / "reference", exclude = {".fai", ".gz.fai", ".gzi", ".tar.gz"})
    panel = get_single_file(in_dir / "panel_bed", "*.bed*")
    return {
        "truth": truth_vcf,
        "query": query_vcf,
        "reference": ref,
        "panel_regions": panel
    }

def get_single_file(path: Path, pattern: str = "*", exclude: set = None) -> Path:
    files = list(path.rglob(pattern))
    if exclude:
        files = [f for f in files if "".join(f.suffixes) not in exclude]
    if not files:
        print(f"No files matching {pattern} found in {path}")
        return None
    return files[0]

def preprocess(vcf: Path, bcftools_image: Path) -> Path:
    normalised_vcf = bcftools.norm(vcf, bcftools_image)
    sorted_vcf = bcftools.sort(normalised_vcf, bcftools_image)
    return sorted_vcf

def new_subjob(fn_name: str, inputs: dict[str, str], priority: str) -> DXJob:
    # using our own wrapper instead of dxpy.new_dxjob because new_dxjob doesn't
    # support setting the job priority
    payload = {
        "function": fn_name,
        "input": inputs,
        "priority": priority
    }
    response = dxpy.api.job_new(payload)
    return dxpy.DXJob(response["id"])

def get_file_id(dx_link: DXLink) -> DXFileID:
    """Extracts the raw file ID string from a DNAnexus link object.

    Handles both flat link structures (e.g., {"$dnanexus_link": "file-XXX"}) 
    and nested structures (e.g., {"$dnanexus_link": {"id": "file-XXX", ...}}).

    Args:
        dx_link: A DNAnexus link dictionary representing a file reference.

    Returns:
        The extracted file ID as a DXFileID (string).
    """
    try:
        return dx_link["$dnanexus_link"]["id"]
    except TypeError:
        return dx_link["$dnanexus_link"]

def read_csvs(path: Path, pattern: str) -> pd.DataFrame:
    """Discovers and concatenates all CSV files in a path.

    Args:
        path: Path object pointing to the directory to search.
        pattern: Glob pattern to match files.

    Returns:
        pd.DataFrame: A single DataFrame containing data from all matched files.
    """
    files = path.glob(pattern)
    df = pd.concat([pd.read_csv(f) for f in files])
    return df

def shorten(name: str) -> str:
    """Extracts the 2nd and 3rd fields from the EPIC name so that they'll fit on a plot. Returns the input
    as-is if not formatted like an EPIC name.

    Args:
        name: EPIC-formatted sample name
    
    Returns:
        Either the shortened string, or the input as-is if not formatted like an EPIC sample name
    """
    parts = name.split('-')
    if len(parts) >= 3:
        return f"{parts[1]}-{parts[2]}"
    return name