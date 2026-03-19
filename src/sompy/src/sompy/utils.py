import re
from pathlib import Path
from docker.types import Mount

def get_container_path(host_path: Path, in_m: Mount, out_m: Mount) -> Path:
    h_in, c_in = Path(in_m["Source"]), Path(in_m["Target"])
    h_out, c_out = Path(out_m["Source"]), Path(out_m["Target"])

    if host_path.is_relative_to(h_in):
        return c_in / host_path.relative_to(h_in)
    return c_out / host_path.relative_to(h_out)

def remove_vcf_extension(vcf: Path | str) -> str:
    """Removes complex VCF extensions including .sorted and .g variations."""
    vcf_name = Path(vcf).name
    return re.sub(r'(\.sorted)?\.(?:g\.)?g?vcf(?:\.gz)?$', "", vcf_name)