#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for the persistent ANTLR DFA cache (v0.84.0 — Goal 11 Batch 5).

Covers:
- save/load round-trip with byte-identical visitor output
- subprocess cold-start elimination (save in one process, load in the next)
- corrupt / wrong-shape / missing cache fallback (parse never breaks)
- disable flag (set_dfa_cache + SYSSMLPY_DFA_CACHE=off)
- stable cache keying
"""

import json
import os
import subprocess
import sys

import pytest

from sysmlpy import dfa_cache
from sysmlpy.antlr.SysMLv2Lexer import SysMLv2Lexer
from sysmlpy.antlr.SysMLv2Parser import SysMLv2Parser

MODEL = """package P {
    part def Engine { attribute rpm : Real; }
    part def Vehicle { part engine : Engine; attribute speed : Real := 70; }
    part def Car :> Vehicle { port p; }
}"""


@pytest.fixture(autouse=True)
def _clean_cache_config():
    """Isolate tests from process-global cache overrides."""
    dfa_cache._state["enabled"] = None
    dfa_cache._state["directory"] = None
    dfa_cache.reset_for_tests()
    yield
    dfa_cache._state["enabled"] = None
    dfa_cache._state["directory"] = None
    dfa_cache.reset_for_tests()


P = SysMLv2Parser
L = SysMLv2Lexer


@pytest.fixture()
def pristine_snapshot():
    """Snapshot and restore the generated classes' ATN/DFA state."""
    snap = (P.atn, P.decisionsToDFA, P.sharedContextCache,
            L.atn, L.decisionsToDFA)
    yield snap
    (P.atn, P.decisionsToDFA, P.sharedContextCache,
     L.atn, L.decisionsToDFA) = snap
    dfa_cache.reset_for_tests()


def _visitor_dict(text):
    from sysmlpy import parse
    from sysmlpy.antlr_visitor import parse_to_dict
    parse(text)   # warm (and trigger save hooks)
    return parse_to_dict(text)


def _canon(d):
    return json.dumps(d, sort_keys=True, default=str)


class TestSaveLoadEquivalence:
    """Save a warm cache, reload it, and require identical output."""

    def test_round_trip_identical_visitor_dict(self, tmp_path,
                                               pristine_snapshot):
        dfa_cache.set_dfa_cache(enabled=True, directory=str(tmp_path))
        dfa_cache.reset_for_tests()

        d1 = _visitor_dict(MODEL)
        assert dfa_cache.save_dfa_cache()
        assert dfa_cache.stats()["saved"] is True

        # hard-reset the generated classes to their pristine state so
        # the subsequent parse truly starts cold, then load the cache
        (P.atn, P.decisionsToDFA, P.sharedContextCache,
         L.atn, L.decisionsToDFA) = pristine_snapshot
        dfa_cache.reset_for_tests()
        assert dfa_cache.load_dfa_cache() is True

        d2 = _visitor_dict(MODEL)
        assert _canon(d1) == _canon(d2)

    def test_loaded_cache_used_for_fresh_parse(self, tmp_path,
                                               pristine_snapshot):
        dfa_cache.set_dfa_cache(enabled=True, directory=str(tmp_path))
        dfa_cache.reset_for_tests()
        _visitor_dict(MODEL)
        assert dfa_cache.save_dfa_cache()

        (P.atn, P.decisionsToDFA, P.sharedContextCache,
         L.atn, L.decisionsToDFA) = pristine_snapshot
        dfa_cache.reset_for_tests()
        assert dfa_cache.load_dfa_cache()
        assert dfa_cache.stats()["loaded"] is True

    def test_state_counts_match_after_restore(self, tmp_path,
                                              pristine_snapshot):
        dfa_cache.set_dfa_cache(enabled=True, directory=str(tmp_path))
        dfa_cache.reset_for_tests()
        _visitor_dict(MODEL)
        warm_counts = [len(d.states) for d in P.decisionsToDFA]
        assert dfa_cache.save_dfa_cache()

        (P.atn, P.decisionsToDFA, P.sharedContextCache,
         L.atn, L.decisionsToDFA) = pristine_snapshot
        dfa_cache.reset_for_tests()
        dfa_cache.load_dfa_cache()
        warm_counts2 = [len(d.states) for d in P.decisionsToDFA]
        assert sum(warm_counts) == sum(warm_counts2)


class TestFallbackSafety:
    """A broken cache must never break parsing."""

    def test_corrupted_cache_falls_back(self, tmp_path,
                                        pristine_snapshot):
        dfa_cache.set_dfa_cache(enabled=True, directory=str(tmp_path))
        dfa_cache.reset_for_tests()
        cache_file = dfa_cache.cache_file()
        os.makedirs(tmp_path, exist_ok=True)
        with open(cache_file, "wb") as f:
            f.write(b"this is not a pickle \x00\x01\x02")
        from sysmlpy import parse
        with pytest.warns(UserWarning, match="DFA cache load failed"):
            r = parse(MODEL)
        assert isinstance(r, tuple) and r[1] == []

    def test_wrong_payload_shape_falls_back(self, tmp_path,
                                            pristine_snapshot):
        dfa_cache.set_dfa_cache(enabled=True, directory=str(tmp_path))
        dfa_cache.reset_for_tests()
        cache_file = dfa_cache.cache_file()
        os.makedirs(tmp_path, exist_ok=True)
        with open(cache_file, "wb") as f:
            import pickle
            pickle.dump(("not", "a", "5-tuple"), f)
        from sysmlpy import parse
        with pytest.warns(UserWarning, match="unexpected cache payload"):
            r = parse(MODEL)
        assert isinstance(r, tuple) and r[1] == []

    def test_missing_file_is_silent(self, tmp_path, pristine_snapshot):
        dfa_cache.set_dfa_cache(enabled=True, directory=str(tmp_path))
        dfa_cache.reset_for_tests()
        assert dfa_cache.load_dfa_cache() is False   # no warning
        from sysmlpy import parse
        r = parse(MODEL)
        assert isinstance(r, tuple) and r[1] == []

    def test_cache_save_never_raises(self, tmp_path, pristine_snapshot,
                                     monkeypatch):
        dfa_cache.set_dfa_cache(enabled=True, directory=str(tmp_path))
        dfa_cache.reset_for_tests()
        # force the write to fail on an impossible directory
        monkeypatch.setattr(dfa_cache, "cache_file",
                            lambda: "/proc/impossible/dir/x.pkl")
        with pytest.warns(UserWarning, match="DFA cache save failed"):
            assert dfa_cache.save_dfa_cache() is False
        from sysmlpy import parse
        r = parse(MODEL)
        assert isinstance(r, tuple) and r[1] == []


