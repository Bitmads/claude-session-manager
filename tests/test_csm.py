#!/usr/bin/env python3
"""
Unit tests for cc-sessions — stdlib only, no pip.

Run:  python3 -m unittest discover -s tests -v
  or: python3 tests/test_csm.py
"""

import os
import sys
import json
import shutil
import pathlib
import tempfile
import unittest
import importlib.machinery
import importlib.util

# Load the cc-sessions script as a module named "ccs".
_ROOT = pathlib.Path(__file__).resolve().parent.parent
_loader = importlib.machinery.SourceFileLoader("ccs", str(_ROOT / "cc-sessions"))
_spec = importlib.util.spec_from_loader("ccs", _loader)
ccs = importlib.util.module_from_spec(_spec)
_loader.exec_module(ccs)


def _reset_config():
    """Force config to reload (it's cached in a module global)."""
    ccs._CONFIG = None
    os.environ.pop("CSM_CONFIG", None)


class TestNamingDefault(unittest.TestCase):
    """Default scheme: TICKET/PHASE.SESSION: Title"""

    def setUp(self):
        _reset_config()

    def tearDown(self):
        _reset_config()

    def test_parse(self):
        g = ccs._parse_title("SET-123/1.003: Implement settlements")
        self.assertEqual(g["ticket"], "SET-123")
        self.assertEqual(g["phase"], "1")
        self.assertEqual(g["session"], "003")
        self.assertEqual(g["title"], "Implement settlements")

    def test_parse_non_match(self):
        self.assertIsNone(ccs._parse_title("just a plain title"))

    def test_bump_session(self):
        self.assertEqual(
            ccs._bump_version("SET-123/1.001: Title"), "SET-123/1.002: Title")
        self.assertEqual(
            ccs._bump_version("VIS-2/3.009: Fix bug"), "VIS-2/3.010: Fix bug")

    def test_bump_strips_wrapping_quotes(self):
        self.assertEqual(
            ccs._bump_version('"SET-9/1.001: Quoted"'), "SET-9/1.002: Quoted")

    def test_group_key_strips_session(self):
        self.assertEqual(
            ccs.extract_task_key("SET-123/1.003: Title"), "SET-123/1: Title")

    def test_title_with_slash(self):
        # title text may itself contain "/"
        self.assertEqual(
            ccs._bump_version("VIS-2/1.001: Address/State selector"),
            "VIS-2/1.002: Address/State selector")


class TestNamingLegacy(unittest.TestCase):
    """Titles that don't match the scheme fall back to generic bumps."""

    def setUp(self):
        _reset_config()

    def test_v_suffix(self):
        self.assertEqual(ccs._bump_version("Legacy - v003"), "Legacy - v004")

    def test_hash_suffix(self):
        self.assertEqual(ccs._bump_version("Task - #3"), "Task - #4")

    def test_paren_suffix(self):
        self.assertEqual(ccs._bump_version("Task (v2)"), "Task (v3)")

    def test_plain_title_gets_v002(self):
        self.assertEqual(ccs._bump_version("plain title"), "plain title - v002")

    def test_extract_key_strips_status_and_version(self):
        self.assertEqual(ccs.extract_task_key("[DONE] Refactor - v003"), "Refactor")


class TestNamingCustomConfig(unittest.TestCase):
    """A user-supplied scheme via $CSM_CONFIG drives parse/bump/group."""

    def setUp(self):
        cfg = {
            "naming": {
                "pattern": r"^(?P<key>[A-Z]+-\d+) v(?P<v>\d+)$",
                "full_template": "{key} v{v}",
                "group_template": "{key}",
                "bump_field": "v",
            }
        }
        self.f = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False)
        json.dump(cfg, self.f)
        self.f.close()
        os.environ["CSM_CONFIG"] = self.f.name
        ccs._CONFIG = None

    def tearDown(self):
        os.unlink(self.f.name)
        _reset_config()

    def test_custom_bump(self):
        self.assertEqual(ccs._bump_version("ABC-42 v5"), "ABC-42 v6")
        self.assertEqual(ccs._bump_version("PROJ-1 v12"), "PROJ-1 v13")

    def test_custom_group(self):
        self.assertEqual(ccs.extract_task_key("ABC-42 v5"), "ABC-42")

    def test_non_matching_falls_back(self):
        self.assertEqual(
            ccs._bump_version("SET-1/1.001: x"), "SET-1/1.001: x - v002")


