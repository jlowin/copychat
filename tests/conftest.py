from pathlib import Path
import pytest
import shutil


@pytest.fixture
def sample_project(tmp_path) -> Path:
    """Create a copy of the fixture project in a temporary directory."""
    fixtures_dir = Path(__file__).parent / "fixtures"
    project_dir = tmp_path / "test_project"

    # Copy all fixtures to temporary directory
    shutil.copytree(fixtures_dir, project_dir, dirs_exist_ok=True)

    return project_dir


@pytest.fixture
def sample_project_files(sample_project) -> list[Path]:
    """Get a list of all files in the sample project."""
    return list(sample_project.rglob("*"))


def test_fixture_structure(sample_project):
    """Verify the fixture structure is correct."""
    assert (sample_project / "src" / "main.py").exists()
    assert (sample_project / "src" / "app.js").exists()
    assert (sample_project / "src" / "styles" / "main.css").exists()
    assert (sample_project / "docs" / "README.md").exists()
    assert (sample_project / "config" / "settings.yml").exists()
    assert (sample_project / "db" / "schema.sql").exists()
    assert (sample_project / ".gitignore").exists()
    assert (sample_project / ".env").exists()
