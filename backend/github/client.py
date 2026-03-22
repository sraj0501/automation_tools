"""
GitHub REST API client (async).

Provides issue management, search, comments, and user lookups.
Uses aiohttp for all HTTP calls.

Configuration (via .env):
    GITHUB_TOKEN     = your_personal_access_token
    GITHUB_OWNER     = your_github_username_or_org
    GITHUB_REPO      = your_repo_name
    GITHUB_API_URL   = https://api.github.com  (optional; override for GitHub Enterprise)
"""

import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiohttp

logger = logging.getLogger(__name__)


def _load_env() -> None:
    """Load .env by walking up from this file. Idempotent via override=False."""
    here = Path(__file__).resolve()
    for parent in [here, *here.parents]:
        env_file = parent / ".env"
        if env_file.exists():
            try:
                from dotenv import load_dotenv
                load_dotenv(env_file, override=False)
            except ImportError:
                pass
            return


_load_env()


def _env(key: str, default: str = "") -> str:
    return os.getenv(key, default)


def _env_int(key: str, default: int = 0) -> int:
    val = os.getenv(key, "")
    try:
        return int(val) if val else default
    except ValueError:
        return default


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class GitHubIssue:
    """Represents a GitHub issue."""

    id: int                          # global numeric ID (stable, use for seen-sets)
    number: int                      # issue number (used in URLs and API calls)
    title: str
    body: str
    state: str                       # "open" | "closed"
    html_url: str
    labels: List[str] = field(default_factory=list)
    assignees: List[str] = field(default_factory=list)
    milestone: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------

