from __future__ import annotations
import csv, io, json, threading, uuid
from datetime import datetime, timezone
from flask import Flask, jsonify, render_template, request, Response, abort
from crawler.security import validate_url, UnsafeDestination
from crawler.fetcher import crawl
from crawler.analyzer import analyze

app=Flask(__name__)
STORE={}; LOCK=threading.RLock()

def public_state(item):
    pages=item["pages"]
    findings=analyze(pages)
    return {"id":item["id"],"status":item["status"],"progress":{"scanned":len(pages),"limit":item["limit"]},"started_at":item["started_at"],"finished_at":item.get("finished_at"),"pages":pages,"failed":[p for p in pages if not p["success"]],"summary":{"pages_scanned":sum(p["success"] for p in pages),"domains":len(findings["entities"]["domain"]),"emails":len(findings["entities"]["email"]),"urls":len(findings["entities"]["url"])},**findings,"error":item.get("error")}

def run_scan(item, url):
    def update(pages):
        with LOCK: item["pages"]=[dict(p) for p in pages]
    try:
        pages=crawl(url,item["limit"],item["cancel"],update)
        with LOCK:
            item["pages"]=pages; item["status"]="cancelled" if item["cancel"].is_set() else "completed"
    except Exception as exc:
        with LOCK: item["status"]="failed"; item["error"]=str(exc) if isinstance(exc, UnsafeDestination) else "Investigation could not be completed."
    finally:
        with LOCK: item["finished_at"]=datetime.now(timezone.utc).isoformat()

@app.get("/")
def index(): return render_template("index.html")
@app.get("/api/health")
def health(): return jsonify(status="ok", application="OpenScope")
@app.post("/api/investigations")
def start():
    data=request.get_json(silent=True) or request.form
    try: url=validate_url(data.get("url", ""))
    except UnsafeDestination as exc: return jsonify(error=str(exc)),400
    try: limit=int(data.get("max_pages",20))
    except (TypeError,ValueError): return jsonify(error="Page limit must be a number."),400
    if not 1 <= limit <= 30: return jsonify(error="Page limit must be between 1 and 30."),400
    item={"id":uuid.uuid4().hex,"status":"running","limit":limit,"pages":[],"cancel":threading.Event(),"started_at":datetime.now(timezone.utc).isoformat()}
    with LOCK: STORE[item["id"]]=item
    threading.Thread(target=run_scan,args=(item,url),daemon=True).start()
    return jsonify(id=item["id"],status="running"),202
@app.get("/api/investigations/<iid>")
def get_investigation(iid):
    with LOCK: item=STORE.get(iid)
    if not item: return jsonify(error="Investigation not found."),404
    with LOCK: return jsonify(public_state(item))
@app.post("/api/investigations/<iid>/cancel")
def cancel(iid):
    with LOCK: item=STORE.get(iid)
    if not item: return jsonify(error="Investigation not found."),404
    if item["status"]=="running": item["cancel"].set()
    return jsonify(status="cancelling" if item["status"]=="running" else item["status"])
@app.get("/api/investigations/<iid>/export.json")
def export_json(iid):
    with LOCK: item=STORE.get(iid)
    if not item: abort(404)
    return Response(json.dumps(public_state(item),indent=2),mimetype="application/json",headers={"Content-Disposition":f"attachment; filename=openscope-{iid}.json"})
@app.get("/api/investigations/<iid>/export.csv")
def export_csv(iid):
    with LOCK: item=STORE.get(iid)
    if not item: abort(404)
    data=public_state(item); out=io.StringIO(); w=csv.writer(out); w.writerow(["type","value","occurrences","source_urls"])
    for typ,vals in data["entities"].items():
        for e in vals: w.writerow([typ,e["value"],e["count"]," | ".join(e["sources"])])
    return Response(out.getvalue(),mimetype="text/csv",headers={"Content-Disposition":f"attachment; filename=openscope-{iid}.csv"})
if __name__=="__main__": app.run(debug=False, threaded=True)
