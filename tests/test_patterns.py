from copychat.patterns import (
    DEFAULT_EXTENSIONS,
    EXCLUDED_DIRS,
    EXCLUDED_PATTERNS,
)


def test_default_extensions():
    """Test default extensions are properly defined."""
    assert isinstance(DEFAULT_EXTENSIONS, set)
    assert "py" in DEFAULT_EXTENSIONS
    assert "js" in DEFAULT_EXTENSIONS
    assert "md" in DEFAULT_EXTENSIONS


def test_excluded_dirs():
    """Test excluded directories are properly defined."""
    assert isinstance(EXCLUDED_DIRS, set)
    assert ".git" in EXCLUDED_DIRS
    assert "node_modules" in EXCLUDED_DIRS
    assert "__pycache__" in EXCLUDED_DIRS


def test_excluded_patterns():
    """Test excluded patterns are properly defined."""
    assert isinstance(EXCLUDED_PATTERNS, set)
    assert "*.pyc" in EXCLUDED_PATTERNS
    assert "*.log" in EXCLUDED_PATTERNS
    assert ".env" in EXCLUDED_PATTERNS
