# -*- coding: utf-8 -*-
"""JSON-RPC / LSP protocol helpers (v0.65.0 — Adoption Roadmap Goal 5).

Implements the ``Content-Length`` message framing used by the Language
Server Protocol over byte streams, plus the small set of LSP constants
the server needs.  Deliberately dependency-free so the server core can
be tested in-process without a transport.

Message framing (both sides):

    Content-Length: <bytes>\\r\\n
    [Content-Type: application/vscode-jsonrpc; charset=utf-8]\\r\\n
    \\r\\n
    <JSON payload>
"""

from __future__ import annotations

import json
from typing import BinaryIO, Dict, Any, Optional

HEADER_ENCODING = "ascii"
PAYLOAD_ENCODING = "utf-8"


class ErrorCodes:
    """JSON-RPC / LSP error codes used by the server."""

    PARSE_ERROR = -32700
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603
    SERVER_NOT_INITIALIZED = -32002


class SymbolKind:
    """LSP SymbolKind values used in documentSymbol results."""

    FILE = 1
    MODULE = 2
    NAMESPACE = 3
    PACKAGE = 4
    CLASS = 5
    METHOD = 6
    PROPERTY = 7
    FIELD = 8
    ENUM = 10
    INTERFACE = 11
    FUNCTION = 12
    VARIABLE = 13
    CONSTANT = 14
    ENUM_MEMBER = 22
    STRUCT = 23


def encode_message(payload: Dict[str, Any]) -> bytes:
    """Encode a JSON-RPC message dict with LSP ``Content-Length`` framing."""
    body = json.dumps(payload, ensure_ascii=False).encode(PAYLOAD_ENCODING)
    header = f"Content-Length: {len(body)}\r\n\r\n".encode(HEADER_ENCODING)
    return header + body


def read_message(stream: BinaryIO) -> Optional[Dict[str, Any]]:
    """Read one framed JSON-RPC message from a binary stream.

    Returns the decoded message dict, or ``None`` on clean EOF before any
    header bytes.  Raises ``ValueError`` on malformed framing.

    Tolerates ``\\n``-only header terminators in addition to the spec's
    ``\\r\\n`` (some clients get this wrong; being lenient costs nothing).
    """
    # Read header lines until the blank separator.
    content_length: Optional[int] = None
    saw_header_bytes = False
    while True:
        line = stream.readline()
        if not line:
            if not saw_header_bytes:
                return None  # clean EOF
            raise ValueError("EOF while reading message header")
        stripped = line.strip()
        if not stripped:
            if content_length is None and not saw_header_bytes:
                continue  # tolerate stray blank lines between messages
            break  # end of headers
        saw_header_bytes = True
        name, _, value = stripped.partition(b":")
        if name.strip().lower() == b"content-length":
            try:
                content_length = int(value.strip())
            except ValueError:
                raise ValueError(
                    f"Malformed Content-Length header: {value!r}"
                ) from None

    if content_length is None:
        raise ValueError("Missing Content-Length header")

    body = stream.read(content_length)
    if len(body) < content_length:
        raise ValueError(
            f"EOF while reading message body "
            f"({len(body)} of {content_length} bytes)"
        )
    return json.loads(body.decode(PAYLOAD_ENCODING))