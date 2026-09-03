# -*- coding: utf-8 -*-
"""stdio transport for the sysmlpy language server (v0.65.0, Goal 5).

Reads LSP-framed JSON-RPC messages from ``sys.stdin.buffer`` and writes
responses to ``sys.stdout.buffer``; human-readable logs go to stderr.

Entry points:

    python -m sysmlpy.lsp          # this package's __main__
    sysmlpy-lsp                    # console script (pyproject [project.scripts])

Options:

    --log FILE   also mirror protocol traffic to a file (debugging)
    --version    print the sysmlpy version and exit
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import BinaryIO, List, Optional

from sysmlpy.lsp.protocol import encode_message, read_message
from sysmlpy.lsp.server import SysmlLanguageServer


def serve(input_stream: BinaryIO, output_stream: BinaryIO,
          log=None) -> None:
    """Run the request loop until the client sends ``exit`` or EOF.

    *log* may be a writable text stream receiving one line per message.
    """
    server = SysmlLanguageServer()

    def send(payload) -> None:
        data = encode_message(payload)
        output_stream.write(data)
        output_stream.flush()
        if log is not None:
            log.write(f"--> {data.decode('utf-8', 'replace')}\n")

    while True:
        try:
            msg = read_message(input_stream)
        except (ValueError, OSError) as exc:
            if log is not None:
                log.write(f"!! framing error: {exc}\n")
            break  # unrecoverable framing — drop the connection
        if msg is None:  # clean EOF
            break

        if log is not None:
            method = msg.get("method", "<response>")
            log.write(f"<-- {method}\n")

        for payload in server.handle_message(msg):
            send(payload)

        if server.exited:
            break


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="sysmlpy-lsp",
        description="sysmlpy Language Server (SysML v2) — stdio transport",
    )
    parser.add_argument("--version", action="store_true",
                        help="print the sysmlpy version and exit")
    parser.add_argument(
        "--log", metavar="FILE",
        help="append protocol traffic to FILE for debugging",
    )
    args = parser.parse_args(argv)

    if args.version:
        import sysmlpy
        print(sysmlpy.__version__)
        return 0

    # The VS Code client on some platforms requires the CWD to be sane;
    # editors generally spawn us with a workspace root anyway.
    log = None
    if args.log:
        try:
            log = open(args.log, "a", encoding="utf-8", buffering=1)
            log.write(f"=== sysmlpy-lsp started (pid={os.getpid()}) ===\n")
        except OSError:
            log = None

    try:
        serve(sys.stdin.buffer, sys.stdout.buffer, log=log)
    except BrokenPipeError:
        pass  # client closed the window — normal exit
    finally:
        if log is not None:
            log.close()
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())