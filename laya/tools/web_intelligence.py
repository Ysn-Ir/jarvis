"""
Laya Web Intelligence Engine
Multi-engine real-time web search and page content extraction.
Combines Wikipedia Knowledge Extracts, Bing Web Search, and BeautifulSoup.
Enables Laya to answer live questions, check news, weather, people, entities, and extract text from URLs.
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
        Execute a robust multi-source web search combining Wikipedia Knowledge summaries
        and Bing Web Search results with structured titles, snippets, and URLs.
        """
        if not query or not query.strip():
            return "No search query provided."

        clean_query = query.strip()
        output_sections: List[str] = []

        # 1. Wikipedia Knowledge Extract (Ultra-fast & 100% accurate for entities/people/facts)
        try:
            wiki_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(clean_query)}"
            w_res = requests.get(wiki_url, headers={"User-Agent": "Laya/2.0"}, timeout=3)
            if w_res.status_code == 200:
                data = w_res.json()
                extract = data.get("extract")
                title = data.get("title")
                if extract:
                    output_sections.append(f"[Verified Knowledge - {title}]:\n{extract}")
        except Exception:
            pass

        # 2. Bing Web Search (Live web pages, news, YouTube, sports, products)
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept-Language": "en-US,en;q=0.9"
            }
            bing_url = f"https://www.bing.com/search?q={urllib.parse.quote(clean_query)}"
            b_res = requests.get(bing_url, headers=headers, timeout=4)
            if b_res.status_code == 200:
                soup = BeautifulSoup(b_res.text, "html.parser")
                web_results = []
                for li in soup.select("li.b_algo")[:max_results]:
                    h2 = li.find("h2")
                    title = h2.get_text().strip() if h2 else ""
                    p = li.find("p") or li.find(".b_caption")
                    snippet = p.get_text().strip() if p else ""
                    link = h2.find("a")["href"] if (h2 and h2.find("a") and h2.find("a").has_attr("href")) else ""
                    if title:
                        res_str = f"• {title}"
                        if snippet:
                            res_str += f"\n  Summary: {snippet}"
                        if link:
                            res_str += f"\n  URL: {link}"
                        web_results.append(res_str)

                if web_results:
                    output_sections.append("[Live Web Results]:\n" + "\n\n".join(web_results))
        except Exception:
            pass

        # 3. DuckDuckGo Instant Answer Fallback
        if not output_sections:
            try:
                api_url = f"https://api.duckduckgo.com/?q={urllib.parse.quote(clean_query)}&format=json&no_html=1"
                d_res = requests.get(api_url, timeout=3, headers={"User-Agent": "Mozilla/5.0"})
                if d_res.status_code == 200:
                    d_data = d_res.json()
                    abstract = d_data.get("AbstractText") or d_data.get("Answer")
                    if abstract:
                        output_sections.append(f"[Search Result]:\n{abstract}")
            except Exception:
                pass

        if output_sections:
            return "\n\n".join(output_sections)

        return f"Could not find live web search results for '{clean_query}'. Please verify your query or internet connection."

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
