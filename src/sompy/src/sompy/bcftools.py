from pathlib import Path
from docker.types import Mount
from egg_helpers import docker_utils
from . import utils

def sort(vcf: Path, out_dir: Path, image: Path, *mounts: Mount) -> Path:
    cmd, sorted_vcf = bcftools_sort_cmd(vcf, out_dir)
    docker_utils.run_container(image, cmd, *mounts)
    return sorted_vcf

@docker_utils.make_io_relative_to_container
def bcftools_sort_cmd(vcf: Path, in_mount: Mount, out_mount: Mount) -> list[str]:
    vcf_name = utils.remove_vcf_extension(vcf)
    out_dir = Path(out_mount["Target"])
    sorted_vcf = out_dir / f"{vcf_name}.sorted.gz" 
    cmd = [
        "bcftools", "sort", "-W=tbi", "-Oz", "-o", sorted_vcf, vcf
    ]
    return cmd, sorted_vcf

def norm(vcf: Path, out_dir: Path, image: Path, *mounts: Mount) -> Path:
    cmd, normalised_vcf = bcftools_norm_cmd(vcf, out_dir)
    docker_utils.run_container(image, cmd, *mounts)
    return normalised_vcf

@docker_utils.make_io_relative_to_container
def bcftools_norm_cmd(vcf: Path, out_dir: Path, reference: Path, *mounts: Mount) -> list[str]:
    vcf_name = utils.remove_vcf_extension(vcf)
    normalised_vcf = out_dir / f"{vcf_name}.normalised.gz" 
    cmd = [
        "bcftools", "norm", "-m-any" "-f", reference, vcf,
        "|",
        "bcftools", "norm", "-d", "any", "-W=tbi", "Oz", "-o", normalised_vcf
    ]
    return cmd, normalised_vcf
