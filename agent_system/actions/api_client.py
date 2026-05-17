# -*- coding: utf-8 -*-
import requests
from agent_system.config import api_config

BASE_URL = "http://43.138.47.115:8600"

def _h():
    cfg = api_config()
    return {"X-API-Key": cfg.get("api_key", "")}

def _req(method, path, params=None):
    try:
        r = requests.request(method, f"{BASE_URL}{path}", headers=_h(), params=params, timeout=30)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"error": str(e), "rows": [], "row_count": 0, "columns": []}

def me(): return _req("GET", "/auth/me")
def daily(team, date=None, page=1, size=500):
    p = {"page": page, "page_size": size}
    if date: p["date"] = date
    return _req("GET", f"/api/v1/team/{team}/daily", p)
def trend(team, days=14): return _req("GET", f"/api/v1/team/{team}/trend", {"days": days})
def tables(team): return _req("GET", f"/api/v1/team/{team}/tables")
def query(team, table_role, date=None, page=1, size=500):
    p = {"page": page, "page_size": size, "table_role": table_role}
    if date: p["date"] = date
    return _req("GET", f"/api/v1/team/{team}/query", p)
def health(team=None):
    path = f"/api/v1/health/{team}" if team else "/api/v1/health/"
    return _req("GET", path)
def ad_daily(date=None):
    p = {}
    if date: p["date"] = date
    return _req("GET", "/api/v1/advertising/daily", p)
def ad_categories(): return _req("GET", "/api/v1/advertising/categories")
def ad_report(rid, date=None, page=1, size=500):
    p = {"page": page, "page_size": size}
    if date: p["date"] = date
    return _req("GET", f"/api/v1/advertising/report/{rid}", p)
def safe_float(v, d=0.0):
    if v is None: return d
    try: return float(str(v).replace(",","").replace("%","").strip())
    except: return d
def safe_int(v, d=0): return int(safe_float(v, d))

def parallel_fetch(calls):
    from concurrent.futures import ThreadPoolExecutor, as_completed
    if not calls:
        return []
    results = [None] * len(calls)
    with ThreadPoolExecutor(max_workers=min(len(calls), 8)) as ex:
        future_map = {ex.submit(fn): i for i, fn in enumerate(calls)}
        for future in as_completed(future_map):
            idx = future_map[future]
            try:
                results[idx] = future.result()
            except Exception as e:
                results[idx] = {"error": str(e), "rows": [], "row_count": 0, "columns": []}
    return results
