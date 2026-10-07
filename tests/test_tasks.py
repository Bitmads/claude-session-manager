#!/usr/bin/env python3
"""
Tests for the task-source layer and the built-in adapters — stdlib only, no
network: adapters get a FakeHttp that returns canned responses shaped like
the real APIs (per their docs).

Run:  python3 -m unittest discover -s tests -v
"""

import os
import json
import pathlib
import tempfile
import unittest
from unittest import mock

from test_csm import ccs, _reset_config

LINEAR_NODE = {
    "identifier": "SET-1234", "title": "Implement multi-country settlements",
    "url": "https://linear.app/x/issue/SET-1234", "description": "Body",
    "updatedAt": "2026-10-01T10:00:00.000Z", "state": {"name": "In Progress"},
    "assignee": {"name": "Peter"}, "team": {"key": "SET"},
}
YT_ISSUE = {
    "idReadable": "VIS-12", "summary": "Fix the map tiles", "description": "Tiles 404",
    "updated": 1759312800000, "resolved": None, "project": {"shortName": "VIS"},
    "customFields": [
        {"name": "State", "value": {"name": "Open"}},
        {"name": "Assignee", "value": {"fullName": "Peter", "login": "peter"}},
        {"name": "Priority", "value": {"name": "Normal"}},
    ],
}


class FakeHttp:
    Error = ccs.HttpError

    def __init__(self, responses):
        self.responses = list(responses)  # each: a value to return, or an exception
        self.calls = []

    def _next(self, *call):
        self.calls.append(call)
        r = self.responses.pop(0)
        if isinstance(r, Exception):
            raise r
        return r

    def get_json(self, url, params=None, headers=None):
        return self._next("GET", url, params, headers)

    def post_json(self, url, body, headers=None):
        return self._next("POST", url, body, headers)


def _registry():
    ccs._REGISTRY = None
    return ccs._adapter_registry()


class TestRegistry(unittest.TestCase):
    def test_builtin_adapters_discovered(self):
        reg = _registry()
        self.assertIn("linear", reg)
        self.assertIn("youtrack", reg)

    def test_user_plugin_dir_overrides_and_bad_plugin_is_skipped(self):
        with tempfile.TemporaryDirectory() as d:
            pathlib.Path(d, "mine.py").write_text(
                "class Mine:\n    kind = 'linear'\n    def __init__(self, o, h): pass\n"
                "    def get(self, key): return {'key': key, 'title': 'from plugin'}\n"
                "ADAPTERS = [Mine]\n")
            pathlib.Path(d, "broken.py").write_text("raise RuntimeError('boom')\n")
            with mock.patch.object(ccs, "ADAPTER_DIRS", ccs.ADAPTER_DIRS[:1] + [pathlib.Path(d)]):
                reg = _registry()
        self.assertEqual(reg["linear"].__name__, "Mine")
        _registry()  # restore the real registry for other tests


class TestContract(unittest.TestCase):
    """Every built-in adapter honors the same contract."""

    def test_all_adapters_have_kind_and_get(self):
        for kind, cls in _registry().items():
            self.assertEqual(cls.kind, kind)
            self.assertTrue(callable(getattr(cls, "get", None)))
            for opt in ("search", "recent", "whoami"):
                attr = getattr(cls, opt, None)
                self.assertTrue(attr is None or callable(attr))


