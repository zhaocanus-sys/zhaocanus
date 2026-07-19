import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agent_system.actions import report_exporter


class ReportExporterTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.report_dir = Path(self.temp_dir.name) / "nested" / "reports"

    def test_export_html_creates_directory_and_writes_utf8_without_opening(self):
        with patch.object(report_exporter, "_REPORTS", self.report_dir), patch.object(
            report_exporter, "_open"
        ) as open_report:
            result = report_exporter.export_html(
                "<html><body>经营日报</body></html>",
                "daily.html",
                open_browser=False,
            )

        expected = self.report_dir / "daily.html"
        self.assertEqual(result, str(expected))
        self.assertEqual(
            expected.read_text(encoding="utf-8"),
            "<html><body>经营日报</body></html>",
        )
        open_report.assert_not_called()

    def test_export_html_opens_only_after_successful_write(self):
        with patch.object(report_exporter, "_REPORTS", self.report_dir), patch.object(
            report_exporter, "_open"
        ) as open_report:
            result = report_exporter.export_html("<html>ok</html>", "daily.html")

        self.assertEqual(result, str(self.report_dir / "daily.html"))
        open_report.assert_called_once_with(str(self.report_dir / "daily.html"))

    def test_export_html_propagates_write_failure_and_does_not_open(self):
        with patch.object(report_exporter, "_REPORTS", self.report_dir), patch.object(
            Path, "write_text", side_effect=OSError("disk full")
        ), patch.object(report_exporter, "_open") as open_report:
            with self.assertRaisesRegex(OSError, "disk full"):
                report_exporter.export_html("<html>failed</html>", "daily.html")

        open_report.assert_not_called()


if __name__ == "__main__":
    unittest.main()
