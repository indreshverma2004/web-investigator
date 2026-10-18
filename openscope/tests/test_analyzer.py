from crawler.analyzer import analyze

def test_deduplicates_and_tracks_sources_and_edges():
    pages=[{"url":"https://a.test/","success":True,"origin":"https://a.test","data":{"emails":["x@a.test","x@a.test"],"domains":["a.test"],"urls":["https://a.test/"],"ips":[],"links":["https://a.test/b"]}}, {"url":"https://a.test/b","success":True,"origin":"https://a.test","data":{"emails":["x@a.test"],"domains":[],"urls":[],"ips":[],"links":[]}}]
    d=analyze(pages)
    e=next(x for x in d["entities"]["email"] if x["value"]=="x@a.test")
    assert e["count"]==3 and len(e["sources"])==2
    assert any(x["type"]=="links" and x["evidence"]=="https://a.test/" for x in d["graph"]["edges"])
