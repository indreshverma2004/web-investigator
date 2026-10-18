"""Aggregate entities, evidence and graph relations."""
from collections import Counter, defaultdict

def analyze(pages: list[dict]) -> dict:
    entities = {k: defaultdict(set) for k in ("email", "domain", "url", "ip")}
    counts = {k: Counter() for k in entities}
    edges = []
    nodes = {}
    for page in pages:
        if not page.get("success"): continue
        src, parsed = page["url"], page.get("data", {})
        pid = "page:" + src
        nodes[pid] = {"id": pid, "type": "page", "label": parsed.get("title") or src, "url": src}
        for typ, vals in (("email", parsed.get("emails", [])), ("domain", parsed.get("domains", [])), ("url", parsed.get("urls", [])), ("ip", parsed.get("ips", []))):
            for value in vals:
                entities[typ][value].add(src); counts[typ][value] += 1
                if typ in ("email", "domain", "ip"):
                    nid = typ + ":" + value
                    nodes[nid] = {"id": nid, "type": typ, "label": value, "value": value}
                    edges.append({"source": pid, "target": nid, "type": "contains" if typ in ("email", "ip") else "mentions", "evidence": src})
        for link in parsed.get("links", []):
            if link.startswith(page.get("origin", "")):
                target = "page:" + link
                nodes.setdefault(target, {"id": target, "type": "page", "label": link, "url": link})
                edges.append({"source": pid, "target": target, "type": "links", "evidence": src})
    result = {typ: [{"value": v, "count": counts[typ][v], "sources": sorted(srcs)} for v, srcs in sorted(items.items())] for typ, items in entities.items()}
    kept = list(nodes.values())[:250]
    kept_ids = {n["id"] for n in kept}
    kept_edges = [e for e in edges if e["source"] in kept_ids and e["target"] in kept_ids][:500]
    return {"entities": result, "graph": {"nodes": kept, "edges": kept_edges}}
