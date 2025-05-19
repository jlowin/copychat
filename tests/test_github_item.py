import pytest
from pathlib import Path
from copychat.sources import GitHubItem


class DummyResponse:
    def __init__(self, data, status=200):
        self._data = data
        self.status_code = status
        self.ok = status == 200

    def raise_for_status(self):
        if not self.ok:
            raise Exception("status")

    def json(self):
        return self._data


def test_github_item_fetch(monkeypatch):
    """GitHubItem should format issue and comments."""

    issue_data = {
        "title": "Test issue",
        "body": "Body text",
        "comments_url": "http://example.com/comments",
        "pull_request": {},
    }
    comments = [
        {"user": {"login": "alice"}, "created_at": "2024-01-01", "body": "hi"}
    ]
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
    assert any("pulls" in c for c in calls)
