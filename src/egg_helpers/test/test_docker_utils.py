import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from docker.types import Mount
from egg_helpers.docker_utils import load_image, run_image_from_archive, make_bindmount

@pytest.fixture
def mock_docker() -> MagicMock:
    """Mocks the entire docker-py client."""
    with patch("docker.from_env") as mock_env:
        mock_client = MagicMock()
        mock_env.return_value = mock_client
        yield mock_client

def test_make_bindmount() -> None:
    src = Path("~/data")
    dst = Path("/app/data")
    mount = make_bindmount(src, dst)
    
    assert isinstance(mount, Mount)
    assert mount["Target"] == "/app/data"
    assert Path(mount["Source"]).is_absolute()

def test_load_image(mock_docker: MagicMock, tmp_path: Path) -> None:
    # Setup: Create a fake gzip file so gzip.open doesn't fail
    fake_img = tmp_path / "test_image.tar.gz"
    fake_img.write_bytes(b"not-really-gzip-data")
    
    # Mock the return value of client.images.load()
    mock_image = MagicMock()
    mock_image.id = "sha256:1234567890abcdef"
    mock_docker.images.load.return_value = [mock_image]

    # We must mock gzip.open because we wrote plain text in fake_img, not real gzip
    with patch("gzip.open", MagicMock()):
        img_id, client = load_image(fake_img)

    assert img_id == "sha256:1234567890abcdef"
    mock_docker.images.load.assert_called_once()

def test_run_image_from_archive(mock_docker):
    # We patch 'load_image' so we don't have to deal with the filesystem here
    with patch("egg_helpers.docker_utils.load_image") as mock_load:
        mock_load.return_value = ("sha256:fake", mock_docker)
        
        mock_container = MagicMock()
        mock_docker.containers.run.return_value = mock_container
        
        container = run_image_from_archive(
            image="dummy.tar.gz",
            command=["ls"],
            mounts=[]
        )
        
        mock_docker.containers.run.assert_called_once_with(
            image="sha256:fake",
            mounts=[],
            command=["ls"],
            detach=True,
            auto_remove=False
        )
        assert container == mock_container