class TestNewInput(unittest.TestCase):
    """csm new normalizes any partial form to the full scheme."""

    def setUp(self):
        _reset_config()

    def test_forms(self):
        cases = {
            "SET-123 Implement settlements": ("SET-123", 1, 1, "Implement settlements"),
            "SET-123: Implement settlements": ("SET-123", 1, 1, "Implement settlements"),
            "SET-123/2 Implement settlements": ("SET-123", 2, 1, "Implement settlements"),
            "SET-123/2.005: Implement settlements": ("SET-123", 2, 5, "Implement settlements"),
            "ABC-1 Fix bug": ("ABC-1", 1, 1, "Fix bug"),
        }
        for text, expected in cases.items():
            self.assertEqual(ccs._parse_new_input(text), expected, text)

    def test_invalid(self):
        self.assertIsNone(ccs._parse_new_input("no ticket here"))


class TestStatusAndNotes(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self._old = ccs.NOTES_DIR
        ccs.NOTES_DIR = pathlib.Path(self.tmp)

    def tearDown(self):
        ccs.NOTES_DIR = self._old
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_default_open(self):
        self.assertEqual(ccs._get_task_status("never-set"), "open")

    def test_roundtrip_all_statuses(self):
        for st in ccs.STATUSES:
            ccs._set_task_status("T-1", st)
            self.assertEqual(ccs._get_task_status("T-1"), st)

    def test_invalid_status_ignored(self):
        ccs._set_task_status("T-1", "wip")
        ccs._set_task_status("T-1", "bogus")  # not in STATUSES → no-op
        self.assertEqual(ccs._get_task_status("T-1"), "wip")

    def test_status_preserved_when_note_added(self):
        ccs._set_task_status("T-1", "blocked")
        nf = ccs.NOTES_DIR / f"{ccs.sanitize('T-1')}.md"
        nf.write_text(nf.read_text() + "the body line\n")
        self.assertEqual(ccs._get_task_status("T-1"), "blocked")

    def test_note_body_strips_frontmatter(self):
        nf = ccs.NOTES_DIR / f"{ccs.sanitize('T-2')}.md"
        nf.write_text("---\nstatus: wip\n---\nthe real note body\n")
        self.assertEqual(ccs._get_task_note("T-2"), "the real note body")
        self.assertEqual(ccs._get_task_status("T-2"), "wip")

    def test_note_without_frontmatter(self):
        nf = ccs.NOTES_DIR / f"{ccs.sanitize('T-3')}.md"
        nf.write_text("plain note, no frontmatter\n")
        self.assertEqual(ccs._get_task_note("T-3"), "plain note, no frontmatter")
        self.assertEqual(ccs._get_task_status("T-3"), "open")


class TestAnsiUtils(unittest.TestCase):
    def test_vis_len_ignores_escapes(self):
        s = "\033[1;36mhello\033[0m"
        self.assertEqual(ccs._vis_len(s), 5)

    def test_truncate_counts_visible_only(self):
        s = "\033[36m" + "x" * 50 + "\033[0m"
        out = ccs._ansi_truncate(s, 10)
        self.assertEqual(ccs._vis_len(out), 10)
        self.assertTrue(out.endswith("\033[0m"))  # always reset

    def test_strip_wrapping_quotes(self):
        self.assertEqual(ccs._strip_wrapping_quotes('"hi"'), "hi")
        self.assertEqual(ccs._strip_wrapping_quotes("'hi'"), "hi")
        self.assertEqual(ccs._strip_wrapping_quotes("hi"), "hi")


class TestProjLabel(unittest.TestCase):
    def test_strips_noise_keeps_last(self):
        self.assertEqual(ccs.proj_label("-home-payments"), "payments")

    def test_keeps_last_two(self):
        self.assertEqual(ccs.proj_label("-srv-app-web"), "app/web")


if __name__ == "__main__":
    unittest.main(verbosity=2)
