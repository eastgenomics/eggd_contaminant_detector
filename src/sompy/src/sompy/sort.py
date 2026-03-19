from pathlib import Path
from docker.types import Mount
from egg_helpers import docker_utils
from . import utils

def run_bcftools_sort(image: Path, vcf: Path, in_mount: Mount, out_mount: Mount) -> Path:
    command = _mounted_sort_cmd(vcf, in_mount, out_mount)
    container = docker_utils.run_from_archive(image=image, command=command, mounts=[in_mount, out_mount])
    try:
        result = container.wait()
        if result.get("StatusCode") != 0:
            print(container.logs().decode())
            raise RuntimeError(f"bcftools sort failed with exit code {result['StatusCode']}")
        vcf_name = utils.remove_vcf_extension(vcf)
        sorted_path = Path(out_mount["Source"]) / f"{vcf_name}.sorted.gz"
        return sorted_path.resolve()
    finally:
        container.remove()

def _mounted_sort_cmd(vcf: Path, in_mount: Mount, out_mount: Mount) -> list[str]:
    c_out = Path(out_mount["Target"])
    c_vcf = utils.get_container_path(vcf, in_mount, out_mount)
    command = _sort_cmd(c_vcf, c_out)
    return command

def _sort_cmd(vcf: Path, out_dir: Path) -> list[str]:
    vcf_name = utils.remove_vcf_extension(vcf)
    sorted_vcf = out_dir / f"{vcf_name}.sorted.gz" 
    cmd = [
        "/opt/hap.py/bin/bcftools",
        "sort",
        "-W=tbi",
        "-Oz",
        "-o", str(sorted_vcf),
        str(vcf)
    ]
    return cmd