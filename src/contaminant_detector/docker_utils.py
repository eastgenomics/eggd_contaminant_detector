import json
import gzip
import tarfile
from functools import singledispatch
from pathlib import Path
from typing import Annotated, Tuple, TypeAlias

import docker
from docker import DockerClient
from docker.models.containers import Container
from docker.types import Mount

#### * ~ <3  T y p e   H i n t i n g  <3 ~ * ####

DIGEST_PATTERN = r"^sha256:[a-fA-F0-9]{64}$"
TAG_PATTERN = r"^[a-z0-9]+(?:[._-][a-z0-9]+)*[:][\w.-]+$"

ImageDigest = Annotated[str, "Docker SHA256 Digest", DIGEST_PATTERN]
ImageTag = Annotated[str, "Standard Image Name (repo:tag)", TAG_PATTERN]

DockerImageRef: TypeAlias = ImageDigest | ImageTag

#### * ~ <3  T h a n k s  <3 ~ * ####

def run_image_from_archive(image: Path, command: list[str], mounts: list[Mount]) -> Container:
    image_ref, client = load_image(image)
    container = client.containers.run(
        image=str(image_ref),
        mounts=mounts,
        command=command,
        detach=True,
        auto_remove=False,
    )
    return container

def load_image(image: Path|str) -> Tuple[DockerImageRef, DockerClient]:
    client = docker.from_env()
    image_ref = get_image_name_or_id(image)
    with gzip.open(image, "rb") as f:
        client.images.load(f)
    return image_ref, client

def get_image_name_or_id(image: Path|str) -> DockerImageRef:
    with tarfile.open(image, "r:gz") as tar:
        names = tar.getnames()
        m_file = tar.extractfile("manifest.json")
        manifest = json.load(m_file)
        try:
            # Hopefully image name is defined
            # This will follow the familiar convention - e.g., "ubuntu:latest"
            return manifest[0]["RepoTags"][0]
        except KeyError:
            # Docker images built against the legacy Docker Image Specification will contain a config file
            # that shares the name of the image's ID. For these, we can simply parse the ID from the config name.
            #
            # On the other hand, recent Docker images will be built against the more modern OCI (Open Container Image)
            # Specification. The contents are stored in a "blobs/" directory, which distinguishes OCI images from legacy
            # Docker images. In these cases, the image ID is more cumbersome to parse.
            # 
            # Therefore, to distinguish between the two, we rely on the presence of the "blobs/" directory
            #
            # The only reason we do all of this is because client.images.load returns every image in your local registry,
            # not just the one you just loaded. If your compressed image is called 'image.tar.gz', there's no way to know
            # which one you just loaded, making this function necessary.
            # 
            # See the following for more details:
            #    Legacy Docker spec: https://github.com/moby/moby/blob/daa4618da826fb1de4fc2478d88196edbba49b2f/image/spec/v1.2.md
            #    OCI spec: https://github.com/opencontainers/distribution-spec/blob/91ba954eac70e40d63b2678421e7197cd33e0f2e/spec.md
            if "blobs" in names:
                # This is an OCI image. Hopefully there's an index.json.
                # If not, this is a bad image since neither the repo tags nor index are present.
                # Don't use it - exiting the program here is desired. We're okay with a traceback
                index = tar.extractfile("index.json").read()
                return index["manifests"][0]["digest"]
            else:
                # this is a legacy Docker image
                digest_id = manifest[0]["Config"].rstrip(".json")
                return f"sha256:{digest_id}"

def make_bindmounts(*bindings: Tuple[Path, Path]):
    return [make_bindmount(*binding) for binding in bindings]

def make_bindmount(src: Path, dst: Path) -> Mount:
    return Mount(source=str(src.expanduser().absolute()), target=str(dst.expanduser().absolute()), type="bind")

def extract_folder(container: Container, src: Path) -> Path:
    file_obj = io.BytesIO()
    bits, stat = container.get_archive(src)
    for chunk in bits:
        file_obj.write(chunk)
    file_obj.seek(0)
    with tarfile.open(fileobj=file_obj) as tar:
        tar.extractall()
    return Path(".").absolute() / src.stem