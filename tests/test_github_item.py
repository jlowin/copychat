from copychat.sources import GitHubItem


class DummyResponse:
    def __init__(self, data, status=200, is_text=False):
        self._data = data
        self.status_code = status
        self.ok = status == 200
        self._is_text = is_text

    def raise_for_status(self):
        if not self.ok:
            raise Exception("status")

    def json(self):
        return self._data

    @property
    def text(self):
        return self._data if self._is_text else ""


def test_github_item_fetch(monkeypatch):
    """GitHubItem should format issue and comments."""

    issue_data = {
        "title": "Test issue",
        "body": "Body text",
        "comments_url": "http://example.com/comments",
        "pull_request": {},
        "html_url": "https://github.com/owner/repo/pull/1",
        "user": {"login": "testuser"},
        "created_at": "2024-01-01",
        "updated_at": "2024-01-02",
        "state": "open",
    }
    comments = [{"user": {"login": "alice"}, "created_at": "2024-01-01", "body": "hi"}]
    reviews = [
        {
            "user": {"login": "bob"},
            "created_at": "2024-01-02",
            "path": "file.py",
            "body": "looks good",
        }
    ]

    calls = []

    def fake_get(url, headers=None, timeout=0):
        calls.append(url)
        if "comments" in url and "pulls" in url:
            return DummyResponse(reviews)
        if "comments" in url:
            return DummyResponse(comments)
        return DummyResponse(issue_data)

    monkeypatch.setattr("requests.get", fake_get)

    item = GitHubItem("owner/repo", 1)
    path, content = item.fetch()

    assert path.name == "owner_repo_pr_1.md"
    assert "Test issue" in content
    assert "alice" in content
    assert "looks good" in content
    assert "**Pull Request**" in content
    assert "**Status**: OPEN" in content
    assert "**Author**: testuser" in content
    assert "https://github.com/owner/repo/pull/1" in content
    assert any("pulls" in c for c in calls)


def test_github_item_fetch_with_diff(monkeypatch):
    """GitHubItem should include PR diff when available."""

    issue_data = {
        "title": "Test PR",
        "body": "PR description",
        "comments_url": "http://example.com/comments",
        "pull_request": {},
        "html_url": "https://github.com/owner/repo/pull/2",
        "user": {"login": "testuser"},
        "created_at": "2024-01-01",
        "updated_at": "2024-01-02",
        "state": "open",
    }
    comments = []
    reviews = []
    diff_content = """diff --git a/file.txt b/file.txt
index abc123..def456 100644
--- a/file.txt
+++ b/file.txt
@@ -1,3 +1,3 @@
 Line 1
-Line 2
+Line 2 modified
 Line 3"""

    calls = []
    headers_received = {}

    def fake_get(url, headers=None, timeout=0):
        calls.append(url)
        if headers:
            headers_received[url] = headers

        if "diff" in headers.get("Accept", "") and "pulls" in url:
            return DummyResponse(diff_content, is_text=True)
        if "comments" in url and "pulls" in url:
            return DummyResponse(reviews)
        if "comments" in url:
            return DummyResponse(comments)
        return DummyResponse(issue_data)

    monkeypatch.setattr("requests.get", fake_get)

    item = GitHubItem("owner/repo", 2)
    path, content = item.fetch()

    assert path.name == "owner_repo_pr_2.md"
    assert "Test PR" in content
    assert "PR description" in content
    assert "**Pull Request**" in content
    assert "## PR Diff" in content
    assert "```diff" in content
    assert "+Line 2 modified" in content
    assert "application/vnd.github.diff" in headers_received.get(
        "https://api.github.com/repos/owner/repo/pulls/2", {}
    ).get("Accept", "")
