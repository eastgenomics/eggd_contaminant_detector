import tarfile
from pathlib import Path
from typing import Optional

import pandas as pd
import dxpy
from .types import DXFileID, DXLink

def download_reference(reference: DXFileID, ref_index: Optional[DXFileID]=None, destination: Path=Path("/home/dnanexus/in")) -> Path:
    ref_name = dxpy.describe(reference)["name"]
    # I added the type hint to this variable because my IDE wasn't reading it as Path for
    # some reason, despite the declaration in the function signature
    ref_path: Path = destination / ref_name
    dxpy.download_dxfile(reference, filename=str(ref_path))
    if ref_path.name.endswith((".tar", ".tar.gz", ".tgz")):
        ref_path = extract_ref_tar(ref_path, destination)
        if ref_index:
            print("WARNING: Tarball provided; ignoring the additional reference_index input.")
    else:
        if not ref_index:
            raise ValueError(f"No index provided for raw FASTA: {ref_name}")
        ref_index_name = dxpy.describe(ref_index)["name"]
        dxpy.download_dxfile(ref_index, str(destination / ref_index_name))
    return ref_path

def extract_ref_tar(ref_path: Path, destination: Path) -> Path:
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
        return destination_root / fasta_m.name

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