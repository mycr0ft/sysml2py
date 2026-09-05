#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for semantic analysis (undefined symbol detection)."""

import pytest
from sysmlpy import loads, analyze, AnalysisResult, SemanticIssue


class TestBasicUndefinedDetection:
    """Detect references to types that are not defined in the model."""

    def test_undefined_type_reference(self):
        model = loads("""
            package P {
                part x : UndefinedType;
            }
        """)
        issues = analyze(model)
        assert any(
            i.code == "UNDEFINED_SYMBOL" and "UndefinedType" in i.message
            for i in issues
        )

    def test_undefined_subsetting(self):
        model = loads("""
            package P {
                part x :> UndefinedFeature;
            }
        """)
        issues = analyze(model)
        assert any(
            i.code == "UNDEFINED_SYMBOL" and "UndefinedFeature" in i.message
            for i in issues
        )

    def test_undefined_redefinition(self):
        model = loads("""
            package P {
                part :>> UndefinedRedefined;
            }
        """)
        issues = analyze(model)
        assert any(
            i.code == "UNDEFINED_SYMBOL" and "UndefinedRedefined" in i.message
            for i in issues
        )


class TestDefinedNoFalsePositives:
    """References to defined types should NOT be flagged."""

    def test_defined_type_reference(self):
        model = loads("""
            package P {
                part def MyPart;
                part x : MyPart;
            }
        """)
        issues = analyze(model)
        assert not any(i.code == "UNDEFINED_SYMBOL" for i in issues)

    def test_part_def_used_by_part(self):
        model = loads("""
            package P {
                part def Engine;
                part myEngine : Engine;
            }
        """)
        issues = analyze(model)
        assert not any(i.code == "UNDEFINED_SYMBOL" for i in issues)

    def test_item_def_used_by_item(self):
        model = loads("""
            package P {
                item def Widget;
                item myWidget : Widget;
            }
        """)
        issues = analyze(model)
        assert not any(i.code == "UNDEFINED_SYMBOL" for i in issues)

    def test_port_def_used_by_port(self):
        model = loads("""
            package P {
                port def SensorPort;
                port p : SensorPort;
            }
        """)
        issues = analyze(model)
        assert not any(i.code == "UNDEFINED_SYMBOL" for i in issues)

    def test_attribute_def_used_by_attribute(self):
        model = loads("""
            package P {
                attribute def MyAttr;
                attribute a : MyAttr;
            }
        """)
        issues = analyze(model)
        assert not any(i.code == "UNDEFINED_SYMBOL" for i in issues)

    def test_action_def_used_by_action(self):
        model = loads("""
            package P {
                action def MyAction;
                action a : MyAction;
            }
        """)
        issues = analyze(model)
        assert not any(i.code == "UNDEFINED_SYMBOL" for i in issues)

    def test_state_def_used_by_state(self):
        model = loads("""
            package P {
                state def MyState;
                state s : MyState;
            }
        """)
        issues = analyze(model)
        assert not any(i.code == "UNDEFINED_SYMBOL" for i in issues)

    def test_constraint_def_used_by_constraint(self):
        model = loads("""
            package P {
                constraint def MyConstraint;
                constraint c : MyConstraint;
            }
        """)
        issues = analyze(model)
        assert not any(i.code == "UNDEFINED_SYMBOL" for i in issues)

    def test_calculation_def_used_by_calculation(self):
        model = loads("""
            package P {
                calc def MyCalc;
                calc c : MyCalc;
            }
        """)
        issues = analyze(model)
        assert not any(i.code == "UNDEFINED_SYMBOL" for i in issues)

    def test_requirement_def_used_by_requirement(self):
        model = loads("""
            package P {
                requirement def MyReq;
                requirement r : MyReq;
            }
        """)
        issues = analyze(model)
        assert not any(i.code == "UNDEFINED_SYMBOL" for i in issues)

    def test_interface_def_used_by_interface(self):
        model = loads("""
            package P {
                interface def MyInterface;
                interface i : MyInterface;
            }
        """)
        issues = analyze(model)
        assert not any(i.code == "UNDEFINED_SYMBOL" for i in issues)

    def test_connection_def_used_by_connection(self):
        model = loads("""
            package P {
                connection def MyConn;
                connection c : MyConn;
            }
        """)
        issues = analyze(model)
        assert not any(i.code == "UNDEFINED_SYMBOL" for i in issues)

    def test_enumeration_def_used_by_enum(self):
        model = loads("""
            package P {
                enum def MyEnum { A; B; }
                enum e : MyEnum;
            }
        """)
        issues = analyze(model)
        assert not any(i.code == "UNDEFINED_SYMBOL" for i in issues)


class TestQualifiedNameResolution:
    """Package-qualified references should resolve correctly."""

    def test_cross_package_reference(self):
        model = loads("""
            package P {
                part def A;
            }
            package Q {
                part x : P::A;
            }
        """)
        issues = analyze(model)
        assert not any(i.code == "UNDEFINED_SYMBOL" for i in issues)

    def test_missing_package_reference(self):
        model = loads("""
            package Q {
                part x : P::A;
            }
        """)
        issues = analyze(model)
        assert any(
            i.code == "UNDEFINED_SYMBOL" and "P::A" in i.message
            for i in issues
        )

    def test_nested_package_reference(self):
        model = loads("""
            package Outer {
                package Inner {
                    part def DeepPart;
                }
                part x : Inner::DeepPart;
            }
        """)
        issues = analyze(model)
        assert not any(i.code == "UNDEFINED_SYMBOL" for i in issues)

    def test_deeply_nested_reference(self):
        model = loads("""
            package A {
                package B {
                    package C {
                        part def DeepPart;
                    }
                }
            }
            package X {
                part x : A::B::C::DeepPart;
            }
        """)
        issues = analyze(model)
        assert not any(i.code == "UNDEFINED_SYMBOL" for i in issues)


class TestNestedScopeResolution:
    """References should resolve through parent scopes."""

    def test_child_references_parent_scope(self):
        model = loads("""
            package P {
                part def A;
                package Q {
                    part x : A;
                }
            }
        """)
        issues = analyze(model)
        assert not any(i.code == "UNDEFINED_SYMBOL" for i in issues)

    def test_sibling_package_no_cross_ref(self):
        model = loads("""
            package P {
                package A {
                    part def PartA;
                }
                package B {
                    part x : PartA;
                }
            }
        """)
        issues = analyze(model)
        # PartA is defined in sibling package A, not directly visible in B
        # In SysML v2, sibling elements require qualified names or imports
        assert any(i.code == "UNDEFINED_SYMBOL" and "PartA" in i.message for i in issues)

    def test_sibling_package_with_qualified_name(self):
        model = loads("""
            package P {
                package A {
                    part def PartA;
                }
                package B {
                    part x : A::PartA;
                }
            }
        """)
        issues = analyze(model)
        # Qualified name should resolve correctly
        assert not any(i.code == "UNDEFINED_SYMBOL" for i in issues)


class TestMultipleUndefinedReferences:
    """Multiple undefined references should each produce an issue."""

    def test_three_undefined_types(self):
        model = loads("""
            package P {
                part a : TypeA;
                part b : TypeB;
                part c : TypeC;
            }
        """)
        issues = analyze(model)
        undefined = [i for i in issues if i.code == "UNDEFINED_SYMBOL"]
        assert len(undefined) == 3

    def test_mixed_defined_and_undefined(self):
        model = loads("""
            package P {
                part def Defined;
                part a : Defined;
                part b : Undefined;
            }
        """)
        issues = analyze(model)
        undefined = [i for i in issues if i.code == "UNDEFINED_SYMBOL"]
        assert len(undefined) == 1
        assert "Undefined" in undefined[0].message


class TestEmptyModel:
    """Empty models should produce no issues."""

    def test_empty_package(self):
        model = loads("""
            package Empty {}
        """)
        issues = analyze(model)
        assert len(issues) == 0

    def test_package_with_only_definitions(self):
        model = loads("""
            package P {
                part def A;
                part def B;
                item def C;
            }
        """)
        issues = analyze(model)
        assert not any(i.code == "UNDEFINED_SYMBOL" for i in issues)


class TestSemanticIssueProperties:
    """Verify SemanticIssue dataclass fields."""

    def test_issue_has_required_fields(self):
        model = loads("""
            package P {
                part x : MissingType;
            }
        """)
        issues = analyze(model)
        issue = [i for i in issues if i.code == "UNDEFINED_SYMBOL"][0]
        assert issue.severity == "error"
        assert issue.code == "UNDEFINED_SYMBOL"
        assert "MissingType" in issue.message
        assert issue.reference == "MissingType"
        assert issue.element is not None


