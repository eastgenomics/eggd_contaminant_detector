import tarfile
import pandas as pd
from pathlib import Path
from typing import Optional

import sompy # type: ignore


def setup_ref_from_data_dir(data_dir: Path) -> None:
    ref_exts = ["*.fa", "*.fa.gz", "*.fasta", "*.fasta.gz", "*.tar*"]
    ref_dir = data_dir / "reference"
    refs = [f for ext in ref_exts for f in ref_dir.glob(ext)]

    ind_exts = ["*.fai", "*.gzi"]
    inds = (f for ext in ind_exts for f in data_dir.rglob(f"**/{ext}"))
    try:
        index_path = next(inds)
    except StopIteration:
        index_path = None

    if len(refs) == 0:
        raise ValueError(f"No reference found in {str(data_dir)}/reference/")
    elif len(refs) > 1:
        errormsg = f"Multiple possible reference files found in {str(data_dir)}/reference/:\n{refs}"
        raise ValueError(errormsg)
    else:
        ref_path = refs[0]
        setup_reference(ref_path, index_path)


def setup_reference(reference: Path, index: Optional[Path] = None) -> None:
    if reference.name.endswith((".tar", ".tar.gz", ".tgz")):
        extract_ref_tar(reference, reference.parent)
    else:
        if index:
            index.rename(reference.parent / index.name)
        else:
            raise ValueError("No index provided")


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
            member.name = Path(member.name).name
        tar.extractall(members=[fasta_m, index_m], path=destination_root, filter="data")


def extract_snvs(input_path: Path) -> pd.DataFrame:
    sompy_df = read_csvs(input_path, pattern="**/*.stats.csv")
    parsed_df = sompy.parse_samples(sompy_df)
    snvs: pd.DataFrame = parsed_df[parsed_df["type"] == "SNVs"]
    return snvs


def read_csvs(path: Path, pattern: str) -> pd.DataFrame:
    files = path.glob(pattern)
    df = pd.concat([pd.read_csv(f) for f in files])
    return df
