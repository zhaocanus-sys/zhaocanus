# -*- coding: utf-8 -*-
MUST_SAY = {"hongniang": ["价格","收费","退费","合同","服务期","冷静期"], "kefu": ["价格","退费","投诉渠道"]}
FORBIDDEN = ["保证找到","一定能","包成功","先付款再看"]
def verify_transcript(text, line="hongniang"):
    r = {"pass": True, "issues": []}
    for kw in MUST_SAY.get(line, []):
        if kw not in text: r["pass"]=False; r["issues"].append(f"必说缺失：{kw}")
    for w in FORBIDDEN:
        if w in text: r["pass"]=False; r["issues"].append(f"禁止用语：{w}")
    return r