class GitHubClient:
    """Async GitHub REST API client."""

    DEFAULT_BASE_URL = "https://api.github.com"

    def __init__(
        self,
        token: Optional[str] = None,
        owner: Optional[str] = None,
        repo: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        self._token = token or _env("GITHUB_TOKEN")
        self._owner = owner or _env("GITHUB_OWNER")
        self._repo = repo or _env("GITHUB_REPO")
        raw_url = base_url or _env("GITHUB_API_URL", self.DEFAULT_BASE_URL)
        self._base_url = raw_url.rstrip("/")
        self._api_version = _env("GITHUB_API_VERSION", "2022-11-28")
        self._timeout_secs = _env_int("HTTP_TIMEOUT", 30)
        self._session: Optional[aiohttp.ClientSession] = None
        self._cached_login: Optional[str] = None  # cached after first /user call

    # -- lifecycle ----------------------------------------------------------

    def is_configured(self) -> bool:
        """Returns True when the minimum required credentials are present."""
        return bool(self._token and self._owner and self._repo)

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            headers = {
                "Authorization": f"Bearer {self._token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": self._api_version,
                "Content-Type": "application/json",
            }
            timeout = aiohttp.ClientTimeout(total=self._timeout_secs)
            self._session = aiohttp.ClientSession(headers=headers, timeout=timeout)
        return self._session

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()

    # -- URL helpers --------------------------------------------------------

    def _api(self, path: str) -> str:
        """Build a full API URL from a path like '/user' or '/repos/...'."""
        return f"{self._base_url}{path}"

    # -- low-level HTTP -----------------------------------------------------

    async def _get(self, url: str, params: Optional[Dict[str, Any]] = None) -> Optional[Any]:
        """GET request; returns parsed JSON or None on error."""
        session = await self._get_session()
        try:
            async with session.get(url, params=params) as resp:
                if resp.status == 200:
                    return await resp.json()
                logger.warning(f"GET {url} → {resp.status}: {await resp.text()}")
                return None
        except Exception as e:
            logger.warning(f"GET {url} failed: {e}")
            return None

    async def _get_with_headers(
        self, url: str, params: Optional[Dict[str, Any]] = None
    ):
        """GET request; returns (json_body, response_headers) for Link-based pagination."""
        session = await self._get_session()
        try:
            async with session.get(url, params=params) as resp:
                if resp.status == 200:
                    return await resp.json(), dict(resp.headers)
                logger.warning(f"GET {url} → {resp.status}")
                return None, {}
        except Exception as e:
            logger.warning(f"GET {url} failed: {e}")
            return None, {}

    async def _post(self, url: str, json_body: Any = None) -> Optional[Dict]:
        session = await self._get_session()
        try:
            async with session.post(url, json=json_body) as resp:
                if resp.status in (200, 201):
                    return await resp.json()
                logger.warning(f"POST {url} → {resp.status}: {await resp.text()}")
                return None
        except Exception as e:
            logger.warning(f"POST {url} failed: {e}")
            return None

    async def _patch(self, url: str, json_body: Any = None) -> Optional[Dict]:
        session = await self._get_session()
        try:
            async with session.patch(url, json=json_body) as resp:
                if resp.status == 200:
                    return await resp.json()
                logger.warning(f"PATCH {url} → {resp.status}: {await resp.text()}")
                return None
        except Exception as e:
            logger.warning(f"PATCH {url} failed: {e}")
            return None

    # -- parsing ------------------------------------------------------------

    @staticmethod
    def _parse_issue(data: Dict[str, Any]) -> GitHubIssue:
        """Convert an API response dict into a GitHubIssue."""
        labels = [
            lbl.get("name", "") if isinstance(lbl, dict) else str(lbl)
            for lbl in data.get("labels", [])
        ]
        assignees = [
            a.get("login", "") if isinstance(a, dict) else str(a)
            for a in data.get("assignees", [])
        ]
        milestone_data = data.get("milestone")
        milestone = milestone_data.get("title") if isinstance(milestone_data, dict) else None

        return GitHubIssue(
            id=data.get("id", 0),
            number=data.get("number", 0),
            title=data.get("title", ""),
            body=data.get("body", "") or "",
            state=data.get("state", ""),
            html_url=data.get("html_url", ""),
            labels=labels,
            assignees=assignees,
            milestone=milestone,
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
        )

    # -- read operations ----------------------------------------------------

    async def get_current_user(self) -> Optional[Dict[str, Any]]:
        """GET /user — returns login, id, name, etc."""
        return await self._get(self._api("/user"))

    async def _ensure_login(self) -> Optional[str]:
        """Fetch and cache the authenticated user's login name."""
        if self._cached_login is None:
            user = await self.get_current_user()
            if user:
                self._cached_login = user.get("login")
        return self._cached_login

    async def get_my_issues(
        self,
        state: str = "open",
        updated_after: Optional[datetime] = None,
    ) -> List[GitHubIssue]:
        """Fetch issues assigned to the authenticated user in the configured repo.

        Uses GET /repos/{owner}/{repo}/issues?assignee={login}&state={state}.
        Fetches the authenticated user's login first, then filters by assignee.
        Handles GitHub's Link-header pagination automatically.

        Args:
            state: Issue state filter ("open", "closed", or "all").
            updated_after: If set, only issues updated at or after this datetime
                (passed as ``since`` to the GitHub API, ISO 8601 format).
        """
        login = await self._ensure_login()
        if not login:
            logger.warning("Could not determine current user login")
            return []

        url = self._api(f"/repos/{self._owner}/{self._repo}/issues")
        params: Dict[str, Any] = {
            "assignee": login,
            "state": state,
            "per_page": 100,
        }
        if updated_after is not None:
            params["since"] = updated_after.isoformat()

        results: List[GitHubIssue] = []
        while url:
            data, headers = await self._get_with_headers(url, params=params)
            if not isinstance(data, list):
                break
            for item in data:
                # GitHub issues endpoint also returns PRs; skip pull requests
                if item.get("pull_request"):
                    continue
                results.append(self._parse_issue(item))
            # Parse Link header for next page
            url = self._parse_next_link(headers.get("Link", ""))
            params = {}  # next-page URL already contains all params

        return results

    async def get_issue(self, number: int) -> Optional[GitHubIssue]:
        """Fetch a single issue by its number. GET /repos/{owner}/{repo}/issues/{number}"""
        url = self._api(f"/repos/{self._owner}/{self._repo}/issues/{number}")
        data = await self._get(url)
        return self._parse_issue(data) if data else None

    async def search_issues(self, query: str, max_results: int = 20) -> List[GitHubIssue]:
        """Search issues in the configured repo.

        Uses GET /search/issues?q={query}+repo:{owner}/{repo}+is:issue
        """
        full_query = f"{query} repo:{self._owner}/{self._repo} is:issue"
        url = self._api("/search/issues")
        params = {"q": full_query, "per_page": max_results}
        data = await self._get(url, params=params)
        if not isinstance(data, dict):
            return []
        items = data.get("items", [])
        return [self._parse_issue(item) for item in items]

    # -- write operations ---------------------------------------------------

    async def create_issue(
        self,
        title: str,
        body: str = "",
        labels: Optional[List[str]] = None,
        assignees: Optional[List[str]] = None,
        milestone: Optional[int] = None,
    ) -> Optional[GitHubIssue]:
        """POST /repos/{owner}/{repo}/issues — create a new issue."""
        payload: Dict[str, Any] = {"title": title}
        if body:
            payload["body"] = body
        if labels:
            payload["labels"] = labels
        if assignees:
            payload["assignees"] = assignees
        if milestone is not None:
            payload["milestone"] = milestone

        url = self._api(f"/repos/{self._owner}/{self._repo}/issues")
        data = await self._post(url, json_body=payload)
        if data:
            issue = self._parse_issue(data)
            logger.info(f"Created GitHub issue #{issue.number}: {title}")
            return issue
        return None

    async def update_issue(
        self,
        number: int,
        title: Optional[str] = None,
        body: Optional[str] = None,
        state: Optional[str] = None,
        labels: Optional[List[str]] = None,
    ) -> Optional[GitHubIssue]:
        """PATCH /repos/{owner}/{repo}/issues/{number} — update issue fields."""
        payload: Dict[str, Any] = {}
        if title is not None:
            payload["title"] = title
        if body is not None:
            payload["body"] = body
        if state is not None:
            payload["state"] = state
        if labels is not None:
            payload["labels"] = labels

        if not payload:
            logger.warning(f"update_issue #{number}: no fields to update")
            return None

        url = self._api(f"/repos/{self._owner}/{self._repo}/issues/{number}")
        data = await self._patch(url, json_body=payload)
        if data:
            issue = self._parse_issue(data)
            logger.info(f"Updated GitHub issue #{number}")
            return issue
        return None

    async def close_issue(self, number: int) -> bool:
        """Close an issue (PATCH state=closed)."""
        result = await self.update_issue(number, state="closed")
        return result is not None

    async def reopen_issue(self, number: int) -> bool:
        """Reopen an issue (PATCH state=open)."""
        result = await self.update_issue(number, state="open")
        return result is not None

    async def add_comment(self, number: int, body: str) -> bool:
        """POST /repos/{owner}/{repo}/issues/{number}/comments — add a comment."""
        url = self._api(f"/repos/{self._owner}/{self._repo}/issues/{number}/comments")
        result = await self._post(url, json_body={"body": body})
        if result:
            logger.info(f"Added comment to GitHub issue #{number}")
            return True
        return False

    # -- pagination helper --------------------------------------------------

    @staticmethod
    def _parse_next_link(link_header: str) -> Optional[str]:
        """Parse GitHub's Link header and return the 'next' URL, or None."""
        if not link_header:
            return None
        for part in link_header.split(","):
            segments = [s.strip() for s in part.split(";")]
            if len(segments) == 2 and segments[1] == 'rel="next"':
                url = segments[0]
                if url.startswith("<") and url.endswith(">"):
                    return url[1:-1]
        return None
