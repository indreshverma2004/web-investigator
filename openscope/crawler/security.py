"""URL and destination checks for public web crawling."""
from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlsplit, urlunsplit


class UnsafeDestination(ValueError):
    pass


def validate_url(url: str) -> str:
    if not isinstance(url, str) or not url.strip():
        raise UnsafeDestination("Enter a website URL.")
    value = url.strip()
    if "://" not in value:
        value = "https://" + value
    try:
        p = urlsplit(value)
        port = p.port
    except ValueError as exc:
        raise UnsafeDestination("The URL is malformed.") from exc
    if p.scheme.lower() not in ("http", "https") or not p.hostname:
        raise UnsafeDestination("Only complete HTTP or HTTPS website URLs are supported.")
    if p.username is not None or p.password is not None:
        raise UnsafeDestination("URLs containing credentials are not allowed.")
    host = p.hostname.rstrip(".").lower()
    if not host or host == "localhost" or host.endswith(".localhost") or host.endswith(".local"):
        raise UnsafeDestination("Local network destinations are not allowed.")
    try:
        addr = ipaddress.ip_address(host.strip("[]"))
    except ValueError:
        addr = None
    if addr and not addr.is_global:
        raise UnsafeDestination("Only publicly routable destinations are allowed.")
    netloc = f"[{host}]" if ":" in host else host
    if port and not ((p.scheme.lower() == "http" and port == 80) or (p.scheme.lower() == "https" and port == 443)):
        netloc += f":{port}"
    path = p.path or "/"
    return urlunsplit((p.scheme.lower(), netloc, path, p.query, ""))


def resolve_public(host: str, resolver=socket.getaddrinfo) -> list[str]:
    try:
        records = resolver(host, None, type=socket.SOCK_STREAM)
    except OSError as exc:
        raise UnsafeDestination("The website host could not be resolved.") from exc
    ips = list(dict.fromkeys(r[4][0].split("%", 1)[0] for r in records))
    if not ips:
        raise UnsafeDestination("The website host has no reachable address.")
    for raw in ips:
        try:
            ip = ipaddress.ip_address(raw)
        except ValueError as exc:
            raise UnsafeDestination("The website resolved to an invalid address.") from exc
        if not ip.is_global:
            raise UnsafeDestination("The website resolves to a non-public address.")
    return ips
