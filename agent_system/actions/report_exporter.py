# -*- coding: utf-8 -*-
import os, sys, subprocess
from pathlib import Path
_ROOT = Path(__file__).resolve().parent.parent.parent
_REPORTS = _ROOT / "reports"

def export_html(html_content, filename, open_browser=True):
    _REPORTS.mkdir(parents=True, exist_ok=True)
    fp = _REPORTS / filename
    fp.write_text(html_content, encoding="utf-8")
    if open_browser: _open(str(fp))
    return str(fp)

def _open(path):
    url = "file://" + os.path.realpath(path)
    try:
        if sys.platform == "darwin":
            subprocess.Popen(["open", url], start_new_session=True, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except: pass