class TestLinear(unittest.TestCase):
    def make(self, responses):
        http = FakeHttp(responses)
        return _registry()["linear"]({"token": "lin_api_x"}, http), http

    def test_get_maps_fields_and_sends_raw_key(self):
        src, http = self.make([{"data": {"issue": LINEAR_NODE}}])
        t = src.get("SET-1234")
        self.assertEqual(t["key"], "SET-1234")
        self.assertEqual(t["title"], "Implement multi-country settlements")
        self.assertEqual(t["status"], "In Progress")
        self.assertEqual(t["project"], "SET")
        method, url, body, headers = http.calls[0]
        self.assertEqual(url, "https://api.linear.app/graphql")
        self.assertEqual(headers["Authorization"], "lin_api_x")  # no "Bearer"
        self.assertEqual(body["variables"], {"id": "SET-1234"})

    def test_get_not_found_is_none(self):
        src, _ = self.make([{"errors": [{"message": "Entity not found: Issue"}], "data": None}])
        self.assertIsNone(src.get("SET-999999"))

    def test_other_errors_raise(self):
        src, _ = self.make([{"errors": [{"message": "Authentication required"}]}])
        with self.assertRaises(Exception):
            src.get("SET-1")

    def test_search_and_recent_filter_by_team(self):
        src, http = self.make([{"data": {"searchIssues": {"nodes": [LINEAR_NODE]}}},
                               {"data": {"issues": {"nodes": [LINEAR_NODE]}}}])
        self.assertEqual(src.search("settle", 5, "SET")[0]["key"], "SET-1234")
        self.assertEqual(http.calls[0][2]["variables"]["filter"], {"team": {"key": {"eq": "SET"}}})
        src.recent(5, "SET")
        flt = http.calls[1][2]["variables"]["filter"]
        self.assertEqual(flt["state"], {"type": {"nin": ["completed", "canceled"]}})


class TestYouTrack(unittest.TestCase):
    def make(self, responses):
        http = FakeHttp(responses)
        opts = {"url": "https://x.youtrack.cloud/", "token": "perm:abc"}
        return _registry()["youtrack"](opts, http), http

    def test_get_maps_fields(self):
        src, http = self.make([YT_ISSUE])
        t = src.get("VIS-12")
        self.assertEqual((t["key"], t["title"], t["status"], t["assignee"]),
                         ("VIS-12", "Fix the map tiles", "Open", "Peter"))
        self.assertEqual(t["url"], "https://x.youtrack.cloud/issue/VIS-12")
        self.assertTrue(t["updated"].startswith("2025-10-01"))
        _, url, params, headers = http.calls[0]
        self.assertEqual(url, "https://x.youtrack.cloud/api/issues/VIS-12")
        self.assertEqual(headers["Authorization"], "Bearer perm:abc")

    def test_get_404_is_none(self):
        src, _ = self.make([ccs.HttpError(404, "not found")])
        self.assertIsNone(src.get("VIS-999"))

    def test_recent_query_scoped_to_project(self):
        src, http = self.make([[YT_ISSUE]])
        self.assertEqual(src.recent(10, "VIS")[0]["key"], "VIS-12")
        self.assertEqual(http.calls[0][2]["query"], "project: VIS #Unresolved sort by: updated desc")
        self.assertEqual(http.calls[0][2]["$top"], 10)


class _ConfigCase(unittest.TestCase):
    CONFIG = {
        "connections": {
            "lin": {"type": "linear", "token_env": "CSM_TEST_LINEAR", "prefixes": ["SET"]},
            "yt": {"type": "youtrack", "url": "https://x.youtrack.cloud", "token_env": "CSM_TEST_YT",
                   "prefixes": ["VIS", "BIT"]},
        },
        "folders": [
            {"path": "/dev/settlemate", "connection": "lin", "scope": "SET"},
            {"path": "/dev/visited", "connection": "yt", "scope": "VIS"},
            {"path": "/dev/visited/sub", "connection": "yt", "scope": "BIT"},
        ],
    }

    def setUp(self):
        _reset_config()
        self.tmp = tempfile.TemporaryDirectory()
        cfg = pathlib.Path(self.tmp.name, "csm.json")
        cfg.write_text(json.dumps(self.CONFIG))
        os.environ["CSM_CONFIG"] = str(cfg)
        os.environ["CSM_ENV_FILE"] = str(pathlib.Path(self.tmp.name, ".env"))
        ccs._SOURCES.clear()
        self.cache = mock.patch.object(ccs, "CACHE_DIR", pathlib.Path(self.tmp.name, "cache"))
        self.cache.start()

    def tearDown(self):
        self.cache.stop()
        os.environ.pop("CSM_ENV_FILE", None)
        ccs._SOURCES.clear()
        _reset_config()
        self.tmp.cleanup()


