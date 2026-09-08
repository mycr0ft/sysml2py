# -*- coding: utf-8 -*-
"""Persistent ANTLR DFA cache (v0.84.0 — Adoption Roadmap Goal 11 Batch 5).

The generated SysML v2 parser/lexer share class-level ATN + DFA caches,
so prediction structures are built once per *process* — but every fresh
process (CLI invocation, LSP session start, first test run) pays that
cold-start cost again.  On a 27 KB model the first parse measured
**8.4 s** versus **1.2 s** for an in-process warm parse: ~85 % of the
first parse is adaptive-prediction DFA construction.

This module serializes the warmed parser + lexer ATN/DFA graphs with
``pickle`` after a successful parse and reinstalls them at the start of
subsequent processes, eliminating the cold start.

Design notes
------------
* The *whole* reachable graph is pickled (ATN objects, DFA states, the
  prediction-context cache) and assigned back to the generated classes'
  class attributes on load.  Pickle preserves shared substructures, so
  the restored graph is self-consistent — no state re-wiring needed.
* The cache file is keyed by SHA-1 of both serialized ATNs + the
  antlr4 runtime version + the sysmlpy version + pickle protocol, so a
  stale or regenerated grammar can never load a mismatched cache.
* Cache failures must never break parsing: every load/save is wrapped
  and degrades to the normal (uncached) behavior with a one-time
  warning.
* Trust: the cache is read from the user's own cache directory
  (``XDG_CACHE_HOME``/``~/.cache/sysmlpy`` or an explicit override) —
  like any Python pickle it must only contain locally generated data;
  point the directory at a trusted location or disable with
  ``SYSSMLPY_DFA_CACHE=off``.
"""

from __future__ import annotations

import hashlib
import os
import pickle
import threading
import warnings
from typing import Any, Dict, Optional, Tuple

_CACHE_PROTOCOL = 4          # stable across Python 3.8+; avoids protocol drift
_MAX_CACHE_BYTES = 256 * 1024 * 1024   # refuse absurd cache files on load

# RLock: stats()/set_dfa_cache() re-enter while held
_lock = threading.RLock()
_state: Dict[str, Any] = {
    "enabled": None,        # None = not overridden by set_dfa_cache()
    "directory": None,      # None = default (env/XDG/~/.cache/sysmlpy)
    "load_attempted": False,
    "loaded": False,
    "save_attempted": False,
    "saved": False,
    "saved_states": 0,
}


# ---------------------------------------------------------------------------
# configuration
# ---------------------------------------------------------------------------


def _env_disabled() -> bool:
    return os.environ.get("SYSSMLPY_DFA_CACHE", "").strip().lower() in (
        "0", "off", "false", "no", "disable", "disabled")


def _env_directory() -> Optional[str]:
    val = os.environ.get("SYSSMLPY_DFA_CACHE", "").strip()
    if val and val.lower() not in (
            "0", "off", "false", "no", "disable", "disabled", "on", "1",
            "true", "yes", "enable", "enabled"):
        return val
    return None


def is_enabled() -> bool:
    """Whether the DFA cache should participate in parsing."""
    with _lock:
        if _state["enabled"] is not None:
            return _state["enabled"]
    return not _env_disabled()


def set_dfa_cache(enabled: Optional[bool] = None,
                  directory: Optional[str] = None) -> Dict[str, Any]:
    """Configure the persistent DFA cache.

    Parameters
    ----------
    enabled : bool, optional
        ``True``/``False`` force the cache on/off for this process;
        ``None`` (default) keeps the ``SYSSMLPY_DFA_CACHE`` env default.
    directory : str, optional
        Override the cache directory for this process; ``None`` keeps
        the env/default location.

    Returns
    -------
    dict
        ``{"enabled": bool, "directory": str}`` — the effective settings.
    """
    with _lock:
        if enabled is not None:
            _state["enabled"] = bool(enabled)
        if directory is not None:
            _state["directory"] = directory
        return {"enabled": is_enabled(),
                "directory": _cache_directory()}


def _cache_directory() -> str:
    with _lock:
        override = _state["directory"]
    if override:
        return override
    env_dir = _env_directory()
    if env_dir:
        return env_dir
    root = os.environ.get("XDG_CACHE_HOME") or os.path.expanduser(
        os.path.join("~", ".cache"))
    return os.path.join(root, "sysmlpy")


