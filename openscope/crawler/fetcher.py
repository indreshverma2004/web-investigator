"""Bounded crawler with public-IP pinning during each socket connection."""
from __future__ import annotations
import threading, time, socket
import ssl
from urllib.parse import urlsplit, urljoin
import requests
from requests.adapters import HTTPAdapter
from urllib.robotparser import RobotFileParser
from .security import validate_url, resolve_public, UnsafeDestination
from .parser import parse_html

USER_AGENT = "OpenScopeResearchBot/1.0 (+local public-site investigation; no form submission)"
MAX_BYTES = 2_000_000
_DNS_LOCK = threading.RLock()

class NativeTrustAdapter(HTTPAdapter):
    """Use Python's native trust store (Windows certificate store on Windows)."""
    def init_poolmanager(self, connections, maxsize, block=False, **pool_kwargs):
        pool_kwargs["ssl_context"] = ssl.create_default_context()
        return super().init_poolmanager(connections, maxsize, block=block, **pool_kwargs)

def safe_get(url: str, timeout: float = 8) -> requests.Response:
    url = validate_url(url)
    p = urlsplit(url); host = p.hostname
    ips = resolve_public(host)
    # requests resolves at connect time; temporarily pin that lookup to the prevalidated set.
    # The lock keeps simultaneous OpenScope requests from changing one another's resolver mapping.
    original = socket.getaddrinfo
    def pinned(name, port, *args, **kwargs):
        if str(name).lower().rstrip(".") == host.lower().rstrip("."):
            infos = []
            for ip in ips:
                infos.extend(original(ip, port, *args, **kwargs))
            return infos
        return original(name, port, *args, **kwargs)
    with _DNS_LOCK:
        socket.getaddrinfo = pinned
        try:
            s = requests.Session(); s.trust_env = False
            s.mount("https://", NativeTrustAdapter())
            response = s.get(url, headers={"User-Agent": USER_AGENT}, timeout=timeout, allow_redirects=False, stream=True)
            response._openscope_session = s
            return response
        except Exception:
            raise
        finally:
            socket.getaddrinfo = original

def fetch_limited(url: str, timeout=8, allowed_origin: str | None = None, html_only: bool = True) -> tuple[int, str, str]:
    current = validate_url(url)
    for _ in range(6):
        response = safe_get(current, timeout)
        status = response.status_code
        if status in (301, 302, 303, 307, 308) and response.headers.get("Location"):
            nxt = validate_url(urljoin(current, response.headers["Location"]))
            response.close(); response._openscope_session.close()
            if allowed_origin and (urlsplit(nxt).scheme + "://" + urlsplit(nxt).netloc) != allowed_origin:
                raise UnsafeDestination("Redirect outside the original website was blocked.")
            current = nxt
            continue
        ctype = response.headers.get("Content-Type", "").lower()
        if status == 200 and html_only and "text/html" not in ctype and "application/xhtml+xml" not in ctype:
            response.close(); response._openscope_session.close()
            raise ValueError("Skipped non-HTML resource")
        chunks=[]; size=0
        if status == 200:
            for chunk in response.iter_content(65536):
                size += len(chunk)
                if size > MAX_BYTES: raise ValueError("Page exceeded the 2 MB response limit")
                chunks.append(chunk)
        response.close(); response._openscope_session.close()
        return status, b"".join(chunks).decode(response.encoding or "utf-8", errors="replace"), current
    raise ValueError("Too many redirects")

def crawl(start_url: str, limit: int, cancelled: threading.Event, on_update):
    start = validate_url(start_url); start_origin = urlsplit(start).scheme + "://" + urlsplit(start).netloc
    robots = RobotFileParser(); robots.set_url(urljoin(start_origin, "/robots.txt"))
    try:
        st, body, _ = fetch_limited(robots.url, allowed_origin=start_origin, html_only=False)
        if st == 200: robots.parse(body.splitlines())
        else: robots.parse([])
    except Exception: robots.parse([])
    queue=[start]; seen=set(); pages=[]
    while queue and len(seen) < limit and not cancelled.is_set():
        url=queue.pop(0)
        try: url=validate_url(url)
        except UnsafeDestination: continue
        if url in seen or (urlsplit(url).scheme + "://" + urlsplit(url).netloc) != start_origin: continue
        seen.add(url)
        row={"url":url,"title":"","status":None,"success":False,"origin":start_origin}
        if not robots.can_fetch(USER_AGENT, url):
            row["error"]="Disallowed by robots.txt"; pages.append(row); on_update(pages); continue
        try:
            status, html, final = fetch_limited(url, allowed_origin=start_origin)
            row["status"]=status; row["url"]=final
            if status == 200:
                data=parse_html(html, final); row.update(title=data["title"], success=True, data=data)
                for link in data["links"]:
                    if (urlsplit(link).scheme + "://" + urlsplit(link).netloc) == start_origin and link not in seen and link not in queue: queue.append(link)
            else: row["error"]=f"HTTP {status}"
        except Exception as exc:
            if isinstance(exc, UnsafeDestination): row["error"] = str(exc)
            elif isinstance(exc, ValueError): row["error"] = str(exc)
            elif isinstance(exc, requests.exceptions.SSLError): row["error"] = "HTTPS certificate could not be verified by this computer."
            elif isinstance(exc, requests.exceptions.Timeout): row["error"] = "Request timed out."
            elif isinstance(exc, requests.exceptions.ConnectionError): row["error"] = "Could not connect to the website."
            else: row["error"] = "Request failed."
        pages.append(row); on_update(pages); time.sleep(0.15)
    return pages
