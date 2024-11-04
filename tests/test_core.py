import pytest
from copychat.core import (
    find_gitignore,
    DiffMode,
    is_glob_pattern,
    resolve_paths,
    scan_directory,
    scan_files,
)
from pathlib import Path


def test_diff_mode_enum():
    """Test DiffMode enum values."""
    assert DiffMode.FULL.value == "full"
    assert DiffMode.FULL_WITH_DIFF.value == "full-with-diff"
    assert DiffMode.CHANGED_WITH_DIFF.value == "changed-with-diff"
    assert DiffMode.DIFF_ONLY.value == "diff-only"


def test_is_glob_pattern():
    """Test glob pattern detection."""
    assert is_glob_pattern("*.py")
    assert is_glob_pattern("src/**/*.js")
    assert is_glob_pattern("test/*")
    assert not is_glob_pattern("src/main.py")
    assert not is_glob_pattern("path/to/file")


def test_resolve_paths(tmp_path):
    """Test path resolution with glob patterns."""
    # Create test files
    (tmp_path / "test1.py").touch()
    (tmp_path / "test2.py").touch()
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").touch()
    (tmp_path / "src" / "util.js").touch()

    # Test glob resolution
    paths = resolve_paths(["*.py", "src/**/*.py"], base_path=tmp_path)
    assert len(paths) == 3
    assert tmp_path / "test1.py" in paths
    assert tmp_path / "test2.py" in paths
    assert tmp_path / "src" / "main.py" in paths

    # Test mixed glob and regular paths
    paths = resolve_paths(["src", "*.py"], base_path=tmp_path)
    assert len(paths) == 3
    assert tmp_path / "src" in paths


@pytest.fixture
def git_repo(tmp_path):
    """Create a temporary git repository with a .gitignore file."""
    gitignore = tmp_path / ".gitignore"
    gitignore.write_text("*.pyc\n__pycache__/\n")
    return tmp_path


def test_scan_with_glob_patterns():
    # Create test directory and files if they don't exist
    test_dir = Path("tests/data")
    test_dir.mkdir(parents=True, exist_ok=True)

    with open(test_dir / "test1.txt", "w") as f:
        f.write("This is a test file")
    with open(test_dir / "test2.md", "w") as f:
        f.write("This is another test file")

    files = scan_files(["*.txt", "*.md"], test_dir)
    assert len(files) == 2


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


def test_scan_with_recursive_glob(tmp_path):
    """Test scanning with recursive glob patterns."""
    # Create nested test files
    (tmp_path / "test1.py").write_text("print('test1')")
    deep_dir = tmp_path / "very" / "deep" / "nested"
    deep_dir.mkdir(parents=True)
    (deep_dir / "test2.py").write_text("print('test2')")
    (deep_dir / "test.js").write_text("console.log('test')")

    # Test recursive glob pattern
    files = scan_directory(
        tmp_path, include=["py"]
    )  # Changed from tmp_path / "**/*.py"
    assert len(files) == 2
    assert any("test1.py" in str(p) for p in files)
    assert any("test2.py" in str(p) for p in files)

    # Test from within subdirectory
    subdir_files = scan_directory(
        tmp_path / "very", include=["py"]
    )  # Changed from tmp_path / "very" / "**/*.py"
    assert len(subdir_files) == 1
    assert any("test2.py" in str(p) for p in subdir_files)


def test_scan_single_file(tmp_path):
    """Test scanning a single file."""
    # Create a test file
    test_file = tmp_path / "test.py"
    test_file.write_text("print('hello world')")

    # Create some other files that shouldn't be included
    (tmp_path / "other.py").write_text("print('other')")
    (tmp_path / "test.js").write_text("console.log('test')")

    # Test scanning just the single file
    files = scan_directory(test_file, include=["py"])

    # Should only contain our specific file
    assert len(files) == 1
    assert test_file in files
    assert files[test_file] == "print('hello world')"

    # Test with non-matching extension filter
    files = scan_directory(test_file, include=["js"])
    assert len(files) == 0

    # Test with non-existent file
    files = scan_directory(tmp_path / "nonexistent.py", include=["py"])
    assert len(files) == 0