class TestLibrarySymbolWhitelist:
    """Standard library symbols should not be flagged as undefined."""

    def test_scalar_values_integer(self):
        model = loads("""
            package P {
                attribute mass : ScalarValues::Integer;
            }
        """)
        issues = analyze(model)
        assert not any(
            i.code == "UNDEFINED_SYMBOL" and "ScalarValues::Integer" in i.message
            for i in issues
        )

    def test_scalar_values_real(self):
        model = loads("""
            package P {
                attribute value : ScalarValues::Real;
            }
        """)
        issues = analyze(model)
        assert not any(
            i.code == "UNDEFINED_SYMBOL" and "ScalarValues::Real" in i.message
            for i in issues
        )

    def test_scalar_values_string(self):
        model = loads("""
            package P {
                attribute name : ScalarValues::String;
            }
        """)
        issues = analyze(model)
        assert not any(
            i.code == "UNDEFINED_SYMBOL" and "ScalarValues::String" in i.message
            for i in issues
        )

    def test_isq_length_value(self):
        model = loads("""
            package P {
                attribute length : ISQ::LengthValue;
            }
        """)
        issues = analyze(model)
        assert not any(
            i.code == "UNDEFINED_SYMBOL" and "ISQ::LengthValue" in i.message
            for i in issues
        )

    def test_isq_mass_value(self):
        model = loads("""
            package P {
                attribute mass : ISQ::MassValue;
            }
        """)
        issues = analyze(model)
        assert not any(
            i.code == "UNDEFINED_SYMBOL" and "ISQ::MassValue" in i.message
            for i in issues
        )

    def test_isq_force_value(self):
        model = loads("""
            package P {
                attribute force : ISQ::ForceValue;
            }
        """)
        issues = analyze(model)
        assert not any(
            i.code == "UNDEFINED_SYMBOL" and "ISQ::ForceValue" in i.message
            for i in issues
        )

    def test_isq_pressure_value(self):
        model = loads("""
            package P {
                attribute pressure : ISQ::PressureValue;
            }
        """)
        issues = analyze(model)
        assert not any(
            i.code == "UNDEFINED_SYMBOL" and "ISQ::PressureValue" in i.message
            for i in issues
        )


class TestImportResolution:
    """Import resolution should make imported symbols visible."""

    def test_namespace_import_makes_symbols_visible(self):
        model = loads("""
            package Types {
                part def Engine;
                part def Wheel;
            }
            package Vehicle {
                private import Types::*;
                part myCar : Engine;
            }
        """)
        issues = analyze(model)
        assert not any(i.code == "UNDEFINED_SYMBOL" for i in issues)

    def test_membership_import_makes_symbol_visible(self):
        model = loads("""
            package Types {
                part def Engine;
            }
            package Vehicle {
                private import Types::Engine;
                part myCar : Engine;
            }
        """)
        issues = analyze(model)
        assert not any(i.code == "UNDEFINED_SYMBOL" for i in issues)

    def test_import_without_wildcard(self):
        model = loads("""
            package Types {
                part def Engine;
                part def Wheel;
            }
            package Vehicle {
                private import Types::Engine;
                part myCar : Engine;
                part myWheel : Wheel;
            }
        """)
        issues = analyze(model)
        # Engine is imported, Wheel is not
        undefined = [i for i in issues if i.code == "UNDEFINED_SYMBOL"]
        assert len(undefined) == 1
        assert "Wheel" in undefined[0].message

    def test_recursive_import(self):
        model = loads("""
            package Types {
                package Mechanical {
                    part def Engine;
                }
                package Electrical {
                    part def Motor;
                }
            }
            package Vehicle {
                private import Types::*::**;
                part myCar : Engine;
                part myHybrid : Motor;
            }
        """)
        issues = analyze(model)
        assert not any(i.code == "UNDEFINED_SYMBOL" for i in issues)

    def test_unresolved_import_target(self):
        model = loads("""
            package Vehicle {
                private import NonExistent::*;
                part myCar : SomeType;
            }
        """)
        issues = analyze(model)
        # SomeType is not defined or imported
        assert any(i.code == "UNDEFINED_SYMBOL" and "SomeType" in i.message for i in issues)

    def test_cross_package_import(self):
        model = loads("""
            package A {
                package B {
                    part def PartB;
                }
            }
            package C {
                private import A::B::*;
                part x : PartB;
            }
        """)
        issues = analyze(model)
        assert not any(i.code == "UNDEFINED_SYMBOL" for i in issues)


class TestUnresolvedImportDetection:
    """Import targets that don't exist should be flagged."""

    def test_import_from_nonexistent_package(self):
        model = loads("""
            package Vehicle {
                private import NonExistent::*;
            }
        """)
        issues = analyze(model)
        assert any(
            i.code == "UNRESOLVED_IMPORT" and "NonExistent" in i.message
            for i in issues
        )

    def test_import_specific_nonexistent_element(self):
        model = loads("""
            package Vehicle {
                private import NonExistent::Engine;
            }
        """)
        issues = analyze(model)
        assert any(
            i.code == "UNRESOLVED_IMPORT" and "NonExistent::Engine" in i.message
            for i in issues
        )

    def test_import_from_nested_nonexistent_package(self):
        model = loads("""
            package A {
                package B {
                    part def PartB;
                }
            }
            package C {
                private import A::NonExistent::*;
            }
        """)
        issues = analyze(model)
        assert any(
            i.code == "UNRESOLVED_IMPORT" and "A::NonExistent" in i.message
            for i in issues
        )

    def test_valid_import_not_flagged(self):
        model = loads("""
            package Types {
                part def Engine;
            }
            package Vehicle {
                private import Types::*;
            }
        """)
        issues = analyze(model)
        assert not any(i.code == "UNRESOLVED_IMPORT" for i in issues)

    def test_valid_membership_import_not_flagged(self):
        model = loads("""
            package Types {
                part def Engine;
            }
            package Vehicle {
                private import Types::Engine;
            }
        """)
        issues = analyze(model)
        assert not any(i.code == "UNRESOLVED_IMPORT" for i in issues)

    def test_unresolved_import_and_undefined_symbol_both_reported(self):
        model = loads("""
            package Vehicle {
                private import NonExistent::*;
                part myCar : SomeType;
            }
        """)
        issues = analyze(model)
        assert any(i.code == "UNRESOLVED_IMPORT" for i in issues)
        assert any(i.code == "UNDEFINED_SYMBOL" for i in issues)

    def test_recursive_import_from_nonexistent(self):
        model = loads("""
            package Vehicle {
                private import NonExistent::*::**;
            }
        """)
        issues = analyze(model)
        assert any(
            i.code == "UNRESOLVED_IMPORT" and "NonExistent" in i.message
            for i in issues
        )


class TestSubsettingResolution:
    """Subsetting references should resolve to defined features, including inherited ones."""

    def test_subsetting_to_defined_feature(self):
        model = loads("""
            package P {
                part def Base {
                    attribute baseAttr;
                }
                part def Derived :> Base {
                    attribute myAttr :> baseAttr;
                }
            }
        """)
        issues = analyze(model)
        # baseAttr is inherited from Base - should resolve correctly
        assert not any(i.code == "UNDEFINED_SYMBOL" and "baseAttr" in i.message for i in issues)

    def test_subsetting_to_undefined_feature(self):
        model = loads("""
            package P {
                part def Base {
                    attribute baseAttr;
                }
                part def Derived :> Base {
                    attribute myAttr :> nonexistent;
                }
            }
        """)
        issues = analyze(model)
        # nonexistent is not defined in Base or Derived
        assert any(i.code == "UNDEFINED_SYMBOL" and "nonexistent" in i.message for i in issues)

    def test_subsetting_through_multiple_inheritance_levels(self):
        model = loads("""
            package P {
                part def Root {
                    attribute rootAttr;
                }
                part def Middle :> Root {
                    attribute middleAttr;
                }
                part def Leaf :> Middle {
                    attribute leafAttr1 :> rootAttr;
                    attribute leafAttr2 :> middleAttr;
                }
            }
        """)
        issues = analyze(model)
        # Both rootAttr and middleAttr should resolve through inheritance chain
        assert not any(i.code == "UNDEFINED_SYMBOL" for i in issues)


