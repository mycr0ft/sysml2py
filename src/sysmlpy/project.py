#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Multi-file project loading for sysmlpy.

Provides functions to load multiple SysML files into a shared model context
and resolve cross-file imports.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional, Sequence

from sysmlpy.definition import Model, Package


def load_files(
    files: Sequence[str | Path],
    *,
    library: Sequence[str | Path] | str | Path | None = None,
) -> Model:
    """Load multiple SysML files into a shared model.

    All files are parsed and their contents merged into a single Model
    instance.  Packages with the same qualified name are merged so that
    definitions from different files end up in the same namespace.

    Parameters
    ----------
    files : sequence of str or Path
        Paths to the SysML (.sysml or .kerml) files to load.
    library : str, Path, sequence of str/Path, or None, optional
        Path(s) to SysML v2 library files for resolving standard library
        imports.  Multiple directories can be provided as a list or tuple.

    Returns
    -------
    Model
        A model containing all definitions from the loaded files.

    Examples
    --------
    >>> model = load_files([
    ...     'models/Shared/Types.sysml',
    ...     'models/SystemGateway/SystemGatewayMain.sysml',
    ... ])
    >>> issues = sysmlpy.analyze(model)

    >>> # Multiple library directories
    >>> model = load_files(
    ...     ['main.sysml'],
    ...     library=['/path/to/kernel', '/path/to/custom'],
    ... )
    """
    model = Model()

    for file_path in files:
        path = Path(file_path)
        if not path.is_file():
            raise FileNotFoundError(f"File not found: {path}")

        content = path.read_text(encoding="utf-8")
        _merge_into_model(model, content, library=library)

    return model


def load_project(
    root: str | Path,
    *,
    entry: str | Path | None = None,
    library: Sequence[str | Path] | str | Path | None = None,
    recursive: bool = True,
) -> Model:
    """Load a SysML project directory with automatic import resolution.

    Scans the directory for .sysml and .kerml files, parses them, and merges
    them into a single model.  If *entry* is provided, only files that are
    reachable from the entry file (via imports) are loaded.

    Parameters
    ----------
    root : str or Path
        Root directory of the project.
    entry : str or Path, optional
        Entry-point file.  If given, only files reachable from this file
        through import statements are loaded.  If None, all .sysml/.kerml
        files under *root* are loaded.
    library : str, Path, sequence of str/Path, or None, optional
        Path(s) to SysML v2 library files for resolving standard library imports.
    recursive : bool
        If True (default), search subdirectories of *root* for files.

    Returns
    -------
    Model
        A model containing all definitions from the project.

    Examples
    --------
    >>> # Load all files in the project
    >>> model = load_project('models/')

    >>> # Load starting from an entry file
    >>> model = load_project('models/', entry='models/SystemGateway/SystemGateway.sysml')

    >>> # Multiple library directories
    >>> model = load_project(
    ...     'models/',
    ...     library=['/path/to/kernel', '/path/to/custom'],
    ... )
    """
    root = Path(root)
    if not root.is_dir():
        raise NotADirectoryError(f"Not a directory: {root}")

    if entry is not None:
        return _load_from_entry(Path(entry), root, library=library)

    # Load all .sysml and .kerml files under root
    files = []
    patterns = ["**/*.sysml", "**/*.kerml"] if recursive else ["*.sysml", "*.kerml"]
    for pattern in patterns:
        files.extend(root.glob(pattern))

    # Deduplicate and sort for deterministic ordering
    files = sorted(set(files))
    return load_files(files, library=library)