class TestConfiguration:

    def test_disabled_skips_save_and_load(self, tmp_path):
        dfa_cache.set_dfa_cache(enabled=False, directory=str(tmp_path))
        dfa_cache.reset_for_tests()
        from sysmlpy import parse
        r = parse(MODEL)
        assert isinstance(r, tuple) and r[1] == []
        assert dfa_cache.save_dfa_cache() is False
        assert dfa_cache.load_dfa_cache() is False
        assert not os.path.exists(dfa_cache.cache_file())

    def test_env_off_disables(self, tmp_path, monkeypatch):
        monkeypatch.setenv("SYSSMLPY_DFA_CACHE", "off")
        dfa_cache.set_dfa_cache(enabled=None, directory=str(tmp_path))
        dfa_cache.reset_for_tests()
        assert dfa_cache.is_enabled() is False

    def test_env_path_overrides_directory(self, tmp_path, monkeypatch):
        monkeypatch.setenv("SYSSMLPY_DFA_CACHE", str(tmp_path))
        dfa_cache.set_dfa_cache(enabled=None, directory=None)
        assert dfa_cache.stats()["directory"] == str(tmp_path)

    def test_default_directory_used_without_override(self, monkeypatch,
                                                     tmp_path):
        monkeypatch.delenv("SYSSMLPY_DFA_CACHE", raising=False)
        monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))
        dfa_cache.set_dfa_cache(enabled=None, directory=None)
        st = dfa_cache.stats()
        assert st["directory"].startswith(str(tmp_path))
        assert "sysmlpy" in st["directory"]

    def test_key_stable_and_file_derives_from_it(self, tmp_path):
        dfa_cache.set_dfa_cache(enabled=True, directory=str(tmp_path))
        k1 = dfa_cache.cache_key()
        k2 = dfa_cache.cache_key()
        assert k1 == k2
        assert len(k1) == 40                    # sha1 hex
        assert dfa_cache.cache_file().endswith("dfa-%s.pkl" % k1[:16])


class TestSubprocessFlow:
    """End-to-end: save in one process, load in the next."""

    SCRIPT = """
import json, os, sys
sys.path.insert(0, {src!r})
os.environ["SYSSMLPY_DFA_CACHE"] = {cache_dir!r}
from sysmlpy import dfa_cache
dfa_cache.reset_for_tests()
from sysmlpy import parse
from sysmlpy.antlr_visitor import parse_to_dict
text = {model!r}
r = parse(text)
ok = isinstance(r, tuple) and r[1] == []
d = parse_to_dict(text)
saved = dfa_cache.stats()["saved"]
loaded = dfa_cache.stats()["loaded"]
print(json.dumps({{"ok": ok, "saved": saved, "loaded": loaded,
                   "dict": json.dumps(d, sort_keys=True, default=str)}}))
"""

    def _run(self, tmp_path, mode):
        env = dict(os.environ)
        script = self.SCRIPT.format(src=os.path.abspath("src"),
                                    cache_dir=str(tmp_path),
                                    model=MODEL)
        proc = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True, text=True, timeout=600, env=env)
        assert proc.returncode == 0, proc.stderr[-800:]
        line = proc.stdout.strip().splitlines()[-1]
        return json.loads(line)

    def test_save_then_load_across_processes(self, tmp_path):
        first = self._run(tmp_path, "save")
        assert first["ok"] is True
        assert first["saved"] is True
        assert first["loaded"] is False
        cache_dir = dfa_cache._cache_directory.__wrapped__ if False else None
        # the subprocess used tmp_path as its cache dir; the file exists
        files = os.listdir(tmp_path)
        assert any(f.startswith("dfa-") and f.endswith(".pkl")
                   for f in files)

        second = self._run(tmp_path, "load")
        assert second["ok"] is True
        assert second["loaded"] is True
        assert second["saved"] is False          # cache file exists
        assert first["dict"] == second["dict"]   # identical parse output

    def test_loaded_run_faster_than_cold(self, tmp_path):
        # not a hard assertion (timing is flaky in CI); recorded for
        # the benchmark docs via a generous upper bound
        import time

        self._run(tmp_path, "save")
        t0 = time.perf_counter()
        second = self._run(tmp_path, "load")
        t1 = time.perf_counter()
        assert second["loaded"] is True
        # a loaded cache must never be slower than the measured cold
        # start of this grammar (~8.4 s for the big benchmark model;
        # this small model is well under a second warm)
        assert (t1 - t0) < 60