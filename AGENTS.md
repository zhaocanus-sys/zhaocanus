# AGENTS.md

## Cursor Cloud specific instructions

### What this project is
A Python 3.12 toolkit that pulls daily operations data from a live HTTP API and renders
standalone HTML "体检报告" (business health reports) for five business lines. Entry points are the
top-level scripts `generate_jianxin_full_report.py`, `generate_hongniang_full_report.py`,
`generate_app_full_report.py`, `generate_shop_full_report.py`, and `generate_telesale_full_report.py`.
Shared logic lives under `agent_system/` (`actions/api_client.py`, `actions/email_sender.py`,
`actions/report_exporter.py`, `config/`). Generated HTML is written to `reports/`.
Standard run commands are documented in `SETUP.md` / `DEPLOY.md`.

### Dependencies / build / test / lint
- Only runtime dependency is `requests` (`requirements.txt`); the update script installs it. There is
  no build step, no test suite, no linter, and no git hooks in this repo.

### Non-obvious caveats (read before running anything)
- **Running a report sends a REAL email by default.** Every `generate_*.py` `main()` unconditionally
  calls `send_report_email(...)`, which logs in to Tencent SMTP using the credentials in
  `agent_system/config/facts.json` and emails live recipients (`zhao.can@zhenai.com`, cc
  `xiaoying.tian@zhenai.com`). The `--no-email` flag shown in the docs is **not implemented** in
  `main()` and is silently ignored. To exercise a report without sending mail, do not run `main()`
  directly — instead call the module's data + render functions (`daily(...)`/`query(...)` →
  `parse_rows` → `generate_html(...)` → `export_html(..., open_browser=False)`), or monkeypatch
  `send_report_email` to a no-op before calling `main()`.
- **`generate_telesale_full_report.py` does not run as-is.** It has a Python `SyntaxError` (malformed
  f-string near line 409), so it fails to import/compile. The other four generators compile and run.
- `agent_system/config/facts.json` is gitignored but is already present in this environment with a
  working API key and SMTP auth code. Verify API connectivity with:
  `python3 -c "from agent_system.actions.api_client import me; print(me())"` (expect
  `{'username': 'zhao_boss', ...}`).
- API base URL is `http://43.138.47.115:8600`. `2026-02-27` is a known date that returns data; weekends
  /holidays may return empty rows.
- `report_exporter.export_html` only opens a browser on macOS (`sys.platform == "darwin"`); on Linux the
  browser-open is a no-op, so `open_browser=True` is safe in headless/cloud runs.
