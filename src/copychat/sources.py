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


class GitHubItem:
    """Fetch a GitHub issue or pull request with comments."""

    def __init__(self, repo_path: str, number: int, token: Optional[str] = None):
        self.repo_path = repo_path.strip("/")
        self.number = number
        self.token = token
        self.api_base = "https://api.github.com"

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/vnd.github+json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def fetch(self) -> tuple[Path, str]:
        """Return (path, content) for the issue or PR."""
        import requests

        issue_url = f"{self.api_base}/repos/{self.repo_path}/issues/{self.number}"
        resp = requests.get(issue_url, headers=self._headers(), timeout=30)
        resp.raise_for_status()
        data = resp.json()

        comments_resp = requests.get(data.get("comments_url"), headers=self._headers(), timeout=30)
        comments_resp.raise_for_status()
        comments = comments_resp.json()

        review_comments = []
        if "pull_request" in data:
            review_url = f"{self.api_base}/repos/{self.repo_path}/pulls/{self.number}/comments"
            rc = requests.get(review_url, headers=self._headers(), timeout=30)
            if rc.ok:
                review_comments = rc.json()

        lines = [f"# {data.get('title', '')} (#{self.number})", ""]
        body = data.get("body") or ""
        if body:
            lines.append(body)
            lines.append("")

        for c in comments:
            user = c.get("user", {}).get("login", "unknown")
            created = c.get("created_at", "")
            lines.append(f"## {user} - {created}")
            if c.get("body"):
                lines.append(c["body"])
            lines.append("")

        for c in review_comments:
            user = c.get("user", {}).get("login", "unknown")
            created = c.get("created_at", "")
            path = c.get("path", "")
            lines.append(f"## Review by {user} on {path} - {created}")
            if c.get("body"):
                lines.append(c["body"])
            lines.append("")

        content = "\n".join(lines).strip() + "\n"
        item_type = "pr" if "pull_request" in data else "issue"
        path = Path(f"{self.repo_path.replace('/', '_')}_{item_type}_{self.number}.md")
        return path, content
