import socket
import pytest
from crawler.security import validate_url, resolve_public, UnsafeDestination

def test_normalizes_and_accepts_public_url():
    assert validate_url("example.com") == "https://example.com/"
    assert validate_url("HTTP://example.com/a#frag") == "http://example.com/a"

@pytest.mark.parametrize("url", ["http://localhost", "http://127.0.0.1", "http://10.0.0.1", "http://169.254.1.2", "ftp://example.com", "http://user:pass@example.com"])
def test_rejects_unsafe_urls(url):
    with pytest.raises(UnsafeDestination): validate_url(url)

def test_rejects_private_dns_and_accepts_public_dns():
    def private(*a, **k): return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("192.168.1.2", 0))]
    def public(*a, **k): return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("8.8.8.8", 0))]
    with pytest.raises(UnsafeDestination): resolve_public("example.test", private)
    assert resolve_public("example.test", public) == ["8.8.8.8"]

