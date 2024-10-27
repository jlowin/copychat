from pathlib import Path
import shutil
from typing import Optional
import git
from rich.console import Console

error_console = Console(stderr=True)


class GitHubSource:
    """Handle GitHub repositories as sources."""

    def __init__(self, repo_path: str, cache_dir: Optional[Path] = None):
        """Initialize GitHub source."""
        self.repo_path = repo_path.strip("/")
        self.cache_dir = cache_dir or Path.home() / ".cache" / "copychat" / "github"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    @property
    def clone_url(self) -> str:
        """Get HTTPS clone URL for repository."""
        return f"https://github.com/{self.repo_path}.git"

    @property
    def repo_dir(self) -> Path:
        """Get path to cached repository."""
        return self.cache_dir / self.repo_path.replace("/", "_")

    def fetch(self) -> Path:
        """Fetch repository and return path to files."""
        try:
            if self.repo_dir.exists():
                # Update existing repo
                repo = git.Repo(self.repo_dir)
                repo.remotes.origin.fetch()
                repo.remotes.origin.pull()
            else:
                # Clone new repo
                git.Repo.clone_from(self.clone_url, self.repo_dir, depth=1)

            return self.repo_dir

        except git.GitCommandError as e:
            error_console.print(f"[red]Error accessing repository:[/] {str(e)}")
            raise

    def cleanup(self) -> None:
        """Remove cached repository."""
        if self.repo_dir.exists():
            shutil.rmtree(self.repo_dir)