def load_with_dependencies(
    entry: str | Path,
    *,
    search_paths: Sequence[str | Path] | None = None,
    library: Sequence[str | Path] | str | Path | None = None,
) -> Model:
    """Load a SysML file and all files it imports.

    Parses the entry file, extracts import statements, and recursively loads
    all imported files from the given search paths.

    Parameters
    ----------
    entry : str or Path
        Path to the entry SysML file.
    search_paths : sequence of str or Path, optional
        Directories to search for imported files.  Defaults to the directory
        containing *entry* and all its ancestor directories up to the current
        working directory.
    library : str, Path, sequence of str/Path, or None, optional
        Path(s) to SysML v2 library files for resolving standard library imports.

    Returns
    -------
    Model
        A model containing the entry file and all its dependencies.

    Examples
    --------
    >>> model = load_with_dependencies(
    ...     'models/SystemGateway/SystemGatewayMain.sysml',
    ...     search_paths=['models/SystemGateway', 'models/Shared'],
    ... )

    >>> # Multiple library directories
    >>> model = load_with_dependencies(
    ...     'main.sysml',
    ...     library=['/path/to/kernel', '/path/to/custom'],
    ... )
    """
    entry_path = Path(entry)
    if not entry_path.is_file():
        raise FileNotFoundError(f"File not found: {entry_path}")

    if search_paths is None:
        # Default: entry directory and ancestors up to cwd
        search_paths = _ancestor_dirs(entry_path.parent)

    search_paths = [Path(p) for p in search_paths]

    loaded: set[Path] = set()
    model = Model()

    _load_file_with_deps(entry_path, search_paths, library, loaded, model)

    return model


# -- Internal helpers --------------------------------------------------------

import re as _re
from sysmlpy import loads as _loads


def _merge_into_model(model: Model, content: str, library=None) -> None:
    """Parse *content* and merge its packages into *model*."""
    # Parse the content
    new_model = _loads(content, library=library)

    # Merge each top-level package from new_model into model
    for pkg in new_model.children:
        _merge_package(model, pkg)


def _merge_package(model: Model, pkg: Package) -> None:
    """Merge *pkg* into *model*, combining packages with the same name."""
    pkg_name = getattr(pkg, "name", None)
    if pkg_name is None:
        # Anonymous package – just append
        model.children.append(pkg)
        return

    # Look for existing package with same name
    existing = None
    for child in model.children:
        if getattr(child, "name", None) == pkg_name:
            existing = child
            break

    if existing is None:
        model.children.append(pkg)
    else:
        # Merge children from pkg into existing
        for child in pkg.children:
            existing.children.append(child)


def _extract_imports(content: str) -> list[str]:
    """Extract imported namespace names from SysML content.

    Returns a list of qualified names like ``['ScalarValues', 'ISQ']``.
    Handles quoted package names (e.g., ``'Some Package'``) and the
    ``all`` keyword (e.g., ``import all Types::*``).

    Since v0.76.0 this scans the SysML v2 lexer token stream instead
    of a regex over raw text (Goal 10 "regex to parser" item), which
    fixes three defects of the old regex:

    - a bare ``import X::Y;`` (no visibility keyword) was missed —
      the visibility prefix is optional per the SysML grammar and is
      now correctly treated as such
    - imports inside comments produced false positives
    - imports inside string literals (e.g. ``doc about "..."``)
      produced false positives

    Syntax-error tolerance: the lexer keeps producing tokens for
    partially broken sources (dependency scanning must not require a
    parseable file), so scanning continues past stray tokens; an
    import with a stray token in its name run is skipped.
    """
    imports: list[str] = []
    try:
        from sysmlpy.antlr_parser import _make_parser
        from sysmlpy.antlr.SysMLv2Lexer import SysMLv2Lexer
        _lexer, token_stream, _parser = _make_parser(content)
        token_stream.fill()
        tokens = token_stream.tokens
    except Exception:
        return imports

    from antlr4.Token import Token

    visible = [t for t in tokens
               if t.type != Token.EOF
               and t.channel == Token.DEFAULT_CHANNEL]

    NAME_TYPES = frozenset((SysMLv2Lexer.IDENTIFIER, SysMLv2Lexer.STRING))
    COLON_COLON = SysMLv2Lexer.COLON_COLON
    STAR = SysMLv2Lexer.STAR
    STAR_STAR = SysMLv2Lexer.STAR_STAR
    SEMI = SysMLv2Lexer.SEMI
    ALL = SysMLv2Lexer.ALL

    i = 0
    n = len(visible)
    while i < n:
        tok = visible[i]
        if tok.type != SysMLv2Lexer.IMPORT:
            i += 1
            continue
        # Collect the import run up to the terminating ';'
        j = i + 1
        parts: list[str] = []
        aborted = False
        while j < n and visible[j].type != SEMI:
            t = visible[j]
            if t.type in NAME_TYPES:
                parts.append(t.text)
            elif t.type in (ALL, COLON_COLON, STAR, STAR_STAR):
                pass  # 'all' keyword, namespace separators, wildcards
            else:
                aborted = True  # stray token — not a well-formed import
                break
            j += 1
        if parts and not aborted:
            imports.append("::".join(parts))
        # advance past the run (or the aborted token) and its ';' if present
        i = j
        if i < n and visible[i].type == SEMI:
            i += 1
    return imports


