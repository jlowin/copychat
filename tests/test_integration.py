from pasteurize.core import scan_directory
from pasteurize.format import format_files


def test_full_project_scan(sample_project):
    """Test scanning and formatting a full project structure."""
    files = scan_directory(
        sample_project,
        include=["py", "js", "css", "md", "yml", "sql", "ts"],
        diff_mode="full",
        verbose=True,
    )

    assert len(files) > 0
    assert any(f.name == "main.py" for f in files)
    assert any(f.name == "app.js" for f in files)

    # Test that ignored files are not included by default
    assert not any(f.name == ".env" for f in files)
    assert not any(f.suffix == ".pyc" for f in files)

    # Format the files
    result = format_files(list(files))

    # Check that the output contains expected content
    assert "def main():" in result
    assert "function App()" in result
    assert "CREATE TABLE users" in result