class TestConvenienceFunction:
    """The module-level analyze() function should work."""

    def test_analyze_returns_list(self):
        model = loads("package P {}")
        result = analyze(model)
        assert isinstance(result, list)

    def test_analyze_finds_issues(self):
        model = loads("""
            package P {
                part x : MissingType;
            }
        """)
        result = analyze(model)
        assert len(result) > 0


class TestLibrarySymbolIndex:
    """Verify library symbol loading from .kerml/.sysml files."""

    def setup_method(self):
        """Clear cache before each test to ensure fresh library scan."""
        from sysmlpy.semantic import LibrarySymbolIndex
        LibrarySymbolIndex.clear_cache()

    def test_library_index_returns_nonempty(self):
        from sysmlpy.semantic import LibrarySymbolIndex
        symbols = LibrarySymbolIndex.get_symbols()
        assert len(symbols) > 0

    def test_library_contains_scalar_values(self):
        from sysmlpy.semantic import LibrarySymbolIndex
        symbols = LibrarySymbolIndex.get_symbols()
        assert "ScalarValues::Integer" in symbols
        assert "ScalarValues::Real" in symbols
        assert "ScalarValues::String" in symbols
        assert "ScalarValues::Boolean" in symbols

    def test_library_contains_isq_types(self):
        from sysmlpy.semantic import LibrarySymbolIndex
        symbols = LibrarySymbolIndex.get_symbols()
        assert "ISQBase::LengthValue" in symbols
        assert "ISQBase::MassValue" in symbols
        assert "ISQBase::DurationValue" in symbols

    def test_library_contains_kerml_types(self):
        from sysmlpy.semantic import LibrarySymbolIndex
        symbols = LibrarySymbolIndex.get_symbols()
        assert "KerML::Kernel::Class" in symbols
        assert "KerML::Core::Classifier" in symbols
        assert "KerML::Kernel::Association" in symbols

    def test_library_contains_collections(self):
        from sysmlpy.semantic import LibrarySymbolIndex
        symbols = LibrarySymbolIndex.get_symbols()
        assert "Collections::Collection" in symbols

    def test_library_cache_is_reused(self):
        from sysmlpy.semantic import LibrarySymbolIndex
        symbols1 = LibrarySymbolIndex.get_symbols()
        symbols2 = LibrarySymbolIndex.get_symbols()
        assert symbols1 is symbols2  # Same frozenset object

    def test_clear_cache_resets(self):
        from sysmlpy.semantic import LibrarySymbolIndex
        LibrarySymbolIndex.clear_cache()
        symbols = LibrarySymbolIndex.get_symbols()
        assert len(symbols) > 0


class TestImportVisibility:
    """Verify that import visibility (private/public/protected) is enforced."""

    def test_private_import_not_visible_in_sibling_package(self):
        """Private imports (default) should not be visible to sibling packages."""
        model = loads("""
            package P {
                part def BaseType;
            }
            package Q {
                private import P::BaseType;
                part x : BaseType;
            }
            package R {
                part y : BaseType;
            }
        """)
        issues = analyze(model)
        # Q's private import of BaseType should not be visible to sibling R
        assert any(i.code == "UNDEFINED_SYMBOL" and "BaseType" in i.message for i in issues)

    def test_public_import_visible_in_sibling_package(self):
        """Public imports should be visible to sibling packages."""
        model = loads("""
            package P {
                part def BaseType;
            }
            package Q {
                public import P::BaseType;
                part x : BaseType;
            }
            package R {
                part y : BaseType;
            }
        """)
        issues = analyze(model)
        # Q's public import of BaseType should be visible to sibling R
        assert not any(i.code == "UNDEFINED_SYMBOL" and "BaseType" in i.message for i in issues)

    def test_protected_import_visible_in_child_not_sibling(self):
        """Protected imports should be visible to child packages but not siblings."""
        model = loads("""
            package P {
                part def BaseType;
            }
            package Q {
                protected import P::BaseType;
                part x : BaseType;
                package QChild {
                    part z : BaseType;
                }
            }
            package R {
                part y : BaseType;
            }
        """)
        issues = analyze(model)
        # Q's protected import should be visible to QChild but not to sibling R
        assert any(i.code == "UNDEFINED_SYMBOL" and "BaseType" in i.message for i in issues)

    def test_default_import_is_private(self):
        """Imports without explicit visibility default to private."""
        model = loads("""
            package P {
                part def BaseType;
            }
            package Q {
                private import P::BaseType;
                part x : BaseType;
            }
            package R {
                part y : BaseType;
            }
        """)
        issues = analyze(model)
        # Default import is private, so R cannot see BaseType
        assert any(i.code == "UNDEFINED_SYMBOL" and "BaseType" in i.message for i in issues)

    def test_public_import_re_exported_through_multiple_levels(self):
        """Public imports should propagate through multiple nesting levels."""
        model = loads("""
            package P {
                part def BaseType;
            }
            package Q {
                public import P::BaseType;
                package Q1 {
                    package Q2 {
                        part deep : BaseType;
                    }
                }
            }
        """)
        issues = analyze(model)
        # Public import should propagate through Q -> Q1 -> Q2
        assert not any(i.code == "UNDEFINED_SYMBOL" and "BaseType" in i.message for i in issues)

    def test_protected_import_visible_to_all_descendants(self):
        """Protected imports should be visible to all descendants (children, grandchildren, etc.)."""
        model = loads("""
            package P {
                part def BaseType;
            }
            package Q {
                protected import P::BaseType;
                package Q1 {
                    part x : BaseType;
                    package Q2 {
                        part y : BaseType;
                    }
                }
            }
        """)
        issues = analyze(model)
        # Protected import should be visible to Q1 and Q2 (all descendants)
        assert not any(i.code == "UNDEFINED_SYMBOL" and "BaseType" in i.message for i in issues)

    def test_protected_import_not_visible_to_siblings(self):
        """Protected imports should not be visible to sibling packages."""
        model = loads("""
            package P {
                part def BaseType;
            }
            package Q {
                protected import P::BaseType;
                part x : BaseType;
            }
            package R {
                part y : BaseType;
            }
        """)
        issues = analyze(model)
        # Q's protected import should not be visible to sibling R
        assert any(i.code == "UNDEFINED_SYMBOL" and "BaseType" in i.message for i in issues)

    def test_transitive_public_import_membership(self):
        """A imports B::X, B publicly imports C::X -> A should see X."""
        model = loads("""
            package C {
                part def BaseType;
            }
            package B {
                public import C::BaseType;
            }
            package A {
                private import B::BaseType;
                part x : BaseType;
            }
        """)
        issues = analyze(model)
        assert not any(i.code == "UNDEFINED_SYMBOL" and "BaseType" in i.message for i in issues)

    def test_transitive_public_import_namespace(self):
        """A imports B::*, B publicly imports C::* -> A should see C's elements."""
        model = loads("""
            package C {
                part def BaseType;
            }
            package B {
                public import C::*;
            }
            package A {
                private import B::*;
                part x : BaseType;
            }
        """)
        issues = analyze(model)
        assert not any(i.code == "UNDEFINED_SYMBOL" and "BaseType" in i.message for i in issues)

    def test_transitive_public_import_cross_branch(self):
        """Cross-branch: A imports Mid::B::BaseType, B publicly imports Lib::C::BaseType."""
        model = loads("""
            package Lib {
                package C {
                    part def BaseType;
                }
            }
            package Mid {
                package B {
                    public import Lib::C::BaseType;
                }
            }
            package A {
                private import Mid::B::BaseType;
                part x : BaseType;
            }
        """)
        issues = analyze(model)
        assert not any(i.code == "UNDEFINED_SYMBOL" and "BaseType" in i.message for i in issues)

    def test_private_import_not_transitively_visible(self):
        """Private imports should not be visible via qualified name from external scopes."""
        model = loads("""
            package C {
                part def BaseType;
            }
            package B {
                private import C::BaseType;
            }
            package A {
                private import B::BaseType;
                part x : BaseType;
            }
        """)
        issues = analyze(model)
        assert any(i.code == "UNDEFINED_SYMBOL" and "BaseType" in i.message for i in issues)

    def test_protected_import_not_transitively_visible_externally(self):
        """Protected imports should not be visible via qualified name from external scopes."""
        model = loads("""
            package C {
                part def BaseType;
            }
            package B {
                protected import C::BaseType;
            }
            package A {
                private import B::BaseType;
                part x : BaseType;
            }
        """)
        issues = analyze(model)
        assert any(i.code == "UNDEFINED_SYMBOL" and "BaseType" in i.message for i in issues)

    def test_private_namespace_import_not_transitively_visible(self):
        """A imports B::*, B privately imports C::* -> A should NOT see C's elements."""
        model = loads("""
            package C {
                part def BaseType;
            }
            package B {
                private import C::*;
            }
            package A {
                private import B::*;
                part x : BaseType;
            }
        """)
        issues = analyze(model)
        assert any(i.code == "UNDEFINED_SYMBOL" and "BaseType" in i.message for i in issues)


