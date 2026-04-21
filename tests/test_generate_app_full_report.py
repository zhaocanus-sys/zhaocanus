import datetime

import generate_app_full_report as app_report


def test_build_trend_data_groups_by_day_and_computes_derived_metrics():
    trend_rows = [
        {
            "ftime": "20260226120000",
            "amt": "100",
            "pay_num": "5",
            "active_members": "100",
            "refund_money": "2",
            "retain_1d": "30",
        },
        {
            "ftime": "20260225100000",
            "amt": "50",
            "pay_num": "2",
            "active_members": "40",
            "refund_money": "1",
            "retain_1d": "10",
        },
        {
            "ftime": "20260226090000",
            "amt": "30",
            "pay_num": "3",
            "active_members": "50",
            "refund_money": "0",
            "retain_1d": "5",
        },
    ]

    result = app_report.build_trend_data(trend_rows)

    assert [item["dt"] for item in result] == ["2026-02-25", "2026-02-26"]
    assert result[0]["amt"] == 50.0
    assert result[0]["pay_num"] == 2.0
    assert result[1]["amt"] == 130.0
    assert result[1]["pay_num"] == 8.0
    assert result[1]["active_members"] == 150.0
    assert result[1]["refund_money"] == 2.0
    assert result[1]["retain_1d"] == 35.0
    assert result[1]["arpu"] == 16.25
    assert result[1]["pay_rate"] == (8.0 / 150.0 * 100.0)


def test_build_trend_data_returns_zero_for_division_by_zero_cases():
    trend_rows = [
        {
            "ftime": "20260227",
            "amt": "10",
            "pay_num": "0",
            "active_members": "0",
            "refund_money": "1",
            "retain_1d": "0",
        }
    ]

    result = app_report.build_trend_data(trend_rows)

    assert len(result) == 1
    assert result[0]["arpu"] == 0
    assert result[0]["pay_rate"] == 0


def test_main_fetches_exact_10_day_trend_and_passes_rows(monkeypatch):
    requested_dates = []
    captured = {}

    def fake_daily(team, date=None, page=1, size=500):
        assert team == "app"
        requested_dates.append(date)
        day_num = int(date[-2:]) if date else 0
        return {
            "rows": [
                {
                    "amt": str(day_num * 100),
                    "pay_num": "10",
                    "active_members": "100",
                    "refund_money": "1",
                    "retain_1d": "50",
                }
            ]
        }

    def fake_generate_html(today_rows, prev_rows, trend_rows_raw, date_display):
        captured["today_rows"] = today_rows
        captured["prev_rows"] = prev_rows
        captured["trend_rows"] = trend_rows_raw
        captured["date_display"] = date_display
        return "<html>ok</html>"

    def fake_export_html(html_content, filename, open_browser=True):
        captured["filename"] = filename
        captured["html_content"] = html_content
        return "/tmp/APP_Full_2026-03-10.html"

    def fake_send_report_email(subject, html_content):
        captured["subject"] = subject
        captured["email_html"] = html_content
        return True

    monkeypatch.setattr(app_report, "daily", fake_daily)
    monkeypatch.setattr(app_report, "generate_html", fake_generate_html)
    monkeypatch.setattr(app_report, "export_html", fake_export_html)
    monkeypatch.setattr(app_report, "send_report_email", fake_send_report_email)
    monkeypatch.setattr(
        app_report.sys,
        "argv",
        ["generate_app_full_report.py", "--date", "2026-03-10"],
    )

    app_report.main()

    assert len(requested_dates) == 12
    assert requested_dates[0] == "20260310"
    assert requested_dates[1] == "20260309"

    expected_trend_dates = [
        (datetime.datetime(2026, 3, 10) - datetime.timedelta(days=delta)).strftime(
            "%Y%m%d"
        )
        for delta in range(9, -1, -1)
    ]
    assert requested_dates[2:] == expected_trend_dates

    assert captured["date_display"] == "2026-03-10"
    assert len(captured["today_rows"]) == 1
    assert len(captured["prev_rows"]) == 1
    assert len(captured["trend_rows"]) == 10
    assert [row["ftime"] for row in captured["trend_rows"]] == expected_trend_dates
    assert captured["filename"] == "APP_Full_2026-03-10.html"
    assert captured["subject"] == "📱 APP全量体检报告 2026-03-10"
    assert captured["email_html"] == "<html>ok</html>"
