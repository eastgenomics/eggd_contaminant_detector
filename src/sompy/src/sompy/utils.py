import re
from pathlib import Path
from docker.types import Mount
from egg_helpers import docker_utils

def remove_vcf_extension(vcf: Path | str) -> str:
    """Removes complex VCF extensions including .sorted and .g variations."""
    vcf_name = Path(vcf).name
    return re.sub(r'(\.sorted)?\.(?:g\.)?g?vcf(?:\.gz)?$', "", vcf_name)

def make_mounts(in_dir: Path, out_dir: Path) -> list[Mount, Mount]:
    host_in = in_dir
    cont_in = Path("/in")
    host_out = out_dir
    host_out.mkdir(parents=True, exist_ok=True)
    cont_out = Path("/out")
    mounts = docker_utils.make_bindmounts((host_in, cont_in), (host_out, cont_out))
    return mounts