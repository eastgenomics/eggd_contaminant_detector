import io
import gzip
import docker
import tarfile
from pathlib import Path

def load_image():
    p = Path("/image/")
    image = next(p.glob("*.tar.gz"))
    client = docker.from_env()
    with gzip.open(image, "rb") as f:
        client.images.load(f)
    return client

def run_image(client, image_name, truth, query, mountpoint):
    container = client.containers.run(
            image=image_name,
            mounts=[mountpoint],
            command=[truth, query],
            detach=True,
            auto_remove=False
            )
    return container

def extract_output(container, output_path):
    file_obj = io.BytesIO()
    bits, stat = container.get_archive(output_path)
    for chunk in bits:
        file_obj.write(chunk)
    file_obj.seek(0)
    with tarfile.open(fileobj=file_obj) as tar:
        stats_csv = [f for f in tar.getmembers() if f.name.endswith(".stats.csv")][0]
        # it's a tarInfo object, so it has a "name" attribute
        stats_csv.name = Path(stats_csv.name).name
        tar.extract(stats_csv, path=".")
    output = next(Path(".").glob("*.stats.csv"))
    container.remove()
    return output
