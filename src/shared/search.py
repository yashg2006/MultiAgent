"""
Pluggable search tools for the Research Agent.

- `NullSearchTool` (default, `SEARCH_TOOL=none`): no network; the agent relies
  on the model alone. Used by tests and CI.
- `WikipediaSearchTool` (`SEARCH_TOOL=wikipedia`): free MediaWiki search API,
  no key. Failures (network, timeout, bad response) return no hits instead of
  failing the research step.

Other tools can be added by subclassing `SearchTool` and registering a name in
`get_search_tool`; the Research Agent does not change.
"""

from __future__ import annotations

import html
import json
import re
import urllib.parse
import urllib.request
from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any

from pydantic import BaseModel

from src.shared.utils import setup_logger

logger = setup_logger(__name__)


class SearchHit(BaseModel):
    title: str
    snippet: str
    url: str


class SearchTool(ABC):
    name: str = "base"

    @abstractmethod
    def search(self, query: str, limit: int = 3) -> list[SearchHit]:
        """Return up to `limit` hits for `query`; never raises."""
        raise NotImplementedError


class NullSearchTool(SearchTool):
    name = "none"

    def search(self, query: str, limit: int = 3) -> list[SearchHit]:
        return []


_TAG_RE = re.compile(r"<[^>]+>")


def _strip_markup(text: str) -> str:
    return html.unescape(_TAG_RE.sub("", text)).strip()


class WikipediaSearchTool(SearchTool):
    """English Wikipedia full-text search via the public MediaWiki API."""

    name = "wikipedia"
    endpoint = "https://en.wikipedia.org/w/api.php"
    # Wikimedia asks API clients to identify themselves.
    user_agent = "MultiAgentAISystem/0.1 (https://github.com/yashg2006/MultiAgent; course project)"

    def __init__(
        self,
        timeout: float = 10.0,
        opener: Callable[..., Any] = urllib.request.urlopen,
    ) -> None:
        self.timeout = timeout
        self._open = opener

    def search(self, query: str, limit: int = 3) -> list[SearchHit]:
        if not query.strip():
            return []
        params = urllib.parse.urlencode(
            {
                "action": "query",
                "list": "search",
                "srsearch": query[:300],
                "srlimit": limit,
                "format": "json",
            }
        )
        request = urllib.request.Request(
            f"{self.endpoint}?{params}", headers={"User-Agent": self.user_agent}
        )
        try:
            with self._open(request, timeout=self.timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
            results = payload["query"]["search"]
        except Exception as exc:  # noqa: BLE001 - search is best-effort context
            logger.warning("Wikipedia search failed for %r: %s", query[:80], exc)
            return []
        hits = []
        for item in results[:limit]:
            title = str(item.get("title", ""))
            hits.append(
                SearchHit(
                    title=title,
                    snippet=_strip_markup(str(item.get("snippet", ""))),
                    url="https://en.wikipedia.org/wiki/"
                    + urllib.parse.quote(title.replace(" ", "_")),
                )
            )
        return hits


def get_search_tool(name: str) -> SearchTool:
    normalized = name.strip().lower()
    if normalized in ("", "none"):
        return NullSearchTool()
    if normalized == "wikipedia":
        return WikipediaSearchTool()
    raise ValueError(f"Unknown SEARCH_TOOL: {name!r} (expected 'none' or 'wikipedia')")