class TestRouting(_ConfigCase):
    def test_prefix_wins_from_any_folder(self):
        self.assertEqual(ccs.route("SET-12", "/tmp"), ("lin", "SET"))
        self.assertEqual(ccs.route("bit-3", "/dev/settlemate"), ("yt", "BIT"))

    def test_longest_folder_match(self):
        self.assertEqual(ccs.route(None, "/dev/visited/app"), ("yt", "VIS"))
        self.assertEqual(ccs.route(None, "/dev/visited/sub/x"), ("yt", "BIT"))

    def test_folder_prefix_is_path_aware(self):
        self.assertEqual(ccs.route(None, "/dev/visitedXYZ"), (None, None))

    def test_unknown_prefix_falls_back_to_folder(self):
        self.assertEqual(ccs.route("ZZZ-1", "/dev/settlemate/api"), ("lin", "SET"))


class TestSecretsAndFactory(_ConfigCase):
    def test_env_file_parsing(self):
        pathlib.Path(os.environ["CSM_ENV_FILE"]).write_text(
            "# comment\nexport CSM_TEST_LINEAR='lin_from_file'\nCSM_TEST_YT=\"perm:yt\"\n\nBAD LINE\n")
        self.assertEqual(ccs._secret("CSM_TEST_LINEAR"), "lin_from_file")
        self.assertEqual(ccs._secret("CSM_TEST_YT"), "perm:yt")

    def test_real_env_overrides_file(self):
        pathlib.Path(os.environ["CSM_ENV_FILE"]).write_text("CSM_TEST_LINEAR=from_file\n")
        with mock.patch.dict(os.environ, {"CSM_TEST_LINEAR": "from_env"}):
            self.assertEqual(ccs._secret("CSM_TEST_LINEAR"), "from_env")

    def test_missing_token_is_a_clear_error(self):
        with self.assertRaises(ccs.TaskSourceError) as cm:
            ccs.make_source("lin")
        self.assertIn("CSM_TEST_LINEAR is not set", str(cm.exception))

    def test_factory_injects_token(self):
        pathlib.Path(os.environ["CSM_ENV_FILE"]).write_text("CSM_TEST_YT=perm:abc\n")
        src = ccs.make_source("yt")
        self.assertEqual(src.headers["Authorization"], "Bearer perm:abc")
        self.assertIs(ccs.make_source("yt"), src)  # memoized

    def test_unknown_connection_and_type(self):
        with self.assertRaises(ccs.TaskSourceError):
            ccs.make_source("nope")