def _find_import_file(
    import_name: str,
    search_paths: Sequence[Path],
    loaded: set[Path],
) -> Path | None:
    """Find a file that defines the imported namespace.

    Searches for files whose package declaration matches the import name.
    Handles quoted package names by stripping quotes for file matching.
    """
    # Strip quotes from import name for file matching
    clean_name = import_name.replace("'", "")
    
    # Convert qualified name to potential file name patterns
    # e.g., 'SystemGateway::Types' could be in Types.sysml or SystemGatewayTypes.sysml
    parts = clean_name.split("::")
    short_name = parts[-1]

    for search_path in search_paths:
        if not search_path.is_dir():
            continue

        # Try common file naming patterns
        candidates = [
            short_name,
            "".join(parts),
            parts[0] + short_name,
        ]

        for candidate in candidates:
            for ext in (".sysml", ".kerml"):
                candidate_path = search_path / (candidate + ext)
                if candidate_path.is_file() and candidate_path not in loaded:
                    # Verify the file actually defines the package
                    content = candidate_path.read_text(encoding="utf-8")
                    if _defines_package(content, import_name):
                        return candidate_path

    return None


def _defines_package(content: str, package_name: str) -> bool:
    """Check if *content* defines a package with the given name.

    Handles both quoted (``'Some Package'``) and unquoted names.
    """
    # Match: package <name> {  (name can be identifier or quoted string)
    if package_name.startswith("'"):
        # Quoted name – match exactly including quotes
        pattern = _re.compile(
            r'\bpackage\s+' + _re.escape(package_name) + r'\s*\{'
        )
    else:
        # Unquoted name – use word boundary
        pattern = _re.compile(
            r'\bpackage\s+' + _re.escape(package_name) + r'\s*\{'
        )
    return bool(pattern.search(content))


def _ancestor_dirs(path: Path) -> list[Path]:
    """Return *path* and all its ancestors up to cwd."""
    dirs = [path]
    cwd = Path.cwd()
    current = path
    while current != current.parent and current != cwd:
        current = current.parent
        dirs.append(current)
    return dirs


def _load_file_with_deps(
    file_path: Path,
    search_paths: Sequence[Path],
    library,
    loaded: set[Path],
    model: Model,
) -> None:
    """Recursively load *file_path* and its dependencies."""
    resolved = file_path.resolve()
    if resolved in loaded:
        return
    loaded.add(resolved)

    content = resolved.read_text(encoding="utf-8")
    _merge_into_model(model, content, library=library)

    # Extract imports and load dependencies
    imports = _extract_imports(content)
    for imp in imports:
        dep_file = _find_import_file(imp, search_paths, loaded)
        if dep_file is not None:
            _load_file_with_deps(dep_file, search_paths, library, loaded, model)


def _load_from_entry(
    entry: Path,
    root: Path,
    library,
) -> Model:
    """Load project starting from an entry file."""
    return load_with_dependencies(entry, search_paths=[root], library=library)
