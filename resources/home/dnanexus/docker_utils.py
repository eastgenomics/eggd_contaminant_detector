import io
import gzip
import tarfile
from pathlib import Path

import docker
from docker import DockerClient
from docker.models.containers import Container
from docker.types import Mount


def run_sompy(truth: str, query: str, image_name: str) -> Path:
    container = run_image(truth, query, image_name)
    container.wait()
    output = extract_stats(container, Path("out"))
    container.remove()
    return output


def run_image(truth: str, query: str, image_name: str) -> Container:
    client = load_image()
    src = "/home/dnanexus/in"
    dst = "/opt/data"
    mount_point = make_bindmount(src, dst)
    container = client.containers.run(
        image=image_name,
        mounts=[mount_point],
        command=[f"{dst}/{truth}", f"{dst}/{query}"],
        detach=True,
        auto_remove=False,
    )
    return container


def load_image() -> DockerClient:
    p = Path("/image/")
    image = next(p.glob("*.tar.gz"))
    client = docker.from_env()
    with gzip.open(image, "rb") as f:
        client.images.load(f)
    return client


def make_bindmount(src: str, dst: str) -> Mount:
    return Mount(source=src, target=dst, type="bind")


def extract_stats(container: Container, output_path: Path) -> Path:
    file_obj = io.BytesIO()
    bits, stat = container.get_archive("/opt/output")
    for chunk in bits:
        file_obj.write(chunk)
    file_obj.seek(0)
    output_path.mkdir(exist_ok=True)
    with tarfile.open(fileobj=file_obj) as tar:
        stats_csv = [f for f in tar.getmembers() if f.name.endswith(".stats.csv")][0]
        # it's a tarInfo object, so it has a "name" attribute
        stats_csv.name = Path(stats_csv.name).name
        tar.extract(stats_csv, path=output_path)
    stats_path = next(output_path.glob("*.stats.csv"))
    return stats_path
