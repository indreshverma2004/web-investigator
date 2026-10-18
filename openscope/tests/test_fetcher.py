import threading
import pytest
import requests
from crawler import fetcher
from crawler.security import UnsafeDestination

def test_crawl_limit_and_duplicate_links(monkeypatch):
    seen=[]
    def fake(url, **kwargs):
        seen.append(url)
        if url.endswith('robots.txt'): return 404,'',''
        return 200,'<title>Page</title><a href="/next">Next</a><a href="/next#frag">Again</a>',url
    monkeypatch.setattr(fetcher,'fetch_limited',fake)
    updates=[]
    pages=fetcher.crawl('https://example.com/',2,threading.Event(),lambda p:updates.append(len(p)))
    assert len(pages)==2 and len(set(p['url'] for p in pages))==2
    assert updates==[1,2]

def test_http_failure_and_cancelled_scan(monkeypatch):
    def failing(url,**kwargs):
        if url.endswith('robots.txt'): return 404,'',''
        return 503,'',url
    monkeypatch.setattr(fetcher,'fetch_limited',failing)
    pages=fetcher.crawl('https://example.com/',3,threading.Event(),lambda p:None)
    assert pages[0]['status']==503 and not pages[0]['success']
    stop=threading.Event(); stop.set()
    assert fetcher.crawl('https://example.com/',3,stop,lambda p:None)==[]

def test_request_timeout_is_recorded_as_failed_page(monkeypatch):
    def timeout(url,**kwargs):
        if url.endswith('robots.txt'): return 404,'',''
        raise requests.exceptions.Timeout('timeout')
    monkeypatch.setattr(fetcher,'fetch_limited',timeout)
    pages=fetcher.crawl('https://example.com/',1,threading.Event(),lambda p:None)
    assert len(pages)==1 and pages[0]['success'] is False
    assert pages[0]['error']=='Request timed out.'

def test_external_redirect_rejected_before_following(monkeypatch):
    class Response:
        status_code=302; headers={'Location':'http://127.0.0.1/admin'}
        def close(self): pass
    Response._openscope_session=type('S',(),{'close':lambda self:None})()
    monkeypatch.setattr(fetcher,'safe_get',lambda *a,**k:Response())
    with pytest.raises(UnsafeDestination): fetcher.fetch_limited('https://example.com/',allowed_origin='https://example.com')