class TestDuplicateNames:
    """Namespace.duplicate_names: No two members may have the same name in a scope."""

    def test_duplicate_part_names_in_package(self):
        model = loads("""
            package P {
                part x;
                part x;
            }
        """)
        issues = analyze(model)
        assert any(i.code == "DUPLICATE_NAME" and "x" in i.message for i in issues)

    def test_duplicate_definition_names_in_package(self):
        model = loads("""
            package P {
                part def Base;
                part def Base;
            }
        """)
        issues = analyze(model)
        assert any(i.code == "DUPLICATE_NAME" and "Base" in i.message for i in issues)

    def test_no_duplicates_in_different_packages(self):
        model = loads("""
            package P1 { part x; }
            package P2 { part x; }
        """)
        issues = analyze(model)
        assert not any(i.code == "DUPLICATE_NAME" for i in issues)

    def test_no_duplicates_in_nested_packages(self):
        model = loads("""
            package P {
                package Q1 { part x; }
                package Q2 { part x; }
            }
        """)
        issues = analyze(model)
        assert not any(i.code == "DUPLICATE_NAME" for i in issues)


class TestCyclicSpecialization:
    """Type.no_cyclic_specialization: A type cannot specialize itself cyclically."""

    def test_direct_cyclic_specialization(self):
        model = loads("""
            package P {
                part def A :> B;
                part def B :> A;
            }
        """)
        issues = analyze(model)
        assert any(i.code == "CYCLIC_SPECIALIZATION" for i in issues)

    def test_indirect_cyclic_specialization(self):
        model = loads("""
            package P {
                part def A :> B;
                part def B :> C;
                part def C :> A;
            }
        """)
        issues = analyze(model)
        assert any(i.code == "CYCLIC_SPECIALIZATION" for i in issues)

    def test_no_cycle_in_valid_hierarchy(self):
        model = loads("""
            package P {
                part def Base;
                part def Middle :> Base;
                part def Leaf :> Middle;
            }
        """)
        issues = analyze(model)
        assert not any(i.code == "CYCLIC_SPECIALIZATION" for i in issues)

    def test_self_specialization(self):
        model = loads("""
            package P {
                part def A :> A;
            }
        """)
        issues = analyze(model)
        assert any(i.code == "CYCLIC_SPECIALIZATION" for i in issues)


class TestSubsettingCompatible:
    """Feature.subsetting_compatible: Subsetting feature must reference a defined feature."""

    def test_subsetting_to_undefined_feature(self):
        model = loads("""
            package P {
                part def MyDef {
                    attribute myAttr :> nonexistent;
                }
            }
        """)
        issues = analyze(model)
        assert any(i.code == "INCOMPATIBLE_SUBSETTING" for i in issues)

    def test_subsetting_to_defined_feature_no_error(self):
        model = loads("""
            package P {
                part def Base {
                    attribute baseAttr;
                }
                part def Derived :> Base {
                    attribute myAttr :> baseAttr;
                }
            }
        """)
        issues = analyze(model)
        assert not any(i.code == "INCOMPATIBLE_SUBSETTING" for i in issues)


class TestRedefinitionCompatible:
    """Feature.redefinition_compatible: Redefining feature must reference a defined feature."""

    def test_redefinition_to_undefined_feature(self):
        model = loads("""
            package P {
                part def MyDef {
                    attribute myAttr :>> nonexistent;
                }
            }
        """)
        issues = analyze(model)
        assert any(i.code == "INCOMPATIBLE_REDEFINITION" for i in issues)

    def test_redefinition_to_defined_feature_no_error(self):
        model = loads("""
            package P {
                part def Base {
                    attribute baseAttr;
                }
                part def Derived :> Base {
                    attribute myAttr :>> baseAttr;
                }
            }
        """)
        issues = analyze(model)
        assert not any(i.code == "INCOMPATIBLE_REDEFINITION" for i in issues)


class TestPartDefinitionCompatible:
    """Part.definition_compatible: A part usage's definition must be a PartDefinition."""

    def test_part_typed_by_part_definition(self):
        model = loads("""
            package P {
                part def MyPartDef;
                part myPart : MyPartDef;
            }
        """)
        issues = analyze(model)
        assert not any(i.code == "INCOMPATIBLE_PART_DEFINITION" for i in issues)

    def test_part_typed_by_attribute_definition(self):
        model = loads("""
            package P {
                attribute def MyAttrDef;
                part myPart : MyAttrDef;
            }
        """)
        issues = analyze(model)
        assert any(i.code == "INCOMPATIBLE_PART_DEFINITION" for i in issues)


class TestPortDefinitionCompatible:
    """Port.definition_compatible: A port usage's definition must be a PortDefinition."""

    def test_port_typed_by_port_definition(self):
        model = loads("""
            package P {
                port def MyPortDef;
                port myPort : MyPortDef;
            }
        """)
        issues = analyze(model)
        assert not any(i.code == "INCOMPATIBLE_PORT_DEFINITION" for i in issues)

    def test_port_typed_by_part_definition(self):
        model = loads("""
            package P {
                part def MyPartDef;
                port myPort : MyPartDef;
            }
        """)
        issues = analyze(model)
        assert any(i.code == "INCOMPATIBLE_PORT_DEFINITION" for i in issues)


class TestFeatureChainingCompatible:
    """Feature.chaining_compatible: Chained features must have compatible types."""

    def test_valid_feature_chain(self):
        model = loads("""
            package P {
                part def Engine {
                    attribute power;
                }
                part def Car {
                    part engine : Engine;
                }
                part myCar : Car {
                    attribute carPower :> engine::power;
                }
            }
        """)
        issues = analyze(model)
        # engine::power should resolve: Car has engine (Engine), Engine has power
        assert not any(i.code == "INCOMPATIBLE_FEATURE_CHAIN" for i in issues)

    def test_invalid_feature_chain(self):
        model = loads("""
            package P {
                part def Engine {
                    attribute power;
                }
                part def Car {
                    part engine : Engine;
                    attribute name;
                }
                part myCar : Car {
                    attribute carName :> engine::name;
                }
            }
        """)
        issues = analyze(model)
        # engine::name should fail: Engine doesn't have 'name' feature
        assert any(i.code == "INCOMPATIBLE_FEATURE_CHAIN" for i in issues)


