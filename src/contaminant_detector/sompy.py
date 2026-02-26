from pathlib import Path

from . import docker_utils

def run_sompy(image: Path, truth: Path, query: Path, reference: Path) -> Path:
    src = Path(truth).absolute().parent
    dst = Path("/opt/data")
    mount = docker_utils.make_bindmount(src, dst)
    output = Path("/opt/output")
    samples = truth.stem.rstrip(".vcf") + "_" + query.stem.rstrip(".vcf")
    command = ["/opt/bin/som.py", "--no-count-unk", "--include-nonpass", "--no-fixchr-truth", "--no-fixchr-query", "-o", str(output / samples), "--reference", str(reference), str(dst / truth.name), str(dst / query.name)]
    container = docker_utils.run_image_from_archive(image=image, command=command, mounts=[mount])
    container.wait()
    stats_path = extract_stats(container)
    container.remove()
    return stats_path

def extract_stats(container: Container) -> Path:
    src = Path("/opt/output/")
    extracted = docker_utils.extract_folder(container, src)
    stats_path = next(extracted.glob("*.stats.csv"))
    return stats_path