import io
import pytest
import app as module

@pytest.fixture
def client(monkeypatch):
    def fake_crawl(url,limit,cancel,on_update):
        pages=[{"url":url,"title":"Example","status":200,"success":True,"origin":"https://example.com","data":{"emails":["hello@example.com"],"domains":["example.com"],"urls":[url],"ips":[],"links":[]}}]
        on_update(pages); return pages
    monkeypatch.setattr(module,"crawl",fake_crawl)
    module.STORE.clear(); module.app.config.update(TESTING=True)
    return module.app.test_client()

def test_health_validation_and_scan_exports(client):
    assert client.get('/api/health').status_code==200
    assert client.post('/api/investigations',json={"url":"http://localhost"}).status_code==400
    assert client.post('/api/investigations',json={"url":"example.com","max_pages":31}).status_code==400
    r=client.post('/api/investigations',json={"url":"example.com","max_pages":3}); assert r.status_code==202
    iid=r.json['id']; state=client.get('/api/investigations/'+iid).get_json()
    # Worker may finish asynchronously; wait briefly without any network dependency.
    import time
    for _ in range(50):
        state=client.get('/api/investigations/'+iid).get_json()
        if state['status']!='running': break
        time.sleep(.01)
    assert state['pages'][0]['title']=='Example'
    assert client.get(f'/api/investigations/{iid}/export.json').mimetype=='application/json'
    csv=client.get(f'/api/investigations/{iid}/export.csv')
    assert csv.status_code==200 and b'hello@example.com' in csv.data

def test_not_found_and_cancel(client):
    assert client.get('/api/investigations/missing').status_code==404
    assert client.post('/api/investigations/missing/cancel').status_code==404

def test_cancel_active_investigation(client,monkeypatch):
    import threading
    started=threading.Event(); release=threading.Event(); observed=[]
    def waiting(url,limit,cancel,on_update):
        observed.append(cancel); started.set(); release.wait(2); return []
    monkeypatch.setattr(module,'crawl',waiting)
    response=client.post('/api/investigations',json={'url':'example.com','max_pages':1})
    assert response.status_code==202 and started.wait(1)
    iid=response.json['id']
    assert client.post(f'/api/investigations/{iid}/cancel').status_code==200
    assert observed[0].is_set()
    release.set()

