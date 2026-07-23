import json
import tokenize
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PREFERENCES_PATH = ROOT / "agent_system" / "config" / "preferences.json"


def load_redline_terms():
    with PREFERENCES_PATH.open(encoding="utf-8") as handle:
        preferences = json.load(handle)
    return set(preferences["report_standards"]["redline_words"])


def report_template_paths():
    paths = sorted(ROOT.glob("generate_*_full_report.py"))
    paths.extend(
        [
            ROOT / "app_report_html.py",
            ROOT / "agent_system" / "agents" / "data_expert.py",
        ]
    )
    return paths


def string_literals(path):
    """Yield source string tokens without matching comments or identifiers."""
    with tokenize.open(path) as handle:
        for token in tokenize.generate_tokens(handle.readline):
            if token.type == tokenize.STRING:
                yield token.string


class ReportOutputRedlineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.redline_terms = load_redline_terms()
        if not cls.redline_terms:
            raise AssertionError("report redline list must not be empty")

    def assertNoRedlineTerms(self, text, source):
        leaked = sorted(term for term in self.redline_terms if term in text)
        self.assertEqual([], leaked, f"{source} contains external-output redline terms")

    def test_report_template_literals_do_not_expose_internal_terms(self):
        paths = report_template_paths()
        self.assertGreaterEqual(len(paths), 7, "expected all report output templates")

        for path in paths:
            with self.subTest(path=path.relative_to(ROOT)):
                self.assertTrue(path.is_file())
                self.assertNoRedlineTerms(
                    "\n".join(string_literals(path)),
                    path.relative_to(ROOT),
                )

    def test_committed_report_artifacts_do_not_expose_internal_terms(self):
        report_paths = sorted((ROOT / "reports").glob("*.html"))
        self.assertTrue(report_paths, "expected committed HTML report artifacts")

        for path in report_paths:
            with self.subTest(path=path.name):
                self.assertNoRedlineTerms(
                    path.read_text(encoding="utf-8"),
                    path.relative_to(ROOT),
                )


if __name__ == "__main__":
    unittest.main()
