import gzip
import tarfile
from pathlib import Path
from typing import Annotated, Tuple

import docker
from docker import DockerClient
from docker.models.containers import Container
from docker.types import Mount

#### * ~ <3  T y p e   H i n t i n g  <3 ~ * ####

DIGEST_PATTERN = r"^sha256:[a-fA-F0-9]{64}$"
ImageID = Annotated[str, "Docker SHA256 Digest", DIGEST_PATTERN]

#### * ~ <3  T h a n k s  <3 ~ * ####

def run_image_from_archive(image: ImageID, command: list[str], mounts: list[Mount]) -> Container:
    image_id, client = load_image(image)
    container = client.containers.run(
        image=image_id,
        mounts=mounts,
        command=command,
        detach=True,
        auto_remove=False,
    )
    return container

def load_image(image: Path|str) -> Tuple[ImageID, DockerClient]:
    client = docker.from_env()
    with gzip.open(image, "rb") as f:
        loaded_images = client.images.load(f)
    image_id = loaded_images[0].id
    return image_id, client

def make_bindmounts(*bindings: Tuple[Path, Path]):
    return [make_bindmount(*binding) for binding in bindings]

def make_bindmount(src: Path, dst: Path) -> Mount:
    return Mount(source=str(src.expanduser().absolute()), target=str(dst.expanduser().absolute()), type="bind")