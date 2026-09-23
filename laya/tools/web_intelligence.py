"""
Laya Web Intelligence Engine
Real-time web search and page content extraction using duckduckgo_search and BeautifulSoup.
Enables Laya to answer live questions, check news, weather, facts, and extract text from URLs.
"""

import re
import urllib.parse
from typing import Optional, List, Dict
import requests
from bs4 import BeautifulSoup


class WebIntelligence:
    _instance: Optional["WebIntelligence"] = None

    @classmethod
    def get_instance(cls) -> "WebIntelligence":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def live_web_search(self, query: str, max_results: int = 4) -> str:
        """
        Execute a live web search and return structured titles, snippets, and URLs.
        """
        if not query or not query.strip():
            return "No search query provided."

        clean_query = query.strip()

        # Primary: duckduckgo_search library
        try:
            from duckduckgo_search import DDGS
            results = list(DDGS().text(clean_query, max_results=max_results))
            if results:
                formatted = []
                for idx, r in enumerate(results, 1):
                    title = r.get("title", "Untitled")
                    snippet = r.get("body", "")
                    url = r.get("href", "")
                    formatted.append(f"[{idx}] {title}\nSummary: {snippet}\nURL: {url}")
                return "\n\n".join(formatted)
        except Exception as e:
            # Fallback to direct DuckDuckGo instant API
            pass

        # Fallback: DuckDuckGo instant answer API
        try:
            api_url = f"https://api.duckduckgo.com/?q={urllib.parse.quote(clean_query)}&format=json&no_html=1"
            res = requests.get(api_url, timeout=5, headers={"User-Agent": "Mozilla/5.0"})
            if res.status_code == 200:
                data = res.json()
                abstract = data.get("AbstractText") or data.get("Answer")
                if abstract:
                    source = data.get("AbstractSource", "DuckDuckGo")
                    return f"Result ({source}):\n{abstract}"
                related = data.get("RelatedTopics", [])
                if related and isinstance(related, list):
                    first_topic = related[0]
                    if isinstance(first_topic, dict) and first_topic.get("Text"):
                        return f"Result:\n{first_topic.get('Text')}"
        except Exception:
            pass

        return f"Could not find live search results for '{clean_query}'. Please check your network connection."

    def fetch_webpage_content(self, url: str, max_chars: int = 2500) -> str:
        """
        Download a webpage and extract clean readable text for summarization or reading.
        """
        if not url or not url.strip():
            return "No URL provided."

        target_url = url.strip()
        if not target_url.startswith(("http://", "https://")):
            target_url = "https://" + target_url

        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            resp = requests.get(target_url, headers=headers, timeout=8)
            resp.raise_for_status()

            soup = BeautifulSoup(resp.text, "html.parser")

            # Remove non-content elements
            for tag in soup(["script", "style", "nav", "footer", "header", "noscript", "svg"]):
                tag.decompose()

            # Extract title and text
            title = soup.title.string.strip() if soup.title and soup.title.string else target_url
            text = soup.get_text(separator="\n")

            # Clean and condense whitespace
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            cleaned_text = "\n".join(lines)

            if len(cleaned_text) > max_chars:
                cleaned_text = cleaned_text[:max_chars] + "\n... [Content truncated]"

            return f"Page Title: {title}\nURL: {target_url}\n\nContent:\n{cleaned_text}"

        except requests.exceptions.Timeout:
            return f"Failed to fetch {target_url}: Connection timed out after 8 seconds."
        except Exception as e:
            return f"Failed to fetch webpage content from {target_url}: {e}"


def get_web_intelligence() -> WebIntelligence:
    return WebIntelligence.get_instance()
