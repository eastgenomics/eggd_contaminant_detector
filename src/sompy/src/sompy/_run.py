from pathlib import Path
from typing import Optional

import ambergris  # type: ignore

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