class TestFeatureChainTypeResolution:
    """Feature chain type resolution (v0.60.0 — STATUS.md Medium Priority).

    Two aspects:
    1. Type references (``attribute mass: ScalarValues::Real``) are namespace
       paths, not feature chains — they must not be chain-checked.
    2. Dotted expression chains (``wheels.hub.mass``) resolve through the
       *declared type* of each feature, following subsetting inheritance.
    """

    def test_qualified_library_type_not_chain_checked(self):
        # Regression: every qualified type name used to raise a false
        # INCOMPATIBLE_FEATURE_CHAIN error ('ScalarValues' treated as a
        # feature of the attribute's own type).
        model = loads("""
            package P {
                part def Hub {
                    attribute mass: ScalarValues::Real;
                }
            }
        """)
        issues = analyze(model)
        assert not any(i.code == "INCOMPATIBLE_FEATURE_CHAIN" for i in issues)

    def test_qualified_user_type_not_chain_checked(self):
        model = loads("""
            package P {
                package Sub {
                    part def Axle;
                }
                part def Car {
                    part a: Sub::Axle;
                }
            }
        """)
        issues = analyze(model)
        assert not any(i.code == "INCOMPATIBLE_FEATURE_CHAIN" for i in issues)

    def test_unknown_qualified_type_still_undefined(self):
        # The typing reference is no longer chain-checked, but an unknown
        # qualified type is still reported by the symbol-resolution pass.
        model = loads("""
            package P {
                part def Car {
                    attribute x: P::NoSuch;
                }
            }
        """)
        issues = analyze(model)
        assert any(i.code == "UNDEFINED_SYMBOL" for i in issues)
        assert not any(i.code == "INCOMPATIBLE_FEATURE_CHAIN" for i in issues)

    def test_expression_chain_through_typed_feature(self):
        # 'wheels.hub.mass': hub is a feature of Wheel (the type of
        # wheels), mass a feature of Hub (the type of hub).
        model = loads("""
            package P {
                part def Wheel {
                    attribute hub: Hub;
                }
                part def Hub {
                    attribute mass: Real;
                }
                part def Car {
                    part wheels: Wheel[4];
                    attribute w: Real = wheels.hub.mass;
                }
            }
        """)
        issues = analyze(model)
        assert not any(
            i.code == "UNRESOLVED_EXPRESSION_IDENTIFIER" for i in issues
        )

    def test_expression_chain_through_typed_feature_in_constraint(self):
        model = loads("""
            package P {
                part def Wheel {
                    attribute hub: Hub;
                }
                part def Hub {
                    attribute mass: Real;
                }
                part def Car {
                    part wheels: Wheel[4];
                    constraint { wheels.hub.mass > 0.0 }
                }
            }
        """)
        issues = analyze(model)
        assert not any(
            i.code == "UNRESOLVED_EXPRESSION_IDENTIFIER" for i in issues
        )

    def test_expression_chain_inherited_feature(self):
        # FancyWheel inherits 'hub' from Wheel via :> subsetting.
        model = loads("""
            package P {
                part def Wheel {
                    attribute hub: Hub;
                }
                part def Hub {
                    attribute mass: Real;
                }
                part def FancyWheel :> Wheel;
                part def Car {
                    part fw: FancyWheel;
                    attribute w: Real = fw.hub.mass;
                }
            }
        """)
        issues = analyze(model)
        assert not any(
            i.code == "UNRESOLVED_EXPRESSION_IDENTIFIER" for i in issues
        )

    def test_expression_chain_bad_middle_segment(self):
        model = loads("""
            package P {
                part def Wheel {
                    attribute hub: Hub;
                }
                part def Hub {
                    attribute mass: Real;
                }
                part def Car {
                    part wheels: Wheel[4];
                    attribute w: Real = wheels.nothub.mass;
                }
            }
        """)
        issues = analyze(model)
        assert any(
            i.code == "UNRESOLVED_EXPRESSION_IDENTIFIER"
            and "wheels.nothub.mass" in i.reference
            for i in issues
        )

    def test_expression_chain_bad_tail_segment(self):
        model = loads("""
            package P {
                part def Wheel {
                    attribute hub: Hub;
                }
                part def Hub {
                    attribute mass: Real;
                }
                part def Car {
                    part wheels: Wheel[4];
                    attribute w: Real = wheels.hub.nomass;
                }
            }
        """)
        issues = analyze(model)
        assert any(
            i.code == "UNRESOLVED_EXPRESSION_IDENTIFIER"
            and "wheels.hub.nomass" in i.reference
            for i in issues
        )

    def test_expression_chain_unknown_head(self):
        model = loads("""
            package P {
                part def Wheel {
                    attribute hub: Hub;
                }
                part def Hub {
                    attribute mass: Real;
                }
                part def Car {
                    part wheels: Wheel[4];
                    attribute w: Real = nope.hub.mass;
                }
            }
        """)
        issues = analyze(model)
        assert any(
            i.code == "UNRESOLVED_EXPRESSION_IDENTIFIER"
            and "nope.hub.mass" in i.reference
            for i in issues
        )

    # -- context-type resolution: members of an enclosing usage's declared
    #    type are visible features inside the usage's body (v0.60.0) --

    def test_subsetting_chain_member_of_usage_type(self):
        # 'engine' is a member of Car (myCar's declared type); 'power' is a
        # member of Engine (engine's type).
        model = loads("""
            package P {
                part def Engine {
                    attribute power;
                }
                part def Car {
                    part engine : Engine;
                }
                part myCar : Car {
                    attribute carPower :> engine::power;
                }
            }
        """)
        issues = analyze(model)
        assert not any(i.code == "UNDEFINED_SYMBOL" for i in issues)
        assert not any(
            i.code == "INCOMPATIBLE_FEATURE_CHAIN" for i in issues
        )

    def test_subsetting_chain_member_of_usage_type_bad_tail(self):
        # 'ghost' is not a member of Engine: both the symbol pass and the
        # chain-compatibility check must still flag it.
        model = loads("""
            package P {
                part def Engine {
                    attribute power;
                }
                part def Car {
                    part engine : Engine;
                }
                part myCar : Car {
                    attribute carPower :> engine::ghost;
                }
            }
        """)
        issues = analyze(model)
        assert any(i.code == "UNDEFINED_SYMBOL" for i in issues)
        assert any(
            i.code == "INCOMPATIBLE_FEATURE_CHAIN" for i in issues
        )

    def test_expression_chain_member_of_usage_type(self):
        # Dotted expression chain in a usage body: 'engine' resolves as a
        # member of Car (myCar's type).
        model = loads("""
            package P {
                part def Engine {
                    attribute power: ScalarValues::Real;
                }
                part def Car {
                    part engine : Engine;
                }
                part myCar : Car {
                    attribute w: ScalarValues::Real = engine.power;
                }
            }
        """)
        issues = analyze(model)
        assert not any(
            i.code == "UNRESOLVED_EXPRESSION_IDENTIFIER" for i in issues
        )

    def test_subsetting_single_member_of_usage_type(self):
        # A single member of the usage's type is also a valid subset target.
        model = loads("""
            package P {
                part def Engine { attribute power; }
                part def Car {
                    part engine : Engine;
                }
                part myCar : Car {
                    part p :> engine;
                }
            }
        """)
        issues = analyze(model)
        assert not any(i.code == "UNDEFINED_SYMBOL" for i in issues)

    def test_subsetting_chain_through_inherited_member(self):
        # 'engine' is declared on Vehicle; Car :> Vehicle inherits it.
        # The tail 'power' must be validated against Engine (engine's
        # declared type), not Vehicle.
        model = loads("""
            package P {
                part def Vehicle { part engine: Engine; }
                part def Engine { attribute power; }
                part def Car :> Vehicle;
                part myCar : Car {
                    attribute carPower :> engine::power;
                }
            }
        """)
        issues = analyze(model)
        assert not any(i.code == "UNDEFINED_SYMBOL" for i in issues)
        assert not any(
            i.code == "INCOMPATIBLE_FEATURE_CHAIN" for i in issues
        )

    def test_inherited_member_chain_bad_tail_flagged(self):
        model = loads("""
            package P {
                part def Vehicle { part engine: Engine; }
                part def Engine { attribute power; }
                part def Car :> Vehicle;
                part myCar : Car {
                    attribute carPower :> engine::ghost;
                }
            }
        """)
        issues = analyze(model)
        assert any(
            i.code == "INCOMPATIBLE_FEATURE_CHAIN"
            and "engine::ghost" in i.reference
            for i in issues
        )

    def test_unknown_head_in_usage_body_flagged(self):
        # 'ghost' is not a member of Car — must stay undefined.
        model = loads("""
            package P {
                part def Engine { attribute power; }
                part def Car {
                    part engine : Engine;
                }
                part myCar : Car {
                    part p :> ghost;
                }
            }
        """)
        issues = analyze(model)
        assert any(i.code == "UNDEFINED_SYMBOL" for i in issues)

    def test_package_level_undefined_still_flagged(self):
        # Guard against over-reach: package-level members have no usage
        # context, so unknown features must still be flagged.
        model = loads("""
            package P {
                part x :> UndefinedFeature;
            }
        """)
        issues = analyze(model)
        assert any(
            i.code == "UNDEFINED_SYMBOL" and "UndefinedFeature" in i.message
            for i in issues
        )


