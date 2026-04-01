from pathlib import Path
from typing import Optional

import sompy  # type: ignore
import ambergris  # type: ignore

from . import _fs
from . import _heredocs
from . import _plot


def run_sompy_batch(
    out_dir: Path, sompy_image: Path, bcftools_image: Path, data_dir: Path
) -> Path:
    mounts = ambergris.make_bindmounts(
        (data_dir, Path("/in")),
        (out_dir, Path("/out")),
    )
    _fs.setup_ref_from_data_dir(data_dir)
    steps = (
        (bcftools_image, _heredocs.bcftools_norm()),
        (bcftools_image, _heredocs.bcftools_sort()),
        (sompy_image, _heredocs.sompy()),
    )
    for image, cmd in steps:
        with ambergris.open_container(image, *mounts) as container:
            ambergris.exec_command(container, ["/bin/bash", "-c", cmd])
    return out_dir


def run_sompy_pair(
    out_dir: Path,
    sompy_image: Path,
    bcftools_image: Path,
    truth: Path,
    query: Path,
    reference: Path,
    panel_bed: Optional[Path] = None,
) -> Path:
    vcfs = {"truth": truth, "query": query}
    norm_dir = out_dir / "normalised"
    norm_dir.mkdir(parents=True, exist_ok=True)
    sort_dir = out_dir / "sorted"
    sort_dir.mkdir(parents=True, exist_ok=True)

    for group, vcf in vcfs.items():
        normalised_vcf = sompy.run_bcftools_norm(
            bcftools_image, out_dir=norm_dir, vcf=vcf, reference=reference
        )
        vcfs[f"sorted_{group}"] = sompy.run_bcftools_sort(
            bcftools_image, out_dir=sort_dir, vcf=normalised_vcf
        )

    kwargs = {
        "sompy_image": sompy_image,
        "out_dir": out_dir,
        "truth": vcfs["sorted_truth"],
        "query": vcfs["sorted_query"],
        "reference": reference,
    }
    if panel_bed:
        kwargs["panel_bed"] = panel_bed

    sompy.run_sompy(**kwargs)
    sompy_output = next(out_dir.glob("*.stats.csv"))
    return sompy_output


def plot_recall(
    sompy_files: list[Path],
    out_dir: Path,
    slope_params: tuple[float, float, float] = (0.0, 0.4, 1.0),
) -> tuple[Path, Path]:
    sompy_in_dir = sompy_files[0].parent
    snv_df = _fs.extract_snvs(sompy_in_dir)
    sompy_data = out_dir / "sompy_data.csv"
    sompy_data.parent.mkdir(exist_ok=True, parents=True)
    snv_df.to_csv(sompy_data)
    recall_plot = _plot._generate_comparison_plot(
        df=snv_df,
        metric="recall2",
        # Average recall value between non-contaminated samples is 0.2
        # so setting beginning of colour ramp-up to be double that
        slope_params=slope_params,
    )
    plot_path = Path(out_dir / "plot.png")
    recall_plot.savefig(plot_path)
    return sompy_data, plot_path