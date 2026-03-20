from functools import wraps
from pathlib import Path
from contextlib import contextmanager
from typing import Annotated, Callable, Iterator, Tuple, Optional

import docker
from docker import DockerClient
from docker.models.containers import Container
from docker.types import Mount

DIGEST_PATTERN = r"^sha256:[a-fA-F0-9]{64}$"
ImageID = Annotated[str, "Docker SHA256 Digest", DIGEST_PATTERN]

@contextmanager
def start_container(image: Path|str, mounts: Optional[list[Mount]]=None) -> Iterator[Container]:
    """Starts a container for use with docker exec inputs."""
    with _start_container(image=image, command=["tail", "-f", "/dev/null"], mounts=mounts) as container:
        yield container

def run_container(image: Path|str, command: list[str], mounts=list[Mount]) -> Iterator[Container]:
    with _start_container(image=image, command=command, mounts=mounts) as container:
        yield container
        result = container.wait()
        status_code = result["StatusCode"]
        if status_code != 0:  
            print(container.logs().decode())
            raise RuntimeError(f"Container failed with exit code {status_code}")

@contextmanager
def _start_container(image: Path|str, command: list[str], mounts: Optional[list[Mount]]=None) -> Iterator[Container]:
    container = _run_from_archive(image, command=command, mounts=mounts)
    try:
        yield container
    finally:
        container.stop()
        container.remove()

def _run_from_archive(image: Path|str, command: Optional[list[str]]=None, mounts: Optional[list[Mount]]=None) -> Container:
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
    kwargs = {
        "image": image_id,
        "detach": True,
        "auto_remove": False
    }
    if command:
        kwargs["command"] = command
    if mounts:
        kwargs["mounts"] = mounts

    container = client.containers.run(**kwargs)
    return container

def load_image(image: Path|str, timeout: int=300) -> Tuple[ImageID, DockerClient]:
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
    client = docker.from_env()
    client.api.timeout = timeout
    with open(image, "rb") as f:
        loaded_images = client.images.load(f)
    if not loaded_images:
        raise ValueError(f"No images found in archive: {image}")
    image_id = loaded_images[0].id
    return image_id, client

def make_io_relative_to_container(func: Callable) -> Callable:
    @wraps(func)
    def wrapper(*args, mounts: list[Mount], **kwargs):
        new_args = [get_container_path(arg, *mounts) if isinstance(arg, Path) else arg for arg in args]
        new_kwargs = {k: (get_container_path(v, *mounts) if isinstance(v, Path) else v) for k, v in kwargs.items()}
        return func(*new_args, **new_kwargs)
    return wrapper

def get_container_path(file_path: Path, *mounts: Mount) -> Path:
    for mount in mounts:
        host = Path(mount["Source"])
        container = Path(mount["Target"])
        try:
            return container / file_path.relative_to(host)
        except ValueError:
            continue
    return file_path

def make_bindmounts(*bindings: Tuple[str|Path, str|Path]) -> list[Mount]:
    """Creates a list of Docker bind mounts from multiple source/target pairs.

    Args:
        *bindings: Variable length argument of tuples, where each tuple 
            contains (source_path, target_path).

    Returns:
        A list of initialized docker.types.Mount objects.
    """
    return [make_bindmount(*binding) for binding in bindings]

def make_bindmount(src: str|Path, dst: str|Path) -> Mount:
    """Creates a single Docker bind mount object.

    Handles path expansion (e.g., '~') and converts paths to absolute 
    to ensure the Docker daemon can resolve them correctly.

    Args:
        src: The host directory or file to mount.
        dst: The destination path inside the container.

    Returns:
        A Mount object configured with the 'bind' type.
    """
    src_exp = Path(src).expanduser().absolute()
    dst_exp = Path(dst).expanduser().absolute()
    return Mount(source=str(src_exp), target=str(dst_exp), type="bind")