def cache_key() -> str:
    """Stable key binding the cache file to the grammar + runtime."""
    import antlr4 as _antlr4
    from sysmlpy.antlr import SysMLv2Lexer, SysMLv2Parser

    parts = [
        SysMLv2Parser.serializedATN(),
        SysMLv2Lexer.serializedATN(),
        getattr(SysMLv2Parser, "grammarFileName", "SysMLv2Parser.g4"),
        getattr(SysMLv2Lexer, "grammarFileName", "SysMLv2Lexer.g4"),
        "antlr4=" + getattr(_antlr4, "__version__", "unknown"),
        "sysmlpy=" + _sysmlpy_version(),
        f"pickle={_CACHE_PROTOCOL}",
    ]
    h = hashlib.sha1()
    for part in parts:
        # serializedATN() is a list of ints — pickle gives a stable
        # byte form for both lists and strings
        h.update(hashlib.sha1(
            pickle.dumps(part, protocol=_CACHE_PROTOCOL)).digest())
        h.update(b"\x00")
    return h.hexdigest()


def _sysmlpy_version() -> str:
    try:
        import sysmlpy
        return getattr(sysmlpy, "__version__", "unknown")
    except Exception:
        return "unknown"


def cache_file() -> str:
    """Full path of the DFA cache file for this grammar version."""
    return os.path.join(_cache_directory(),
                        "dfa-%s.pkl" % cache_key()[:16])


# ---------------------------------------------------------------------------
# load / save
# ---------------------------------------------------------------------------


def _classes() -> Tuple[type, type]:
    # NB: ``sysmlpy.antlr`` is a namespace package whose submodule names
    # shadow the class names — import the classes from their modules
    from sysmlpy.antlr.SysMLv2Lexer import SysMLv2Lexer as _Lexer
    from sysmlpy.antlr.SysMLv2Parser import SysMLv2Parser as _Parser
    return _Parser, _Lexer


def _payload() -> Tuple[Any, ...]:
    """The pickled state: parser + lexer ATN/DFA/context-cache attrs."""
    P, L = _classes()
    return (P.atn, P.decisionsToDFA, P.sharedContextCache,
            L.atn, L.decisionsToDFA)


def _rebind_empty_contexts(payload: Tuple[Any, ...]) -> Tuple[Any, ...]:
    """Re-point pickled empty prediction contexts at the live singleton.

    ``EmptyPredictionContext`` is identity-comparable in the runtime
    (``__eq__`` is ``self is other`` and ``isEmpty()`` is
    ``self is self.EMPTY``), so unpickled copies must be replaced by the
    live ``PredictionContext.EMPTY`` singleton, and the shared cache
    rebuilt, or prediction diverges from the pristine parser.
    """
    from antlr4.PredictionContext import (
        PredictionContext as _PC,
        PredictionContextCache,
        EmptyPredictionContext,
    )
    from antlr4.atn.SemanticContext import SemanticContext

    live_empty = _PC.EMPTY
    live_none = SemanticContext.NONE
    seen: set = set()

    def fix(ctx):
        if ctx is None:
            return None
        if isinstance(ctx, EmptyPredictionContext):
            return live_empty
        cid = id(ctx)
        if cid in seen:
            return ctx
        seen.add(cid)
        # NB: SingletonPredictionContext stores its parent as
        # ``parentCtx``; ArrayPredictionContext as ``parents``
        parent = getattr(ctx, "parentCtx", None)
        if parent is not None:
            ctx.parentCtx = fix(parent)
        parents = getattr(ctx, "parents", None)
        if parents is not None:
            ctx.parents = [fix(p) for p in parents]
        return ctx

    def fix_sem(sc):
        if sc is None:
            return None
        if isinstance(sc, type(live_none)):
            return live_none
        return sc

    P_ctx = payload[2]
    rebuilt = PredictionContextCache()
    for ctx in P_ctx.cache.values():
        rebuilt.add(fix(ctx))

    # DFA config sets also hold prediction contexts that never made it
    # into the shared cache — rebind those graphs as well
    for dfa_list in (payload[1], payload[4]):
        for dfa in dfa_list:
            for state in dfa.states.values():
                configs = getattr(state, "configs", None)
                if configs is None:
                    continue
                for cfg in getattr(configs, "configs", []) or []:
                    context = getattr(cfg, "context", None)
                    if context is not None:
                        cfg.context = fix(context)
                    cfg.semanticContext = fix_sem(
                        getattr(cfg, "semanticContext", None))
                predicates = getattr(state, "predicates", None)
                if predicates:
                    state.predicates = [
                        (alt, live_none if isinstance(pred, type(live_none))
                         else pred)
                        for alt, pred in predicates
                    ]
    return (payload[0], payload[1], rebuilt, payload[3], payload[4])


