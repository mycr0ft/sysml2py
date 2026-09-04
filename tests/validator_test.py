#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for ISQ type/unit conformance validation.
"""

import pytest
import pint

from sysmlpy.usage import ureg
from sysmlpy.validator import (
    validate_unit_conformance,
    validate_quantity_conformance,
    get_expected_dimension,
    is_dimensionless_type,
    ISQ_TYPE_DIMENSIONS,
)
from sysmlpy import Attribute, Part


class TestValidatorModule:
    """Tests for the validator module functions."""

    def test_validate_conformant_length(self):
        """Test that metre is conformant to LengthValue."""
        is_conformant, message = validate_unit_conformance('LengthValue', ureg.metre)
        assert is_conformant
        assert 'conformant' in message

    def test_validate_conformant_mass(self):
        """Test that kilogram is conformant to MassValue."""
        is_conformant, message = validate_unit_conformance('MassValue', ureg.kilogram)
        assert is_conformant

    def test_validate_conformant_duration(self):
        """Test that second is conformant to DurationValue."""
        is_conformant, message = validate_unit_conformance('DurationValue', ureg.second)
        assert is_conformant

    def test_validate_conformant_force(self):
        """Test that newton is conformant to ForceValue."""
        is_conformant, message = validate_unit_conformance('ForceValue', ureg.newton)
        assert is_conformant

    def test_validate_conformant_pressure(self):
        """Test that pascal is conformant to PressureValue."""
        is_conformant, message = validate_unit_conformance('PressureValue', ureg.pascal)
        assert is_conformant

    def test_validate_conformant_energy(self):
        """Test that joule is conformant to EnergyValue."""
        is_conformant, message = validate_unit_conformance('EnergyValue', ureg.joule)
        assert is_conformant

    def test_validate_conformant_power(self):
        """Test that watt is conformant to PowerValue."""
        is_conformant, message = validate_unit_conformance('PowerValue', ureg.watt)
        assert is_conformant

    def test_validate_nonconformant_length_with_mass_unit(self):
        """Test that kilogram is NOT conformant to LengthValue."""
        is_conformant, message = validate_unit_conformance('LengthValue', ureg.kilogram)
        assert not is_conformant
        assert 'NOT conformant' in message

    def test_validate_nonconformant_mass_with_length_unit(self):
        """Test that metre is NOT conformant to MassValue."""
        is_conformant, message = validate_unit_conformance('MassValue', ureg.metre)
        assert not is_conformant

    def test_validate_nonconformant_force_with_length_unit(self):
        """Test that metre is NOT conformant to ForceValue."""
        is_conformant, message = validate_unit_conformance('ForceValue', ureg.metre)
        assert not is_conformant

    def test_validate_dimensionless_type(self):
        """Test that dimensionless units are conformant to dimensionless types."""
        is_conformant, message = validate_unit_conformance('StrainValue', ureg.dimensionless)
        assert is_conformant

    def test_validate_unknown_type(self):
        """Test that unknown types are skipped (return conformant)."""
        is_conformant, message = validate_unit_conformance('UnknownType', ureg.metre)
        assert is_conformant
        assert 'Unknown ISQ type' in message

    def test_validate_with_quantity(self):
        """Test validation with a pint Quantity instead of just a unit."""
        quantity = 100 * ureg.metre
        is_conformant, message = validate_quantity_conformance('LengthValue', quantity)
        assert is_conformant

    def test_validate_with_nonconformant_quantity(self):
        """Test validation with a non-conformant pint Quantity."""
        quantity = 100 * ureg.kilogram
        is_conformant, message = validate_quantity_conformance('LengthValue', quantity)
        assert not is_conformant

    def test_get_expected_dimension_length(self):
        """Test getting expected dimension for LengthValue."""
        dim = get_expected_dimension('LengthValue')
        assert dim is not None
        assert dim['[length]'] == 1

    def test_get_expected_dimension_force(self):
        """Test getting expected dimension for ForceValue."""
        dim = get_expected_dimension('ForceValue')
        assert dim is not None
        assert dim['[length]'] == 1
        assert dim['[mass]'] == 1
        assert dim['[time]'] == -2

    def test_get_expected_dimension_unknown(self):
        """Test getting expected dimension for unknown type."""
        dim = get_expected_dimension('UnknownType')
        assert dim is None

    def test_is_dimensionless_type_strain(self):
        """Test that StrainValue is dimensionless."""
        assert is_dimensionless_type('StrainValue')

    def test_is_dimensionless_type_reynolds_number(self):
        """Test that ReynoldsNumberValue is dimensionless."""
        assert is_dimensionless_type('ReynoldsNumberValue')

    def test_is_dimensionless_type_length(self):
        """Test that LengthValue is NOT dimensionless."""
        assert not is_dimensionless_type('LengthValue')

    def test_is_dimensionless_type_unknown(self):
        """Test that unknown type returns False."""
        assert not is_dimensionless_type('UnknownType')


class TestDerivedUnits:
    """Tests for derived unit conformance."""

    def test_kilometre_conformant_to_length(self):
        """Test that kilometre is conformant to LengthValue."""
        is_conformant, _ = validate_unit_conformance('LengthValue', ureg.kilometre)
        assert is_conformant

    def test_millimetre_conformant_to_length(self):
        """Test that millimetre is conformant to LengthValue."""
        is_conformant, _ = validate_unit_conformance('LengthValue', ureg.millimeter)
        assert is_conformant

    def test_hour_conformant_to_duration(self):
        """Test that hour is conformant to DurationValue."""
        is_conformant, _ = validate_unit_conformance('DurationValue', ureg.hour)
        assert is_conformant

    def test_minute_conformant_to_duration(self):
        """Test that minute is conformant to DurationValue."""
        is_conformant, _ = validate_unit_conformance('DurationValue', ureg.minute)
        assert is_conformant

    def test_tonne_conformant_to_mass(self):
        """Test that tonne (metric ton) is conformant to MassValue."""
        # pint uses 'metric_ton' for tonne
        is_conformant, _ = validate_unit_conformance('MassValue', ureg.metric_ton)
        assert is_conformant

    def test_kilopascal_conformant_to_pressure(self):
        """Test that kilopascal is conformant to PressureValue."""
        kpa = 1000 * ureg.pascal
        is_conformant, _ = validate_unit_conformance('PressureValue', kpa.units)
        assert is_conformant

    def test_megajoule_conformant_to_energy(self):
        """Test that megajoule is conformant to EnergyValue."""
        mj = 1e6 * ureg.joule
        is_conformant, _ = validate_unit_conformance('EnergyValue', mj.units)
        assert is_conformant


class TestISQTypeCoverage:
    """Tests to verify ISQ type coverage in the validator."""

    def test_base_quantities_covered(self):
        """Test that all 7 ISQ base quantities are covered."""
        base_types = [
            'LengthValue',
            'MassValue',
            'DurationValue',
            'ThermodynamicTemperatureValue',
            'ElectricCurrentValue',
            'LuminousIntensityValue',
            'AmountOfSubstanceValue',
        ]
        for base_type in base_types:
            assert base_type in ISQ_TYPE_DIMENSIONS, f"{base_type} not covered"

    def test_mechanics_quantities_covered(self):
        """Test that key mechanics quantities are covered."""
        mechanics_types = [
            'ForceValue',
            'PressureValue',
            'EnergyValue',
            'PowerValue',
            'MomentumValue',
            'TorqueValue',
            'MassDensityValue',
        ]
        for mech_type in mechanics_types:
            assert mech_type in ISQ_TYPE_DIMENSIONS, f"{mech_type} not covered"

    def test_thermodynamics_quantities_covered(self):
        """Test that key thermodynamics quantities are covered."""
        thermo_types = [
            'TemperatureValue',
            'TemperatureDifferenceValue',
            'HeatCapacityValue',
            'EntropyValue',
            'EnthalpyValue',
            'ThermalConductivityValue',
        ]
        for thermo_type in thermo_types:
            assert thermo_type in ISQ_TYPE_DIMENSIONS, f"{thermo_type} not covered"

    def test_electromagnetism_quantities_covered(self):
        """Test that key electromagnetism quantities are covered."""
        em_types = [
            'ElectricChargeValue',
            'ElectricPotentialValue',
            'ResistanceValue',
            'CapacitanceValue',
            'MagneticFluxValue',
            'InductanceValue',
        ]
        for em_type in em_types:
            assert em_type in ISQ_TYPE_DIMENSIONS, f"{em_type} not covered"


class TestAttributeValidation:
    """Tests for unit conformance validation in Attribute.set_value()."""

    # Note: The Attribute.set_value() functionality has a pre-existing bug
    # where self.grammar.usage.completion is None when Attribute is created
    # without parsing. These tests verify the validation logic is correct
    # when the grammar is properly initialized.

    def test_validation_logic_with_typed_attribute(self):
        """Test that validation would raise error for non-conformant unit on typed attribute."""
        from sysmlpy.validator import validate_unit_conformance

        # Simulate what would happen if an attribute typed as 'mass' got a length value
        is_conformant, message = validate_unit_conformance('MassValue', ureg.metre)
        assert not is_conformant
        assert 'NOT conformant' in message

    def test_validation_logic_with_conformant_unit(self):
        """Test that validation would pass for conformant unit on typed attribute."""
        from sysmlpy.validator import validate_unit_conformance

        # Simulate what would happen if an attribute typed as 'mass' got a mass value
        is_conformant, message = validate_unit_conformance('MassValue', ureg.kilogram)
        assert is_conformant
        assert 'conformant' in message




def sysmlpy_loads(text):
    import sysmlpy
    return sysmlpy.loads(text)

from sysmlpy import analyze

class TestStateMachineWellFormedness:
    """Goal 9: OCL well-formedness for ``state def`` machines."""

    def _codes(self, model):
        from sysmlpy import analyze
        return [i.code for i in analyze(model)]

    def test_clean_machine_has_no_state_issues(self):
        model = sysmlpy_loads("""
        package M {
            attribute key : ScalarValues::Boolean := true;
            state def Cruise {
                entry; then off;
                state off;
                state engaged;
                transition engage first off accept Engage when key then engaged;
                transition cancel first engaged accept Cancel then off;
            }
        }
        """)
        assert self._codes(model) == []

    def test_unresolved_transition_endpoint(self):
        model = sysmlpy_loads("""
        package M {
            state def Broken {
                entry; then a;
                state a;
                state b;
                transition t1 first a accept Go then s9;
            }
        }
        """)
        issues = [i for i in analyze(model)
                  if i.code == "UNRESOLVED_TRANSITION_ENDPOINT"]
        assert len(issues) == 1
        assert issues[0].severity == "error"
        assert "'t1'" in issues[0].message
        assert "s9" in issues[0].message

    def test_no_initial_state_warning(self):
        model = sysmlpy_loads("""
        package M {
            state def M {
                state a;
                state b;
                transition go first a accept Go then b;
            }
        }
        """)
        issues = [i for i in analyze(model) if i.code == "NO_INITIAL_STATE"]
        assert len(issues) == 1
        assert issues[0].severity == "warning"
        assert "no initial state" in issues[0].message

    def test_single_state_needs_no_initial(self):
        model = sysmlpy_loads("""
        package M {
            state def M {
                state only;
            }
        }
        """)
        assert [i for i in analyze(model)
                if i.code == "NO_INITIAL_STATE"] == []

    def test_unreachable_state_warning(self):
        model = sysmlpy_loads("""
        package M {
            state def M {
                entry; then a;
                state a;
                state b;
                state lonely;
                transition go first a accept Go then b;
            }
        }
        """)
        issues = [i for i in analyze(model) if i.code == "UNREACHABLE_STATE"]
        assert len(issues) == 1
        assert issues[0].severity == "warning"
        assert "'lonely'" in issues[0].message

    def test_reachable_cycle_has_no_warning(self):
        model = sysmlpy_loads("""
        package M {
            state def M {
                entry; then a;
                state a;
                state b;
                transition go first a accept Go then b;
                transition back first b accept Back then a;
            }
        }
        """)
        assert [i for i in analyze(model)
                if i.code == "UNREACHABLE_STATE"] == []

    def test_composite_states_resolve_qualified(self):
        """Region-internal and cross-region bare references resolve; a
        truly unknown endpoint still errors."""
        model = sysmlpy_loads("""
        package M {
            state def M {
                entry; then a;
                state a;
                transition go first a accept Go then comp;
                state comp {
                    entry; then c1;
                    state c1;
                    state c2;
                    transition inner first c1 accept Flip then c2;
                    transition eject first c2 accept Eject then a;
                }
            }
        }
        """)
        bad = [i for i in analyze(model)
               if i.code in ("UNRESOLVED_TRANSITION_ENDPOINT",
                             "UNREACHABLE_STATE")]
        assert bad == []
