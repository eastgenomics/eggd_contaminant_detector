import re
import tarfile
import pandas as pd
from functools import reduce
from pathlib import Path
from typing import Optional

from . import _dataframe


def setup_reference(reference: Path, index: Optional[Path] = None) -> Path:
    if reference.name.endswith((".tar", ".tar.gz", ".tgz")):
        processed_ref = extract_ref_tar(reference, reference.parent)
    else:
        if index:
            index.rename(reference.parent / index.name)
            processed_ref = reference
        else:
            raise ValueError("No index provided")
    return processed_ref.resolve()


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
            member.name = Path(member.name).name
        tar.extractall(members=[fasta_m, index_m], path=destination_root, filter="data")
    return destination_root / Path(fasta_m.name).name


def extract_snvs(input_path: Path) -> pd.DataFrame:
    sompy_df = read_csvs(input_path, pattern="*.stats.csv")
    parsed_df = _dataframe.parse_samples(sompy_df)
    snvs: pd.DataFrame = parsed_df[parsed_df["type"] == "SNVs"]
    return snvs


def remove_vcf_extension(vcf: Path | str) -> str:
    vcf_name = Path(vcf).name
    pattern = r"(\.norm\.sorted|\.sorted)?\.(?:g\.)?g?vcf(?:\.gz)?$"
    return re.sub(pattern, "", vcf_name)


def read_csvs(path: Path, pattern: str) -> pd.DataFrame:
    files = list(path.rglob(pattern))
    if not files:
        raise FileNotFoundError(f"No files matching {pattern!r} under {path}")
    return pd.concat([pd.read_csv(f) for f in files], ignore_index=True)