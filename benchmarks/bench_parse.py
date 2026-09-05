#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Parse-pipeline benchmarks (v0.84.0 — Adoption Roadmap Goal 11 Batch 5).

Measures the three parse scenarios for the same model:

1. **cold**   — fresh process, persistent DFA cache disabled.  This is
   the cost every CLI invocation / LSP session start / first test run
   paid before the cache existed.
2. **cached** — fresh process, persistent DFA cache loaded.  The DFA
   states warmed by a previous run are reinstated before the first
   parse, eliminating adaptive-prediction construction.
3. **warm**   — second parse inside the same process (the runtime
   shares its ATN/DFA caches per process).

Usage::

    python benchmarks/bench_parse.py [parts]

``parts`` is the model size knob (default 300 part definitions ≈ 27 KB
of SysML).  The cache directory defaults to a temporary location; set
``BENCH_CACHE_DIR`` to keep it.

Measured on the reference machine (2026-09): cold ≈ 8.4 s,
cached ≈ 1.2 s, warm ≈ 1.2 s for the default model — the persistent
cache removes ~85 % of the cold-start cost.
"""
import os
import subprocess
import sys
import tempfile
import time

MODEL_TEMPLATE = ("package Big {{ " + chr(10).join(
    f"part def Comp{{i}} {{ attribute a{{i}} : Real := {{i}}; "
    f"part def Sub{{i}} {{ attribute b : Boolean; }} }}"
    for _ in range(1)) + " }}")

SCRIPT = """
import sys, time
sys.path.insert(0, {src!r})
model = {model!r}
from sysmlpy import parse
t0 = time.perf_counter()
r = parse(model)
t1 = time.perf_counter()
ok = isinstance(r, tuple) and r[1] == []
print(f"{{t1 - t0:.3f}} {{ok}}")
"""


def model_text(parts: int) -> str:
    body = chr(10).join(
        f"part def Comp{i} {{ attribute a{i} : Real := {i}; "
        f"part def Sub{i} {{ attribute b : Boolean; }} }}"
        for i in range(parts))
    return "package Big { " + body + " }"


def run_subprocess(model: str, cache_env: str) -> float:
    script = SCRIPT.format(src=os.path.join(os.path.dirname(__file__),
                                            "..", "src"),
                           model=model)
    env = dict(os.environ)
    env["SYSSMLPY_DFA_CACHE"] = cache_env
    t0 = time.perf_counter()
    proc = subprocess.run([sys.executable, "-c", script],
                          capture_output=True, text=True,
                          timeout=600, env=env)
    elapsed = time.perf_counter() - t0
    assert proc.returncode == 0, proc.stderr[-500:]
    assert "True" in proc.stdout, proc.stdout
    return elapsed


def run_warm(model: str) -> float:
    sys.path.insert(0, os.path.join(os.path.dirname(__file__),
                                    "..", "src"))
    env_backup = os.environ.get("SYSSMLPY_DFA_CACHE")
    os.environ["SYSSMLPY_DFA_CACHE"] = "off"
    try:
        from sysmlpy import parse
        parse(model)                       # warm this process
        t0 = time.perf_counter()
        r = parse(model)
        t1 = time.perf_counter()
        assert isinstance(r, tuple) and r[1] == []
        return t1 - t0
    finally:
        if env_backup is None:
            os.environ.pop("SYSSMLPY_DFA_CACHE", None)
        else:
            os.environ["SYSSMLPY_DFA_CACHE"] = env_backup


def main() -> None:
    parts = int(sys.argv[1]) if len(sys.argv) > 1 else 300
    model = model_text(parts)
    print(f"model: {parts} part definitions, {len(model)} chars")
    with tempfile.TemporaryDirectory() as cache_dir:
        # pass 1 populates the cache (cold + save)
        t_cold = run_subprocess(model, cache_dir)
        # pass 2 loads the cache
        t_cached = run_subprocess(model, cache_dir)
    t_warm = run_warm(model)
    speedup = (t_cold / t_cached) if t_cached else float("inf")
    print(f"cold   (fresh process, no cache):   {t_cold:7.3f}s")
    print(f"cached (fresh process, DFA cache): {t_cached:7.3f}s")
    print(f"warm   (second parse, same proc):  {t_warm:7.3f}s")
    print(f"cold-start eliminated: "
          f"{100 * (1 - t_cached / t_cold):.0f}% ({speedup:.1f}x faster)")


if __name__ == "__main__":
    main()