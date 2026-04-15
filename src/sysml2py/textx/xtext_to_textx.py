#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
XText to textX Grammar Converter

Converts the official SysML v2 XText grammar files from the
SysML v2 Pilot Implementation into textX format for use in sysml2py.

Originally created on Wed May 24 16:41:15 2023
@author: christophercox

Updated 2026-04 for SysML v2 Pilot Implementation 2026-03 tag.
@author: jonfox
"""
import re


def xtext_to_textx(rules):
    # Remove grammar declaration
    rules = re.sub(r"grammar .*", "", rules)

    # Remove imports (EMF model imports, not SysML imports)
    rules = re.sub(r'import "http://.*".*', "", rules)
    rules = re.sub(r'import "https://.*".*', "", rules)

    # Remove returns clauses (both SysML:: and Ecore:: types)
    rules = re.sub(r"returns SysML::\S+\s*:", ":", rules)
    rules = re.sub(r"returns Ecore::\S+\s*:", ":", rules)

    # Remove terminal keyword
    rules = re.sub(r"terminal ", "", rules)

    # Remove fragments, enum, annotations
    rules = re.sub(r"fragment", "", rules)
    rules = re.sub(r"enum", "", rules)
    rules = re.sub(r"@Override", "", rules)

    # Protect '=>' keyword strings BEFORE stripping syntactic predicates.
    # In 2026-03, '=>' is used both as an XText syntactic predicate (parser hint)
    # and as a SysML keyword for the 'crosses' relationship.
    # Strategy: temporarily replace the keyword usage, strip predicates, restore.
    rules = re.sub(r"'=> '", "'__CROSSES__'", rules)
    rules = re.sub(r"'=>'", "'__CROSSES__'", rules)

    # Remove XText syntactic predicates (-> and =>)
    # These are parser hints, not part of the grammar syntax.
    rules = re.sub(r"[\s]?=>", "", rules)
    rules = re.sub(r" ->", "", rules)

    # Restore '=>' keyword
    rules = re.sub(r"'__CROSSES__'", "'=>'", rules)

    # Remove SysML empty object instantiations: {SysML::ClassName}
    rules = re.sub(r"\{SysML::[a-zA-Z]*\}", "", rules)
    # Remove SysML action expressions with 'current': {SysML::Type.attr += current}
    rules = re.sub(r"\{SysML::[a-zA-Z\.\+\=\s]*\}", "", rules)

    # Remove SysML cross-references: [SysML::Type | QualifiedName] -> [QualifiedName]
    rules = re.sub(
        r"\[[\s]?SysML::[a-zA-Z]*[\s]?\|[\s]?QualifiedName[\s]?\]",
        "[QualifiedName]",
        rules,
    )
    # Handle ConjugatedPortDefinition special case
    rules = re.sub(
        r"SysML::ConjugatedPortDefinition \| ConjugatedQualifiedName",
        "ConjugatedQualifiedName",
        rules,
    )

    # Fix double QualifiedName references
    rules = re.sub(
        r"\[QualifiedName \| QualifiedName\]", "[QualifiedName]", rules
    )
    rules = re.sub(
        r"\[QualifiedName\|QualifiedName\]", "[QualifiedName]", rules
    )

    # =========================================================================
    # Special case patches for rules that don't translate cleanly to textX
    # =========================================================================

    # MultiplicityExpressionMember - textX can't handle inline alternatives
    # in ownedRelatedElement
    good_str = r"""
MultiplicityRelatedElement :
    (LiteralExpression | FeatureReferenceExpression)
;

MultiplicityExpressionMember :
    ownedRelatedElement += MultiplicityRelatedElement
;"""
    rules = re.sub(r"MultiplicityExpressionMember :[\s\S]*?;", good_str, rules)

    # ActionBodyItem - restructure for textX compatibility
    good_str = r"""
ActionBodyItemTarget :
    ( BehaviorUsageMember | ActionNodeMember )
;

ActionBodyItem :
	  ownedRelationship += Import
	| ownedRelationship += AliasMember
	| ownedRelationship += DefinitionMember
	| ownedRelationship += VariantUsageMember
	| ownedRelationship += NonOccurrenceUsageMember
	| ( ownedRelationship += EmptySuccessionMember )?
	  ownedRelationship += StructureUsageMember
	| ownedRelationship += InitialNodeMember
	  ( ownedRelationship += TargetSuccessionMember )*
	| ( ownedRelationship += EmptySuccessionMember )?
	  ownedRelationship += ActionBodyItemTarget
	  ( ownedRelationship += TargetSuccessionMember )*
	| ownedRelationship += GuardedSuccessionMember
