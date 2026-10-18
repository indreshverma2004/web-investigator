from crawler.parser import parse_html

def test_extracts_visible_entities_and_links():
    html='''<html><head><title>About</title><script>hidden@example.com</script></head><body><p>Contact team@example.org and 8.8.8.8</p><a href="/contact">Contact</a><a href="mailto:hello@example.org">Email</a><a href="https://outside.example/path">Other</a><form><input value="secret@example.org"></form></body></html>'''
    d=parse_html(html,"https://site.example/")
    assert d["title"]=="About"
    assert "team@example.org" in d["emails"] and "hello@example.org" in d["emails"]
    assert "hidden@example.com" not in d["emails"] and "secret@example.org" not in d["emails"]
    assert "8.8.8.8" in d["ips"] and "127.0.0.1" not in d["ips"]
    assert "site.example" in d["domains"] and "https://site.example/contact" in d["links"]

def test_filters_non_public_ip_and_collects_text_urls():
    d=parse_html("<p>Use https://docs.example/a and 10.1.2.3</p>","https://site.example")
    assert d["urls"]==["https://docs.example/a"]
    assert d["ips"]==[]
