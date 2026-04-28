import re
from typing import Any
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup


USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/123.0.0.0 Safari/537.36"
)


def _extract_price_from_text(text: str | None) -> str | None:
    if not text:
        return None

    normalized = " ".join(text.split())
    # Supports common formats: 19.99, 19,99, $19.99, NIS 49.90, etc.
    price_match = re.search(r"(?:(?:[$€£₪]|USD|EUR|NIS)\s*)?(\d{1,6}(?:[.,]\d{1,2})?)", normalized)
    if not price_match:
        return None

    return price_match.group(1).replace(",", ".")


def _extract_images(soup: BeautifulSoup, base_url: str) -> list[str]:
    candidates: list[str] = []

    for tag in soup.select("meta[property='og:image'], meta[name='twitter:image']"):
        content = (tag.get("content") or "").strip()
        if content:
            candidates.append(content)

    for img in soup.find_all("img"):
        src = (img.get("src") or img.get("data-src") or "").strip()
        if not src:
            continue
        if src.startswith("data:"):
            continue
        candidates.append(src)

    normalized: list[str] = []
    seen = set()
    for src in candidates:
        absolute = urljoin(base_url, src)
        if absolute in seen:
            continue
        seen.add(absolute)
        normalized.append(absolute)
        if len(normalized) == 4:
            break

    return normalized


def scrape_product(url: str) -> dict[str, Any]:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("Invalid URL. Please provide a full http/https URL.")

    response = requests.get(
        url,
        timeout=20,
        headers={"User-Agent": USER_AGENT, "Accept-Language": "en-US,en;q=0.9"},
    )
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    title = (soup.title.string.strip() if soup.title and soup.title.string else None)

    price_sources = [
        soup.select_one("meta[property='product:price:amount']"),
        soup.select_one("meta[property='og:price:amount']"),
        soup.select_one("meta[itemprop='price']"),
    ]

    price: str | None = None
    for source in price_sources:
        if source:
            raw = source.get("content") or source.get("value") or source.get_text(strip=True)
            price = _extract_price_from_text(raw)
            if price:
                break

    if not price:
        script_prices = re.findall(r'"price"\s*:\s*"?(?P<value>\d+(?:[.,]\d{1,2})?)"?', response.text)
        if script_prices:
            price = script_prices[0].replace(",", ".")

    images = _extract_images(soup, response.url)

    return {
        "source_url": response.url,
        "title": title,
        "price": price,
        "images": images,
    }
