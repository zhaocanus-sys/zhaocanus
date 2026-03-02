# -*- coding: utf-8 -*-
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from agent_system.config import smtp_config, contacts

def _cfg():
    c = smtp_config()
    return {"host": c.get("host","smtp.exmail.qq.com"), "port": c.get("port",465),
            "from_email": c.get("from_email",""), "auth_code": c.get("auth_code",""),
            "from_name": c.get("from_name","智慧助理")}

def send_email(subject, to, cc=None, body_text="", body_html="", html_template_path="", from_name=""):
    cfg = _cfg()
    if not cfg["from_email"] or not cfg["auth_code"]: return False
    cc = cc or []
    msg = MIMEMultipart("alternative")
    msg["From"] = f"{from_name or cfg['from_name']} <{cfg['from_email']}>"
    msg["To"] = ", ".join(to)
    if cc: msg["Cc"] = ", ".join(cc)
    msg["Subject"] = subject
    if html_template_path:
        p = Path(html_template_path)
        if p.exists(): body_html = p.read_text(encoding="utf-8")
    if body_text: msg.attach(MIMEText(body_text, "plain", "utf-8"))
    if body_html: msg.attach(MIMEText(body_html, "html", "utf-8"))
    try:
        with smtplib.SMTP_SSL(cfg["host"], cfg["port"], timeout=15) as s:
            s.login(cfg["from_email"], cfg["auth_code"])
            s.sendmail(cfg["from_email"], list(set(to+cc)), msg.as_string())
        return True
    except Exception as e:
        print(f"邮件发送失败: {e}"); return False

def send_report_email(subject, html_content, to="", cc=""):
    cfg = _cfg()
    c = contacts()
    t = to or c.get("zhao_coo",{}).get("email", cfg["from_email"])
    cc_addr = cc or c.get("tian_xiaoying",{}).get("email","")
    return send_email(subject, [t], [cc_addr] if cc_addr else [], body_html=html_content, from_name="Data Expert")