;
"""
    rules = re.sub(r"ActionBodyItem :[\s\S]*?;", good_str, rules)

    # IfNode - extract else clause alternative into helper rule
    good_str = r"""
IfNodeElseMember :
    ( ActionBodyParameterMember | IfNodeParameterMember )
;

IfNode :
	ActionNodePrefix
	'if' ownedRelationship += ExpressionParameterMember
	ownedRelationship += ActionBodyParameterMember
	( 'else' ownedRelationship += IfNodeElseMember )?
;
"""
    rules = re.sub(r"IfNode :[\s\S]*?;", good_str, rules)

    # MultiplicityPart - ordered/nonunique handling
    # In 2026-03, 'nonunique' uses Nonunique value converter pattern:
    #   isUnique = Nonunique instead of isNonunique ?= 'nonunique'
    good_str = r"""
( isOrdered ?= 'ordered' isNonunique ?= 'nonunique'
   | isNonunique2 ?= 'nonunique' isOrdered2 ?= 'ordered'
)
"""
    rules = re.sub(
        r"\( isOrdered[a-zA-Z0-9\?\=\s'\|\(\)]*\)", good_str, rules
    )

    # =========================================================================
    # Empty rules - XText allows empty object instantiation {SysML::Type}
    # but textX requires some content. Replace with placeholder strings.
    # =========================================================================

    empty_rules = [
        "EmptyTargetEnd",
        "PortConjugation",
        "EmptySourceEnd",
        "EmptyUsage",
        "EmptyActionUsage",
        "EmptyFeature",
        "EmptyMultiplicity",
    ]
    for empty_rule in empty_rules:
        rules = re.sub(
            empty_rule + r" :[\s\S]*?;",
            empty_rule
            + " ://This doesn't work.\n\t'"
            + empty_rule.lower()
            + "'\n;",
            rules,
        )

    # =========================================================================
    # Base/terminal rules - replace with textX regex equivalents
    # =========================================================================

    rules = re.sub(
        r"DECIMAL_VALUE[\s]:[\s0-9\(\)'\*\.]*;",
        "DECIMAL_VALUE :\n   /[0-9]*/;",
        rules,
    )
    rules = re.sub(
        r"ID[\s]?:[\sa-zA-Z0-9_'|().*]*;",
        "ID :\n   /[a-zA-Z_][a-zA-Z_0-9]*/;",
        rules,
    )

    # Replace all terminal rules from ID onwards with textX equivalents
    final_rules = """;

ID :
   /[a-zA-Z_][a-zA-Z_0-9]*/;

UNRESTRICTED_NAME :
	/'\\'\\'' (\\'\\\\\\' (\\'b\\' | \\'t\\' | \\'n\\' | \\'f\\' | \\'r\\' | \\'"\\' | "\\'" | \\'\\\\\\') | !(\\'\\\\\\' | \\'\\'\\'\\'))* \\'\\'\\'\\'/;

STRING_VALUE :
	/'\"' (\\'\\\\\\' (\\'b\\' | \\'t\\' | \\'n\\' | \\'f\\' | \\'r\\' | \\'"\\' | "\\'" | \\'\\\\\\') | !(\\'\\\\\\' | \\'"\\'))* '\"'/;

REGULAR_COMMENT:
	'/*''*/';

ML_NOTE:
	/'\\/*'->'*\\/'/;

SL_NOTE:
	/'\\/\\/' (!('\\n' | '\\r') !('\\n' | '\\r')*)? ('\\r'? '\\n')?/;

WS:
	/(' ' | '\\t' | '\\r' | '\\n')+/;
"""
    rules = re.sub(r";[\s]*ID[\s\S]*;", final_rules, rules)
    return rules


if __name__ == "__main__":
    print("Converting SysML.xtext -> SysML.tx")
    with open("SysML.xtext", "r") as f:
        rules = f.read()

    rules = xtext_to_textx(rules)

    with open("SysML.tx", "w") as f:
        f.write("import KerML\nimport KerMLExpressions\n" + rules)

    print("Converting KerML.xtext -> KerML.tx")
    with open("KerML.xtext", "r") as f:
        rules = f.read()

    rules = xtext_to_textx(rules)

    with open("KerML.tx", "w") as f:
        f.write("import KerMLExpressions\n" + rules)

    print("Converting KerMLExpressions.xtext -> KerMLExpressions.tx")
    with open("KerMLExpressions.xtext", "r") as f:
        rules = f.read()

    rules = xtext_to_textx(rules)

    with open("KerMLExpressions.tx", "w") as f:
        f.write(rules)

    print("Done. Copy .tx files to ../grammar/ and run compile_grammar.py")
