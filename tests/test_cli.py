from typer.testing import CliRunner
from copychat.cli import app
import pyperclip
import re

runner = CliRunner(mix_stderr=False)


def strip_ansi(text: str) -> str:
    """Remove ANSI escape codes from text."""
    ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
    return ansi_escape.sub("", text)


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
    assert 'language="python"' in copied_content[0]
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
    assert 'language="python"' in content
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
    assert 'language="python"' in result.stdout
    assert "print('hello')" in result.stdout


def test_cli_no_files_found(tmp_path):
    """Test behavior when no matching files are found."""
    # Create a non-matching file
    test_file = tmp_path / "test.txt"
    test_file.write_text("hello")

    # Run CLI with filter for .py files only
    result = runner.invoke(app, [str(tmp_path), "--include", "py"])

    # Since this is expected behavior, CLI should exit with code 0 rather than 1
    assert result.exit_code == 0
    assert "Found 0 matching files" in strip_ansi(result.stderr)


def test_cli_multiple_outputs(tmp_path, monkeypatch):
    """Test combining output options."""
    # Create a test file
    test_file = tmp_path / "test.py"
    test_file.write_text("print('hello')")

    # Create output file path
    out_file = tmp_path / "output.md"

    # Mock pyperclip.copy and paste
    copied_content = []

    def mock_copy(text):
        copied_content.append(text)

    # Since we're using output file, clipboard copy won't happen
    # Instead just check the file output and stdout
    monkeypatch.setattr(pyperclip, "copy", mock_copy)

    # Run CLI with both file output and print
    result = runner.invoke(app, [str(tmp_path), "--out", str(out_file), "--print"])

    assert result.exit_code == 0

    # Check file
    assert out_file.exists()
    file_content = out_file.read_text()
    assert 'language="python"' in file_content

    # Check stdout
    assert 'language="python"' in result.stdout


def test_cli_issue(monkeypatch):
    runner = CliRunner(mix_stderr=False)

    def fake_fetch(self):
        return Path("issue.md"), "issue body"

    monkeypatch.setattr("copychat.sources.GitHubItem.fetch", fake_fetch)
    copied = []
    monkeypatch.setattr(pyperclip, "copy", lambda x: copied.append(x))

    result = runner.invoke(app, ["owner/repo#1"])
    assert result.exit_code == 0
    assert copied
    assert "issue body" in copied[0]
