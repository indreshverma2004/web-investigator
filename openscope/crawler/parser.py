"""Extract visible page content and evidence-backed entities."""
from __future__ import annotations
import ipaddress
import re
from urllib.parse import urljoin, urlsplit, urldefrag
from bs4 import BeautifulSoup

EMAIL_RE = re.compile(r"(?i)\b[a-z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-z0-9](?:[a-z0-9-]*[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]*[a-z0-9])?)+\b")
URL_RE = re.compile(r"(?i)\b(?:https?://|www\.)[^\s<>\"']+")
IP_RE = re.compile(r"(?<![\w.])(?:\d{1,3}\.){3}\d{1,3}(?![\w.])")

def public_ipv4(value: str) -> bool:
    try: return ipaddress.ip_address(value).version == 4 and ipaddress.ip_address(value).is_global
    except ValueError: return False

def parse_html(html: str, source_url: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    for node in soup(["script", "style", "noscript", "template", "svg"]): node.decompose()
    title = soup.title.get_text(" ", strip=True) if soup.title else ""
    visible = soup.get_text(" ", strip=True)
    emails = set(EMAIL_RE.findall(visible))
    links = []
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if href.lower().startswith("mailto:"):
            emails.update(EMAIL_RE.findall(href[7:].split("?", 1)[0]))
            continue
        full = urldefrag(urljoin(source_url, href))[0]
        if urlsplit(full).scheme in ("http", "https"): links.append(full)
    urls = set(URL_RE.findall(visible))
    urls.update(links)
    domains = {urlsplit("https:" + u if u.lower().startswith("www.") else u).hostname.lower().rstrip(".") for u in urls if urlsplit("https:" + u if u.lower().startswith("www.") else u).hostname}
    domains.update(e.rsplit("@", 1)[1].lower() for e in emails)
    ips = {x for x in IP_RE.findall(visible) if public_ipv4(x)}
    for u in urls:
        h = urlsplit("https:" + u if u.lower().startswith("www.") else u).hostname or ""
        if public_ipv4(h): ips.add(h)
    return {"title": title, "text": visible, "links": list(dict.fromkeys(links)), "urls": sorted(urls), "emails": sorted(emails), "domains": sorted(domains), "ips": sorted(ips)}
