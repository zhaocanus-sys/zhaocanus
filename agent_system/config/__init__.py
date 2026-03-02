import json, os
from pathlib import Path
_D = Path(__file__).resolve().parent
_cache = {}
def _load(p, k):
    if k not in _cache:
        _cache[k] = json.loads(p.read_text(encoding='utf-8')) if p.exists() else {}
    return _cache[k]
def facts(): return _load(_D/'facts.json', 'facts')
def preferences(): return _load(_D/'preferences.json', 'prefs')
def smtp_config(): return facts().get('smtp', {})
def contacts(): return facts().get('contacts', {})
def dept_managers(): return facts().get('dept_managers', {})
def api_config(): return facts().get('api', {})
def reload(): _cache.clear()
