import pytest
from copychat.core import find_gitignore, DiffMode


def test_diff_mode_enum():
    """Test DiffMode enum values."""
    assert DiffMode.FULL.value == "full"
    assert DiffMode.FULL_WITH_DIFF.value == "full-with-diff"
    assert DiffMode.CHANGED_WITH_DIFF.value == "changed-with-diff"
    assert DiffMode.DIFF_ONLY.value == "diff-only"


@pytest.fixture
def git_repo(tmp_path):
    """Create a temporary git repository with a .gitignore file."""
    gitignore = tmp_path / ".gitignore"
    gitignore.write_text("*.pyc\n__pycache__/\n")
    return tmp_path


def test_find_gitignore_exists(git_repo):
    """Test finding .gitignore in current directory."""
    result = find_gitignore(git_repo)
    assert result == git_repo / ".gitignore"


def test_find_gitignore_parent(git_repo):
    """Test finding .gitignore in parent directory."""
    child_dir = git_repo / "subdir"
    child_dir.mkdir()
    result = find_gitignore(child_dir)
    assert result == git_repo / ".gitignore"


def test_find_gitignore_not_found(tmp_path):
    """Test behavior when no .gitignore is found."""
    result = find_gitignore(tmp_path)
    assert result is None
