"""
scraper.py
Web scraping module – fetches URLs, cleans HTML, extracts contact info.
"""
from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from typing import List

import requests
from bs4 import BeautifulSoup

# ── Patterns ──────────────────────────────────────────────────────────────────
_PHONE_PATTERN = re.compile(
    r"(?:0(?:5[0-9]|[2-9])[- ]?(?:\d[- ]?){6,7}\d)"
)
_EMAIL_PATTERN = re.compile(
    r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+"
)
_ADDRESS_PATTERN = re.compile(
    r"(?:רחוב|רח'|שד'|שדרות|דרך|כיכר|סמטת|ככר)"
    r"\s+[\u05d0-\u05ea\w\s\"'\"]{2,30}\s*\d{1,4}"
    r"|[\u05d0-\u05ea\s]{3,20}\s+\d{1,4}\s*,\s*[\u05d0-\u05ea\s]{2,20}",
    re.UNICODE,
)
_HOURS_PATTERN = re.compile(
    r"(?:א|ב|ג|ד|ה|ו|ש)['-]?(?:א|ב|ג|ד|ה|ו|ש)?['\"]?"
    r"\s*[-–]\s*(?:א|ב|ג|ד|ה|ו|ש)['\"]?"
    r".*?\d{1,2}:\d{2}"
    r"|(?:שעות פעילות|פתוח|סגור|זמין).*?\d{1,2}:\d{2}"
    r"|\d{1,2}:\d{2}\s*[-–]\s*\d{1,2}:\d{2}",
    re.UNICODE,
)

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}


# ── Data model ────────────────────────────────────────────────────────────────
@dataclass
class ScrapedPage:
    url: str
    text: str = ""
    phones: List[str] = field(default_factory=list)
    emails: List[str] = field(default_factory=list)
    addresses: List[str] = field(default_factory=list)
    hours: List[str] = field(default_factory=list)
    error: str | None = None


# ── Helpers ───────────────────────────────────────────────────────────────────
def _clean_text(soup: BeautifulSoup) -> str:
    """Remove script/style tags and return clean page text."""
    for tag in soup(["script", "style", "noscript", "svg", "img"]):
        tag.decompose()
    return " ".join(soup.get_text(separator=" ").split())


def _extract_phones(text: str) -> List[str]:
    raw = _PHONE_PATTERN.findall(text)
    cleaned = [re.sub(r"[- ]", "", p) for p in raw]
    return list(dict.fromkeys(cleaned))


def _extract_emails(text: str) -> List[str]:
    found = _EMAIL_PATTERN.findall(text)
    return list(dict.fromkeys(e.lower() for e in found))


def _extract_addresses(text: str) -> List[str]:
    found = _ADDRESS_PATTERN.findall(text)
    return list(dict.fromkeys(a.strip() for a in found))


def _extract_hours(text: str) -> List[str]:
    found = _HOURS_PATTERN.findall(text)
    return list(dict.fromkeys(h.strip() for h in found))


def _parse_soup(url: str, soup: BeautifulSoup) -> ScrapedPage:
    text = _clean_text(soup)
    return ScrapedPage(
        url=url,
        text=text,
        phones=_extract_phones(text),
        emails=_extract_emails(text),
        addresses=_extract_addresses(text),
        hours=_extract_hours(text),
    )


# ── Public API ────────────────────────────────────────────────────────────────
def scrape_url(url: str, timeout: int = 15) -> ScrapedPage:
    """Fetch a single URL and return a ScrapedPage."""
    try:
        resp = requests.get(
            url, headers=_HEADERS, timeout=timeout, verify=False
        )
        resp.raise_for_status()
        soup = BeautifulSoup(resp.content, "lxml")
        return _parse_soup(url, soup)
    except requests.exceptions.Timeout:
        return ScrapedPage(url=url, error=f"Timeout after {timeout}s")
    except requests.exceptions.ConnectionError as e:
        return ScrapedPage(url=url, error=f"Connection error: {e}")
    except Exception as e:
        return ScrapedPage(url=url, error=str(e))


def scan_all(urls: list[str]) -> list[ScrapedPage]:
    """Scrape multiple URLs with a small delay between requests."""
    pages = []
    for i, url in enumerate(urls):
        if i > 0:
            time.sleep(1)
        pages.append(scrape_url(url))
    return pages


def merge_scraped(pages: list[ScrapedPage]) -> dict:
    """Merge multiple scraped pages into one payload for the AI."""
    all_phones: list[str] = []
    all_emails: list[str] = []
    all_addresses: list[str] = []
    all_hours: list[str] = []
    combined_text_parts: list[str] = []
    errors: list[str] = []

    for page in pages:
        if page.error:
            errors.append(f"{page.url}: {page.error}")
        else:
            combined_text_parts.append(f"[URL: {page.url}]\n{page.text}")
            all_phones.extend(page.phones)
            all_emails.extend(page.emails)
            all_addresses.extend(page.addresses)
            all_hours.extend(page.hours)

    return {
        "combined_text": "\n\n".join(combined_text_parts),
        "phones": list(dict.fromkeys(all_phones)),
        "emails": list(dict.fromkeys(all_emails)),
        "addresses": list(dict.fromkeys(all_addresses)),
        "hours": list(dict.fromkeys(all_hours)),
        "errors": errors,
        "page_count": len(pages),
    }
