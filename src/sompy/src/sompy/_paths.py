import os
import re
from pathlib import Path

import ambergris
from docker.types import Mount


def _resolve_in_dir(*tool_args: Path, **tool_kwargs: Path) -> Path:
    all_args = list(tool_args) + list(tool_kwargs.values())
    paths = [Path(arg) for arg in all_args if isinstance(arg, (str, Path))]
    if len(paths) == 1:
        common_parent = paths[0].parent
    else:
        common_parent = os.path.commonpath(paths)
    return Path(common_parent).resolve()


def _get_out_dir(*mounts: Mount, key: str = "Source") -> Path:
    return next(Path(m[key]) for m in mounts if m["Target"] == "/out")


def _remove_vcf_extension(vcf: Path | str) -> str:
    vcf_name = Path(vcf).name
    return re.sub(r"(\.sorted)?\.(?:g\.)?g?vcf(?:\.gz)?$", "", vcf_name)


def _make_mounts(in_dir: str | Path, out_dir: str | Path) -> list[Mount]:
    host_in = Path(in_dir)
    cont_in = Path("/in")
    host_out = Path(out_dir)
    host_out.mkdir(parents=True, exist_ok=True)
    cont_out = Path("/out")
    mounts: list[Mount] = ambergris.make_bindmounts(
        (host_in, cont_in), (host_out, cont_out)
    )
    return mounts
