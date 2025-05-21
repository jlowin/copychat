from pathlib import Path
import shutil
from typing import Optional
import git
from rich.console import Console
import tempfile

error_console = Console(stderr=True)

# Shared temporary directory for GitHub items
_github_temp_dir = None


def get_github_temp_dir() -> Path:
    """Get a temporary directory for GitHub items that persists for the process."""
    global _github_temp_dir
    if _github_temp_dir is None:
        _github_temp_dir = Path(tempfile.mkdtemp(prefix="copychat_github_"))
    return _github_temp_dir


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

    def _fetch_pr_diff(self) -> Optional[str]:
        """Fetch the PR diff from GitHub."""
        import requests

        if not self.token:
            error_console.print(
                "[yellow]Warning: GitHub token not provided. Some rate limits may apply.[/]"
            )

        # Get the diff using the GitHub API
        diff_url = f"{self.api_base}/repos/{self.repo_path}/pulls/{self.number}"
        headers = self._headers()
        headers["Accept"] = "application/vnd.github.diff"
        try:
            diff_resp = requests.get(diff_url, headers=headers, timeout=30)
            diff_resp.raise_for_status()
            return diff_resp.text
        except Exception as e:
            error_console.print(
                f"[yellow]Warning: Failed to fetch PR diff: {str(e)}[/]"
            )
            return None

    def fetch(self) -> tuple[Path, str]:
        """Return (path, content) for the issue or PR."""
        import requests

        issue_url = f"{self.api_base}/repos/{self.repo_path}/issues/{self.number}"
        resp = requests.get(issue_url, headers=self._headers(), timeout=30)
        resp.raise_for_status()
        data = resp.json()

        comments_resp = requests.get(
            data.get("comments_url"), headers=self._headers(), timeout=30
        )
        comments_resp.raise_for_status()
        comments = comments_resp.json()

        review_comments = []
        is_pr = "pull_request" in data
        diff_content = None

        if is_pr:
            # Fetch review comments
            review_url = (
                f"{self.api_base}/repos/{self.repo_path}/pulls/{self.number}/comments"
            )
            rc = requests.get(review_url, headers=self._headers(), timeout=30)
            if rc.ok:
                review_comments = rc.json()

            # Get the PR diff
            diff_content = self._fetch_pr_diff()

        lines = [f"# {data.get('title', '')} (#{self.number})", ""]
        body = data.get("body") or ""

        # Add metadata section
        item_type = "Pull Request" if is_pr else "Issue"
        html_url = data.get(
            "html_url", f"https://github.com/{self.repo_path}/issues/{self.number}"
        )
        user = data.get("user", {}).get("login", "unknown")
        created_at = data.get("created_at", "")
        updated_at = data.get("updated_at", "")
        state = data.get("state", "").upper()

        # Create a metadata header
        lines.extend(
            [
                f"> **{item_type}**: [{self.repo_path}#{self.number}]({html_url})",
                f"> **Status**: {state}",
                f"> **Author**: {user}",
                f"> **Created**: {created_at}",
                f"> **Updated**: {updated_at}",
                "",
            ]
        )

        if body:
            lines.append(body)
            lines.append("")

        # Add PR diff if available
        if is_pr and diff_content:
            lines.extend(
                [
                    "## PR Diff",
                    "",
                    "```diff",
                    diff_content,
                    "```",
                    "",
                ]
            )

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
        item_type_filename = "pr" if is_pr else "issue"

        # Use temporary directory instead of current working directory
        filename = (
            f"{self.repo_path.replace('/', '_')}_{item_type_filename}_{self.number}.md"
        )
        temp_dir = get_github_temp_dir()
        path = temp_dir / filename

        return path, content
