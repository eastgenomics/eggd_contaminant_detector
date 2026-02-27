import re
from pathlib import Path

from . import docker_utils

def clean_sample_name(vcf: Path) -> str:
    return re.sub(r'\.(?:g\.)?g?vcf(?:\.gz)?$', "", vcf.name)

def run_sompy(image: Path, truth: Path, query: Path, reference: Path) -> Path:
    host_in = Path(truth).absolute().parent
    host_out = Path("out").absolute()
    host_out.mkdir(parents=True, exist_ok=True)

    cont_in = Path("/in")
    cont_out = Path("/out")

    in_mount = docker_utils.make_bindmount(host_in, cont_in)
    out_mount = docker_utils.make_bindmount(host_out, cont_out)
    mounts = [in_mount, out_mount]

    truth_sample = clean_sample_name(truth)
    query_sample = clean_sample_name(query)
    samples = f"{truth_sample}_{query_sample}"

    command = [
        "/opt/bin/som.py",
        "--no-count-unk",
        "--no-fixchr-truth", 
        "--include-nonpass", 
        "--no-fixchr-query", 
        "-o", str(cont_out / samples), 
        "--reference", str(cont_in / reference.relative_to(host_in)), 
        str(cont_in / truth.name), 
        str(cont_in / query.name)
        ]
    container = docker_utils.run_image_from_archive(image=image, command=command, mounts=mounts)
    result = container.wait()
    if result.get("StatusCode") != 0:
        print(container.logs().decode())
        raise RuntimeError(f"Sompy failed with exit code {result['StatusCode']}")
    stats_path = next(host_out.glob("*.stats.csv")).resolve()
    container.remove()
    return stats_path