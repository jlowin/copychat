from typer.testing import CliRunner
from copychat.cli import app
import pyperclip

runner = CliRunner()


def test_cli_default_behavior(tmp_path, monkeypatch):
    """Test that default behavior copies to clipboard."""
    # Create a test file
    test_file = tmp_path / "test.py"
    test_file.write_text("print('hello')")

    # Mock pyperclip.copy
    copied_content = []

    def mock_copy(text):
        copied_content.append(text)

    monkeypatch.setattr(pyperclip, "copy", mock_copy)

    # Run CLI
    result = runner.invoke(app, [str(tmp_path)])

    assert result.exit_code == 0
    assert len(copied_content) == 1
    assert "test.py" in copied_content[0]
    assert "print('hello')" in copied_content[0]


def test_cli_output_file(tmp_path, monkeypatch):
    """Test writing output to file."""
    # Create a test file
    test_file = tmp_path / "test.py"
    test_file.write_text("print('hello')")

    # Create output file path
    out_file = tmp_path / "output.md"

    # Mock pyperclip.copy
    monkeypatch.setattr(pyperclip, "copy", lambda x: None)

    # Run CLI
    result = runner.invoke(app, [str(tmp_path), "--out", str(out_file)])

    assert result.exit_code == 0
    assert out_file.exists()
    content = out_file.read_text()
    assert "test.py" in content
    assert "print('hello')" in content


def test_cli_print_output(tmp_path, monkeypatch):
    """Test printing output to screen."""
    # Create a test file
    test_file = tmp_path / "test.py"
    test_file.write_text("print('hello')")

    # Mock pyperclip.copy
    monkeypatch.setattr(pyperclip, "copy", lambda x: None)

    # Run CLI
    result = runner.invoke(app, [str(tmp_path), "--print"])

    assert result.exit_code == 0
    assert "test.py" in result.stdout
    assert "print('hello')" in result.stdout


def test_cli_no_files_found(tmp_path):
    """Test behavior when no matching files are found."""
    # Create a non-matching file
    test_file = tmp_path / "test.txt"
    test_file.write_text("hello")

    # Run CLI with filter for .py files only
    result = runner.invoke(app, [str(tmp_path), "--include", "py"])

    assert result.exit_code == 1
    # Rich's output includes ANSI color codes, so we check for the plain text portion
    assert "No matching files found" in result.output.strip()


def test_cli_multiple_outputs(tmp_path, monkeypatch):
    """Test combining output options."""
    # Create a test file
    test_file = tmp_path / "test.py"
    test_file.write_text("print('hello')")

    # Create output file path
    out_file = tmp_path / "output.md"

    # Mock pyperclip.copy
    copied_content = []

    def mock_copy(text):
        copied_content.append(text)

    monkeypatch.setattr(pyperclip, "copy", mock_copy)

    # Run CLI with both file output and print
    result = runner.invoke(app, [str(tmp_path), "--out", str(out_file), "--print"])

    assert result.exit_code == 0
    # Check clipboard
    assert len(copied_content) == 1
    assert "test.py" in copied_content[0]
    # Check file
    assert out_file.exists()
    assert "test.py" in out_file.read_text()
    # Check stdout
    assert "test.py" in result.stdout
