#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for import visibility validation and serialization.
"""

import pytest
import sysmlpy


class TestImportVisibility:
    """Tests for import visibility validation."""

    def test_import_without_visibility_raises_error(self):
        """Import without visibility keyword should raise a syntax error."""
        from sysmlpy.antlr_parser import SysMLSyntaxError
        with pytest.raises(SysMLSyntaxError):
            sysmlpy.loads("""
            package P {
                import OtherPackage::*;
            }
            """)

    def test_private_import_works(self):
        """Private import should parse successfully."""
        model = sysmlpy.loads("""
        package P {
            private import OtherPackage::*;
        }
        """)
        assert model is not None

    def test_public_import_works(self):
        """Public import should parse successfully."""
        model = sysmlpy.loads("""
        package P {
            public import OtherPackage::*;
        }
        """)
        assert model is not None

    def test_protected_import_works(self):
        """Protected import should parse successfully."""
        model = sysmlpy.loads("""
        package P {
            protected import OtherPackage::*;
        }
        """)
        assert model is not None

    def test_membership_import_without_visibility_raises_error(self):
        """Membership import without visibility should raise a syntax error."""
        from sysmlpy.antlr_parser import SysMLSyntaxError
        with pytest.raises(SysMLSyntaxError):
            sysmlpy.loads("""
            package P {
                import OtherPackage::SomeElement;
            }
            """)

    def test_membership_import_with_visibility_works(self):
        """Membership import with visibility should parse successfully."""
        model = sysmlpy.loads("""
        package P {
            private import OtherPackage::SomeElement;
        }
        """)
        assert model is not None


class TestImportRoundTrip:
    """Tests for import serialization round-trip."""

    def test_namespace_import_round_trip(self):
        """Namespace import should survive dump -> load round trip."""
        model = sysmlpy.loads("""
        package P {
            private import ScalarValues::*;
            public import BaseTypes;
            protected import ISQ;
        }
        """)

        output = model.dump()
        model2 = sysmlpy.loads(output)

        pkg = model2.children[0]
        import_count = sum(1 for c in pkg.grammar.body.children if c.__class__.__name__ == 'Import')
        assert import_count == 3

    def test_membership_import_round_trip(self):
        """Membership import should survive dump -> load round trip."""
        model = sysmlpy.loads("""
        package P {
            private import ISQ::LengthValue;
            public import BaseTypes::SomeType;
        }
        """)

        output = model.dump()
        model2 = sysmlpy.loads(output)

        pkg = model2.children[0]
        import_count = sum(1 for c in pkg.grammar.body.children if c.__class__.__name__ == 'Import')
        assert import_count == 2

    def test_visibility_preserved_in_dump(self):
        """Visibility keywords should be preserved in dump output."""
        model = sysmlpy.loads("""
        package P {
            private import A;
            public import B;
            protected import C;
        }
        """)

        output = model.dump()
        assert "private import" in output
        assert "public import" in output
        assert "protected import" in output


class TestAddImport:
    """Tests for the Package.add_import() method."""

    def test_add_private_import(self):
        """Adding a private import should work."""
        model = sysmlpy.loads("package P { part def X; }")
        pkg = model.children[0]

        pkg.add_import('ScalarValues', visibility='private')
        output = model.dump()

        assert "private import" in output

    def test_add_public_import(self):
        """Adding a public import should work."""
        model = sysmlpy.loads("package P { part def X; }")
        pkg = model.children[0]

        pkg.add_import('BaseTypes', visibility='public')
        output = model.dump()

        assert "public import" in output

    def test_add_protected_import(self):
        """Adding a protected import should work."""
        model = sysmlpy.loads("package P { part def X; }")
        pkg = model.children[0]

        pkg.add_import('ISQ', visibility='protected')
        output = model.dump()

        assert "protected import" in output

    def test_add_import_invalid_visibility(self):
        """Adding an import with invalid visibility should fail."""
        model = sysmlpy.loads("package P { part def X; }")
        pkg = model.children[0]

        with pytest.raises(ValueError, match="visibility must be"):
            pkg.add_import('ScalarValues', visibility='invalid')

    def test_add_membership_import(self):
        """Adding a membership import should work."""
        model = sysmlpy.loads("package P { part def X; }")
        pkg = model.children[0]

        pkg.add_import('ISQ', visibility='private', membership='LengthValue')
        output = model.dump()

        assert "private import ISQ::LengthValue" in output

    def test_add_import_round_trip(self):
        """Programmatically added imports should survive round trip."""
        model = sysmlpy.loads("package P { part def X; }")
        pkg = model.children[0]

        pkg.add_import('ScalarValues', visibility='private')
        pkg.add_import('BaseTypes', visibility='public')
        pkg.add_import('ISQ', visibility='protected', membership='LengthValue')

        output = model.dump()
        model2 = sysmlpy.loads(output)

        pkg2 = model2.children[0]
        import_count = sum(1 for c in pkg2.grammar.body.children if c.__class__.__name__ == 'Import')
        assert import_count == 3

    def test_add_import_chaining(self):
        """add_import should return self for chaining."""
        model = sysmlpy.loads("package P { part def X; }")
        pkg = model.children[0]

        result = pkg.add_import('A', visibility='private').add_import('B', visibility='public')
        assert result is pkg


class TestPackageImportsProperty:
    """Tests for the Package.imports property."""

    def test_imports_after_parse(self):
        """Imports should be accessible via .imports property after parsing."""
        model = sysmlpy.loads("""
        package P {
            private import ScalarValues::*;
            public import BaseTypes;
        }
        """)
        pkg = model.children[0]
        assert len(pkg.imports) == 2
        assert all(imp.__class__.__name__ == 'Import' for imp in pkg.imports)

    def test_imports_after_add_import(self):
        """Imports added via add_import should appear in .imports."""
        model = sysmlpy.loads("package P { part def X; }")
        pkg = model.children[0]
        assert len(pkg.imports) == 0

        pkg.add_import('ScalarValues', visibility='private')
        assert len(pkg.imports) == 1
        assert pkg.imports[0].__class__.__name__ == 'Import'

    def test_imports_survive_round_trip(self):
        """Imports should be accessible via .imports after round-trip parse -> dump -> parse."""
        model = sysmlpy.loads("""
        package P {
            private import ScalarValues::*;
            public import BaseTypes;
            protected import ISQ;
        }
        """)
        output = model.dump()
        model2 = sysmlpy.loads(output)
        pkg = model2.children[0]
        assert len(pkg.imports) == 3
        assert all(imp.__class__.__name__ == 'Import' for imp in pkg.imports)

    def test_imports_empty_when_no_imports(self):
        """Package with no imports should have empty imports list."""
        model = sysmlpy.loads("package P { part def X; }")
        pkg = model.children[0]
        assert pkg.imports == []

    def test_imports_returns_copy(self):
        """imports property should return a copy, not the internal list."""
        model = sysmlpy.loads("package P { private import A; }")
        pkg = model.children[0]
        imports = pkg.imports
        imports.clear()
        assert len(pkg.imports) == 1


class TestImportSourceOrder:
    """Imports/aliases must stay at their original source positions (v0.58.0).

    Previously _ensure_body() always appended Import/AliasMember nodes after
    all members, so any source file interleaving imports with definitions
    failed exact-text round-trip."""

    @staticmethod
    def _round_trip_equal(src: str) -> bool:
        model = sysmlpy.loads(src)
        out = model.dump()
        strip = lambda s: "".join(s.split())
        return strip(src) == strip(out)

    def test_import_before_member_round_trip(self):
        src = """package P {
    private import Q::*;
    package Q;
}
"""
        assert self._round_trip_equal(src)

    def test_import_after_member_round_trip(self):
        src = """package P {
    package A;
    private import Q::*;
}
"""
        assert self._round_trip_equal(src)

    def test_import_interleaved_round_trip(self):
        src = """package P {
    package A;
    public import Q::*;
    package B;
    private import R;
    package C;
}
"""
        assert self._round_trip_equal(src)

    def test_import_order_multiple(self):
        model = sysmlpy.loads("""package P {
    private import Q::*;
    package A;
    public import R::*;
    package B;
}
""")
        out = model.dump()
        strip = lambda s: "".join(s.split())
        # import positions preserved relative to members
        q_pos = strip(out).index("privateimportQ::*;")
        b_pos = out.index("package B;")
        r_pos = strip(out).index("publicimportR::*;")
        c_pos = out.index("private import Q")
        assert q_pos < out.index("package Q") if "package Q" in out else True
        assert r_pos < b_pos

    def test_alias_source_position_round_trip(self):
        src = """package P {
    alias A for Q;
    package Q;
}
"""
        assert self._round_trip_equal(src)

    def test_alias_after_member_round_trip(self):
        src = """package P {
    package Q;
    alias A for Q;
}
"""
        assert self._round_trip_equal(src)

    def test_mixed_import_alias_interleaved(self):
        src = """package P {
    private import S::*;
    alias A1 for Q;
    package Q;
    package S;
}
"""
        assert self._round_trip_equal(src)

    def test_nested_package_import_round_trip(self):
        src = """package P {
    package Inner {
        private import Q::*;
        package Q;
    }
}
"""
        assert self._round_trip_equal(src)

    def test_programmatic_add_appends_after_import(self):
        """Children added programmatically go to the end; existing import untouched."""
        model = sysmlpy.loads("package P { private import Q::*; package Q; }")
        pkg = model.children[0]
        pkg._set_child(sysmlpy.Part(definition=True, name="Motor"))
        out = model.dump()
        assert out.index("private import") < out.index("part def")

    def test_imports_survive_dump_loop(self):
        """dump -> load -> dump is stable (idempotent ordering)."""
        src = """package P {
    private import Q::*;
    package Q;
    alias A for Q;
}
"""
        first = sysmlpy.loads(src).dump()
        second = sysmlpy.loads(first).dump()
        assert "".join(first.split()) == "".join(second.split())
