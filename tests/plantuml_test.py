#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for the PlantUML generator module.
"""

import pytest
import sysmlpy
from sysmlpy.plantuml import (
    to_plantuml,
    PlantUMLGenerator,
    _get_typedby_name,
    _get_specializes_names,
    _get_redefines_names,
)


class TestPlantUMLGenerator:
    """Tests for the PlantUML generator."""

    def test_basic_structure(self):
        """Test basic model generates valid PlantUML structure."""
        model = sysmlpy.loads("""
        package P {
            part def Wheel;
            part def Vehicle {
                part frontLeft : Wheel;
            }
        }
        """)
        puml = to_plantuml(model)

        assert "@startuml" in puml
        assert "@enduml" in puml
        assert "Wheel" in puml
        assert "Vehicle" in puml
        assert "frontLeft" in puml

    def test_typing_relationship(self):
        """Test that typing relationships are generated."""
        model = sysmlpy.loads("""
        package P {
            part def Wheel;
            part def Vehicle {
                part frontLeft : Wheel;
            }
        }
        """)
        puml = to_plantuml(model)

        assert "--:|>" in puml  # typing arrow
        assert "types" in puml

    def test_specialization_relationship(self):
        """Test that specialization relationships are generated."""
        model = sysmlpy.loads("""
        package P {
            part def RotatingPart;
            part def Wheel :> RotatingPart;
        }
        """)
        puml = to_plantuml(model)

        assert "--|>" in puml  # specialization arrow
        assert "specializes" in puml

    def test_redefinition_relationship(self):
        """Test that redefinition relationships are generated."""
        model = sysmlpy.loads("""
        package P {
            part def Wheel {
                attribute radius;
            }
            part def CarWheel :> Wheel {
                attribute :>> radius;
            }
        }
        """)
        puml = to_plantuml(model)

        assert "--||>" in puml  # redefinition arrow
        assert "redefines" in puml

    def test_composite_containment(self):
        """Test that composite containment is generated."""
        model = sysmlpy.loads("""
        package P {
            part def Vehicle {
                part engine;
                part wheel;
            }
        }
        """)
        puml = to_plantuml(model)

        assert "*--" in puml  # composite diamond

    def test_bw_style(self):
        """Test B&W style generates monochrome output."""
        model = sysmlpy.loads("""
        package P {
            part def Wheel;
        }
        """)
        puml = to_plantuml(model, style="bw")

        assert "skinparam monochrome true" in puml
        assert "<style>" not in puml  # No CSS block in BW mode

    def test_color_style(self):
        """Test color style generates CSS block."""
        model = sysmlpy.loads("""
        package P {
            part def Wheel;
        }
        """)
        puml = to_plantuml(model, style="color")

        assert "<style>" in puml
        assert "RoundCorner" in puml

    def test_legend_included(self):
        """Test that legend is included by default."""
        model = sysmlpy.loads("""
        package P {
            part def Wheel;
        }
        """)
        puml = to_plantuml(model, include_legend=True)

        assert "legend right" in puml
        assert "endlegend" in puml

    def test_legend_excluded(self):
        """Test that legend can be excluded."""
        model = sysmlpy.loads("""
        package P {
            part def Wheel;
        }
        """)
        puml = to_plantuml(model, include_legend=False)

        assert "legend right" not in puml
        assert "endlegend" not in puml

    def test_direction_lr(self):
        """Test left-to-right direction."""
        model = sysmlpy.loads("""
        package P {
            part def Wheel;
        }
        """)
        puml = to_plantuml(model, direction="LR")

        assert "left to right direction" in puml

    def test_direction_tb(self):
        """Test top-to-bottom direction."""
        model = sysmlpy.loads("""
        package P {
            part def Wheel;
        }
        """)
        puml = to_plantuml(model, direction="TB")

        assert "top to bottom direction" in puml

    def test_stereotype_for_definition(self):
        """Test that definitions get correct stereotype."""
        model = sysmlpy.loads("""
        package P {
            part def Wheel;
        }
        """)
        puml = to_plantuml(model)

        assert "part def" in puml

    def test_stereotype_for_usage(self):
        """Test that usages get correct stereotype."""
        model = sysmlpy.loads("""
        package P {
            part def Wheel;
            part def Vehicle {
                part frontLeft : Wheel;
            }
        }
        """)
        puml = to_plantuml(model)

        # frontLeft is a usage, should have "part" stereotype (not "part def")
        assert "part>>" in puml
        assert "part def>>" in puml  # Wheel and Vehicle are definitions

    def test_stereotype_for_portion_kind(self):
        """Test that individual/timeslice/snapshot prefixes appear in stereotype."""
        model = sysmlpy.loads("""
        package P {
            individual part p1;
            part p2;
            individual part p3 : P3 {
                timeslice ts1;
                snapshot ts2;
            }
        }
        """)
        puml = to_plantuml(model)

        assert "<<individual part>>" in puml
        assert "<<part>>" in puml
        assert "<<timeslice part>>" in puml
        assert "<<snapshot part>>" in puml

    def test_multiple_relationships(self):
        """Test complex model with multiple relationship types."""
        model = sysmlpy.loads("""
        package Vehicle {
            part def RotatingPart;
            part def Wheel :> RotatingPart {
                attribute radius;
            }
            part def CarWheel :> Wheel {
                attribute :>> radius;
            }
            part def Vehicle {
                part frontLeft : CarWheel;
                part frontRight : CarWheel;
            }
        }
        """)
        puml = to_plantuml(model)

        # Check all relationship types present
        assert "--:|>" in puml  # typing
        assert "--|>" in puml   # specialization
        assert "--||>" in puml  # redefinition
        assert "*--" in puml    # composite containment

    def test_empty_model(self):
        """Test empty package generates valid PlantUML."""
        model = sysmlpy.loads("""
        package P {
        }
        """)
        puml = to_plantuml(model)

        assert "@startuml" in puml
        assert "@enduml" in puml


class TestHelperFunctions:
    """Tests for helper functions that extract relationships from grammar."""

    def test_get_typedby_name(self):
        """Test extracting typed-by name from grammar."""
        model = sysmlpy.loads("""
        package P {
            part def Wheel;
            part def Vehicle {
                part frontLeft : Wheel;
            }
        }
        """)
        frontLeft = model.find('frontLeft')[0]
        name = _get_typedby_name(frontLeft)
        assert name == 'Wheel'

    def test_get_typedby_name_no_typing(self):
        """Test extracting typed-by name when no typing exists."""
        model = sysmlpy.loads("""
        package P {
            part def Wheel;
        }
        """)
        wheel = model.find('Wheel')[0]
        name = _get_typedby_name(wheel)
        assert name is None

    def test_get_specializes_names(self):
        """Test extracting specialization names from grammar."""
        model = sysmlpy.loads("""
        package P {
            part def RotatingPart;
            part def Wheel :> RotatingPart;
        }
        """)
        wheel = model.find('Wheel')[0]
        names = _get_specializes_names(wheel)
        assert names == ['RotatingPart']

    def test_get_specializes_names_no_specialization(self):
        """Test extracting specialization names when none exist."""
        model = sysmlpy.loads("""
        package P {
            part def Wheel;
        }
        """)
        wheel = model.find('Wheel')[0]
        names = _get_specializes_names(wheel)
        assert names == []

    def test_get_redefines_names(self):
        """Test extracting redefinition names from grammar."""
        model = sysmlpy.loads("""
        package P {
            part def Wheel {
                attribute radius;
            }
            part def CarWheel :> Wheel {
                attribute :>> radius;
            }
        }
        """)
        carwheel = model.find('CarWheel')[0]
        # Find the anonymous redefining attribute
        for child in carwheel.children:
            names = _get_redefines_names(child)
            if names:
                assert 'radius' in names
                break

    def test_get_redefines_names_no_redefinition(self):
        """Test extracting redefinition names when none exist."""
        model = sysmlpy.loads("""
        package P {
            part def Wheel {
                attribute radius;
            }
        }
        """)
        wheel = model.find('Wheel')[0]
        radius = wheel.children[0]
        names = _get_redefines_names(radius)
        assert names == []


class TestPlantUMLFiltering:
    """Tests for the focus/elements filtering features."""

    def test_focus_element(self):
        """Test focusing on a specific element shows only its subtree."""
        model = sysmlpy.loads("""
        package P {
            part def Vehicle {
                part engine;
                part wheel;
            }
            part def OtherThing {
                part something;
            }
        }
        """)
        vehicle = model.find('Vehicle')[0]
        puml = to_plantuml(model, focus=vehicle)

        assert "Vehicle" in puml
        assert "engine" in puml
        assert "wheel" in puml
        assert "OtherThing" not in puml
        assert "something" not in puml

    def test_focus_with_external_relationships(self):
        """Test that external relationships are shown when show_external=True."""
        model = sysmlpy.loads("""
        package P {
            part def Wheel;
            part def Vehicle {
                part frontLeft : Wheel;
            }
        }
        """)
        vehicle = model.find('Vehicle')[0]
        puml = to_plantuml(model, focus=vehicle, show_external=True)

        # Should include Wheel (external) and the typing relationship
        assert "Wheel" in puml
        assert "--:|>" in puml
        assert "types" in puml

    def test_focus_without_external_relationships(self):
        """Test that external relationships are hidden when show_external=False."""
        model = sysmlpy.loads("""
        package P {
            part def Wheel;
            part def Vehicle {
                part frontLeft : Wheel;
            }
        }
        """)
        vehicle = model.find('Vehicle')[0]
        puml = to_plantuml(model, focus=vehicle, show_external=False, include_legend=False)

        # Should NOT include Wheel or typing relationship
        assert "Wheel" not in puml
        # Check that no typing arrows appear in relationships (not in legend)
        lines = [l for l in puml.split('\n') if not l.strip().startswith('|')]
        rel_lines = [l for l in lines if '--:|>' in l]
        assert len(rel_lines) == 0

    def test_elements_filter(self):
        """Test selecting specific elements."""
        model = sysmlpy.loads("""
        package P {
            part def Wheel;
            part def Axle;
            part def Engine;
        }
        """)
        wheel = model.find('Wheel')[0]
        axle = model.find('Axle')[0]
        puml = to_plantuml(model, elements=[wheel, axle])

        assert "Wheel" in puml
        assert "Axle" in puml
        assert "Engine" not in puml

    def test_elements_filter_shows_relationships(self):
        """Test that relationships between selected elements are shown."""
        model = sysmlpy.loads("""
        package P {
            part def RotatingPart;
            part def Wheel :> RotatingPart;
            part def Engine;
        }
        """)
        wheel = model.find('Wheel')[0]
        rotating = model.find('RotatingPart')[0]
        puml = to_plantuml(model, elements=[wheel, rotating])

        assert "Wheel" in puml
        assert "RotatingPart" in puml
        assert "--|>" in puml  # specialization
        assert "Engine" not in puml

    def test_max_depth(self):
        """Test max_depth limits traversal depth."""
        model = sysmlpy.loads("""
        package P {
            part def Vehicle {
                part engine {
                    part piston;
                }
            }
        }
        """)
        vehicle = model.find('Vehicle')[0]

        # max_depth=1 should only show Vehicle and engine
        puml = to_plantuml(model, focus=vehicle, max_depth=1)
        assert "Vehicle" in puml
        assert "engine" in puml
        assert "piston" not in puml

        # max_depth=2 should show all three
        puml = to_plantuml(model, focus=vehicle, max_depth=2)
        assert "Vehicle" in puml
        assert "engine" in puml
        assert "piston" in puml

    def test_focus_title(self):
        """Test that focus element name appears in title."""
        model = sysmlpy.loads("""
        package P {
            part def Vehicle;
        }
        """)
        vehicle = model.find('Vehicle')[0]
        puml = to_plantuml(model, focus=vehicle)

        assert "Vehicle" in puml.split('title')[1].split('\n')[0]

    def test_elements_title(self):
        """Test that header contains rendering kind and element info."""
        model = sysmlpy.loads("""
        package P {
            part def Wheel;
            part def Axle;
        }
        """)
        wheel = model.find('Wheel')[0]
        axle = model.find('Axle')[0]
        puml = to_plantuml(model, elements=[wheel, axle])

        assert "gv [part def] Wheel" in puml


class TestViewRenderings:
    """Tests for SysML v2 view rendering convenience functions."""

    def test_as_graphical_rendering_basic(self):
        """Graphical rendering produces valid PlantUML."""
        from sysmlpy.plantuml import as_graphical_rendering

        model = sysmlpy.loads("""
        package P {
            part def Engine;
        }
        """)
        puml = as_graphical_rendering(model)

        assert "@startuml" in puml
        assert "@enduml" in puml
        assert "Engine" in puml
        assert "part def" in puml

    def test_as_graphical_rendering_with_focus(self):
        """Graphical rendering with focus shows subtree."""
        from sysmlpy.plantuml import as_graphical_rendering

        model = sysmlpy.loads("""
        package P {
            part def Engine {
                attribute power;
            }
        }
        """)
        engine = model.find('Engine')[0]
        puml = as_graphical_rendering(model, focus=engine)

        assert "Engine" in puml
        assert "power" in puml

    def test_as_tree_diagram_nested_containers(self):
        """Tree diagram uses nested containers for hierarchy."""
        from sysmlpy.plantuml import as_tree_diagram

        model = sysmlpy.loads("""
        package P {
            part def Engine {
                port intake;
                attribute power;
            }
        }
        """)
        puml = as_tree_diagram(model)

        assert "@startuml" in puml
        assert "@enduml" in puml
        # Should have nested structure
        assert "Engine" in puml
        assert "intake" in puml
        assert "power" in puml
        # Check nesting via braces
        assert "{" in puml
        assert "}" in puml

    def test_as_tree_diagram_with_focus(self):
        """Tree diagram with focus shows only subtree."""
        from sysmlpy.plantuml import as_tree_diagram

        model = sysmlpy.loads("""
        package P {
            part def Engine {
                port intake;
            }
            part def Wheel;
        }
        """)
        engine = model.find('Engine')[0]
        puml = as_tree_diagram(model, focus=engine)

        assert "Engine" in puml
        assert "intake" in puml
        # Wheel should not appear when focused on Engine
        assert "Wheel" not in puml

    def test_as_element_table_basic(self):
        """Element table produces tabular output."""
        from sysmlpy.plantuml import as_element_table

        model = sysmlpy.loads("""
        package P {
            part def Engine;
            part myEngine : Engine;
        }
        """)
        puml = as_element_table(model)

        assert "@startuml" in puml
        assert "@enduml" in puml
        assert "Name" in puml and "Type" in puml and "Kind" in puml
        assert "Engine" in puml
        assert "myEngine" in puml
        assert "part def" in puml
        assert "part" in puml

    def test_as_element_table_with_focus(self):
        """Element table with focus shows only subtree elements."""
        from sysmlpy.plantuml import as_element_table

        model = sysmlpy.loads("""
        package P {
            part def Engine {
                attribute power;
                attribute torque;
            }
            part def Wheel;
        }
        """)
        engine = model.find('Engine')[0]
        puml = as_element_table(model, focus=engine)

        assert "Engine" in puml
        assert "power" in puml
        assert "torque" in puml
        # Wheel should not appear
        assert "Wheel" not in puml

    def test_as_textual_notation_basic(self):
        """Textual notation produces indented text in a note."""
        from sysmlpy.plantuml import as_textual_notation

        model = sysmlpy.loads("""
        package P {
            part def Engine {
                port intake;
            }
        }
        """)
        puml = as_textual_notation(model)

        assert "@startuml" in puml
        assert "@enduml" in puml
        assert "note as TextualNotation" in puml
        assert "end note" in puml
        assert "part def Engine" in puml
        assert "port intake" in puml

    def test_as_textual_notation_with_focus(self):
        """Textual notation with focus shows only subtree."""
        from sysmlpy.plantuml import as_textual_notation

        model = sysmlpy.loads("""
        package P {
            part def Engine {
                port intake;
            }
            part def Wheel;
        }
        """)
        engine = model.find('Engine')[0]
        puml = as_textual_notation(model, focus=engine)

        assert "part def Engine" in puml
        assert "port intake" in puml
        assert "Wheel" not in puml

    def test_as_interconnection_diagram_basic(self):
        """Interconnection diagram produces valid PlantUML."""
        from sysmlpy.plantuml import as_interconnection_diagram

        model = sysmlpy.loads("""
        package P {
            part def Engine {
                port intake;
            }
            part myEngine : Engine;
        }
        """)
        puml = as_interconnection_diagram(model)

        assert "@startuml" in puml
        assert "@enduml" in puml
        assert "Interconnection" in puml

    def test_view_renderings_all_start_and_end(self):
        """All view rendering functions produce valid PlantUML delimiters."""
        from sysmlpy.plantuml import (
            as_graphical_rendering,
            as_tree_diagram,
            as_element_table,
            as_textual_notation,
            as_interconnection_diagram,
            as_general_view,
            as_package_view,
        )

        model = sysmlpy.loads("""
        package P {
            part def Engine;
        }
        """)

        for func in [
            as_graphical_rendering,
            as_tree_diagram,
            as_element_table,
            as_textual_notation,
            as_interconnection_diagram,
            as_general_view,
            as_package_view,
        ]:
            puml = func(model)
            assert puml.startswith("@startuml"), f"{func.__name__} missing @startuml"
            assert puml.rstrip().endswith("@enduml"), f"{func.__name__} missing @enduml"


class TestActionFlowView:
    """Tests for the Action Flow View (AFV) rendering."""

    def test_as_action_flow_view_basic(self):
        """Action Flow View produces valid PlantUML structure."""
        from sysmlpy.plantuml import as_action_flow_view

        model = sysmlpy.loads("""
        package P {
            action def A;
            action def B;
        }
        """)
        puml = as_action_flow_view(model)

        assert "@startuml" in puml
        assert "@enduml" in puml
        assert "Action Flow View" in puml
        assert "A" in puml
        assert "B" in puml
        assert "action def" in puml

    def test_as_action_flow_view_with_focus(self):
        """Focus on an action shows only its subtree."""
        from sysmlpy.plantuml import as_action_flow_view

        model = sysmlpy.loads("""
        package P {
            action def A {
                action nested;
            }
            action def OtherAction;
        }
        """)
        action_a = model.find('A')[0]
        puml = as_action_flow_view(model, focus=action_a)

        assert "A" in puml
        assert "nested" in puml
        assert "OtherAction" not in puml

    def test_as_action_flow_view_with_flows(self):
        """Flow connections appear in the diagram."""
        from sysmlpy.plantuml import as_action_flow_view

        model = sysmlpy.loads("""
        package P {
            part def P;
            part def Q;
            action def A { in p : P; out q : Q; }
            action def B { in q : Q; out r : P; }
            action def C {
                action a : A;
                action b : B;
                flow f1 from a.q to b.q;
            }
        }
        """)
        puml = as_action_flow_view(model)

        assert "@startuml" in puml
        assert "action def" in puml
        assert "part def" in puml
        # Flow elements should be present
        assert "f1" in puml or "flow" in puml

    def test_as_action_flow_view_shows_nested_actions(self):
        """Nested actions are rendered."""
        from sysmlpy.plantuml import as_action_flow_view

        model = sysmlpy.loads("""
        package P {
            action def A {
                action a1;
                action a2;
            }
        }
        """)
        puml = as_action_flow_view(model)

        assert "a1" in puml
        assert "a2" in puml
        assert "action def" in puml

    def test_as_action_flow_view_bw_style(self):
        """B&W style produces monochrome output."""
        from sysmlpy.plantuml import as_action_flow_view

        model = sysmlpy.loads("""
        package P {
            action def A;
        }
        """)
        puml = as_action_flow_view(model, style="bw")

        assert "skinparam monochrome true" in puml
        assert "<style>" not in puml

    def test_as_action_flow_view_color_style(self):
        """Color style produces CSS block."""
        from sysmlpy.plantuml import as_action_flow_view

        model = sysmlpy.loads("""
        package P {
            action def A;
        }
        """)
        puml = as_action_flow_view(model, style="color")

        assert "<style>" in puml

    def test_as_action_flow_view_legend(self):
        """Legend is included by default."""
        from sysmlpy.plantuml import as_action_flow_view

        model = sysmlpy.loads("""
        package P {
            action def A;
        }
        """)
        puml = as_action_flow_view(model, include_legend=True)

        assert "Action Flow Legend" in puml or "legend" in puml

    def test_as_action_flow_view_no_legend(self):
        """Legend can be excluded."""
        from sysmlpy.plantuml import as_action_flow_view

        model = sysmlpy.loads("""
        package P {
            action def A;
        }
        """)
        puml = as_action_flow_view(model, include_legend=False)

        assert "legend right" not in puml

    def test_as_action_flow_view_direction_lr(self):
        """Left-to-right direction produces correct output."""
        from sysmlpy.plantuml import as_action_flow_view

        model = sysmlpy.loads("""
        package P {
            action def A;
        }
        """)
        puml = as_action_flow_view(model, direction="LR")

        assert "left to right direction" in puml

    def test_as_action_flow_view_custom_style(self):
        """Custom style lines are appended."""
        from sysmlpy.plantuml import as_action_flow_view

        model = sysmlpy.loads("""
        package P {
            action def A;
        }
        """)
        custom = ["skinparam backgroundColor LightGray"]
        puml = as_action_flow_view(model, custom_style=custom)

        assert "skinparam backgroundColor LightGray" in puml

    def test_as_action_flow_view_auto_include_flows(self):
        """When auto_include_flows is True, flows connected to selected actions are included."""
        from sysmlpy.plantuml import as_action_flow_view

        model = sysmlpy.loads("""
        package P {
            part def X;
            part def Y;
            action def A { out q : X; }
            action def B { in q : X; }
            action def C {
                action a : A;
                action b : B;
                flow f1 from a.q to b.q;
            }
        }
        """)
        action_c = model.find('C')[0]
        puml = as_action_flow_view(model, focus=action_c, auto_include_flows=True)

        assert "C" in puml
        assert "action def" in puml
        # The flow arrow between a and b should be rendered
        assert "E2 --> E3 : flow" in puml

    def test_as_action_flow_view_no_auto_include(self):
        """When auto_include_flows is False, flows are not auto-included."""
        from sysmlpy.plantuml import as_action_flow_view

        model = sysmlpy.loads("""
        package P {
            part def X;
            action def A { out q : X; }
            action def B { in q : X; }
            action def C {
                action a : A;
                action b : B;
                flow f1 from a.q to b.q;
            }
        }
        """)
        action_a = model.find('A')[0]
        puml = as_action_flow_view(model, focus=action_a, auto_include_flows=False)

        assert "A" in puml
        # f1 should not be auto-included since auto_include_flows is False
        # and f1 is not in A's direct subtree
        assert "f1" not in puml


class TestInterconnectionView:
    """Tests for the Interconnection View (IV) rendering."""

    def test_as_interconnection_view_basic(self):
        """Interconnection View produces valid PlantUML structure."""
        from sysmlpy.plantuml import as_interconnection_view

        model = sysmlpy.loads("""
        package P {
            part def Engine;
            port def FuelPort;
            part myEngine : Engine {
                port fuelIn : FuelPort;
            }
        }
        """)
        puml = as_interconnection_view(model)

        assert "@startuml" in puml
        assert "@enduml" in puml
        assert "Interconnection View" in puml
        assert "Engine" in puml
        assert "FuelPort" in puml

    def test_as_interconnection_view_with_focus(self):
        """Focus shows only subtree in interconnection view."""
        from sysmlpy.plantuml import as_interconnection_view

        model = sysmlpy.loads("""
        package P {
            part def Engine {
                port intake;
            }
            part def Wheel;
        }
        """)
        engine = model.find('Engine')[0]
        puml = as_interconnection_view(model, focus=engine)

        assert "Engine" in puml
        assert "intake" in puml
        assert "Wheel" not in puml

    def test_as_interconnection_view_with_elements(self):
        """Element selection works in interconnection view."""
        from sysmlpy.plantuml import as_interconnection_view

        model = sysmlpy.loads("""
        package P {
            part def Engine;
            part def Wheel;
            part def Axle;
        }
        """)
        engine = model.find('Engine')[0]
        wheel = model.find('Wheel')[0]
        puml = as_interconnection_view(model, elements=[engine, wheel])

        assert "Engine" in puml
        assert "Wheel" in puml
        assert "Axle" not in puml

    def test_as_interconnection_view_bw_style(self):
        """B&W style produces monochrome output."""
        from sysmlpy.plantuml import as_interconnection_view

        model = sysmlpy.loads("""
        package P {
            part def Engine;
        }
        """)
        puml = as_interconnection_view(model, style="bw")

        assert "skinparam monochrome true" in puml

    def test_as_interconnection_view_color_style(self):
        """Color style produces CSS block."""
        from sysmlpy.plantuml import as_interconnection_view

        model = sysmlpy.loads("""
        package P {
            part def Engine;
        }
        """)
        puml = as_interconnection_view(model, style="color")

        assert "<style>" in puml

    def test_as_interconnection_view_legend(self):
        """Legend is included by default."""
        from sysmlpy.plantuml import as_interconnection_view

        model = sysmlpy.loads("""
        package P {
            part def Engine;
        }
        """)
        puml = as_interconnection_view(model, include_legend=True)

        assert "Interconnection Legend" in puml

    def test_as_interconnection_view_no_legend(self):
        """Legend can be excluded."""
        from sysmlpy.plantuml import as_interconnection_view

        model = sysmlpy.loads("""
        package P {
            part def Engine;
        }
        """)
        puml = as_interconnection_view(model, include_legend=False)

        assert "legend right" not in puml

    def test_as_interconnection_view_direction(self):
        """Direction parameter works."""
        from sysmlpy.plantuml import as_interconnection_view

        model = sysmlpy.loads("""
        package P {
            part def Engine;
        }
        """)
        puml = as_interconnection_view(model, direction="LR")

        assert "left to right direction" in puml

    def test_as_interconnection_view_custom_style(self):
        """Custom style lines are appended."""
        from sysmlpy.plantuml import as_interconnection_view

        model = sysmlpy.loads("""
        package P {
            part def Engine;
        }
        """)
        custom = ["skinparam backgroundColor LightGray"]
        puml = as_interconnection_view(model, custom_style=custom)

        assert "skinparam backgroundColor LightGray" in puml

    def test_as_interconnection_diagram_legacy_alias(self):
        """The legacy as_interconnection_diagram still works."""
        from sysmlpy.plantuml import as_interconnection_diagram

        model = sysmlpy.loads("""
        package P {
            part def Engine;
        }
        """)
        puml = as_interconnection_diagram(model)

        assert "@startuml" in puml
        assert "@enduml" in puml

    def test_as_interconnection_view_auto_include_connection(self):
        """Auto-include discovers connections between selected features."""
        from sysmlpy.plantuml import as_interconnection_view

        model = sysmlpy.loads("""
        package P {
            part def X;
            part def A {
                port p : X;
                port q : X;
            }
            part def B {
                port r : X;
            }
            part def C {
                part a : A;
                part b : B;
                flow f1 from a.q to b.r;
            }
        }
        """)
        part_c = model.find('C')[0]
        puml = as_interconnection_view(model, focus=part_c,
                                       auto_include_connections=True)

        assert "C" in puml
        # The flow arrow should appear
        assert "flow" in puml

    def test_as_interconnection_view_show_external(self):
        """External relationships are shown with show_external=True."""
        from sysmlpy.plantuml import as_interconnection_view

        model = sysmlpy.loads("""
        package P {
            part def Wheel;
            part def Vehicle {
                part frontLeft : Wheel;
            }
        }
        """)
        vehicle = model.find('Vehicle')[0]
        puml = as_interconnection_view(model, focus=vehicle,
                                       show_external=True)

        assert "Vehicle" in puml
        # Wheel should appear as external reference
        assert "Wheel" in puml


class TestStateTransitionView:
    """Tests for the State Transition View (STV) rendering."""

    def test_as_state_transition_view_basic(self):
        """State Transition View produces valid PlantUML structure."""
        from sysmlpy.plantuml import as_state_transition_view

        model = sysmlpy.loads("""
        package P {
            state def SM {
                state Idle;
                state Active;
                transition t1 first Idle then Active;
            }
        }
        """)
        puml = as_state_transition_view(model)

        assert "@startuml" in puml
        assert "@enduml" in puml
        assert "State Transition View" in puml
        assert "Idle" in puml
        assert "Active" in puml
        assert "SM" in puml
        assert 'state "SM"' in puml or "state" in puml

    def test_as_state_transition_view_transition_arrow(self):
        """Transition arrow appears between states."""
        from sysmlpy.plantuml import as_state_transition_view

        model = sysmlpy.loads("""
        package P {
            state def SM {
                state Idle;
                state Active;
                transition t1 first Idle then Active;
            }
        }
        """)
        puml = as_state_transition_view(model)

        assert "--> : t1" in puml or "t1" in puml

    def test_as_state_transition_view_with_focus(self):
        """Focus on a state shows only its subtree."""
        from sysmlpy.plantuml import as_state_transition_view

        model = sysmlpy.loads("""
        package P {
            state def SM {
                state Idle;
                state Active;
                transition t1 first Idle then Active;
            }
            state def OtherSM {
                state X;
            }
        }
        """)
        sm = model.find('SM')[0]
        puml = as_state_transition_view(model, focus=sm)

        assert "SM" in puml
        assert "Idle" in puml
        assert "Active" in puml
        assert "OtherSM" not in puml
        assert "X" not in puml

    def test_as_state_transition_view_bw_style(self):
        """B&W style produces monochrome output."""
        from sysmlpy.plantuml import as_state_transition_view

        model = sysmlpy.loads("""
        package P {
            state def SM;
        }
        """)
        puml = as_state_transition_view(model, style="bw")

        assert "skinparam monochrome true" in puml

    def test_as_state_transition_view_color_style(self):
        """Color style produces CSS block."""
        from sysmlpy.plantuml import as_state_transition_view

        model = sysmlpy.loads("""
        package P {
            state def SM;
        }
        """)
        puml = as_state_transition_view(model, style="color")

        assert "<style>" in puml

    def test_as_state_transition_view_legend(self):
        """Legend is included by default."""
        from sysmlpy.plantuml import as_state_transition_view

        model = sysmlpy.loads("""
        package P {
            state def SM;
        }
        """)
        puml = as_state_transition_view(model, include_legend=True)

        assert "State Transition Legend" in puml

    def test_as_state_transition_view_no_legend(self):
        """Legend can be excluded."""
        from sysmlpy.plantuml import as_state_transition_view

        model = sysmlpy.loads("""
        package P {
            state def SM;
        }
        """)
        puml = as_state_transition_view(model, include_legend=False)

        assert "legend right" not in puml

    def test_as_state_transition_view_direction(self):
        """Direction parameter works."""
        from sysmlpy.plantuml import as_state_transition_view

        model = sysmlpy.loads("""
        package P {
            state def SM;
        }
        """)
        puml = as_state_transition_view(model, direction="LR")

        assert "left to right direction" in puml

    def test_as_state_transition_view_with_elements(self):
        """Element selection works (exact list)."""
        from sysmlpy.plantuml import as_state_transition_view

        model = sysmlpy.loads("""
        package P {
            state def SM {
                state Idle;
                state Active;
            }
            state def OtherSM {
                state X;
            }
        }
        """)
        sm = model.find('SM')[0]
        idle = model.find('Idle')[0]
        active = model.find('Active')[0]
        puml = as_state_transition_view(model, elements=[sm, idle, active])

        assert "SM" in puml
        assert "Idle" in puml
        assert "Active" in puml
        assert "OtherSM" not in puml
        assert "X" not in puml

    def test_as_state_transition_view_custom_style(self):
        """Custom style lines are appended."""
        from sysmlpy.plantuml import as_state_transition_view

        model = sysmlpy.loads("""
        package P {
            state def SM;
        }
        """)
        custom = ["skinparam backgroundColor LightGray"]
        puml = as_state_transition_view(model, custom_style=custom)

        assert "skinparam backgroundColor LightGray" in puml

    def test_as_state_transition_view_multiple_transitions(self):
        """Multiple transitions between states are rendered."""
        from sysmlpy.plantuml import as_state_transition_view

        model = sysmlpy.loads("""
        package P {
            state def SM {
                state Idle;
                state Active;
                state Error;
                transition t1 first Idle then Active;
                transition t2 first Active then Error;
                transition t3 first Error then Idle;
            }
        }
        """)
        puml = as_state_transition_view(model)

        assert "t1" in puml
        assert "t2" in puml
        assert "t3" in puml


class TestGeneralView:
    """Tests for the General View (GV) rendering."""

    def test_as_general_view_basic(self):
        """General View produces valid PlantUML structure."""
        from sysmlpy.plantuml import as_general_view

        model = sysmlpy.loads("""
        package P {
            part def Engine;
            part def Vehicle {
                part frontLeft : Wheel;
            }
            action def Start;
        }
        """)
        puml = as_general_view(model)

        assert "@startuml" in puml
        assert "@enduml" in puml
        assert "General View" in puml
        assert "Engine" in puml
        assert "Vehicle" in puml
        assert "Start" in puml

    def test_as_general_view_element_types(self):
        """General View renders multiple element types."""
        from sysmlpy.plantuml import as_general_view

        model = sysmlpy.loads("""
        package P {
            part def MyPart;
            item def MyItem;
            attribute def MyAttribute;
            port def MyPort;
            action def MyAction;
            state def MyState;
            constraint def MyConstraint;
            requirement def MyReq;
            connection def MyConn;
            flow def MyFlow;
        }
        """)
        puml = as_general_view(model)

        assert "MyPart" in puml
        assert "MyItem" in puml
        assert "MyAttribute" in puml
        assert "MyPort" in puml
        assert "MyAction" in puml
        assert "MyState" in puml
        assert "MyReq" in puml
        assert "MyConn" in puml
        assert "MyFlow" in puml

    def test_as_general_view_with_focus(self):
        """Focus on an element shows its subtree."""
        from sysmlpy.plantuml import as_general_view

        model = sysmlpy.loads("""
        package P {
            part def Engine {
                attribute power;
                attribute torque;
            }
            part def Wheel;
        }
        """)
        engine = model.find('Engine')[0]
        puml = as_general_view(model, focus=engine)

        assert "Engine" in puml
        assert "power" in puml
        assert "torque" in puml
        assert "Wheel" not in puml

    def test_as_general_view_bw_style(self):
        """B&W style produces monochrome output."""
        from sysmlpy.plantuml import as_general_view

        model = sysmlpy.loads("""
        package P {
            part def Engine;
        }
        """)
        puml = as_general_view(model, style="bw")

        assert "skinparam monochrome true" in puml

    def test_as_general_view_color_style(self):
        """Color style produces CSS block."""
        from sysmlpy.plantuml import as_general_view

        model = sysmlpy.loads("""
        package P {
            part def Engine;
        }
        """)
        puml = as_general_view(model, style="color")

        assert "<style>" in puml

    def test_as_general_view_legend(self):
        """Legend is included by default."""
        from sysmlpy.plantuml import as_general_view

        model = sysmlpy.loads("""
        package P {
            part def Engine;
        }
        """)
        puml = as_general_view(model, include_legend=True)

        assert "General View Legend" in puml

    def test_as_general_view_no_legend(self):
        """Legend can be excluded."""
        from sysmlpy.plantuml import as_general_view

        model = sysmlpy.loads("""
        package P {
            part def Engine;
        }
        """)
        puml = as_general_view(model, include_legend=False)

        assert "legend right" not in puml

    def test_as_general_view_direction(self):
        """Direction parameter works."""
        from sysmlpy.plantuml import as_general_view

        model = sysmlpy.loads("""
        package P {
            part def Engine;
        }
        """)
        puml = as_general_view(model, direction="LR")

        assert "left to right direction" in puml

    def test_as_general_view_with_elements(self):
        """Element selection works."""
        from sysmlpy.plantuml import as_general_view

        model = sysmlpy.loads("""
        package P {
            part def Engine;
            part def Wheel;
        }
        """)
        engine = model.find('Engine')[0]
        puml = as_general_view(model, elements=[engine])

        assert "Engine" in puml
        assert "Wheel" not in puml

    def test_as_general_view_custom_style(self):
        """Custom style lines are appended."""
        from sysmlpy.plantuml import as_general_view

        model = sysmlpy.loads("""
        package P {
            part def Engine;
        }
        """)
        custom = ["skinparam backgroundColor LightGray"]
        puml = as_general_view(model, custom_style=custom)

        assert "skinparam backgroundColor LightGray" in puml


class TestPackageView:
    """Tests for the Package View rendering."""

    def test_as_package_view_basic(self):
        """Package View produces valid PlantUML structure."""
        from sysmlpy.plantuml import as_package_view

        model = sysmlpy.loads("""
        package P {
            part def Engine;
            package Q {
                part def Wheel;
            }
        }
        """)
        puml = as_package_view(model)

        assert "@startuml" in puml
        assert "@enduml" in puml
        assert "Package View" in puml
        assert "P" in puml
        assert "Q" in puml
        assert "Engine" in puml
        assert "Wheel" in puml

    def test_as_package_view_bw_style(self):
        """B&W style produces monochrome output."""
        from sysmlpy.plantuml import as_package_view

        model = sysmlpy.loads("""
        package P {
            part def Engine;
        }
        """)
        puml = as_package_view(model, style="bw")

        assert "skinparam monochrome true" in puml

    def test_as_package_view_color_style(self):
        """Color style produces CSS block."""
        from sysmlpy.plantuml import as_package_view

        model = sysmlpy.loads("""
        package P {
            part def Engine;
        }
        """)
        puml = as_package_view(model, style="color")

        assert "<style>" in puml

    def test_as_package_view_legend(self):
        """Legend is included by default."""
        from sysmlpy.plantuml import as_package_view

        model = sysmlpy.loads("""
        package P {
            part def Engine;
        }
        """)
        puml = as_package_view(model, include_legend=True)

        assert "Package View Legend" in puml

    def test_as_package_view_no_legend(self):
        """Legend can be excluded."""
        from sysmlpy.plantuml import as_package_view

        model = sysmlpy.loads("""
        package P {
            part def Engine;
        }
        """)
        puml = as_package_view(model, include_legend=False)

        assert "legend right" not in puml

    def test_as_package_view_direction(self):
        """Direction parameter works."""
        from sysmlpy.plantuml import as_package_view

        model = sysmlpy.loads("""
        package P {
            part def Engine;
        }
        """)
        puml = as_package_view(model, direction="LR")

        assert "left to right direction" in puml

    def test_as_package_view_custom_style(self):
        """Custom style lines are appended."""
        from sysmlpy.plantuml import as_package_view

        model = sysmlpy.loads("""
        package P {
            part def Engine;
        }
        """)
        custom = ["skinparam backgroundColor LightGray"]
        puml = as_package_view(model, custom_style=custom)

        assert "skinparam backgroundColor LightGray" in puml

    def test_as_package_view_nested_packages(self):
        """Nested packages are rendered as nested rectangles."""
        from sysmlpy.plantuml import as_package_view

        model = sysmlpy.loads("""
        package P {
            part def Engine;
            package Q {
                part def Wheel;
                package R {
                    part def Tire;
                }
            }
        }
        """)
        puml = as_package_view(model)

        assert "P" in puml
        assert "Q" in puml
        assert "R" in puml
        assert "{" in puml
        assert "}" in puml


class TestTabularView:
    """Tests for the Tabular View (GridView specialization)."""

    def test_as_tabular_view_plantuml(self):
        """Tabular View produces valid PlantUML table."""
        from sysmlpy.plantuml import as_tabular_view

        model = sysmlpy.loads("""
        package P {
            part def Engine;
            part def Wheel;
        }
        """)
        puml = as_tabular_view(model, output_format="plantuml")

        assert "@startuml" in puml
        assert "@enduml" in puml
        assert "Tabular View" in puml
        assert "Engine" in puml
        assert "Wheel" in puml
        assert "Name" in puml
        assert "Type" in puml
        assert "Kind" in puml
        assert "Parent" in puml

    def test_as_tabular_view_markdown(self):
        """Tabular View produces markdown table."""
        from sysmlpy.plantuml import as_tabular_view

        model = sysmlpy.loads("""
        package P {
            part def Engine;
        }
        """)
        md = as_tabular_view(model, output_format="markdown")

        assert "| Name " in md
        assert "| Engine " in md
        assert "| part def " in md
        assert "| :--- " in md

    def test_as_tabular_view_html(self):
        """Tabular View produces HTML table."""
        from sysmlpy.plantuml import as_tabular_view

        model = sysmlpy.loads("""
        package P {
            part def Engine;
        }
        """)
        html = as_tabular_view(model, output_format="html")

        assert "<table" in html
        assert "</table>" in html
        assert "<th>Name</th>" in html
        assert "<td>Engine</td>" in html
        assert "<td>part def</td>" in html

    def test_as_tabular_view_custom_columns(self):
        """Tabular View supports custom column selection."""
        from sysmlpy.plantuml import as_tabular_view

        model = sysmlpy.loads("""
        package P {
            part def Engine;
        }
        """)
        md = as_tabular_view(model, columns=["Name", "Type"], output_format="markdown")

        assert "| Name " in md
        assert "| Type " in md
        assert "| Kind " not in md
        assert "| Engine " in md

    def test_as_tabular_view_with_focus(self):
        """Tabular View with focus shows only subtree."""
        from sysmlpy.plantuml import as_tabular_view

        model = sysmlpy.loads("""
        package P {
            part def Engine {
                attribute power;
            }
            part def Wheel;
        }
        """)
        engine = model.find('Engine')[0]
        md = as_tabular_view(model, focus=engine, output_format="markdown")

        assert "Engine" in md
        assert "power" in md
        assert "Wheel" not in md


class TestDataValueTabularView:
    """Tests for the Data Value Tabular View (GridView specialization)."""

    def test_as_data_value_tabular_view_plantuml(self):
        """Data Value View produces valid PlantUML table."""
        from sysmlpy.plantuml import as_data_value_tabular_view

        model = sysmlpy.loads("""
        package P {
            part def Engine {
                attribute power;
                attribute torque;
            }
        }
        """)
        puml = as_data_value_tabular_view(model, output_format="plantuml")

        assert "@startuml" in puml
        assert "@enduml" in puml
        assert "Data Value" in puml
        assert "Attribute" in puml
        assert "Value" in puml
        assert "Unit" in puml

    def test_as_data_value_tabular_view_markdown(self):
        """Data Value View produces markdown table."""
        from sysmlpy.plantuml import as_data_value_tabular_view

        model = sysmlpy.loads("""
        package P {
            part def Engine {
                attribute power;
                attribute torque;
            }
        }
        """)
        md = as_data_value_tabular_view(model, output_format="markdown")

        assert "| Element " in md
        assert "| Attribute " in md
        assert "| Value " in md
        assert "| Unit " in md
        assert "power" in md
        assert "torque" in md
        assert "Engine" in md

    def test_as_data_value_tabular_view_html(self):
        """Data Value View produces HTML table."""
        from sysmlpy.plantuml import as_data_value_tabular_view

        model = sysmlpy.loads("""
        package P {
            part def Engine {
                attribute power;
            }
        }
        """)
        html = as_data_value_tabular_view(model, output_format="html")

        assert "<table" in html
        assert "</table>" in html
        assert "<th>Value</th>" in html

    def test_as_data_value_tabular_view_only_attributes(self):
        """Data Value View only shows attribute elements."""
        from sysmlpy.plantuml import as_data_value_tabular_view

        model = sysmlpy.loads("""
        package P {
            part def Engine {
                attribute power;
            }
            part def Wheel;
        }
        """)
        md = as_data_value_tabular_view(model, output_format="markdown")

        assert "power" in md
        assert "Wheel" not in md
        assert "Engine" in md

    def test_as_data_value_tabular_view_with_focus(self):
        """Data Value View with focus works."""
        from sysmlpy.plantuml import as_data_value_tabular_view

        model = sysmlpy.loads("""
        package P {
            part def Engine {
                attribute power;
                attribute torque;
            }
            part def Wheel {
                attribute diameter;
            }
        }
        """)
        engine = model.find('Engine')[0]
        md = as_data_value_tabular_view(model, focus=engine, output_format="markdown")

        assert "power" in md
        assert "torque" in md
        assert "diameter" not in md


class TestRelationshipMatrixView:
    """Tests for the Relationship Matrix View (GridView specialization)."""

    def test_as_relationship_matrix_view_plantuml(self):
        """Relationship Matrix View produces valid PlantUML salt matrix."""
        from sysmlpy.plantuml import as_relationship_matrix_view

        model = sysmlpy.loads("""
        package P {
            part def Engine;
            part def Wheel;
        }
        """)
        puml = as_relationship_matrix_view(model, output_format="plantuml")

        assert "@startuml" in puml
        assert "@enduml" in puml
        assert "Relationship Matrix" in puml
        assert "Engine" in puml
        assert "Wheel" in puml

    def test_as_relationship_matrix_view_markdown(self):
        """Relationship Matrix View produces markdown table."""
        from sysmlpy.plantuml import as_relationship_matrix_view

        model = sysmlpy.loads("""
        package P {
            part def Engine {
                attribute power;
            }
            part def Wheel;
        }
        """)
        md = as_relationship_matrix_view(model, output_format="markdown")

        assert "| Engine " in md
        assert "| Wheel " in md
        assert "| power " in md

    def test_as_relationship_matrix_view_html(self):
        """Relationship Matrix View produces HTML table."""
        from sysmlpy.plantuml import as_relationship_matrix_view

        model = sysmlpy.loads("""
        package P {
            part def Engine {
                attribute power;
            }
            part def Wheel;
        }
        """)
        html = as_relationship_matrix_view(model, output_format="html")

        assert "<table" in html
        assert "</table>" in html
        assert "relationship-matrix-view" in html

    def test_as_relationship_matrix_view_row_type_filter(self):
        """Row type filter limits row elements."""
        from sysmlpy.plantuml import as_relationship_matrix_view

        model = sysmlpy.loads("""
        package P {
            part def Engine;
            action def Start;
        }
        """)
        md = as_relationship_matrix_view(model, row_type="part", output_format="markdown")

        assert "Engine" in md
        assert "Start" not in md

    def test_as_relationship_matrix_view_shows_containment(self):
        """Relationship Matrix shows composite containment."""
        from sysmlpy.plantuml import as_relationship_matrix_view

        model = sysmlpy.loads("""
        package P {
            part def Engine {
                attribute power;
            }
        }
        """)
        md = as_relationship_matrix_view(model, output_format="markdown")

        # Engine contains power (composite = C)
        assert "C" in md

    def test_as_relationship_matrix_view_with_focus(self):
        """Relationship Matrix with focus works."""
        from sysmlpy.plantuml import as_relationship_matrix_view

        model = sysmlpy.loads("""
        package P {
            part def Engine {
                attribute power;
            }
        }
        """)
        engine = model.find('Engine')[0]
        md = as_relationship_matrix_view(model, focus=engine, output_format="markdown")

        assert "Engine" in md
        assert "power" in md
        assert "Wheel" not in md

class TestSequenceView:
    """Tests for as_sequence_view."""

    def test_as_sequence_view_basic(self):
        """Sequence View produces basic PlantUML output."""
        from sysmlpy.plantuml import as_sequence_view

        model = sysmlpy.loads("""
        package P {
            part def Engine;
            part def Wheel;
        }
        """)
        puml = as_sequence_view(model)

        assert "@startuml" in puml
        assert "@enduml" in puml
        assert "Sequence View" in puml
        assert "participant" in puml

    def test_as_sequence_view_title_with_focus(self):
        """Sequence View title includes focus name."""
        from sysmlpy.plantuml import as_sequence_view

        model = sysmlpy.loads("""
        package P { action def MyAction; }
        """)
        focus = model.find('MyAction')[0]
        puml = as_sequence_view(model, focus=focus)

        assert "sv [action def] MyAction [Sequence View]" in puml

    def test_as_sequence_view_custom_style(self):
        """Sequence View accepts custom style."""
        from sysmlpy.plantuml import as_sequence_view

        model = sysmlpy.loads("""
        package P { part def A; part def B; }
        """)
        custom = ["skinparam monochrome false"]
        puml = as_sequence_view(model, custom_style=custom)

        assert "skinparam monochrome false" in puml


class TestCaseView:
    """Tests for as_case_view."""

    def test_as_case_view_basic(self):
        """Case View produces basic PlantUML output."""
        from sysmlpy.plantuml import as_case_view

        model = sysmlpy.loads("""
        package P {
            part def Driver;
            action def StartEngine;
        }
        """)
        puml = as_case_view(model)

        assert "@startuml" in puml
        assert "@enduml" in puml
        assert "Case View" in puml

    def test_as_case_view_title_with_focus(self):
        """Case View title includes focus name."""
        from sysmlpy.plantuml import as_case_view

        model = sysmlpy.loads("""
        package P { action def MyCase; }
        """)
        focus = model.find('MyCase')[0]
        puml = as_case_view(model, focus=focus)

        assert "gv [action def] MyCase [Case View]" in puml

    def test_as_case_view_custom_style(self):
        """Case View accepts custom style."""
        from sysmlpy.plantuml import as_case_view

        model = sysmlpy.loads("""
        package P { part def Ext; action def DoSomething; }
        """)
        custom = ["skinparam monochrome false"]
        puml = as_case_view(model, custom_style=custom)

        assert "skinparam monochrome false" in puml


class TestBrowserView:
    """Tests for as_browser_view."""

    def test_as_browser_view_basic(self):
        """Browser View produces basic PlantUML WBS output."""
        from sysmlpy.plantuml import as_browser_view

        model = sysmlpy.loads("""
        package P {
            part def Wheel;
            part def Vehicle {
                part frontLeft : Wheel;
            }
        }
        """)
        puml = as_browser_view(model)

        assert "@startwbs" in puml
        assert "@endwbs" in puml
        assert "Browser View" in puml
        assert "«package»" in puml or "<<package>>" in puml
        assert "Wheel" in puml
        assert "Vehicle" in puml
        assert "frontLeft" in puml

    def test_as_browser_view_hierarchy(self):
        """Browser View preserves tree structure."""
        from sysmlpy.plantuml import as_browser_view

        model = sysmlpy.loads("""
        package Outer {
            package Inner {
                part def Widget;
            }
        }
        """)
        puml = as_browser_view(model)

        # Check hierarchy markers — deeper nesting = more asterisks
        lines = [l for l in puml.splitlines() if l.strip().startswith(('*', ' ', 'skinparam', '@', 'title'))]
        # Find the WBS items (asterisk lines)
        wbs_lines = [l for l in lines if l.startswith('*')]
        assert len(wbs_lines) >= 3  # root + Outer + Inner + Widget

        # Outer and Inner should both be present
        assert "Outer" in puml
        assert "Inner" in puml
        assert "Widget" in puml

    def test_as_browser_view_focus(self):
        """Browser View with focus shows only focused element subtree."""
        from sysmlpy.plantuml import as_browser_view

        model = sysmlpy.loads("""
        package P {
            part def FocusPart;
            part def OtherPart;
        }
        """)
        focus = model.find('FocusPart')[0]
        puml = as_browser_view(model, focus=focus)

        assert "FocusPart" in puml
        assert "OtherPart" not in puml

    def test_as_browser_view_style_color(self):
        """Browser View supports color style."""
        from sysmlpy.plantuml import as_browser_view

        model = sysmlpy.loads("""
        package P { part def A; }
        """)
        puml = as_browser_view(model, style="color")

        assert "@startwbs" in puml
        # Color mode should not have monochrome
        assert "monochrome true" not in puml

    def test_as_browser_view_custom_style(self):
        """Browser View accepts custom style."""
        from sysmlpy.plantuml import as_browser_view

        model = sysmlpy.loads("""
        package P { part def A; }
        """)
        custom = ["skinparam BackgroundColor #FFFF00"]
        puml = as_browser_view(model, custom_style=custom)

        assert "skinparam BackgroundColor #FFFF00" in puml

    def test_as_browser_view_empty_model(self):
        """Browser View handles minimal model gracefully."""
        from sysmlpy.plantuml import as_browser_view

        model = sysmlpy.loads("package Empty {}")
        puml = as_browser_view(model)

        assert "@startwbs" in puml
        assert "@endwbs" in puml
        assert "Empty" in puml

    def test_as_browser_view_with_elements(self):
        """Browser View with specific elements list."""
        from sysmlpy.plantuml import as_browser_view

        model = sysmlpy.loads("""
        package P {
            part def A;
            part def B;
        }
        """)
        a = model.find('A')[0]
        b = model.find('B')[0]
        puml = as_browser_view(model, elements=[a, b])

        assert "A" in puml
        assert "B" in puml
        assert "bv [part def] A [Browser View]" in puml
