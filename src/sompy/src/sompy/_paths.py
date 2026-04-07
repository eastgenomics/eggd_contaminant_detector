import os
from functools import wraps
from pathlib import Path
from typing import Optional

import ambergris
from docker.types import Mount


def resolve_in_dir(*tool_args: Optional[Path], **tool_kwargs: Optional[Path]) -> Path:
    all_args = list(tool_args) + list(tool_kwargs.values())
    paths = [Path(arg) for arg in all_args if isinstance(arg, (str, Path))]
    if len(paths) == 1:
        common_parent = paths[0].parent
    else:
        common_parent = Path(os.path.commonpath(paths))
    return common_parent.resolve()


def make_mounts(in_dir: str | Path, out_dir: str | Path) -> list[Mount]:
    host_in = Path(in_dir)
    cont_in = Path("/in")
    host_out = Path(out_dir)
    host_out.mkdir(parents=True, exist_ok=True)
    cont_out = Path("/out")
    mounts: list[Mount] = ambergris.make_bindmounts(
        (host_in, cont_in), (host_out, cont_out)
    )
    return mounts


@ambergris.make_io_relative_to_container
def write_paths(
    truths: list[Path],
    querys: list[Path],
    reference: Path,
    panel_bed: Optional[Path] = None,
    mounts: list[Mount] = [],
) -> None:
    """
    Write text files containing paths for the heredocs to use. Helps distinguish between file types if (for instance) truth
    and query samples are in the same directory, for whatever reason.
    """
    in_dir = Path(mounts[0]["Source"]).resolve()

    # ambergris.make_io_relative_to_container doesn't support lists of Paths... yet
    # Remove this when it does
    target = Path(mounts[0]["Target"]).resolve()
    c_truths = [target / vcf.relative_to(in_dir) for vcf in truths]
    c_querys = [target / vcf.relative_to(in_dir) for vcf in querys]

    path_maps = [
        {"filename": "truths.txt", "paths": c_truths},
        {"filename": "querys.txt", "paths": c_querys},
        {"filename": "reference.txt", "paths": [reference]},
    ]
    if panel_bed:
        path_maps.append({"filename": "panel.txt", "paths": [panel_bed]})
    for map in path_maps:
        with open(in_dir / str(map["filename"]), "w") as f:
            for p in map["paths"]:
                f.write(f"{str(p)}\n")


def get_output_path(out_dir: Path, pattern: str) -> Path:
    files = [f for f in out_dir.glob(pattern)]
    if len(files) == 1:
        output_path = files[0]
    elif len(files) > 1:
        output_path = Path(os.path.commonpath(files))
    else:
        raise ValueError("No output returned - something broke. Exiting...")
    return output_path.resolve()