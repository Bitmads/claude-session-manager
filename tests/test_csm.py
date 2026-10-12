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



class TestHopPrompt(unittest.TestCase):
    OLD = ("Read the previous session transcript at /t/x.jsonl (JSONL format: user messages in "
           "type=user message.content, assistant messages in type=assistant message.content[].text). ")

    def test_without_handoff_is_the_original_prompt(self):
        self.assertEqual(ccs._hop_prompt("T", "id", "/t/x.jsonl"),
                         self.OLD + "Continue where we left off.")

    def test_handoff_is_added_not_a_replacement(self):
        out = ccs._hop_prompt("T", "id", "/t/x.jsonl", "/h/HANDOFF.md")
        self.assertTrue(out.startswith(self.OLD))
        self.assertIn("/h/HANDOFF.md", out)
        self.assertNotIn("grep", out)

    def test_message_appended_verbatim(self):
        out = ccs._hop_prompt("T", "id", "/t/x.jsonl", "/h/H.md", "don't deploy yet")
        self.assertTrue(out.startswith(self.OLD))
        self.assertTrue(out.endswith("Message from the user for this session:\ndon't deploy yet"))

    def test_no_message_leaves_prompt_unchanged(self):
        self.assertEqual(ccs._hop_prompt("T", "id", "/t/x.jsonl", None, None),
                         ccs._hop_prompt("T", "id", "/t/x.jsonl"))


class TestFindHopSession(unittest.TestCase):
    S = [
        {"session_id": "aaa111", "title": "SET-1/1.001: X", "cwd": "/p", "last_ts": "2026-01-02", "transcript": "/t/aaa111.jsonl"},
        {"session_id": "bbb222", "title": "SET-2/1.001: Y", "cwd": "/p", "last_ts": "2026-01-03", "transcript": "/t/bbb222.jsonl"},
    ]

    def test_current_session_beats_newer_session_in_same_cwd(self):
        self.assertEqual(ccs._find_hop_session(self.S, None, "aaa111", "/p")["session_id"], "aaa111")

    def test_current_id_matches_transcript_filename(self):
        s = [dict(self.S[0], session_id="other")]
        self.assertIs(ccs._find_hop_session(s, None, "aaa111", "/p"), s[0])

    def test_falls_back_to_newest_in_cwd_without_current_id(self):
        self.assertEqual(ccs._find_hop_session(self.S, None, None, "/p")["session_id"], "bbb222")

    def test_query_by_id_prefix_then_title(self):
        self.assertEqual(ccs._find_hop_session(self.S, "bbb")["session_id"], "bbb222")
        self.assertEqual(ccs._find_hop_session(self.S, "set-1/1")["session_id"], "aaa111")
        self.assertIsNone(ccs._find_hop_session(self.S, "nope"))

    def test_exact_title_beats_substring(self):
        s = [dict(self.S[0], session_id="ccc", title="SET-1/1.001: X v2"), self.S[0]]
        self.assertEqual(ccs._find_hop_session(s, "SET-1/1.001: X")["session_id"], "aaa111")


class TestPickerKeys(unittest.TestCase):
    K = staticmethod(lambda c, searching=False: ccs._key_action(ord(c) if isinstance(c, str) else c, searching))

    def test_letters_are_commands_outside_search(self):
        for key, act in {"h": "hop", "n": "new", "r": "rename", "o": "note", "s": "status",
                         "d": "delete", "p": "panel", "/": "search", "?": "help", "q": "quit"}.items():
            self.assertEqual(self.K(key), act)
        self.assertIsNone(self.K("z"))

    def test_letters_are_text_while_searching(self):
        for key in "hnrosd/?q z":
            self.assertEqual(self.K(key, True), "type")

    def test_esc_and_backspace_depend_on_mode(self):
        self.assertEqual(self.K(27), "quit")
        self.assertEqual(self.K(27, True), "clear")
        self.assertEqual(self.K(127, True), "backspace")
        self.assertIsNone(self.K(127))

    def test_ctrl_keys_work_in_both_modes(self):
        for code, act in {6: "search", 7: "hop", 20: "new", 5: "rename", 15: "note",
                          19: "status", 24: "delete", 18: "refresh", 4: "panel", 10: "open"}.items():
            self.assertEqual(self.K(code), act)
            self.assertEqual(self.K(code, True), act)

    def test_every_action_in_help_is_reachable(self):
        acts = set(ccs._KEYS_ANY.values()) | set(ccs._KEYS_NORMAL.values())
        for needed in ("hop", "new", "rename", "note", "status", "delete", "panel", "search", "help"):
            self.assertIn(needed, acts)