class TestNew(_ConfigCase):
    def test_parse_new_input(self):
        P = ccs._parse_new_input
        self.assertEqual(P("SET-1234"), ("SET-1234", 1, 1, None))
        self.assertEqual(P("SET-1234/2"), ("SET-1234", 2, 1, None))
        self.assertEqual(P("SET-1234/2.005"), ("SET-1234", 2, 5, None))
        self.assertEqual(P("SET-1234 Some title"), ("SET-1234", 1, 1, "Some title"))
        self.assertEqual(P("SET-123/2.005: Implement x"), ("SET-123", 2, 5, "Implement x"))
        self.assertIsNone(P("just words"))

    def test_title_uses_configured_template(self):
        self.assertEqual(ccs._new_session_title("SET-1", 2, 5, "X"), "SET-1/2.005: X")

    def test_new_fetches_full_title_never_truncated(self):
        long_title = "A very long ticket title " * 8
        node = dict(LINEAR_NODE, title=long_title)
        pathlib.Path(os.environ["CSM_ENV_FILE"]).write_text("CSM_TEST_LINEAR=lin\n")
        src = ccs.make_source("lin")
        src.http = FakeHttp([{"data": {"issue": node}}])
        with mock.patch.object(ccs.os, "execvp") as ex:
            ccs.cmd_new("SET-1234/2")
        ex.assert_called_once_with("claude", ["claude", "-n", f"SET-1234/2.001: {long_title.strip()}"])
        cached = ccs._cache_get("lin")
        self.assertEqual(cached[0]["title"], long_title)

    def test_new_with_title_makes_no_network_call(self):
        with mock.patch.object(ccs, "fetch_task") as ft, mock.patch.object(ccs.os, "execvp") as ex:
            ccs.cmd_new("SET-1 My own title")
        ft.assert_not_called()
        ex.assert_called_once_with("claude", ["claude", "-n", "SET-1/1.001: My own title"])

    def test_new_not_found_exits_without_session(self):
        pathlib.Path(os.environ["CSM_ENV_FILE"]).write_text("CSM_TEST_LINEAR=lin\n")
        ccs.make_source("lin").http = FakeHttp([{"errors": [{"message": "Entity not found"}]}])
        with mock.patch.object(ccs.os, "execvp") as ex, self.assertRaises(SystemExit):
            ccs.cmd_new("SET-999999")
        ex.assert_not_called()


class TestCompletion(_ConfigCase):
    def seed(self):
        ccs._cache_put("lin", [ccs._norm_task({"key": "SET-1", "title": "old", "project": "SET", "updated": "2026-01-01"}),
                               ccs._norm_task({"key": "SET-2", "title": "new", "project": "SET", "updated": "2026-09-01"})])
        ccs._cache_put("yt", [ccs._norm_task({"key": "SET-9", "title": "other tracker", "project": "SET", "updated": "2026-12-01"}),
                              ccs._norm_task({"key": "VIS-5", "title": "vis", "project": "VIS", "updated": "2026-10-01"})])

    def test_folder_project_first_then_newest(self):
        self.seed()
        with mock.patch.object(ccs.subprocess, "Popen"):
            keys = [t["key"] for t in ccs.complete_tasks("SET", "/dev/settlemate")]
        self.assertEqual(keys, ["SET-2", "SET-1", "SET-9"])

    def test_prefix_filter_is_case_insensitive(self):
        self.seed()
        with mock.patch.object(ccs.subprocess, "Popen"):
            self.assertEqual([t["key"] for t in ccs.complete_tasks("vis", "/tmp")], ["VIS-5"])

    def test_fresh_cache_does_not_refresh_but_stale_does(self):
        self.seed()
        with mock.patch.object(ccs.subprocess, "Popen") as po:
            ccs.complete_tasks("", "/dev/settlemate")
        po.assert_not_called()
        with mock.patch.object(ccs, "CACHE_TTL", -1), mock.patch.object(ccs.subprocess, "Popen") as po:
            ccs.complete_tasks("", "/dev/settlemate")
        po.assert_called_once()

    def test_completion_scripts_render(self):
        import io, contextlib
        for shell in ("zsh", "bash"):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                ccs.cmd_completion(shell)
            out = buf.getvalue()
            self.assertIn("_complete new", out)
            self.assertNotIn("__PY__", out)
            self.assertNotIn("__SCRIPT__", out)


class TestNextSessionNumber(unittest.TestCase):
    def setUp(self):
        _reset_config()

    def test_counts_only_same_ticket_and_phase(self):
        sessions = [{"title": "SET-1/1.001: A"}, {"title": "SET-1/1.004: A"},
                    {"title": "SET-1/2.009: A"}, {"title": "SET-10/1.007: B"}, {"title": "plain"}]
        self.assertEqual(ccs._next_session_number(sessions, "SET-1"), 5)
        self.assertEqual(ccs._next_session_number(sessions, "set-1", 2), 10)
        self.assertEqual(ccs._next_session_number(sessions, "SET-2"), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
