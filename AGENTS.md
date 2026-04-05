# AGENTS.md

## Cursor Cloud specific instructions

### Project overview

This is a Python-based AI assistant system ("珍爱网智慧助理 / Linh") that generates daily business health reports for Zhenai.com across 5 business lines (建信/电销/红娘/门店/APP). It fetches data from a remote API, generates HTML reports, and optionally sends them via email. See `SETUP.md` and `DEPLOY.md` for full documentation.

### Running report generators

Each business line has its own report generator script. Run with `--no-email` to skip email sending:

```
python3 generate_jianxin_full_report.py --date YYYY-MM-DD --no-email
python3 generate_telesale_full_report.py --date YYYY-MM-DD --no-email
python3 generate_hongniang_full_report.py --date YYYY-MM-DD --no-email
python3 generate_shop_full_report.py --date YYYY-MM-DD --no-email
python3 generate_app_full_report.py --date YYYY-MM-DD --no-email
```

Reports are output to `reports/` directory.

### Known issues

- `generate_telesale_full_report.py` has a pre-existing f-string syntax error on line 409 (invalid `{{}age{}` escape sequence). It will not run until fixed.
- `generate_hongniang_full_report.py` crashes with `ValueError: max() iterable argument is empty` when API returns empty data (no guard for empty `depts` list in `generate_html`).

### Credentials / secrets

The system requires `agent_system/config/facts.json` (gitignored). Copy from `facts.json.template` and fill in:
- `api.api_key` — Zhenai Data Platform API key
- `smtp.auth_code` — Tencent Exmail SMTP authorization code
- `smtp.from_email` — sender email address

Without valid API credentials, report scripts will still run but produce reports with zero/empty data. Without valid SMTP credentials, email sending will fail (scripts still complete when `--no-email` is used).

### Lint / syntax checking

No lint tooling is configured in the project. Use `python3 -m py_compile <file>` for syntax checks, or install `ruff` and run `python3 -m ruff check --select E9 .` for syntax-level linting.

### Testing

No automated test suite exists in this project. Validation is done by running report generators and inspecting output HTML files.
