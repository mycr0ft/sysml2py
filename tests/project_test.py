#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for multi-file project loading.
"""

import pytest
import tempfile
import os
from pathlib import Path

import sysmlpy
from sysmlpy import load_files, load_project, load_with_dependencies
from sysmlpy import analyze


class TestLoadFiles:
    """Tests for load_files() function."""

    def test_load_single_file(self):
        """Loading a single file should work."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "test.sysml"
            file_path.write_text("""
package Test {
    part def Engine;
}
""")
            model = load_files([file_path])
            assert model is not None
            assert len(model.children) == 1
            assert model.children[0].name == "Test"

    def test_load_multiple_files(self):
        """Loading multiple files should merge their contents."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file1 = Path(tmpdir) / "types.sysml"
            file1.write_text("""
package Types {
    part def Engine;
    part def Wheel;
}
""")
            file2 = Path(tmpdir) / "vehicle.sysml"
            file2.write_text("""
package Vehicle {
    part myCar;
}
""")
            model = load_files([file1, file2])
            assert model is not None
            assert len(model.children) == 2
            names = {pkg.name for pkg in model.children}
            assert "Types" in names
            assert "Vehicle" in names

    def test_load_files_merge_same_package(self):
        """Files defining the same package should be merged."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file1 = Path(tmpdir) / "types1.sysml"
            file1.write_text("""
package Types {
    part def Engine;
}
""")
            file2 = Path(tmpdir) / "types2.sysml"
            file2.write_text("""
package Types {
    part def Wheel;
}
""")
            model = load_files([file1, file2])
            assert model is not None
            # Should have one package with merged contents
            assert len(model.children) == 1
            pkg = model.children[0]
            assert pkg.name == "Types"
            # Both definitions should be present
            child_names = {c.name for c in pkg.children if hasattr(c, 'name')}
            assert "Engine" in child_names
            assert "Wheel" in child_names

    def test_load_file_not_found(self):
        """Loading a non-existent file should raise FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            load_files(["/nonexistent/file.sysml"])


class TestLoadProject:
    """Tests for load_project() function."""

    def test_load_project_directory(self):
        """Loading a project directory should find all .sysml files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "types.sysml").write_text("""
package Types {
    part def Engine;
}
""")
            (root / "vehicle.sysml").write_text("""
package Vehicle {
    part myCar;
}
""")
            model = load_project(root)
            assert model is not None
            assert len(model.children) == 2

    def test_load_project_not_a_directory(self):
        """Loading a non-directory should raise NotADirectoryError."""
        with pytest.raises(NotADirectoryError):
            load_project("/nonexistent/directory")

    def test_load_project_recursive(self):
        """Loading a project should search subdirectories by default."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            subdir = root / "sub"
            subdir.mkdir()
            (root / "top.sysml").write_text("""
package Top {
    part def TopPart;
}
""")
            (subdir / "nested.sysml").write_text("""
package Nested {
    part def NestedPart;
}
""")
            model = load_project(root)
            assert model is not None
            assert len(model.children) == 2


class TestLoadWithDependencies:
    """Tests for load_with_dependencies() function."""

    def test_load_entry_file(self):
        """Loading an entry file should work."""
        with tempfile.TemporaryDirectory() as tmpdir:
            entry = Path(tmpdir) / "main.sysml"
            entry.write_text("""
package Main {
    part def MainPart;
}
""")
            model = load_with_dependencies(entry)
            assert model is not None
            assert len(model.children) == 1

    def test_load_with_dependencies_finds_imported_file(self):
        """Imported files should be loaded from search paths."""
        with tempfile.TemporaryDirectory() as tmpdir:
            shared = Path(tmpdir) / "Shared"
            shared.mkdir()
            (shared / "Types.sysml").write_text("""
package Types {
    part def Engine;
}
""")
            entry = Path(tmpdir) / "main.sysml"
            entry.write_text("""
package Main {
    private import Types::*;
    part myEngine : Engine;
}
""")
            model = load_with_dependencies(
                entry,
                search_paths=[shared],
            )
            assert model is not None
            # Should have loaded both Main and Types packages
            names = {pkg.name for pkg in model.children}
            assert "Main" in names
            assert "Types" in names

    def test_load_entry_not_found(self):
        """Loading a non-existent entry file should raise FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            load_with_dependencies("/nonexistent/file.sysml")


class TestCrossFileResolution:
    """End-to-end tests for cross-file import resolution."""

    def test_cross_file_type_reference(self):
        """Type defined in one file should be usable in another."""
        with tempfile.TemporaryDirectory() as tmpdir:
            shared = Path(tmpdir) / "Shared"
            shared.mkdir()
            (shared / "SystemGatewayRequirements.sysml").write_text("""
package SystemGateway {
    enum def DriverType {
        Block1_IOP;
        RAS_A;
    }
}
""")
            main = Path(tmpdir) / "SystemGatewayMain.sysml"
            main.write_text("""
package SystemGateway {
    private import ScalarValues::*;
    part def System_Driver {
        attribute type : DriverType;
    }
}
""")
            model = load_files([
                shared / "SystemGatewayRequirements.sysml",
                main,
            ])
            issues = analyze(model)
            # DriverType should be resolved since both files are loaded
            undefined = [i for i in issues if i.code == "UNDEFINED_SYMBOL" and "DriverType" in i.message]
            assert len(undefined) == 0

    def test_standard_library_import_with_library_path(self):
        """Standard library imports should resolve when library path is provided."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "test.sysml"
            file_path.write_text("""
