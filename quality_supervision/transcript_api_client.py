# -*- coding: utf-8 -*-
from agent_system.config import facts
def is_api_configured():
    return bool(facts().get("transcript_api",{}).get("base_url","").strip())
def fetch_transcripts(date=None, line=None): return []
