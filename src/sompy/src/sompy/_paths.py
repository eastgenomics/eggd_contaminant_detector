import re
from pathlib import Path

import ambergris
from docker.types import Mount


def _resolve_in_dir(*tool_args: Path, **tool_kwargs: Path) -> Path:
    all_args = list(tool_args) + list(tool_kwargs.values())
    paths = [Path(arg) for arg in all_args if isinstance(arg, (str, Path))]
    common_parent = _resolve_common_parent(paths)
    return Path(common_parent)


def _resolve_common_parent(paths: list[Path]) -> str:
    resolved_paths = [p.resolve() for p in paths]
    return _get_next_in_tree(resolved_paths)


def _get_next_in_tree(paths: list[Path], current_root: str = "") -> str:
    parts = [p.parts for p in paths]
    roots = ["/" + p[0] for p in parts]
    stems = [Path("/".join(p[1:])) for p in parts]
    roots_set = set(roots)
    if len(roots_set) == 1:
        current_root = current_root + str(list(roots_set)[0])
        if current_root == "//":
            final_root = _get_next_in_tree(stems, "")
        else:
            final_root = _get_next_in_tree(stems, current_root)
    else:
        return current_root
    return final_root


def _get_out_dir(*mounts: Mount, key: str = "Source") -> Path:
    return next(Path(m[key]) for m in mounts if m["Target"] == "/out")


def _remove_vcf_extension(vcf: Path | str) -> str:
    vcf_name = Path(vcf).name
    return re.sub(r"(\.sorted)?\.(?:g\.)?g?vcf(?:\.gz)?$", "", vcf_name)


def make_mounts(in_dir: str | Path, out_dir: str | Path) -> list[Mount]:
    host_in = Path(in_dir)
    cont_in = Path("/in")
    host_out = Path(out_dir)
    host_out.mkdir(parents=True, exist_ok=True)
    cont_out = Path("/out")
    mounts = ambergris.make_bindmounts((host_in, cont_in), (host_out, cont_out))
    return mounts