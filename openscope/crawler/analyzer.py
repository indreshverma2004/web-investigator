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
    # Keep every fetched page, then add the most frequently observed entities.
    # Full entity sets remain in the tables so the graph stays readable.
    fetched_urls = {p["url"] for p in pages if p.get("success")}
    page_nodes = [n for n in nodes.values() if n["type"] == "page" and n.get("url") in fetched_urls]
    linked_pages = [n for n in nodes.values() if n["type"] == "page" and n.get("url") not in fetched_urls]
    linked_pages.sort(key=lambda n: sum(1 for e in edges if e["target"] == n["id"]), reverse=True)
    def entity_nodes(typ, limit):
        vals = [n for n in nodes.values() if n["type"] == typ]
        vals.sort(key=lambda n: (counts[typ].get(n["value"], 0), len(entities[typ].get(n["value"], set()))), reverse=True)
        return vals[:limit]
    kept = page_nodes + linked_pages[:12] + entity_nodes("domain", 30) + entity_nodes("email", 20) + entity_nodes("ip", 10)
    kept_ids = {n["id"] for n in kept}
    kept_edges = [e for e in edges if e["source"] in kept_ids and e["target"] in kept_ids][:500]
    return {"entities": result, "graph": {"nodes": kept, "edges": kept_edges}}
