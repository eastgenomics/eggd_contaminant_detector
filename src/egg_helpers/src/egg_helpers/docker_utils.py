from pathlib import Path
from typing import Annotated, Tuple

import docker
from docker import DockerClient
from docker.models.containers import Container
from docker.types import Mount

DIGEST_PATTERN = r"^sha256:[a-fA-F0-9]{64}$"
ImageID = Annotated[str, "Docker SHA256 Digest", DIGEST_PATTERN]

def run_image_from_archive(image: ImageID, command: list[str], mounts: list[Mount]) -> Container:
    """Loads a Docker image from an archive and runs it as a detached container.

    This is a high-level wrapper that first ensures the image is available in 
    the local Docker daemon before initiating a container run.

    Args:
        image: Path to the gzipped Docker image archive (.tar.gz) or a string path.
        command: The command or list of commands to execute inside the container.
        mounts: A list of docker.types.Mount objects defining volume bindings.

    Returns:
        A docker.models.containers.Container object in a detached state.
    """
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
    """Loads a gzipped Docker image archive into the local Docker daemon.

    Args:
        image: Path to the gzipped image file.

    Returns:
        A tuple containing:
            - image_id: The SHA256 digest of the loaded image (ImageID).
            - client: An initialized DockerClient instance from the environment.

    Raises:
        FileNotFoundError: If the image path does not exist.
        docker.errors.DockerException: If the Docker daemon is unreachable.
    """
    client = docker.from_env(timeout=300)
    client.api.timeout = 300
    with open(image, "rb") as f:
        loaded_images = client.images.load(f)
    image_id = loaded_images[0].id
    return image_id, client

def make_bindmounts(*bindings: Tuple[Path, Path]) -> list[Mount]:
    """Creates a list of Docker bind mounts from multiple source/target pairs.

    Args:
        *bindings: Variable length argument of tuples, where each tuple 
            contains (source_path, target_path).

    Returns:
        A list of initialized docker.types.Mount objects.
    """
    return [make_bindmount(*binding) for binding in bindings]

def make_bindmount(src: Path, dst: Path) -> Mount:
    """Creates a single Docker bind mount object.

    Handles path expansion (e.g., '~') and converts paths to absolute 
    to ensure the Docker daemon can resolve them correctly.

    Args:
        src: The host directory or file to mount.
        dst: The destination path inside the container.

    Returns:
        A Mount object configured with the 'bind' type.
    """
    return Mount(source=str(src.expanduser().absolute()), target=str(dst.expanduser().absolute()), type="bind")