package Test {
    private import ScalarValues::*;
    attribute x : Real;
}
""")
            # Get the bundled library path
            import sysmlpy as sp
            library_path = Path(sp.__file__).parent / "library"

            model = load_files([file_path], library=library_path)
            issues = analyze(model)
            # UNRESOLVED_IMPORT should not be reported for ScalarValues
            unresolved = [i for i in issues if i.code == "UNRESOLVED_IMPORT" and "ScalarValues" in i.message]
            assert len(unresolved) == 0


class TestQuotedPackageNames:
    """Tests for quoted package name support."""

    def test_load_files_with_quoted_package_names(self):
        """Quoted package names should be handled correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            types = Path(tmpdir) / "Types.sysml"
            types.write_text("""
package 'My Types' {
    part def Engine;
}
""")
            main = Path(tmpdir) / "Main.sysml"
            main.write_text("""
package Main {
    private import 'My Types'::*;
    part myEngine : Engine;
}
""")
            model = load_files([types, main])
            issues = analyze(model)
            undefined = [i for i in issues if i.code == "UNDEFINED_SYMBOL" and "Engine" in i.message]
            assert len(undefined) == 0

    def test_import_extraction_quoted_names(self):
        """Import extraction should handle quoted package names."""
        from sysmlpy.project import _extract_imports

        assert _extract_imports("private import 'Enumeration Definitions'::*;") == ["'Enumeration Definitions'"]
        assert _extract_imports("private import 'Port Example'::SomePort;") == ["'Port Example'::SomePort"]
        assert _extract_imports("private import A::'B Name'::*;") == ["A::'B Name'"]

    def test_import_extraction_bare_import(self):
        """Goal 10: a bare import (no visibility keyword) is extracted."""
        from sysmlpy.project import _extract_imports

        assert _extract_imports("import ScalarValues::*;") == ["ScalarValues"]
        assert _extract_imports("import A::B::C;") == ["A::B::C"]

    def test_import_extraction_skips_comments(self):
        """Goal 10: commented-out imports are not false positives."""
        from sysmlpy.project import _extract_imports

        src = """
        package P {
            // private import Comment::Gone::*;
            /* import Also::Gone::*; */
            import Real::Import::*;
        }
        """
        assert _extract_imports(src) == ["Real::Import"]

    def test_import_extraction_skips_string_literals(self):
        """Goal 10: imports inside string literals are not matched."""
        from sysmlpy.project import _extract_imports

        src = """
        package P {
            doc about "private import Fake::Str::*;";
            import Real::Import::*;
        }
        """
        assert _extract_imports(src) == ["Real::Import"]

    def test_import_extraction_survives_stray_tokens(self):
        """Goal 10: dependency scanning tolerates broken sources."""
        from sysmlpy.project import _extract_imports

        src = """
        package P {
            part broken {
                import Stray::Tokens @@@ ;
            }
            import OK::After::Broken::*;
        }
        """
        assert _extract_imports(src) == ["OK::After::Broken"]

    def test_import_extraction_all_keyword(self):
        """Import extraction should handle the 'all' keyword."""
        from sysmlpy.project import _extract_imports

        assert _extract_imports("private import all Types::*;") == ["Types"]
        assert _extract_imports("public import all ScalarValues::*;") == ["ScalarValues"]
        assert _extract_imports("protected import all A::B::*::**;") == ["A::B"]


class TestMultipleLibraries:
    """Tests for multiple library directory support."""

    def test_analyze_with_multiple_library_paths(self):
        """analyze() should accept multiple library directories."""
        import sysmlpy
        from sysmlpy.semantic import LibrarySymbolIndex

        LibrarySymbolIndex.clear_cache()

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a custom library with additional types
            custom_lib = Path(tmpdir) / "custom"
            custom_lib.mkdir()
            (custom_lib / "CustomTypes.kerml").write_text("""
package CustomTypes {
    part def CustomPart;
}
""")
            file_path = Path(tmpdir) / "test.sysml"
            file_path.write_text("""
package Test {
    private import ScalarValues::*;
    private import CustomTypes::*;
    attribute x : Real;
    part myPart : CustomPart;
}
""")
            # Get the bundled library path
            library_path = Path(sysmlpy.__file__).parent / "library"

            model = load_files([file_path])
            issues = analyze(model, library=[library_path, custom_lib])

            # UNRESOLVED_IMPORT should not be reported for ScalarValues or CustomTypes
            unresolved = [i for i in issues if i.code == "UNRESOLVED_IMPORT"]
            assert len(unresolved) == 0

    def test_analyze_with_single_library_path(self):
        """analyze() should accept a single library path (str or Path)."""
        import sysmlpy
        from sysmlpy.semantic import LibrarySymbolIndex

        LibrarySymbolIndex.clear_cache()

        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "test.sysml"
            file_path.write_text("""
package Test {
    private import ScalarValues::*;
    attribute x : Real;
}
""")
            library_path = Path(sysmlpy.__file__).parent / "library"

            model = load_files([file_path])

            # Test with Path
            LibrarySymbolIndex.clear_cache()
            issues = analyze(model, library=library_path)
            unresolved = [i for i in issues if i.code == "UNRESOLVED_IMPORT"]
            assert len(unresolved) == 0

            # Test with str
            LibrarySymbolIndex.clear_cache()
            issues = analyze(model, library=str(library_path))
            unresolved = [i for i in issues if i.code == "UNRESOLVED_IMPORT"]
            assert len(unresolved) == 0
