import pytest
import shutil
from copychat.sources import GitHubSource


@pytest.fixture
def temp_cache_dir(tmp_path):
    """Create temporary cache directory."""
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    yield cache_dir
    # Cleanup
    if cache_dir.exists():
        shutil.rmtree(cache_dir)


def test_github_source_init(temp_cache_dir):
    """Test GitHubSource initialization."""
    source = GitHubSource("owner/repo", cache_dir=temp_cache_dir)
    assert source.repo_path == "owner/repo"
    assert source.clone_url == "https://github.com/owner/repo.git"
    assert source.repo_dir == temp_cache_dir / "owner_repo"


def test_github_source_fetch(temp_cache_dir):
    """Test fetching a real public repository."""
    source = GitHubSource("prefecthq/prefect", cache_dir=temp_cache_dir)
    repo_dir = source.fetch()

    assert repo_dir.exists()
    assert (repo_dir / ".git").exists()
    assert (repo_dir / "README.md").exists()

    # Test update of existing repo
    repo_dir = source.fetch()  # Should use cached version
    assert repo_dir.exists()


def test_github_source_cleanup(temp_cache_dir):
    """Test repository cleanup."""
    source = GitHubSource("prefecthq/prefect", cache_dir=temp_cache_dir)
    source.fetch()
    assert source.repo_dir.exists()

    source.cleanup()
    assert not source.repo_dir.exists()
