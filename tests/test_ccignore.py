"""Tests for .ccignore functionality."""

import pytest
from copychat.core import (
    find_ccignore_files,
    get_ccignore_spec,
    scan_directory,
)


@pytest.fixture
def ccignore_test_dir(tmp_path):
    """Create a test directory structure with .ccignore files."""
    # Root directory with .ccignore
    root_ccignore = tmp_path / ".ccignore"
    root_ccignore.write_text("*.log\n")

    # Create subdirectory with its own .ccignore
    subdir = tmp_path / "subdir"
    subdir.mkdir()
    subdir_ccignore = subdir / ".ccignore"
    subdir_ccignore.write_text("*.json\n")

    # Create nested subdirectory with its own .ccignore
    nested_subdir = subdir / "nested"
    nested_subdir.mkdir()
    nested_ccignore = nested_subdir / ".ccignore"
    nested_ccignore.write_text("*.md\n")

    # Create test files
    (tmp_path / "root.txt").write_text("root text file")
    (tmp_path / "root.log").write_text("root log file")
    (tmp_path / "root.json").write_text("root json file")
    (tmp_path / "root.md").write_text("root md file")

    (subdir / "subdir.txt").write_text("subdir text file")
    (subdir / "subdir.log").write_text("subdir log file")
    (subdir / "subdir.json").write_text("subdir json file")
    (subdir / "subdir.md").write_text("subdir md file")

    (nested_subdir / "nested.txt").write_text("nested text file")
    (nested_subdir / "nested.log").write_text("nested log file")
    (nested_subdir / "nested.json").write_text("nested json file")
    (nested_subdir / "nested.md").write_text("nested md file")

    return tmp_path


def test_find_ccignore_files(ccignore_test_dir):
    """Test finding all .ccignore files that apply to a path."""
    nested_dir = ccignore_test_dir / "subdir" / "nested"

    # Should find 3 .ccignore files, from most specific to most general
    result = find_ccignore_files(nested_dir)
    assert len(result) == 3

    # Check the order - should be from most specific to most general
    assert result[0][0] == nested_dir / ".ccignore"
    assert result[1][0] == ccignore_test_dir / "subdir" / ".ccignore"
    assert result[2][0] == ccignore_test_dir / ".ccignore"

    # Test with path that has no .ccignore
    empty_dir = ccignore_test_dir / "empty_dir"
    empty_dir.mkdir()
    result = find_ccignore_files(empty_dir)
    assert len(result) == 1
    assert result[0][0] == ccignore_test_dir / ".ccignore"


def test_get_ccignore_spec(ccignore_test_dir):
    """Test generating PathSpec from .ccignore files."""
    # Root directory should only exclude .log files
    root_spec = get_ccignore_spec(ccignore_test_dir)
    assert root_spec.match_file("test.log")
    assert not root_spec.match_file("test.json")
    assert not root_spec.match_file("test.md")

    # Subdirectory should exclude .log and .json files
    subdir_spec = get_ccignore_spec(ccignore_test_dir / "subdir")
    assert subdir_spec.match_file("test.log")
    assert subdir_spec.match_file("test.json")
    assert not subdir_spec.match_file("test.md")

    # Nested subdirectory should exclude .log, .json, and .md files
    nested_spec = get_ccignore_spec(ccignore_test_dir / "subdir" / "nested")
    assert nested_spec.match_file("test.log")
    assert nested_spec.match_file("test.json")
    assert nested_spec.match_file("test.md")


def test_scan_directory_with_ccignore(ccignore_test_dir):
    """Test that scan_directory respects .ccignore patterns."""
    # Scan the root directory - should exclude .log files
    files = scan_directory(ccignore_test_dir, include=["txt", "json", "md", "log"])
    paths = {str(f) for f in files}

    # Root dir - .log should be excluded, others included
    assert not any(p.endswith("root.log") for p in paths)
    assert any(p.endswith("root.txt") for p in paths)
    assert any(p.endswith("root.json") for p in paths)
    assert any(p.endswith("root.md") for p in paths)

    # Subdir - .log and .json should be excluded, others included
    assert not any(p.endswith("subdir.log") for p in paths)
    assert not any(p.endswith("subdir.json") for p in paths)
    assert any(p.endswith("subdir.txt") for p in paths)
    assert any(p.endswith("subdir.md") for p in paths)

    # Nested subdir - .log, .json, and .md should be excluded, others included
    assert not any(p.endswith("nested.log") for p in paths)
    assert not any(p.endswith("nested.json") for p in paths)
    assert not any(p.endswith("nested.md") for p in paths)
    assert any(p.endswith("nested.txt") for p in paths)


def test_ccignore_with_extra_patterns(ccignore_test_dir):
    """Test that extra exclude patterns work with .ccignore."""
    # Add extra exclude pattern for .txt files
    spec = get_ccignore_spec(ccignore_test_dir, extra_patterns=["*.txt"])

    # Should exclude both .log files (from .ccignore) and .txt files (from extra patterns)
    assert spec.match_file("test.log")
    assert spec.match_file("test.txt")
    assert not spec.match_file("test.json")