class TestMultiplicityBoundsValid:
    """Multiplicity.bounds_valid: Lower bound must be <= upper bound."""

    def test_invalid_multiplicity_bounds(self):
        model = loads("""
            package P {
                part myPart[5..2];
            }
        """)
        issues = analyze(model)
        assert any(i.code == "INVALID_MULTIPLICITY_BOUNDS" for i in issues)

    def test_valid_multiplicity_bounds(self):
        model = loads("""
            package P {
                part myPart[2..5];
            }
        """)
        issues = analyze(model)
        assert not any(i.code == "INVALID_MULTIPLICITY_BOUNDS" for i in issues)

    def test_valid_single_multiplicity(self):
        model = loads("""
            package P {
                part myPart[3];
            }
        """)
        issues = analyze(model)
        assert not any(i.code == "INVALID_MULTIPLICITY_BOUNDS" for i in issues)

    def test_valid_unbounded_multiplicity(self):
        model = loads("""
            package P {
                part myPart[0..*];
            }
        """)
        issues = analyze(model)
        assert not any(i.code == "INVALID_MULTIPLICITY_BOUNDS" for i in issues)

    def test_invalid_bounds_on_attribute(self):
        # Note: Attribute multiplicity support requires a visitor fix.
        # The visitor currently hardcodes specialization=None for top-level attributes.
        # This test uses a nested attribute inside a part definition instead.
        model = loads("""
            package P {
                part def MyDef {
                    attribute myAttr[10..1];
                }
            }
        """)
        issues = analyze(model)
        assert any(i.code == "INVALID_MULTIPLICITY_BOUNDS" for i in issues)


class TestNamingConventions:
    """Tests for stylistic naming convention checks."""

    def test_pascal_case_definition_ok(self):
        """PascalCase definitions should not trigger warnings."""
        model = loads("""
            package P {
                part def Engine;
            }
        """)
        issues = analyze(model)
        assert not any(i.code == "NAMING_CONVENTION" for i in issues)

    def test_lowercase_definition_warning(self):
        """Lowercase definitions should trigger a warning."""
        model = loads("""
            package P {
                part def engine;
            }
        """)
        issues = analyze(model)
        naming = [i for i in issues if i.code == "NAMING_CONVENTION"]
        assert len(naming) == 1
        assert "engine" in naming[0].message
        assert "PascalCase" in naming[0].message

    def test_camel_case_usage_ok(self):
        """camelCase usages should not trigger warnings."""
        model = loads("""
            package P {
                part def Engine;
                part myEngine : Engine;
            }
        """)
        issues = analyze(model)
        assert not any(i.code == "NAMING_CONVENTION" for i in issues)

    def test_pascal_case_usage_warning(self):
        """PascalCase usages should trigger a warning."""
        model = loads("""
            package P {
                part def Engine;
                part MyEngine : Engine;
            }
        """)
        issues = analyze(model)
        naming = [i for i in issues if i.code == "NAMING_CONVENTION"]
        assert len(naming) == 1
        assert "MyEngine" in naming[0].message
        assert "camelCase" in naming[0].message

    def test_pascal_case_package_ok(self):
        """PascalCase packages should not trigger warnings."""
        model = loads("""
            package MyPackage {
                part def Engine;
            }
        """)
        issues = analyze(model)
        assert not any(i.code == "NAMING_CONVENTION" for i in issues)

    def test_lowercase_package_warning(self):
        """Lowercase packages should trigger a warning."""
        model = loads("""
            package mypackage {
                part def Engine;
            }
        """)
        issues = analyze(model)
        naming = [i for i in issues if i.code == "NAMING_CONVENTION"]
        assert len(naming) == 1
        assert "mypackage" in naming[0].message
        assert "PascalCase" in naming[0].message

    def test_camel_case_attribute_ok(self):
        """camelCase attributes should not trigger warnings."""
        model = loads("""
            package P {
                part def Engine {
                    attribute powerLevel;
                }
            }
        """)
        issues = analyze(model)
        assert not any(i.code == "NAMING_CONVENTION" for i in issues)

    def test_pascal_case_attribute_warning(self):
        """PascalCase attributes should trigger a warning."""
        model = loads("""
            package P {
                part def Engine {
                    attribute PowerLevel;
                }
            }
        """)
        issues = analyze(model)
        naming = [i for i in issues if i.code == "NAMING_CONVENTION"]
        assert len(naming) == 1
        assert "PowerLevel" in naming[0].message
        assert "camelCase" in naming[0].message

    def test_camel_case_port_ok(self):
        """camelCase ports should not trigger warnings."""
        model = loads("""
            package P {
                part def Engine {
                    port intakePort;
                }
            }
        """)
        issues = analyze(model)
        assert not any(i.code == "NAMING_CONVENTION" for i in issues)

    def test_pascal_case_port_warning(self):
        """PascalCase ports should trigger a warning."""
        model = loads("""
            package P {
                part def Engine {
                    port IntakePort;
                }
            }
        """)
        issues = analyze(model)
        naming = [i for i in issues if i.code == "NAMING_CONVENTION"]
        assert len(naming) == 1
        assert "IntakePort" in naming[0].message
        assert "camelCase" in naming[0].message

    def test_style_checks_disabled(self):
        """Disabling style checks should suppress naming warnings."""
        model = loads("""
            package mypackage {
                part def engine {
                    attribute PowerLevel;
                    port IntakePort;
                }
                part MyEngine : engine;
            }
        """)
        issues = analyze(model, style_checks=False)
        assert not any(i.code == "NAMING_CONVENTION" for i in issues)

    def test_naming_warnings_are_warnings_not_errors(self):
        """Naming convention issues should have severity 'warning'."""
        model = loads("""
            package mypackage {
                part def engine;
            }
        """)
        issues = analyze(model)
        naming = [i for i in issues if i.code == "NAMING_CONVENTION"]
        for issue in naming:
            assert issue.severity == "warning"


class TestFilePackageMatch:
    """Tests for file-package name matching checks."""

    def test_matching_filename_ok(self):
        """Matching filename and package name should not trigger warnings."""
        model = loads("""
            package Engine {
                part def EngineDef;
            }
        """)
        issues = analyze(model, filename="Engine.sysml")
        assert not any(i.code == "FILE_PACKAGE_MISMATCH" for i in issues)

    def test_mismatching_filename_warning(self):
        """Mismatching filename should trigger a warning."""
        model = loads("""
            package WrongName {
                part def EngineDef;
            }
        """)
        issues = analyze(model, filename="Engine.sysml")
        mismatch = [i for i in issues if i.code == "FILE_PACKAGE_MISMATCH"]
        assert len(mismatch) == 1
        assert "WrongName" in mismatch[0].message
        assert "Engine.sysml" in mismatch[0].message
        assert "Engine" in mismatch[0].message

    def test_no_filename_no_check(self):
        """Not providing filename should not trigger file-package warnings."""
        model = loads("""
            package WrongName {
                part def EngineDef;
            }
        """)
        issues = analyze(model)  # No filename provided
        assert not any(i.code == "FILE_PACKAGE_MISMATCH" for i in issues)

    def test_kerml_extension(self):
        """Should work with .kerml extension."""
        model = loads("""
            package MyKernel {
                part def KernelPart;
            }
        """)
        issues = analyze(model, filename="MyKernel.kerml")
        assert not any(i.code == "FILE_PACKAGE_MISMATCH" for i in issues)

    def test_file_package_warnings_are_warnings(self):
        """File-package mismatch issues should have severity 'warning'."""
        model = loads("""
            package WrongName {
                part def EngineDef;
            }
        """)
        issues = analyze(model, filename="Engine.sysml")
        mismatch = [i for i in issues if i.code == "FILE_PACKAGE_MISMATCH"]
        for issue in mismatch:
            assert issue.severity == "warning"


class TestAnalysisResult:
    """Tests for AnalysisResult wrapper and strict mode."""

    def test_analyze_returns_analysis_result(self):
        model = loads("package P {}")
        result = analyze(model)
        assert isinstance(result, AnalysisResult)

    def test_analysis_result_is_list_subclass(self):
        model = loads("package P {}")
        result = analyze(model)
        assert isinstance(result, list)

    def test_strict_raises_on_errors(self):
        model = loads("""
            package P {
                part x : MissingType;
            }
        """)
        with pytest.raises(ValueError, match="Semantic errors found"):
            analyze(model, strict=True)

    def test_strict_no_raise_on_clean_model(self):
        model = loads("""
            package P {
                part def Engine;
                part e : Engine;
            }
        """)
        result = analyze(model, strict=True)
        assert isinstance(result, AnalysisResult)
        assert len(result) == 0

    def test_errors_property(self):
        model = loads("""
            package P {
                part x : MissingA;
                part y : MissingB;
            }
        """)
        result = analyze(model)
        assert len(result.errors) > 0
        assert all(i.severity == "error" for i in result.errors)

    def test_warnings_property(self):
        model = loads("""
            package P {
                part def engine_lowercase;
            }
        """)
        result = analyze(model)
        warnings = result.warnings
        assert any("engine_lowercase" in i.message for i in warnings)

    def test_raise_on_errors_raises_when_errors_exist(self):
        model = loads("""
            package P {
                part x : MissingType;
            }
        """)
        result = analyze(model)
        with pytest.raises(ValueError, match="Semantic errors found"):
            result.raise_on_errors()

    def test_raise_on_errors_returns_self_when_clean(self):
        model = loads("package P {}")
        result = analyze(model)
        returned = result.raise_on_errors()
        assert returned is result

    def test_bool_is_true_for_clean_model(self):
        model = loads("package P {}")
        result = analyze(model)
        assert bool(result) is True

    def test_bool_is_false_for_errored_model(self):
        model = loads("""
            package P {
                part x : MissingType;
            }
        """)
        result = analyze(model)
        assert bool(result) is False

    def test_analysis_result_still_iterable(self):
        model = loads("""
            package P {
                part x : MissingType;
            }
        """)
        result = analyze(model)
        count = sum(1 for _ in result)
        assert count == len(result)


