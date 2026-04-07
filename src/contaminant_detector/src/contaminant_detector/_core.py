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
    sompy_image: Path,
    bcftools_image: Path,
    panel_bed: Optional[Path] = None,
    ref_index: Optional[Path] = None,
    preprocess: bool = True,
) -> tuple[Path, Path]:
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
    slope_params: tuple[float, float, float] = (0.0, 0.4, 1.0),
) -> tuple[Path, Path]:
    snv_df = _fs.extract_snvs(in_dir)
    sompy_data = out_dir / "sompy_data.csv"
    sompy_data.parent.mkdir(exist_ok=True, parents=True)
    snv_df.to_csv(sompy_data)
    recall_plot = _plot._generate_comparison_plot(
        df=snv_df,
        metric="recall2",
        slope_params=slope_params,
    )
    plot_path = Path(out_dir / "plot.png")
    recall_plot.savefig(plot_path)
    return sompy_data, plot_path
