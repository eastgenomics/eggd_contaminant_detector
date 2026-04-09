from pathlib import Path
from typing import Optional

import sompy

from . import _fs
from . import _plot


def run_contam_check(
    truths: list[Path],
    querys: list[Path],
    reference: Path,
    out_dir: Path,
    sompy_image: str | Path,
    bcftools_image: Optional[str | Path],
    panel_regions: Optional[Path] = None,
    ref_index: Optional[Path] = None,
    preprocess: bool = True,
) -> tuple[Path, Path]:
    """
    Executes som.py using containerised tools to produce the files required for
    contamination check plotting (see plot_recall)

    This function runs comparisons of query VCFs against truthset VCFs using som.py.
    It automatically maps host paths to container paths. It optionally performs
    preprocessing for input sanitisation using bcftools before running som.py - specifically,
    bcftools is used to normalise (decomposing multiallelic variants and removing
    duplicates) and sort the input before running through som.py. This operation is performed
    on both truth and query lists if requested.

    Args:
        truths: A list of paths to the truthset VCF files.
        querys: A list of paths to the query VCF files to be evaluated.
        reference: Path to the reference genome FASTA file - please unpack if stored as tar[.gz].
        out_dir: Directory where results will be stored.
        sompy_image: Path or URI to the som.py docker image, or
            the name:tag of the image stored in your local docker registry.
        bcftools_image: Path or URI to the bcftools docker image, or
            the name:tag of the image stored in your local docker registry.
            Required if `preprocess` is True.
        panel_regions: Optional path to a BED file defining specific genomic
            regions for evaluation (e.g., high-confidence regions).
        ref_index: Optional path to the reference genome index if not submitting an archived
            tar containing both the reference genome and its related index. Required if submitting
            a raw FASTA file to the reference argument.
        preprocess: If True, executes a preprocessing step (i.e. normalisation and sorting) on
            input VCFs using the bcftools container before benchmarking. Defaults to True.

    Returns:
        A tuple containing (stats_path, metrics_path):
            * stats_path (Path): Path to the generated `.stats.csv` file.
            * metrics_path (Path): Path to the generated `.metrics.json` file.
    """
    processed_ref = _fs.setup_reference(reference, ref_index)
    kwargs = {
        "out_dir": out_dir,
        "truths": truths,
        "querys": querys,
        "reference": processed_ref,
        "sompy_image": sompy_image,
        "bcftools_image": bcftools_image,
        "preprocess": preprocess,
    }
    if panel_bed:
        kwargs["panel_regions"] = panel_bed
    stats_csv, metrics_json = sompy.run(**kwargs)
    return stats_csv, metrics_json


def plot_recall(
    in_dir: Path,
    out_dir: Path,
    baseline: float = 0.4,
) -> tuple[Path, Path]:
    """
    Produces either a heatmap or barplot object from a directory containing
    *.stats.csv outputs from run_contam_check. If only one truthset is present,
    the output will be a barplot of the recall values for the comparison against
    each candidate. If more than one truthset is present, the output will be a heatmap.
    The function also concatenates all of the som.py output CSV data into a single CSV, and
    adds columns containing the sample names for contaminated samples and candidates.

    The colour gradient curve can be modified with the baseline argument if the recall midpoint
    of the dataset is known to deviate from the default of 0.4. In other words, the curve controls
    the rate at which the colour gradient changes after the midpoint is reached, which can be useful
    for separating truly high values from the baseline.

    For instance, if you know your average recall value between unrelated and uncontaminated samples for
    your assay is 0.6, then setting the baseline to 0.6 will cause everything up to that point to be represented
    with the low end of the colour scale, and everything after that point will accelerate into the high end
    fairly quickly.

    Args:
        in_dir: Path to directory containing the collection of *stats.csv files
        out_dir: Path to directory where you want to store the output
        baseline: float value for the expected midpoint of recall values for a given assay
    """
    snv_df = _fs.extract_snvs(in_dir)
    sompy_data = out_dir / "sompy_data.csv"
    sompy_data.parent.mkdir(exist_ok=True, parents=True)
    snv_df.to_csv(sompy_data)
    recall_plot = _plot._generate_comparison_plot(
        df=snv_df, metric="recall2", slope_params=(0.0, baseline, 1.0)
    )
    plot_path = Path(out_dir / "plot.png")
    recall_plot.savefig(plot_path)
    return sompy_data, plot_path
