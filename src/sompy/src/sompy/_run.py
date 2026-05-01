from pathlib import Path
from typing import Optional

import ambergris

from . import _paths, _heredocs


def run(
    truths: list[Path],
    querys: list[Path],
    reference: Path,
    out_dir: Path,
    sompy_image: Path | str,
    bcftools_image: Optional[Path | str],
    panel_regions: Optional[Path] = None,
    preprocess: bool = True,
) -> tuple[Path, Path]:
    """
    Executes som.py using containerized tools.

    This function runs comparisons of query VCFs against truthset VCFs using som.py.
    It automatically maps host paths to container paths. It optionally performs
    preprocessing for input sanitisation using bcftools before running som.py - specifically,
    bcftools is used to normalise (decomposing multiallelic variants and removing
    duplicates) and sort the input before running through som.py. This operation is performed
    on both truth and query lists if requested.

    Args:
        truths: A list of paths to the truthset VCF files.
        querys: A list of paths to the query VCF files to be evaluated.
        reference: Path to the reference genome FASTA file.
        out_dir: Directory where benchmarking results and logs will be stored.
        sompy_image: Path or URI to the SomPy container image (e.g., SIF file).
        bcftools_image: Path or URI to the bcftools container image. Required if
            `preprocess` is True.
        panel_regions: Optional path to a BED file defining specific genomic
            regions for evaluation (e.g., high-confidence regions).
        preprocess: If True, executes a preprocessing step on input VCFs using
            the bcftools container before benchmarking. Defaults to True.

    Returns:
        A tuple containing (stats_path, metrics_path):
            * stats_path (Path): Path to the generated `.stats.csv` file.
            * metrics_path (Path): Path to the generated `.metrics.json` file.

    Raises:
        ValueError: If `preprocess` is True but `bcftools_image` is not provided.
        FileNotFoundError: If required input paths cannot be resolved or output
            files are not generated.
    """
    in_dir = _paths.resolve_in_dir(*truths, *querys, reference, panel_regions)
    mounts = _paths.make_mounts(in_dir, out_dir)
    _paths.write_paths(truths, querys, reference, panel_regions, mounts=mounts)
    if preprocess:
        if bcftools_image is None:
            raise ValueError(
                "preprocess flag is True, but no bcftools image was provided. Exiting..."
            )
        with ambergris.open_container(bcftools_image, *mounts) as bcftools_container:
            ambergris.exec_command(
                bcftools_container, ["/bin/bash", "-c", _heredocs.preprocess()]
            )
    with ambergris.open_container(sompy_image, *mounts) as sompy_container:
        ambergris.exec_command(sompy_container, ["/bin/bash", "-c", _heredocs.sompy()])
    stats = _paths.get_output_path(out_dir, "*.stats.csv")
    metrics = _paths.get_output_path(out_dir, "*.metrics.json")
    return stats, metrics