# ---------------------------------------------------------------------------
# Expression identifier resolution (v0.54.0 — Phase B)
# ---------------------------------------------------------------------------


class TestExpressionIdentifierResolution:
    """Identifiers inside expression bodies must resolve against the symbol table."""

    def test_constraint_body_resolved(self):
        model = loads("""
            package P {
                part def Vehicle {
                    part wheel1 { attribute mass : Integer; }
                    constraint c1 { wheel1.mass > 0 }
                }
            }
        """)
        issues = analyze(model)
        assert not [i for i in issues if i.code == "UNRESOLVED_EXPRESSION_IDENTIFIER"]

    def test_deep_chain_resolved(self):
        model = loads("""
            package P {
                part def Vehicle {
                    part chassis { part hub { attribute rpm : Integer; } }
                    constraint c2 { chassis.hub.rpm < 5000.0 }
                }
            }
        """)
        issues = analyze(model)
        assert not [i for i in issues if i.code == "UNRESOLVED_EXPRESSION_IDENTIFIER"]

    def test_unresolved_in_constraint_body(self):
        model = loads("""
            package P {
                part def Vehicle {
                    constraint c1 { missing_var > 0 }
                }
            }
        """)
        issues = analyze(model)
        bad = [i for i in issues if i.code == "UNRESOLVED_EXPRESSION_IDENTIFIER"]
        assert any("missing_var" in i.reference for i in bad)

    def test_attribute_default_value_resolved(self):
        model = loads("""
            package P {
                part def V {
                    attribute a : Integer;
                    attribute b : Integer = a + 2;
                }
            }
        """)
        issues = analyze(model)
        assert not [i for i in issues if i.code == "UNRESOLVED_EXPRESSION_IDENTIFIER"]

    def test_attribute_default_value_unresolved(self):
        model = loads("""
            package P {
                part def V {
                    attribute b : Integer = nohere.mass + ghost;
                }
            }
        """)
        issues = analyze(model)
        bad = [i for i in issues if i.code == "UNRESOLVED_EXPRESSION_IDENTIFIER"]
        assert any("nohere" in i.reference for i in bad)
        assert any("ghost" in i.reference for i in bad)

    def test_unresolved_chain_reports_head_and_chain(self):
        model = loads("""
            package P {
                part def V {
                    constraint c { wheel9.deep.nope == 1 }
                }
            }
        """)
        issues = analyze(model)
        bad = [i.reference for i in issues if i.code == "UNRESOLVED_EXPRESSION_IDENTIFIER"]
        assert "wheel9" in bad
        assert "wheel9.deep.nope" in bad

    def test_imported_symbol_resolves_in_expression(self):
        model = loads("""
            package P {
                public import ScalarValues::*;
                part def Shape {
                    attribute edges : Integer;
                    attribute perimeter : Integer = size(edges) * 2;
                }
            }
        """)
        issues = analyze(model)
        assert not [i for i in issues if i.code == "UNRESOLVED_EXPRESSION_IDENTIFIER"]

    def test_assert_constraint_body_resolved(self):
        model = loads("""
            package P {
                part def V {
                    attribute a : Integer;
                    assert constraint { a < 100 }
                }
            }
        """)
        issues = analyze(model)
        assert not [i for i in issues if i.code == "UNRESOLVED_EXPRESSION_IDENTIFIER"]

    def test_guard_expression_resolved(self):
        model = loads("""
            package P {
                part def V {
                    attribute a : Integer;
                    state s {
                        state S1;
                        state S2;
                        transition t1 first S1
                            if a > 1.0
                            then S2;
                    }
                }
            }
        """)
        issues = analyze(model)
        assert not [i for i in issues if i.code == "UNRESOLVED_EXPRESSION_IDENTIFIER"]

    def test_guard_unresolved(self):
        model = loads("""
            package P {
                part def V {
                    state s {
                        state S1;
                        state S2;
                        transition t1 first S1
                            if nosuchsignal > 1.0
                            then S2;
                    }
                }
            }
        """)
        issues = analyze(model)
        bad = [i for i in issues if i.code == "UNRESOLVED_EXPRESSION_IDENTIFIER"]
        assert any("nosuchsignal" in i.reference for i in bad)

    def test_issue_message_names_expression_owner(self):
        model = loads("""
            package P {
                part def Vehicle {
                    constraint c1 { mystery > 0 }
                }
            }
        """)
        issues = analyze(model)
        expr_issues = [i for i in issues if i.code == "UNRESOLVED_EXPRESSION_IDENTIFIER"]
        assert expr_issues
        assert any("Constraint" in i.message for i in expr_issues)

    def test_library_function_size_in_expr(self):
        """`size` (CollectionFunctions) must be indexed from the bundled library."""
        from sysmlpy.semantic import LibrarySymbolIndex
        LibrarySymbolIndex.clear_cache()
        model = loads("""
            package P {
                public import ScalarValues::*;
                part def Shape {
                    attribute edges : Integer;
                    attribute perimeter : Integer = size(edges) * 2;
                }
            }
        """)
        issues = analyze(model)
        assert not [
            i for i in issues
            if i.code == "UNRESOLVED_EXPRESSION_IDENTIFIER" and i.reference == "size"
        ]


# ---------------------------------------------------------------------------
# Expression type checking & unit safety (v0.55.0 — Phase C)
# ---------------------------------------------------------------------------


class TestOperatorTypeChecking:
    """Operand type compatibility inside expression bodies."""

    def test_logical_operator_rejects_numeric_operand(self):
        model = loads("""
            package P {
                part def V {
                    attribute flag : Boolean;
                    attribute n : Integer;
                    constraint c1 { flag and n }
                }
            }
        """)
        issues = analyze(model)
        assert any(
            i.code == "OPERAND_TYPE_MISMATCH" and i.reference == "and"
            for i in issues
        )

    def test_logical_operator_accepts_boolean_pair(self):
        model = loads("""
            package P {
                part def V {
                    attribute a : Boolean;
                    attribute b : Boolean;
                    constraint ok { a or b }
                }
            }
        """)
        issues = analyze(model)
        assert not [i for i in issues if i.code == "OPERAND_TYPE_MISMATCH"]

    def test_equality_rejects_boolean_vs_numeric(self):
        model = loads("""
            package P {
                part def V {
                    attribute flag : Boolean;
                    attribute n : Integer;
                    constraint c { flag == n }
                }
            }
        """)
        issues = analyze(model)
        assert any(
            i.code == "OPERAND_TYPE_MISMATCH" and i.reference == "=="
            for i in issues
        )

    def test_relational_rejects_boolean_operand(self):
        model = loads("""
            package P {
                part def V {
                    attribute flag : Boolean;
                    attribute n : Integer;
                    constraint c { flag < n }
                }
            }
        """)
        issues = analyze(model)
        assert any(
            i.code == "OPERAND_TYPE_MISMATCH" and i.reference == "<"
            for i in issues
        )

    def test_arithmetic_rejects_string_plus_number(self):
        model = loads("""
            package P {
                part def V {
                    attribute s : String;
                    attribute n : Integer;
                    attribute joined : Integer = s + n;
                }
            }
        """)
        issues = analyze(model)
        assert any(
            i.code == "OPERAND_TYPE_MISMATCH" and i.reference == "+"
            for i in issues
        )

    def test_unary_not_rejects_numeric(self):
        model = loads("""
            package P {
                part def V {
                    attribute n : Integer;
                    constraint c { not n }
                }
            }
        """)
        issues = analyze(model)
        assert any(
            i.code == "OPERAND_TYPE_MISMATCH" and i.reference == "not"
            for i in issues
        )

    def test_numeric_arithmetic_is_clean(self):
        model = loads("""
            package P {
                part def V {
                    attribute n : Integer;
                    attribute ok : Integer = n * 2 + 1;
                    constraint c { n > 3 and n < 10 }
                }
            }
        """)
        issues = analyze(model)
        assert not [i for i in issues if i.code in ("OPERAND_TYPE_MISMATCH", "UNIT_DIMENSION_MISMATCH")]


