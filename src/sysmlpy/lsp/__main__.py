# -*- coding: utf-8 -*-
"""``python -m sysmlpy.lsp`` — run the language server over stdio."""

import sys

from sysmlpy.lsp.stdio import main

if __name__ == "__main__":
    sys.exit(main())