class TestHopPromptHook(unittest.TestCase):
    """Stop hook: ask once per session when context reaches the threshold."""

    def setUp(self):
        _reset_config()
        self.tmp = tempfile.TemporaryDirectory()
        d = pathlib.Path(self.tmp.name)
        self.cfg = d / "csm.json"
        os.environ["CSM_CONFIG"] = str(self.cfg)
        self.ctx, self.asked = d / "ctx", d / "asked"
        self.ctx.mkdir()
        self._orig = (ccs.CTX_DIR, ccs.HOP_ASKED_DIR)
        ccs.CTX_DIR, ccs.HOP_ASKED_DIR = self.ctx, self.asked

    def tearDown(self):
        ccs.CTX_DIR, ccs.HOP_ASKED_DIR = self._orig
        _reset_config()
        self.tmp.cleanup()

    def run_hook(self, pct=None, **payload):
        import io, contextlib
        if pct is not None:
            (self.ctx / "s1").write_text(str(pct))
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            ccs._hook_stop(dict({"session_id": "s1", "hook_event_name": "Stop"}, **payload))
        return json.loads(buf.getvalue()) if buf.getvalue() else None

    def test_below_threshold_is_silent(self):
        self.assertIsNone(self.run_hook(87.9))
        self.assertFalse(self.asked.exists())

    def test_at_threshold_blocks_once(self):
        out = self.run_hook(88)
        self.assertEqual(out["decision"], "block")
        self.assertIn("Context is at 88%", out["reason"])
        self.assertIn("AskUserQuestion", out["reason"])
        self.assertIsNone(self.run_hook(95))  # already asked in this session

    def test_stop_hook_active_never_blocks(self):
        self.assertIsNone(self.run_hook(99, stop_hook_active=True))
        self.assertFalse(self.asked.exists())

    def test_disabled_and_custom_percent(self):
        self.cfg.write_text(json.dumps({"hop_prompt": {"enabled": False}}))
        self.assertIsNone(self.run_hook(99))
        _reset_config(); os.environ["CSM_CONFIG"] = str(self.cfg)
        self.cfg.write_text(json.dumps({"hop_prompt": {"enabled": True, "percent": 50}}))
        self.assertEqual(self.run_hook(51)["decision"], "block")

    def test_no_reading_means_no_guess(self):
        self.assertIsNone(self.run_hook(None, transcript_path="/nonexistent"))

    def test_transcript_estimate_only_with_configured_window(self):
        tp = pathlib.Path(self.tmp.name) / "t.jsonl"
        rows = [{"type": "assistant", "message": {"usage": {"input_tokens": 10, "cache_read_input_tokens": 100000}}},
                {"type": "assistant", "isSidechain": True, "message": {"usage": {"input_tokens": 999999}}},
                {"type": "assistant", "message": {"usage": {"input_tokens": 0, "cache_creation_input_tokens": 500,
                                                            "cache_read_input_tokens": 179500}}}]
        tp.write_text("\n".join(json.dumps(r) for r in rows))
        self.assertEqual(ccs._transcript_context_tokens(str(tp)), 180000)
        self.assertIsNone(self.run_hook(None, transcript_path=str(tp)))
        self.cfg.write_text(json.dumps({"hop_prompt": {"context_window": 200000}}))
        _reset_config(); os.environ["CSM_CONFIG"] = str(self.cfg)
        self.assertIn("Context is at 90%", self.run_hook(None, transcript_path=str(tp))["reason"])

if __name__ == "__main__":
    unittest.main(verbosity=2)