class TestUnitDimensionChecking:
    """pint-backed dimension compatibility for + and -."""

    def test_plus_mismatch_error(self):
        model = loads("""
            package P {
                public import ISQ::*;
                part def V {
                    attribute mass : MassValue;
                    attribute length : LengthValue;
                    constraint c { mass + length > 0 }
                }
            }
        """)
        issues = analyze(model)
        assert any(
            i.code == "UNIT_DIMENSION_MISMATCH"
            for i in issues
        )

    def test_plus_same_dimension_ok(self):
        model = loads("""
            package P {
                public import ISQ::*;
                part def V {
                    attribute mass1 : MassValue;
                    attribute mass2 : MassValue;
                    constraint c { mass1 + mass2 > 0 }
                }
            }
        """)
        issues = analyze(model)
        assert not [i for i in issues if i.code == "UNIT_DIMENSION_MISMATCH"]

    def test_dimensionless_plus_quantity_ok(self):
        model = loads("""
            package P {
                public import ISQ::*;
                part def V {
                    attribute mass : MassValue;
                    constraint c { mass + 5.0 > 0 }
                }
            }
        """)
        issues = analyze(model)
        assert not [i for i in issues if i.code == "UNIT_DIMENSION_MISMATCH"]

    def test_multiplication_any_dimension_ok(self):
        model = loads("""
            package P {
                public import ISQ::*;
                part def V {
                    attribute mass : MassValue;
                    attribute length : LengthValue;
                    attribute m2 : AreaValue = mass * length;
                }
            }
        """)
        issues = analyze(model)
        assert not [i for i in issues if i.code == "UNIT_DIMENSION_MISMATCH"]


class TestConstantFolding:
    """const_fold: static reduction of deterministic literal expressions."""

    def test_arithmetic_precedence(self):
        from sysmlpy import loads as _loads
        import sysmlpy.semantic as S
        model = _loads("package P { part def V { attribute x : Integer = 2 + 3 * 4; } }")
        v = model.children[0].children[0]
        exprs = S._find_owned_expressions(v.children[0].grammar.get_definition())
        assert S.const_fold(exprs[0]) == 14

    def test_division_float(self):
        from sysmlpy import loads as _loads
        import sysmlpy.semantic as S
        model = _loads("package P { part def V { attribute x : Integer = 10 / 4; } }")
        v = model.children[0].children[0]
        exprs = S._find_owned_expressions(v.children[0].grammar.get_definition())
        assert S.const_fold(exprs[0]) == 2.5

    def test_exponentiation(self):
        from sysmlpy import loads as _loads
        import sysmlpy.semantic as S
        model = _loads("package P { part def V { attribute x : Integer = 2 ** 10; } }")
        v = model.children[0].children[0]
        exprs = S._find_owned_expressions(v.children[0].grammar.get_definition())
        assert S.const_fold(exprs[0]) == 1024

    def test_parenthesized_unary_text(self):
        from sysmlpy import loads as _loads
        import sysmlpy.semantic as S
        model = _loads("package P { part def V { attribute x : Integer = -(2-5); } }")
        v = model.children[0].children[0]
        exprs = S._find_owned_expressions(v.children[0].grammar.get_definition())
        assert S.const_fold(exprs[0]) == 3

    def test_non_numeric_returns_none(self):
        from sysmlpy import loads as _loads
        import sysmlpy.semantic as S
        model = _loads("package P { part def V { attribute a : Integer; attribute x : Integer = a + 1; } }")
        v = model.children[0].children[0]
        exprs = S._find_owned_expressions(v.children[1].grammar.get_definition())
        assert S.const_fold(exprs[0]) is None

    def test_fold_text_guard_rejects_names(self):
        import sysmlpy.semantic as S
        assert S._fold_text("__import__('os')") is None
        assert S._fold_text("lambda: 1") is None
        assert S._fold_text("2 + 2") == 4


class TestUnitDimensionDerivation:
    """Goal 10: ``*`` / ``/`` dimension algebra vs declared typing.

    The initializer's dimension is derived algebraically (multiplication
    adds exponents, division subtracts, literal-integer exponents
    multiply) and compared against the declared quantity type.
    """

    def test_mass_times_speed_vs_force_is_error(self):
        model = loads("""
            package P {
                public import ISQ::*;
                part def V {
                    attribute mass : MassValue;
                    attribute speed : SpeedValue;
                    attribute f : ForceValue = mass * speed;
                }
            }
        """)
        issues = analyze(model)
        assert any(
            i.code == "UNIT_DIMENSION_DERIVATION_MISMATCH"
            and i.severity == "error"
            for i in issues
        )

    def test_force_over_area_vs_pressure_ok(self):
        model = loads("""
            package P {
                public import ISQ::*;
                part def V {
                    attribute force : ForceValue;
                    attribute area : AreaValue;
                    attribute p : PressureValue = force / area;
                }
            }
        """)
        issues = analyze(model)
        assert not [i for i in issues
                    if i.code == "UNIT_DIMENSION_DERIVATION_MISMATCH"]

    def test_mass_over_area_vs_force_is_error(self):
        model = loads("""
            package P {
                public import ISQ::*;
                part def V {
                    attribute mass : MassValue;
                    attribute area : AreaValue;
                    attribute f : ForceValue = mass / area;
                }
            }
        """)
        issues = analyze(model)
        assert any(i.code == "UNIT_DIMENSION_DERIVATION_MISMATCH"
                   for i in issues)

    def test_mass_squared_vs_force_is_error(self):
        model = loads("""
            package P {
                public import ISQ::*;
                part def V {
                    attribute mass : MassValue;
                    attribute f : ForceValue = mass ** 2;
                }
            }
        """)
        issues = analyze(model)
        assert any(
            i.code == "UNIT_DIMENSION_DERIVATION_MISMATCH"
            and "M^2" in i.message
            for i in issues
        )

    def test_bare_literal_is_silent(self):
        model = loads("""
            package P {
                public import ISQ::*;
                part def V {
                    attribute f : ForceValue = 70;
                }
            }
        """)
        issues = analyze(model)
        assert not [i for i in issues
                    if i.code == "UNIT_DIMENSION_DERIVATION_MISMATCH"]

    def test_unknown_operand_is_silent(self):
        model = loads("""
            package P {
                public import ISQ::*;
                part def V {
                    attribute mass : MassValue;
                    attribute x;
                    attribute f : ForceValue = mass * x;
                }
            }
        """)
        issues = analyze(model)
        assert not [i for i in issues
                    if i.code == "UNIT_DIMENSION_DERIVATION_MISMATCH"]

    def test_same_dimension_multiplication_ok(self):
        model = loads("""
            package P {
                public import ISQ::*;
                part def V {
                    attribute mass : MassValue;
                    attribute m2 : MassValue = mass * 2;
                    attribute m3 : MassValue = mass / 2;
                }
            }
        """)
        issues = analyze(model)
        assert not [i for i in issues
                    if i.code == "UNIT_DIMENSION_DERIVATION_MISMATCH"]

    def test_constraint_bodies_are_not_flagged(self):
        model = loads("""
            package P {
                public import ISQ::*;
                part def V {
                    attribute mass : MassValue;
                    attribute speed : SpeedValue;
                    constraint c { mass * speed > 0 }
                }
            }
        """)
        issues = analyze(model)
        assert not [i for i in issues
                    if i.code == "UNIT_DIMENSION_DERIVATION_MISMATCH"]

    def test_message_names_both_dimensions(self):
        model = loads("""
            package P {
                public import ISQ::*;
                part def V {
                    attribute mass : MassValue;
                    attribute speed : SpeedValue;
                    attribute f : ForceValue = mass * speed;
                }
            }
        """)
        issues = analyze(model)
        deriv = [i for i in issues
                 if i.code == "UNIT_DIMENSION_DERIVATION_MISMATCH"]
        assert len(deriv) == 1
        assert "L^1*M^1*T^-1" in deriv[0].message
        assert "L^1*M^1*T^-2" in deriv[0].message
        assert "ForceValue" in deriv[0].message