def _install(payload: Tuple[Any, ...]) -> None:
    payload = _rebind_empty_contexts(payload)
    P_atn, P_dfa, P_ctx, L_atn, L_dfa = payload
    P, L = _classes()
    P.atn = P_atn
    P.decisionsToDFA = P_dfa
    P.sharedContextCache = P_ctx
    L.atn = L_atn
    L.decisionsToDFA = L_dfa


def load_dfa_cache(path: Optional[str] = None) -> bool:
    """Try to install a persisted DFA cache.  Returns True on success.

    Safe to call repeatedly (loads at most once per process) and never
    raises: any problem falls back to the normal uncached path with a
    one-time warning.
    """
    with _lock:
        if _state["load_attempted"]:
            return _state["loaded"]
        _state["load_attempted"] = True
    if not is_enabled():
        return False
    path = path or cache_file()
    try:
        if not os.path.isfile(path):
            return False
        if os.path.getsize(path) > _MAX_CACHE_BYTES:
            raise ValueError("cache file exceeds size guard")
        with open(path, "rb") as f:
            payload = pickle.load(f)
        if not isinstance(payload, tuple) or len(payload) != 5:
            raise ValueError("unexpected cache payload shape")
        with _lock:
            _install(payload)
            _state["loaded"] = True
        return True
    except Exception as exc:
        warnings.warn(
            f"DFA cache load failed ({type(exc).__name__}: {exc}); "
            f"parsing continues without it", stacklevel=3)
        return False


def save_dfa_cache(path: Optional[str] = None) -> bool:
    """Persist the (warm) DFA cache.  Returns True when written.

    Never raises; failures degrade to a one-time warning.  Skipped when
    the cache is disabled or nothing new to save.
    """
    with _lock:
        if _state["save_attempted"]:
            return _state["saved"]
        _state["save_attempted"] = True
    if not is_enabled():
        return False
    path = path or cache_file()
    try:
        if os.path.isfile(path):
            with _lock:
                _state["saved"] = False
            return False
        P, L = _classes()
        payload = _payload()
        blob = pickle.dumps(payload, protocol=_CACHE_PROTOCOL)
        states = sum(len(dfa.states) for dfa in payload[1])
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp = path + ".tmp-%d" % os.getpid()
        with open(tmp, "wb") as f:
            f.write(blob)
        os.replace(tmp, path)
        with _lock:
            _state["saved"] = True
            _state["saved_states"] = states
        return True
    except Exception as exc:
        warnings.warn(
            f"DFA cache save failed ({type(exc).__name__}: {exc}); "
            f"parsing continues without it", stacklevel=3)
        return False


def maybe_load() -> None:
    """Lazy hook: attempt the cache load once per process."""
    load_dfa_cache()


def maybe_save() -> None:
    """Lazy hook: persist the warm cache once per process, if missing."""
    save_dfa_cache()


def reset_for_tests() -> None:
    """Reset process state (load/save flags); used by the test suite."""
    with _lock:
        for key in ("load_attempted", "loaded", "save_attempted",
                    "saved", "saved_states"):
            _state[key] = False if key != "saved_states" else 0


def stats() -> Dict[str, Any]:
    """Current cache state (for tests and diagnostics)."""
    with _lock:
        return {
            "enabled": is_enabled(),
            "directory": _cache_directory(),
            "file": cache_file(),
            "key": cache_key(),
            "load_attempted": _state["load_attempted"],
            "loaded": _state["loaded"],
            "save_attempted": _state["save_attempted"],
            "saved": _state["saved"],
            "saved_states": _state["saved_states"],
        }