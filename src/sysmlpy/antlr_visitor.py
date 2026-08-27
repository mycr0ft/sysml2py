#!/usr/bin/env python3
"""
ANTLR4 to dictionary converter for SysML v2.0.

This module converts the ANTLR4 parse tree to a dictionary format
for use with the sysmlpy class hierarchy.
"""
import uuid


def _extract_name_shortname(name_text):
    """Given a name text, return (name, shortname) tuple.
    
    This function is only called for single-name identifications without
    angle brackets. In that case the name is always a declaredName.
    Short names require explicit < > in source, handled at call sites.
    """
    return name_text, None


def _extract_name_from_ident(ident):
    """Extract (name, shortname) from an Identification context.
    
    Parameters
    ----------
    ident : antlr4 ParserRuleContext
        Identification context from ANTLR parser.
    
    Returns
    -------
    tuple
        (name, shortname) tuple. Returns (None, None) if no name found.
    
    Handles:
    - `name` → (name, None)
    - `<shortname> name` → (name, shortname)
    - `qualifiedName` → (qualifiedName, None)
    """
    name = None
    shortname = None
    if ident is None:
        return name, shortname
    
    if hasattr(ident, 'qualifiedIdentification') and ident.qualifiedIdentification():
        qn = ident.qualifiedIdentification()
        if hasattr(qn, 'name') and qn.name():
            names = qn.name()
            if isinstance(names, list):
                name = "::".join([n.getText() for n in names])
            else:
                name = names.getText()
        return name, shortname
    
    if hasattr(ident, 'name'):
        name_list = ident.name()
        if name_list and isinstance(name_list, list):
            if len(name_list) == 2:
                shortname = name_list[0].getText()
                name = name_list[1].getText()
            elif len(name_list) == 1:
                name_text = name_list[0].getText()
                if hasattr(ident, 'LT') and ident.LT() is not None:
                    shortname = name_text
                else:
                    name = name_text
    
    return name, shortname


def _get_usage_identification(ctx):
    """Extract (name, shortname) from a usage context by navigating to usageDeclaration().identification().
    
    The ctx can be either a usage context (with usageDeclaration) or an occurrence usage element context (with usage() method).
    Returns (name, shortname) tuple.
    """
    name = None
    shortname = None
    if ctx is None:
        return name, shortname
    
    # Try to get usageDeclaration directly from ctx (if ctx is a usage context)
    usage_decl = None
    if hasattr(ctx, 'usageDeclaration') and ctx.usageDeclaration():
        usage_decl = ctx.usageDeclaration()
    elif hasattr(ctx, 'usage') and ctx.usage():
        usage = ctx.usage()
        if hasattr(usage, 'usageDeclaration') and usage.usageDeclaration():
            usage_decl = usage.usageDeclaration()
    
    if usage_decl and hasattr(usage_decl, 'identification') and usage_decl.identification():
        ident = usage_decl.identification()
        name, shortname = _extract_name_from_ident(ident)
    
    return name, shortname


def _get_subclassification_part(ctx):
    """Extract SubclassificationPart dict from a definition context.
    
    Handles 'part def Foo :> Bar, Baz' — returns the :> clause as a dict,
    or None if there is no subclassification.
    
    Handles both regular definitions (via definition().definitionDeclaration()) 
    and enumeration definitions (via definitionDeclaration() directly).
    """
    defn = None
    dd = None
    
    # Try direct definitionDeclaration first (for enumeration definitions, etc.)
    if hasattr(ctx, 'definitionDeclaration') and ctx.definitionDeclaration():
        dd = ctx.definitionDeclaration()
    # Then try nested definition() for regular definitions
    if dd is None and hasattr(ctx, 'definition') and ctx.definition():
        defn = ctx.definition()
        if hasattr(defn, 'definitionDeclaration') and defn.definitionDeclaration():
            dd = defn.definitionDeclaration()
    
    if dd is None:
        return None
    
    if not (hasattr(dd, 'subclassificationPart') and dd.subclassificationPart()):
        return None
    
    sc = dd.subclassificationPart()
    owned = []
    if hasattr(sc, 'ownedSubclassification'):
        for osc in sc.ownedSubclassification():
            if hasattr(osc, 'qualifiedName') and osc.qualifiedName():
                qn_text = osc.qualifiedName().getText()
                qn_names = qn_text.split("::")
                owned.append({
                    "name": "OwnedSubclassification",
                    "superclassifier": {"name": "QualifiedName", "names": qn_names}
                })
    
    if not owned:
        return None
    
    return {
        "name": "SubclassificationPart",
        "ownedRelationship": owned
    }


def _get_definition_identification(ctx):
    """Extract (name, shortname) from a definition context by navigating definition().definitionDeclaration().identification().
    
    Returns (name, shortname) tuple.
    """
    name = None
    shortname = None
    if ctx is None:
        return name, shortname
    
    # Try different paths to find definitionDeclaration
    defn = None
    if hasattr(ctx, 'definition') and ctx.definition():
        defn = ctx.definition()
    
    dd = None
    if defn and hasattr(defn, 'definitionDeclaration') and defn.definitionDeclaration():
        dd = defn.definitionDeclaration()
    elif hasattr(ctx, 'definitionDeclaration') and ctx.definitionDeclaration():
        dd = ctx.definitionDeclaration()
    
    if dd and hasattr(dd, 'identification') and dd.identification():
        ident = dd.identification()
        name, shortname = _extract_name_from_ident(ident)
    
    return name, shortname


def _build_identification_dict(ident_ctx):
    """Build an identification dictionary from an ANTLR IdentificationContext.
    
    Returns a dict like {"name": "Identification", "declaredName": ..., "declaredShortName": ...}
    or None if there is no identification.
    """
    if ident_ctx is None:
        return None
    
    name = None
    shortname = None
    
    if hasattr(ident_ctx, 'name'):
        name, shortname = _extract_name_from_ident(ident_ctx)
    
    if name is None and shortname is None:
        return None
    
    return {
        "name": "Identification",
        "declaredShortName": shortname,
        "declaredName": name
    }


def _visit_documentation_dict(ctx):
    """Visit a documentation context and return a Documentation dictionary.
    
    Grammar: DOC identification? (LOCALE DOUBLE_STRING)? REGULAR_COMMENT
    """
    body = None
    if ctx.REGULAR_COMMENT():
        body = ctx.REGULAR_COMMENT().getText()
    
    identification = None
    if ctx.identification():
        identification = _build_identification_dict(ctx.identification())
    
    return {
        "name": "Documentation",
        "body": body,
        "identification": identification,
        "ownedRelationship": []
    }


def _visit_comment_dict(ctx):
    """Visit a comment context and return a CommentSysML dictionary.
    
    Grammar: (COMMENT identification? ( ABOUT annotation ( COMMA annotation)*)?)? (LOCALE DOUBLE_STRING)? REGULAR_COMMENT
    """
    body = None
    if ctx.REGULAR_COMMENT():
        body = ctx.REGULAR_COMMENT().getText()
    
    identification = None
    if ctx.identification():
        identification = _build_identification_dict(ctx.identification())
    
    annotations = []
    if ctx.ABOUT():
        for i in range(ctx.getChildCount()):
            ann_ctx = ctx.annotation(i) if i < len(ctx.annotation()) else None
            # annotation(i) returns None for out-of-range; iterate properly
        for ann_idx in range(len(ctx.annotation())):
            ann_ctx = ctx.annotation(ann_idx)
            if ann_ctx and ann_ctx.qualifiedName():
                qn_text = ann_ctx.qualifiedName().getText()
                annotations.append({
                    "name": "Annotation",
                    "annotatedElement": {
                        "name": "QualifiedName",
                        "names": qn_text.split("::")
                    }
                })
    
    return {
        "name": "CommentSysML",
        "body": body,
        "identification": identification,
        "ownedRelationship": annotations
    }


def _visit_textual_representation_dict(ctx):
    """Visit a textualRepresentation context and return a TextualRepresentation dictionary.
    
    Grammar: (REP identification?)? LANGUAGE DOUBLE_STRING REGULAR_COMMENT
    """
    identification = None
    if ctx.identification():
        identification = _build_identification_dict(ctx.identification())
    
    language = ""
    if ctx.DOUBLE_STRING():
        language = ctx.DOUBLE_STRING().getText().strip('"')
    
    body = ""
    if ctx.REGULAR_COMMENT():
        body = ctx.REGULAR_COMMENT().getText()
    
    return {
        "name": "TextualRepresentation",
        "identification": identification,
        "language": language,
        "body": body
    }


def _visit_metadata_feature_dict(ctx):
    """Visit a metadataFeature context and return a MetadataFeature dictionary.
    
    Grammar: (prefixMetadataMember)* (AT_SIGN | METADATA) metadataFeatureDeclaration (
        ABOUT annotation ( COMMA annotation)*
    )? metadataBody
    """
    prefix_members = []
    for pm in ctx.prefixMetadataMember():
        prefix_members.append(_visit_prefix_metadata_member_dict(pm))
    
    identification = None
    owned_feature_typing = None
    if ctx.metadataFeatureDeclaration():
        mfd = ctx.metadataFeatureDeclaration()
        if mfd.identification():
            identification = _build_identification_dict(mfd.identification())
        if mfd.ownedFeatureTyping():
            owned_feature_typing = _visit_owned_feature_typing_dict(mfd.ownedFeatureTyping())
    
    annotations = []
    if ctx.ABOUT():
        for ann_idx in range(len(ctx.annotation())):
            ann_ctx = ctx.annotation(ann_idx)
            if ann_ctx and ann_ctx.qualifiedName():
                qn_text = ann_ctx.qualifiedName().getText()
                annotations.append({
                    "name": "Annotation",
                    "annotatedElement": {
                        "name": "QualifiedName",
                        "names": qn_text.split("::")
                    }
                })
    
    body = ""
    body_features = []
    if ctx.metadataBody():
        if ctx.metadataBody().SEMI():
            body = ";"
        else:
            # Braced body: preserve the raw text so the body content
            # (field assignments, nested usage members, etc.) survives
            # the round-trip. Without this, every `key = value;` inside
            # a metadata application is silently dropped at visit time.
            body = ctx.metadataBody().getText()
            # Issue #8: also surface each metadataBodyElement as a
            # structured bodyFeatures entry so downstream consumers
            # (sysml2kit, validators, etc.) can read individual
            # key = value fields without re-parsing the raw text.
            # Mirrors the per-endpoint capture introduced for issue #5.
            body_features = _visit_metadata_body_features(ctx.metadataBody())

    return {
        "name": "MetadataFeature",
        "prefixMetadataMember": prefix_members,
        "identification": identification,
        "ownedFeatureTyping": owned_feature_typing,
        "ownedRelationship_about": annotations,
        "body": body,
        "bodyFeatures": body_features,
    }


def _visit_metadata_body_features(mb_ctx):
    """Capture each ``metadataBodyElement`` from a braced metadata body.

    Issue #8: ``_visit_metadata_feature_dict`` previously emitted the
    raw body text but never surfaced the individual ``key = value;``
    items, so consumers of ``load_grammar_antlr`` had no way to read
    the field assignments without re-parsing the raw text.

    The emitted ``bodyFeatures`` list contains one dict per
    ``metadataBodyElement``. For the common ``metadataBodyFeature``
    case each entry carries ``name`` (the feature name from
    ``ownedRedefinition``), ``value`` (the raw ``=value`` text from
    ``valuePart``), and ``text`` (the full source text of the
    element). For the heterogeneous alternative
    (``definitionMember | metadataBodyUsageMember | aliasMember |
    importRule``) only ``text`` is captured.
    """
    if mb_ctx is None:
        return []

    features = []

    # First alternative: metadataBodyElement list (the common path).
    if hasattr(mb_ctx, 'metadataBodyElement') and mb_ctx.metadataBodyElement():
        for elem in mb_ctx.metadataBodyElement():
            entry = _visit_metadata_body_element(elem)
            if entry is not None:
                features.append(entry)

    # Second alternative: heterogeneous (definitionMember |
    # metadataBodyUsageMember | aliasMember | importRule). ANTLR
    # matches exactly one of the two alternatives; if the first
    # alternative returned nothing, try the heterogeneous shapes.
    if not features:
        for attr in ('definitionMember', 'metadataBodyUsageMember',
                     'aliasMember', 'importRule'):
            if hasattr(mb_ctx, attr) and getattr(mb_ctx, attr)():
                items = getattr(mb_ctx, attr)()
                if not isinstance(items, list):
                    items = [items]
                for item in items:
                    features.append({
                        "name": None,
                        "value": None,
                        "text": item.getText(),
                    })

    return features


def _visit_metadata_body_element(elem_ctx):
    """Capture a single ``metadataBodyElement`` as a bodyFeatures entry."""
    if elem_ctx is None:
        return None

    text = elem_ctx.getText()

    # Common case: metadataBodyFeatureMember -> metadataBodyFeature.
    if hasattr(elem_ctx, 'metadataBodyFeatureMember') and elem_ctx.metadataBodyFeatureMember():
        fbm = elem_ctx.metadataBodyFeatureMember()
        if hasattr(fbm, 'metadataBodyFeature') and fbm.metadataBodyFeature():
            f = fbm.metadataBodyFeature()
            # Feature name from ownedRedefinition (qualifiedName).
            name_text = None
            if hasattr(f, 'ownedRedefinition') and f.ownedRedefinition():
                name_text = f.ownedRedefinition().getText()
            # Value text from valuePart (e.g. '="demo"' or '=0.5').
            # Preserve the operator so downstream tools can decide
            # whether '=' vs ':=' vs 'default =' was used.
            value_text = None
            if hasattr(f, 'valuePart') and f.valuePart():
                value_text = f.valuePart().getText()
            # Optional featureSpecializationPart (e.g. ': Type') and
            # FEATURE keyword (redefinition marker). Capture for
            # downstream consumers that need to distinguish redefines
            # vs new feature declarations.
            specialization = None
            if hasattr(f, 'featureSpecializationPart') and f.featureSpecializationPart():
                specialization = f.featureSpecializationPart().getText()
            is_feature_keyword = (
                hasattr(f, 'FEATURE') and f.FEATURE() is not None
            )
            is_redefines = (
                hasattr(f, 'REDEFINES') and getattr(f, 'REDEFINES', lambda: None)() is not None
            )
            return {
                "name": name_text,
                "value": value_text,
                "text": text,
                "featureKeyword": is_feature_keyword,
                "redefines": is_redefines,
                "specialization": specialization,
            }

    # Fallback for non-feature metadataBodyElement shapes
    # (aliasMember / importRule / nonFeatureMember).
    return {
        "name": None,
        "value": None,
        "text": text,
    }


def _visit_prefix_metadata_member_dict(ctx):
    """Visit a prefixMetadataMember context."""
    visibility = ""
    direction = ""
    
    if ctx.PRIVATE():
        visibility = "private"
    elif ctx.PROTECTED():
        visibility = "protected"
    elif ctx.PUBLIC():
        visibility = "public"
    
    if ctx.IN():
        direction = "in"
    elif ctx.OUT():
        direction = "out"
    elif ctx.INOUT():
        direction = "inout"
    
    return {
        "name": "PrefixMetadataMember",
        "visibility": visibility,
        "direction": direction
    }


def _visit_owned_feature_typing_dict(ctx):
    """Visit an ownedFeatureTyping context and return an OwnedFeatureTyping dictionary."""
    if ctx is None:
        return None
    
    if hasattr(ctx, 'qualifiedName') and ctx.qualifiedName():
        qns = ctx.qualifiedName()
        if not isinstance(qns, list):
            qns = [qns]
        names = []
        for qn in qns:
            if qn:
                names.append(qn.getText())
        if names:
            return {
                "name": "OwnedFeatureTyping",
                "type": {
                    "name": "FeatureType",
                    "type": {
                        "name": "QualifiedName",
                        "names": names
                    },
                    "ownedRelatedElement": []
                },
                "ownedRelatedElement": []
            }
    return None


def _visit_annotating_element_dict(annot_elem_ctx):
    """Visit an annotating element context and return an AnnotatingElement dictionary.
    
    Dispatches to documentation, comment, textualRepresentation, or metadataFeature.
    """
    if annot_elem_ctx is None:
        return None
    
    inner = None
    if hasattr(annot_elem_ctx, 'documentation') and annot_elem_ctx.documentation():
        inner = _visit_documentation_dict(annot_elem_ctx.documentation())
    elif hasattr(annot_elem_ctx, 'comment') and annot_elem_ctx.comment():
        inner = _visit_comment_dict(annot_elem_ctx.comment())
    elif hasattr(annot_elem_ctx, 'textualRepresentation') and annot_elem_ctx.textualRepresentation():
        inner = _visit_textual_representation_dict(annot_elem_ctx.textualRepresentation())
    elif hasattr(annot_elem_ctx, 'metadataFeature') and annot_elem_ctx.metadataFeature():
        inner = _visit_metadata_feature_dict(annot_elem_ctx.metadataFeature())
    
    if inner is None:
        return None
    
    return {
        "name": "AnnotatingElement",
        "ownedRelatedElement": inner
    }


def parse_to_dict(source, library=None):
    """Parse SysML source and return a dictionary.
    
    Parameters
    ----------
    source : str or file-like
        Either a string containing SysML v2.0 code, or a file object.
    library : str or Path, optional
        Path to SysML v2 library files for resolving imports.
    
    Returns
    -------
    dict
        A dictionary representation of the SysML model.
    """
    from sysmlpy import antlr_parser
    
    tree = antlr_parser.parse(source, library=library)
    return _visit_root_namespace_dict(tree)


def _visit_root_namespace_dict(tree):
    """Visit the root namespace (top-level) which can have multiple packageBodyElements."""
    body_elements = []
    
    if hasattr(tree, 'packageBodyElement'):
        elements = tree.packageBodyElement()
        if elements:
            for elem_ctx in elements:
                elem_dict = _visit_package_body_element_dict(elem_ctx)
                if elem_dict:
                    body_elements.append(elem_dict)
    
    return {
        "name": "PackageBodyElement",
        "ownedRelationship": body_elements
    }


def _visit_package_dict(tree):
    """Visit a package context and return a dictionary."""
    # Get package name from identification
    pkg_name = None
    pkg_shortname = None
    if tree.packageDeclaration():
        decl = tree.packageDeclaration()
        if hasattr(decl, 'identification'):
            ident = decl.identification()
            if ident:
                # Handle identification: LT name GT name | LT name GT | name
                pkg_name, pkg_shortname = _extract_name_from_ident(ident)

    # Build package body elements
    body_elements = []
    if tree.packageBody():
        body = tree.packageBody()
        if hasattr(body, 'packageBodyElement'):
            elements = body.packageBodyElement()
            for elem_ctx in elements:
                elem_dict = _visit_package_body_element_dict(elem_ctx)
                if elem_dict:
                    body_elements.append(elem_dict)

    # Build the complete package dictionary
    result = {
        "name": "PackageBodyElement",
        "ownedRelationship": [
            {
                "name": "PackageMember",
                "prefix": None,
                "ownedRelatedElement": {
                    "name": "DefinitionElement",
                    "ownedRelatedElement": {
                        "name": "Package",
                        "ownedRelationship": [],
                        "declaration": {
                            "name": "PackageDeclaration",
                            "identification": {
                                "name": "Identification",
                                "declaredShortName": pkg_shortname,
                                "declaredName": pkg_name
                            }
                        },
                        "body": {
                            "name": "PackageBody",
                            "ownedRelationship": body_elements
                        }
                    }
                }
            }
        ]
    }

    return result


def _visit_visibility_indicator_dict(vis_ctx):
    """Build a VisibilityIndicator dict from ANTLR context."""
    return {
        "name": "VisibilityIndicator",
        "private": "private" if vis_ctx.PRIVATE() else "",
        "protected": "protected" if vis_ctx.PROTECTED() else "",
        "public": "public" if vis_ctx.PUBLIC() else ""
    }


def _visit_import_rule_dict(import_ctx):
    """Visit an import rule context and return an Import dictionary."""
    visibility_dict = None
    if import_ctx.visibilityIndicator():
        visibility_dict = _visit_visibility_indicator_dict(import_ctx.visibilityIndicator())

    is_import_all = import_ctx.ALL() is not None

    imp_dec = import_ctx.importDeclaration()

    qn_text = None
    is_recursive = False
    has_namespace = False

    if imp_dec.membershipImport():
        mem = imp_dec.membershipImport()
        qn_text = mem.qualifiedName().getText()
        is_recursive = mem.STAR_STAR() is not None
        qn_names = qn_text.split("::")
        return {
            "name": "Import",
            "body": {"name": "RelationshipBody", "ownedRelationship": []},
            "ownedRelationship": {
                "name": "MembershipImport",
                "prefix": {
                    "name": "ImportPrefix",
                    "visibility": visibility_dict,
                    "isImportAll": is_import_all
                },
                "membership": {
                    "name": "ImportedMembership",
                    "importedMembership": {"name": "QualifiedName", "names": qn_names},
                    "isRecursive": is_recursive
                }
            }
        }

    elif imp_dec.namespaceImport():
        ns = imp_dec.namespaceImport()

        # filterPackage: e.g. vehicle1_c1::*[@Filter] or vehicle1_c1::**[@Filter]
        if ns.filterPackage() is not None:
            fp = ns.filterPackage()
            fpd = fp.filterPackageImportDeclaration()
            if fpd is not None and fpd.namespaceImportDirect() is not None:
                nid = fpd.namespaceImportDirect()
                qn_text = nid.qualifiedName().getText()
                qn_names = qn_text.split("::")
                is_recursive = nid.STAR_STAR() is not None
                return {
                    "name": "Import",
                    "body": {"name": "RelationshipBody", "ownedRelationship": []},
                    "ownedRelationship": {
                        "name": "NamespaceImport",
                        "prefix": {
                            "name": "ImportPrefix",
                            "visibility": visibility_dict,
                            "isImportAll": is_import_all
                        },
                        "ownedRelatedElement": [],
                        "namespace": {
                            "name": "ImportedNamespace",
                            "namespace": {"name": "QualifiedName", "names": qn_names},
                            "isRecursive": is_recursive
                        }
                    }
                }
            elif fpd is not None and fpd.membershipImport() is not None:
                mi = fpd.membershipImport()
                qn_text = mi.qualifiedName().getText()
                qn_names = qn_text.split("::")
                is_recursive = mi.STAR_STAR() is not None
                return {
                    "name": "Import",
                    "body": {"name": "RelationshipBody", "ownedRelationship": []},
                    "ownedRelationship": {
                        "name": "MembershipImport",
                        "prefix": {
                            "name": "ImportPrefix",
                            "visibility": visibility_dict,
                            "isImportAll": is_import_all
                        },
                        "membership": {
                            "name": "ImportedMembership",
                            "importedMembership": {"name": "QualifiedName", "names": qn_names},
                            "isRecursive": is_recursive
                        }
                    }
                }
            # Fallback: return a generic import
            return {
                "name": "Import",
                "body": {"name": "RelationshipBody", "ownedRelationship": []},
                "ownedRelationship": {
                    "name": "NamespaceImport",
                    "prefix": {
                        "name": "ImportPrefix",
                        "visibility": visibility_dict,
                        "isImportAll": is_import_all
                    },
                    "ownedRelatedElement": [],
                    "namespace": None
                }
            }

        qn_text = ns.qualifiedName().getText()
        qn_names = qn_text.split("::")
        has_colon_colon = ns.COLON_COLON() is not None
        has_star_star = ns.STAR_STAR() is not None

        if has_colon_colon:
            return {
                "name": "Import",
                "body": {"name": "RelationshipBody", "ownedRelationship": []},
                "ownedRelationship": {
                    "name": "NamespaceImport",
                    "prefix": {
                        "name": "ImportPrefix",
                        "visibility": visibility_dict,
                        "isImportAll": is_import_all
                    },
                    "ownedRelatedElement": [],
                    "namespace": {
                        "name": "ImportedNamespace",
                        "namespace": {"name": "QualifiedName", "names": qn_names},
                        "isRecursive": has_star_star
                    }
                }
            }
        else:
            return {
                "name": "Import",
                "body": {"name": "RelationshipBody", "ownedRelationship": []},
                "ownedRelationship": {
                    "name": "MembershipImport",
                    "prefix": {
                        "name": "ImportPrefix",
                        "visibility": visibility_dict,
                        "isImportAll": is_import_all
                    },
                    "membership": {
                        "name": "ImportedMembership",
                        "importedMembership": {"name": "QualifiedName", "names": qn_names},
                        "isRecursive": False
}
                }
            }
        
        if hasattr(behav_elem, 'assertConstraintUsage') and behav_elem.assertConstraintUsage():
            ctx = behav_elem.assertConstraintUsage()
            result = _make_assert_constraint_usage_dict(ctx, None)
            if result:
                return {
                    "name": "UsageElement",
                    "ownedRelatedElement": {
                        "name": "OccurrenceUsageElement",
                        "ownedRelatedElement": {
                            "name": "BehaviorUsageElement",
                            "ownedRelationship": result
}
                }
            }
        
        if hasattr(behav_elem, 'assertConstraintUsage') and behav_elem.assertConstraintUsage():
            ctx = behav_elem.assertConstraintUsage()
            result = _make_assert_constraint_usage_dict(ctx, None)
            if result:
                return {
                    "name": "UsageElement",
                    "ownedRelatedElement": {
                        "name": "OccurrenceUsageElement",
                        "ownedRelatedElement": {
                            "name": "BehaviorUsageElement",
                            "ownedRelationship": result
                        }
                    }
                }
            return None
    
    return None
    
    return None


def _visit_alias_member_dict(alias_ctx):
    """Visit an alias member context and return an AliasMember dictionary."""
    short_name = None
    name = None
    has_short_name = alias_ctx.LT() is not None

    name_list = alias_ctx.name() if hasattr(alias_ctx, 'name') else None
    if name_list and isinstance(name_list, list):
        if len(name_list) >= 2:
            short_name = name_list[0].getText() if name_list[0] else None
            name = name_list[1].getText() if name_list[1] else None
        elif len(name_list) == 1:
            if has_short_name:
                short_name = name_list[0].getText()
            else:
                name = name_list[0].getText()

    qn_text = alias_ctx.qualifiedName().getText()

    # Extract visibility from memberPrefix
    prefix = None
    if hasattr(alias_ctx, 'memberPrefix') and alias_ctx.memberPrefix():
        mp = alias_ctx.memberPrefix()
        if hasattr(mp, 'visibilityIndicator') and mp.visibilityIndicator():
            prefix = {
                "name": "MemberPrefix",
                "visibility": _visit_visibility_indicator_dict(mp.visibilityIndicator())
            }

    # Extract body annotations (e.g. block comments inside alias body)
    body_owned = []
    if hasattr(alias_ctx, 'relationshipBody') and alias_ctx.relationshipBody():
        rb = alias_ctx.relationshipBody()
        for child in rb.children:
            if type(child).__name__ == 'RelationshipOwnedElementContext':
                for c2 in child.children:
                    if type(c2).__name__ == 'OwnedAnnotationContext':
                        for c3 in c2.children:
                            if type(c3).__name__ == 'AnnotatingElementContext':
                                comment_text = c3.getText()
                                body_owned.append({
                                    "name": "OwnedAnnotation",
                                    "ownedRelatedElement": [
                                        {
                                            "name": "AnnotatingElement",
                                            "ownedRelatedElement": {
                                                "name": "CommentSysML",
                                                "body": comment_text,
                                                "identification": None,
                                                "ownedRelationship": []
                                            }
                                        }
                                    ]
                                })

    return {
        "name": "AliasMember",
        "prefix": prefix,
        "body": {"name": "RelationshipBody", "ownedRelationship": body_owned},
        "memberShortName": short_name,
        "memberName": name,
        "memberElement": {"name": "QualifiedName", "names": qn_text.split("::")}
    }


def _visit_package_body_element_dict(elem_ctx):
    """Visit a package body element and return a dictionary."""
    # Check for importRule first
    if hasattr(elem_ctx, 'importRule') and elem_ctx.importRule():
        return _visit_import_rule_dict(elem_ctx.importRule())

    # Check for aliasMember
    if hasattr(elem_ctx, 'aliasMember') and elem_ctx.aliasMember():
        return _visit_alias_member_dict(elem_ctx.aliasMember())

    if not hasattr(elem_ctx, 'packageMember'):
        return None
    
    member = elem_ctx.packageMember()
    if not member:
        return None
    
    # Get prefix if present (memberPrefix = (visibilityIndicator)?)
    prefix = None
    if hasattr(member, 'memberPrefix'):
        mp = member.memberPrefix()
        if mp and hasattr(mp, 'visibilityIndicator') and mp.visibilityIndicator():
            prefix = {
                "name": "MemberPrefix",
                "visibility": _visit_visibility_indicator_dict(mp.visibilityIndicator())
            }
    
    # Check if it's a definition or usage element
    if hasattr(member, 'definitionElement'):
        def_elem = member.definitionElement()
        if def_elem:
            return _visit_definition_element_dict(def_elem, prefix)
    
    # Check usage element (only if definition was falsy or absent)
    if hasattr(member, 'usageElement'):
        usage_elem = member.usageElement()
        if usage_elem:
            return _visit_usage_element_dict(usage_elem, prefix)
    
    return None


def _visit_definition_element_dict(def_elem_ctx, prefix=None):
    """Visit a definition element context and return a dictionary."""
    # Try different definition types
    # Check package first (nested packages)
    if hasattr(def_elem_ctx, 'package') and def_elem_ctx.package():
        ctx = def_elem_ctx.package()
        return _make_nested_package_dict(ctx, prefix)
    elif hasattr(def_elem_ctx, 'libraryPackage') and def_elem_ctx.libraryPackage():
        # `standard library package Foo { ... }` shares the declaration/body
        # structure of `package Foo { ... }`. Pass is_standard_library=True so
        # the round-trip dict preserves the `standard library` keywords.
        ctx = def_elem_ctx.libraryPackage()
        return _make_nested_package_dict(ctx, prefix, is_standard_library=True)
    elif hasattr(def_elem_ctx, 'dependency') and def_elem_ctx.dependency():
        # Issue #4: dependency statements were silently dropped. The grammar
        # class Dependency is fully implemented but no visitor dispatch
        # constructed it.
        ctx = def_elem_ctx.dependency()
        return _make_dependency_dict(ctx, prefix)
    elif hasattr(def_elem_ctx, 'itemDefinition') and def_elem_ctx.itemDefinition():
        ctx = def_elem_ctx.itemDefinition()
        return _make_item_definition_dict(ctx, prefix)
    elif hasattr(def_elem_ctx, 'partDefinition') and def_elem_ctx.partDefinition():
        ctx = def_elem_ctx.partDefinition()
        return _make_part_definition_dict(ctx, prefix)
    elif hasattr(def_elem_ctx, 'attributeDefinition') and def_elem_ctx.attributeDefinition():
        ctx = def_elem_ctx.attributeDefinition()
        return _make_attribute_definition_dict(ctx, prefix)
    elif hasattr(def_elem_ctx, 'portDefinition') and def_elem_ctx.portDefinition():
        ctx = def_elem_ctx.portDefinition()
        return _make_port_definition_dict(ctx, prefix)
    elif hasattr(def_elem_ctx, 'requirementDefinition') and def_elem_ctx.requirementDefinition():
        ctx = def_elem_ctx.requirementDefinition()
        return _make_requirement_definition_dict(ctx, prefix)
    elif hasattr(def_elem_ctx, 'useCaseDefinition') and def_elem_ctx.useCaseDefinition():
        ctx = def_elem_ctx.useCaseDefinition()
        return _make_use_case_definition_dict(ctx, prefix)
    elif hasattr(def_elem_ctx, 'actionDefinition') and def_elem_ctx.actionDefinition():
        ctx = def_elem_ctx.actionDefinition()
        return _make_action_definition_dict(ctx, prefix)
    elif hasattr(def_elem_ctx, 'stateDefinition') and def_elem_ctx.stateDefinition():
        ctx = def_elem_ctx.stateDefinition()
        return _make_state_definition_dict(ctx, prefix)
    elif hasattr(def_elem_ctx, 'flowConnectionDefinition') and def_elem_ctx.flowConnectionDefinition():
        ctx = def_elem_ctx.flowConnectionDefinition()
        return _make_flow_connection_definition_dict(ctx, prefix)
    elif hasattr(def_elem_ctx, 'flowDefinition') and def_elem_ctx.flowDefinition():
        ctx = def_elem_ctx.flowDefinition()
        return _make_flow_connection_definition_dict(ctx, prefix)
    elif hasattr(def_elem_ctx, 'calculationDefinition') and def_elem_ctx.calculationDefinition():
        ctx = def_elem_ctx.calculationDefinition()
        return _make_calculation_definition_dict(ctx, prefix)
    elif hasattr(def_elem_ctx, 'interfaceDefinition') and def_elem_ctx.interfaceDefinition():
        ctx = def_elem_ctx.interfaceDefinition()
        return _make_interface_definition_dict(ctx, prefix)
    elif hasattr(def_elem_ctx, 'connectionDefinition') and def_elem_ctx.connectionDefinition():
        ctx = def_elem_ctx.connectionDefinition()
        return _make_connection_definition_dict(ctx, prefix)
    elif hasattr(def_elem_ctx, 'constraintDefinition') and def_elem_ctx.constraintDefinition():
        ctx = def_elem_ctx.constraintDefinition()
        return _make_constraint_definition_dict(ctx, prefix)
    elif hasattr(def_elem_ctx, 'enumerationDefinition') and def_elem_ctx.enumerationDefinition():
        ctx = def_elem_ctx.enumerationDefinition()
        return _make_enumeration_definition_dict(ctx, prefix)
    elif hasattr(def_elem_ctx, 'allocationDefinition') and def_elem_ctx.allocationDefinition():
        ctx = def_elem_ctx.allocationDefinition()
        return _make_allocation_definition_dict(ctx, prefix)
    elif hasattr(def_elem_ctx, 'metadataDefinition') and def_elem_ctx.metadataDefinition():
        ctx = def_elem_ctx.metadataDefinition()
        return _make_metadata_definition_dict(ctx, prefix)
    elif hasattr(def_elem_ctx, 'renderingDefinition') and def_elem_ctx.renderingDefinition():
        ctx = def_elem_ctx.renderingDefinition()
        return _make_rendering_definition_dict(ctx, prefix)
    elif hasattr(def_elem_ctx, 'individualDefinition') and def_elem_ctx.individualDefinition():
        ctx = def_elem_ctx.individualDefinition()
        return _make_individual_definition_dict(ctx, prefix)
    elif hasattr(def_elem_ctx, 'viewDefinition') and def_elem_ctx.viewDefinition():
        ctx = def_elem_ctx.viewDefinition()
        return _make_view_definition_dict(ctx, prefix)
    elif hasattr(def_elem_ctx, 'viewpointDefinition') and def_elem_ctx.viewpointDefinition():
        ctx = def_elem_ctx.viewpointDefinition()
        return _make_viewpoint_definition_dict(ctx, prefix)
    elif hasattr(def_elem_ctx, 'concernDefinition') and def_elem_ctx.concernDefinition():
        ctx = def_elem_ctx.concernDefinition()
        return _make_concern_definition_dict(ctx, prefix)
    elif hasattr(def_elem_ctx, 'caseDefinition') and def_elem_ctx.caseDefinition():
        ctx = def_elem_ctx.caseDefinition()
        return _make_case_definition_dict(ctx, prefix)
    elif hasattr(def_elem_ctx, 'analysisCaseDefinition') and def_elem_ctx.analysisCaseDefinition():
        ctx = def_elem_ctx.analysisCaseDefinition()
        return _make_analysis_case_definition_dict(ctx, prefix)
    elif hasattr(def_elem_ctx, 'verificationCaseDefinition') and def_elem_ctx.verificationCaseDefinition():
        ctx = def_elem_ctx.verificationCaseDefinition()
        return _make_verification_case_definition_dict(ctx, prefix)
    elif hasattr(def_elem_ctx, 'annotatingElement') and def_elem_ctx.annotatingElement():
        ann_ctx = def_elem_ctx.annotatingElement()
        ann_dict = _visit_annotating_element_dict(ann_ctx)
        if ann_dict is None:
            return None
        return {
            "name": "PackageMember",
            "prefix": prefix,
            "ownedRelatedElement": {
                "name": "DefinitionElement",
                "ownedRelatedElement": ann_dict
            }
        }
    
    return None


def _make_item_definition_dict(ctx, member_prefix=None):
    """Create an ItemDefinition dictionary."""
    name, shortname = _get_definition_identification(ctx)
    occ_prefix = _get_occurrence_definition_prefix(ctx)
    
    # Get body items
    body_items = []
    if hasattr(ctx, 'definition'):
        defn = ctx.definition()
        if defn and hasattr(defn, 'definitionBody'):
            body_ctx = defn.definitionBody()
            if body_ctx:
                body_items = _visit_definition_body_dict(body_ctx)
    
    return {
        "name": "PackageMember",
        "prefix": member_prefix,
        "ownedRelatedElement": {
            "name": "DefinitionElement",
            "ownedRelatedElement": {
                "name": "ItemDefinition",
                "prefix": occ_prefix,
                "definition": {
                    "name": "Definition",
                    "declaration": {
                        "name": "DefinitionDeclaration",
                        "identification": {
                            "name": "Identification",
                            "declaredShortName": shortname,
                            "declaredName": name
                        },
                        "subclassificationpart": _get_subclassification_part(ctx)
                    },
                    "body": {
                        "name": "DefinitionBody",
                        "ownedRelatedElement": body_items
                    }
                }
            }
        }
    }


def _make_nested_package_dict(ctx, prefix=None, is_standard_library=False):
    """Create a Package dictionary for a nested package.
    
    Similar to _visit_package_dict but returns a PackageMember wrapped result.
    
    ``is_standard_library`` is True when the source was a
    ``standard library package`` declaration; in that case the
    ``standard library`` keyword is preserved through the round-trip.
    """
    pkg_name = None
    pkg_shortname = None
    if hasattr(ctx, 'packageDeclaration') and ctx.packageDeclaration():
        decl = ctx.packageDeclaration()
        if hasattr(decl, 'identification'):
            ident = decl.identification()
            if ident:
                pkg_name, pkg_shortname = _extract_name_from_ident(ident)
    
    # Process body elements
    body_elements = []
    if hasattr(ctx, 'packageBody') and ctx.packageBody():
        body = ctx.packageBody()
        if hasattr(body, 'packageBodyElement'):
            elements = body.packageBodyElement()
            for elem_ctx in elements:
                elem_dict = _visit_package_body_element_dict(elem_ctx)
                if elem_dict:
                    body_elements.append(elem_dict)
    
    return {
        "name": "PackageMember",
        "prefix": None,
        "ownedRelatedElement": {
            "name": "DefinitionElement",
            "ownedRelatedElement": {
                "name": "Package",
                "ownedRelationship": [],
                "isStandardLibrary": is_standard_library,
                "declaration": {
                    "name": "PackageDeclaration",
                    "identification": {
                        "name": "Identification",
                        "declaredShortName": pkg_shortname,
                        "declaredName": pkg_name
                    }
                },
                "body": {
                    "name": "PackageBody",
                    "ownedRelationship": body_elements
                }
            }
        }
    }


def _get_occurrence_usage_prefix(ctx):
    """Extract OccurrenceUsagePrefix from a usage context (for 'ref', direction, etc.)."""
    is_reference = False
    direction_in = ""
    direction_out = ""
    direction_inout = ""
    is_end = False
    is_individual = False
    portion_kind = None
    
    if hasattr(ctx, 'occurrenceUsagePrefix') and ctx.occurrenceUsagePrefix():
        oup = ctx.occurrenceUsagePrefix()
        if hasattr(oup, 'basicUsagePrefix') and oup.basicUsagePrefix():
            bup = oup.basicUsagePrefix()
            is_reference = hasattr(bup, 'REF') and bup.REF() is not None
            # Extract direction and end from refPrefix
            if hasattr(bup, 'refPrefix') and bup.refPrefix():
                rp = bup.refPrefix()
                if hasattr(rp, 'featureDirection') and rp.featureDirection():
                    fd = rp.featureDirection()
                    direction_in = "in " if fd.IN() is not None else ""
                    direction_out = "out" if fd.OUT() is not None else ""
                    direction_inout = "inout" if fd.INOUT() is not None else ""
                # Check for END keyword
                if hasattr(rp, 'END') and rp.END() is not None:
                    is_end = True
        
        # Extract INDIVIDUAL keyword
        if hasattr(oup, 'INDIVIDUAL') and oup.INDIVIDUAL() is not None:
            is_individual = True
        
        # Extract portionKind (SNAPSHOT or TIMESLICE)
        if hasattr(oup, 'portionKind') and oup.portionKind():
            pk_ctx = oup.portionKind()
            if hasattr(pk_ctx, 'SNAPSHOT') and pk_ctx.SNAPSHOT() is not None:
                portion_kind = "snapshot"
            elif hasattr(pk_ctx, 'TIMESLICE') and pk_ctx.TIMESLICE() is not None:
                portion_kind = "timeslice"
    
    has_direction = any([direction_in, direction_out, direction_inout])
    
    if not is_reference and not has_direction and not is_end and not is_individual and portion_kind is None:
        return None
    
    ref_prefix = None
    if has_direction or is_end:
        ref_prefix = {
            "name": "RefPrefix",
            "direction": {
                "name": "FeatureDirection",
                "in": direction_in,
                "out": direction_out,
                "inout": direction_inout
            },
            "isAbstract": None,
            "isVariation": None,
            "isReadOnly": None,
            "isDerived": None,
            "isEnd": "end" if is_end else None
        }
    
    portion_kind_dict = None
    if portion_kind is not None:
        portion_kind_dict = {
            "name": "PortionKind",
            "kind": portion_kind
        }
    
    return {
        "name": "OccurrenceUsagePrefix",
        "prefix": {
            "name": "BasicUsagePrefix",
            "prefix": ref_prefix,
            "isReference": is_reference
        },
        "isIndividual": "individual" if is_individual else None,
        "portionKind": portion_kind_dict,
        "usageExtension": []
    }


def _make_portion_usage_prefix(ctx):
    """Build an OccurrenceUsagePrefix dict from a PortionUsageContext.
    
    PortionUsageContext has basicUsagePrefix directly (not via occurrenceUsagePrefix),
    plus optional INDIVIDUAL and required portionKind.
    """
    is_reference = False
    direction_in = ""
    direction_out = ""
    direction_inout = ""
    is_end = False
    is_individual = False
    portion_kind = None

    if hasattr(ctx, 'basicUsagePrefix') and ctx.basicUsagePrefix():
        bup = ctx.basicUsagePrefix()
        is_reference = hasattr(bup, 'REF') and bup.REF() is not None
        if hasattr(bup, 'refPrefix') and bup.refPrefix():
            rp = bup.refPrefix()
            if hasattr(rp, 'featureDirection') and rp.featureDirection():
                fd = rp.featureDirection()
                direction_in = "in " if fd.IN() is not None else ""
                direction_out = "out" if fd.OUT() is not None else ""
                direction_inout = "inout" if fd.INOUT() is not None else ""
            if hasattr(rp, 'END') and rp.END() is not None:
                is_end = True

    if hasattr(ctx, 'INDIVIDUAL') and ctx.INDIVIDUAL() is not None:
        is_individual = True

    if hasattr(ctx, 'portionKind') and ctx.portionKind():
        pk_ctx = ctx.portionKind()
        if hasattr(pk_ctx, 'SNAPSHOT') and pk_ctx.SNAPSHOT() is not None:
            portion_kind = "snapshot"
        elif hasattr(pk_ctx, 'TIMESLICE') and pk_ctx.TIMESLICE() is not None:
            portion_kind = "timeslice"

    ref_prefix = None
    has_direction = any([direction_in, direction_out, direction_inout])
    if has_direction or is_end:
        ref_prefix = {
            "name": "RefPrefix",
            "direction": {
                "name": "FeatureDirection",
                "in": direction_in,
                "out": direction_out,
                "inout": direction_inout
            },
            "isAbstract": None,
            "isVariation": None,
            "isReadOnly": None,
            "isDerived": None,
            "isEnd": "end" if is_end else None
        }

    portion_kind_dict = None
    if portion_kind is not None:
        portion_kind_dict = {
            "name": "PortionKind",
            "kind": portion_kind
        }

    return {
        "name": "OccurrenceUsagePrefix",
        "prefix": {
            "name": "BasicUsagePrefix",
            "prefix": ref_prefix,
            "isReference": is_reference
        },
        "isIndividual": "individual" if is_individual else None,
        "portionKind": portion_kind_dict,
        "usageExtension": []
    }


def _get_occurrence_definition_prefix(ctx):
    """Extract OccurrenceDefinitionPrefix from a definition context (for 'abstract' etc.)."""
    is_abstract = False
    is_variation = False
    
    if hasattr(ctx, 'occurrenceDefinitionPrefix') and ctx.occurrenceDefinitionPrefix():
        odp = ctx.occurrenceDefinitionPrefix()
        if hasattr(odp, 'basicDefinitionPrefix') and odp.basicDefinitionPrefix():
            bdp = odp.basicDefinitionPrefix()
            is_abstract = hasattr(bdp, 'ABSTRACT') and bdp.ABSTRACT() is not None
            is_variation = hasattr(bdp, 'VARIATION') and bdp.VARIATION() is not None
    
    if not is_abstract and not is_variation:
        return None
    
    return {
        "name": "OccurrenceDefinitionPrefix",
        "prefix": {
            "name": "BasicDefinitionPrefix",
            "isAbstract": "abstract" if is_abstract else None,
            "isVariation": "variation" if is_variation else None,
        },
        "isIndividual": None,
        "ownedRelationship": [],
        "keyword": []
    }

def _make_part_definition_dict(ctx, member_prefix=None):
    """Create a PartDefinition dictionary.
    
    member_prefix: MemberPrefix dict (visibility) to place on PackageMember.prefix.
    The OccurrenceDefinitionPrefix (abstract) is extracted from the ANTLR context.
    """
    name, shortname = _get_definition_identification(ctx)
    occ_prefix = _get_occurrence_definition_prefix(ctx)
    
    # Get body items
    body_items = []
    if hasattr(ctx, 'definition'):
        defn = ctx.definition()
        if defn and hasattr(defn, 'definitionBody'):
            body_ctx = defn.definitionBody()
            if body_ctx:
                body_items = _visit_definition_body_dict(body_ctx)
    
    result = {
        "name": "PackageMember",
        "prefix": member_prefix,
        "ownedRelatedElement": {
            "name": "DefinitionElement",
            "ownedRelatedElement": {
                "name": "PartDefinition",
                "prefix": occ_prefix,
                "definition": {
                    "name": "Definition",
                    "declaration": {
                        "name": "DefinitionDeclaration",
                        "identification": {
                            "name": "Identification",
                            "declaredShortName": shortname,
                            "declaredName": name
                        },
                        "subclassificationpart": _get_subclassification_part(ctx)
                    },
                    "body": {
                        "name": "DefinitionBody",
                        "ownedRelatedElement": body_items
                    }
                }
            }
        }
    }
    
    return result


def _make_attribute_definition_dict(ctx, member_prefix=None):
    """Create an AttributeDefinition dictionary."""
    name, shortname = _get_definition_identification(ctx)
    occ_prefix = _get_occurrence_definition_prefix(ctx)
    # Get body items from definition body
    body_items = []
    if hasattr(ctx, "definition") and ctx.definition():
        defn = ctx.definition()
        if hasattr(defn, "definitionBody") and defn.definitionBody():
            body_items = _visit_definition_body_dict(defn.definitionBody())
    
    return {
        "name": "PackageMember",
        "prefix": member_prefix,
        "ownedRelatedElement": {
            "name": "DefinitionElement",
            "ownedRelatedElement": {
                "name": "AttributeDefinition",
                "prefix": occ_prefix,
                "definition": {
                    "name": "Definition",
                    "declaration": {
                        "name": "DefinitionDeclaration",
                        "identification": {
                            "name": "Identification",
                            "declaredShortName": shortname,
                            "declaredName": name
                        },
                        "subclassificationpart": _get_subclassification_part(ctx)
                    },
                    "body": {
                        "name": "DefinitionBody",
                        "ownedRelatedElement": body_items
                    }
                }
            }
        }
    }


def _make_port_definition_dict(ctx, member_prefix=None):
    """Create a PortDefinition dictionary."""
    name, shortname = _get_definition_identification(ctx)
    occ_prefix = _get_occurrence_definition_prefix(ctx)
    
    # Get body items
    body_items = []
    if hasattr(ctx, 'definition'):
        defn = ctx.definition()
        if defn and hasattr(defn, 'definitionBody'):
            body_ctx = defn.definitionBody()
            if body_ctx:
                body_items = _visit_definition_body_dict(body_ctx)
    
    return {
        "name": "PackageMember",
        "prefix": member_prefix,
        "ownedRelatedElement": {
            "name": "DefinitionElement",
            "ownedRelatedElement": {
                "name": "PortDefinition",
                "prefix": occ_prefix,
                "definition": {
                    "name": "Definition",
                    "declaration": {
                        "name": "DefinitionDeclaration",
                        "identification": {
                            "name": "Identification",
                            "declaredShortName": shortname,
                            "declaredName": name
                        },
                        "subclassificationpart": _get_subclassification_part(ctx)
                    },
                    "body": {
                        "name": "DefinitionBody",
                        "ownedRelatedElement": body_items
                    }
                }
            }
        }
    }


def _make_requirement_definition_dict(ctx, member_prefix=None):
    """Create a RequirementDefinition dictionary.
    
    RequirementDefinition uses requirementBody (not definitionBody).
    """
    name, shortname = _get_definition_identification(ctx)
    occ_prefix = _get_occurrence_definition_prefix(ctx)
    
    body_items = []
    if hasattr(ctx, "requirementBody") and ctx.requirementBody():
        body_ctx = ctx.requirementBody()
        body_items = _visit_requirement_body_dict(body_ctx)
    
    if not name and not shortname:
        name = "Requirement_" + str(uuid.uuid4())[:8]
    
    return {
        "name": "PackageMember",
        "prefix": member_prefix,
        "ownedRelatedElement": {
            "name": "DefinitionElement",
            "ownedRelatedElement": {
                "name": "RequirementDefinition",
                "prefix": occ_prefix,
                "declaration": {
                    "name": "DefinitionDeclaration",
                    "identification": {
                        "name": "Identification",
                        "declaredShortName": shortname,
                        "declaredName": name
                    },
                    "subclassificationpart": _get_subclassification_part(ctx)
                },
                "body": {
                    "name": "RequirementBody",
                    "item": body_items
                }
            }
        }
    }


def _make_use_case_definition_dict(ctx, member_prefix=None):
    """Create a UseCaseDefinition dictionary."""
    name, shortname = _get_definition_identification(ctx)
    occ_prefix = _get_occurrence_definition_prefix(ctx)
    # Get body items from definition body
    body_items = []
    if hasattr(ctx, "definition") and ctx.definition():
        defn = ctx.definition()
        if hasattr(defn, "definitionBody") and defn.definitionBody():
            body_items = _visit_definition_body_dict(defn.definitionBody())
    if not name and not shortname:
        name = "UseCase_" + str(uuid.uuid4())[:8]
    
    # Note: UseCaseDefinition uses 'declaration' not 'definition'
    return {
        "name": "PackageMember",
        "prefix": member_prefix,
        "ownedRelatedElement": {
            "name": "DefinitionElement",
            "ownedRelatedElement": {
                "name": "UseCaseDefinition",
                "prefix": occ_prefix,
                "declaration": {
                    "name": "DefinitionDeclaration",
                    "identification": {
                        "name": "Identification",
                        "declaredShortName": shortname,
                        "declaredName": name
                    },
                    "subclassificationpart": _get_subclassification_part(ctx)
                },
                "body": {
                    "name": "CaseBody",
                    "item": [],
                    "ownedRelationship": None
                }
            }
        }
    }


def _make_use_case_usage_dict(ctx, prefix=None):
    """Create a UseCaseUsage dictionary.
    
    Grammar: useCaseUsage: occurrenceUsagePrefix USE CASE constraintUsageDeclaration caseBody
    UseCaseUsage class expects: prefix, declaration (CalculationUsageDeclaration), body (CaseBody)
    """
    name = None
    shortname = None
    typed_by = None
    
    # Extract name from constraintUsageDeclaration
    cud = None
    if hasattr(ctx, 'constraintUsageDeclaration') and ctx.constraintUsageDeclaration():
        cud = ctx.constraintUsageDeclaration()
    
    ud = None
    if cud and hasattr(cud, 'usageDeclaration') and cud.usageDeclaration():
        ud = cud.usageDeclaration()
    
    if ud and hasattr(ud, 'identification') and ud.identification():
        ident = ud.identification()
        if hasattr(ident, 'name'):
            name_list = ident.name()
            if name_list and isinstance(name_list, list):
                if len(name_list) == 2:
                    shortname = name_list[0].getText()
                    name = name_list[1].getText()
                elif len(name_list) == 1:
                    name_text = name_list[0].getText()
                    name, shortname = _extract_name_shortname(name_text)
    
    # Extract typed_by from specialization
    typed_by = _get_action_usage_typed_by(ctx)
    if typed_by is None:
        typed_by = _get_action_usage_subsetted_by(ctx)
    
    spec_full = _full_specialization_for_ctx(ctx)
    if spec_full is not None:
        specialization = spec_full
    else:
        specialization = _build_specialization(typed_by) if typed_by else None
    occ_prefix = _get_occurrence_usage_prefix(ctx) if ctx else None
    
    # Get case body items
    body_items = []
    if hasattr(ctx, 'caseBody') and ctx.caseBody():
        body_items = _visit_case_body_items(ctx.caseBody())
    
    return {
        "name": "PackageMember",
        "prefix": None,
        "ownedRelatedElement": {
            "name": "UsageElement",
            "ownedRelatedElement": {
                "name": "OccurrenceUsageElement",
                "ownedRelatedElement": {
                    "name": "BehaviorUsageElement",
                    "ownedRelationship": {
                        "name": "UseCaseUsage",
                        "prefix": occ_prefix or prefix,
                        "declaration": {
                            "name": "CalculationUsageDeclaration",
                            "declaration": {
                                "name": "UsageDeclaration",
                                "declaration": {
                                    "name": "FeatureDeclaration",
                                    "identification": {
                                        "name": "Identification",
                                        "declaredShortName": shortname,
                                        "declaredName": name
                                    },
                                    "specialization": specialization
                                }
                            },
                            "valuepart": None
                        },
                        "body": {
                            "name": "CaseBody",
                            "item": body_items
                        }
                    }
                }
            }
        }
    }


def _make_message_dict(ctx, prefix=None):
    """Create a Message dictionary.
    
    Grammar: message: occurrenceUsagePrefix MESSAGE messageDeclaration definitionBody
    Message class expects: prefix, declaration (MessageDeclaration), body (DefinitionBody)
    """
    name = None
    shortname = None
    of_item = None
    from_event = None
    to_event = None
    
    # Extract from messageDeclaration
    msg_decl = None
    if hasattr(ctx, 'messageDeclaration') and ctx.messageDeclaration():
        msg_decl = ctx.messageDeclaration()
        
        # Get usageDeclaration for name
        ud = None
        if hasattr(msg_decl, 'usageDeclaration') and msg_decl.usageDeclaration():
            ud = msg_decl.usageDeclaration()
            if ud and hasattr(ud, 'identification') and ud.identification():
                ident = ud.identification()
                if hasattr(ident, 'name'):
                    name_list = ident.name()
                    if name_list and isinstance(name_list, list):
                        if len(name_list) == 2:
                            shortname = name_list[0].getText()
                            name = name_list[1].getText()
                        elif len(name_list) == 1:
                            name_text = name_list[0].getText()
                            name, shortname = _extract_name_shortname(name_text)
        
        # Get OF item
        if hasattr(msg_decl, 'flowPayloadFeatureMember') and msg_decl.flowPayloadFeatureMember():
            of_item = msg_decl.flowPayloadFeatureMember()
        
        # Get FROM/TO events
        if hasattr(msg_decl, 'messageEventMember') and msg_decl.messageEventMember():
            events = msg_decl.messageEventMember()
            if isinstance(events, list) and len(events) >= 2:
                from_event = events[0]
                to_event = events[1]
            elif isinstance(events, list) and len(events) == 1:
                to_event = events[0]
    
    occ_prefix = _get_occurrence_usage_prefix(ctx) if ctx else None
    
    # Get definition body items
    body_items = []
    if hasattr(ctx, 'definitionBody') and ctx.definitionBody():
        body_items = _visit_definition_body_dict(ctx.definitionBody())
    
    # Build message declaration dict
    msg_decl_dict = {
        "name": "MessageDeclaration",
        "declaration": None,
        "valuepart": None,
        "ownedRelationship": []
    }
    
    if ud:
        msg_decl_dict["declaration"] = {
            "name": "UsageDeclaration",
            "declaration": {
                "name": "FeatureDeclaration",
                "identification": {
                    "name": "Identification",
                    "declaredShortName": shortname,
                    "declaredName": name
                },
                "specialization": None
            }
        }
    
    # Build from/to events
    if from_event:
        msg_decl_dict["ownedRelationship"].append({
            "name": "MessageEventMember",
            "ownedRelatedElement": [{
                "name": "MessageEvent",
                "ownedRelationship": []
            }]
        })
    if to_event:
        msg_decl_dict["ownedRelationship"].append({
            "name": "MessageEventMember",
            "ownedRelatedElement": [{
                "name": "MessageEvent",
                "ownedRelationship": []
            }]
        })
    
    return {
        "name": "PackageMember",
        "prefix": None,
        "ownedRelatedElement": {
            "name": "UsageElement",
            "ownedRelatedElement": {
                "name": "OccurrenceUsageElement",
                "ownedRelatedElement": {
                    "name": "StructureUsageElement",
                    "ownedRelatedElement": {
                        "name": "Message",
                        "prefix": occ_prefix or prefix,
                        "declaration": msg_decl_dict,
                        "body": {
                            "name": "DefinitionBody",
                            "ownedRelatedElement": body_items
                        }
                    }
                }
            }
        }
    }


def _make_interface_definition_dict(ctx, member_prefix=None):
    """Create an InterfaceDefinition dictionary."""
    name, shortname = _get_definition_identification(ctx)
    occ_prefix = _get_occurrence_definition_prefix(ctx)
    # Get body items from interface body
    body_items = []
    if hasattr(ctx, "interfaceBody") and ctx.interfaceBody():
        body_ctx = ctx.interfaceBody()
        if hasattr(body_ctx, 'interfaceBodyItem') and body_ctx.interfaceBodyItem():
            for item_ctx in body_ctx.interfaceBodyItem():
                item_dict = _visit_definition_body_item_dict(item_ctx, is_interface=True)
                if item_dict:
                    body_items.append(item_dict)
    if not name and not shortname:
        name = "Interface_" + str(uuid.uuid4())[:8]
    
    return {
        "name": "PackageMember",
        "prefix": member_prefix,
        "ownedRelatedElement": {
            "name": "DefinitionElement",
            "ownedRelatedElement": {
                "name": "InterfaceDefinition",
                "prefix": occ_prefix,
                "definition": {
                    "name": "Definition",
                    "declaration": {
                        "name": "DefinitionDeclaration",
                        "identification": {
                            "name": "Identification",
                            "declaredShortName": shortname,
                            "declaredName": name
                        },
                        "subclassificationpart": _get_subclassification_part(ctx)
                    },
                    "body": {
                        "name": "DefinitionBody",
                        "ownedRelatedElement": body_items
                    }
                }
            }
        }
    }


def _make_action_definition_dict(ctx, member_prefix=None):
    """Create an ActionDefinition dictionary.
    
    ActionDefinition uses 'declaration' directly (not wrapped in 'definition').
    """
    # ActionDefinition's identification is at ctx.definitionDeclaration().identification()
    name = None
    shortname = None
    if ctx is not None:
        dd = None
        if hasattr(ctx, 'definitionDeclaration') and ctx.definitionDeclaration():
            dd = ctx.definitionDeclaration()
        
        if dd and hasattr(dd, 'identification') and dd.identification():
            ident = dd.identification()
            if hasattr(ident, 'name'):
                name_list = ident.name()
                if name_list and isinstance(name_list, list):
                    if len(name_list) == 2:
                        shortname = name_list[0].getText()
                        name = name_list[1].getText()
                    elif len(name_list) == 1:
                        name_text = name_list[0].getText()
                        if hasattr(ident, 'LT') and ident.LT() is not None:
                            shortname = name_text
                        else:
                            name = name_text
    
    # Extract action body items from actionBody (not definitionBody)
    body_items = []
    if hasattr(ctx, 'actionBody') and ctx.actionBody():
        action_body = ctx.actionBody()
        if hasattr(action_body, 'actionBodyItem') and action_body.actionBodyItem():
            for abi_ctx in action_body.actionBodyItem():
                item_dict = _visit_action_body_item(abi_ctx)
                if item_dict:
                    body_items.append(item_dict)
    
    occ_prefix = _get_occurrence_definition_prefix(ctx)
    return {
        "name": "PackageMember",
        "prefix": member_prefix,
        "ownedRelatedElement": {
            "name": "DefinitionElement",
            "ownedRelatedElement": {
                "name": "ActionDefinition",
                "prefix": occ_prefix,
                "declaration": {
                    "name": "DefinitionDeclaration",
                    "identification": {
                        "name": "Identification",
                        "declaredShortName": shortname,
                        "declaredName": name
                    },
                    "subclassificationpart": _get_subclassification_part(ctx)
                },
                "body": {
                    "name": "ActionBody",
                    "items": body_items
                }
            }
        }
    }


def _visit_action_body_items(ctx):
    """Extract ActionBodyItem dicts from an actionDefinition or actionUsage context.
    
    Processes actionBody().actionBodyItem() items, handling nonBehaviorBodyItem
    (in/out parameters, attributes) and actionBehaviorMember (nested actions).
    """
    if ctx is None:
        return []
    
    action_body = None
    if hasattr(ctx, 'actionBody') and ctx.actionBody():
        action_body = ctx.actionBody()
    
    if action_body is None:
        return []
    
    items = []
    if not (hasattr(action_body, 'actionBodyItem') and action_body.actionBodyItem()):
        return []
    
    for abi_ctx in action_body.actionBodyItem():
        item_dict = _visit_action_body_item(abi_ctx)
        if item_dict:
            items.append(item_dict)
    
    return items


def _visit_action_body_item(abi_ctx):
    """Visit a single actionBodyItem and return an ActionBodyItem dict.
    
    Grammar:
      actionBodyItem
        : nonBehaviorBodyItem
        | initialNodeMember ( actionTargetSuccessionMember)*
        | (sourceSuccessionMember)? actionBehaviorMember (actionTargetSuccessionMember)*
        | guardedSuccessionMember
        ;
    
    The sourceSuccessionMember ('then') is a prefix to actionBehaviorMember.
    """
    if abi_ctx is None:
        return None
    
    # Handle nonBehaviorBodyItem (in/out params, attributes, imports, bindings)
    if hasattr(abi_ctx, 'nonBehaviorBodyItem') and abi_ctx.nonBehaviorBodyItem():
        nbi = abi_ctx.nonBehaviorBodyItem()
        inner = _visit_non_behavior_body_item(nbi)
        if inner:
            return {
                "name": "ActionBodyItem",
                "ownedRelationship": [inner]
            }
    
    # Handle initialNodeMember (first X) with optional actionTargetSuccessionMember (then Y) suffixes
    if hasattr(abi_ctx, 'initialNodeMember') and abi_ctx.initialNodeMember():
        relationships = []
        inm = abi_ctx.initialNodeMember()
        inner = _visit_initial_node_member(inm)
        if inner:
            relationships.append(inner)
        
        # Handle actionTargetSuccessionMember suffixes
        if hasattr(abi_ctx, 'actionTargetSuccessionMember'):
            for atsm in abi_ctx.actionTargetSuccessionMember():
                inner = _visit_action_target_succession_member(atsm)
                if inner:
                    relationships.append(inner)
        
        if relationships:
            return {
                "name": "ActionBodyItem",
                "ownedRelationship": relationships
            }
    
    # Handle actionBehaviorMember (nested actions), possibly with sourceSuccessionMember prefix
    # and actionTargetSuccessionMember suffix
    if hasattr(abi_ctx, 'actionBehaviorMember') and abi_ctx.actionBehaviorMember():
        relationships = []
        # Check for sourceSuccessionMember prefix ('then')
        if hasattr(abi_ctx, 'sourceSuccessionMember') and abi_ctx.sourceSuccessionMember():
            relationships.append({
                "name": "EmptySuccessionMember",
                "ownedRelatedElement": [{
                    "name": "EmptySuccession",
                    "ownedRelationship": []
                }]
            })
        abm = abi_ctx.actionBehaviorMember()
        inner = _visit_action_behavior_member(abm)
        if inner:
            relationships.append(inner)
        
        # Handle actionTargetSuccessionMember suffixes
        if hasattr(abi_ctx, 'actionTargetSuccessionMember'):
            for atsm in abi_ctx.actionTargetSuccessionMember():
                inner = _visit_action_target_succession_member(atsm)
                if inner:
                    relationships.append(inner)
        
        if relationships:
            return {
                "name": "ActionBodyItem",
                "ownedRelationship": relationships
            }
    
    # Handle guardedSuccessionMember
    if hasattr(abi_ctx, 'guardedSuccessionMember') and abi_ctx.guardedSuccessionMember():
        gsm = abi_ctx.guardedSuccessionMember()
        inner = _visit_guarded_succession_member(gsm)
        if inner:
            return {
                "name": "ActionBodyItem",
                "ownedRelationship": [inner]
            }
    
    return None


def _visit_action_behavior_member(abm_ctx):
    """Visit an actionBehaviorMember context and return a member dict.
    
    actionBehaviorMember can be:
    - actionNodeMember (send action, accept action, etc.)
    - behaviorUsageMember (nested action usage)
    """
    if abm_ctx is None:
        return None
    
    # Handle behaviorUsageMember (nested action usage)
    if hasattr(abm_ctx, 'behaviorUsageMember') and abm_ctx.behaviorUsageMember():
        bum = abm_ctx.behaviorUsageMember()
        return _visit_behavior_usage_member(bum)
    
    # Handle actionNodeMember
    if hasattr(abm_ctx, 'actionNodeMember') and abm_ctx.actionNodeMember():
        anm = abm_ctx.actionNodeMember()
        return _visit_action_node_member(anm)
    
    return None


def _visit_source_succession_member(ssm_ctx):
    """Visit a sourceSuccessionMember context.
    
    This handles 'then action ...' constructs and flow connections with succession.
    """
    if ssm_ctx is None:
        return None
    
    result_items = []
    
    # Handle succession (flow connections)
    if hasattr(ssm_ctx, 'succession') and ssm_ctx.succession():
        succ = ssm_ctx.succession()
        inner = _visit_succession(succ)
        if inner:
            result_items.append(inner)
    
    # Handle actionBehaviorMember after 'then'
    if hasattr(ssm_ctx, 'actionBehaviorMember') and ssm_ctx.actionBehaviorMember():
        abm = ssm_ctx.actionBehaviorMember()
        inner = _visit_action_behavior_member(abm)
        if inner:
            result_items.append(inner)
    
    if len(result_items) == 1:
        return {
            "name": "ActionBodyItem",
            "ownedRelationship": result_items[0]
        }
    elif len(result_items) > 1:
        # Return single ActionBodyItem with multiple ownedRelationship items
        return {
            "name": "ActionBodyItem",
            "ownedRelationship": result_items
        }
    
    return None


def _visit_initial_node_member(inm_ctx):
    """Visit an initialNodeMember context and return an InitialNodeMember dict.
    
    initialNodeMember: memberPrefix FIRST qualifiedName relationshipBody
    """
    if inm_ctx is None:
        return None
    
    prefix = None
    if hasattr(inm_ctx, 'memberPrefix') and inm_ctx.memberPrefix():
        mp = inm_ctx.memberPrefix()
        if mp and hasattr(mp, 'visibilityIndicator') and mp.visibilityIndicator():
            prefix = {
                "name": "MemberPrefix",
                "visibility": _visit_visibility_indicator_dict(mp.visibilityIndicator())
            }
    
    name = None
    if hasattr(inm_ctx, 'qualifiedName') and inm_ctx.qualifiedName():
        name = inm_ctx.qualifiedName().getText()

    # relationshipBody may carry its own ";" (e.g. `first A3;` followed by
    # further succession members in the same actionBodyItem).
    has_semi = False
    if hasattr(inm_ctx, 'relationshipBody') and inm_ctx.relationshipBody():
        rb = inm_ctx.relationshipBody()
        if rb.SEMI() is not None:
            has_semi = True

    return {
        "name": "InitialNodeMember",
        "prefix": prefix,
        "ownedRelatedElement": {
            "name": "InitialNode",
            "declaredName": name,
            "hasSemi": has_semi,
            "ownedRelationship": []
        }
    }


def _visit_action_target_succession_member(atsm_ctx):
    """Visit an actionTargetSuccessionMember context and return an ActionTargetSuccessionMember dict.

    actionTargetSuccessionMember: memberPrefix actionTargetSuccession
    actionTargetSuccession: (targetSuccession | guardedTargetSuccession | defaultTargetSuccession) usageBody
    targetSuccession: sourceEndMember THEN connectorEndMember
    defaultTargetSuccession: ELSE transitionSuccessionMember
    """
    if atsm_ctx is None:
        return None

    prefix = None
    if hasattr(atsm_ctx, 'memberPrefix') and atsm_ctx.memberPrefix():
        mp = atsm_ctx.memberPrefix()
        if mp and hasattr(mp, 'visibilityIndicator') and mp.visibilityIndicator():
            prefix = {
                "name": "MemberPrefix",
                "visibility": _visit_visibility_indicator_dict(mp.visibilityIndicator())
            }

    keyword = "then"
    name = None
    condition = None
    has_semi = False
    if hasattr(atsm_ctx, 'actionTargetSuccession') and atsm_ctx.actionTargetSuccession():
        ats = atsm_ctx.actionTargetSuccession()

        def _usage_body_has_semi(ats):
            ub = ats.usageBody() if hasattr(ats, 'usageBody') else None
            if ub is not None:
                db = ub.definitionBody() if hasattr(ub, 'definitionBody') else None
                if db is not None and hasattr(db, 'SEMI') and db.SEMI():
                    return True
            return False

        # `else done` form (defaultTargetSuccession)
        if hasattr(ats, 'defaultTargetSuccession') and ats.defaultTargetSuccession():
            keyword = "else"
            dts = ats.defaultTargetSuccession()
            has_semi = _usage_body_has_semi(ats)
            if hasattr(dts, 'transitionSuccessionMember') and dts.transitionSuccessionMember():
                tsm2 = dts.transitionSuccessionMember()
                if hasattr(tsm2, 'transitionSuccession') and tsm2.transitionSuccession():
                    ts2 = tsm2.transitionSuccession()
                    if hasattr(ts2, 'connectorEndMember') and ts2.connectorEndMember():
                        cem2 = ts2.connectorEndMember()
                        if cem2 is not None:
                            name = _extract_connector_end_name(cem2)
        # `if <cond> then X` form (guardedTargetSuccession)
        elif hasattr(ats, 'guardedTargetSuccession') and ats.guardedTargetSuccession():
            gts = ats.guardedTargetSuccession()
            has_semi = _usage_body_has_semi(ats)
            if hasattr(gts, 'guardExpressionMember') and gts.guardExpressionMember():
                gem = gts.guardExpressionMember()
                if hasattr(gem, 'ownedExpression') and gem.ownedExpression():
                    condition = gem.ownedExpression().getText()
            if hasattr(gts, 'transitionSuccessionMember') and gts.transitionSuccessionMember():
                tsm3 = gts.transitionSuccessionMember()
                if hasattr(tsm3, 'transitionSuccession') and tsm3.transitionSuccession():
                    ts3 = tsm3.transitionSuccession()
                    if hasattr(ts3, 'connectorEndMember') and ts3.connectorEndMember():
                        cem3 = ts3.connectorEndMember()
                        if cem3 is not None:
                            name = _extract_connector_end_name(cem3)
        # Standard `then X` form (targetSuccession)
        elif hasattr(ats, 'targetSuccession') and ats.targetSuccession():
            ts = ats.targetSuccession()
            has_semi = _usage_body_has_semi(ats)
            if hasattr(ts, 'connectorEndMember') and ts.connectorEndMember():
                cem = ts.connectorEndMember()
                if cem is not None:
                    name = _extract_connector_end_name(cem)

    return {
        "name": "ActionTargetSuccessionMember",
        "prefix": prefix,
        "ownedRelatedElement": {
            "name": "ActionTargetSuccession",
            "keyword": keyword,
            "declaredName": name,
            "condition": condition,
            "hasSemi": has_semi,
            "ownedRelationship": []
        }
    }


def _extract_connector_end_name(ce_member_ctx):
    """Extract the target feature text from a connectorEndMember.

    Handles plain names (connectorEnd.name), qualified references via
    ownedReferenceSubsetting, and feature chains.
    """
    if ce_member_ctx is None:
        return None
    ce = None
    if hasattr(ce_member_ctx, 'connectorEnd'):
        ce = ce_member_ctx.connectorEnd()
    if ce is None:
        return None

    if hasattr(ce, 'name') and ce.name():
        return ce.name().getText()

    # `then m` / `then some.chain` carry an ownedReferenceSubsetting whose
    # qualifiedName holds the target (possibly dotted).
    if hasattr(ce, 'ownedReferenceSubsetting') and ce.ownedReferenceSubsetting():
        return ce.ownedReferenceSubsetting().getText()

    return None


def _visit_guarded_succession_member(gsm_ctx):
    """Visit a guardedSuccessionMember context and return a GuardedSuccessionMember dict.
    
    guardedSuccessionMember: memberPrefix guardedSuccession
    guardedSuccession: (SUCCESSION usageDeclaration?)? FIRST featureChainMember guardExpressionMember THEN transitionSuccessionMember usageBody
    """
    if gsm_ctx is None:
        return None
    
    prefix = None
    if hasattr(gsm_ctx, 'memberPrefix') and gsm_ctx.memberPrefix():
        mp = gsm_ctx.memberPrefix()
        if mp and hasattr(mp, 'visibilityIndicator') and mp.visibilityIndicator():
            prefix = {
                "name": "MemberPrefix",
                "visibility": _visit_visibility_indicator_dict(mp.visibilityIndicator())
            }
    
    keyword = "succession"
    declared_name = None
    has_semi = False
    source_name = None
    condition = None
    target_name = None
    
    if hasattr(gsm_ctx, 'guardedSuccession') and gsm_ctx.guardedSuccession():
        gs = gsm_ctx.guardedSuccession()
        
        # Extract source name from featureChainMember (qualified name chain)
        if hasattr(gs, 'featureChainMember') and gs.featureChainMember():
            source_name = gs.featureChainMember().getText()
        
        # Extract condition from guardExpressionMember (if expression)
        if hasattr(gs, 'guardExpressionMember') and gs.guardExpressionMember():
            gem = gs.guardExpressionMember()
            if hasattr(gem, 'ownedExpression') and gem.ownedExpression():
                condition = gem.ownedExpression().getText()
        
        # Extract declared name from optional usageDeclaration (`succession S ...`)
        if hasattr(gs, 'usageDeclaration') and gs.usageDeclaration():
            ud = gs.usageDeclaration()
            if hasattr(ud, 'identification') and ud.identification():
                ident = ud.identification()
                if hasattr(ident, 'name') and ident.name():
                    declared_name = ident.name()[-1].getText()

        # Extract target name from transitionSuccessionMember
        if hasattr(gs, 'transitionSuccessionMember') and gs.transitionSuccessionMember():
            tsm = gs.transitionSuccessionMember()
            if hasattr(tsm, 'transitionSuccession') and tsm.transitionSuccession():
                ts = tsm.transitionSuccession()
                if hasattr(ts, 'connectorEndMember') and ts.connectorEndMember():
                    target_name = _extract_connector_end_name(ts.connectorEndMember())

        # Whether the trailing usageBody carries its own ";"
        ub = gs.usageBody() if hasattr(gs, 'usageBody') else None
        if ub is not None:
            db = ub.definitionBody() if hasattr(ub, 'definitionBody') else None
            if db is not None and hasattr(db, 'SEMI') and db.SEMI():
                has_semi = True

    return {
        "name": "GuardedSuccessionMember",
        "prefix": prefix,
        "ownedRelatedElement": {
            "name": "GuardedSuccession",
            "keyword": keyword,
            "declaredName": declared_name,
            "sourceName": source_name,
            "condition": condition,
            "targetName": target_name,
            "hasSemi": has_semi,
            "ownedRelationship": []
        }
    }


def _visit_behavior_usage_member(bum_ctx):
    """Visit a behaviorUsageMember context (nested action usage).
    
    behaviorUsageMember: memberPrefix behaviorUsageElement
    """
    if bum_ctx is None:
        return None
    
    prefix = None
    if hasattr(bum_ctx, 'memberPrefix') and bum_ctx.memberPrefix():
        mp = bum_ctx.memberPrefix()
        if mp and hasattr(mp, 'visibilityIndicator') and mp.visibilityIndicator():
            prefix = {
                "name": "MemberPrefix",
                "visibility": _visit_visibility_indicator_dict(mp.visibilityIndicator())
            }
    
    if hasattr(bum_ctx, 'behaviorUsageElement') and bum_ctx.behaviorUsageElement():
        bue = bum_ctx.behaviorUsageElement()
        if hasattr(bue, 'actionUsage') and bue.actionUsage():
            ctx = bue.actionUsage()
            return _make_action_usage_element(ctx, prefix)
        elif hasattr(bue, 'calculationUsage') and bue.calculationUsage():
            ctx = bue.calculationUsage()
            result = _make_calculation_usage_dict(ctx, prefix)
            if result and result.get("name") == "PackageMember":
                # Wrap as BehaviorUsageMember for action body
                ue = result.get("ownedRelatedElement", {})
                if ue.get("name") == "UsageElement":
                    occ = ue.get("ownedRelatedElement", {})
                    if occ.get("name") == "OccurrenceUsageElement":
                        return {
                            "name": "BehaviorUsageMember",
                            "prefix": prefix,
                            "ownedRelatedElement": occ.get("ownedRelatedElement")
                        }
            return result
        elif hasattr(bue, 'constraintUsage') and bue.constraintUsage():
            ctx = bue.constraintUsage()
            result = _make_constraint_usage_dict(ctx, prefix)
            if result and result.get("name") == "PackageMember":
                ue = result.get("ownedRelatedElement", {})
                if ue.get("name") == "UsageElement":
                    occ = ue.get("ownedRelatedElement", {})
                    if occ.get("name") == "OccurrenceUsageElement":
                        return {
                            "name": "BehaviorUsageMember",
                            "prefix": prefix,
                            "ownedRelatedElement": occ.get("ownedRelatedElement")
                        }
            return result
        elif hasattr(bue, 'assertConstraintUsage') and bue.assertConstraintUsage():
            return _make_assert_constraint_usage_dict(bue.assertConstraintUsage(), prefix)
        elif hasattr(bue, 'satisfyRequirementUsage') and bue.satisfyRequirementUsage():
            return _make_satisfy_requirement_usage_dict(bue.satisfyRequirementUsage(), prefix)
    
    return None


def _make_assert_constraint_usage_dict(acu_ctx, prefix=None):
    """Create an AssertConstraintUsage dictionary.
    
    Grammar:
      assertConstraintUsage
        : occurrenceUsagePrefix ASSERT (NOT)? (
            ownedReferenceSubsetting featureSpecializationPart?
            | CONSTRAINT constraintUsageDeclaration
          ) calculationBody
        ;
    """
    if acu_ctx is None:
        return None
    
    is_negated = False
    occ_prefix = _get_occurrence_usage_prefix(acu_ctx)
    
    if hasattr(acu_ctx, 'NOT') and acu_ctx.NOT():
        is_negated = True
    
    body_parts = _visit_calculation_body_items(acu_ctx)
    
    owned_relationship = []
    fsp = None
    
    if hasattr(acu_ctx, 'ownedReferenceSubsetting') and acu_ctx.ownedReferenceSubsetting():
        ors = _build_owned_reference_subsetting_dict(acu_ctx.ownedReferenceSubsetting())
        if ors:
            owned_relationship.append(ors)
        
        if hasattr(acu_ctx, 'featureSpecializationPart') and acu_ctx.featureSpecializationPart():
            fsp_ctx = acu_ctx.featureSpecializationPart()
            fsp = _build_full_specialization_from_fsp(fsp_ctx)
    
    declaration = None
    if hasattr(acu_ctx, 'constraintUsageDeclaration') and acu_ctx.constraintUsageDeclaration():
        cud = acu_ctx.constraintUsageDeclaration()
        name = None
        shortname = None
        typed_by = None
        
        if hasattr(cud, 'usageDeclaration') and cud.usageDeclaration():
            ud = cud.usageDeclaration()
            if hasattr(ud, 'identification') and ud.identification():
                ident = ud.identification()
                if hasattr(ident, 'name'):
                    name_list = ident.name()
                    if name_list and isinstance(name_list, list):
                        if len(name_list) == 2:
                            shortname = name_list[0].getText()
                            name = name_list[1].getText()
                        elif len(name_list) == 1:
                            name_text = name_list[0].getText()
                            name, shortname = _extract_name_shortname(name_text)
            
            typed_by = _get_action_usage_typed_by(cud)
            if typed_by is None:
                typed_by = _get_action_usage_subsetted_by(cud)
        
        specialization = _build_specialization(typed_by) if typed_by else None
        
        valuepart = None
        if hasattr(cud, 'valuePart') and cud.valuePart():
            vp = cud.valuePart()
            if hasattr(vp, 'ownedExpression') and vp.ownedExpression():
                expr = _visit_expression(vp.ownedExpression())
                if expr:
                    valuepart = {"name": "ValuePart", "ownedRelationship": expr}
        
        declaration = {
            "name": "UsageDeclaration",
            "declaration": {
                "name": "FeatureDeclaration",
                "identification": {
                    "name": "Identification",
                    "declaredShortName": shortname,
                    "declaredName": name
                },
                "specialization": specialization
            }
        }
        
        if valuepart:
            declaration["valuepart"] = valuepart
    
    return {
        "name": "AssertConstraintUsage",
        "prefix": occ_prefix or prefix,
        "isNegated": is_negated,
        "ownedRelationship": owned_relationship,
        "featurespecializationpart": fsp,
        "declaration": declaration,
        "body": {
            "name": "CalculationBody",
            "part": body_parts
        }
    }


def _make_satisfy_requirement_usage_dict(sru_ctx, prefix=None):
    """Create a SatisfyRequirementUsage dictionary.
    
    Grammar:
      satisfyRequirementUsage
        : occurrenceUsagePrefix (ASSERT ( NOT)? | NOT)? SATISFY (
            ownedReferenceSubsetting featureSpecializationPart?
            | REQUIREMENT usageDeclaration?
          ) valuePart? (BY satisfactionSubjectMember)? requirementBody
        ;
    """
    if sru_ctx is None:
        return None
    
    is_assert = False
    is_negated = False
    occ_prefix = _get_occurrence_usage_prefix(sru_ctx)
    
    # Check for ASSERT ( NOT)? | NOT
    if hasattr(sru_ctx, 'ASSERT') and sru_ctx.ASSERT():
        is_assert = True
        if hasattr(sru_ctx, 'NOT') and sru_ctx.NOT():
            is_negated = True
    elif hasattr(sru_ctx, 'NOT') and sru_ctx.NOT():
        is_negated = True
    
    # Determine if using ownedReferenceSubsetting or REQUIREMENT keyword
    ors = None
    fsp = None
    declaration = None
    
    if hasattr(sru_ctx, 'ownedReferenceSubsetting') and sru_ctx.ownedReferenceSubsetting():
        ors = _build_owned_reference_subsetting_dict(sru_ctx.ownedReferenceSubsetting())
        
        if hasattr(sru_ctx, 'featureSpecializationPart') and sru_ctx.featureSpecializationPart():
            fsp_ctx = sru_ctx.featureSpecializationPart()
            fsp = _build_full_specialization_from_fsp(fsp_ctx)
    elif hasattr(sru_ctx, 'REQUIREMENT') and sru_ctx.REQUIREMENT():
        if hasattr(sru_ctx, 'usageDeclaration') and sru_ctx.usageDeclaration():
            ud = sru_ctx.usageDeclaration()
            name = None
            shortname = None
            typed_by = None
            
            if hasattr(ud, 'identification') and ud.identification():
                ident = ud.identification()
                if hasattr(ident, 'name'):
                    name_list = ident.name()
                    if name_list and isinstance(name_list, list):
                        if len(name_list) == 2:
                            shortname = name_list[0].getText()
                            name = name_list[1].getText()
                        elif len(name_list) == 1:
                            name_text = name_list[0].getText()
                            name, shortname = _extract_name_shortname(name_text)
            
            typed_by = _get_action_usage_typed_by(sru_ctx)
            if typed_by is None:
                typed_by = _get_action_usage_subsetted_by(sru_ctx)
            
            specialization = _build_specialization(typed_by) if typed_by else None
            
            declaration = {
                "name": "UsageDeclaration",
                "declaration": {
                    "name": "FeatureDeclaration",
                    "identification": {
                        "name": "Identification",
                        "declaredShortName": shortname,
                        "declaredName": name
                    },
                    "specialization": specialization
                }
            }
    
    # Extract valuePart
    valuepart = None
    if hasattr(sru_ctx, 'valuePart') and sru_ctx.valuePart():
        vp = sru_ctx.valuePart()
        if hasattr(vp, 'ownedExpression') and vp.ownedExpression():
            expr = _visit_expression(vp.ownedExpression())
            if expr:
                valuepart = {"name": "ValuePart", "ownedRelationship": expr}
    
    # Extract satisfactionSubjectMember (after 'by')
    ssm = None
    if hasattr(sru_ctx, 'satisfactionSubjectMember') and sru_ctx.satisfactionSubjectMember():
        ssm_ctx = sru_ctx.satisfactionSubjectMember()
        ssm = _visit_satisfaction_subject_member(ssm_ctx)
    
    # Extract requirementBody
    body = _visit_requirement_body(sru_ctx)
    
    return {
        "name": "SatisfyRequirementUsage",
        "prefix": occ_prefix or prefix,
        "isAssert": is_assert,
        "isNegated": is_negated,
        "ors": ors,
        "fsp": fsp,
        "declaration": declaration,
        "valuepart": valuepart,
        "ssm": ssm,
        "body": body
    }


def _visit_satisfaction_subject_member(ssm_ctx):
    """Visit a satisfactionSubjectMember context.
    
    Grammar:
      satisfactionSubjectMember : satisfactionParameter ;
      satisfactionParameter : satisfactionFeatureValue ;
      satisfactionFeatureValue : ownedRelatedElement = SatisfactionReferenceExpression ;
      SatisfactionReferenceExpression : ownedRelatedElement = FeatureChainMember ;
    """
    if ssm_ctx is None:
        return None
    
    if hasattr(ssm_ctx, 'satisfactionParameter') and ssm_ctx.satisfactionParameter():
        sp_ctx = ssm_ctx.satisfactionParameter()
        if hasattr(sp_ctx, 'satisfactionFeatureValue') and sp_ctx.satisfactionFeatureValue():
            sfv_ctx = sp_ctx.satisfactionFeatureValue()
            
            # Try to extract qualified name from SatisfactionReferenceExpression
            for child in sfv_ctx.getChildren():
                child_name = type(child).__name__
                if 'Reference' in child_name or 'Expression' in child_name:
                    qn_text = child.getText()
                    return {
                        "name": "SatisfactionSubjectMember",
                        "ownedRelatedElement": {
                            "name": "SatisfactionParameter",
                            "ownedRelationship": {
                                "name": "SatisfactionFeatureValue",
                                "ownedRelatedElement": {
                                    "name": "SatisfactionReferenceExpression",
                                    "ownedRelatedElement": {
                                        "name": "FeatureChainMember",
                                        "memberElement": {
                                            "name": "QualifiedName",
                                            "names": [qn_text]
                                        }
                                    }
                                }
                            }
                        }
                    }
    
    return None


def _visit_requirement_body(ctx):
    """Visit a requirementBody context.
    
    Grammar:
      requirementBody
        : LBRACE requirementBodyItem* RBRACE
        | SEMI
        ;
    """
    if ctx is None:
        return {"name": "RequirementBody", "ownedRelationship": []}
    
    if hasattr(ctx, 'requirementBodyItem') and ctx.requirementBodyItem():
        items = ctx.requirementBodyItem()
        if not isinstance(items, list):
            items = [items]
        owned_relationship = []
        for item in items:
            result = _visit_requirement_body_item(item)
            if result:
                owned_relationship.append(result)
        return {"name": "RequirementBody", "ownedRelationship": owned_relationship}
    
    return {"name": "RequirementBody", "ownedRelationship": []}


def _visit_requirement_body_item(item_ctx):
    """Visit a requirementBodyItem context."""
    if item_ctx is None:
        return None
    
    # Check for various usage types inside requirement body
    if hasattr(item_ctx, 'behaviorUsageMember') and item_ctx.behaviorUsageMember():
        return _visit_behavior_usage_member(item_ctx.behaviorUsageMember())
    
    return None


def _visit_action_node_member(anm_ctx):
    """Visit an actionNodeMember context (send action, accept action, if/while/for/control, etc.)."""
    if anm_ctx is None:
        return None
    
    # Extract memberPrefix
    prefix = None
    if hasattr(anm_ctx, 'memberPrefix') and anm_ctx.memberPrefix():
        mp = anm_ctx.memberPrefix()
        if hasattr(mp, 'visibilityIndicator') and mp.visibilityIndicator():
            prefix = {
                "name": "MemberPrefix",
                "visibility": _visit_visibility_indicator_dict(mp.visibilityIndicator())
            }
    
    # Dispatch through actionNode for control flow nodes
    if hasattr(anm_ctx, 'actionNode') and anm_ctx.actionNode():
        an = anm_ctx.actionNode()
        node_dict = _visit_action_node(an)
        if node_dict:
            return {
                "name": "ActionNodeMember",
                "prefix": prefix,
                "ownedRelatedElement": {
                    "name": "ActionNode",
                    "node": node_dict
                }
            }
    
    return None


def _visit_action_node(an_ctx):
    """Visit an actionNode context and return the inner node dict."""
    if an_ctx is None:
        return None
    
    if hasattr(an_ctx, 'sendNode') and an_ctx.sendNode():
        return _visit_send_node(an_ctx.sendNode())
    
    if hasattr(an_ctx, 'acceptNode') and an_ctx.acceptNode():
        return _visit_accept_node(an_ctx.acceptNode())
    
    if hasattr(an_ctx, 'assignmentNode') and an_ctx.assignmentNode():
        return _visit_assignment_node(an_ctx.assignmentNode())
    
    if hasattr(an_ctx, 'terminateNode') and an_ctx.terminateNode():
        return _visit_terminate_node(an_ctx.terminateNode())
    
    if hasattr(an_ctx, 'ifNode') and an_ctx.ifNode():
        return _visit_if_node(an_ctx.ifNode())
    
    if hasattr(an_ctx, 'whileLoopNode') and an_ctx.whileLoopNode():
        return _visit_while_loop_node(an_ctx.whileLoopNode())
    
    if hasattr(an_ctx, 'forLoopNode') and an_ctx.forLoopNode():
        return _visit_for_loop_node(an_ctx.forLoopNode())
    
    if hasattr(an_ctx, 'controlNode') and an_ctx.controlNode():
        return _visit_control_node(an_ctx.controlNode())
    
    return None


def _visit_action_body_parameter(ctx):
    """Visit an actionBodyParameter context and return an ActionBody dict.
    
    actionBodyParameter: (ACTION usageDeclaration?)? LBRACE actionBodyItem* RBRACE
    """
    if ctx is None:
        return {"name": "ActionBody", "item": []}
    
    items = []
    if hasattr(ctx, 'actionBodyItem'):
        body_items = ctx.actionBodyItem()
        if body_items and isinstance(body_items, list):
            for item_ctx in body_items:
                item_dict = _visit_action_body_item(item_ctx)
                if item_dict:
                    items.append(item_dict)
    
    return {"name": "ActionBody", "item": items}


def _visit_if_node(ctx):
    """Visit an ifNode context.
    
    ifNode: actionNodePrefix IF expressionParameterMember actionBodyParameterMember
            (ELSE (actionBodyParameterMember | ifNodeParameterMember))?
    
    expressionParameterMember: ownedExpression
    actionBodyParameterMember: actionBodyParameter
    actionBodyParameter: (ACTION usageDeclaration?)? LBRACE actionBodyItem* RBRACE
    ifNodeParameterMember: ifNode
    """
    if ctx is None:
        return None
    
    result = {
        "name": "IfNode",
        "prefix": None,
        "condition": None,
        "thenBody": None,
        "elseBody": None,
        "elseIf": None
    }
    
    # Extract prefix from actionNodePrefix
    if hasattr(ctx, 'actionNodePrefix') and ctx.actionNodePrefix():
        anp = ctx.actionNodePrefix()
        result["prefix"] = _get_occurrence_usage_prefix(anp)
    
    # Extract condition from expressionParameterMember
    if hasattr(ctx, 'expressionParameterMember') and ctx.expressionParameterMember():
        epm = ctx.expressionParameterMember()
        if hasattr(epm, 'ownedExpression') and epm.ownedExpression():
            result["condition"] = epm.ownedExpression().getText()
    
    # Extract then-body from actionBodyParameterMember(0)
    bodies = None
    if hasattr(ctx, 'actionBodyParameterMember'):
        bodies = ctx.actionBodyParameterMember()
        if bodies and len(bodies) > 0:
            abp = bodies[0]
            if hasattr(abp, 'actionBodyParameter') and abp.actionBodyParameter():
                result["thenBody"] = _visit_action_body_parameter(abp.actionBodyParameter())
    
    # Handle optional ELSE clause
    if hasattr(ctx, 'ELSE') and ctx.ELSE():
        if bodies and len(bodies) > 1:
            abp = bodies[1]
            if hasattr(abp, 'actionBodyParameter') and abp.actionBodyParameter():
                result["elseBody"] = _visit_action_body_parameter(abp.actionBodyParameter())
        elif hasattr(ctx, 'ifNodeParameterMember') and ctx.ifNodeParameterMember():
            inpm = ctx.ifNodeParameterMember()
            if hasattr(inpm, 'ifNode') and inpm.ifNode():
                result["elseIf"] = _visit_if_node(inpm.ifNode())
    
    return result


def _visit_while_loop_node(ctx):
    """Visit a whileLoopNode context.
    
    whileLoopNode: actionNodePrefix
                   (WHILE expressionParameterMember | LOOP emptyParameterMember)
                   actionBodyParameterMember
                   (UNTIL expressionParameterMember SEMI)?
    """
    if ctx is None:
        return None
    
    result = {
        "name": "WhileLoopNode",
        "prefix": None,
        "keyword": "while",
        "condition": None,
        "body": None,
        "until": None
    }
    
    if hasattr(ctx, 'actionNodePrefix') and ctx.actionNodePrefix():
        result["prefix"] = _get_occurrence_usage_prefix(ctx.actionNodePrefix())
    
    if hasattr(ctx, 'WHILE') and ctx.WHILE():
        result["keyword"] = "while"
        if hasattr(ctx, 'expressionParameterMember'):
            epms = ctx.expressionParameterMember()
            if epms and len(epms) > 0:
                epm = epms[0]
                if hasattr(epm, 'ownedExpression') and epm.ownedExpression():
                    result["condition"] = epm.ownedExpression().getText()
    elif hasattr(ctx, 'LOOP') and ctx.LOOP():
        result["keyword"] = "loop"
    
    if hasattr(ctx, 'actionBodyParameterMember') and ctx.actionBodyParameterMember():
        abpm = ctx.actionBodyParameterMember()
        if hasattr(abpm, 'actionBodyParameter') and abpm.actionBodyParameter():
            result["body"] = _visit_action_body_parameter(abpm.actionBodyParameter())
    
    if hasattr(ctx, 'UNTIL') and ctx.UNTIL():
        if hasattr(ctx, 'expressionParameterMember'):
            epms = ctx.expressionParameterMember()
            if epms and len(epms) > 0:
                # The last expression parameter member is the UNTIL condition
                epm = epms[-1]
                if hasattr(epm, 'ownedExpression') and epm.ownedExpression():
                    until_text = epm.ownedExpression().getText()
                    if until_text and until_text.strip():
                        result["until"] = until_text.strip()
                        # Also strip trailing semicolon that might come from getText
                        if result["until"].endswith(';'):
                            result["until"] = result["until"][:-1].strip()
    
    return result


def _visit_for_loop_node(ctx):
    """Visit a forLoopNode context.
    
    forLoopNode: actionNodePrefix
                 FOR forVariableDeclarationMember IN nodeParameterMember
                 actionBodyParameterMember
    """
    if ctx is None:
        return None
    
    result = {
        "name": "ForLoopNode",
        "prefix": None,
        "variable": None,
        "collection": None,
        "body": None
    }
    
    if hasattr(ctx, 'actionNodePrefix') and ctx.actionNodePrefix():
        result["prefix"] = _get_occurrence_usage_prefix(ctx.actionNodePrefix())
    
    if hasattr(ctx, 'forVariableDeclarationMember') and ctx.forVariableDeclarationMember():
        fvdm = ctx.forVariableDeclarationMember()
        text_val = None
        if hasattr(fvdm, 'usageDeclaration') and fvdm.usageDeclaration():
            text_val = fvdm.usageDeclaration().getText()
        else:
            text_val = fvdm.getText()
        if text_val and text_val.strip():
            result["variable"] = text_val.strip()
    
    if hasattr(ctx, 'nodeParameterMember') and ctx.nodeParameterMember():
        npm = ctx.nodeParameterMember()
        text_val = npm.getText()
        if text_val and text_val.strip():
            result["collection"] = text_val.strip()
    
    if hasattr(ctx, 'actionBodyParameterMember') and ctx.actionBodyParameterMember():
        abpm = ctx.actionBodyParameterMember()
        if hasattr(abpm, 'actionBodyParameter') and abpm.actionBodyParameter():
            result["body"] = _visit_action_body_parameter(abpm.actionBodyParameter())
    
    return result


def _visit_control_node(ctx):
    """Visit a controlNode context.
    
    controlNode: mergeNode | decisionNode | joinNode | forkNode
    
    Each sub-node has: controlNodePrefix keyword (usageDeclaration)? actionBody
    """
    if ctx is None:
        return None
    
    result = {
        "name": "ControlNode",
        "prefix": None,
        "keyword": None,
        "declaredName": None,
        "body": None
    }

    sub = None
    if hasattr(ctx, 'mergeNode') and ctx.mergeNode():
        sub = ctx.mergeNode()
        result["keyword"] = "merge"
    elif hasattr(ctx, 'decisionNode') and ctx.decisionNode():
        sub = ctx.decisionNode()
        result["keyword"] = "decide"
    elif hasattr(ctx, 'joinNode') and ctx.joinNode():
        sub = ctx.joinNode()
        result["keyword"] = "join"
    elif hasattr(ctx, 'forkNode') and ctx.forkNode():
        sub = ctx.forkNode()
        result["keyword"] = "fork"

    if sub is not None:
        if hasattr(sub, 'controlNodePrefix') and sub.controlNodePrefix():
            result["prefix"] = _get_occurrence_usage_prefix(sub.controlNodePrefix())
        if hasattr(sub, 'usageDeclaration') and sub.usageDeclaration():
            ud = sub.usageDeclaration()
            if hasattr(ud, 'identification') and ud.identification():
                ident = ud.identification()
                if hasattr(ident, 'name') and ident.name():
                    name_list = ident.name()
                    result["declaredName"] = name_list[-1].getText()
        if hasattr(sub, 'actionBody') and sub.actionBody():
            result["body"] = _visit_action_body(sub.actionBody())

    return result


def _visit_send_node(ctx):
    """Visit a sendNode context.

    sendNode: occurrenceUsagePrefix
              (actionNodeUsageDeclaration | actionUsageDeclaration)
              SEND
              (nodeParameterMember senderReceiverPart? | emptyParameterMember senderReceiverPart?)
              actionBody
    """
    if ctx is None:
        return None

    prefix = _get_occurrence_usage_prefix(ctx)

    # Build declaration dict matching SendNodeDeclaration shape
    decl = None
    action_node_decl = None
    if hasattr(ctx, 'actionNodeUsageDeclaration') and ctx.actionNodeUsageDeclaration():
        aud = ctx.actionNodeUsageDeclaration()
        action_node_decl = {
            "name": "ActionNodeUsageDeclaration",
            "declaration": None
        }
        if hasattr(aud, 'usageDeclaration') and aud.usageDeclaration():
            ud = aud.usageDeclaration()
            if ud:
                name, shortname = _get_usage_identification_from_ud(ud)
                action_node_decl["declaration"] = {
                    "name": "UsageDeclaration",
                    "declaration": {
                        "name": "FeatureDeclaration",
                        "identification": {
                            "name": "Identification",
                            "declaredShortName": shortname,
                            "declaredName": name
                        },
                        "specialization": None
                    }
                }
    elif hasattr(ctx, 'actionUsageDeclaration') and ctx.actionUsageDeclaration():
        aud = ctx.actionUsageDeclaration()
        action_node_decl = {
            "name": "ActionNodeUsageDeclaration",
            "declaration": None
        }
        if hasattr(aud, 'usageDeclaration') and aud.usageDeclaration():
            ud = aud.usageDeclaration()
            if ud:
                name, shortname = _get_usage_identification_from_ud(ud)
                action_node_decl["declaration"] = {
                    "name": "UsageDeclaration",
                    "declaration": {
                        "name": "FeatureDeclaration",
                        "identification": {
                            "name": "Identification",
                            "declaredShortName": shortname,
                            "declaredName": name
                        },
                        "specialization": None
                    }
                }

    node_param = None
    if hasattr(ctx, 'nodeParameterMember') and ctx.nodeParameterMember():
        node_param = _visit_node_parameter_member(ctx.nodeParameterMember())

    sender_receiver = None
    if hasattr(ctx, 'senderReceiverPart') and ctx.senderReceiverPart():
        sender_receiver = _visit_sender_receiver_part(ctx.senderReceiverPart())

    decl = {
        "name": "SendNodeDeclaration",
        "declaration": action_node_decl,
        "nodeParameter": node_param,
        "senderReceiver": sender_receiver
    }

    body = None
    if hasattr(ctx, 'actionBody') and ctx.actionBody():
        body = _visit_action_body(ctx.actionBody())

    return {
        "name": "SendNode",
        "prefix": prefix,
        "declaration": decl,
        "body": body
    }


def _visit_accept_node(ctx):
    """Visit an acceptNode context.

    acceptNode: occurrenceUsagePrefix acceptNodeDeclaration actionBody
    acceptNodeDeclaration: (actionNodeUsageDeclaration)? ACCEPT acceptParameterPart
    """
    if ctx is None:
        return None

    prefix = _get_occurrence_usage_prefix(ctx)

    decl = None
    if hasattr(ctx, 'acceptNodeDeclaration') and ctx.acceptNodeDeclaration():
        decl = _visit_accept_node_declaration(ctx.acceptNodeDeclaration())

    body = None
    if hasattr(ctx, 'actionBody') and ctx.actionBody():
        body = _visit_action_body(ctx.actionBody())

    return {
        "name": "AcceptNode",
        "prefix": prefix,
        "declaration": decl,
        "body": body
    }


def _visit_assignment_node(ctx):
    """Visit an assignmentNode context.

    assignmentNode: occurrenceUsagePrefix assignmentNodeDeclaration actionBody
    assignmentNodeDeclaration: (actionNodeUsageDeclaration)? ASSIGN assignmentTargetMember featureChainMember COLON_EQ nodeParameterMember
    """
    if ctx is None:
        return None

    prefix = _get_occurrence_usage_prefix(ctx)

    decl = None
    if hasattr(ctx, 'assignmentNodeDeclaration') and ctx.assignmentNodeDeclaration():
        decl = _visit_assignment_node_declaration(ctx.assignmentNodeDeclaration())

    body = None
    if hasattr(ctx, 'actionBody') and ctx.actionBody():
        body = _visit_action_body(ctx.actionBody())

    return {
        "name": "AssignmentNode",
        "prefix": prefix,
        "declaration": decl,
        "body": body
    }


def _visit_terminate_node(ctx):
    """Visit a terminateNode context.

    terminateNode: occurrenceUsagePrefix actionNodeUsageDeclaration? TERMINATE nodeParameterMember? actionBody
    """
    if ctx is None:
        return None

    prefix = _get_occurrence_usage_prefix(ctx)

    action_node_decl = None
    if hasattr(ctx, 'actionNodeUsageDeclaration') and ctx.actionNodeUsageDeclaration():
        aud = ctx.actionNodeUsageDeclaration()
        action_node_decl = {
            "name": "ActionNodeUsageDeclaration",
            "declaration": None
        }
        if hasattr(aud, 'usageDeclaration') and aud.usageDeclaration():
            ud = aud.usageDeclaration()
            if ud:
                name, shortname = _get_usage_identification_from_ud(ud)
                action_node_decl["declaration"] = {
                    "name": "UsageDeclaration",
                    "declaration": {
                        "name": "FeatureDeclaration",
                        "identification": {
                            "name": "Identification",
                            "declaredShortName": shortname,
                            "declaredName": name
                        },
                        "specialization": None
                    }
                }

    target = None
    if hasattr(ctx, 'nodeParameterMember') and ctx.nodeParameterMember():
        target = _visit_node_parameter_member(ctx.nodeParameterMember())

    body = None
    if hasattr(ctx, 'actionBody') and ctx.actionBody():
        body = _visit_action_body(ctx.actionBody())

    return {
        "name": "TerminateNode",
        "prefix": prefix,
        "declaration": action_node_decl,
        "target": target,
        "body": body
    }


def _visit_succession(succ_ctx):
    """Visit a succession context (flow connections)."""
    if succ_ctx is None:
        return None
    
    # Handle succession usage
    if hasattr(succ_ctx, 'successionUsage') and succ_ctx.successionUsage():
        return _make_succession_usage_dict(succ_ctx.successionUsage())
    
    return None


def _make_action_usage_element(ctx, member_prefix=None):
    """Create an action usage element dictionary from an actionUsage context.

    This is used for nested action usages inside action bodies.
    """
    if ctx is None:
        return None

    occ_prefix = _get_occurrence_usage_prefix(ctx)
    name = None
    shortname = None
    typed_by = None

    # Get name from actionUsageDeclaration -> usageDeclaration -> identification
    if ctx.actionUsageDeclaration():
        aud = ctx.actionUsageDeclaration()
        if hasattr(aud, 'usageDeclaration') and aud.usageDeclaration():
            ud = aud.usageDeclaration()
            if isinstance(ud, list):
                ud = ud[0] if ud else None
            if ud and hasattr(ud, 'identification') and ud.identification():
                ident = ud.identification()
                if hasattr(ident, 'name'):
                    name_list = ident.name()
                    if name_list and isinstance(name_list, list):
                        if len(name_list) == 2:
                            shortname = name_list[0].getText()
                            name = name_list[1].getText()
                        elif len(name_list) == 1:
                            name_text = name_list[0].getText()
                            name, shortname = _extract_name_shortname(name_text)
                # Extract typed_by for the specialization
                typed_by = _get_action_usage_typed_by(ctx)
                if typed_by is None:
                    typed_by = _get_action_usage_subsetted_by(ctx)
    
    # Get body items
    action_items = _visit_action_body_items(ctx)
    
    # Full specialization (Typings + Subsettings + Redefinitions +
    # References); typed-by fallback for odd contexts.
    spec_full = _full_specialization_for_ctx(ctx)
    if spec_full is not None:
        specialization = spec_full
    else:
        specialization = _build_specialization(typed_by) if typed_by else None
    
    return {
        "name": "BehaviorUsageMember",
        "prefix": member_prefix,
        "ownedRelatedElement": {
            "name": "BehaviorUsageElement",
            "ownedRelationship": {
                "name": "ActionUsage",
                "prefix": occ_prefix,
                "declaration": {
                    "name": "ActionUsageDeclaration",
                    "declaration": {
                        "name": "UsageDeclaration",
                        "declaration": {
                            "name": "FeatureDeclaration",
                            "identification": {
                                "name": "Identification",
                                "declaredShortName": shortname,
                                "declaredName": name
                            },
                            "specialization": specialization
                        }
                    },
                    "valuepart": None
                },
                "body": {
                    "name": "ActionBody",
                    "items": action_items
                }
            }
        }
    }


def _make_succession_usage_dict(ctx, prefix=None):
    """Create a succession usage dictionary for flow connections."""
    if ctx is None:
        return None
    
    name = None
    if hasattr(ctx, 'identification') and ctx.identification():
        ident = ctx.identification()
        if hasattr(ident, 'name'):
            name_list = ident.name()
            if name_list and isinstance(name_list, list):
                name = name_list[0].getText() if len(name_list) >= 1 else None
    
    # Get succession items
    succession_items = []
    if hasattr(ctx, 'successionItem') and ctx.successionItem():
        items = ctx.successionItem()
        if not isinstance(items, list):
            items = [items]
        for item in items:
            item_dict = _visit_succession_item(item)
            if item_dict:
                succession_items.append(item_dict)
    
    return {
        "name": "SuccessionItemUsage",
        "prefix": prefix,
        "ownedRelatedElement": {
            "name": "SuccessionUsage",
            "identification": {
                "name": "Identification",
                "declaredShortName": None,
                "declaredName": name
            },
            "items": succession_items
        }
    }


def _visit_succession_item(item_ctx):
    """Visit a succession item (source -> target connection)."""
    if item_ctx is None:
        return None
    
    source = None
    target = None
    
    if hasattr(item_ctx, 'source') and item_ctx.source():
        source = _visit_relationship_end(item_ctx.source())
    
    if hasattr(item_ctx, 'target') and item_ctx.target():
        target = _visit_relationship_end(item_ctx.target())
    
    if source or target:
        return {
            "name": "SuccessionItem",
            "source": source,
            "target": target
        }
    
    return None


def _visit_relationship_end(end_ctx):
    """Visit a relationship end (for flow connections)."""
    if end_ctx is None:
        return None
    
    # Handle feature path (e.g., focus.image)
    if hasattr(end_ctx, 'featurePath') and end_ctx.featurePath():
        fp = end_ctx.featurePath()
        names = []
        if hasattr(fp, 'qualifiedName') and fp.qualifiedName():
            qn = fp.qualifiedName()
            if hasattr(qn, 'name') and qn.name():
                names = [n.getText() for n in qn.name()]
        return {
            "name": "FeaturePath",
            "names": names
        }
    
    return None


def _build_flow_end_member_dict(flow_end_ctx):
    """Build a FlowEndMember dict from a FlowEndMemberContext."""
    if flow_end_ctx is None:
        return None
    
    fes_list = []
    ffm_list = []
    
    # flowEndMember -> flowEnd
    # flowEnd : qualifiedName (DOT qualifiedName)*
    # For "focus.image", first qualifiedName is subsetting, rest are features
    if hasattr(flow_end_ctx, 'flowEnd') and flow_end_ctx.flowEnd():
        flow_end = flow_end_ctx.flowEnd()
        if hasattr(flow_end, 'qualifiedName') and flow_end.qualifiedName():
            qnames = flow_end.qualifiedName()
            if not isinstance(qnames, list):
                qnames = [qnames]
            
            # First qualifiedName -> FlowEndSubsetting
            if len(qnames) >= 1:
                qn = qnames[0]
                if hasattr(qn, 'name') and qn.name():
                    names = [n.getText() for n in qn.name()]
                    fes_list.append({
                        "name": "FlowEndSubsetting",
                        "referencedFeature": {
                            "name": "QualifiedName",
                            "names": names
                        },
                        "ownedRelatedElement": []
                    })
            
            # Remaining qualifiedNames -> FlowFeatureMember
            for qn in qnames[1:]:
                if hasattr(qn, 'name') and qn.name():
                    names = [n.getText() for n in qn.name()]
                    ffm_list.append({
                        "name": "FlowFeatureMember",
                        "ownedRelatedElement": [{
                            "name": "FlowFeature",
                            "ownedRelationship": [{
                                "name": "FlowRedefinition",
                                "redefinedFeature": {
                                    "name": "QualifiedName",
                                    "names": names
                                }
                            }]
                        }]
                    })
    
    # Create FlowEnd dict
    flow_end_dict = {
        "name": "FlowEnd",
        "fes": fes_list,
        "ffm": ffm_list
    }
    
    return {
        "name": "FlowEndMember",
        "ownedRelatedElement": [flow_end_dict]
    }


def _visit_calculation_body_items(ctx):
    """Extract CalculationBodyPart dicts from a constraint/calculation definition context.
    
    Processes calculationBody().calculationBodyPart() items, handling calculationBodyItem
    (in/out parameters, attributes) and result expressions.
    """
    if ctx is None:
        return []
    
    calc_body = None
    if hasattr(ctx, 'calculationBody') and ctx.calculationBody():
        calc_body = ctx.calculationBody()
    
    if calc_body is None:
        return []
    
    parts = []
    if hasattr(calc_body, 'calculationBodyPart') and calc_body.calculationBodyPart():
        part_ctx_list = calc_body.calculationBodyPart()
        if not isinstance(part_ctx_list, list):
            part_ctx_list = [part_ctx_list]
        for part_ctx in part_ctx_list:
            if part_ctx:
                part_dict = _visit_calculation_body_part(part_ctx)
                if part_dict:
                    parts.append(part_dict)
    
    return parts


def _visit_calculation_body_part(part_ctx):
    """Visit a single CalculationBodyPart and return a dict."""
    if part_ctx is None:
        return None
    
    items = []
    rem = []
    
    # Handle calculationBodyItem
    if hasattr(part_ctx, 'calculationBodyItem') and part_ctx.calculationBodyItem():
        for cbi_ctx in part_ctx.calculationBodyItem():
            item_dict = _visit_calculation_body_item(cbi_ctx)
            if item_dict:
                items.append(item_dict)
    
    # Handle resultExpressionMember (e.g. "sum(partMasses) <= massLimit")
    if hasattr(part_ctx, 'resultExpressionMember') and part_ctx.resultExpressionMember():
        rem_ctx = part_ctx.resultExpressionMember()
        rem_dict = _visit_result_expression_member(rem_ctx)
        if rem_dict:
            rem.append(rem_dict)
    
    return {
        "name": "CalculationBodyPart",
        "item": items,
        "ownedRelationship": rem
    }


def _visit_result_expression_member(rem_ctx):
    """Visit a resultExpressionMember context.
    
    Grammar:
      resultExpressionMember : memberPrefix ownedExpression ;
    """
    if rem_ctx is None:
        return None
    
    prefix = None
    if hasattr(rem_ctx, 'memberPrefix') and rem_ctx.memberPrefix():
        mp = rem_ctx.memberPrefix()
        if hasattr(mp, 'visibilityIndicator') and mp.visibilityIndicator():
            prefix = {
                "name": "MemberPrefix",
                "visibility": _visit_visibility_indicator_dict(mp.visibilityIndicator())
            }
    
    owned_expr = None
    if hasattr(rem_ctx, 'ownedExpression') and rem_ctx.ownedExpression():
        oe_ctx = rem_ctx.ownedExpression()
        owned_expr = _visit_owned_expression(oe_ctx)
    
    return {
        "name": "ResultExpressionMember",
        "prefix": prefix,
        "ownedRelatedElement": owned_expr
    }


def _visit_calculation_body_item(cbi_ctx):
    """Visit a single CalculationBodyItem and return a CalculationBodyItem dict."""
    if cbi_ctx is None:
        return None
    
    # Handle actionBodyItem (which contains nonBehaviorBodyItem)
    if hasattr(cbi_ctx, 'actionBodyItem') and cbi_ctx.actionBodyItem():
        abi = cbi_ctx.actionBodyItem()
        action_item = _visit_action_body_item(abi)
        if action_item:
            return {
                "name": "CalculationBodyItem",
                "item": action_item,
                "ownedRelationship": None
            }
    
    # Handle returnParameterMember
    if hasattr(cbi_ctx, 'returnParameterMember') and cbi_ctx.returnParameterMember():
        rpm = cbi_ctx.returnParameterMember()
        inner = _visit_return_parameter_member(rpm)
        if inner:
            return {
                "name": "CalculationBodyItem",
                "item": None,
                "ownedRelationship": inner
            }
    
    return None


def _visit_return_parameter_member(rpm_ctx):
    """Visit a returnParameterMember.
    
    Grammar:
      returnParameterMember : memberPrefix RETURN usageElement ;
      usageElement : nonOccurrenceUsageElement | occurrenceUsageElement ;
    """
    if rpm_ctx is None:
        return None
    
    prefix = None
    if hasattr(rpm_ctx, 'memberPrefix') and rpm_ctx.memberPrefix():
        mp = rpm_ctx.memberPrefix()
        if hasattr(mp, 'visibilityIndicator') and mp.visibilityIndicator():
            prefix = {
                "name": "MemberPrefix",
                "visibility": _visit_visibility_indicator_dict(mp.visibilityIndicator())
            }
    
    # Find usageElement
    usage_element_dict = None
    if hasattr(rpm_ctx, 'usageElement') and rpm_ctx.usageElement():
        ue = rpm_ctx.usageElement()
        # Check if non-occurrence or occurrence
        if hasattr(ue, 'nonOccurrenceUsageElement') and ue.nonOccurrenceUsageElement():
            non_occ = ue.nonOccurrenceUsageElement()
            inner = _visit_nested_non_occurrence_usage(non_occ)
            if inner:
                if inner.get("name") == "NonOccurrenceUsageElement":
                    usage_element_dict = {
                        "name": "UsageElement",
                        "ownedRelatedElement": inner
                    }
                else:
                    # Wrap raw element in NonOccurrenceUsageElement
                    usage_element_dict = {
                        "name": "UsageElement",
                        "ownedRelatedElement": {
                            "name": "NonOccurrenceUsageElement",
                            "ownedRelatedElement": inner
                        }
                    }
        elif hasattr(ue, 'occurrenceUsageElement') and ue.occurrenceUsageElement():
            occ = ue.occurrenceUsageElement()
            inner = _visit_nested_occurrence_usage(occ)
            if inner:
                if inner.get("name") == "UsageElement":
                    usage_element_dict = inner
                else:
                    usage_element_dict = {
                        "name": "UsageElement",
                        "ownedRelatedElement": inner
                    }
    
    return {
        "name": "ReturnParameterMember",
        "prefix": prefix,
        "ownedRelatedElement": usage_element_dict
    }


def _visit_non_behavior_body_item(nbi_ctx):
    """Visit a nonBehaviorBodyItem - similar to definitionBodyItem but inside action body."""
    if nbi_ctx is None:
        return None
    
    # Handle nonOccurrenceUsageMember (in/out params, attributes)
    for child in nbi_ctx.children:
        cname = type(child).__name__
        
        if cname == 'NonOccurrenceUsageMemberContext':
            # Navigate: NonOccurrenceUsageMember -> NonOccurrenceUsageElement -> usage
            for c2 in child.children:
                if type(c2).__name__ == 'NonOccurrenceUsageElementContext':
                    inner = _visit_nested_non_occurrence_usage(c2)
                    if inner:
                        if inner.get("name") == "NonOccurrenceUsageElement":
                            owned = [inner]
                        else:
                            owned = [inner]
                        return {
                            "name": "NonOccurrenceUsageMember",
                            "prefix": None,
                            "ownedRelatedElement": owned
                        }
        
        elif cname == 'DefinitionMemberContext':
            # Handle comments/documentation inside bodies
            # Structure: DefinitionMember -> DefinitionElement -> AnnotatingElement -> Comment
            for c2 in child.children:
                if type(c2).__name__ == 'DefinitionElementContext':
                    for c3 in c2.children:
                        if type(c3).__name__ == 'AnnotatingElementContext':
                            if hasattr(c3, 'comment') and c3.comment():
                                comment = _visit_comment_dict(c3.comment())
                                if comment:
                                    return comment
                            elif hasattr(c3, 'documentation') and c3.documentation():
                                doc = _visit_documentation_dict(c3.documentation())
                                if doc:
                                    return doc
        
        elif cname == 'StructureUsageMemberContext':
            # Handle occurrence usages (parts, items, ports)
            for c2 in child.children:
                c2name = type(c2).__name__
                if c2name == 'OccurrenceUsageElementContext':
                    inner = _visit_nested_occurrence_usage(c2)
                    if inner:
                        if inner.get("name") == "UsageElement":
                            occ_elem = inner.get("ownedRelatedElement", {})
                            if occ_elem.get("name") == "OccurrenceUsageElement":
                                owned = [occ_elem]
                            else:
                                owned = [inner]
                        else:
                            owned = [inner]
                        return {
                            "name": "OccurrenceUsageMember",
                            "prefix": None,
                            "ownedRelatedElement": owned
                        }
                elif c2name == 'StructureUsageElementContext':
                    # StructureUsageElementContext is the direct child of StructureUsageMemberContext
                    inner = _visit_nested_occurrence_usage(c2)
                    if inner:
                        if inner.get("name") == "UsageElement":
                            occ_elem = inner.get("ownedRelatedElement", {})
                            if occ_elem.get("name") == "OccurrenceUsageElement":
                                owned = [occ_elem]
                            else:
                                owned = [inner]
                        else:
                            owned = [inner]
                        return {
                            "name": "OccurrenceUsageMember",
                            "prefix": None,
                            "ownedRelatedElement": owned
                        }
    
    return None


def _make_state_definition_dict(ctx, member_prefix=None):
    """Create a StateDefinition dictionary.
    
    StateDefinition has the pattern:
    state def Name { body }
    
    Uses 'declaration' directly (DefinitionDeclaration) and 'body' (StateDefBody).
    """
    # StateDefinition's declaration is at ctx.definitionDeclaration()
    name = None
    shortname = None
    if ctx is not None:
        dd = None
        if hasattr(ctx, 'definitionDeclaration') and ctx.definitionDeclaration():
            dd = ctx.definitionDeclaration()
        
        if dd and hasattr(dd, 'identification') and dd.identification():
            ident = dd.identification()
            if hasattr(ident, 'name'):
                name_list = ident.name()
                if name_list and isinstance(name_list, list):
                    if len(name_list) == 2:
                        shortname = name_list[0].getText()
                        name = name_list[1].getText()
                    elif len(name_list) == 1:
                        name_text = name_list[0].getText()
                        name, shortname = _extract_name_shortname(name_text)
    
    occ_prefix = _get_occurrence_definition_prefix(ctx)
    
    # Parse state body
    body = _visit_state_def_body(ctx)
    
    return {
        "name": "PackageMember",
        "prefix": member_prefix,
        "ownedRelatedElement": {
            "name": "DefinitionElement",
            "ownedRelatedElement": {
                "name": "StateDefinition",
                "prefix": occ_prefix,
                "declaration": {
                    "name": "DefinitionDeclaration",
                    "identification": {
                        "name": "Identification",
                        "declaredShortName": shortname,
                        "declaredName": name
                    },
                    "subclassificationpart": _get_subclassification_part(ctx)
                },
                "body": body
            }
        }
    }


def _visit_state_def_body(ctx):
    """Visit a stateDefBody context and return a StateDefBody dict."""
    if ctx is None:
        return {"name": "StateDefBody", "part": None, "isParallel": None}
    
    # ctx might be a StateDefinitionContext, not a StateDefBodyContext
    # Try to navigate to stateDefBody first
    body_ctx = ctx
    if hasattr(ctx, 'stateDefBody') and ctx.stateDefBody():
        body_ctx = ctx.stateDefBody()
        if isinstance(body_ctx, list):
            body_ctx = body_ctx[0]
    
    # Check if it's empty (SEMI)
    if hasattr(body_ctx, 'SEMI') and body_ctx.SEMI():
        return {"name": "StateDefBody", "part": None, "isParallel": None}
    
    # Check for parallel keyword
    is_parallel = False
    if hasattr(body_ctx, 'PARALLEL') and body_ctx.PARALLEL():
        is_parallel = True
    
    # Parse state body items
    # If LBRACE is present (explicit braces), create a part even if empty
    has_braces = hasattr(body_ctx, 'LBRACE') and body_ctx.LBRACE()
    part = None
    if hasattr(body_ctx, 'stateBodyItem'):
        items = body_ctx.stateBodyItem()
        if items and isinstance(items, list):
            body_items = []
            for item_ctx in items:
                item_dict = _visit_state_body_item(item_ctx)
                if item_dict:
                    body_items.append(item_dict)
            
            if body_items:
                part = {
                    "name": "StateBodyPart",
                    "item": body_items
                }
    
    # If explicit braces but no items, create an empty StateBodyPart
    if part is None and has_braces:
        part = {"name": "StateBodyPart", "item": []}
    
    return {
        "name": "StateDefBody",
        "part": part,
        "isParallel": is_parallel
    }


def _visit_state_body_item(ctx):
    """Visit a stateBodyItem context and return a StateBodyItem dict."""
    if ctx is None:
        return None
    
    owned_rel = []
    
    # Check for nonBehaviorBodyItem
    if hasattr(ctx, 'nonBehaviorBodyItem') and ctx.nonBehaviorBodyItem():
        items = ctx.nonBehaviorBodyItem()
        if not isinstance(items, list):
            items = [items]
        for item in items:
            item_dict = _visit_state_non_behavior_body_item(item)
            if item_dict:
                owned_rel.append(item_dict)
    
    # Check for behaviorUsageMember (state usages)
    if hasattr(ctx, 'behaviorUsageMember') and ctx.behaviorUsageMember():
        items = ctx.behaviorUsageMember()
        if not isinstance(items, list):
            items = [items]
        for item in items:
            item_dict = _visit_state_behavior_usage_member(item)
            if item_dict:
                owned_rel.append(item_dict)
    
    # Check for transitionUsageMember
    if hasattr(ctx, 'transitionUsageMember') and ctx.transitionUsageMember():
        items = ctx.transitionUsageMember()
        if not isinstance(items, list):
            items = [items]
        for item in items:
            item_dict = _visit_transition_usage_member(item)
            if item_dict:
                owned_rel.append(item_dict)
    
    # Check for entryActionMember
    if hasattr(ctx, 'entryActionMember') and ctx.entryActionMember():
        items = ctx.entryActionMember()
        if not isinstance(items, list):
            items = [items]
        for item in items:
            item_dict = _visit_entry_action_member(item)
            if item_dict:
                owned_rel.append(item_dict)
    
    # Check for doActionMember
    if hasattr(ctx, 'doActionMember') and ctx.doActionMember():
        items = ctx.doActionMember()
        if not isinstance(items, list):
            items = [items]
        for item in items:
            item_dict = _visit_do_action_member(item)
            if item_dict:
                owned_rel.append(item_dict)
    
    # Check for exitActionMember
    if hasattr(ctx, 'exitActionMember') and ctx.exitActionMember():
        items = ctx.exitActionMember()
        if not isinstance(items, list):
            items = [items]
        for item in items:
            item_dict = _visit_exit_action_member(item)
            if item_dict:
                owned_rel.append(item_dict)
    
    # Check for sourceSuccessionMember followed by behaviorUsageMember
    if hasattr(ctx, 'sourceSuccessionMember') and ctx.sourceSuccessionMember():
        items = ctx.sourceSuccessionMember()
        if not isinstance(items, list):
            items = [items]
        for item in items:
            item_dict = _visit_source_succession_member(item)
            if item_dict:
                owned_rel.append(item_dict)
    
    # Check for targetTransitionUsageMember
    if hasattr(ctx, 'targetTransitionUsageMember') and ctx.targetTransitionUsageMember():
        items = ctx.targetTransitionUsageMember()
        if not isinstance(items, list):
            items = [items]
        for item in items:
            item_dict = _visit_target_transition_usage_member(item)
            if item_dict:
                owned_rel.append(item_dict)
    
    # Check for entryTransitionMember
    if hasattr(ctx, 'entryTransitionMember') and ctx.entryTransitionMember():
        items = ctx.entryTransitionMember()
        if not isinstance(items, list):
            items = [items]
        for item in items:
            item_dict = _visit_entry_transition_member(item)
            if item_dict:
                owned_rel.append(item_dict)
    
    if not owned_rel:
        return None
    
    return {
        "name": "StateBodyItem",
        "ownedRelationship": owned_rel
    }


def _visit_entry_action_member(ctx):
    """Visit an entryActionMember and return a dict."""
    if ctx is None:
        return None
    
    prefix = None
    if hasattr(ctx, 'memberPrefix') and ctx.memberPrefix():
        mp = ctx.memberPrefix()
        if hasattr(mp, 'visibilityIndicator') and mp.visibilityIndicator():
            prefix = {
                "name": "MemberPrefix",
                "visibility": _visit_visibility_indicator_dict(mp.visibilityIndicator())
            }
    
    action_dict = None
    if hasattr(ctx, 'stateActionUsage') and ctx.stateActionUsage():
        action_dict = _visit_state_action_usage(ctx.stateActionUsage())
    
    return {
        "name": "EntryActionMember",
        "prefix": prefix,
        "ownedRelatedElement": action_dict
    }


def _visit_do_action_member(ctx):
    """Visit a doActionMember and return a dict."""
    if ctx is None:
        return None
    
    prefix = None
    if hasattr(ctx, 'memberPrefix') and ctx.memberPrefix():
        mp = ctx.memberPrefix()
        if hasattr(mp, 'visibilityIndicator') and mp.visibilityIndicator():
            prefix = {
                "name": "MemberPrefix",
                "visibility": _visit_visibility_indicator_dict(mp.visibilityIndicator())
            }
    
    action_dict = None
    if hasattr(ctx, 'stateActionUsage') and ctx.stateActionUsage():
        action_dict = _visit_state_action_usage(ctx.stateActionUsage())
    
    return {
        "name": "DoActionMember",
        "prefix": prefix,
        "ownedRelatedElement": action_dict
    }


def _visit_exit_action_member(ctx):
    """Visit an exitActionMember and return a dict."""
    if ctx is None:
        return None
    
    prefix = None
    if hasattr(ctx, 'memberPrefix') and ctx.memberPrefix():
        mp = ctx.memberPrefix()
        if hasattr(mp, 'visibilityIndicator') and mp.visibilityIndicator():
            prefix = {
                "name": "MemberPrefix",
                "visibility": _visit_visibility_indicator_dict(mp.visibilityIndicator())
            }
    
    action_dict = None
    if hasattr(ctx, 'stateActionUsage') and ctx.stateActionUsage():
        action_dict = _visit_state_action_usage(ctx.stateActionUsage())
    
    return {
        "name": "ExitActionMember",
        "prefix": prefix,
        "ownedRelatedElement": action_dict
    }


def _visit_state_action_usage(ctx):
    """Visit a stateActionUsage context and return the appropriate dict."""
    if ctx is None:
        return None
    
    # Try emptyActionUsage_
    if hasattr(ctx, 'emptyActionUsage_') and ctx.emptyActionUsage_():
        empty = ctx.emptyActionUsage_()
        if isinstance(empty, list):
            empty = empty[0]
        if empty:
            return _visit_empty_action_usage(empty)
    
    # Try statePerformActionUsage
    if hasattr(ctx, 'statePerformActionUsage') and ctx.statePerformActionUsage():
        perf = ctx.statePerformActionUsage()
        if isinstance(perf, list):
            perf = perf[0]
        if perf:
            return _visit_state_perform_action_usage(perf)
    
    # Try stateAcceptActionUsage
    if hasattr(ctx, 'stateAcceptActionUsage') and ctx.stateAcceptActionUsage():
        accept = ctx.stateAcceptActionUsage()
        if isinstance(accept, list):
            accept = accept[0]
        if accept:
            return _visit_state_accept_action_usage(accept)
    
    # Try stateSendActionUsage
    if hasattr(ctx, 'stateSendActionUsage') and ctx.stateSendActionUsage():
        send = ctx.stateSendActionUsage()
        if isinstance(send, list):
            send = send[0]
        if send:
            return _visit_state_send_action_usage(send)
    
    # Try stateAssignmentActionUsage
    if hasattr(ctx, 'stateAssignmentActionUsage') and ctx.stateAssignmentActionUsage():
        assign = ctx.stateAssignmentActionUsage()
        if isinstance(assign, list):
            assign = assign[0]
        if assign:
            return _visit_state_assignment_action_usage(assign)
    
    return None


def _visit_empty_action_usage(ctx):
    """Visit an emptyActionUsage and return a StateActionUsage dict."""
    if ctx is None:
        return None
    
    # Empty action usage is just a semicolon
    return {
        "name": "StateActionUsage",
        "body": None,
        "pau": None
    }


def _visit_perform_action_usage_declaration(ctx):
    """Visit a performActionUsageDeclaration context.
    
    Grammar: performActionUsageDeclaration:
      (ownedReferenceSubsetting featureSpecializationPart? | ACTION usageDeclaration?) valuePart? ;
    
    Returns a PerformActionUsageDeclaration dict:
      {name, ownedRelationship, fspart, declaration, valuepart}
    """
    if ctx is None:
        return None
    
    ors = None  # OwnedReferenceSubsetting (the action name like 'performSelfTest')
    fspart = None
    decl = None
    
    # Case 1: ownedReferenceSubsetting (named action reference)
    if hasattr(ctx, 'ownedReferenceSubsetting') and ctx.ownedReferenceSubsetting():
        ors_ctx = ctx.ownedReferenceSubsetting()
        if isinstance(ors_ctx, list):
            ors_ctx = ors_ctx[0]
        if ors_ctx and hasattr(ors_ctx, 'qualifiedName') and ors_ctx.qualifiedName():
            qns = ors_ctx.qualifiedName()
            if not isinstance(qns, list):
                qns = [qns]
            qns = [qn for qn in qns if qn]
            if qns:
                # First qualified name is referencedFeature
                first_name = qns[0].getText()
                # Remaining qualified names (after DOT) are ownedRelatedElement
                owned_elements = []
                for qn in qns[1:]:
                    owned_elements.append({
                        "name": "OwnedFeatureChain",
                        "feature": {
                            "name": "FeatureChain",
                            "ownedRelationship": [{
                                "name": "OwnedFeatureChaining",
                                "chainingFeature": {
                                    "name": "QualifiedName",
                                    "names": [qn.getText()]
                                }
                            }]
                        }
                    })
                ors = {
                    "name": "OwnedReferenceSubsetting",
                    "referencedFeature": {
                        "name": "QualifiedName",
                        "names": [first_name]
                    },
                    "ownedRelatedElement": owned_elements
                }
    
    # Extract featureSpecializationPart (for both ownedReferenceSubsetting and ACTION cases)
    if hasattr(ctx, 'featureSpecializationPart') and ctx.featureSpecializationPart():
        fsp = ctx.featureSpecializationPart()
        fspart = _build_full_specialization_from_fsp(fsp)
    
    # Case 2: ACTION usageDeclaration (anonymous or named action keyword)
    if ors is None and hasattr(ctx, 'ACTION') and ctx.ACTION():
        if hasattr(ctx, 'usageDeclaration') and ctx.usageDeclaration():
            ud = ctx.usageDeclaration()
            name, shortname = None, None
            specialization = None
            
            if hasattr(ud, 'identification') and ud.identification():
                ident = ud.identification()
                name_list = ident.name() if hasattr(ident, 'name') else []
                if name_list and isinstance(name_list, list) and len(name_list) >= 1:
                    usage_name = name_list[-1].getText()
                    name = usage_name
            
            # Extract featureSpecializationPart (typings like ': GenerateTorque')
            if hasattr(ud, 'featureSpecializationPart') and ud.featureSpecializationPart():
                fsp = ud.featureSpecializationPart()
                if hasattr(fsp, 'featureSpecialization') and fsp.featureSpecialization():
                    specs = fsp.featureSpecialization()
                    if not isinstance(specs, list):
                        specs = [specs]
                    for spec in specs:
                        if hasattr(spec, 'typings') and spec.typings():
                            typings = spec.typings()
                            if hasattr(typings, 'typedBy') and typings.typedBy():
                                tb = typings.typedBy()
                                if hasattr(tb, 'featureTyping') and tb.featureTyping():
                                    ft = tb.featureTyping()
                                    # Try ownedFeatureTyping first (for ': TypeName' syntax)
                                    if hasattr(ft, 'ownedFeatureTyping') and ft.ownedFeatureTyping():
                                        oft = ft.ownedFeatureTyping()
                                        qns = oft.qualifiedName()
                                        if isinstance(qns, list):
                                            qns = [qn for qn in qns if qn]
                                        if qns:
                                            if isinstance(qns, list):
                                                typed_by = qns[0].getText()
                                            else:
                                                typed_by = qns.getText()
                                            specialization = {
                                                "name": "FeatureSpecializationPart",
                                                "specialization": [{
                                                    "name": "FeatureSpecialization",
                                                    "ownedRelationship": {
                                                        "name": "Typings",
                                                        "typedby": {
                                                            "name": "TypedBy",
                                                            "ownedRelationship": [{
                                                                "name": "FeatureTyping",
                                                                "ownedRelationship": {
                                                                    "name": "OwnedFeatureTyping",
                                                                    "type": {
                                                                        "name": "FeatureType",
                                                                        "type": {
                                                                            "name": "QualifiedName",
                                                                            "names": [typed_by]
                                                                        },
                                                                        "ownedRelatedElement": []
                                                                    }
                                                                }
                                                            }]
                                                        },
                                                        "ownedRelationship": []
                                                    }
                                                }],
                                                "multiplicity": None,
                                                "specialization2": [],
                                                "multiplicity2": None
                                            }
                                    # Fallback to qualifiedName directly
                                    elif hasattr(ft, 'qualifiedName') and ft.qualifiedName():
                                        typed_by = ft.qualifiedName().getText()
                                        specialization = {
                                            "name": "FeatureSpecializationPart",
                                            "specialization": [{
                                                "name": "FeatureSpecialization",
                                                "ownedRelationship": {
                                                    "name": "Typings",
                                                    "typedby": {
                                                        "name": "TypedBy",
                                                        "ownedRelationship": [{
                                                            "name": "FeatureTyping",
                                                            "ownedRelationship": {
                                                                "name": "OwnedFeatureTyping",
                                                                "type": {
                                                                    "name": "FeatureType",
                                                                    "type": {
                                                                        "name": "QualifiedName",
                                                                        "names": [typed_by]
                                                                    },
                                                                    "ownedRelatedElement": []
                                                                }
                                                            }
                                                        }]
                                                    },
                                                    "ownedRelationship": []
                                                }
                                            }],
                                            "multiplicity": None,
                                            "specialization2": [],
                                            "multiplicity2": None
                                        }
            
            if name:
                decl = {
                    "name": "UsageDeclaration",
                    "declaration": {
                        "name": "FeatureDeclaration",
                        "identification": {
                            "name": "Identification",
                            "declaredShortName": shortname,
                            "declaredName": name
                        },
                        "specialization": specialization
                    }
                }
    
    # Extract valuePart (e.g., "= someValue")
    valuepart = None
    if hasattr(ctx, 'valuePart') and ctx.valuePart():
        vp_ctx = ctx.valuePart()
        valuepart = _visit_value_part(vp_ctx)
    
    return {
        "name": "PerformActionUsageDeclaration",
        "ownedRelationship": ors,
        "fspart": fspart,
        "declaration": decl,
        "valuepart": valuepart
    }


def _visit_state_perform_action_usage(ctx):
    """Visit a statePerformActionUsage and return a StateActionUsage dict.
    
    Grammar: statePerformActionUsage: performActionUsageDeclaration actionBody ;
    EntryActionMember.ownedRelatedElement = StateActionUsage { pau, body }
    """
    if ctx is None:
        return None
    
    pau = None
    if hasattr(ctx, 'performActionUsageDeclaration') and ctx.performActionUsageDeclaration():
        decl_dict = _visit_perform_action_usage_declaration(ctx.performActionUsageDeclaration())
        if decl_dict:
            pau = {
                "name": "PerformedActionUsage",
                "declaration": decl_dict
            }
    
    body = None
    if hasattr(ctx, 'actionBody') and ctx.actionBody():
        body = _visit_action_body(ctx.actionBody())
    
    return {
        "name": "StateActionUsage",
        "body": body,
        "pau": pau
    }


def _visit_state_accept_action_usage(ctx):
    """Visit a stateAcceptActionUsage and return a dict."""
    if ctx is None:
        return None
    
    decl = None
    if hasattr(ctx, 'acceptNodeDeclaration') and ctx.acceptNodeDeclaration():
        decl_dict = _visit_accept_node_declaration(ctx.acceptNodeDeclaration())
        decl = decl_dict
    
    body = None
    if hasattr(ctx, 'actionBody') and ctx.actionBody():
        body = _visit_action_body(ctx.actionBody())
    
    return {
        "name": "StateAcceptActionUsage",
        "declaration": decl,
        "body": body
    }


def _visit_state_send_action_usage(ctx):
    """Visit a stateSendActionUsage and return a dict."""
    if ctx is None:
        return None
    
    decl = None
    if hasattr(ctx, 'sendNodeDeclaration') and ctx.sendNodeDeclaration():
        decl_dict = _visit_send_node_declaration(ctx.sendNodeDeclaration())
        decl = decl_dict
    
    body = None
    if hasattr(ctx, 'actionBody') and ctx.actionBody():
        body = _visit_action_body(ctx.actionBody())
    
    return {
        "name": "StateSendActionUsage",
        "declaration": decl,
        "body": body
    }


def _visit_accept_node_declaration(ctx):
    """Visit an acceptNodeDeclaration context.
    
    Grammar:
      acceptNodeDeclaration
        : (actionNodeUsageDeclaration)? ACCEPT acceptParameterPart
        ;
    
    Returns:
      {name: "AcceptNodeDeclaration", declaration, acceptParameter}
    """
    if ctx is None:
        return None
    
    decl = None
    if hasattr(ctx, 'actionNodeUsageDeclaration') and ctx.actionNodeUsageDeclaration():
        aud = ctx.actionNodeUsageDeclaration()
        decl = {
            "name": "ActionNodeUsageDeclaration",
            "declaration": None
        }
        if hasattr(aud, 'usageDeclaration') and aud.usageDeclaration():
            ud = aud.usageDeclaration()
            if ud:
                name, shortname = _get_usage_identification_from_ud(ud)
                decl["declaration"] = {
                    "name": "UsageDeclaration",
                    "declaration": {
                        "name": "FeatureDeclaration",
                        "identification": {
                            "name": "Identification",
                            "declaredShortName": shortname,
                            "declaredName": name
                        },
                        "specialization": None
                    }
                }
    
    accept_param = None
    if hasattr(ctx, 'acceptParameterPart') and ctx.acceptParameterPart():
        accept_param = _visit_accept_parameter_part(ctx.acceptParameterPart())
    
    return {
        "name": "AcceptNodeDeclaration",
        "declaration": decl,
        "acceptParameter": accept_param
    }


def _visit_sender_receiver_part(ctx):
    """Visit a senderReceiverPart context.
    
    Grammar:
      senderReceiverPart
        : VIA nodeParameterMember (TO nodeParameterMember)?
        | emptyParameterMember TO nodeParameterMember
        ;
    
    Returns:
      {name: "SenderReceiverPart", via: nodeParameterMember, to: nodeParameterMember}
    """
    if ctx is None:
        return None
    
    via = None
    to = None
    nps = ctx.nodeParameterMember() if hasattr(ctx, 'nodeParameterMember') else None
    
    if hasattr(ctx, 'VIA') and ctx.VIA():
        # Alternative 1: VIA nodeParameterMember (TO nodeParameterMember)?
        if nps and len(nps) > 0:
            via = _visit_node_parameter_member(nps[0])
        if nps and len(nps) > 1:
            to = _visit_node_parameter_member(nps[1])
    elif hasattr(ctx, 'TO') and ctx.TO():
        # Alternative 2: emptyParameterMember TO nodeParameterMember
        if nps and len(nps) > 0:
            to = _visit_node_parameter_member(nps[0])
    
    return {
        "name": "SenderReceiverPart",
        "via": via,
        "to": to
    }


def _visit_send_node_declaration(ctx):
    """Visit a sendNodeDeclaration context.
    
    Grammar:
      sendNodeDeclaration
        : (actionNodeUsageDeclaration)? SEND nodeParameterMember senderReceiverPart?
        ;
    
    Returns:
      {name: "SendNodeDeclaration", declaration, nodeParameter, senderReceiver}
    """
    if ctx is None:
        return None
    
    decl = None
    if hasattr(ctx, 'actionNodeUsageDeclaration') and ctx.actionNodeUsageDeclaration():
        aud = ctx.actionNodeUsageDeclaration()
        decl = {
            "name": "ActionNodeUsageDeclaration",
            "declaration": None
        }
        if hasattr(aud, 'usageDeclaration') and aud.usageDeclaration():
            ud = aud.usageDeclaration()
            if ud:
                name, shortname = _get_usage_identification_from_ud(ud)
                decl["declaration"] = {
                    "name": "UsageDeclaration",
                    "declaration": {
                        "name": "FeatureDeclaration",
                        "identification": {
                            "name": "Identification",
                            "declaredShortName": shortname,
                            "declaredName": name
                        },
                        "specialization": None
                    }
                }
    
    node_param = None
    if hasattr(ctx, 'nodeParameterMember') and ctx.nodeParameterMember():
        node_param = _visit_node_parameter_member(ctx.nodeParameterMember())
    
    sender_receiver = None
    if hasattr(ctx, 'senderReceiverPart') and ctx.senderReceiverPart():
        sender_receiver = _visit_sender_receiver_part(ctx.senderReceiverPart())
    
    return {
        "name": "SendNodeDeclaration",
        "declaration": decl,
        "nodeParameter": node_param,
        "senderReceiver": sender_receiver
    }


def _visit_assignment_node_declaration(ctx):
    """Visit an assignmentNodeDeclaration context.
    
    Grammar:
      assignmentNodeDeclaration
        : (actionNodeUsageDeclaration)? ASSIGN assignmentTargetMember featureChainMember COLON_EQ nodeParameterMember
        ;
    
    Returns:
      {name: "AssignmentNodeDeclaration", declaration, target, ownedRelationship1, ownedRelationship2}
    """
    if ctx is None:
        return None
    
    decl = None
    if hasattr(ctx, 'actionNodeUsageDeclaration') and ctx.actionNodeUsageDeclaration():
        aud = ctx.actionNodeUsageDeclaration()
        decl = {
            "name": "ActionNodeUsageDeclaration",
            "declaration": None
        }
        if hasattr(aud, 'usageDeclaration') and aud.usageDeclaration():
            ud = aud.usageDeclaration()
            if ud:
                name, shortname = _get_usage_identification_from_ud(ud)
                decl["declaration"] = {
                    "name": "UsageDeclaration",
                    "declaration": {
                        "name": "FeatureDeclaration",
                        "identification": {
                            "name": "Identification",
                            "declaredShortName": shortname,
                            "declaredName": name
                        },
                        "specialization": None
                    }
                }
    
    # assignmentTargetMember (the prefix like 'vehicle.')
    target = None
    if hasattr(ctx, 'assignmentTargetMember') and ctx.assignmentTargetMember():
        atm = ctx.assignmentTargetMember()
        target = _visit_assignment_target_member(atm)
    
    # featureChainMember (ownedRelationship1)
    fcm = None
    if hasattr(ctx, 'featureChainMember') and ctx.featureChainMember():
        fcm = _visit_feature_chain_member(ctx.featureChainMember())
    
    # nodeParameterMember (ownedRelationship2)
    npm = None
    if hasattr(ctx, 'nodeParameterMember') and ctx.nodeParameterMember():
        npm_ctx = ctx.nodeParameterMember()
        npm = _visit_node_parameter_member(npm_ctx)
    
    return {
        "name": "AssignmentNodeDeclaration",
        "declaration": decl,
        "target": target,
        "ownedRelationship1": fcm,
        "ownedRelationship2": npm
    }


def _visit_assignment_target_member(ctx):
    """Visit an assignmentTargetMember context.
    
    Grammar:
      assignmentTargetMember : assignmentTargetParameter ;
      assignmentTargetParameter : assignmentTargetBinding DOT ;
      assignmentTargetBinding : nonFeatureChainPrimaryExpression ;
    """
    if ctx is None:
        return None
    
    if hasattr(ctx, 'assignmentTargetParameter') and ctx.assignmentTargetParameter():
        atp = ctx.assignmentTargetParameter()
        if hasattr(atp, 'assignmentTargetBinding') and atp.assignmentTargetBinding():
            atb = atp.assignmentTargetBinding()
            # Extract the name from the binding
            if hasattr(atb, 'nonFeatureChainPrimaryExpression') and atb.nonFeatureChainPrimaryExpression():
                nfcp = atb.nonFeatureChainPrimaryExpression()
                # Get the text directly (it's a simple identifier)
                name = atb.getText()
                return {
                    "name": "QualifiedName",
                    "names": [name]
                }
    
    return None


def _visit_node_parameter_member(ctx):
    """Visit a nodeParameterMember context.
    
    Grammar:
      nodeParameterMember : ownedRelatedElement += NodeParameter ;
    """
    if ctx is None:
        return None
    
    owned_rel = []
    if hasattr(ctx, 'nodeParameter') and ctx.nodeParameter():
        np = ctx.nodeParameter()
        if not isinstance(np, list):
            np = [np]
        for p in np:
            param_dict = _visit_node_parameter(p)
            if param_dict:
                owned_rel.append(param_dict)
    
    return {
        "name": "NodeParameterMember",
        "ownedRelatedElement": owned_rel
    }


def _visit_node_parameter(ctx):
    """Visit a nodeParameter context.
    
    Grammar:
      nodeParameter : ownedRelationship = FeatureBinding ;
    """
    if ctx is None:
        return None
    
    owned_rel = None
    if hasattr(ctx, 'featureBinding') and ctx.featureBinding():
        fb = ctx.featureBinding()
        owned_rel = _visit_feature_binding(fb)
    
    return {
        "name": "NodeParameter",
        "ownedRelationship": owned_rel
    }


def _visit_feature_binding(ctx):
    """Visit a featureBinding context.
    
    Grammar:
      featureBinding : ownedRelatedElement = OwnedExpression ;
    """
    if ctx is None:
        return None
    
    owned_rel = None
    if hasattr(ctx, 'ownedExpression') and ctx.ownedExpression():
        oe = ctx.ownedExpression()
        owned_rel = _visit_owned_expression(oe)
    
    return {
        "name": "FeatureBinding",
        "ownedRelatedElement": owned_rel
    }


def _visit_owned_expression(ctx):
    """Visit an ownedExpression context."""
    if ctx is None:
        return None
    
    # Extract the expression text
    expr_text = ctx.getText()
    
    return {
        "name": "OwnedExpression",
        "expression": expr_text
    }


def _get_usage_identification_from_ud(ud):
    """Extract name and shortname from a usageDeclaration context."""
    name = None
    shortname = None
    if ud and hasattr(ud, 'identification') and ud.identification():
        ident = ud.identification()
        name, shortname = _extract_name_from_ident(ident)
    return name, shortname


def _visit_state_assignment_action_usage(ctx):
    """Visit a stateAssignmentActionUsage and return a dict."""
    if ctx is None:
        return None
    
    decl = None
    if hasattr(ctx, 'assignmentNodeDeclaration') and ctx.assignmentNodeDeclaration():
        decl_dict = _visit_assignment_node_declaration(ctx.assignmentNodeDeclaration())
        decl = decl_dict
    
    body = None
    if hasattr(ctx, 'actionBody') and ctx.actionBody():
        body = _visit_action_body(ctx.actionBody())
    
    return {
        "name": "StateAssignmentActionUsage",
        "declaration": decl,
        "body": body
    }


def _visit_transition_usage_member(ctx):
    """Visit a transitionUsageMember and return a dict."""
    if ctx is None:
        return None
    
    prefix = None
    if hasattr(ctx, 'memberPrefix') and ctx.memberPrefix():
        mp = ctx.memberPrefix()
        if hasattr(mp, 'visibilityIndicator') and mp.visibilityIndicator():
            prefix = {
                "name": "MemberPrefix",
                "visibility": _visit_visibility_indicator_dict(mp.visibilityIndicator())
            }
    
    transition_dict = None
    if hasattr(ctx, 'transitionUsage') and ctx.transitionUsage():
        transition_dict = _visit_transition_usage(ctx.transitionUsage())
    
    return {
        "name": "TransitionUsageMember",
        "prefix": prefix,
        "ownedRelatedElement": transition_dict
    }


def _visit_transition_usage(ctx):
    """Visit a transitionUsage context and return a TransitionUsage dict.
    
    Grammar:
      transitionUsage: TRANSITION (usageDeclaration? FIRST)? featureChainMember emptyParameterMember
        (emptyParameterMember triggerActionMember)? (guardExpressionMember)?
        (effectBehaviorMember)? THEN transitionSuccessionMember actionBody ;
    """
    if ctx is None:
        return None
    
    name = "TransitionUsage"
    
    # Get declaration (optional transition name like 'off_to_starting')
    decl = None
    if hasattr(ctx, 'usageDeclaration') and ctx.usageDeclaration():
        ud = ctx.usageDeclaration()
        if ud:
            decl_name = None
            shortname = None
            if hasattr(ud, 'identification') and ud.identification():
                ident = ud.identification()
                if hasattr(ident, 'name') and ident.name():
                    name_list = ident.name()
                    if name_list and isinstance(name_list, list):
                        if len(name_list) == 2:
                            shortname = name_list[0].getText()
                            decl_name = name_list[1].getText()
                        elif len(name_list) == 1:
                            decl_name = name_list[0].getText()
            
            decl = {
                "name": "UsageDeclaration",
                "declaration": {
                    "name": "FeatureDeclaration",
                    "identification": {
                        "name": "Identification",
                        "declaredShortName": shortname,
                        "declaredName": decl_name
                    },
                    "specialization": None
                }
            }
    
    # Build ownedRelationship with all members
    owned_rel = []
    
    # Source state from featureChainMember (e.g., 'first off')
    if hasattr(ctx, 'featureChainMember') and ctx.featureChainMember():
        fcm = ctx.featureChainMember()
        if hasattr(fcm, 'qualifiedName') and fcm.qualifiedName():
            qnames = fcm.qualifiedName()
            if not isinstance(qnames, list):
                qnames = [qnames]
            if qnames:
                src_text = ".".join(qn.getText() for qn in qnames if qn)
                owned_rel.append({
                    "name": "TransitionSourceMember",
                    "memberElement": {
                        "name": "QualifiedName",
                        "names": src_text.split("::")
                    },
                    "ownedRelatedElement": []
                })
    
    # Trigger (accept action) - TriggerActionMember
    if hasattr(ctx, 'triggerActionMember') and ctx.triggerActionMember():
        trigger_dict = _visit_trigger_action_member(ctx.triggerActionMember())
        if trigger_dict:
            owned_rel.append(trigger_dict)
    
    # Guard - GuardExpressionMember
    if hasattr(ctx, 'guardExpressionMember') and ctx.guardExpressionMember():
        guard_dict = _visit_guard_expression_member(ctx.guardExpressionMember())
        if guard_dict:
            owned_rel.append(guard_dict)
    
    # Effect - EffectBehaviorMember
    if hasattr(ctx, 'effectBehaviorMember') and ctx.effectBehaviorMember():
        effect_dict = _visit_effect_behavior_member(ctx.effectBehaviorMember())
        if effect_dict:
            owned_rel.append(effect_dict)
    
    # Target state - TransitionSuccessionMember (contains TransitionSuccession)
    if hasattr(ctx, 'transitionSuccessionMember') and ctx.transitionSuccessionMember():
        tsm = ctx.transitionSuccessionMember()
        if isinstance(tsm, list):
            tsm = tsm[0]
        if tsm:
            tsm_dict = _visit_transition_succession_member(tsm)
            if tsm_dict:
                owned_rel.append(tsm_dict)
    
    # Get body (action body)
    body = None
    if hasattr(ctx, 'actionBody') and ctx.actionBody():
        body = _visit_action_body(ctx.actionBody())
    
    return {
        "name": name,
        "declaration": decl,
        "body": body,
        "ownedRelationship": owned_rel
    }


def _visit_state_behavior_usage_member(ctx):
    """Visit a behaviorUsageMember in a state body context.
    
    Grammar: behaviorUsageMember: memberPrefix behaviorUsageElement ;
    BehaviorUsageMember class expects:
      ownedRelatedElement = BehaviorUsageElement { ownedRelationship = StateUsage|ActionUsage|... }
    
    This handles stateUsage specially; for other usages falls back to the general handler.
    """
    if ctx is None:
        return None
    
    prefix = None
    if hasattr(ctx, 'memberPrefix') and ctx.memberPrefix():
        mp = ctx.memberPrefix()
        if hasattr(mp, 'visibilityIndicator') and mp.visibilityIndicator():
            prefix = {
                "name": "MemberPrefix",
                "visibility": _visit_visibility_indicator_dict(mp.visibilityIndicator())
            }
    
    # Navigate through behaviorUsageElement to find specific usage type
    if hasattr(ctx, 'behaviorUsageElement') and ctx.behaviorUsageElement():
        bue = ctx.behaviorUsageElement()
        if hasattr(bue, 'stateUsage') and bue.stateUsage():
            su = bue.stateUsage()
            if isinstance(su, list):
                su = su[0]
            if su:
                usage_dict = _visit_state_usage(su)
                return {
                    "name": "BehaviorUsageMember",
                    "prefix": prefix,
                    "ownedRelatedElement": {
                        "name": "BehaviorUsageElement",
                        "ownedRelationship": usage_dict
                    }
                }
    
    # Fall back to general handler
    return _visit_behavior_usage_member(ctx)


def _visit_action_usage_declaration(ctx):
    """Visit an actionUsageDeclaration and return the dict.
    
    Grammar: actionUsageDeclaration: usageDeclaration? valuePart? ;
    ActionUsageDeclaration class expects:
      {"name": "ActionUsageDeclaration", "declaration": UsageDeclaration_or_None, "valuepart": ValuePart_or_None}
    """
    if ctx is None:
        return {"name": "ActionUsageDeclaration", "declaration": None, "valuepart": None}
    
    decl = None
    if hasattr(ctx, 'usageDeclaration') and ctx.usageDeclaration():
        ud = ctx.usageDeclaration()
        if isinstance(ud, list):
            ud = ud[0]
        if ud:
            # Extract name from usageDeclaration -> identification
            name = None
            shortname = None
            if hasattr(ud, 'identification') and ud.identification():
                ident = ud.identification()
                if hasattr(ident, 'name'):
                    name_list = ident.name()
                    if name_list and isinstance(name_list, list):
                        if len(name_list) == 2:
                            shortname = name_list[0].getText()
                            name = name_list[1].getText()
                        elif len(name_list) == 1:
                            name_text = name_list[0].getText()
                            if hasattr(ident, 'LT') and ident.LT() is not None:
                                shortname = name_text
                            else:
                                name = name_text
            
            # Get specialization (e.g., ': VehicleStates' or ':> Foo')
            spec = None
            typed_by = _get_action_usage_typed_by(ctx)
            if typed_by is None:
                typed_by = _get_action_usage_subsetted_by(ctx)
            if typed_by:
                spec = _build_specialization(typed_by)
            
            decl = {
                "name": "UsageDeclaration",
                "declaration": {
                    "name": "FeatureDeclaration",
                    "identification": {
                        "name": "Identification",
                        "declaredShortName": shortname,
                        "declaredName": name
                    },
                    "specialization": spec
                }
            }
    
    return {"name": "ActionUsageDeclaration", "declaration": decl, "valuepart": None}


def _visit_state_usage(ctx):
    """Visit a stateUsage context and return a StateUsage dict."""
    if ctx is None:
        return None
    
    prefix = _get_occurrence_usage_prefix(ctx)
    keyword = "state"
    
    # Get declaration
    decl = None
    if hasattr(ctx, 'actionUsageDeclaration') and ctx.actionUsageDeclaration():
        decl_dict = _visit_action_usage_declaration(ctx.actionUsageDeclaration())
        decl = decl_dict
    
    # Get body
    body = None
    if hasattr(ctx, 'stateUsageBody') and ctx.stateUsageBody():
        su_body = ctx.stateUsageBody()
        if isinstance(su_body, list):
            su_body = su_body[0]
        if su_body:
            body_dict = _visit_state_usage_body(su_body)
            body = body_dict
    
    return {
        "name": "StateUsage",
        "prefix": prefix,
        "keyword": keyword,
        "declaration": decl,
        "body": body
    }


def _visit_state_usage_body(ctx):
    """Visit a stateUsageBody context.
    
    Grammar: stateUsageBody: SEMI | (PARALLEL)? LBRACE stateBodyItem* RBRACE ;
    StateUsageBody class expects: {"name": "StateUsageBody", "body": StateDefBody_dict}
    """
    if ctx is None:
        return {
            "name": "StateUsageBody",
            "body": {"name": "StateDefBody", "part": None, "isParallel": None}
        }
    
    # stateUsageBody has stateBodyItem() directly (no stateDefBody wrapper)
    # _visit_state_def_body can handle this context since it checks stateBodyItem
    body = _visit_state_def_body(ctx)
    
    return {
        "name": "StateUsageBody",
        "body": body
    }


def _visit_source_succession_member(ctx):
    """Visit a sourceSuccessionMember (then transitions from a state)."""
    if ctx is None:
        return None
    
    prefix = None
    if hasattr(ctx, 'memberPrefix') and ctx.memberPrefix():
        mp = ctx.memberPrefix()
        if hasattr(mp, 'visibilityIndicator') and mp.visibilityIndicator():
            prefix = {
                "name": "MemberPrefix",
                "visibility": _visit_visibility_indicator_dict(mp.visibilityIndicator())
            }
    
    succession = None
    if hasattr(ctx, 'succession') and ctx.succession():
        succ = ctx.succession()
        if isinstance(succ, list):
            succ = succ[0]
        if succ:
            succession = _visit_succession(succ)
    
    return {
        "name": "SourceSuccessionMember",
        "prefix": prefix,
        "ownedRelatedElement": succession
    }


def _visit_target_transition_usage_member(ctx):
    """Visit a targetTransitionUsageMember.
    
    Grammar: targetTransitionUsageMember: memberPrefix targetTransitionUsage ;
    TargetTransitionUsageMember class expects prefix and ownedRelatedElement=TargetTransitionUsage.
    """
    if ctx is None:
        return None
    
    prefix = None
    if hasattr(ctx, 'memberPrefix') and ctx.memberPrefix():
        mp = ctx.memberPrefix()
        if hasattr(mp, 'visibilityIndicator') and mp.visibilityIndicator():
            prefix = {
                "name": "MemberPrefix",
                "visibility": _visit_visibility_indicator_dict(mp.visibilityIndicator())
            }
    
    transition_dict = None
    if hasattr(ctx, 'targetTransitionUsage') and ctx.targetTransitionUsage():
        tt = ctx.targetTransitionUsage()
        if isinstance(tt, list):
            tt = tt[0]
        if tt:
            transition_dict = _visit_target_transition_usage(tt)
    
    return {
        "name": "TargetTransitionUsageMember",
        "prefix": prefix,
        "ownedRelatedElement": transition_dict
    }


def _visit_target_transition_usage(ctx):
    """Visit a targetTransitionUsage context.
    
    Grammar: targetTransitionUsage:
      emptyParameterMember (TRANSITION ...)? (guard)? (effect)? THEN transitionSuccessionMember actionBody ;
    
    TargetTransitionUsage class expects:
      ownedRelationship1: TriggerActionMember (optional)
      ownedRelationship2: GuardExpressionMember (optional)
      ownedRelationship3: EffectBehaviorMember (optional)
      ownedRelationship4: TransitionSuccessionMember (required)
      body: ActionBody
    """
    if ctx is None:
        return None
    
    r1 = None  # TriggerActionMember
    r2 = None  # GuardExpressionMember
    r3 = None  # EffectBehaviorMember
    r4 = None  # TransitionSuccessionMember
    
    if hasattr(ctx, 'triggerActionMember') and ctx.triggerActionMember():
        tam = ctx.triggerActionMember()
        if isinstance(tam, list):
            tam = tam[0]
        if tam:
            r1 = _visit_trigger_action_member(tam)
    
    if hasattr(ctx, 'guardExpressionMember') and ctx.guardExpressionMember():
        gem = ctx.guardExpressionMember()
        if isinstance(gem, list):
            gem = gem[0]
        if gem:
            r2 = _visit_guard_expression_member(gem)
    
    if hasattr(ctx, 'effectBehaviorMember') and ctx.effectBehaviorMember():
        ebm = ctx.effectBehaviorMember()
        if isinstance(ebm, list):
            ebm = ebm[0]
        if ebm:
            r3 = _visit_effect_behavior_member(ebm)
    
    if hasattr(ctx, 'transitionSuccessionMember') and ctx.transitionSuccessionMember():
        tsm = ctx.transitionSuccessionMember()
        if isinstance(tsm, list):
            tsm = tsm[0]
        if tsm:
            r4 = _visit_transition_succession_member(tsm)
    
    body = {"name": "ActionBody", "items": []}
    if hasattr(ctx, 'actionBody') and ctx.actionBody():
        body = _visit_action_body(ctx.actionBody())
    
    return {
        "name": "TargetTransitionUsage",
        "ownedRelationship1": r1,
        "ownedRelationship2": r2,
        "ownedRelationship3": r3,
        "ownedRelationship4": r4,
        "body": body
    }


def _visit_entry_transition_member(ctx):
    """Visit an entryTransitionMember.
    
    Grammar: entryTransitionMember: memberPrefix (guardedTargetSuccession | THEN transitionSuccessionMember) SEMI ;
    
    EntryTransitionMember class expects ownedRelatedElement to be either:
    - GuardedTargetSuccession (when there's a guard)
    - TransitionSuccession (for plain 'then <state>;')
    """
    if ctx is None:
        return None
    
    prefix = None
    if hasattr(ctx, 'memberPrefix') and ctx.memberPrefix():
        mp = ctx.memberPrefix()
        if hasattr(mp, 'visibilityIndicator') and mp.visibilityIndicator():
            prefix = {
                "name": "MemberPrefix",
                "visibility": _visit_visibility_indicator_dict(mp.visibilityIndicator())
            }
    
    ownedRelatedElement = None
    
    if hasattr(ctx, 'guardedTargetSuccession') and ctx.guardedTargetSuccession():
        gts = ctx.guardedTargetSuccession()
        if isinstance(gts, list):
            gts = gts[0]
        if gts:
            ownedRelatedElement = _visit_guarded_target_succession(gts)
    elif hasattr(ctx, 'transitionSuccessionMember') and ctx.transitionSuccessionMember():
        tsm = ctx.transitionSuccessionMember()
        if isinstance(tsm, list):
            tsm = tsm[0]
        if tsm:
            # Navigate directly to transitionSuccession to get TransitionSuccession dict
            if hasattr(tsm, 'transitionSuccession') and tsm.transitionSuccession():
                ts = tsm.transitionSuccession()
                if isinstance(ts, list):
                    ts = ts[0]
                if ts:
                    ownedRelatedElement = _visit_transition_succession(ts)
    
    return {
        "name": "EntryTransitionMember",
        "prefix": prefix,
        "ownedRelatedElement": ownedRelatedElement
    }


def _visit_guarded_target_succession(ctx):
    """Visit a guardedTargetSuccession context."""
    if ctx is None:
        return None
    
    guard = None
    if hasattr(ctx, 'guardExpression') and ctx.guardExpression():
        guard_dict = _visit_expression(ctx.guardExpression())
        guard = {
            "name": "GuardExpression",
            "expression": guard_dict
        }
    
    succession = None
    if hasattr(ctx, 'succession') and ctx.succession():
        succ = ctx.succession()
        if isinstance(succ, list):
            succ = succ[0]
        if succ:
            succession = _visit_succession(succ)
    
    return {
        "name": "GuardedTargetSuccession",
        "guard": guard,
        "ownedRelatedElement": succession
    }


def _visit_succession(ctx):
    """Visit a succession context."""
    if ctx is None:
        return None
    
    owned_rel = []
    
    # Get the feature chain (source)
    if hasattr(ctx, 'featureChainMember') and ctx.featureChainMember():
        fc = ctx.featureChainMember()
        if isinstance(fc, list):
            fc = fc[0]
        if fc:
            fc_dict = _visit_feature_chain_member(fc)
            if fc_dict:
                owned_rel.append(fc_dict)
    
    # Get empty parameter members
    if hasattr(ctx, 'emptyParameterMember') and ctx.emptyParameterMember():
        members = ctx.emptyParameterMember()
        if not isinstance(members, list):
            members = [members]
        for member in members:
            member_dict = _visit_empty_parameter_member(member)
            if member_dict:
                owned_rel.append(member_dict)
    
    return {
        "name": "OwnedSuccession",
        "ownedRelationship": owned_rel
    }


def _visit_transition_succession(ctx):
    """Visit a transitionSuccession context.
    
    Grammar: transitionSuccession: emptyEndMember connectorEndMember ;
    Returns a TransitionSuccession dict.
    """
    if ctx is None:
        return None
    
    cem_dict = None
    if hasattr(ctx, 'connectorEndMember') and ctx.connectorEndMember():
        cem = ctx.connectorEndMember()
        if isinstance(cem, list):
            cem = cem[0]
        if cem:
            cem_dict = _visit_connector_end_member(cem)
    
    return {
        "name": "TransitionSuccession",
        "ownedRelationship": [cem_dict] if cem_dict else []
    }


def _visit_transition_succession_member(ctx):
    """Visit a transitionSuccessionMember context.
    
    Grammar: transitionSuccessionMember: transitionSuccession ;
    Returns a TransitionSuccessionMember dict containing a TransitionSuccession.
    """
    if ctx is None:
        return None
    
    succession = None
    if hasattr(ctx, 'transitionSuccession') and ctx.transitionSuccession():
        ts = ctx.transitionSuccession()
        if isinstance(ts, list):
            ts = ts[0]
        if ts:
            succession = _visit_transition_succession(ts)
    
    if succession is None:
        succession = {"name": "TransitionSuccession", "ownedRelationship": []}
    
    return {
        "name": "TransitionSuccessionMember",
        "ownedRelatedElement": succession
    }


def _visit_connector_end_member(ctx):
    """Visit a connectorEndMember context."""
    if ctx is None:
        return None
    
    # connectorEndMember : ownedRelatedElement += ConnectorEnd
    elements = []
    if hasattr(ctx, 'connectorEnd') and ctx.connectorEnd():
        ce = ctx.connectorEnd()
        if not isinstance(ce, list):
            ce = [ce]
        for c in ce:
            end_dict = _visit_connector_end(c)
            if end_dict:
                elements.append(end_dict)
    
    return {
        "name": "ConnectorEndMember",
        "ownedRelatedElement": elements
    }


def _visit_connector_end(ctx):
    """Visit a ConnectorEnd context.
    
    Grammar: connectorEnd: (ownedCrossMultiplicityMember)? (name (COLON_COLON_GT | REFERENCES))? ownedReferenceSubsetting ownedMultiplicity? ;
    The target state name is in ownedReferenceSubsetting (as qualifiedName), not in the connector end's name.
    The optional name before '::>' or 'references' is the declaredName.
    """
    if ctx is None:
        return None
    
    # Optional declared name (before '::>' or 'references')
    declared_name = None
    if hasattr(ctx, 'name') and ctx.name():
        n = ctx.name()
        if n:
            declared_name = n.getText()
    
    # Required ownedReferenceSubsetting — contains the target qualified name
    # For connector ends, the qualified names are separated by '.' in the grammar
    owned_rel = []
    if hasattr(ctx, 'ownedReferenceSubsetting') and ctx.ownedReferenceSubsetting():
        ors = ctx.ownedReferenceSubsetting()
        qnames = []
        if hasattr(ors, 'qualifiedName'):
            qns = ors.qualifiedName()
            if not isinstance(qns, list):
                qns = [qns]
            for qn in qns:
                if qn:
                    qnames.append(qn.getText())
        if qnames:
            # Use FeatureChain for connector ends (dumps with '.' separator)
            owned_rel.append({
                "name": "OwnedReferenceSubsetting",
                "referencedFeature": None,
                "ownedRelatedElement": [{
                    "name": "OwnedFeatureChain",
                    "feature": {
                        "name": "FeatureChain",
                        "ownedRelationship": [
                            {
                                "name": "OwnedFeatureChaining",
                                "chainingFeature": {
                                    "name": "QualifiedName",
                                    "names": [name]
                                }
                            }
                            for name in qnames
                        ]
                    }
                }]
            })
    
    # Optional ownedMultiplicity
    if hasattr(ctx, 'ownedMultiplicity') and ctx.ownedMultiplicity():
        om_ctx = ctx.ownedMultiplicity()
        mult_dict = _extract_multiplicity_from_ctx(om_ctx)
        if mult_dict:
            owned_rel.append(mult_dict)
    
    return {
        "name": "ConnectorEnd",
        "declaredName": declared_name,
        "ownedRelationship": owned_rel
    }


def _visit_state_non_behavior_body_item(ctx):
    """Visit a nonBehaviorBodyItem in state context.
    Handles documentation, annotating elements, and falls back to general handler.
    """
    if ctx is None:
        return None
    
    # Check for documentation
    if hasattr(ctx, 'documentation') and ctx.documentation():
        doc = ctx.documentation()
        if isinstance(doc, list):
            doc = doc[0]
        if doc:
            return _visit_documentation(doc)
    
    # Check for annotatingElement
    if hasattr(ctx, 'annotatingElement') and ctx.annotatingElement():
        ae = ctx.annotatingElement()
        if isinstance(ae, list):
            ae = ae[0]
        if ae:
            return _visit_annotating_element(ae)
    
    # Fall back to general handler for in/out params, parts, etc.
    return _visit_non_behavior_body_item(ctx)


def _visit_documentation(ctx):
    """Visit a documentation context."""
    if ctx is None:
        return None
    
    body = None
    if hasattr(ctx, 'documentationBody') and ctx.documentationBody():
        body_text = ctx.documentationBody().getText()
        body = body_text
    
    return {
        "name": "Documentation",
        "body": body
    }


def _visit_annotating_element(ctx):
    """Visit an annotatingElement context."""
    if ctx is None:
        return None
    
    # Check for documentation
    if hasattr(ctx, 'documentation') and ctx.documentation():
        doc = ctx.documentation()
        if isinstance(doc, list):
            doc = doc[0]
        if doc:
            doc_dict = _visit_documentation(doc)
            return {
                "name": "AnnotatingElement",
                "ownedRelatedElement": doc_dict
            }
    
    return None


def _visit_empty_parameter_member(ctx):
    """Visit an emptyParameterMember context."""
    if ctx is None:
        return None
    
    feature_chain = None
    if hasattr(ctx, 'featureChainMember') and ctx.featureChainMember():
        fc = ctx.featureChainMember()
        if isinstance(fc, list):
            fc = fc[0]
        if fc:
            feature_chain = _visit_feature_chain_member(fc)
    elif hasattr(ctx, 'emptyUsage_') and ctx.emptyUsage_():
        pass
    
    return {
        "name": "EmptyParameterMember",
        "featureChain": feature_chain
    }


def _visit_feature_chain_member(ctx):
    """Visit a featureChainMember context."""
    if ctx is None:
        return None
    
    # Check for direct qualifiedName (simple case like 'maintenanceTime')
    if hasattr(ctx, 'qualifiedName') and ctx.qualifiedName():
        qn = ctx.qualifiedName()
        if isinstance(qn, list):
            qn = qn[0]
        if qn and hasattr(qn, 'name') and qn.name():
            names = [n.getText() for n in qn.name()]
            return {
                "name": "FeatureChainMember",
                "memberElement": {
                    "name": "QualifiedName",
                    "names": names
                }
            }
    
    owned_rel = []
    
    if hasattr(ctx, 'featureReferenceMember') and ctx.featureReferenceMember():
        refs = ctx.featureReferenceMember()
        if not isinstance(refs, list):
            refs = [refs]
        for ref in refs:
            ref_dict = _visit_feature_reference_member(ref)
            if ref_dict:
                owned_rel.append(ref_dict)
    
    if owned_rel:
        return {
            "name": "FeatureChainMember",
            "ownedRelationship": owned_rel
        }
    
    return {
        "name": "FeatureChainMember",
        "ownedRelationship": []
    }


def _visit_feature_reference_member(ctx):
    """Visit a featureReferenceMember context."""
    if ctx is None:
        return None
    
    qnames = []
    if hasattr(ctx, 'qualifiedName') and ctx.qualifiedName():
        qn = ctx.qualifiedName()
        if isinstance(qn, list):
            for q in qn:
                if hasattr(q, 'name') and q.name():
                    names = [n.getText() for n in q.name()]
                    qnames.extend(names)
        else:
            if hasattr(qn, 'name') and qn.name():
                names = [n.getText() for n in qn.name()]
                qnames = names
    
    return {
        "name": "FeatureReferenceMember",
        "memberElement": {
            "name": "QualifiedName",
            "names": qnames
        }
    }


def _visit_trigger_action_member(ctx):
    """Visit a triggerActionMember context.
    
    Grammar: triggerActionMember: ACCEPT triggerAction ;
    triggerAction: acceptParameterPart ;
    TriggerActionMember class expects: {"name": "TriggerActionMember", "ownedRelatedElement": TriggerAction_dict}
    TriggerAction class expects: {"name": "TriggerAction", "part": AcceptParameterPart_dict}
    """
    if ctx is None:
        return None
    
    trigger_action = None
    if hasattr(ctx, 'triggerAction') and ctx.triggerAction():
        ta = ctx.triggerAction()
        if isinstance(ta, list):
            ta = ta[0]
        if ta:
            part = None
            if hasattr(ta, 'acceptParameterPart') and ta.acceptParameterPart():
                app = ta.acceptParameterPart()
                if isinstance(app, list):
                    app = app[0]
                if app:
                    part = _visit_accept_parameter_part(app)
            trigger_action = {
                "name": "TriggerAction",
                "part": part
            }
    
    if trigger_action is None:
        return None  # No trigger found - return None so caller skips it
    
    return {
        "name": "TriggerActionMember",
        "ownedRelatedElement": trigger_action
    }


def _visit_accept_action_usage(ctx):
    """Visit an acceptActionUsage (trigger in transition) and return a TriggerAction dict."""
    if ctx is None:
        return None
    
    # Get accept parameter part
    part = None
    if hasattr(ctx, 'acceptParameterPart') and ctx.acceptParameterPart():
        app = ctx.acceptParameterPart()
        if isinstance(app, list):
            app = app[0]
        if app:
            part = _visit_accept_parameter_part(app)
    
    return {
        "name": "TriggerAction",
        "part": part
    }


def _visit_accept_parameter_part(ctx):
    """Visit an AcceptParameterPart context."""
    if ctx is None:
        return None
    
    owned_rel = []
    
    # Get payload parameter members
    if hasattr(ctx, 'payloadParameterMember') and ctx.payloadParameterMember():
        members = ctx.payloadParameterMember()
        if not isinstance(members, list):
            members = [members]
        for member in members:
            member_dict = _visit_payload_parameter_member(member)
            if member_dict:
                owned_rel.append(member_dict)
    
    # Get node parameter members
    if hasattr(ctx, 'nodeParameterMember') and ctx.nodeParameterMember():
        members = ctx.nodeParameterMember()
        if not isinstance(members, list):
            members = [members]
        for member in members:
            member_dict = _visit_node_parameter_member(member)
            if member_dict:
                owned_rel.append(member_dict)
    
    return {
        "name": "AcceptParameterPart",
        "ownedRelationship": owned_rel
    }


def _visit_payload_parameter_member(ctx):
    """Visit a PayloadParameterMember context."""
    if ctx is None:
        return None
    
    element = None
    if hasattr(ctx, 'payloadParameter') and ctx.payloadParameter():
        pp = ctx.payloadParameter()
        if isinstance(pp, list):
            pp = pp[0]
        if pp:
            element = _visit_payload_parameter(pp)
    
    return {
        "name": "PayloadParameterMember",
        "ownedRelatedElement": element
    }


def _visit_payload_parameter(ctx):
    """Visit a PayloadParameter context."""
    if ctx is None:
        return None
    
    # Get feature reference
    feature = None
    if hasattr(ctx, 'payloadFeature') and ctx.payloadFeature():
        pf = ctx.payloadFeature()
        if pf:
            feature = _visit_payload_feature(pf)
    
    # Get identification
    identification = None
    if hasattr(ctx, 'identification') and ctx.identification():
        ident = ctx.identification()
        if ident:
            name_list = ident.name()
            if name_list and isinstance(name_list, list):
                if len(name_list) == 2:
                    shortname = name_list[0].getText()
                    name = name_list[1].getText()
                elif len(name_list) == 1:
                    name_text = name_list[0].getText()
                    name = name_text
                    shortname = None
                else:
                    name = None
                    shortname = None
            else:
                name = None
                shortname = None
            identification = {
                "name": "Identification",
                "declaredShortName": shortname,
                "declaredName": name
            }
    
    # Get trigger value part
    tvp = None
    if hasattr(ctx, 'triggerValuePart') and ctx.triggerValuePart():
        tv = ctx.triggerValuePart()
        if isinstance(tv, list):
            tv = tv[0]
        if tv:
            tvp = _visit_trigger_value_part(tv)
    
    return {
        "name": "PayloadParameter",
        "feature": feature,
        "identification": identification,
        "pfsp": None,
        "tvp": tvp
    }


def _visit_payload_feature(ctx):
    """Visit a PayloadFeature context.
    
    PayloadFeature class expects:
      identification, valuepart, multiplicity1, multiplicity2, ownedRelationship (OwnedFeatureTyping), pfsp
    For 'accept VehicleStartSignal': ownedRelationship contains the type name.
    """
    if ctx is None:
        return None
    
    owned_rel = None
    # ownedFeatureTyping contains the payload type (e.g., VehicleStartSignal)
    if hasattr(ctx, 'ownedFeatureTyping') and ctx.ownedFeatureTyping():
        oft = ctx.ownedFeatureTyping()
        if isinstance(oft, list):
            oft = oft[0]
        if oft and hasattr(oft, 'qualifiedName') and oft.qualifiedName():
            qns = oft.qualifiedName()
            if not isinstance(qns, list):
                qns = [qns]
            names = []
            for qn in qns:
                if qn:
                    names.append(qn.getText())
            if names:
                type_name = "::".join(names)
                owned_rel = {
                    "name": "OwnedFeatureTyping",
                    "type": {
                        "name": "FeatureType",
                        "type": {
                            "name": "QualifiedName",
                            "names": type_name.split("::")
                        },
                        "ownedRelatedElement": []
                    }
                }
    
    return {
        "name": "PayloadFeature",
        "identification": None,
        "valuepart": None,
        "multiplicity1": None,
        "multiplicity2": None,
        "ownedRelationship": owned_rel,
        "pfsp": None
    }


def _visit_trigger_value_part(ctx):
    """Visit a TriggerValuePart context."""
    if ctx is None:
        return None
    
    tfv_dict = None
    if hasattr(ctx, 'triggerFeatureValue') and ctx.triggerFeatureValue():
        tfv = ctx.triggerFeatureValue()
        if isinstance(tfv, list):
            tfv = tfv[0]
        if tfv:
            tfv_dict = _visit_trigger_feature_value(tfv)
    
    return {
        "name": "TriggerValuePart",
        "ownedRelationship": tfv_dict
    }


def _visit_trigger_feature_value(ctx):
    """Visit a TriggerFeatureValue context.
    
    Grammar: triggerFeatureValue : triggerExpression ;
    triggerExpression : (AT | WHEN | AFTER) argumentMember ;
    """
    if ctx is None:
        return None
    
    trigger_expr = None
    
    if hasattr(ctx, 'triggerExpression') and ctx.triggerExpression():
        te = ctx.triggerExpression()
        # Determine trigger keyword
        is_at = te.AT() is not None
        is_after = te.AFTER() is not None
        is_when = getattr(te, 'WHEN', lambda: None)() is not None
        trigger_kind = {
            "name": "TimeTriggerKind",
            "isAt": is_at,
            "isAfter": is_after,
            "isWhen": is_when
        }

        # Extract expression: (AT|AFTER) argumentMember | WHEN argumentExpressionMember
        owned_expr_member = None
        if hasattr(te, 'argumentMember') and te.argumentMember():
            am = te.argumentMember()
            if hasattr(am, 'ownedExpression') and am.ownedExpression():
                oe = am.ownedExpression()
                owned_expr = _visit_owned_expression(oe)
                owned_expr_member = {
                    "name": "OwnedExpressionMember",
                    "ownedRelatedElement": owned_expr
                }
        elif hasattr(te, 'argumentExpressionMember') and te.argumentExpressionMember():
            aem = te.argumentExpressionMember()
            if hasattr(aem, 'ownedExpression') and aem.ownedExpression():
                oe = aem.ownedExpression()
                owned_expr = _visit_owned_expression(oe)
                owned_expr_member = {
                    "name": "OwnedExpressionMember",
                    "ownedRelatedElement": owned_expr
                }

        trigger_expr = {
            "name": "TriggerExpression",
            "kind": trigger_kind,
            "ownedRelationship": owned_expr_member
        }
    
    return {
        "name": "TriggerFeatureValue",
        "ownedRelatedElement": trigger_expr
    }


def _visit_node_parameter_member(ctx):
    """Visit a NodeParameterMember context."""
    if ctx is None:
        return None
    
    element = None
    if hasattr(ctx, 'nodeParameter') and ctx.nodeParameter():
        np = ctx.nodeParameter()
        if isinstance(np, list):
            np = np[0]
        if np:
            element = _visit_node_parameter(np)
    
    return {
        "name": "NodeParameterMember",
        "ownedRelatedElement": element
    }


def _visit_node_parameter(ctx):
    """Visit a NodeParameter context."""
    if ctx is None:
        return None
    
    # Check for featureBinding (expression binding like in assignment)
    if hasattr(ctx, 'featureBinding') and ctx.featureBinding():
        fb = ctx.featureBinding()
        if hasattr(fb, 'ownedExpression') and fb.ownedExpression():
            oe = fb.ownedExpression()
            owned_expr = _visit_owned_expression(oe)
            return {
                "name": "NodeParameter",
                "ownedRelationship": {
                    "name": "FeatureBinding",
                    "ownedRelatedElement": owned_expr
                }
            }
    
    # Check for qualifiedName (simple reference)
    qnames = []
    if hasattr(ctx, 'qualifiedName') and ctx.qualifiedName():
        qn = ctx.qualifiedName()
        if isinstance(qn, list):
            for q in qn:
                if hasattr(q, 'name') and q.name():
                    names = [n.getText() for n in q.name()]
                    qnames.extend(names)
        else:
            if hasattr(qn, 'name') and qn.name():
                names = [n.getText() for n in qn.name()]
                qnames = names
    
    return {
        "name": "NodeParameter",
        "memberElement": {
            "name": "QualifiedName",
            "names": qnames
        }
    }


def _visit_guard_expression_member(ctx):
    """Visit a guardExpressionMember context."""
    if ctx is None:
        return None
    
    keyword = "if"
    if hasattr(ctx, 'GUARD') and ctx.GUARD():
        keyword = "guard"
    elif hasattr(ctx, 'IF') and ctx.IF():
        keyword = "if"
    
    owned_element = None
    if hasattr(ctx, 'ownedExpression') and ctx.ownedExpression():
        owned_element = _visit_owned_expression(ctx.ownedExpression())
    
    return {
        "name": "GuardExpressionMember",
        "keyword": keyword,
        "ownedRelatedElement": owned_element
    }


def _visit_effect_behavior_member(ctx):
    """Visit an effectBehaviorMember context."""
    if ctx is None:
        return None
    
    behavior = None
    if hasattr(ctx, 'transitionEffect') and ctx.transitionEffect():
        te = ctx.transitionEffect()
        if isinstance(te, list):
            te = te[0]
        if te:
            behavior = _visit_transition_effect(te)
    
    return {
        "name": "EffectBehaviorMember",
        "ownedRelatedElement": behavior
    }


def _visit_transition_effect(ctx):
    """Visit a transitionEffect context."""
    if ctx is None:
        return None
    
    body = None
    if hasattr(ctx, 'actionBody') and ctx.actionBody():
        body = _visit_action_body(ctx.actionBody())
    
    return {
        "name": "TransitionEffect",
        "body": body
    }


def _visit_action_body(ctx):
    """Visit an actionBody context and return an ActionBody dict."""
    if ctx is None:
        return None
    
    items = []
    if hasattr(ctx, 'actionBodyItem'):
        body_items = ctx.actionBodyItem()
        if body_items and isinstance(body_items, list):
            for item_ctx in body_items:
                item_dict = _visit_action_body_item(item_ctx)
                if item_dict:
                    items.append(item_dict)
    
    return {
        "name": "ActionBody",
        "item": items
    }


def _make_constraint_definition_dict(ctx, member_prefix=None):
    """Create a ConstraintDefinition dictionary."""
    name = None
    shortname = None
    if ctx is not None:
        dd = None
        if hasattr(ctx, 'definitionDeclaration') and ctx.definitionDeclaration():
            dd = ctx.definitionDeclaration()
        
        if dd and hasattr(dd, 'identification') and dd.identification():
            ident = dd.identification()
            if hasattr(ident, 'name'):
                name_list = ident.name()
                if name_list and isinstance(name_list, list):
                    if len(name_list) == 2:
                        shortname = name_list[0].getText()
                        name = name_list[1].getText()
                    elif len(name_list) == 1:
                        name_text = name_list[0].getText()
                        name, shortname = _extract_name_shortname(name_text)
    
    occ_prefix = _get_occurrence_definition_prefix(ctx)
    
    # Get body items from calculationBody
    body_parts = _visit_calculation_body_items(ctx)
    
    return {
        "name": "PackageMember",
        "prefix": member_prefix,
        "ownedRelatedElement": {
            "name": "DefinitionElement",
            "ownedRelatedElement": {
                "name": "ConstraintDefinition",
                "prefix": occ_prefix,
                "declaration": {
                    "name": "DefinitionDeclaration",
                    "identification": {
                        "name": "Identification",
                        "declaredShortName": shortname,
                        "declaredName": name
                    },
                    "subclassificationpart": _get_subclassification_part(ctx)
                },
                "body": {
                    "name": "CalculationBody",
                    "part": body_parts
                }
            }
        }
    }


def _make_calculation_definition_dict(ctx, member_prefix=None):
    """Create a CalculationDefinition dictionary."""
    name = None
    shortname = None
    if ctx is not None:
        dd = None
        if hasattr(ctx, 'definitionDeclaration') and ctx.definitionDeclaration():
            dd = ctx.definitionDeclaration()
        
        if dd and hasattr(dd, 'identification') and dd.identification():
            ident = dd.identification()
            if hasattr(ident, 'name'):
                name_list = ident.name()
                if name_list and isinstance(name_list, list):
                    if len(name_list) == 2:
                        shortname = name_list[0].getText()
                        name = name_list[1].getText()
                    elif len(name_list) == 1:
                        name_text = name_list[0].getText()
                        name, shortname = _extract_name_shortname(name_text)
    
    occ_prefix = _get_occurrence_definition_prefix(ctx)
    body_parts = _visit_calculation_body_items(ctx)
    return {
        "name": "PackageMember",
        "prefix": member_prefix,
        "ownedRelatedElement": {
            "name": "DefinitionElement",
            "ownedRelatedElement": {
                "name": "CalculationDefinition",
                "prefix": occ_prefix,
                "declaration": {
                    "name": "DefinitionDeclaration",
                    "identification": {
                        "name": "Identification",
                        "declaredShortName": shortname,
                        "declaredName": name
                    },
                    "subclassificationpart": _get_subclassification_part(ctx)
                },
                "body": {
                    "name": "CalculationBody",
                    "part": body_parts
                }
            }
        }
    }


def _make_connection_definition_dict(ctx, member_prefix=None):
    """Create a ConnectionDefinition dictionary.
    
    ConnectionDefinition uses 'definition' wrapper pattern (like part, item, port).
    """
    name, shortname = _get_definition_identification(ctx)
    occ_prefix = _get_occurrence_definition_prefix(ctx)
    # Get body items from definition body
    body_items = []
    if hasattr(ctx, "definition") and ctx.definition():
        defn = ctx.definition()
        if hasattr(defn, "definitionBody") and defn.definitionBody():
            body_items = _visit_definition_body_dict(defn.definitionBody())
    
    return {
        "name": "PackageMember",
        "prefix": member_prefix,
        "ownedRelatedElement": {
            "name": "DefinitionElement",
            "ownedRelatedElement": {
                "name": "ConnectionDefinition",
                "prefix": occ_prefix,
                "definition": {
                    "name": "Definition",
                    "declaration": {
                        "name": "DefinitionDeclaration",
                        "identification": {
                            "name": "Identification",
                            "declaredShortName": shortname,
                            "declaredName": name
                        },
                        "subclassificationpart": _get_subclassification_part(ctx)
                    },
                    "body": {
                        "name": "DefinitionBody",
                        "ownedRelatedElement": body_items
                    }
                }
            }
        }
    }


def _make_end_feature_usage_dict(ctx):
    """Create an EndFeatureUsage dictionary.
    
    Grammar: endFeatureUsage: endUsagePrefix featureDeclaration usageCompletion ;
    endUsagePrefix: END ownedCrossFeatureMember ;
    """
    # Get name from endUsagePrefix -> ownedCrossFeatureMember -> ownedCrossFeature -> featureDeclaration
    name = None
    shortname = None
    if hasattr(ctx, 'endUsagePrefix') and ctx.endUsagePrefix():
        eup = ctx.endUsagePrefix()
        if hasattr(eup, 'ownedCrossFeatureMember') and eup.ownedCrossFeatureMember():
            ocfm = eup.ownedCrossFeatureMember()
            if isinstance(ocfm, list):
                ocfm = ocfm[0]
            if hasattr(ocfm, 'ownedCrossFeature') and ocfm.ownedCrossFeature():
                ocf = ocfm.ownedCrossFeature()
                if isinstance(ocf, list):
                    ocf = ocf[0]
                if hasattr(ocf, 'featureDeclaration') and ocf.featureDeclaration():
                    fd = ocf.featureDeclaration()
                    if isinstance(fd, list):
                        fd = fd[0]
                    if hasattr(fd, 'featureIdentification') and fd.featureIdentification():
                        fi = fd.featureIdentification()
                        if hasattr(fi, 'name') and fi.name():
                            n = fi.name()
                            if isinstance(n, list):
                                n = n[0] if n else None
                            if n:
                                name = n.getText()
    
    # Get specialization from endUsagePrefix -> ownedCrossFeatureMember -> ownedCrossFeature -> featureDeclaration
    specialization = None
    if hasattr(ctx, 'endUsagePrefix') and ctx.endUsagePrefix():
        eup = ctx.endUsagePrefix()
        if hasattr(eup, 'ownedCrossFeatureMember') and eup.ownedCrossFeatureMember():
            ocfm = eup.ownedCrossFeatureMember()
            if isinstance(ocfm, list):
                ocfm = ocfm[0]
            if hasattr(ocfm, 'ownedCrossFeature') and ocfm.ownedCrossFeature():
                ocf = ocfm.ownedCrossFeature()
                if isinstance(ocf, list):
                    ocf = ocf[0]
                if hasattr(ocf, 'featureDeclaration') and ocf.featureDeclaration():
                    fd = ocf.featureDeclaration()
                    if isinstance(fd, list):
                        fd = fd[0]
                    if hasattr(fd, 'featureSpecializationPart') and fd.featureSpecializationPart():
                        fsp = fd.featureSpecializationPart()
                        specialization = _build_specialization_from_fsp(fsp)
    
    # Get multiplicity from featureDeclaration (direct child of EndFeatureUsage)
    multiplicity_dict = None
    if hasattr(ctx, 'featureDeclaration') and ctx.featureDeclaration():
        fd = ctx.featureDeclaration()
        if hasattr(fd, 'featureSpecializationPart') and fd.featureSpecializationPart():
            fsp = fd.featureSpecializationPart()
            if hasattr(fsp, 'multiplicityPart') and fsp.multiplicityPart():
                mp = fsp.multiplicityPart()
                multiplicity_dict = _extract_multiplicity_from_mp(mp)
    
    # Merge multiplicity into specialization if both exist
    if specialization and multiplicity_dict:
        specialization["multiplicity"] = multiplicity_dict
        specialization["multiplicity2"] = None
    
    # Get value part and body from usageCompletion
    valuepart = None
    body_items = []
    if hasattr(ctx, 'usageCompletion') and ctx.usageCompletion():
        uc = ctx.usageCompletion()
        if hasattr(uc, 'valuePart') and uc.valuePart():
            valuepart = _visit_value_part(uc.valuePart())
        if hasattr(uc, 'usageBody') and uc.usageBody():
            ub = uc.usageBody()
            if hasattr(ub, 'definitionBody') and ub.definitionBody():
                body_items = _visit_definition_body_dict(ub.definitionBody())
    
    return {
        "name": "NonOccurrenceUsageElement",
        "ownedRelatedElement": {
            "name": "EndFeatureUsage",
            "prefix": {
                "name": "EndUsagePrefix",
                "prefix": {
                    "name": "RefPrefix",
                    "isAbstract": None,
                    "isVariation": None,
                    "isReadOnly": None,
                    "isDerived": None,
                    "isEnd": "end",
                    "direction": {
                        "name": "FeatureDirection",
                        "in": "",
                        "out": "",
                        "inout": ""
                    }
                }
            },
            "usage": {
                "name": "Usage",
                "declaration": {
                    "name": "UsageDeclaration",
                    "declaration": {
                        "name": "FeatureDeclaration",
                        "identification": {
                            "name": "Identification",
                            "declaredShortName": shortname,
                            "declaredName": name
                        },
                        "specialization": specialization
                    }
                },
                "completion": {
                    "name": "UsageCompletion",
                    "valuepart": valuepart,
                    "body": {
                        "name": "UsageBody",
                        "body": {
                            "name": "DefinitionBody",
                            "ownedRelatedElement": body_items
                        }
                    }
                }
            }
        }
    }


def _make_flow_connection_definition_dict(ctx, member_prefix=None):
    """Create a FlowConnectionDefinition dictionary.
    
    FlowConnectionDefinition uses 'definition' wrapper pattern.
    """
    name, shortname = _get_definition_identification(ctx)
    occ_prefix = _get_occurrence_definition_prefix(ctx)
    # Get body items from definition body
    body_items = []
    if hasattr(ctx, "definition") and ctx.definition():
        defn = ctx.definition()
        if hasattr(defn, "definitionBody") and defn.definitionBody():
            body_items = _visit_definition_body_dict(defn.definitionBody())
    
    return {
        "name": "PackageMember",
        "prefix": member_prefix,
        "ownedRelatedElement": {
            "name": "DefinitionElement",
            "ownedRelatedElement": {
                "name": "FlowConnectionDefinition",
                "prefix": occ_prefix,
                "definition": {
                    "name": "Definition",
                    "declaration": {
                        "name": "DefinitionDeclaration",
                        "identification": {
                            "name": "Identification",
                            "declaredShortName": shortname,
                            "declaredName": name
                        },
                        "subclassificationpart": _get_subclassification_part(ctx)
                    },
                    "body": {
                        "name": "DefinitionBody",
                        "ownedRelatedElement": body_items
                    }
                }
            }
        }
    }


def _make_reference_usage_dict(ctx):
    """Create a ReferenceUsage dictionary.
    
    Grammar: referenceUsage: (endUsagePrefix | refPrefix) REF usage ;
    Example: ref :>> payload : Fuel;
    """
    # Get usage info
    name = None
    shortname = None
    specialization = None
    valuepart = None
    
    if hasattr(ctx, 'usage') and ctx.usage():
        usage = ctx.usage()
        # Get identification from usage
        if hasattr(usage, 'usageDeclaration') and usage.usageDeclaration():
            ud = usage.usageDeclaration()
            # Check for identification (name)
            if hasattr(ud, 'identification') and ud.identification():
                ident = ud.identification()
                if hasattr(ident, 'name'):
                    name_list = ident.name()
                    if name_list:
                        if isinstance(name_list, list):
                            if len(name_list) >= 1:
                                name = name_list[-1].getText()
                            if len(name_list) >= 2:
                                shortname = name_list[0].getText()
                        else:
                            name = name_list.getText()
            # Get specialization using full specialization builder
            specialization = _build_full_specialization_from_ctx(ctx)
        # Get value part
        if hasattr(usage, 'valuePart') and usage.valuePart():
            valuepart = _visit_value_part(usage.valuePart())
    
    return {
        "name": "NonOccurrenceUsageElement",
        "ownedRelatedElement": {
            "name": "ReferenceUsage",
            "prefix": {
                "name": "RefPrefix",
                "isAbstract": None,
                "isVariation": None,
                "isReadOnly": None,
                "isDerived": None,
                "isEnd": None,
                "direction": {
                    "name": "FeatureDirection",
                    "in": "",
                    "out": "",
                    "inout": ""
                }
            },
            "usage": {
                "name": "Usage",
                "declaration": {
                    "name": "UsageDeclaration",
                    "declaration": {
                        "name": "FeatureDeclaration",
                        "identification": {
                            "name": "Identification",
                            "declaredShortName": shortname,
                            "declaredName": name
                        },
                        "specialization": specialization
                    }
                },
                "completion": {
                    "name": "UsageCompletion",
                    "valuepart": valuepart,
                    "body": {
                        "name": "UsageBody",
                        "body": {
                            "name": "DefinitionBody",
                            "ownedRelatedElement": []
                        }
                    }
                }
            }
        }
    }


def _make_state_usage_dict(ctx, prefix=None):
    """Create a StateUsage dictionary for package-level state usages.
    
    State usage: state Name : TypeName { ... }
    Wrapped: PackageMember -> UsageElement -> OccurrenceUsageElement -> BehaviorUsageElement -> StateUsage
    """
    if ctx is None:
        return None
    
    # Build the declaration from actionUsageDeclaration
    decl_dict = None
    if hasattr(ctx, 'actionUsageDeclaration') and ctx.actionUsageDeclaration():
        decl_dict = _visit_action_usage_declaration(ctx.actionUsageDeclaration())
    
    # Parse the body (stateUsageBody)
    body_dict = {"name": "StateUsageBody", "body": {"name": "StateDefBody", "part": None, "isParallel": None}}
    if hasattr(ctx, 'stateUsageBody') and ctx.stateUsageBody():
        sub = ctx.stateUsageBody()
        if isinstance(sub, list):
            sub = sub[0]
        if sub:
            body_dict = _visit_state_usage_body(sub)
    
    return {
        "name": "PackageMember",
        "prefix": None,
        "ownedRelatedElement": {
            "name": "UsageElement",
            "ownedRelatedElement": {
                "name": "OccurrenceUsageElement",
                "ownedRelatedElement": {
                    "name": "BehaviorUsageElement",
                    "ownedRelationship": {
                        "name": "StateUsage",
                        "prefix": prefix,
                        "declaration": decl_dict,
                        "body": body_dict
                    }
                }
            }
        }
    }


def _make_calculation_usage_dict(ctx, prefix=None):
    """Create a CalculationUsage dictionary.
    
    calc Name ;
    Wrapped: ... -> BehaviorUsageElement -> CalculationUsage
    
    Per grammar, CalculationUsage uses actionUsageDeclaration (not calculationUsageDeclaration).
    """
    name = None
    shortname = None
    typed_by = None
    redefined_feature = None
    
    if ctx is not None:
        cud = None
        # Try both actionUsageDeclaration and calculationUsageDeclaration
        if hasattr(ctx, 'actionUsageDeclaration') and ctx.actionUsageDeclaration():
            cud = ctx.actionUsageDeclaration()
        elif hasattr(ctx, 'calculationUsageDeclaration') and ctx.calculationUsageDeclaration():
            cud = ctx.calculationUsageDeclaration()
        
        ud = None
        if cud and hasattr(cud, 'usageDeclaration') and cud.usageDeclaration():
            ud = cud.usageDeclaration()
        
        # Check for redefinitions in featureSpecializationPart
        if ud and hasattr(ud, 'featureSpecializationPart') and ud.featureSpecializationPart():
            fsp = ud.featureSpecializationPart()
            if hasattr(fsp, 'featureSpecialization') and fsp.featureSpecialization():
                specs = fsp.featureSpecialization()
                if not isinstance(specs, list):
                    specs = [specs]
                for spec in specs:
                    if hasattr(spec, 'redefinitions') and spec.redefinitions():
                        redef_text = spec.redefinitions().getText()
                        # Extract name from :>>name
                        if redef_text.startswith(':>>'):
                            redefined_feature = redef_text[3:].strip()
                            name = redefined_feature
        
        if ud and hasattr(ud, 'identification') and ud.identification():
            ident = ud.identification()
            if hasattr(ident, 'name'):
                name_list = ident.name()
                if name_list and isinstance(name_list, list):
                    if len(name_list) == 2:
                        shortname = name_list[0].getText()
                        name = name_list[1].getText()
                    elif len(name_list) == 1:
                        name_text = name_list[0].getText()
                        name, shortname = _extract_name_shortname(name_text)
        
        # Extract typed_by for the specialization
        typed_by = _get_action_usage_typed_by(ctx)
        if typed_by is None:
            typed_by = _get_action_usage_subsetted_by(ctx)
    
    spec_full = _full_specialization_for_ctx(ctx)
    if spec_full is not None:
        specialization = spec_full
    else:
        specialization = _build_specialization(typed_by) if typed_by else None
    body_parts = _visit_calculation_body_items(ctx)
    occ_prefix = _get_occurrence_usage_prefix(ctx) if ctx else None
    
    # Build declaration
    declaration = {
        "name": "CalculationUsageDeclaration",
        "declaration": {
            "name": "UsageDeclaration",
            "declaration": {
                "name": "FeatureDeclaration",
                "identification": {
                    "name": "Identification",
                    "declaredShortName": shortname,
                    "declaredName": name
                },
                "specialization": specialization
            }
        },
        "valuepart": None
    }
    
    # Build ownedRelationship for redefinitions
    owned_relationship = []
    if redefined_feature:
        owned_relationship.append({
            "name": "OwnedReferenceSubsetting",
            "referencedFeature": {
                "name": "QualifiedName",
                "names": [redefined_feature]
            },
            "ownedRelatedElement": []
        })
    
    result = {
        "name": "PackageMember",
        "prefix": None,
        "ownedRelatedElement": {
            "name": "UsageElement",
            "ownedRelatedElement": {
                "name": "OccurrenceUsageElement",
                "ownedRelatedElement": {
                    "name": "BehaviorUsageElement",
                    "ownedRelationship": {
                        "name": "CalculationUsage",
                        "prefix": occ_prefix or prefix,
                        "declaration": declaration,
                        "body": {
                            "name": "CalculationBody",
                            "part": body_parts
                        }
                    }
                }
            }
        }
    }
    
    if owned_relationship:
        result["ownedRelatedElement"]["ownedRelatedElement"]["ownedRelatedElement"]["ownedRelationship"]["ownedRelationship"] = owned_relationship
    
    return result


def _make_nested_calculation_usage_dict(ctx, prefix=None):
    """Create a CalculationUsage dict for nested usage (returns UsageElement-rooted dict)."""
    result = _make_calculation_usage_dict(ctx, prefix)
    if result and result.get("name") == "PackageMember":
        return result.get("ownedRelatedElement")
    return result


def _make_constraint_usage_dict(ctx, prefix=None):
    """Create a ConstraintUsage dictionary.
    
    constraint Name ;
    """
    name = None
    shortname = None
    typed_by = None
    if ctx is not None:
        cud = None
        # Try several possibilities
        if hasattr(ctx, 'constraintUsageDeclaration') and ctx.constraintUsageDeclaration():
            cud = ctx.constraintUsageDeclaration()
        elif hasattr(ctx, 'actionUsageDeclaration') and ctx.actionUsageDeclaration():
            cud = ctx.actionUsageDeclaration()
        elif hasattr(ctx, 'calculationUsageDeclaration') and ctx.calculationUsageDeclaration():
            cud = ctx.calculationUsageDeclaration()
        
        ud = None
        if cud and hasattr(cud, 'usageDeclaration') and cud.usageDeclaration():
            ud = cud.usageDeclaration()
        
        if ud and hasattr(ud, 'identification') and ud.identification():
            ident = ud.identification()
            if hasattr(ident, 'name'):
                name_list = ident.name()
                if name_list and isinstance(name_list, list):
                    if len(name_list) == 2:
                        shortname = name_list[0].getText()
                        name = name_list[1].getText()
                    elif len(name_list) == 1:
                        name_text = name_list[0].getText()
                        name, shortname = _extract_name_shortname(name_text)
        
        # Extract typed_by for the specialization (e.g. "constraint X : MassConstraint")
        typed_by = _get_action_usage_typed_by(ctx)
        if typed_by is None:
            typed_by = _get_action_usage_subsetted_by(ctx)
    
    spec_full = _full_specialization_for_ctx(ctx)
    if spec_full is not None:
        specialization = spec_full
    else:
        specialization = _build_specialization(typed_by) if typed_by else None
    body_parts = _visit_calculation_body_items(ctx)
    occ_prefix = _get_occurrence_usage_prefix(ctx) if ctx else None
    
    # ConstraintUsage wrapped through OccurrenceUsageElement -> BehaviorUsageElement
    return {
        "name": "PackageMember",
        "prefix": None,
        "ownedRelatedElement": {
            "name": "UsageElement",
            "ownedRelatedElement": {
                "name": "OccurrenceUsageElement",
                "ownedRelatedElement": {
                    "name": "BehaviorUsageElement",
                    "ownedRelationship": {
                        "name": "ConstraintUsage",
                        "prefix": occ_prefix or prefix,
                        "declaration": {
                            "name": "CalculationUsageDeclaration",
                            "declaration": {
                                "name": "UsageDeclaration",
                                "declaration": {
                                    "name": "FeatureDeclaration",
                                    "identification": {
                                        "name": "Identification",
                                        "declaredShortName": shortname,
                                        "declaredName": name
                                    },
                                    "specialization": specialization
                                }
                            },
                            "valuepart": None
                        },
                        "body": {
                            "name": "CalculationBody",
                            "part": body_parts
                        }
                    }
                }
            }
        }
    }


def _make_requirement_usage_dict(ctx, prefix=None):
    """Create a RequirementUsage dictionary.
    
    Grammar: requirementUsage: occurrenceUsagePrefix REQUIREMENT constraintUsageDeclaration requirementBody ;
    RequirementUsage class expects: prefix, declaration (CalculationUsageDeclaration), body (RequirementBody)
    """
    if ctx is None:
        return None
    
    name = None
    shortname = None
    typed_by = None
    
    # Extract name from constraintUsageDeclaration
    cud = None
    if hasattr(ctx, 'constraintUsageDeclaration') and ctx.constraintUsageDeclaration():
        cud = ctx.constraintUsageDeclaration()
    
    ud = None
    if cud and hasattr(cud, 'usageDeclaration') and cud.usageDeclaration():
        ud = cud.usageDeclaration()
    
    if ud and hasattr(ud, 'identification') and ud.identification():
        ident = ud.identification()
        if hasattr(ident, 'name'):
            name_list = ident.name()
            if name_list and isinstance(name_list, list):
                if len(name_list) == 2:
                    shortname = name_list[0].getText()
                    name = name_list[1].getText()
                elif len(name_list) == 1:
                    name_text = name_list[0].getText()
                    name, shortname = _extract_name_shortname(name_text)
    
    # Extract typed_by from specialization (e.g., ': VehicleMassLimitationRequirement')
    typed_by = _get_action_usage_typed_by(ctx)
    if typed_by is None:
        typed_by = _get_action_usage_subsetted_by(ctx)
    
    spec_full = _full_specialization_for_ctx(ctx)
    if spec_full is not None:
        specialization = spec_full
    else:
        specialization = _build_specialization(typed_by) if typed_by else None
    occ_prefix = _get_occurrence_usage_prefix(ctx) if ctx else None
    
    # Get requirement body items
    body_items = []
    if hasattr(ctx, 'requirementBody') and ctx.requirementBody():
        body_items = _visit_requirement_body_dict(ctx.requirementBody())
    
    return {
        "name": "PackageMember",
        "prefix": None,
        "ownedRelatedElement": {
            "name": "UsageElement",
            "ownedRelatedElement": {
                "name": "OccurrenceUsageElement",
                "ownedRelatedElement": {
                    "name": "BehaviorUsageElement",
                    "ownedRelationship": {
                        "name": "RequirementUsage",
                        "prefix": occ_prefix or prefix,
                        "declaration": {
                            "name": "CalculationUsageDeclaration",
                            "declaration": {
                                "name": "UsageDeclaration",
                                "declaration": {
                                    "name": "FeatureDeclaration",
                                    "identification": {
                                        "name": "Identification",
                                        "declaredShortName": shortname,
                                        "declaredName": name
                                    },
                                    "specialization": specialization
                                }
                            },
                            "valuepart": None
                        },
                        "body": {
                            "name": "RequirementBody",
                            "item": body_items
                        }
                    }
                }
            }
        }
    }


def _make_connection_usage_dict(ctx, prefix=None):
    """Create a ConnectionUsage dictionary."""
    name, shortname = _get_usage_identification(ctx)
    
    return {
        "name": "PackageMember",
        "prefix": None,
        "ownedRelatedElement": {
            "name": "UsageElement",
            "ownedRelatedElement": {
                "name": "OccurrenceUsageElement",
                "ownedRelatedElement": {
                    "name": "StructureUsageElement",
                    "ownedRelatedElement": {
                        "name": "ConnectionUsage",
                        "prefix": prefix,
                        "declaration": {
                            "name": "UsageDeclaration",
                            "declaration": {
                                "name": "FeatureDeclaration",
                                "identification": {
                                    "name": "Identification",
                                    "declaredShortName": shortname,
                                    "declaredName": name
                                },
                                "specialization": None
                            }
                        },
                        "part": None,
                        "body": {
                            "name": "UsageBody",
                            "body": {
                                "name": "DefinitionBody",
                                "ownedRelatedElement": []
                            }
                        }
                    }
                }
            }
        }
    }


def _make_interface_usage_dict(ctx, prefix=None):
    """Create an InterfaceUsage dictionary.
    
    interfaceUsage: occurrenceUsagePrefix INTERFACE interfaceUsageDeclaration interfaceBody
    interfaceUsageDeclaration: usageDeclaration? valuePart? (CONNECT interfacePart)?
    
    interfacePart: binaryInterfacePart | naryInterfacePart
    binaryInterfacePart: interfaceEndMember TO interfaceEndMember
    naryInterfacePart: LPAREN interfaceEndMember COMMA interfaceEndMember (COMMA interfaceEndMember)* RPAREN
    
    interfaceEndMember: interfaceEnd
    interfaceEnd: (ownedCrossMultiplicityMember)? (name (COLON_COLON_GT | REFERENCES))? ownedReferenceSubsetting
    """
    name = None
    shortname = None
    typed_by = None
    interface_part = None
    if ctx is not None:
        aud = None
        if hasattr(ctx, 'interfaceUsageDeclaration') and ctx.interfaceUsageDeclaration():
            aud = ctx.interfaceUsageDeclaration()
            if isinstance(aud, list):
                aud = aud[0] if aud else None
        
        ud = None
        if aud and hasattr(aud, 'usageDeclaration') and aud.usageDeclaration():
            ud = aud.usageDeclaration()
            if isinstance(ud, list):
                ud = ud[0] if ud else None
        
        if ud and hasattr(ud, 'identification') and ud.identification():
            ident = ud.identification()
            if isinstance(ident, list):
                ident = ident[0] if ident else None
            if hasattr(ident, 'name'):
                name_list = ident.name()
                if name_list and isinstance(name_list, list):
                    if len(name_list) == 2:
                        shortname = name_list[0].getText()
                        name = name_list[1].getText()
                    elif len(name_list) == 1:
                        name_text = name_list[0].getText()
                        name, shortname = _extract_name_shortname(name_text)
        
        if ud and hasattr(ud, 'featureSpecializationPart') and ud.featureSpecializationPart():
            fsp = ud.featureSpecializationPart()
            if isinstance(fsp, list):
                fsp = fsp[0] if fsp else None
            if fsp and hasattr(fsp, 'featureSpecialization') and fsp.featureSpecialization():
                specs = fsp.featureSpecialization()
                if not isinstance(specs, list):
                    specs = [specs]
                for spec in specs:
                    if hasattr(spec, 'typings') and spec.typings():
                        typings = spec.typings()
                        if isinstance(typings, list):
                            typings = typings[0] if typings else None
                        if typings and hasattr(typings, 'getText'):
                            text = typings.getText()
                            if text.startswith(':'):
                                typed_by = text[1:].strip()
                                break
        
        if aud and hasattr(aud, 'interfacePart') and aud.interfacePart():
            interface_part = aud.interfacePart()
            if isinstance(interface_part, list):
                interface_part = interface_part[0] if interface_part else None
    
    occ_prefix = _get_occurrence_usage_prefix(ctx)
    
    body_items = []
    if hasattr(ctx, 'interfaceBody') and ctx.interfaceBody():
        body_ctx = ctx.interfaceBody()
        if hasattr(body_ctx, 'interfaceBodyItem') and body_ctx.interfaceBodyItem():
            for item_ctx in body_ctx.interfaceBodyItem():
                item_dict = _visit_definition_body_item_dict(item_ctx, is_interface=True)
                if item_dict:
                    body_items.append(item_dict)
    
    spec_full = _full_specialization_for_ctx(ctx)
    if spec_full is not None:
        specialization = spec_full
    else:
        specialization = _build_specialization(typed_by) if typed_by else None
    
    interface_end_members = []
    if interface_part:
        if hasattr(interface_part, 'binaryInterfacePart') and interface_part.binaryInterfacePart():
            bip = interface_part.binaryInterfacePart()
            if isinstance(bip, list):
                bip = bip[0] if bip else None
            if bip:
                end_members_list = bip.interfaceEndMember() if hasattr(bip, 'interfaceEndMember') else []
                if isinstance(end_members_list, list) and len(end_members_list) >= 1:
                    end1 = _visit_interface_end_member(end_members_list[0])
                    if end1:
                        interface_end_members.append(end1)
                if isinstance(end_members_list, list) and len(end_members_list) >= 2:
                    end2 = _visit_interface_end_member(end_members_list[1])
                    if end2:
                        interface_end_members.append(end2)
        elif hasattr(interface_part, 'naryInterfacePart') and interface_part.naryInterfacePart():
            nip = interface_part.naryInterfacePart()
            if isinstance(nip, list):
                nip = nip[0] if nip else None
            if nip and hasattr(nip, 'interfaceEndMember') and nip.interfaceEndMember():
                end_members = nip.interfaceEndMember()
                if isinstance(end_members, list):
                    for em in end_members:
                        end = _visit_interface_end_member(em)
                        if end:
                            interface_end_members.append(end)
    
    decl_dict = {
        "name": "InterfaceUsageDeclaration",
        "declaration": {
            "name": "UsageDeclaration",
            "declaration": {
                "name": "FeatureDeclaration",
                "identification": {
                    "name": "Identification",
                    "declaredShortName": shortname,
                    "declaredName": name
                },
                "specialization": specialization
            }
        },
        "part1": {
            "name": "InterfacePart",
            "binarypart": {
                "name": "BinaryInterfacePart",
                "ownedRelationship": [
                    {"name": "InterfaceEndMember", "ownedRelatedElement": end}
                    for end in interface_end_members
                ]
            }
        },
        "part2": None
    }
    
    if interface_end_members:
        interface_body = {
            "name": "InterfaceBody",
            "item": body_items
        }
    else:
        interface_body = None if not body_items else {
            "name": "InterfaceBody",
            "item": body_items
        }
    
    return {
        "name": "PackageMember",
        "prefix": None,
        "ownedRelatedElement": {
            "name": "UsageElement",
            "ownedRelatedElement": {
                "name": "OccurrenceUsageElement",
                "ownedRelatedElement": {
                    "name": "StructureUsageElement",
                    "ownedRelatedElement": {
                        "name": "InterfaceUsage",
                        "prefix": occ_prefix or prefix,
                        "declaration": decl_dict,
                        "body": interface_body
                    }
                }
            }
        }
    }


def _visit_interface_end_member(em_ctx):
    """Visit an interface end member and return an InterfaceEnd dict.
    
    interfaceEnd: (ownedCrossMultiplicityMember)? (name (COLON_COLON_GT | REFERENCES))? ownedReferenceSubsetting
    """
    end_dict = {
        "name": "InterfaceEnd",
        "declaredName": None,
        "ownedRelationship": []
    }
    
    if em_ctx is None:
        return end_dict
    
    if hasattr(em_ctx, 'interfaceEnd') and em_ctx.interfaceEnd():
        iface_end = em_ctx.interfaceEnd()
        if isinstance(iface_end, list):
            iface_end = iface_end[0] if iface_end else None
        
        if iface_end:
            end_dict = {
                "name": "InterfaceEnd",
                "declaredName": None,
                "ownedRelationship": []
            }
            
            if hasattr(iface_end, 'name') and iface_end.name():
                names = iface_end.name()
                if isinstance(names, list):
                    end_dict["declaredName"] = names[0].getText() if names else None
                else:
                    end_dict["declaredName"] = names.getText() if hasattr(names, 'getText') else None
            
            if hasattr(iface_end, 'ownedReferenceSubsetting') and iface_end.ownedReferenceSubsetting():
                ref = iface_end.ownedReferenceSubsetting()
                if isinstance(ref, list):
                    ref = ref[0] if ref else None
                if ref:
                    ref_subset = _visit_reference_subsetting(ref)
                    if ref_subset:
                        end_dict["ownedRelationship"].append(ref_subset)
            
            if hasattr(iface_end, 'ownedCrossMultiplicityMember') and iface_end.ownedCrossMultiplicityMember():
                mult = iface_end.ownedCrossMultiplicityMember()
                if isinstance(mult, list):
                    mult = mult[0] if mult else None
                if mult:
                    mult_dict = _visit_multiplicity(mult)
                    if mult_dict:
                        end_dict["ownedRelationship"].append(mult_dict)
    
    return end_dict


def _visit_reference_subsetting(ref_ctx):
    """Visit an owned reference subsetting and return a dict.
    
    ownedReferenceSubsetting: qualifiedName (DOT qualifiedName)*
    """
    result = {
        "name": "OwnedReferenceSubsetting",
        "referencedFeature": None,
        "ownedRelatedElement": []
    }
    
    if ref_ctx is None:
        return result
    
    chaining_items = []
    current_name = []
    
    def process_qname(qn_ctx):
        if hasattr(qn_ctx, 'name') and qn_ctx.name():
            name_list = qn_ctx.name()
            if isinstance(name_list, list):
                return [n.getText() for n in name_list]
            elif hasattr(name_list, 'getText'):
                return [name_list.getText()]
        return []
    
    if hasattr(ref_ctx, 'qualifiedName') and ref_ctx.qualifiedName():
        qn_list = ref_ctx.qualifiedName()
        if not isinstance(qn_list, list):
            qn_list = [qn_list]
        
        first = True
        for qn in qn_list:
            names = process_qname(qn)
            if names:
                if first and not chaining_items:
                    current_name.extend(names)
                    first = False
                else:
                    if current_name:
                        chaining_items.append({
                            "name": "OwnedFeatureChaining",
                            "chainingFeature": {"name": "QualifiedName", "names": current_name}
                        })
                    current_name = names
    
    if current_name:
        chaining_items.append({
            "name": "OwnedFeatureChaining",
            "chainingFeature": {"name": "QualifiedName", "names": current_name}
        })
    
    if chaining_items:
        result["ownedRelatedElement"].append({
            "name": "OwnedFeatureChain",
            "feature": {
                "name": "FeatureChain",
                "ownedRelationship": chaining_items
            }
        })
    
    return result


def _build_reference_subsetting_from_ctx(rs_ctx):
    """Build an OwnedReferenceSubsetting dict from a referenceSubsetting context."""
    result = {
        "name": "OwnedReferenceSubsetting",
        "referencedFeature": None,
        "ownedRelatedElement": []
    }
    
    if rs_ctx is None:
        return result
    
    if hasattr(rs_ctx, 'ownedRelatedElement') and rs_ctx.ownedRelatedElement():
        ore_list = rs_ctx.ownedRelatedElement()
        if not isinstance(ore_list, list):
            ore_list = [ore_list]
        
        for ore in ore_list:
            if hasattr(ore, 'featureReference') and ore.featureReference():
                fr = ore.featureReference()
                if isinstance(fr, list):
                    fr = fr[0] if fr else None
                if fr:
                    ref_dict = _build_feature_reference_from_ctx(fr)
                    if ref_dict:
                        result["ownedRelatedElement"].append(ref_dict)
            elif hasattr(ore, 'referenceSubsetting') and ore.referenceSubsetting():
                sub_rs = ore.referenceSubsetting()
                if isinstance(sub_rs, list):
                    sub_rs = sub_rs[0] if sub_rs else None
                if sub_rs:
                    sub_result = _build_reference_subsetting_from_ctx(sub_rs)
                    result["ownedRelatedElement"].append(sub_result)
            elif hasattr(ore, 'ownedFeatureChain') and ore.ownedFeatureChain():
                fc = ore.ownedFeatureChain()
                if isinstance(fc, list):
                    fc = fc[0] if fc else None
                if fc:
                    fc_dict = _build_feature_chain_from_ctx(fc)
                    if fc_dict:
                        result["ownedRelatedElement"].append(fc_dict)
    
    if hasattr(rs_ctx, 'referencedFeature') and rs_ctx.referencedFeature():
        rf = rs_ctx.referencedFeature()
        if isinstance(rf, list):
            rf = rf[0] if rf else None
        if rf and hasattr(rf, 'qualifiedName') and rf.qualifiedName():
            qn = rf.qualifiedName()
            if isinstance(qn, list):
                qn = qn[0] if qn else None
            if qn and hasattr(qn, 'name'):
                names_list = qn.name()
                if isinstance(names_list, list):
                    names = [n.getText() for n in names_list]
                elif hasattr(names_list, 'getText'):
                    names = [names_list.getText()]
                else:
                    names = []
                result["referencedFeature"] = {
                    "name": "QualifiedName",
                    "names": names
                }
    
    return result


def _build_feature_chain_from_ctx(fc_ctx):
    """Build a FeatureChain dict from a featureChain context."""
    result = {
        "name": "OwnedFeatureChain",
        "feature": {
            "name": "FeatureChain",
            "ownedRelationship": []
        }
    }
    
    if fc_ctx is None:
        return result
    
    if hasattr(fc_ctx, 'ownedRelatedElement') and fc_ctx.ownedRelatedElement():
        ore_list = fc_ctx.ownedRelatedElement()
        if not isinstance(ore_list, list):
            ore_list = [ore_list]
        
        for ore in ore_list:
            chaining_dict = _build_feature_chaining_from_ctx(ore)
            if chaining_dict:
                result["feature"]["ownedRelationship"].append(chaining_dict)
    
    return result


def _build_feature_chaining_from_ctx(ch_ctx):
    """Build an OwnedFeatureChaining dict from a context."""
    result = {
        "name": "OwnedFeatureChaining",
        "chainingFeature": {
            "name": "QualifiedName",
            "names": []
        }
    }
    
    if ch_ctx is None:
        return result
    
    if hasattr(ch_ctx, 'qualifiedName') and ch_ctx.qualifiedName():
        qn = ch_ctx.qualifiedName()
        if isinstance(qn, list):
            qn = qn[0] if qn else None
        if qn and hasattr(qn, 'name'):
            names_list = qn.name()
            if isinstance(names_list, list):
                names = [n.getText() for n in names_list]
            elif hasattr(names_list, 'getText'):
                names = [names_list.getText()]
            else:
                names = []
            result["chainingFeature"]["names"] = names
    
    return result


def _build_feature_reference_from_ctx(fr_ctx):
    """Build a FeatureReference dict from a featureReference context."""
    result = {
        "name": "FeatureReference",
        "ownedRelatedElement": []
    }
    
    if fr_ctx is None:
        return result
    
    if hasattr(fr_ctx, 'ownedRelatedElement') and fr_ctx.ownedRelatedElement():
        ore_list = fr_ctx.ownedRelatedElement()
        if not isinstance(ore_list, list):
            ore_list = [ore_list]
        
        for ore in ore_list:
            chaining_dict = _build_feature_chaining_from_ctx(ore)
            if chaining_dict:
                result["ownedRelatedElement"].append(chaining_dict)
    
    return result


def _visit_multiplicity(mult_ctx):
    """Visit a multiplicity and return a dict."""
    result = {"name": "OwnedMultiplicity"}
    
    if mult_ctx is None:
        return result
    
    if hasattr(mult_ctx, 'ownedRelatedElement') and mult_ctx.ownedRelatedElement():
        related = mult_ctx.ownedRelatedElement()
        if isinstance(related, list):
            related = related[0] if related else None
        if related and hasattr(related, 'multiplicity') and related.multiplicity():
            mult = related.multiplicity()
            if isinstance(mult, list):
                mult = mult[0] if mult else None
            if mult:
                result = _build_multiplicity_from_ctx(mult)
    
    return result


def _extract_multiplicity_from_ctx(om_ctx):
    """Extract multiplicity from an OwnedMultiplicityContext and return a dict."""
    if om_ctx is None:
        return None
    
    try:
        omrc = om_ctx.ownedMultiplicityRange()
        if omrc is None:
            return None
        bounds = omrc.multiplicityBounds()
        if bounds is None:
            return None
        members = bounds.multiplicityExpressionMember()
        if not isinstance(members, list):
            members = [members] if members else []
        
        def _make_bound(value_text):
            if value_text == '*':
                return {
                    "name": "MultiplicityExpressionMember",
                    "ownedRelatedElement": [
                        {"name": "MultiplicityRelatedElement", "ownedRelatedElement":
                            {"name": "LiteralInfinity", "value": "*"}
                        }
                    ]
                }
            else:
                return {
                    "name": "MultiplicityExpressionMember",
                    "ownedRelatedElement": [
                        {"name": "MultiplicityRelatedElement", "ownedRelatedElement":
                            {"name": "LiteralInteger", "value": int(value_text)}
                        }
                    ]
                }
        
        if len(members) == 1:
            bound_dicts = [_make_bound(members[0].getText())]
        elif len(members) == 2:
            bound_dicts = [_make_bound(members[0].getText()), _make_bound(members[1].getText())]
        else:
            return None
        
        return {
            "name": "OwnedMultiplicity",
            "ownedRelatedElement": [
                {
                    "name": "MultiplicityRange",
                    "ownedRelationship": bound_dicts
                }
            ]
        }
    except (IndexError, AttributeError):
        return None


def _extract_multiplicity_from_mp(mp_ctx):
    """Extract multiplicity from a MultiplicityPartContext and return a dict."""
    if mp_ctx is None:
        return None
    
    try:
        # MultiplicityPart -> OwnedMultiplicity -> OwnedMultiplicityRange -> MultiplicityBounds
        omc = mp_ctx.ownedMultiplicity()
        if isinstance(omc, list):
            omc = omc[0] if omc else None
        if omc is None:
            return None
        omrc = omc.ownedMultiplicityRange()
        if omrc is None:
            return None
        bounds = omrc.multiplicityBounds()
        if bounds is None:
            return None
        members = bounds.multiplicityExpressionMember()
        if not isinstance(members, list):
            members = [members] if members else []
        
        def _make_bound(value_text):
            if value_text == '*':
                return {
                    "name": "MultiplicityExpressionMember",
                    "ownedRelatedElement": [
                        {"name": "MultiplicityRelatedElement", "ownedRelatedElement":
                            {"name": "LiteralInfinity", "value": "*"}
                        }
                    ]
                }
            else:
                return {
                    "name": "MultiplicityExpressionMember",
                    "ownedRelatedElement": [
                        {"name": "MultiplicityRelatedElement", "ownedRelatedElement":
                            {"name": "LiteralInteger", "value": int(value_text)}
                        }
                    ]
                }
        
        if len(members) == 1:
            bound_dicts = [_make_bound(members[0].getText())]
        elif len(members) == 2:
            bound_dicts = [_make_bound(members[0].getText()), _make_bound(members[1].getText())]
        else:
            return None
        
        return {
            "name": "MultiplicityPart",
            "isOrdered": False,
            "isNonunique": False,
            "ownedRelationship": [
                {
                    "name": "OwnedMultiplicity",
                    "ownedRelatedElement": [
                        {
                            "name": "MultiplicityRange",
                            "ownedRelationship": bound_dicts
                        }
                    ]
                }
            ]
        }
    except (IndexError, AttributeError):
        return None



def _build_item_feature_member_from_payload(pfm_ctx):
    """Build an ItemFeatureMember dict from a (flow)payloadFeatureMember context.
    
    This handles the 'of TYPE' clause in flow connections, like 'flow of Fuel from ... to ...'.
    
    Grammar:
      payloadFeatureMember : payloadFeature ;
      flowPayloadFeatureMember : flowPayloadFeature ;
      flowPayloadFeature : payloadFeature ;
      payloadFeature
          : identification? valuePart
          | identification? payloadFeatureSpecializationPart valuePart?
          | ownedFeatureTyping (ownedMultiplicity)?
          | ownedMultiplicity (ownedFeatureTyping)?
          ;
    """
    if pfm_ctx is None:
        return None
    
    # Drill down to payloadFeature
    pf = None
    if hasattr(pfm_ctx, 'payloadFeature') and pfm_ctx.payloadFeature():
        pf = pfm_ctx.payloadFeature()
    elif hasattr(pfm_ctx, 'flowPayloadFeature') and pfm_ctx.flowPayloadFeature():
        fpf = pfm_ctx.flowPayloadFeature()
        if hasattr(fpf, 'payloadFeature') and fpf.payloadFeature():
            pf = fpf.payloadFeature()
    
    if pf is None:
        return None
    
    # Extract the type name (e.g. "Fuel") from ownedFeatureTyping
    type_name = None
    if hasattr(pf, 'ownedFeatureTyping') and pf.ownedFeatureTyping():
        oft = pf.ownedFeatureTyping()
        if hasattr(oft, 'qualifiedName') and oft.qualifiedName():
            qn = oft.qualifiedName()
            if hasattr(qn, 'name') and qn.name():
                names = [n.getText() for n in qn.name()]
                type_name = names
    
    if type_name is None:
        # Fallback: use the full text
        text = pf.getText()
        if text:
            type_name = [text]
        else:
            return None
    
    return {
        "name": "ItemFeatureMember",
        "ownedRelatedElement": [{
            "name": "ItemFeature",
            "ownedRelatedElement": {
                "name": "PayloadFeature",
                "identification": None,
                "valuepart": None,
                "multiplicity1": None,
                "multiplicity2": None,
                "ownedRelationship": {
                    "name": "OwnedFeatureTyping",
                    "type": {
                        "name": "FeatureType",
                        "type": {
                            "name": "QualifiedName",
                            "names": type_name
                        },
                        "ownedRelatedElement": []
                    }
                },
                "pfsp": None
            }
        }]
    }


def _make_nested_flow_connection_usage_dict(ctx, prefix=None):
    """Create a nested FlowConnectionUsage dictionary (for use inside action bodies)."""
    name = None
    shortname = None
    from_end = None
    to_end = None
    of_payload = None
    
    if ctx is not None:
        fd = None
        if hasattr(ctx, 'flowDeclaration') and ctx.flowDeclaration():
            fd = ctx.flowDeclaration()
        elif hasattr(ctx, 'flowConnectionDeclaration') and ctx.flowConnectionDeclaration():
            fd = ctx.flowConnectionDeclaration()
        
        if fd:
            # Extract flow ends (FROM x TO y)
            if hasattr(fd, 'flowEndMember') and fd.flowEndMember():
                flow_ends = fd.flowEndMember()
                if isinstance(flow_ends, list) and len(flow_ends) >= 2:
                    from_end = _build_flow_end_member_dict(flow_ends[0])
                    to_end = _build_flow_end_member_dict(flow_ends[1])
            
            # Extract optional 'of' payload (e.g., "of Fuel")
            pfm = None
            if hasattr(fd, 'flowPayloadFeatureMember') and fd.flowPayloadFeatureMember():
                pfm = fd.flowPayloadFeatureMember()
            elif hasattr(fd, 'payloadFeatureMember') and fd.payloadFeatureMember():
                pfm = fd.payloadFeatureMember()
            if pfm is not None:
                of_payload = _build_item_feature_member_from_payload(pfm)
            
            # Get name from featureDeclaration or usageDeclaration
            if hasattr(fd, 'featureDeclaration') and fd.featureDeclaration():
                featd = fd.featureDeclaration()
                if hasattr(featd, 'featureIdentification') and featd.featureIdentification():
                    fi = featd.featureIdentification()
                    if hasattr(fi, 'name') and fi.name():
                        name_res = fi.name()
                        if isinstance(name_res, list):
                            if len(name_res) == 2:
                                shortname = name_res[0].getText()
                                name = name_res[1].getText()
                            elif len(name_res) == 1:
                                name_text = name_res[0].getText()
                                name, shortname = _extract_name_shortname(name_text)
                    else:
                        text = fi.getText()
                        if text:
                            name, shortname = _extract_name_shortname(text)
            elif hasattr(fd, 'usageDeclaration') and fd.usageDeclaration():
                ud = fd.usageDeclaration()
                if ud and hasattr(ud, 'identification') and ud.identification():
                    ident = ud.identification()
                    if hasattr(ident, 'name'):
                        name_list = ident.name()
                        if name_list and isinstance(name_list, list):
                            if len(name_list) == 2:
                                shortname = name_list[0].getText()
                                name = name_list[1].getText()
                        elif len(name_list) == 1:
                            name_text = name_list[0].getText()
                            if hasattr(ident, 'LT') and ident.LT() is not None:
                                shortname = name_text
                            else:
                                name = name_text
            
            if not name and not shortname:
                name, shortname = _get_usage_identification(ctx)
    
    # Extract specialization from featureDeclaration
    specialization = None
    if ctx is not None:
        fd = None
        if hasattr(ctx, 'flowDeclaration') and ctx.flowDeclaration():
            fd = ctx.flowDeclaration()
        elif hasattr(ctx, 'flowConnectionDeclaration') and ctx.flowConnectionDeclaration():
            fd = ctx.flowConnectionDeclaration()
        
        if fd and hasattr(fd, 'featureDeclaration') and fd.featureDeclaration():
            featd = fd.featureDeclaration()
            if hasattr(featd, 'featureSpecializationPart') and featd.featureSpecializationPart():
                fsp = featd.featureSpecializationPart()
                specialization = _build_specialization_from_fsp(fsp)
    
    # Build declaration - omit declaration if no name/shortname (e.g. anonymous flow)
    inner_declaration = None
    if name or shortname or specialization:
        inner_declaration = {
            "name": "UsageDeclaration",
            "declaration": {
                "name": "FeatureDeclaration",
                "identification": {
                    "name": "Identification",
                    "declaredShortName": shortname,
                    "declaredName": name
                },
                "specialization": specialization
            }
        }
    
    return {
        "name": "UsageElement",
        "ownedRelatedElement": {
            "name": "OccurrenceUsageElement",
            "ownedRelatedElement": {
                "name": "StructureUsageElement",
                "ownedRelatedElement": {
                    "name": "FlowConnectionUsage",
                    "prefix": prefix,
                    "declaration": {
                        "name": "FlowConnectionDeclaration",
                        "declaration": inner_declaration,
                        "valuepart": None,
                        "ownedRelationship_of": of_payload,
                        "ownedRelationship_from": from_end,
                        "ownedRelationship_to": to_end
                    },
                    "body": {
                        "name": "DefinitionBody",
                        "ownedRelatedElement": []
                    }
                }
            }
        }
}


def _make_nested_succession_flow_usage_dict(ctx, prefix=None):
    """Create a nested SuccessionFlowConnectionUsage dictionary.
    
    Grammar:
      successionFlowUsage
        : occurrenceUsagePrefix SUCCESSION FLOW flowDeclaration definitionBody
    """
    name = None
    shortname = None
    from_end = None
    to_end = None
    
    if ctx is not None:
        fd = None
        if hasattr(ctx, 'flowDeclaration') and ctx.flowDeclaration():
            fd = ctx.flowDeclaration()
        
        if fd:
            # Extract flow ends (FROM x TO y)
            if hasattr(fd, 'flowEndMember') and fd.flowEndMember():
                flow_ends = fd.flowEndMember()
                if isinstance(flow_ends, list) and len(flow_ends) >= 2:
                    from_end = _build_flow_end_member_dict(flow_ends[0])
                    to_end = _build_flow_end_member_dict(flow_ends[1])
            
            # Get name from usageDeclaration
            if hasattr(fd, 'usageDeclaration') and fd.usageDeclaration():
                ud = fd.usageDeclaration()
                if ud and hasattr(ud, 'identification') and ud.identification():
                    ident = ud.identification()
                    if hasattr(ident, 'name'):
                        name_list = ident.name()
                        if name_list and isinstance(name_list, list):
                            if len(name_list) == 2:
                                shortname = name_list[0].getText()
                                name = name_list[1].getText()
                        elif len(name_list) == 1:
                            name_text = name_list[0].getText()
                            name = name_text
    
    declaration = None
    if name or shortname:
        declaration = {
            "name": "UsageDeclaration",
            "declaration": {
                "name": "FeatureDeclaration",
                "identification": {
                    "name": "Identification",
                    "declaredShortName": shortname,
                    "declaredName": name
                },
                "specialization": specialization
            }
        }
    else:
        declaration = {
            "name": "FlowConnectionDeclaration",
            "declaration": None,
            "valuepart": None,
            "ownedRelationship_of": None,
            "ownedRelationship_from": from_end,
            "ownedRelationship_to": to_end
        }
    
    return {
        "name": "UsageElement",
        "ownedRelatedElement": {
            "name": "OccurrenceUsageElement",
            "ownedRelatedElement": {
                "name": "StructureUsageElement",
                "ownedRelatedElement": {
                    "name": "SuccessionFlowConnectionUsage",
                    "prefix": prefix,
                    "declaration": declaration,
                    "body": {
                        "name": "DefinitionBody",
                        "ownedRelatedElement": []
                    }
                }
            }
        }
    }


def _make_nested_perform_action_usage_dict(ctx, prefix=None):
    """Create a nested PerformActionUsage dictionary.
    
    Grammar:
      performActionUsage
        : occurrenceUsagePrefix PERFORM performActionUsageDeclaration actionBody
        ;
      performActionUsageDeclaration
        : (ownedReferenceSubsetting featureSpecializationPart? | ACTION usageDeclaration?) valuePart?
        ;
    """
    if ctx is None:
        return None
    
    occ_prefix = _get_occurrence_usage_prefix(ctx)
    if prefix is not None:
        occ_prefix = prefix
    
    # Extract from performActionUsageDeclaration
    decl_dict = None
    if hasattr(ctx, 'performActionUsageDeclaration') and ctx.performActionUsageDeclaration():
        decl_dict = _visit_perform_action_usage_declaration(ctx.performActionUsageDeclaration())
    
    # Get body items from action body
    action_items = []
    if hasattr(ctx, 'actionBody') and ctx.actionBody():
        action_body = ctx.actionBody()
        if hasattr(action_body, 'actionBodyItem') and action_body.actionBodyItem():
            for abi_ctx in action_body.actionBodyItem():
                item_dict = _visit_action_body_item(abi_ctx)
                if item_dict:
                    action_items.append(item_dict)
    
    return {
        "name": "UsageElement",
        "ownedRelatedElement": {
            "name": "OccurrenceUsageElement",
            "ownedRelatedElement": {
                "name": "BehaviorUsageElement",
                "ownedRelationship": {
                    "name": "PerformActionUsage",
                    "prefix": occ_prefix,
                    "declaration": decl_dict,
                    "body": {
                        "name": "ActionBody",
                        "items": action_items
                    }
                }
            }
        }
    }


def _make_nested_connection_usage_dict(ctx, prefix=None):
    """Create a nested ConnectionUsage dictionary (for use inside interface/action bodies).
    
    Grammar:
      connectionUsage
        : occurrenceUsagePrefix (
            CONNECTION usageDeclaration? valuePart? ( CONNECT connectorPart)?
            | CONNECT connectorPart
        ) usageBody
      ;
    """
    name = None
    shortname = None
    connector_part = None
    specialization = None
    
    if ctx is not None:
        # Try to get name and specialization from usageDeclaration
        if hasattr(ctx, 'usageDeclaration') and ctx.usageDeclaration():
            ud = ctx.usageDeclaration()
            # Check for identification (name)
            if hasattr(ud, 'identification') and ud.identification():
                ident = ud.identification()
                if hasattr(ident, 'name'):
                    name_list = ident.name()
                    if name_list and isinstance(name_list, list):
                        if len(name_list) == 2:
                            shortname = name_list[0].getText()
                            name = name_list[1].getText()
                        elif len(name_list) == 1:
                            name = name_list[0].getText()
            # Check for featureSpecializationPart (typing like : PressureSeat)
            if hasattr(ud, 'featureSpecializationPart') and ud.featureSpecializationPart():
                fsp = ud.featureSpecializationPart()
                specialization = _build_specialization_from_fsp(fsp)
        
        # Get connectorPart (e.g., "suppliedBy.hot to deliveredTo.hot")
        if hasattr(ctx, 'connectorPart') and ctx.connectorPart():
            cp = ctx.connectorPart()
            connector_part = _build_connector_part_dict(cp)
    
    # Build declaration
    declaration = None
    if name or shortname or specialization:
        declaration = {
            "name": "UsageDeclaration",
            "declaration": {
                "name": "FeatureDeclaration",
                "identification": {
                    "name": "Identification",
                    "declaredShortName": shortname,
                    "declaredName": name
                },
                "specialization": specialization
            }
        }
    
    return {
        "name": "UsageElement",
        "ownedRelatedElement": {
            "name": "OccurrenceUsageElement",
            "ownedRelatedElement": {
                "name": "StructureUsageElement",
                "ownedRelatedElement": {
                    "name": "ConnectionUsage",
                    "prefix": prefix,
                    "declaration": declaration,
                    "part": connector_part,
                    "body": {
                        "name": "UsageBody",
                        "body": {
                            "name": "DefinitionBody",
                            "ownedRelatedElement": []
                        }
                    }
                }
            }
        }
    }


def _build_connector_part_dict(ctx):
    """Build a ConnectorPart dictionary from a connectorPart context.

    Grammar:
      connectorPart : binaryConnectorPart | naryConnectorPart ;
      binaryConnectorPart : connectorEndMember TO connectorEndMember ;
      naryConnectorPart : LPAREN connectorEndMember (COMMA connectorEndMember)* RPAREN ;
    """
    if ctx is None:
        return None

    if hasattr(ctx, 'binaryConnectorPart') and ctx.binaryConnectorPart():
        bcp = ctx.binaryConnectorPart()
        owned_rel = []
        if hasattr(bcp, 'connectorEndMember') and bcp.connectorEndMember():
            ends = bcp.connectorEndMember()
            if not isinstance(ends, list):
                ends = [ends]
            for end in ends:
                end_dict = _visit_connector_end_member(end)
                if end_dict:
                    owned_rel.append(end_dict)

        return {
            "name": "ConnectorPart",
            "part": {
                "name": "BinaryConnectorPart",
                "ownedRelationship": owned_rel
            }
        }

    if hasattr(ctx, 'naryConnectorPart') and ctx.naryConnectorPart():
        ncp = ctx.naryConnectorPart()
        owned_rel = []
        if hasattr(ncp, 'connectorEndMember') and ncp.connectorEndMember():
            ends = ncp.connectorEndMember()
            if not isinstance(ends, list):
                ends = [ends]
            for end in ends:
                end_dict = _visit_connector_end_member(end)
                if end_dict:
                    owned_rel.append(end_dict)

        return {
            "name": "ConnectorPart",
            "part": {
                "name": "NaryConnectorPart",
                "ownedRelationship": owned_rel
            }
        }

    return None


def _make_view_definition_dict(ctx, member_prefix=None):
    """Create a ViewDefinition dictionary.
    
    viewDefinition: occurrenceDefinitionPrefix VIEW DEF definitionDeclaration viewDefinitionBody
    """
    name, shortname = _get_definition_identification(ctx)
    occ_prefix = _get_occurrence_definition_prefix(ctx)
    # Get body items from viewDefinitionBody
    body_items = []
    if hasattr(ctx, "viewDefinitionBody") and ctx.viewDefinitionBody():
        body_items = _visit_view_definition_body_dict(ctx.viewDefinitionBody())
    # ViewDefinition uses _DeclaredDefinitionBase pattern: prefix + keyword + declaration + body
    return {
        "name": "PackageMember",
        "prefix": member_prefix,
        "ownedRelatedElement": {
            "name": "DefinitionElement",
            "ownedRelatedElement": {
                "name": "ViewDefinition",
                "prefix": None,
                "declaration": {
                    "name": "DefinitionDeclaration",
                    "identification": {
                        "name": "Identification",
                        "declaredShortName": shortname,
                        "declaredName": name
                    },
                    "subclassificationpart": _get_subclassification_part(ctx)
                },
                "body": {
                    "name": "ViewDefinitionBody",
                    "ownedRelatedElement": body_items
                }
            }
        }
    }


def _make_viewpoint_definition_dict(ctx, member_prefix=None):
    """Create a ViewpointDefinition dictionary.
    
    viewpointDefinition: occurrenceDefinitionPrefix VIEWPOINT DEF definitionDeclaration requirementBody
    """
    name, shortname = _get_definition_identification(ctx)
    occ_prefix = _get_occurrence_definition_prefix(ctx)
    # Get body items from definition body
    body_items = []
    if hasattr(ctx, "definition") and ctx.definition():
        defn = ctx.definition()
        if hasattr(defn, "definitionBody") and defn.definitionBody():
            body_items = _visit_definition_body_dict(defn.definitionBody())
    return {
        "name": "PackageMember",
        "prefix": member_prefix,
        "ownedRelatedElement": {
            "name": "DefinitionElement",
            "ownedRelatedElement": {
                "name": "ViewpointDefinition",
                "prefix": None,
                "declaration": {
                    "name": "DefinitionDeclaration",
                    "identification": {
                        "name": "Identification",
                        "declaredShortName": shortname,
                        "declaredName": name
                    },
                    "subclassificationpart": _get_subclassification_part(ctx)
                },
                "body": {
                    "name": "RequirementBody",
                    "ownedRelationship": []
                }
            }
        }
    }


def _make_concern_definition_dict(ctx, member_prefix=None):
    """Create a ConcernDefinition dictionary.
    
    concernDefinition: occurrenceDefinitionPrefix CONCERN DEF definitionDeclaration requirementBody
    """
    name, shortname = _get_definition_identification(ctx)
    occ_prefix = _get_occurrence_definition_prefix(ctx)
    # Get body items from definition body
    body_items = []
    if hasattr(ctx, "definition") and ctx.definition():
        defn = ctx.definition()
        if hasattr(defn, "definitionBody") and defn.definitionBody():
            body_items = _visit_definition_body_dict(defn.definitionBody())
    return {
        "name": "PackageMember",
        "prefix": member_prefix,
        "ownedRelatedElement": {
            "name": "DefinitionElement",
            "ownedRelatedElement": {
                "name": "ConcernDefinition",
                "prefix": None,
                "declaration": {
                    "name": "DefinitionDeclaration",
                    "identification": {
                        "name": "Identification",
                        "declaredShortName": shortname,
                        "declaredName": name
                    },
                    "subclassificationpart": _get_subclassification_part(ctx)
                },
                "body": {
                    "name": "RequirementBody",
                    "ownedRelationship": []
                }
            }
        }
    }


def _make_case_definition_dict(ctx, member_prefix=None):
    """Create a CaseDefinition dictionary.
    
    caseDefinition: occurrenceDefinitionPrefix CASE DEF definitionDeclaration caseBody
    """
    name, shortname = _get_definition_identification(ctx)
    occ_prefix = _get_occurrence_definition_prefix(ctx)
    # Get body items from definition body
    body_items = []
    if hasattr(ctx, "definition") and ctx.definition():
        defn = ctx.definition()
        if hasattr(defn, "definitionBody") and defn.definitionBody():
            body_items = _visit_definition_body_dict(defn.definitionBody())
    if not name and not shortname:
        name = "Case_" + str(uuid.uuid4())[:8]
    return {
        "name": "PackageMember",
        "prefix": member_prefix,
        "ownedRelatedElement": {
            "name": "DefinitionElement",
            "ownedRelatedElement": {
                "name": "CaseDefinition",
                "prefix": occ_prefix,
                "declaration": {
                    "name": "DefinitionDeclaration",
                    "identification": {
                        "name": "Identification",
                        "declaredShortName": shortname,
                        "declaredName": name
                    },
                    "subclassificationpart": _get_subclassification_part(ctx)
                },
                "body": {
                    "name": "CaseBody",
                    "item": [],
                    "ownedRelationship": None
                }
            }
        }
    }


def _make_analysis_case_definition_dict(ctx, member_prefix=None):
    """Create an AnalysisCaseDefinition dictionary.
    
    analysisCaseDefinition: occurrenceDefinitionPrefix ANALYSIS DEF definitionDeclaration caseBody
    """
    name, shortname = _get_definition_identification(ctx)
    occ_prefix = _get_occurrence_definition_prefix(ctx)
    if not name and not shortname:
        name = "AnalysisCase_" + str(uuid.uuid4())[:8]
    
    # Parse caseBody
    case_body = {"name": "CaseBody", "item": [], "ownedRelationship": None}
    if hasattr(ctx, "caseBody") and ctx.caseBody():
        case_body = _visit_case_body_dict(ctx.caseBody())
    
    return {
        "name": "PackageMember",
        "prefix": member_prefix,
        "ownedRelatedElement": {
            "name": "DefinitionElement",
            "ownedRelatedElement": {
                "name": "AnalysisCaseDefinition",
                "prefix": occ_prefix,
                "declaration": {
                    "name": "DefinitionDeclaration",
                    "identification": {
                        "name": "Identification",
                        "declaredShortName": shortname,
                        "declaredName": name
                    },
                    "subclassificationpart": _get_subclassification_part(ctx)
                },
                "body": case_body
            }
        }
    }


def _make_verification_case_definition_dict(ctx, member_prefix=None):
    """Create a VerificationCaseDefinition dictionary.
    
    verificationCaseDefinition: occurrenceDefinitionPrefix VERIFICATION DEF definitionDeclaration caseBody
    """
    name, shortname = _get_definition_identification(ctx)
    occ_prefix = _get_occurrence_definition_prefix(ctx)
    # Get body items from definition body
    body_items = []
    if hasattr(ctx, "definition") and ctx.definition():
        defn = ctx.definition()
        if hasattr(defn, "definitionBody") and defn.definitionBody():
            body_items = _visit_definition_body_dict(defn.definitionBody())
    if not name and not shortname:
        name = "VerificationCase_" + str(uuid.uuid4())[:8]
    return {
        "name": "PackageMember",
        "prefix": member_prefix,
        "ownedRelatedElement": {
            "name": "DefinitionElement",
            "ownedRelatedElement": {
                "name": "VerificationCaseDefinition",
                "prefix": occ_prefix,
                "declaration": {
                    "name": "DefinitionDeclaration",
                    "identification": {
                        "name": "Identification",
                        "declaredShortName": shortname,
                        "declaredName": name
                    },
                    "subclassificationpart": _get_subclassification_part(ctx)
                },
                "body": {
                    "name": "CaseBody",
                    "item": [],
                    "ownedRelationship": None
                }
            }
        }
    }


def _make_view_usage_dict(ctx, prefix=None):
    """Create a ViewUsage dictionary.
    
    viewUsage: occurrenceUsagePrefix VIEW usageDeclaration? valuePart? viewBody
    """
    name, shortname = _get_usage_identification(ctx)
    # Get body items from viewBody
    body_items = []
    if hasattr(ctx, 'viewBody') and ctx.viewBody():
        body_items = _visit_view_body_dict(ctx.viewBody())
    return {
        "name": "PackageMember",
        "prefix": None,
        "ownedRelatedElement": {
            "name": "UsageElement",
            "ownedRelatedElement": {
                "name": "OccurrenceUsageElement",
                "ownedRelatedElement": {
                    "name": "StructureUsageElement",
                    "ownedRelatedElement": {
                        "name": "ViewUsage",
                        "prefix": None,
                        "declaration": {
                            "name": "UsageDeclaration",
                            "declaration": {
                                "name": "FeatureDeclaration",
                                "identification": {
                                    "name": "Identification",
                                    "declaredShortName": shortname,
                                    "declaredName": name
                                },
                                "specialization": None
                            }
                        },
                        "body": {
                            "name": "ViewBody",
                            "ownedRelatedElement": body_items
                        }
                    }
                }
            }
        }
    }


def _make_viewpoint_usage_dict(ctx, prefix=None):
    """Create a ViewpointUsage dictionary.
    
    viewpointUsage: occurrenceUsagePrefix VIEWPOINT constraintUsageDeclaration requirementBody
    """
    name = None
    shortname = None
    if ctx is not None:
        cud = None
        if hasattr(ctx, 'constraintUsageDeclaration') and ctx.constraintUsageDeclaration():
            cud = ctx.constraintUsageDeclaration()
        
        ud = None
        if cud and hasattr(cud, 'usageDeclaration') and cud.usageDeclaration():
            ud = cud.usageDeclaration()
        
        if ud and hasattr(ud, 'identification') and ud.identification():
            ident = ud.identification()
            if hasattr(ident, 'name'):
                name_list = ident.name()
                if name_list and isinstance(name_list, list):
                    if len(name_list) == 2:
                        shortname = name_list[0].getText()
                        name = name_list[1].getText()
                    elif len(name_list) == 1:
                        name_text = name_list[0].getText()
                        name, shortname = _extract_name_shortname(name_text)
    
    return {
        "name": "PackageMember",
        "prefix": None,
        "ownedRelatedElement": {
            "name": "UsageElement",
            "ownedRelatedElement": {
                "name": "OccurrenceUsageElement",
                "ownedRelatedElement": {
                    "name": "BehaviorUsageElement",
                    "ownedRelationship": {
                        "name": "ViewpointUsage",
                        "prefix": None,
                        "declaration": {
                            "name": "UsageDeclaration",
                            "declaration": {
                                "name": "FeatureDeclaration",
                                "identification": {
                                    "name": "Identification",
                                    "declaredShortName": shortname,
                                    "declaredName": name
                                },
                                "specialization": None
                            }
                        },
                        "body": {
                            "name": "UsageBody",
                            "body": {
                                "name": "DefinitionBody",
                                "ownedRelatedElement": []
                            }
                        }
                    }
                }
            }
        }
    }


def _make_concern_usage_dict(ctx, prefix=None):
    """Create a ConcernUsage dictionary.
    
    concernUsage: occurrenceUsagePrefix CONCERN constraintUsageDeclaration requirementBody
    """
    name = None
    shortname = None
    if ctx is not None:
        cud = None
        if hasattr(ctx, 'constraintUsageDeclaration') and ctx.constraintUsageDeclaration():
            cud = ctx.constraintUsageDeclaration()
        
        ud = None
        if cud and hasattr(cud, 'usageDeclaration') and cud.usageDeclaration():
            ud = cud.usageDeclaration()
        
        if ud and hasattr(ud, 'identification') and ud.identification():
            ident = ud.identification()
            if hasattr(ident, 'name'):
                name_list = ident.name()
                if name_list and isinstance(name_list, list):
                    if len(name_list) == 2:
                        shortname = name_list[0].getText()
                        name = name_list[1].getText()
                    elif len(name_list) == 1:
                        name_text = name_list[0].getText()
                        name, shortname = _extract_name_shortname(name_text)
    
    return {
        "name": "PackageMember",
        "prefix": None,
        "ownedRelatedElement": {
            "name": "UsageElement",
            "ownedRelatedElement": {
                "name": "OccurrenceUsageElement",
                "ownedRelatedElement": {
                    "name": "BehaviorUsageElement",
                    "ownedRelationship": {
                        "name": "ConcernUsage",
                        "prefix": None,
                        "declaration": {
                            "name": "UsageDeclaration",
                            "declaration": {
                                "name": "FeatureDeclaration",
                                "identification": {
                                    "name": "Identification",
                                    "declaredShortName": shortname,
                                    "declaredName": name
                                },
                                "specialization": None
                            }
                        },
                        "body": {
                            "name": "UsageBody",
                            "body": {
                                "name": "DefinitionBody",
                                "ownedRelatedElement": []
                            }
                        }
                    }
                }
            }
        }
    }


def _make_allocation_usage_dict(ctx, prefix=None):
    """Create an AllocationUsage dictionary.

    allocationUsage: occurrenceUsagePrefix allocationUsageDeclaration usageBody
    allocationUsageDeclaration
        : ALLOCATION usageDeclaration? (ALLOCATE connectorPart)?
        | ALLOCATE connectorPart
        ;

    Issue #5: the connector endpoints (`allocate X to Y`) were silently
    dropped before reaching the dict. Mirror the InterfaceUsage pattern:
    walk `aud.connectorPart()` (when present) and emit a ConnectorPart
    dict with binary or nary ends under the `part` key — the same key
    ConnectionUsage already uses, so downstream consumers share one
    shape across connector-bearing usages.
    """
    name = None
    shortname = None
    connector_part = None
    if ctx is not None:
        aud = None
        if hasattr(ctx, 'allocationUsageDeclaration') and ctx.allocationUsageDeclaration():
            aud = ctx.allocationUsageDeclaration()

        ud = None
        if aud and hasattr(aud, 'usageDeclaration') and aud.usageDeclaration():
            ud = aud.usageDeclaration()

        if ud and hasattr(ud, 'identification') and ud.identification():
            ident = ud.identification()
            if hasattr(ident, 'name'):
                name_list = ident.name()
                if name_list and isinstance(name_list, list):
                    if len(name_list) == 2:
                        shortname = name_list[0].getText()
                        name = name_list[1].getText()
                    elif len(name_list) == 1:
                        name_text = name_list[0].getText()
                        name, shortname = _extract_name_shortname(name_text)

        # Issue #5: capture the `allocate X to Y` (or `allocate X, Y to Z`)
        # connector part. Either standalone or appended after the
        # allocation keyword + optional usageDeclaration.
        if aud and hasattr(aud, 'connectorPart') and aud.connectorPart():
            connector_part = _build_connector_part_dict(aud.connectorPart())

    return {
        "name": "PackageMember",
        "prefix": None,
        "ownedRelatedElement": {
            "name": "UsageElement",
            "ownedRelatedElement": {
                "name": "OccurrenceUsageElement",
                "ownedRelatedElement": {
                    "name": "StructureUsageElement",
                    "ownedRelatedElement": {
                        "name": "AllocationUsage",
                        "prefix": None,
                        "declaration": {
                            "name": "UsageDeclaration",
                            "declaration": {
                                "name": "FeatureDeclaration",
                                "identification": {
                                    "name": "Identification",
                                    "declaredShortName": shortname,
                                    "declaredName": name
                                },
                                "specialization": None
                            }
                        },
                        "part": connector_part,
                        "body": {
                            "name": "UsageBody",
                            "body": {
                                "name": "DefinitionBody",
                                "ownedRelatedElement": []
                            }
                        }
                    }
                }
            }
        }
    }


def _make_rendering_usage_dict(ctx, prefix=None):
    """Create a RenderingUsage dictionary.
    
    renderingUsage: occurrenceUsagePrefix RENDERING usage
    """
    name = None
    shortname = None
    if ctx is not None:
        # RenderingUsage uses just `usage` (not usageDeclaration)
        usage = None
        if hasattr(ctx, 'usage') and ctx.usage():
            usage = ctx.usage()
        
        ud = None
        if usage and hasattr(usage, 'usageDeclaration') and usage.usageDeclaration():
            ud = usage.usageDeclaration()
        
        if ud and hasattr(ud, 'identification') and ud.identification():
            ident = ud.identification()
            if hasattr(ident, 'name'):
                name_list = ident.name()
                if name_list and isinstance(name_list, list):
                    if len(name_list) == 2:
                        shortname = name_list[0].getText()
                        name = name_list[1].getText()
                    elif len(name_list) == 1:
                        name_text = name_list[0].getText()
                        name, shortname = _extract_name_shortname(name_text)
    
    return {
        "name": "PackageMember",
        "prefix": None,
        "ownedRelatedElement": {
            "name": "UsageElement",
            "ownedRelatedElement": {
                "name": "OccurrenceUsageElement",
                "ownedRelatedElement": {
                    "name": "StructureUsageElement",
                    "ownedRelatedElement": {
                        "name": "RenderingUsage",
                        "prefix": None,
                        "declaration": {
                            "name": "UsageDeclaration",
                            "declaration": {
                                "name": "FeatureDeclaration",
                                "identification": {
                                    "name": "Identification",
                                    "declaredShortName": shortname,
                                    "declaredName": name
                                },
                                "specialization": None
                            }
                        },
                        "body": {
                            "name": "UsageBody",
                            "body": {
                                "name": "DefinitionBody",
                                "ownedRelatedElement": []
                            }
                        }
                    }
                }
            }
        }
    }


def _make_individual_usage_dict(ctx, prefix=None):
    """Create an IndividualUsage dictionary.
    
    individualUsage: basicUsagePrefix INDIVIDUAL usageExtensionKeyword* usage
    """
    name = None
    shortname = None
    if ctx is not None:
        # individualUsage has `usage` at the end
        usage = None
        if hasattr(ctx, 'usage') and ctx.usage():
            usage = ctx.usage()
        
        ud = None
        if usage and hasattr(usage, 'usageDeclaration') and usage.usageDeclaration():
            ud = usage.usageDeclaration()
        
        if ud and hasattr(ud, 'identification') and ud.identification():
            ident = ud.identification()
            if hasattr(ident, 'name'):
                name_list = ident.name()
                if name_list and isinstance(name_list, list):
                    if len(name_list) == 2:
                        shortname = name_list[0].getText()
                        name = name_list[1].getText()
                    elif len(name_list) == 1:
                        name_text = name_list[0].getText()
                        name, shortname = _extract_name_shortname(name_text)
    
    # Use IndividualUsageSimple per our simplified model
    return {
        "name": "PackageMember",
        "prefix": None,
        "ownedRelatedElement": {
            "name": "UsageElement",
            "ownedRelatedElement": {
                "name": "OccurrenceUsageElement",
                "ownedRelatedElement": {
                    "name": "StructureUsageElement",
                    "ownedRelatedElement": {
                        "name": "IndividualUsageSimple",
                        "prefix": None,
                        "declaration": {
                            "name": "UsageDeclaration",
                            "declaration": {
                                "name": "FeatureDeclaration",
                                "identification": {
                                    "name": "Identification",
                                    "declaredShortName": shortname,
                                    "declaredName": name
                                },
                                "specialization": None
                            }
                        },
                        "body": {
                            "name": "UsageBody",
                            "body": {
                                "name": "DefinitionBody",
                                "ownedRelatedElement": []
                            }
                        }
                    }
                }
            }
        }
    }


def _make_dependency_dict(ctx, member_prefix=None):
    """Create a Dependency dictionary.

    Grammar (SysML v2):
      dependency
        : (prefixMetadataAnnotation)* DEPENDENCY (identification? FROM)?
            qualifiedName (COMMA qualifiedName)* TO qualifiedName
            (COMMA qualifiedName)* relationshipBody
        | (prefixMetadataAnnotation)* DEPENDENCY dependencyDeclaration
            relationshipBody
        ;

    Wrapped in PackageMember + DefinitionElement so the loader places it in
    the enclosing package / namespace body.
    """
    if ctx is None:
        return None

    identification = None
    clients = []
    suppliers = []
    body = {"name": "RelationshipBody", "ownedRelationship": []}

    if hasattr(ctx, 'dependencyDeclaration') and ctx.dependencyDeclaration():
        # Alternative 2: dependencyDeclaration carries identification / FROM /
        # client-list / supplier-list / TO. relationshipBody is the next
        # sibling on the dependency context.
        dep_decl = ctx.dependencyDeclaration()
        if hasattr(dep_decl, 'identification') and dep_decl.identification():
            identification = _build_identification_dict(dep_decl.identification())
        qn_list = dep_decl.qualifiedName()
        if not isinstance(qn_list, list):
            qn_list = [qn_list] if qn_list is not None else []
        # Split on TO: first batch is clients, second batch is suppliers.
        to_token = dep_decl.TO()
        if to_token is not None:
            # ANTLR TerminalNodeImpl doesn't expose `.start` directly; use
            # `.symbol.start` (the underlying token's char position).
            to_start = to_token.symbol.start
            split_idx = len(qn_list)
            for i, qn in enumerate(qn_list):
                if qn.start.start > to_start:
                    split_idx = i
                    break
            clients = qn_list[:split_idx]
            suppliers = qn_list[split_idx:]
        else:
            clients = qn_list
        # relationshipBody sits on the parent dependency context
        if hasattr(ctx, 'relationshipBody') and ctx.relationshipBody():
            body = _visit_dependency_relationship_body_dict(ctx.relationshipBody())
    else:
        # Alternative 1: bare `dependency [ident]? [from]? qn , qn , ... to qn , qn , ... {body}`
        if hasattr(ctx, 'identification') and ctx.identification():
            identification = _build_identification_dict(ctx.identification())
        qn_list = ctx.qualifiedName()
        if not isinstance(qn_list, list):
            qn_list = [qn_list] if qn_list is not None else []
        to_token = ctx.TO()
        if to_token is not None:
            to_start = to_token.symbol.start
            split_idx = len(qn_list)
            for i, qn in enumerate(qn_list):
                if qn.start.start > to_start:
                    split_idx = i
                    break
            clients = qn_list[:split_idx]
            suppliers = qn_list[split_idx:]
        else:
            clients = qn_list
        if hasattr(ctx, 'relationshipBody') and ctx.relationshipBody():
            body = _visit_dependency_relationship_body_dict(ctx.relationshipBody())

    return {
        "name": "PackageMember",
        "prefix": member_prefix,
        "ownedRelatedElement": {
            "name": "DefinitionElement",
            "ownedRelatedElement": {
                "name": "Dependency",
                "identification": identification,
                "clients": [
                    {"name": "QualifiedName", "names": qn.getText().split("::")}
                    for qn in clients if qn is not None
                ],
                "suppliers": [
                    {"name": "QualifiedName", "names": qn.getText().split("::")}
                    for qn in suppliers if qn is not None
                ],
                "body": body,
            }
        }
    }


def _visit_dependency_relationship_body_dict(rb_ctx):
    """Capture a dependency's relationshipBody.

    Mirrors the aliasMember pattern: walk the body for any
    OwnedAnnotation / CommentSysML so doc comments survive the round-trip.
    For the `;` form (empty body), returns the empty shape.
    """
    if rb_ctx is None:
        return {"name": "RelationshipBody", "ownedRelationship": []}
    owned = []
    for child in rb_ctx.children:
        if type(child).__name__ == 'RelationshipOwnedElementContext':
            for c2 in child.children:
                if type(c2).__name__ == 'OwnedAnnotationContext':
                    for c3 in c2.children:
                        if type(c3).__name__ == 'AnnotatingElementContext':
                            owned.append({
                                "name": "OwnedAnnotation",
                                "ownedRelatedElement": [
                                    {
                                        "name": "AnnotatingElement",
                                        "ownedRelatedElement": {
                                            "name": "CommentSysML",
                                            "body": c3.getText(),
                                            "identification": None,
                                            "ownedRelationship": []
                                        }
                                    }
                                ]
                            })
    return {"name": "RelationshipBody", "ownedRelationship": owned}


def _make_enumeration_definition_dict(ctx, member_prefix=None):
    """Create an EnumerationDefinition dictionary.
    
    EnumerationDefinition has 'declaration' and 'body' (EnumerationBody).
    """
    name = None
    shortname = None
    if ctx is not None:
        dd = None
        if hasattr(ctx, 'definitionDeclaration') and ctx.definitionDeclaration():
            dd = ctx.definitionDeclaration()
        
        if dd and hasattr(dd, 'identification') and dd.identification():
            ident = dd.identification()
            if hasattr(ident, 'name'):
                name_list = ident.name()
                if name_list and isinstance(name_list, list):
                    if len(name_list) == 2:
                        shortname = name_list[0].getText()
                        name = name_list[1].getText()
                    elif len(name_list) == 1:
                        name_text = name_list[0].getText()
                        if hasattr(ident, 'LT') and ident.LT() is not None:
                            shortname = name_text
                        else:
                            name = name_text
    
    # Extract enum body members
    enum_members = []
    if ctx is not None and hasattr(ctx, 'enumerationBody') and ctx.enumerationBody():
        body_ctx = ctx.enumerationBody()
        if hasattr(body_ctx, 'enumerationUsageMember'):
            for member_ctx in body_ctx.enumerationUsageMember():
                member_dict = _visit_enumeration_usage_member(member_ctx)
                if member_dict:
                    enum_members.append(member_dict)
    
    occ_prefix = _get_occurrence_definition_prefix(ctx)
    return {
        "name": "PackageMember",
        "prefix": member_prefix,
        "ownedRelatedElement": {
            "name": "DefinitionElement",
            "ownedRelatedElement": {
                "name": "EnumerationDefinition",
                "prefix": occ_prefix,
                "declaration": {
                    "name": "DefinitionDeclaration",
                    "identification": {
                        "name": "Identification",
                        "declaredShortName": shortname,
                        "declaredName": name
                    },
                    "subclassificationpart": _get_subclassification_part(ctx)
                },
                "body": {
                    "name": "EnumerationBody",
                    "ownedRelationship": enum_members
                }
            }
        }
    }


def _visit_enumeration_usage_member(member_ctx):
    """Build an EnumerationUsageMember dict from ANTLR context."""
    # member_ctx children: MemberPrefixContext, EnumeratedValueContext
    prefix = None
    if hasattr(member_ctx, 'memberPrefix') and member_ctx.memberPrefix():
        mp = member_ctx.memberPrefix()
        if hasattr(mp, 'visibilityIndicator') and mp.visibilityIndicator():
            prefix = {
                "name": "MemberPrefix",
                "visibility": _visit_visibility_indicator_dict(mp.visibilityIndicator())
            }
    
    # Find EnumeratedValueContext
    ev_ctx = None
    for child in member_ctx.children:
        if type(child).__name__ == 'EnumeratedValueContext':
            ev_ctx = child
            break
    
    if ev_ctx is None:
        return None
    
    # EnumeratedValue children: TerminalNodeImpl("enum"), UsageContext
    keyword = None
    usage_ctx = None
    for child in ev_ctx.children:
        cname = type(child).__name__
        if cname == 'TerminalNodeImpl':
            keyword = child.getText()  # "enum"
        elif cname == 'UsageContext':
            usage_ctx = child
    
    if usage_ctx is None:
        return None
    
    # Extract name from UsageContext -> UsageDeclarationContext -> IdentificationContext
    ev_name = None
    ev_shortname = None
    ud = None
    if hasattr(usage_ctx, 'usageDeclaration') and usage_ctx.usageDeclaration():
        ud = usage_ctx.usageDeclaration()
        if hasattr(ud, 'identification') and ud.identification():
            ident = ud.identification()
            name_list = ident.name() if hasattr(ident, 'name') else []
            if name_list and isinstance(name_list, list):
                if len(name_list) == 2:
                    ev_shortname = name_list[0].getText()
                    ev_name = name_list[1].getText()
                elif len(name_list) == 1:
                    ev_name_text = name_list[0].getText()
                    if hasattr(ident, 'LT') and ident.LT() is not None:
                        ev_shortname = ev_name_text
                    else:
                        ev_name = ev_name_text
    
    # Extract specialization (redefinitions) from the usage context
    specialization = None
    if hasattr(ud, 'featureSpecializationPart') and ud.featureSpecializationPart():
        specialization = _build_full_specialization_from_ctx(usage_ctx)
    
    # Extract valuepart from usage completion (e.g., =4.0 for A = 4.0)
    valuepart = None
    if hasattr(usage_ctx, 'usageCompletion') and usage_ctx.usageCompletion():
        uc = usage_ctx.usageCompletion()
        if hasattr(uc, 'valuePart') and uc.valuePart():
            valuepart = _visit_value_part(uc.valuePart())
    
    # Extract body items from usage completion
    # Note: UsageContext has usageCompletion directly (not via usage attribute)
    body_items = []
    if hasattr(usage_ctx, 'usageCompletion') and usage_ctx.usageCompletion():
        uc = usage_ctx.usageCompletion()
        if hasattr(uc, 'usageBody') and uc.usageBody():
            ub = uc.usageBody()
            if hasattr(ub, 'definitionBody') and ub.definitionBody():
                body_items = _visit_definition_body_dict(ub.definitionBody())
    
    return {
        "name": "EnumerationUsageMember",
        "prefix": prefix,
        "ownedRelatedElement": [
            {
                "name": "EnumeratedValue",
                "keyword": keyword,
                "usage": {
                    "name": "Usage",
                    "declaration": {
                        "name": "UsageDeclaration",
                        "declaration": {
                            "name": "FeatureDeclaration",
                            "identification": {
                                "name": "Identification",
                                "declaredShortName": ev_shortname,
                                "declaredName": ev_name
                            },
                            "specialization": specialization
                        }
                    },
                    "completion": {
                        "name": "UsageCompletion",
                        "valuepart": valuepart,
                        "body": {
                            "name": "UsageBody",
                            "body": {
                                "name": "DefinitionBody",
                                "ownedRelatedElement": body_items
                            }
                        }
                    }
                }
            }
        ]
    }


def _make_allocation_definition_dict(ctx, member_prefix=None):
    """Create an AllocationDefinition dictionary (uses Definition body)."""
    name, shortname = _get_definition_identification(ctx)
    occ_prefix = _get_occurrence_definition_prefix(ctx)
    # Get body items from definition body
    body_items = []
    if hasattr(ctx, "definition") and ctx.definition():
        defn = ctx.definition()
        if hasattr(defn, "definitionBody") and defn.definitionBody():
            body_items = _visit_definition_body_dict(defn.definitionBody())
    return {
        "name": "PackageMember",
        "prefix": member_prefix,
        "ownedRelatedElement": {
            "name": "DefinitionElement",
            "ownedRelatedElement": {
                "name": "AllocationDefinition",
                "prefix": occ_prefix,
                "definition": {
                    "name": "Definition",
                    "declaration": {
                        "name": "DefinitionDeclaration",
                        "identification": {
                            "name": "Identification",
                            "declaredShortName": shortname,
                            "declaredName": name
                        },
                        "subclassificationpart": _get_subclassification_part(ctx)
                    },
                    "body": {
                        "name": "DefinitionBody",
                        "ownedRelatedElement": body_items
                    }
                }
            }
        }
    }


def _make_metadata_definition_dict(ctx, member_prefix=None):
    """Create a MetadataDefinition dictionary."""
    name, shortname = _get_definition_identification(ctx)
    occ_prefix = _get_occurrence_definition_prefix(ctx)
    # Get body items from definition body
    body_items = []
    if hasattr(ctx, "definition") and ctx.definition():
        defn = ctx.definition()
        if hasattr(defn, "definitionBody") and defn.definitionBody():
            body_items = _visit_definition_body_dict(defn.definitionBody())
    return {
        "name": "PackageMember",
        "prefix": member_prefix,
        "ownedRelatedElement": {
            "name": "DefinitionElement",
            "ownedRelatedElement": {
                "name": "MetadataDefinition",
                "isAbstract": False,
                "keyword": [],
                "definition": {
                    "name": "Definition",
                    "declaration": {
                        "name": "DefinitionDeclaration",
                        "identification": {
                            "name": "Identification",
                            "declaredShortName": shortname,
                            "declaredName": name
                        },
                        "subclassificationpart": _get_subclassification_part(ctx)
                    },
                    "body": {
                        "name": "DefinitionBody",
                        "ownedRelatedElement": body_items
                    }
                }
            }
        }
    }


def _make_rendering_definition_dict(ctx, member_prefix=None):
    """Create a RenderingDefinition dictionary."""
    name, shortname = _get_definition_identification(ctx)
    occ_prefix = _get_occurrence_definition_prefix(ctx)
    # Get body items from definition body
    body_items = []
    if hasattr(ctx, "definition") and ctx.definition():
        defn = ctx.definition()
        if hasattr(defn, "definitionBody") and defn.definitionBody():
            body_items = _visit_definition_body_dict(defn.definitionBody())
    return {
        "name": "PackageMember",
        "prefix": member_prefix,
        "ownedRelatedElement": {
            "name": "DefinitionElement",
            "ownedRelatedElement": {
                "name": "RenderingDefinition",
                "prefix": occ_prefix,
                "definition": {
                    "name": "Definition",
                    "declaration": {
                        "name": "DefinitionDeclaration",
                        "identification": {
                            "name": "Identification",
                            "declaredShortName": shortname,
                            "declaredName": name
                        },
                        "subclassificationpart": _get_subclassification_part(ctx)
                    },
                    "body": {
                        "name": "DefinitionBody",
                        "ownedRelatedElement": body_items
                    }
                }
            }
        }
    }


def _make_individual_definition_dict(ctx, member_prefix=None):
    """Create an IndividualDefinition dictionary."""
    name, shortname = _get_definition_identification(ctx)
    occ_prefix = _get_occurrence_definition_prefix(ctx)
    return {
        "name": "PackageMember",
        "prefix": member_prefix,
        "ownedRelatedElement": {
            "name": "DefinitionElement",
            "ownedRelatedElement": {
                "name": "IndividualDefinition",
                "prefix": occ_prefix,
                "definition": {
                    "name": "Definition",
                    "declaration": {
                        "name": "DefinitionDeclaration",
                        "identification": {
                            "name": "Identification",
                            "declaredShortName": shortname,
                            "declaredName": name
                        },
                        "subclassificationpart": _get_subclassification_part(ctx)
                    },
                    "body": {
                        "name": "DefinitionBody",
                        "ownedRelatedElement": []
                    }
                }
            }
        }
    }


def _visit_definition_body_dict(body_ctx):
    """Visit a definition body and return a list of DefinitionBodyItem dicts."""
    # Debug print
    # print(f"_visit_definition_body_dict called with body_ctx: {body_ctx}")
    if body_ctx is None:
        # print("  body_ctx is None")
        return []
    
    items = []
    if hasattr(body_ctx, 'definitionBodyItem') and body_ctx.definitionBodyItem():
        items_list = body_ctx.definitionBodyItem()
        # print(f"  Found {len(items_list)} definitionBodyItem(s)")
        for i, item_ctx in enumerate(items_list):
            # print(f"    Item {i}: {item_ctx}")
            item_dict = _visit_definition_body_item_dict(item_ctx)
            if item_dict:
                # print(f"      -> item_dict: {item_dict}")
                items.append(item_dict)
            else:
                # print(f"      -> item_dict is None")
                pass
    else:
        # print("  No definitionBodyItem found")
        pass
    # print(f"  Returning {len(items)} items")
    return items


def _make_view_rendering_member_dict(ctx, prefix=None):
    """Create a ViewRenderingMember dictionary.
    
    viewRenderingMember : memberPrefix RENDER viewRenderingUsage
    viewRenderingUsage
        : ownedReferenceSubsetting featureSpecializationPart? usageBody
        | ( usageExtensionKeyword* RENDERING | usageExtensionKeyword+) usage
        ;
    """
    member_prefix = prefix
    
    reference = None
    specialization = None
    body = None
    rendering_usage = None
    usage_dict = None
    
    if hasattr(ctx, 'viewRenderingUsage') and ctx.viewRenderingUsage():
        vru = ctx.viewRenderingUsage()
        
        if hasattr(vru, 'ownedReferenceSubsetting') and vru.ownedReferenceSubsetting():
            ref_ctx = vru.ownedReferenceSubsetting()
            if hasattr(ref_ctx, 'qualifiedName') and ref_ctx.qualifiedName():
                qn_list = ref_ctx.qualifiedName()
                if isinstance(qn_list, list) and len(qn_list) > 0:
                    qn = qn_list[0]
                else:
                    qn = qn_list
                if hasattr(qn, 'name') and qn.name():
                    names = qn.name()
                    if isinstance(names, list):
                        reference = {"name": "QualifiedName", "names": [n.getText() for n in names]}
                    else:
                        reference = {"name": "QualifiedName", "names": [names.getText()]}
            
            if hasattr(vru, 'featureSpecializationPart') and vru.featureSpecializationPart():
                pass  # TODO: handle featureSpecializationPart
            
            if hasattr(vru, 'usageBody') and vru.usageBody():
                body = {"name": "UsageBody", "body": {"name": "DefinitionBody", "ownedRelatedElement": []}}
        
        elif hasattr(vru, 'usage') and vru.usage():
            usage_ctx = vru.usage()
            name, shortname = _get_usage_identification(usage_ctx)
            # Check if RENDERING keyword was present
            has_rendering_keyword = False
            if hasattr(vru, 'RENDERING') and vru.RENDERING():
                has_rendering_keyword = True
            usage_dict = {
                "name": "Usage",
                "declaration": {
                    "name": "UsageDeclaration",
                    "declaration": {
                        "name": "FeatureDeclaration",
                        "identification": {
                            "name": "Identification",
                            "declaredShortName": shortname,
                            "declaredName": name
                        },
                        "specialization": None
                    }
                },
                "completion": None
            }
            if has_rendering_keyword:
                rendering_usage = usage_dict
                usage_dict = None
    
    return {
        "name": "ViewRenderingMember",
        "prefix": member_prefix,
        "usage": {
            "name": "ViewRenderingUsage",
            "reference": reference,
            "specialization": specialization,
            "body": body,
            "renderingUsage": rendering_usage,
            "usage": usage_dict
        }
    }


def _make_render_state_member_dict(ctx, prefix=None):
    """Create a RenderStateMember dictionary.
    
    renderStateMember : memberPrefix RENDER STATE name renderStateBody
    renderStateBody : SEMI | LBRACE renderStateBodyItem* RBRACE
    """
    member_prefix = prefix
    
    state_name = None
    if hasattr(ctx, 'name') and ctx.name():
        state_name = ctx.name().getText()
    
    body_items = []
    if hasattr(ctx, 'renderStateBody') and ctx.renderStateBody():
        body_ctx = ctx.renderStateBody()
        if hasattr(body_ctx, 'renderStateBodyItem') and body_ctx.renderStateBodyItem():
            items_list = body_ctx.renderStateBodyItem()
            if not isinstance(items_list, list):
                items_list = [items_list]
            for item in items_list:
                if hasattr(item, 'shapeDirective') and item.shapeDirective():
                    sd = item.shapeDirective()
                    shape_name = sd.name().getText() if hasattr(sd, 'name') and sd.name() else None
                    body_items.append({"name": "ShapeDirective", "shape": shape_name})
                elif hasattr(item, 'colorDirective') and item.colorDirective():
                    cd = item.colorDirective()
                    color_name = cd.name().getText() if hasattr(cd, 'name') and cd.name() else None
                    body_items.append({"name": "ColorDirective", "color": color_name})
                elif hasattr(item, 'showDirective') and item.showDirective():
                    sd = item.showDirective()
                    target = None
                    if hasattr(sd, 'showTarget') and sd.showTarget():
                        st = sd.showTarget()
                        if hasattr(st, 'ENTRY') and st.ENTRY():
                            target = "entry behavior"
                        elif hasattr(st, 'DO') and st.DO():
                            target = "do behavior"
                        elif hasattr(st, 'EVENTS') and st.EVENTS():
                            target = "events"
                        elif hasattr(st, 'name') and st.name():
                            target = st.name().getText()
                    body_items.append({"name": "ShowDirective", "target": target})
                elif hasattr(item, 'annotationDirective') and item.annotationDirective():
                    ad = item.annotationDirective()
                    text = None
                    if hasattr(ad, 'STRING') and ad.STRING():
                        text = ad.STRING().getText()
                    elif hasattr(ad, 'DOUBLE_STRING') and ad.DOUBLE_STRING():
                        text = ad.DOUBLE_STRING().getText()
                    body_items.append({"name": "AnnotationDirective", "text": text})
    
    return {
        "name": "RenderStateMember",
        "prefix": member_prefix,
        "stateName": state_name,
        "body": body_items
    }


def _visit_view_definition_body_dict(body_ctx):
    """Visit a viewDefinitionBody and return a list of body item dicts.
    
    viewDefinitionBody : SEMI | LBRACE viewDefinitionBodyItem* RBRACE
    viewDefinitionBodyItem
        : definitionBodyItem
        | elementFilterMember
        | renderStateMember
        | viewRenderingMember
        ;
    """
    if body_ctx is None:
        return []
    
    items = []
    if hasattr(body_ctx, 'viewDefinitionBodyItem') and body_ctx.viewDefinitionBodyItem():
        items_list = body_ctx.viewDefinitionBodyItem()
        if not isinstance(items_list, list):
            items_list = [items_list]
        for item_ctx in items_list:
            if hasattr(item_ctx, 'renderStateMember') and item_ctx.renderStateMember():
                item_dict = _make_render_state_member_dict(item_ctx.renderStateMember())
                if item_dict:
                    items.append(item_dict)
            elif hasattr(item_ctx, 'definitionBodyItem') and item_ctx.definitionBodyItem():
                item_dict = _visit_definition_body_item_dict(item_ctx.definitionBodyItem())
                if item_dict:
                    items.append(item_dict)
            elif hasattr(item_ctx, 'viewRenderingMember') and item_ctx.viewRenderingMember():
                item_dict = _make_view_rendering_member_dict(item_ctx.viewRenderingMember())
                if item_dict:
                    items.append(item_dict)
            elif hasattr(item_ctx, 'elementFilterMember') and item_ctx.elementFilterMember():
                pass  # TODO: handle elementFilterMember
    
    return items


def _visit_view_body_dict(body_ctx):
    """Visit a viewBody and return a list of body item dicts.
    
    viewBody : SEMI | LBRACE viewBodyItem* RBRACE
    viewBodyItem
        : definitionBodyItem
        | elementFilterMember
        | renderStateMember
        | viewRenderingMember
        | expose
        ;
    """
    if body_ctx is None:
        return []
    
    items = []
    if hasattr(body_ctx, 'viewBodyItem') and body_ctx.viewBodyItem():
        items_list = body_ctx.viewBodyItem()
        if not isinstance(items_list, list):
            items_list = [items_list]
        for item_ctx in items_list:
            if hasattr(item_ctx, 'renderStateMember') and item_ctx.renderStateMember():
                item_dict = _make_render_state_member_dict(item_ctx.renderStateMember())
                if item_dict:
                    items.append(item_dict)
            elif hasattr(item_ctx, 'definitionBodyItem') and item_ctx.definitionBodyItem():
                item_dict = _visit_definition_body_item_dict(item_ctx.definitionBodyItem())
                if item_dict:
                    items.append(item_dict)
            elif hasattr(item_ctx, 'viewRenderingMember') and item_ctx.viewRenderingMember():
                item_dict = _make_view_rendering_member_dict(item_ctx.viewRenderingMember())
                if item_dict:
                    items.append(item_dict)
            elif hasattr(item_ctx, 'elementFilterMember') and item_ctx.elementFilterMember():
                pass  # TODO: handle elementFilterMember
            elif hasattr(item_ctx, 'expose') and item_ctx.expose():
                pass  # TODO: handle expose
    
    return items


def _visit_requirement_body_dict(body_ctx):
    """Visit a requirement body and return a list of RequirementBodyItem dicts.
    
    Per grammar:
    requirementBodyItem
        : definitionBodyItem
        | subjectMember
        | requirementConstraintMember
        | framedConcernMember
        | requirementVerificationMember
        | actorMember
        | stakeholderMember
        ;
    """
    if body_ctx is None:
        return []
    
    items = []
    if hasattr(body_ctx, 'requirementBodyItem') and body_ctx.requirementBodyItem():
        items_list = body_ctx.requirementBodyItem()
        if not isinstance(items_list, list):
            items_list = [items_list]
        for item_ctx in items_list:
            item_dict = _visit_requirement_body_item_dict(item_ctx)
            if item_dict:
                items.append(item_dict)
    
    return items


def _visit_case_body_dict(body_ctx):
    """Visit a caseBody and return a CaseBody dict.
    
    Grammar:
      caseBody: SEMI | LBRACE caseBodyItem* (resultExpressionMember)? RBRACE ;
      caseBodyItem: actionBodyItem | returnParameterMember | subjectMember | actorMember | objectiveMember ;
    
    CaseBody class expects: {"name": "CaseBody", "item": [...CaseBodyItems...], "ownedRelationship": ...}
    CaseBodyItem.ownedRelationship can be: CalculationBodyItem, SubjectMember, ActorMember, ObjectiveMember
    """
    if body_ctx is None:
        return {"name": "CaseBody", "item": [], "ownedRelationship": None}
    
    # SEMI case - empty body
    if hasattr(body_ctx, 'SEMI') and body_ctx.SEMI():
        return {"name": "CaseBody", "item": [], "ownedRelationship": None}
    
    items = []
    if hasattr(body_ctx, 'caseBodyItem') and body_ctx.caseBodyItem():
        for item_ctx in body_ctx.caseBodyItem():
            item_dict = _visit_case_body_item_dict(item_ctx)
            if item_dict:
                items.append(item_dict)
    
    result_expr = None
    if hasattr(body_ctx, 'resultExpressionMember') and body_ctx.resultExpressionMember():
        rem_ctx = body_ctx.resultExpressionMember()
        result_expr = _visit_result_expression_member(rem_ctx)
    
    return {"name": "CaseBody", "item": items, "ownedRelationship": result_expr}


def _visit_case_body_item_dict(item_ctx):
    """Visit a caseBodyItem and return a CaseBodyItem dict."""
    if item_ctx is None:
        return None
    
    # subjectMember
    if hasattr(item_ctx, 'subjectMember') and item_ctx.subjectMember():
        sm = item_ctx.subjectMember()
        if isinstance(sm, list):
            sm = sm[0]
        subject_dict = _visit_subject_member_dict(sm)
        if subject_dict:
            return {"name": "CaseBodyItem", "ownedRelationship": subject_dict}
    
    # returnParameterMember → wraps in CalculationBodyItem
    if hasattr(item_ctx, 'returnParameterMember') and item_ctx.returnParameterMember():
        rpm = item_ctx.returnParameterMember()
        if isinstance(rpm, list):
            rpm = rpm[0]
        rpm_dict = _visit_return_parameter_member(rpm)
        if rpm_dict:
            return {
                "name": "CaseBodyItem",
                "ownedRelationship": {
                    "name": "CalculationBodyItem",
                    "item": None,
                    "ownedRelationship": rpm_dict
                }
            }
    
    # actionBodyItem → wraps in CalculationBodyItem
    if hasattr(item_ctx, 'actionBodyItem') and item_ctx.actionBodyItem():
        abi = item_ctx.actionBodyItem()
        if isinstance(abi, list):
            abi = abi[0]
        action_dict = _visit_action_body_item(abi)
        if action_dict:
            return {
                "name": "CaseBodyItem",
                "ownedRelationship": {
                    "name": "CalculationBodyItem",
                    "item": action_dict,
                    "ownedRelationship": None
                }
            }
    
    # objectiveMember
    if hasattr(item_ctx, 'objectiveMember') and item_ctx.objectiveMember():
        om = item_ctx.objectiveMember()
        if isinstance(om, list):
            om = om[0]
        obj_dict = _visit_objective_member_dict(om)
        if obj_dict:
            return {"name": "CaseBodyItem", "ownedRelationship": obj_dict}
    
    return None


def _visit_objective_member_dict(om_ctx):
    """Visit an objectiveMember and return an ObjectiveMember dict.
    
    Grammar: objectiveMember: memberPrefix OBJECTIVE objectiveRequirementUsage ;
    objectiveRequirementUsage: usageExtensionKeyword* constraintUsageDeclaration requirementBody ;
    """
    if om_ctx is None:
        return None
    
    prefix = None
    if hasattr(om_ctx, 'memberPrefix') and om_ctx.memberPrefix():
        mp = om_ctx.memberPrefix()
        if hasattr(mp, 'visibilityIndicator') and mp.visibilityIndicator():
            prefix = {
                "name": "MemberPrefix",
                "visibility": _visit_visibility_indicator_dict(mp.visibilityIndicator())
            }
    
    oru_dict = None
    if hasattr(om_ctx, 'objectiveRequirementUsage') and om_ctx.objectiveRequirementUsage():
        oru = om_ctx.objectiveRequirementUsage()
        
        # Extract name from constraintUsageDeclaration
        name = None
        shortname = None
        typed_by = None
        cud = None
        if hasattr(oru, 'constraintUsageDeclaration') and oru.constraintUsageDeclaration():
            cud = oru.constraintUsageDeclaration()
        
        ud = None
        if cud and hasattr(cud, 'usageDeclaration') and cud.usageDeclaration():
            ud = cud.usageDeclaration()
        
        if ud and hasattr(ud, 'identification') and ud.identification():
            ident = ud.identification()
            if hasattr(ident, 'name'):
                name_list = ident.name()
                if name_list and isinstance(name_list, list):
                    if len(name_list) == 2:
                        shortname = name_list[0].getText()
                        name = name_list[1].getText()
                    elif len(name_list) == 1:
                        name_text = name_list[0].getText()
                        name, shortname = _extract_name_shortname(name_text)
        
        typed_by = _get_action_usage_typed_by(oru)
        if typed_by is None:
            typed_by = _get_action_usage_subsetted_by(oru)
        specialization = _build_specialization(typed_by) if typed_by else None
        
        # Get requirement body
        body_items = []
        if hasattr(oru, 'requirementBody') and oru.requirementBody():
            body_items = _visit_requirement_body_dict(oru.requirementBody())
        
        # Keywords (like '#metadata')
        keywords = []
        if hasattr(oru, 'usageExtensionKeyword') and oru.usageExtensionKeyword():
            for kw in oru.usageExtensionKeyword():
                keywords.append({"name": "UsageExtensionKeyword"})
        
        oru_dict = {
            "name": "ObjectiveRequirementUsage",
            "keyword": keywords,
            "declaration": {
                "name": "CalculationUsageDeclaration",
                "declaration": {
                    "name": "UsageDeclaration",
                    "declaration": {
                        "name": "FeatureDeclaration",
                        "identification": {
                            "name": "Identification",
                            "declaredShortName": shortname,
                            "declaredName": name
                        },
                        "specialization": specialization
                    }
                },
                "valuepart": None
            },
            "body": {
                "name": "RequirementBody",
                "item": body_items
            }
        }
    
    return {
        "name": "ObjectiveMember",
        "prefix": prefix,
        "ownedRelatedElement": oru_dict
    }


def _visit_requirement_body_item_dict(item_ctx):
    """Visit a requirement body item and return a RequirementBodyItem dict."""
    if item_ctx is None:
        return None
    
    inner_dict = None
    
    # Check for definitionBodyItem first
    if hasattr(item_ctx, 'definitionBodyItem') and item_ctx.definitionBodyItem():
        def_item = item_ctx.definitionBodyItem()
        if isinstance(def_item, list):
            def_item = def_item[0]
        inner_dict = _visit_definition_body_item_dict(def_item)
        if inner_dict:
            return {
                "name": "RequirementBodyItem",
                "ownedRelationship": inner_dict
            }
    
    # Check for subjectMember
    if hasattr(item_ctx, 'subjectMember') and item_ctx.subjectMember():
        sm = item_ctx.subjectMember()
        if isinstance(sm, list):
            sm = sm[0]
        subject_dict = _visit_subject_member_dict(sm)
        if subject_dict:
            return {
                "name": "RequirementBodyItem",
                "ownedRelationship": subject_dict
            }
    
    # Check for requirementConstraintMember
    if hasattr(item_ctx, 'requirementConstraintMember') and item_ctx.requirementConstraintMember():
        rcm = item_ctx.requirementConstraintMember()
        if isinstance(rcm, list):
            rcm = rcm[0]
        constraint_dict = _visit_requirement_constraint_member_dict(rcm)
        if constraint_dict:
            return {
                "name": "RequirementBodyItem",
                "ownedRelationship": constraint_dict
            }
    
    # Check for actorMember (skip for now)
    # Check for stakeholderMember (skip for now)
    # Check for framedConcernMember (skip for now)
    # Check for requirementVerificationMember (skip for now)
    
    return None


def _visit_subject_member_dict(sm_ctx):
    """Visit a subjectMember and return a SubjectMember dict.
    
    subjectMember : memberPrefix subjectUsage ;
    subjectUsage : SUBJECT usageExtensionKeyword* usage ;
    """
    if sm_ctx is None:
        return None
    
    prefix = None
    if hasattr(sm_ctx, 'memberPrefix') and sm_ctx.memberPrefix():
        mp = sm_ctx.memberPrefix()
        if hasattr(mp, 'visibilityIndicator') and mp.visibilityIndicator():
            prefix = {
                "name": "MemberPrefix",
                "visibility": _visit_visibility_indicator_dict(mp.visibilityIndicator())
            }
    
    usage_dict = None
    if hasattr(sm_ctx, 'subjectUsage') and sm_ctx.subjectUsage():
        su = sm_ctx.subjectUsage()
        if isinstance(su, list):
            su = su[0]
        
        keywords = []
        if hasattr(su, 'usageExtensionKeyword') and su.usageExtensionKeyword():
            kw_list = su.usageExtensionKeyword()
            if not isinstance(kw_list, list):
                kw_list = [kw_list]
            for kw in kw_list:
                if hasattr(kw, 'getText'):
                    keywords.append({"name": "UsageExtensionKeyword", "keyword": kw.getText()})
        
        if hasattr(su, 'usage') and su.usage():
            usage_ctx = su.usage()
            if isinstance(usage_ctx, list):
                usage_ctx = usage_ctx[0]
            usage_dict = _visit_usage_for_subject(usage_ctx)
    
    return {
        "name": "SubjectMember",
        "prefix": prefix,
        "ownedRelatedElement": {
            "name": "SubjectUsage",
            "keyword": keywords,
            "usage": usage_dict
        }
    }


def _visit_usage_for_subject(usage_ctx):
    """Visit a usage element for subject usage.
    
    Subject usage is a simplified usage without full body.
    Note: The usage_ctx is a UsageContext, which contains a usage() method
    that returns the actual usage with usageDeclaration.
    """
    if usage_ctx is None:
        return None
    
    # Drill into usage() if present (subjectUsage has 'usage' which is a UsageContext)
    actual_ctx = usage_ctx
    if hasattr(usage_ctx, 'usage') and usage_ctx.usage():
        usages = usage_ctx.usage()
        if isinstance(usages, list):
            usages = usages[0]
        if usages:
            actual_ctx = usages
    
    name, shortname = _get_usage_identification(actual_ctx)
    typed_by = _get_action_usage_typed_by(actual_ctx)
    specialization = _build_specialization(typed_by)
    
    # Extract valuePart directly from actual_ctx (which is a UsageContext)
    # UsageContext has usageCompletion() which has valuePart()
    valuepart = None
    if hasattr(actual_ctx, 'usageCompletion') and actual_ctx.usageCompletion():
        uc = actual_ctx.usageCompletion()
        if hasattr(uc, 'valuePart') and uc.valuePart():
            vp_ctx = uc.valuePart()
            valuepart = _visit_value_part(vp_ctx)
    
    return {
        "name": "Usage",
        "declaration": {
            "name": "UsageDeclaration",
            "declaration": {
                "name": "FeatureDeclaration",
                "identification": {
                    "name": "Identification",
                    "declaredShortName": shortname,
                    "declaredName": name
                },
                "specialization": specialization
            }
        },
        "completion": {
            "name": "UsageCompletion",
            "valuepart": valuepart,
            "body": {
                "name": "UsageBody",
                "body": {
                    "name": "DefinitionBody",
                    "ownedRelatedElement": []
                }
            }
        }
    }


def _visit_requirement_constraint_member_dict(rcm_ctx):
    """Visit a requirementConstraintMember and return a RequirementConstraintMember dict.
    
    requirementConstraintMember : memberPrefix requirementKind requirementConstraintUsage ;
    requirementKind : ASSUME | REQUIRE ;
    """
    if rcm_ctx is None:
        return None
    
    prefix = None
    if hasattr(rcm_ctx, 'memberPrefix') and rcm_ctx.memberPrefix():
        mp = rcm_ctx.memberPrefix()
        if hasattr(mp, 'visibilityIndicator') and mp.visibilityIndicator():
            prefix = {
                "name": "MemberPrefix",
                "visibility": _visit_visibility_indicator_dict(mp.visibilityIndicator())
            }
    
    kind = None
    if hasattr(rcm_ctx, 'requirementKind') and rcm_ctx.requirementKind():
        kh = rcm_ctx.requirementKind()
        if hasattr(kh, 'ASSUME') and kh.ASSUME():
            kind = {"name": "RequirementConstraintKind", "assumption": "assume", "requirement": None}
        elif hasattr(kh, 'REQUIRE') and kh.REQUIRE():
            kind = {"name": "RequirementConstraintKind", "assumption": None, "requirement": "require"}
    
    usage_dict = None
    if hasattr(rcm_ctx, 'requirementConstraintUsage') and rcm_ctx.requirementConstraintUsage():
        rcu = rcm_ctx.requirementConstraintUsage()
        if isinstance(rcu, list):
            rcu = rcu[0]
        usage_dict = _visit_requirement_constraint_usage(rcu)
    
    return {
        "name": "RequirementConstraintMember",
        "prefix": prefix,
        "kind": kind,
        "ownedRelatedElement": usage_dict
    }


def _visit_requirement_constraint_usage(rcu_ctx):
    """Visit a requirementConstraintUsage and return a RequirementConstraintUsage dict.
    
    requirementConstraintUsage
        : ownedReferenceSubsetting featureSpecializationPart? requirementBody
        | (usageExtensionKeyword* CONSTRAINT | usageExtensionKeyword+) constraintUsageDeclaration calculationBody
        ;
    """
    if rcu_ctx is None:
        return None
    
    # Check first alternative: ownedReferenceSubsetting
    if hasattr(rcu_ctx, 'ownedReferenceSubsetting') and rcu_ctx.ownedReferenceSubsetting():
        ors = _build_owned_reference_subsetting_dict(rcu_ctx.ownedReferenceSubsetting())
        
        fs = []
        if hasattr(rcu_ctx, 'featureSpecializationPart') and rcu_ctx.featureSpecializationPart():
            fsp_ctx = rcu_ctx.featureSpecializationPart()
            fsp = _build_full_specialization_from_fsp(fsp_ctx)
            if fsp and "specialization" in fsp:
                fs = fsp["specialization"]
        
        body_dict = None
        if hasattr(rcu_ctx, 'requirementBody') and rcu_ctx.requirementBody():
            body_items = _visit_requirement_body_dict(rcu_ctx.requirementBody())
            body_dict = {
                "name": "RequirementBody",
                "item": body_items
            }
        
        return {
            "name": "RequirementConstraintUsage",
            "ownedRelationship": ors,
            "fs": fs,
            "body": body_dict
        }
    
    # Check second alternative: constraint usage with keywords
    keywords_before = []
    if hasattr(rcu_ctx, 'usageExtensionKeyword') and rcu_ctx.usageExtensionKeyword():
        kw_list = rcu_ctx.usageExtensionKeyword()
        if not isinstance(kw_list, list):
            kw_list = [kw_list]
        for kw in kw_list:
            if hasattr(kw, 'getText'):
                keywords_before.append({"name": "UsageExtensionKeyword", "keyword": kw.getText()})
    
    has_constraint_keyword = False
    if hasattr(rcu_ctx, 'CONSTRAINT') and rcu_ctx.CONSTRAINT():
        has_constraint_keyword = True
    
    declaration = None
    if hasattr(rcu_ctx, 'constraintUsageDeclaration') and rcu_ctx.constraintUsageDeclaration():
        cud = rcu_ctx.constraintUsageDeclaration()
        if isinstance(cud, list):
            cud = cud[0]
        declaration = _make_constraint_usage_declaration_dict(cud)
    
    body_parts = []
    if hasattr(rcu_ctx, 'calculationBody') and rcu_ctx.calculationBody():
        # Pass the parent context (rcu_ctx), not the calculationBody directly
        # _visit_calculation_body_items will extract calculationBody from it
        body_parts = _visit_calculation_body_items(rcu_ctx)
    
    return {
        "name": "RequirementConstraintUsage",
        "ownedRelationship": None,
        "keyword1": keywords_before,
        "keyword2": [],
        "constraint": "constraint" if has_constraint_keyword else None,
        "declaration": declaration,
        "body": {
            "name": "CalculationBody",
            "part": body_parts
        }
    }


def _make_constraint_usage_declaration_dict(cud_ctx):
    """Create a constraint usage declaration dict.
    
    constraintUsageDeclaration : usageDeclaration? valuePart? ;
    """
    name = None
    shortname = None
    typed_by = None
    
    if hasattr(cud_ctx, 'usageDeclaration') and cud_ctx.usageDeclaration():
        ud = cud_ctx.usageDeclaration()
        if isinstance(ud, list):
            ud = ud[0]
        if ud and hasattr(ud, 'identification') and ud.identification():
            ident = ud.identification()
            if hasattr(ident, 'name'):
                name_list = ident.name()
                if name_list and isinstance(name_list, list):
                    if len(name_list) == 2:
                        shortname = name_list[0].getText()
                        name = name_list[1].getText()
                    elif len(name_list) == 1:
                        name_text = name_list[0].getText()
                        name, shortname = _extract_name_shortname(name_text)
        
        typed_by = _get_action_usage_typed_by(cud_ctx)
        if typed_by is None:
            typed_by = _get_action_usage_subsetted_by(cud_ctx)
    
    specialization = _build_specialization(typed_by) if typed_by else None
    
    return {
        "name": "CalculationUsageDeclaration",
        "declaration": {
            "name": "UsageDeclaration",
            "declaration": {
                "name": "FeatureDeclaration",
                "identification": {
                    "name": "Identification",
                    "declaredShortName": shortname,
                    "declaredName": name
                },
                "specialization": specialization
            }
        },
        "valuepart": None
    }


def _visit_definition_body_item_dict(item_ctx, is_interface=False):
    """Visit a definition body item and return a dictionary.
    
    Per grammar:
    definitionBodyItem
        : importRule
        | memberPrefix definitionBodyItemContent
        | ( sourceSuccessionMember)? memberPrefix endOccurrenceUsageElement
        | ( sourceSuccessionMember)? memberPrefix occurrenceUsageElement
        | ( sourceSuccessionMember)? memberPrefix interfaceOccurrenceUsageElement
        | ( sourceSuccessionMember)? interfaceNonOccurrenceUsageMember
        ;
    
    definitionBodyItemContent
        : ALIAS (LT name GT)? (name)? FOR qualifiedName relationshipBody
        | VARIANT variantUsageElement
        | definitionElement
        | nonOccurrenceUsageElement
        ;
    """
    if item_ctx is None:
        return None
    
    # print(f"DEBUG _visit_definition_body_item_dict: {item_ctx}")
    
    inner_element = None
    wrapper = None
    
    # Check for occurrenceUsageElement (part, item, port, action, etc.)
    if hasattr(item_ctx, 'occurrenceUsageElement') and item_ctx.occurrenceUsageElement():
        occ_elem = item_ctx.occurrenceUsageElement()
        # print(f"DEBUG: Found occurrenceUsageElement: {occ_elem}")
        inner_element = _visit_nested_occurrence_usage(occ_elem)
        wrapper = "OccurrenceUsageMember"
    # Check for interfaceOccurrenceUsageMember (for interface ends, etc.)
    elif hasattr(item_ctx, 'interfaceOccurrenceUsageMember') and item_ctx.interfaceOccurrenceUsageMember():
        memb = item_ctx.interfaceOccurrenceUsageMember()
        # print(f"DEBUG: Found interfaceOccurrenceUsageMember: {memb}")
        if memb and hasattr(memb, 'interfaceOccurrenceUsageElement') and memb.interfaceOccurrenceUsageElement():
            occ_elem = memb.interfaceOccurrenceUsageElement()
            # print(f"DEBUG: Found interfaceOccurrenceUsageElement: {occ_elem}")
            inner_element = _visit_nested_occurrence_usage(occ_elem)
            wrapper = "InterfaceOccurrenceUsageMember"
    # Check for endOccurrenceUsageElement (for regular definition body)
    elif hasattr(item_ctx, 'endOccurrenceUsageElement') and item_ctx.endOccurrenceUsageElement():
        occ_elem = item_ctx.endOccurrenceUsageElement()
        if isinstance(occ_elem, list):
            occ_elem = occ_elem[0]
        # EndOccurrenceUsageElementContext has OccurrenceUsageElement as a child
        # Get the second child (first is usually the 'end' keyword terminal)
        children = list(occ_elem.getChildren())
        actual_occ_elem = None
        for child in children:
            # TerminalNode has 'symbol' attribute, ParserRuleContext doesn't
            if not hasattr(child, 'symbol') and hasattr(child, 'getChildCount'):
                # This is a ParserRuleContext, not a terminal
                actual_occ_elem = child
                break
        if actual_occ_elem is None and len(children) > 1:
            actual_occ_elem = children[1]
        if actual_occ_elem:
            inner_element = _visit_nested_occurrence_usage(actual_occ_elem)
            # Add END prefix if not already present
            if inner_element:
                occ_usage_elem = inner_element.get("ownedRelatedElement", {})
                occ_elem_inner = occ_usage_elem.get("ownedRelatedElement", {})
                if occ_elem_inner.get("name") == "StructureUsageElement":
                    struct_elem = occ_elem_inner.get("ownedRelatedElement", {})
                    if isinstance(struct_elem, dict) and struct_elem.get("prefix") is None:
                        struct_elem["prefix"] = {
                            "name": "OccurrenceUsagePrefix",
                            "prefix": {
                                "name": "BasicUsagePrefix",
                                "prefix": {
                                    "name": "RefPrefix",
                                    "isAbstract": None,
                                    "isVariation": None,
                                    "isReadOnly": None,
                                    "isDerived": None,
                                    "isEnd": "end",
                                    "direction": {
                                        "name": "FeatureDirection",
                                        "in": "",
                                        "out": "",
                                        "inout": ""
                                    }
                                },
                                "isReference": False
                            },
                            "isIndividual": None,
                            "portionKind": None,
                            "usageExtension": []
                        }
            wrapper = "OccurrenceUsageMember"
    # Check for interfaceNonOccurrenceUsageMember
    elif hasattr(item_ctx, 'interfaceNonOccurrenceUsageMember') and item_ctx.interfaceNonOccurrenceUsageMember():
        memb = item_ctx.interfaceNonOccurrenceUsageMember()
        # print(f"DEBUG: Found interfaceNonOccurrenceUsageMember: {memb}")
        if memb and hasattr(memb, 'interfaceNonOccurrenceUsageElement') and memb.interfaceNonOccurrenceUsageElement():
            non_occ = memb.interfaceNonOccurrenceUsageElement()
            # print(f"DEBUG: Found interfaceNonOccurrenceUsageElement: {non_occ}")
            inner_element = _visit_nested_non_occurrence_usage(non_occ)
            wrapper = "NonOccurrenceUsageMember"
    
    # Check for definitionBodyItemContent
    if not inner_element and hasattr(item_ctx, 'definitionBodyItemContent') and item_ctx.definitionBodyItemContent():
        content = item_ctx.definitionBodyItemContent()
        # print(f"DEBUG: Found definitionBodyItemContent: {content}")
        # Check nested definition
        if hasattr(content, 'definitionElement') and content.definitionElement():
            def_elem = content.definitionElement()
            # print(f"DEBUG: Found definitionElement: {def_elem}")
            inner_element = _visit_nested_definition_element(def_elem)
            wrapper = "DefinitionMember"
        # Check nonOccurrenceUsageElement
        elif hasattr(content, 'nonOccurrenceUsageElement') and content.nonOccurrenceUsageElement():
            non_occ = content.nonOccurrenceUsageElement()
            # print(f"DEBUG: Found nonOccurrenceUsageElement: {non_occ}")
            inner_element = _visit_nested_non_occurrence_usage(non_occ)
            wrapper = "NonOccurrenceUsageMember"
    
    # print(f"DEBUG: inner_element={inner_element}, wrapper={wrapper}")
    if not inner_element or not wrapper:
        # print(f"DEBUG: Returning None")
        return None
    
    # For OccurrenceUsageMember and InterfaceOccurrenceUsageMember, the ownedRelatedElement should be a LIST of OccurrenceUsageElement
    if wrapper == "OccurrenceUsageMember":
        # inner_element is currently UsageElement wrapping OccurrenceUsageElement
        # We need to extract just the OccurrenceUsageElement and put it in a list
        if inner_element.get("name") == "UsageElement":
            occ_elem = inner_element.get("ownedRelatedElement", {})
            if occ_elem.get("name") == "OccurrenceUsageElement":
                # Check if it's a StructureUsageElement with InterfaceUsage
                inner2 = occ_elem.get("ownedRelatedElement", {})
                if inner2.get("name") == "StructureUsageElement":
                    inner3 = inner2.get("ownedRelatedElement", {})
                    if inner3.get("name") == "InterfaceUsage":
                        # For InterfaceUsage, keep the full UsageElement structure
                        # but we need to create a wrapper that doesn't break the class hierarchy
                        owned = [{
                            "name": "OccurrenceUsageElement",
                            "ownedRelatedElement": inner3  # InterfaceUsage directly, not wrapped in StructureUsageElement
                        }]
                    else:
                        owned = [occ_elem]
                else:
                    owned = [occ_elem]
            else:
                owned = [inner_element]
        else:
            owned = [inner_element]
    elif wrapper == "InterfaceOccurrenceUsageMember":
        # InterfaceOccurrenceUsageMember expects ownedRelatedElement as a list of InterfaceOccurrenceUsageElement dicts
        # Each InterfaceOccurrenceUsageElement has: element (DefaultInterfaceEnd or StructureUsageElement dict)
        if inner_element.get("name") == "UsageElement":
            occ_elem_dict = inner_element.get("ownedRelatedElement", {})
            if occ_elem_dict.get("name") == "OccurrenceUsageElement":
                struct_usage_elem = occ_elem_dict.get("ownedRelatedElement", {})
                inner_usage = struct_usage_elem.get("ownedRelatedElement", {})
                usage_name = inner_usage.get("name", "") if isinstance(inner_usage, dict) else ""
                
                # For ConnectionUsage and other structure usages, keep as StructureUsageElement
                if usage_name in ("ConnectionUsage", "FlowConnectionUsage", "SuccessionFlowConnectionUsage", "InterfaceUsage"):
                    iface_elem = {
                        "name": "InterfaceOccurrenceUsageElement",
                        "element": struct_usage_elem
                    }
                    owned = [iface_elem]
                else:
                    # For PartUsage, ItemUsage, PortUsage, convert to DefaultInterfaceEnd
                    part_usage_prefix = inner_usage.get("prefix", {}) if isinstance(inner_usage, dict) else {}
                    occ_prefix = part_usage_prefix.get("prefix", {}) if isinstance(part_usage_prefix, dict) else {}
                    ref_prefix = occ_prefix.get("prefix", {}) if isinstance(occ_prefix, dict) else {}
                    is_abstract = ref_prefix.get("isAbstract") if isinstance(ref_prefix, dict) else None
                    is_variation = ref_prefix.get("isVariation") if isinstance(ref_prefix, dict) else None
                    is_end = ref_prefix.get("isEnd") if isinstance(ref_prefix, dict) else None
                    usage_dict = inner_usage.get("usage", {})
                    direction = None
                    if isinstance(ref_prefix, dict) and "direction" in ref_prefix:
                        dir_dict = ref_prefix["direction"]
                        if dir_dict and isinstance(dir_dict, dict) and len(dir_dict) > 0:
                            direction = dir_dict
                    # Preserve the keyword from the usage type
                    # Only set keyword for non-default types (item/port).
                    # PartUsage is the default interface end type — no keyword needed.
                    usage_to_keyword = {"ItemUsage": "item", "PortUsage": "port"}
                    keyword = usage_to_keyword.get(usage_name, None)
                    default_interface_end = {
                        "name": "DefaultInterfaceEnd",
                        "direction": direction,
                        "isAbstract": is_abstract,
                        "isVariation": is_variation,
                        "isEnd": is_end,
                        "keyword": keyword,
                        "usage": usage_dict
                    }
                    iface_elem = {
                        "name": "InterfaceOccurrenceUsageElement",
                        "element": default_interface_end
                    }
                    owned = [iface_elem]
            else:
                default_interface_end = {
                    "name": "DefaultInterfaceEnd",
                    "direction": None,
                    "isAbstract": None,
                    "isVariation": None,
                    "isEnd": "end",
                    "usage": None
                }
                iface_elem = {
                    "name": "InterfaceOccurrenceUsageElement",
                    "element": default_interface_end
                }
                owned = [iface_elem]
        else:
            default_interface_end = {
                "name": "DefaultInterfaceEnd",
                "direction": None,
                "isAbstract": None,
                "isVariation": None,
                "isEnd": "end",
                "usage": None
            }
            iface_elem = {
                "name": "InterfaceOccurrenceUsageElement",
                "element": default_interface_end
            }
            owned = [iface_elem]
    elif wrapper == "NonOccurrenceUsageMember":
        # NonOccurrenceUsageMember expects ownedRelatedElement to be a list
        if inner_element.get("name") == "NonOccurrenceUsageElement":
            owned = [inner_element]
        else:
            owned = [inner_element]
    else:
        # DefinitionMember - expects ownedRelatedElement to be a list of DefinitionElements
        # inner_element from _visit_nested_definition_element is a PackageMember containing DefinitionElement
        # We need to extract the DefinitionElement
        if inner_element.get("name") == "PackageMember":
            de = inner_element.get("ownedRelatedElement", {})
            if de.get("name") == "DefinitionElement":
                owned = [de]
            else:
                owned = [inner_element]
        elif inner_element.get("name") == "DefinitionElement":
            owned = [inner_element]
        else:
            owned = [inner_element]
    
    # print(f"DEBUG: Returning DefinitionBodyItem with wrapper={wrapper}, owned={owned}")
    return {
        "name": "InterfaceBodyItem" if is_interface else "DefinitionBodyItem",
        "ownedRelationship": [
            {
                "name": wrapper,
                "prefix": None,
                "ownedRelatedElement": owned
            }
        ]
    }


def _visit_nested_occurrence_usage(occ_elem):
    """Visit an occurrence usage element for nested body items."""
    if occ_elem is None:
        return None
    
    # Handle case where occ_elem is directly a StructureUsageElementContext
    if type(occ_elem).__name__ == 'StructureUsageElementContext':
        if hasattr(occ_elem, 'itemUsage') and occ_elem.itemUsage():
            ctx = occ_elem.itemUsage()
            name, shortname = _get_usage_identification(ctx)
            body_items = _get_usage_body_items(ctx)
            occ_prefix = _get_occurrence_usage_prefix(ctx)
            specialization = _build_full_specialization_from_ctx(ctx)
            valuepart = _get_usage_value_part(ctx)
            return _make_nested_usage_element("ItemUsage", name, shortname, occ_prefix, body_items, specialization, valuepart)
        elif hasattr(occ_elem, 'partUsage') and occ_elem.partUsage():
            ctx = occ_elem.partUsage()
            name, shortname = _get_usage_identification(ctx)
            body_items = _get_usage_body_items(ctx)
            occ_prefix = _get_occurrence_usage_prefix(ctx)
            specialization = _build_full_specialization_from_ctx(ctx)
            valuepart = _get_usage_value_part(ctx)
            return _make_nested_usage_element("PartUsage", name, shortname, occ_prefix, body_items, specialization, valuepart)
        elif hasattr(occ_elem, 'portUsage') and occ_elem.portUsage():
            ctx = occ_elem.portUsage()
            name, shortname = _get_usage_identification(ctx)
            body_items = _get_usage_body_items(ctx)
            occ_prefix = _get_occurrence_usage_prefix(ctx)
            specialization = _build_full_specialization_from_ctx(ctx)
            valuepart = _get_usage_value_part(ctx)
            return _make_nested_usage_element("PortUsage", name, shortname, occ_prefix, body_items, specialization, valuepart)
        elif hasattr(occ_elem, 'flowUsage') and occ_elem.flowUsage():
            ctx = occ_elem.flowUsage()
            return _make_nested_flow_connection_usage_dict(ctx, None)
        elif hasattr(occ_elem, 'flowConnectionUsage') and occ_elem.flowConnectionUsage():
            ctx = occ_elem.flowConnectionUsage()
            return _make_nested_flow_connection_usage_dict(ctx, None)
        elif hasattr(occ_elem, 'successionFlowUsage') and occ_elem.successionFlowUsage():
            ctx = occ_elem.successionFlowUsage()
            return _make_nested_succession_flow_usage_dict(ctx, None)
        elif hasattr(occ_elem, 'connectionUsage') and occ_elem.connectionUsage():
            ctx = occ_elem.connectionUsage()
            return _make_nested_connection_usage_dict(ctx, None)
        elif hasattr(occ_elem, 'interfaceUsage') and occ_elem.interfaceUsage():
            ctx = occ_elem.interfaceUsage()
            result = _make_interface_usage_dict(ctx, None)
            if result and result.get("name") == "PackageMember":
                inner = result.get("ownedRelatedElement", {})
                return inner
            return result
        elif hasattr(occ_elem, 'renderingUsage') and occ_elem.renderingUsage():
            ctx = occ_elem.renderingUsage()
            result = _make_rendering_usage_dict(ctx, None)
            if result and result.get("name") == "PackageMember":
                inner = result.get("ownedRelatedElement", {})
                return inner
            return result
        elif hasattr(occ_elem, 'portionUsage') and occ_elem.portionUsage():
            ctx = occ_elem.portionUsage()
            name, shortname = _get_usage_identification(ctx)
            body_items = _get_usage_body_items(ctx)
            occ_prefix = _make_portion_usage_prefix(ctx)
            specialization = _build_full_specialization_from_ctx(ctx)
            valuepart = _get_usage_value_part(ctx)
            return _make_nested_usage_element("PortionUsage", name, shortname, occ_prefix, body_items, specialization, valuepart)
        elif hasattr(occ_elem, 'individualUsage') and occ_elem.individualUsage():
            ctx = occ_elem.individualUsage()
            name, shortname = _get_usage_identification(ctx)
            body_items = _get_usage_body_items(ctx)
            occ_prefix = _make_portion_usage_prefix(ctx)
            specialization = _build_full_specialization_from_ctx(ctx)
            valuepart = _get_usage_value_part(ctx)
            return _make_nested_usage_element("PortionUsage", name, shortname, occ_prefix, body_items, specialization, valuepart)
        return None
    
    # print(f"DEBUG _visit_nested_occurrence_usage: {type(occ_elem).__name__}")
    
    # Check structure usage elements (part, item, port)
    if hasattr(occ_elem, 'structureUsageElement') and occ_elem.structureUsageElement():
        struct_elem = occ_elem.structureUsageElement()
        # print(f"DEBUG: Has structureUsageElement: {struct_elem}")
        
        if hasattr(struct_elem, 'partUsage') and struct_elem.partUsage():
            ctx = struct_elem.partUsage()
            # print(f"DEBUG: Found partUsage: {ctx}")
            name, shortname = _get_usage_identification(ctx)
            # print(f"DEBUG: partUsage name: {name}, shortname: {shortname}")
            body_items = _get_usage_body_items(ctx)
            occ_prefix = _get_occurrence_usage_prefix(ctx)
            specialization = _build_full_specialization_from_ctx(ctx)
            valuepart = _get_usage_value_part(ctx)
            return _make_nested_usage_element("PartUsage", name, shortname, occ_prefix, body_items, specialization, valuepart)
        elif hasattr(struct_elem, 'itemUsage') and struct_elem.itemUsage():
            ctx = struct_elem.itemUsage()
            # print(f"DEBUG: Found itemUsage: {ctx}")
            name, shortname = _get_usage_identification(ctx)
            body_items = _get_usage_body_items(ctx)
            occ_prefix = _get_occurrence_usage_prefix(ctx)
            specialization = _build_full_specialization_from_ctx(ctx)
            valuepart = _get_usage_value_part(ctx)
            return _make_nested_usage_element("ItemUsage", name, shortname, occ_prefix, body_items, specialization, valuepart)
        elif hasattr(struct_elem, 'portUsage') and struct_elem.portUsage():
            ctx = struct_elem.portUsage()
            name, shortname = _get_usage_identification(ctx)
            body_items = _get_usage_body_items(ctx)
            occ_prefix = _get_occurrence_usage_prefix(ctx)
            specialization = _build_full_specialization_from_ctx(ctx)
            valuepart = _get_usage_value_part(ctx)
            return _make_nested_usage_element("PortUsage", name, shortname, occ_prefix, body_items, specialization, valuepart)
        elif hasattr(struct_elem, 'interfaceUsage') and struct_elem.interfaceUsage():
            ctx = struct_elem.interfaceUsage()
            result = _make_interface_usage_dict(ctx, None)
            if result and result.get("name") == "PackageMember":
                inner = result.get("ownedRelatedElement", {})
                return inner  # Extract the inner UsageElement for nested usage
            return result
        elif hasattr(struct_elem, 'flowUsage') and struct_elem.flowUsage():
            ctx = struct_elem.flowUsage()
            return _make_nested_flow_connection_usage_dict(ctx, None)
        elif hasattr(struct_elem, 'flowConnectionUsage') and struct_elem.flowConnectionUsage():
            ctx = struct_elem.flowConnectionUsage()
            return _make_nested_flow_connection_usage_dict(ctx, None)
        elif hasattr(struct_elem, 'successionFlowUsage') and struct_elem.successionFlowUsage():
            ctx = struct_elem.successionFlowUsage()
            return _make_nested_succession_flow_usage_dict(ctx, None)
        elif hasattr(struct_elem, 'connectionUsage') and struct_elem.connectionUsage():
            ctx = struct_elem.connectionUsage()
            return _make_nested_connection_usage_dict(ctx, None)
        elif hasattr(struct_elem, 'allocationUsage') and struct_elem.allocationUsage():
            # Phase 0: allocation usages inside a definition body.
            ctx = struct_elem.allocationUsage()
            result = _make_allocation_usage_dict(ctx, None)
            if result and result.get("name") == "PackageMember":
                # Unwrap the PackageMember -> UsageElement chain so the
                # body builder sees an OccurrenceUsageElement at the
                # expected position.
                return result.get("ownedRelatedElement")
            return result
        elif hasattr(struct_elem, 'portionUsage') and struct_elem.portionUsage():
            ctx = struct_elem.portionUsage()
            name, shortname = _get_usage_identification(ctx)
            body_items = _get_usage_body_items(ctx)
            occ_prefix = _make_portion_usage_prefix(ctx)
            specialization = _build_full_specialization_from_ctx(ctx)
            valuepart = _get_usage_value_part(ctx)
            return _make_nested_usage_element("PortionUsage", name, shortname, occ_prefix, body_items, specialization, valuepart)
        elif hasattr(struct_elem, 'individualUsage') and struct_elem.individualUsage():
            ctx = struct_elem.individualUsage()
            name, shortname = _get_usage_identification(ctx)
            body_items = _get_usage_body_items(ctx)
            occ_prefix = _make_portion_usage_prefix(ctx)
            specialization = _build_full_specialization_from_ctx(ctx)
            valuepart = _get_usage_value_part(ctx)
            return _make_nested_usage_element("PortionUsage", name, shortname, occ_prefix, body_items, specialization, valuepart)
    
    # Check for interface occurrence usage element (has defaultInterfaceEnd keyword)
    if hasattr(occ_elem, 'defaultInterfaceEnd') and occ_elem.defaultInterfaceEnd() is not None:
        default_interface_end_ctx = occ_elem.defaultInterfaceEnd()
        # print(f"DEBUG: Found defaultInterfaceEnd: {default_interface_end_ctx}")
        if default_interface_end_ctx and hasattr(default_interface_end_ctx, 'usage') and default_interface_end_ctx.usage():
            # Pass default_interface_end_ctx to _get_usage_body_items since it has usage() method
            name, shortname = _get_usage_identification(default_interface_end_ctx)
            # print(f"DEBUG: Name: {name}, Shortname: {shortname}")
            body_items = _get_usage_body_items(default_interface_end_ctx)
            # print(f"DEBUG: Body items: {body_items}")
            occ_prefix = _get_occurrence_usage_prefix(default_interface_end_ctx)
            # print(f"DEBUG: Occ prefix: {occ_prefix}")
            # If we have a defaultInterfaceEnd, we need to set the is_end flag in the occurrence usage prefix
            if hasattr(default_interface_end_ctx, 'END') and default_interface_end_ctx.END() is not None:
                if occ_prefix is None:
                    # Create a ref_prefix with just the end flag
                    ref_prefix = {
                        "name": "RefPrefix",
                        "direction": {
                            "name": "FeatureDirection",
                            "in": "",
                            "out": "",
                            "inout": ""
                        },
                        "isAbstract": None,
                        "isVariation": None,
                        "isReadOnly": None,
                        "isDerived": None,
                        "isEnd": "end"
                    }
                    occ_prefix = {
                        "name": "OccurrenceUsagePrefix",
                        "prefix": {
                            "name": "BasicUsagePrefix",
                            "prefix": ref_prefix,
                            "isReference": False
                        },
                        "isIndividual": None,
                        "portionKind": None,
                        "usageExtension": []
                    }
                else:
                    # Update the existing occ_prefix to set isEnd
                    # The occ_prefix structure: {name: "OccurrenceUsagePrefix", prefix: {name: "BasicUsagePrefix", prefix: ref_prefix, isReference: bool}, ...}
                    basic_prefix = occ_prefix["prefix"]["prefix"]
                    if basic_prefix and basic_prefix["name"] == "RefPrefix":
                        basic_prefix["direction"]["isEnd"] = "end"
                    else:
                        # This should not happen if occ_prefix is not None, but just in case
                        # We'll create a new RefPrefix with the end flag and keep the existing direction if possible?
                        # For simplicity, we'll assume the direction is empty and just set the end flag.
                        ref_prefix = {
                            "name": "RefPrefix",
                            "direction": {
                                "name": "FeatureDirection",
                                "in": "",
                                "out": "",
                                "inout": "",
                                "isEnd": "end"
                            },
                            "isAbstract": None,
                            "isVariation": None,
                            "isReadOnly": None,
                            "isDerived": None
                        }
                        occ_prefix["prefix"]["prefix"] = ref_prefix
            specialization = _build_full_specialization_from_ctx(default_interface_end_ctx)
            return _make_nested_usage_element("PartUsage", name, shortname, occ_prefix, body_items, specialization)
    if hasattr(occ_elem, 'behaviorUsageElement') and occ_elem.behaviorUsageElement():
        behav_elem = occ_elem.behaviorUsageElement()
        if isinstance(behav_elem, list):
            behav_elem = behav_elem[0]
        
        if hasattr(behav_elem, 'actionUsage') and behav_elem.actionUsage():
            ctx = behav_elem.actionUsage()
            # Use action usage navigation
            name = None
            shortname = None
            if ctx.actionUsageDeclaration():
                aud = ctx.actionUsageDeclaration()
                if hasattr(aud, 'usageDeclaration') and aud.usageDeclaration():
                    ud = aud.usageDeclaration()
                    if ud and hasattr(ud, 'identification') and ud.identification():
                        ident = ud.identification()
                        if hasattr(ident, 'name'):
                            name_list = ident.name()
                            if name_list and isinstance(name_list, list):
                                if len(name_list) == 2:
                                    shortname = name_list[0].getText()
                                    name = name_list[1].getText()
                                elif len(name_list) == 1:
                                    name_text = name_list[0].getText()
                                    name, shortname = _extract_name_shortname(name_text)
            
            # Get body items from action body
            action_items = _visit_action_body_items(ctx)
            
            # Extract typed_by for the specialization
            typed_by = _get_action_usage_typed_by(ctx)
            if typed_by is None:
                typed_by = _get_action_usage_subsetted_by(ctx)
            spec_full = _full_specialization_for_ctx(ctx)
            if spec_full is not None:
                specialization = spec_full
            else:
                specialization = _build_specialization(typed_by) if typed_by else None
            
            occ_prefix = _get_occurrence_usage_prefix(ctx)
            
            return {
                "name": "UsageElement",
                "ownedRelatedElement": {
                    "name": "OccurrenceUsageElement",
                    "ownedRelatedElement": {
                        "name": "BehaviorUsageElement",
                        "ownedRelationship": {
                            "name": "ActionUsage",
                            "prefix": occ_prefix,
                            "declaration": {
                                "name": "ActionUsageDeclaration",
                                "declaration": {
                                    "name": "UsageDeclaration",
                                    "declaration": {
                                        "name": "FeatureDeclaration",
                                        "identification": {
                                            "name": "Identification",
                                            "declaredShortName": shortname,
                                            "declaredName": name
                                        },
                                        "specialization": specialization
                                    }
                                },
                                "valuepart": None
                            },
                            "body": {
                                "name": "ActionBody",
                                "items": action_items
                            }
                        }
                    }
                }
            }
        elif hasattr(behav_elem, 'performActionUsage') and behav_elem.performActionUsage():
            ctx = behav_elem.performActionUsage()
            return _make_nested_perform_action_usage_dict(ctx, None)
        elif hasattr(behav_elem, 'calculationUsage') and behav_elem.calculationUsage():
            ctx = behav_elem.calculationUsage()
            return _make_nested_calculation_usage_dict(ctx, None)
        elif hasattr(behav_elem, 'constraintUsage') and behav_elem.constraintUsage():
            ctx = behav_elem.constraintUsage()
            result = _make_constraint_usage_dict(ctx, None)
            if result and result.get("name") == "PackageMember":
                return result.get("ownedRelatedElement")
            return result
        elif hasattr(behav_elem, 'requirementUsage') and behav_elem.requirementUsage():
            ctx = behav_elem.requirementUsage()
            result = _make_requirement_usage_dict(ctx, None)
            if result and result.get("name") == "PackageMember":
                return result.get("ownedRelatedElement")
            return result
        elif hasattr(behav_elem, 'assertConstraintUsage') and behav_elem.assertConstraintUsage():
            ctx = behav_elem.assertConstraintUsage()
            result = _make_assert_constraint_usage_dict(ctx, None)
            if result:
                return {
                    "name": "UsageElement",
                    "ownedRelatedElement": {
                        "name": "OccurrenceUsageElement",
                        "ownedRelatedElement": {
                            "name": "BehaviorUsageElement",
                            "ownedRelationship": result
                        }
                    }
                }
            return None
        elif hasattr(behav_elem, 'satisfyRequirementUsage') and behav_elem.satisfyRequirementUsage():
            ctx = behav_elem.satisfyRequirementUsage()
            result = _make_satisfy_requirement_usage_dict(ctx, None)
            if result:
                return {
                    "name": "UsageElement",
                    "ownedRelatedElement": {
                        "name": "OccurrenceUsageElement",
                        "ownedRelatedElement": {
                            "name": "BehaviorUsageElement",
                            "ownedRelationship": result
                        }
                    }
                }
            return None
        elif hasattr(behav_elem, 'analysisCaseUsage') and behav_elem.analysisCaseUsage():
            ctx = behav_elem.analysisCaseUsage()
            return _make_nested_analysis_case_usage_dict(ctx, None)
        elif hasattr(behav_elem, 'caseUsage') and behav_elem.caseUsage():
            ctx = behav_elem.caseUsage()
            return _make_nested_case_usage_dict(ctx, None)
        elif hasattr(behav_elem, 'useCaseUsage') and behav_elem.useCaseUsage():
            ctx = behav_elem.useCaseUsage()
            result = _make_use_case_usage_dict(ctx, None)
            if result and result.get("name") == "PackageMember":
                return result.get("ownedRelatedElement")
            return result
        elif hasattr(behav_elem, 'stateUsage') and behav_elem.stateUsage():
            # Phase 0: state usages live in a BehaviorUsageElement too.
            ctx = behav_elem.stateUsage()
            result = _make_state_usage_dict(ctx, None)
            if result and result.get("name") == "PackageMember":
                inner = result.get("ownedRelatedElement", {})
                return inner
            return result
        elif hasattr(behav_elem, 'allocationUsage') and behav_elem.allocationUsage():
            # Phase 0: allocation usages inside a definition body.
            ctx = behav_elem.allocationUsage()
            result = _make_allocation_usage_dict(ctx, None)
            if result and result.get("name") == "PackageMember":
                # Unwrap the PackageMember -> UsageElement chain so the
                # body builder sees an OccurrenceUsageElement at the
                # expected position.
                return result.get("ownedRelatedElement")
            return result
    
    # print(f"DEBUG: No match found in _visit_nested_occurrence_usage")
    # Fall through to check structure usage elements
    
    # Check structure usage elements (part, item, port, interface, connection, etc.)
    if hasattr(occ_elem, 'structureUsageElement') and occ_elem.structureUsageElement():
        struct_elem = occ_elem.structureUsageElement()
        
        if hasattr(struct_elem, 'partUsage') and struct_elem.partUsage():
            ctx = struct_elem.partUsage()
            name, shortname = _get_usage_identification(ctx)
            body_items = _get_usage_body_items(ctx)
            occ_prefix = _get_occurrence_usage_prefix(ctx)
            specialization = _build_full_specialization_from_ctx(ctx)
            valuepart = _get_usage_value_part(ctx)
            return _make_nested_usage_element("PartUsage", name, shortname, occ_prefix, body_items, specialization, valuepart)
        elif hasattr(struct_elem, 'itemUsage') and struct_elem.itemUsage():
            ctx = struct_elem.itemUsage()
            name, shortname = _get_usage_identification(ctx)
            body_items = _get_usage_body_items(ctx)
            occ_prefix = _get_occurrence_usage_prefix(ctx)
            specialization = _build_full_specialization_from_ctx(ctx)
            valuepart = _get_usage_value_part(ctx)
            return _make_nested_usage_element("ItemUsage", name, shortname, occ_prefix, body_items, specialization, valuepart)
        elif hasattr(struct_elem, 'portUsage') and struct_elem.portUsage():
            ctx = struct_elem.portUsage()
            name, shortname = _get_usage_identification(ctx)
            body_items = _get_usage_body_items(ctx)
            occ_prefix = _get_occurrence_usage_prefix(ctx)
            specialization = _build_full_specialization_from_ctx(ctx)
            valuepart = _get_usage_value_part(ctx)
            return _make_nested_usage_element("PortUsage", name, shortname, occ_prefix, body_items, specialization, valuepart)
        elif hasattr(struct_elem, 'connectionUsage') and struct_elem.connectionUsage():
            ctx = struct_elem.connectionUsage()
            return _make_nested_connection_usage_dict(ctx, None)
        elif hasattr(struct_elem, 'interfaceUsage') and struct_elem.interfaceUsage():
            ctx = struct_elem.interfaceUsage()
            result = _make_interface_usage_dict(ctx, None)
            if result and result.get("name") == "PackageMember":
                inner = result.get("ownedRelatedElement", {})
                return inner
            return result
        elif hasattr(struct_elem, 'renderingUsage') and struct_elem.renderingUsage():
            ctx = struct_elem.renderingUsage()
            result = _make_rendering_usage_dict(ctx, None)
            if result and result.get("name") == "PackageMember":
                inner = result.get("ownedRelatedElement", {})
                return inner
            return result
        elif hasattr(struct_elem, 'portionUsage') and struct_elem.portionUsage():
            ctx = struct_elem.portionUsage()
            name, shortname = _get_usage_identification(ctx)
            body_items = _get_usage_body_items(ctx)
            occ_prefix = _make_portion_usage_prefix(ctx)
            specialization = _build_full_specialization_from_ctx(ctx)
            valuepart = _get_usage_value_part(ctx)
            return _make_nested_usage_element("PortionUsage", name, shortname, occ_prefix, body_items, specialization, valuepart)
        elif hasattr(struct_elem, 'individualUsage') and struct_elem.individualUsage():
            ctx = struct_elem.individualUsage()
            name, shortname = _get_usage_identification(ctx)
            body_items = _get_usage_body_items(ctx)
            occ_prefix = _make_portion_usage_prefix(ctx)
            specialization = _build_full_specialization_from_ctx(ctx)
            valuepart = _get_usage_value_part(ctx)
            return _make_nested_usage_element("PortionUsage", name, shortname, occ_prefix, body_items, specialization, valuepart)
    
    # Check behavior usage elements (action)
    if hasattr(occ_elem, 'behaviorUsageElement') and occ_elem.behaviorUsageElement():
        behav_elem = occ_elem.behaviorUsageElement()
        if hasattr(behav_elem, 'actionUsage') and behav_elem.actionUsage():
            ctx = behav_elem.actionUsage()
            # Use action usage navigation
            name = None
            shortname = None
            if ctx.actionUsageDeclaration():
                aud = ctx.actionUsageDeclaration()
                if hasattr(aud, 'usageDeclaration') and aud.usageDeclaration():
                    ud = aud.usageDeclaration()
                    if ud and hasattr(ud, 'identification') and ud.identification():
                        ident = ud.identification()
                        if hasattr(ident, 'name'):
                            name_list = ident.name()
                            if name_list and isinstance(name_list, list):
                                if len(name_list) == 2:
                                    shortname = name_list[0].getText()
                                    name = name_list[1].getText()
                                elif len(name_list) == 1:
                                    name_text = name_list[0].getText()
                                    name, shortname = _extract_name_shortname(name_text)
            return {
                "name": "UsageElement",
                "ownedRelatedElement": {
                    "name": "OccurrenceUsageElement",
                    "ownedRelatedElement": {
                        "name": "BehaviorUsageElement",
                        "ownedRelationship": {
                            "name": "ActionUsage",
                            "prefix": None,
                            "declaration": {
                                "name": "ActionUsageDeclaration",
                                "declaration": {
                                    "name": "UsageDeclaration",
                                    "declaration": {
                                        "name": "FeatureDeclaration",
                                        "identification": {
                                            "name": "Identification",
                                            "declaredShortName": shortname,
                                            "declaredName": name
                                        },
                                        "specialization": None
                                    }
                                },
                                "valuepart": None
                            },
                            "body": {
                                "name": "ActionBody",
                                "items": []
                            }
                        }
                    }
                }
            }
        
        if hasattr(behav_elem, 'assertConstraintUsage') and behav_elem.assertConstraintUsage():
            ctx = behav_elem.assertConstraintUsage()
            result = _make_assert_constraint_usage_dict(ctx, None)
            if result:
                return {
                    "name": "UsageElement",
                    "ownedRelatedElement": {
                        "name": "OccurrenceUsageElement",
                        "ownedRelatedElement": {
                            "name": "BehaviorUsageElement",
                            "ownedRelationship": result
                        }
                    }
                }
            return None
    
    return None


def _get_usage_prefix_dict(ctx):
    """Extract UsagePrefix dict from an attributeUsage (or similar) context.
    Returns None if no direction/ref is present.
    """
    if ctx is None:
        return None
    if not (hasattr(ctx, 'usagePrefix') and ctx.usagePrefix()):
        return None
    
    up = ctx.usagePrefix()
    is_reference = False
    direction_in = ""
    direction_out = ""
    direction_inout = ""
    
    # Navigate: usagePrefix -> unextendedUsagePrefix -> basicUsagePrefix -> refPrefix
    bup = None
    if hasattr(up, 'unextendedUsagePrefix') and up.unextendedUsagePrefix():
        uep = up.unextendedUsagePrefix()
        if hasattr(uep, 'basicUsagePrefix') and uep.basicUsagePrefix():
            bup = uep.basicUsagePrefix()
    elif hasattr(up, 'basicUsagePrefix') and up.basicUsagePrefix():
        bup = up.basicUsagePrefix()
    
    if bup:
        is_reference = hasattr(bup, 'REF') and bup.REF() is not None
        if hasattr(bup, 'refPrefix') and bup.refPrefix():
            rp = bup.refPrefix()
            if hasattr(rp, 'featureDirection') and rp.featureDirection():
                fd = rp.featureDirection()
                direction_in = "in " if (hasattr(fd, 'IN') and fd.IN() is not None) else ""
                direction_out = "out" if (hasattr(fd, 'OUT') and fd.OUT() is not None) else ""
                direction_inout = "inout" if (hasattr(fd, 'INOUT') and fd.INOUT() is not None) else ""
    
    has_direction = any([direction_in, direction_out, direction_inout])
    if not is_reference and not has_direction:
        return None
    
    ref_prefix = None
    if has_direction:
        ref_prefix = {
            "name": "RefPrefix",
            "direction": {
                "name": "FeatureDirection",
                "in": direction_in,
                "out": direction_out,
                "inout": direction_inout
            },
            "isAbstract": None,
            "isVariation": None,
            "isReadOnly": None,
            "isDerived": None,
            "isEnd": None
        }
    
    return {
        "name": "UsagePrefix",
        "prefix": {
            "name": "BasicUsagePrefix",
            "prefix": ref_prefix,
            "isReference": is_reference
        },
        "usageKeyword": []
    }


def _visit_nested_non_occurrence_usage(non_occ):
    """Visit a non-occurrence usage element for nested body items."""
    if non_occ is None:
        return None
    
    # Handle endFeatureUsage (end bead : TireBead[1];)
    if hasattr(non_occ, 'endFeatureUsage') and non_occ.endFeatureUsage():
        ctx = non_occ.endFeatureUsage()
        return _make_end_feature_usage_dict(ctx)
    
    # Handle referenceUsage (ref :>> payload : Fuel;)
    if hasattr(non_occ, 'referenceUsage') and non_occ.referenceUsage():
        ctx = non_occ.referenceUsage()
        return _make_reference_usage_dict(ctx)
    
    if hasattr(non_occ, 'attributeUsage') and non_occ.attributeUsage():
        ctx = non_occ.attributeUsage()
        name, shortname = _get_usage_identification(ctx)
        specialization = _build_full_specialization_from_ctx(ctx)
        valuepart = _get_usage_value_part(ctx)
        usage_prefix = _get_usage_prefix_dict(ctx)
        body_elements = _extract_body_from_usage_ctx(ctx)
        return {
            "name": "NonOccurrenceUsageElement",
            "ownedRelatedElement": {
                "name": "AttributeUsage",
                "prefix": usage_prefix,
                "usage": {
                    "name": "Usage",
                    "declaration": {
                        "name": "UsageDeclaration",
                        "declaration": {
                            "name": "FeatureDeclaration",
                            "identification": {
                                "name": "Identification",
                                "declaredShortName": shortname,
                                "declaredName": name
                            },
                            "specialization": specialization
                        }
                    },
                    "completion": {
                        "name": "UsageCompletion",
                        "valuepart": valuepart,
                        "body": {
                            "name": "UsageBody",
                            "body": {
                                "name": "DefinitionBody",
                                "ownedRelatedElement": body_elements
                            }
                        }
                    }
                }
            }
        }
    
    # Handle defaultReferenceUsage (directed features like "in Fuel;", "out Fuel;")
    if hasattr(non_occ, 'defaultReferenceUsage') and non_occ.defaultReferenceUsage():
        ctx = non_occ.defaultReferenceUsage()
        return _make_default_reference_usage_dict(ctx)
    
    # Handle bindingConnectorAsUsage (bind X = Y)
    if hasattr(non_occ, 'bindingConnectorAsUsage') and non_occ.bindingConnectorAsUsage():
        ctx = non_occ.bindingConnectorAsUsage()
        return _make_binding_connector_dict(ctx)
    
    # Handle successionAsUsage (first X then Y)
    if hasattr(non_occ, 'successionAsUsage') and non_occ.successionAsUsage():
        ctx = non_occ.successionAsUsage()
        return _make_succession_as_usage_dict(ctx)
    
    return None


def _build_owned_reference_subsetting_dict(ors_ctx):
    """Build an OwnedReferenceSubsetting dict from an ownedReferenceSubsetting context.
    
    ownedReferenceSubsetting : qualifiedName (DOT qualifiedName)*
    
    Single qualifiedName -> referencedFeature
    Multiple (e.g. focus.scene) -> ownedRelatedElement feature chain
    """
    if ors_ctx is None:
        return None
    
    qnames = ors_ctx.qualifiedName()
    if not isinstance(qnames, list):
        qnames = [qnames]
    
    if len(qnames) == 1:
        # Single qualified name - referencedFeature
        qn = qnames[0]
        names = [n.getText() for n in qn.name()] if hasattr(qn, 'name') and qn.name() else []
        return {
            "name": "OwnedReferenceSubsetting",
            "referencedFeature": {
                "name": "QualifiedName",
                "names": names
            },
            "ownedRelatedElement": []
        }
    else:
        # Multiple qualified names - feature chain
        chain_elements = []
        for qn in qnames:
            names = [n.getText() for n in qn.name()] if hasattr(qn, 'name') and qn.name() else []
            chain_elements.append({
                "name": "OwnedFeatureChaining",
                "chainingFeature": {
                    "name": "QualifiedName",
                    "names": names
                }
            })
        return {
            "name": "OwnedReferenceSubsetting",
            "referencedFeature": None,
            "ownedRelatedElement": [{
                "name": "OwnedFeatureChain",
                "feature": {
                    "name": "FeatureChain",
                    "ownedRelationship": chain_elements
                }
            }]
        }


def _build_connector_end_member_dict(cem_ctx):
    """Build a ConnectorEndMember dict from a connectorEndMember context.
    
    connectorEndMember : connectorEnd ;
    connectorEnd : (ownedCrossMultiplicityMember)? (name (COLON_COLON_GT | REFERENCES))? ownedReferenceSubsetting ;
    """
    if cem_ctx is None:
        return None
    
    ce_ctx = cem_ctx.connectorEnd() if hasattr(cem_ctx, 'connectorEnd') else None
    if ce_ctx is None:
        return None
    
    declared_name = None
    if hasattr(ce_ctx, 'name') and ce_ctx.name():
        declared_name = ce_ctx.name().getText()
    
    relationships = []
    if hasattr(ce_ctx, 'ownedReferenceSubsetting') and ce_ctx.ownedReferenceSubsetting():
        ors = _build_owned_reference_subsetting_dict(ce_ctx.ownedReferenceSubsetting())
        if ors:
            relationships.append(ors)
    
    return {
        "name": "ConnectorEndMember",
        "ownedRelatedElement": [{
            "name": "ConnectorEnd",
            "declaredName": declared_name,
            "ownedRelationship": relationships
        }]
    }


def _make_binding_connector_dict(ctx):
    """Create a NonOccurrenceUsageElement dict wrapping a BindingConnector.
    
    Grammar:
      bindingConnectorAsUsage
        : usagePrefix (BINDING usageDeclaration?)? BIND connectorEndMember EQ connectorEndMember usageBody
    """
    if ctx is None:
        return None
    
    # Get connector ends
    ends = []
    if hasattr(ctx, 'connectorEndMember') and ctx.connectorEndMember():
        cem_list = ctx.connectorEndMember()
        if not isinstance(cem_list, list):
            cem_list = [cem_list]
        for cem in cem_list:
            cem_dict = _build_connector_end_member_dict(cem)
            if cem_dict:
                ends.append(cem_dict)
    
    # Check for optional declaration (BINDING usageDeclaration)
    declaration = None
    if hasattr(ctx, 'usageDeclaration') and ctx.usageDeclaration():
        ud = ctx.usageDeclaration()
        if ud is not None:
            # Extract name from usageDeclaration
            decl_name = None
            decl_shortname = None
            if hasattr(ud, 'identification') and ud.identification():
                ident = ud.identification()
                if hasattr(ident, 'name'):
                    name_list = ident.name()
                    if name_list and isinstance(name_list, list):
                        if len(name_list) == 2:
                            decl_shortname = name_list[0].getText()
                            decl_name = name_list[1].getText()
                        elif len(name_list) == 1:
                            decl_name = name_list[0].getText()
            declaration = {
                "name": "UsageDeclaration",
                "declaration": {
                    "name": "FeatureDeclaration",
                    "identification": {
                        "name": "Identification",
                        "declaredShortName": decl_shortname,
                        "declaredName": decl_name
                    },
                    "specialization": None
                }
            }
    
    return {
        "name": "NonOccurrenceUsageElement",
        "ownedRelatedElement": {
            "name": "BindingConnector",
            "prefix": None,
            "declaration": declaration,
            "ownedRelationship": ends,
            "body": {
                "name": "DefinitionBody",
                "ownedRelatedElement": []
            }
        }
    }


def _make_succession_as_usage_dict(ctx):
    """Create a NonOccurrenceUsageElement dict wrapping a Succession.
    
    Grammar:
      successionAsUsage
        : usagePrefix (SUCCESSION usageDeclaration?)? FIRST connectorEndMember THEN connectorEndMember usageBody
    """
    if ctx is None:
        return None
    
    # Get connector ends
    ends = []
    if hasattr(ctx, 'connectorEndMember') and ctx.connectorEndMember():
        cem_list = ctx.connectorEndMember()
        if not isinstance(cem_list, list):
            cem_list = [cem_list]
        for cem in cem_list:
            cem_dict = _build_connector_end_member_dict(cem)
            if cem_dict:
                ends.append(cem_dict)
    
    # Check for optional declaration (SUCCESSION usageDeclaration)
    declaration = None
    if hasattr(ctx, 'usageDeclaration') and ctx.usageDeclaration():
        ud = ctx.usageDeclaration()
        if ud is not None:
            decl_name = None
            decl_shortname = None
            if hasattr(ud, 'identification') and ud.identification():
                ident = ud.identification()
                if hasattr(ident, 'name'):
                    name_list = ident.name()
                    if name_list and isinstance(name_list, list):
                        if len(name_list) == 2:
                            decl_shortname = name_list[0].getText()
                            decl_name = name_list[1].getText()
                        elif len(name_list) == 1:
                            decl_name = name_list[0].getText()
            declaration = {
                "name": "UsageDeclaration",
                "declaration": {
                    "name": "FeatureDeclaration",
                    "identification": {
                        "name": "Identification",
                        "declaredShortName": decl_shortname,
                        "declaredName": decl_name
                    },
                    "specialization": None
                }
            }
    
    return {
        "name": "NonOccurrenceUsageElement",
        "ownedRelatedElement": {
            "name": "Succession",
            "prefix": None,
            "declaration": declaration,
            "ownedRelationship": ends,
            "body": {
                "name": "DefinitionBody",
                "ownedRelatedElement": []
            }
        }
    }


# Phase 1: precedence-climbing expression capture
# -----------------------------------------------
# The vendored SysML v2 grammar lists all binary operators in the same
# ``ownedExpression`` rule with equal precedence, so ANTLR left-associates
# and produces a non-precedence-respecting parse (e.g. ``a + b * c`` is
# parsed as ``(a+b) * c``). To recover the correct precedence, we run
# our own precedence-climbing pass on the ANTLR children list and
# build the structured chain from the resulting tree.
#
# Precedence ranks: HIGHER number = binds TIGHTER. The lowest-rank
# operator in the children list is the one that should be the top of
# the tree. For left-associative operators at the same rank, we pick
# the RIGHTMOST one (so ``a - b - c`` becomes ``(a-b) - c``).
# Exponentiation (``**``/``^``) is right-associative per the grammar.

_PRECEDENCE_RANK = {
    # Logical (lowest binding)
    "implies": 1,
    "or": 2,
    "xor": 3,
    "and": 4,
    # Equality / classification
    "==": 5, "!=": 5, "===": 5, "!==": 5,
    "istype": 5, "hastype": 5,
    # Relational
    "<": 6, ">": 6, "<=": 6, ">=": 6,
    # Range
    "..": 7,
    # Additive
    "+": 8, "-": 8,
    # Multiplicative
    "*": 9, "/": 9, "%": 9,
    # Exponentiation (right-associative)
    "**": 10, "^": 10,
}

# Operator → grammar-class layer name. The chain has parallel layers
# for each of these; the operator populates the layer's operator/operation
# field and the rhs is unwrapped to the next-lower layer.
_OPERATOR_TO_LAYER = {
    "implies": "ImpliesExpression",
    "or": "OrExpression",
    "xor": "XorExpression",
    "and": "AndExpression",
    "==": "EqualityExpression",
    "!=": "EqualityExpression",
    "===": "EqualityExpression",
    "!==": "EqualityExpression",
    "istype": "EqualityExpression",
    "hastype": "EqualityExpression",
    "<": "RelationalExpression",
    ">": "RelationalExpression",
    "<=": "RelationalExpression",
    ">=": "RelationalExpression",
    "..": "RangeExpression",
    "+": "AdditiveExpression",
    "-": "AdditiveExpression",
    "*": "MultiplicativeExpression",
    "/": "MultiplicativeExpression",
    "%": "MultiplicativeExpression",
    "**": "ExponentiationExpression",
    "^": "ExponentiationExpression",
}

# Tokens that are field access (DOT, DOT_QUESTION, ARROW, QUESTION
# inside an ownedExpression for member access) — NOT binary operators.
# They belong to the base expression's qualifiedName rule.
_FIELD_ACCESS_TOKENS = {".", "?.", "->", "?"}
# QUESTION used for ternary IF ? : is a separator, not a binary op.
# The ternary is handled separately in the IF/THEN/ELSE branch.

# Tokens that are part of unary prefix forms: +, -, ~, not
_UNARY_PREFIX_TOKENS = {"+", "-", "~", "not"}


def _is_binary_operator_token(text):
    """True if the token text is a recognized binary operator."""
    return text in _PRECEDENCE_RANK


def _is_unary_prefix_token(text):
    """True if the token text is a recognized unary prefix operator."""
    return text in _UNARY_PREFIX_TOKENS


def _find_split_index(children, left_assoc=True):
    """Find the index of the operator that should be the TOP of the tree.

    Walks ``children`` (the ANTLR children list of an ownedExpression
    context, alternating OwnedExpr/TerminalNode) and finds the operator
    with the LOWEST precedence rank. For left-associative operators
    at the same rank, returns the RIGHTMOST index (so ``a - b - c``
    becomes ``(a - b) - c``). For right-associative (``**``/``^``),
    returns the LEFTMOST index.

    Returns (op_index, op_text) or (None, None) if no binary operator
    is found.
    """
    best_idx = None
    best_text = None
    best_rank = None
    for i, c in enumerate(children):
        type_name = type(c).__name__
        if type_name != "TerminalNodeImpl":
            continue
        text = c.getText().strip()
        if text in _FIELD_ACCESS_TOKENS:
            continue
        if not _is_binary_operator_token(text):
            continue
        rank = _PRECEDENCE_RANK[text]
        right_assoc = text in ("**", "^")
        if best_idx is None:
            best_idx, best_text, best_rank = i, text, rank
            continue
        if rank < best_rank:
            # Lower precedence → becomes the new top
            best_idx, best_text, best_rank = i, text, rank
        elif rank == best_rank:
            # Same precedence: prefer the rightmost for left-assoc,
            # leftmost for right-assoc
            if right_assoc:
                if i < best_idx:
                    best_idx, best_text = i, text
            else:
                if i > best_idx:
                    best_idx, best_text = i, text
    return best_idx, best_text


def _build_binary_chain(op_text, lhs_owned_ctx, rhs_owned_ctx):
    """Build a chain for ``lhs OP rhs`` by recursing on each side and
    splicing the operator at the right layer.

    The lhs and rhs are ANTLR ownedExpression contexts. We recursively
    emit each, then splice ``op_text`` at the layer corresponding to
    its precedence. The result is a single OwnedExpression chain
    with the operator populated at the right layer.
    """
    lhs_chain = _emit_structured_expression(lhs_owned_ctx)
    rhs_chain = _emit_structured_expression(rhs_owned_ctx)
    return _splice_operator(lhs_chain, _OPERATOR_TO_LAYER[op_text], op_text, rhs_chain)


def _splice_operator(lhs_chain, layer_name, op_text, rhs_chain):
    """Splice ``op_text`` at ``layer_name`` into ``lhs_chain`` with
    ``rhs_chain`` as the rhs operand.

    The lhs_chain is the result of recursing on the LHS. The rhs_chain
    is the result of recursing on the RHS. The lhs chain has the
    natural chain shape; the rhs chain is unwrapped to the layer
    BELOW the splicing layer (per the grammar-class contract — e.g.
    EqualityOperand.operand expects a ClassificationExpression).

    If the rhs chain has operators at layers ABOVE the splicing layer
    (lower binding power), those operators are PRESERVED by embedding
    the rhs's higher-layer data into the lhs chain at the rhs's
    top-op layer. This handles cases like ``a * b + c`` where ANTLR
    produces ``(a*b) + c`` (the top is ``+``) but the rhs's
    multiplicative layer is empty.
    """
    if not _is_owned_chain(lhs_chain):
        lhs_chain = _wrap_expression_layers(lhs_chain)
    if not _is_owned_chain(rhs_chain):
        rhs_chain = _wrap_expression_layers(rhs_chain)
    rhs_unwrapped = _unwrap_to_layer(rhs_chain, layer_name)
    # Embed any higher-layer operators from rhs into the lhs chain
    _embed_rhs_higher_ops(lhs_chain, rhs_chain, layer_name)

    layer_paths = {
        "EqualityExpression": ["expression", "operand", 0, "implies", "or", "xor", "and", "equality"],
        "RelationalExpression": ["expression", "operand", 0, "implies", "or", "xor", "and", "equality", "classification", "relational"],
        "RangeExpression": ["expression", "operand", 0, "implies", "or", "xor", "and", "equality", "classification", "relational", "range"],
        "AdditiveExpression": ["expression", "operand", 0, "implies", "or", "xor", "and", "equality", "classification", "relational", "range", "additive"],
        "MultiplicativeExpression": ["expression", "operand", 0, "implies", "or", "xor", "and", "equality", "classification", "relational", "range", "additive", "multiplicitive"],
        "ExponentiationExpression": ["expression", "operand", 0, "implies", "or", "xor", "and", "equality", "classification", "relational", "range", "additive", "multiplicitive", "exponential"],
        "AndExpression": ["expression", "operand", 0, "implies", "or", "xor", "and"],
        "OrExpression": ["expression", "operand", 0, "implies", "or"],
        "XorExpression": ["expression", "operand", 0, "implies", "or", "xor"],
        "ImpliesExpression": ["expression", "operand", 0, "implies"],
    }
    path = layer_paths[layer_name]
    node = lhs_chain
    for step in path:
        if isinstance(step, int):
            node = node[step]
        else:
            node = node[step]

    if layer_name == "EqualityExpression":
        existing = node.get("operation", [])
        node["operation"] = existing + [
            {"name": "EqualityOperand", "operator": op_text, "operand": rhs_unwrapped}
        ]
    elif layer_name == "RelationalExpression":
        existing = node.get("operation", [])
        node["operation"] = existing + [
            {"name": "RelationalOperand", "operator": op_text, "operand": rhs_unwrapped}
        ]
    elif layer_name == "RangeExpression":
        node["operand"] = rhs_unwrapped
        node["operator"] = op_text
    elif layer_name == "AdditiveExpression":
        existing = node.get("operation", [])
        node["operation"] = existing + [
            {"name": "AdditiveOperand", "operator": op_text, "operand": rhs_unwrapped}
        ]
    elif layer_name == "MultiplicativeExpression":
        existing = node.get("operation", [])
        node["operation"] = existing + [
            {"name": "MultiplicativeOperand", "operator": op_text, "operand": rhs_unwrapped}
        ]
    elif layer_name == "ExponentiationExpression":
        existing = node.get("operator", [])
        if not isinstance(existing, list):
            existing = [existing] if existing else []
        existing.append(op_text)
        node["operator"] = existing
        existing_op = node.get("operand", [])
        if not isinstance(existing_op, list):
            existing_op = [existing_op] if existing_op else []
        existing_op.append(rhs_unwrapped)
        node["operand"] = existing_op
    elif layer_name == "AndExpression":
        existing = node.get("operation", [])
        node["operation"] = existing + [
            {"name": "AndOperand", "operator": op_text, "operand": rhs_unwrapped}
        ]
    elif layer_name == "OrExpression":
        existing = node.get("operator", [])
        if not isinstance(existing, list):
            existing = [existing] if existing else []
        existing.append(op_text)
        node["operator"] = existing
        existing_op = node.get("operand", [])
        if not isinstance(existing_op, list):
            existing_op = [existing_op] if existing_op else []
        existing_op.append(rhs_unwrapped)
        node["operand"] = existing_op
    elif layer_name == "XorExpression":
        existing = node.get("operator", [])
        if not isinstance(existing, list):
            existing = [existing] if existing else []
        existing.append(op_text)
        node["operator"] = existing
        existing_op = node.get("operand", [])
        if not isinstance(existing_op, list):
            existing_op = [existing_op] if existing_op else []
        existing_op.append(rhs_unwrapped)
        node["operand"] = existing_op
    elif layer_name == "ImpliesExpression":
        existing = node.get("operator", [])
        if not isinstance(existing, list):
            existing = [existing] if existing else []
        existing.append(op_text)
        node["operator"] = existing
        existing_op = node.get("operand", [])
        if not isinstance(existing_op, list):
            existing_op = [existing_op] if existing_op else []
        existing_op.append(rhs_unwrapped)
        node["operand"] = existing_op
    return lhs_chain


def _is_owned_chain(d):
    """True if d is a full OwnedExpression chain dict."""
    return isinstance(d, dict) and d.get("name") == "OwnedExpression"


def _walk_chain(root, path):
    """Walk a chain dict following a path of keys/indices. Returns the
    node at the end of the path, or None if the path doesn't exist."""
    node = root
    for step in path:
        if node is None:
            return None
        if isinstance(step, int):
            if step >= len(node):
                return None
            node = node[step]
        else:
            if not isinstance(node, dict):
                return None
            node = node.get(step)
    return node


def _rhs_top_op_layer(rhs_chain):
    """Find the highest (lowest binding power) layer in an rhs chain
    that has an operator populated. Returns the layer name or None.
    """
    if not _is_owned_chain(rhs_chain):
        return None
    paths = [
        ("ConditionalExpression", ["expression"]),
        ("NullCoalescingExpression", ["expression", "operand", 0]),
        ("ImpliesExpression", ["expression", "operand", 0, "implies"]),
        ("OrExpression", ["expression", "operand", 0, "implies", "or"]),
        ("XorExpression", ["expression", "operand", 0, "implies", "or", "xor"]),
        ("AndExpression", ["expression", "operand", 0, "implies", "or", "xor", "and"]),
        ("EqualityExpression", ["expression", "operand", 0, "implies", "or", "xor", "and", "equality"]),
        ("RelationalExpression", ["expression", "operand", 0, "implies", "or", "xor", "and", "equality", "classification", "relational"]),
        ("RangeExpression", ["expression", "operand", 0, "implies", "or", "xor", "and", "equality", "classification", "relational", "range"]),
        ("AdditiveExpression", ["expression", "operand", 0, "implies", "or", "xor", "and", "equality", "classification", "relational", "range", "additive"]),
        ("MultiplicativeExpression", ["expression", "operand", 0, "implies", "or", "xor", "and", "equality", "classification", "relational", "range", "additive", "multiplicitive"]),
    ]
    for layer, path in paths:
        node = _walk_chain(rhs_chain, path)
        if not isinstance(node, dict):
            continue
        # Each layer has a different operator-bearing field:
        # - ConditionalExpression: operator (list) + operand (list of NullCoalescing)
        # - NullCoalescingExpression: operator (list)
        # - ImpliesExpression: operator (list)
        # - OrExpression: operator (list)
        # - XorExpression: operator (list)
        # - AndExpression: operation (list)
        # - EqualityExpression: operation (list)
        # - RelationalExpression: operation (list)
        # - RangeExpression: operator (str) + operand (dict or None)
        # - AdditiveExpression: operation (list)
        # - MultiplicativeExpression: operation (list)
        op_field = node.get("operation")
        if op_field:
            return layer
        op_str = node.get("operator")
        if op_str and (isinstance(op_str, list) and op_str) or (isinstance(op_str, str) and op_str):
            return layer
    return None


def _embed_rhs_higher_ops(lhs_chain, rhs_chain, splicing_layer):
    """If the rhs chain has operators at a HIGHER layer (lower binding
    power) than ``splicing_layer``, embed those operators into the
    lhs chain so they aren't lost. This handles cases like
    ``a + b * c`` where the parse would otherwise hide one of the
    operators.
    """
    top = _rhs_top_op_layer(rhs_chain)
    if top is None:
        return
    top_rank = _PRECEDENCE_RANK.get(_LAYER_TO_OPERATORS.get(top, [None])[0], 0) if _LAYER_TO_OPERATORS.get(top) else 0
    splicing_rank = _PRECEDENCE_RANK.get(_LAYER_TO_OPERATORS.get(splicing_layer, [None])[0], 0) if _LAYER_TO_OPERATORS.get(splicing_layer) else 0
    if top_rank >= splicing_rank:
        return
    # Embed: copy the rhs's top-op layer's operator/operation data into
    # the lhs chain at the same layer.
    paths = {
        "ConditionalExpression": ["expression"],
        "NullCoalescingExpression": ["expression", "operand", 0],
        "ImpliesExpression": ["expression", "operand", 0, "implies"],
        "OrExpression": ["expression", "operand", 0, "implies", "or"],
        "XorExpression": ["expression", "operand", 0, "implies", "or", "xor"],
        "AndExpression": ["expression", "operand", 0, "implies", "or", "xor", "and"],
        "EqualityExpression": ["expression", "operand", 0, "implies", "or", "xor", "and", "equality"],
        "RelationalExpression": ["expression", "operand", 0, "implies", "or", "xor", "and", "equality", "classification", "relational"],
        "RangeExpression": ["expression", "operand", 0, "implies", "or", "xor", "and", "equality", "classification", "relational", "range"],
        "AdditiveExpression": ["expression", "operand", 0, "implies", "or", "xor", "and", "equality", "classification", "relational", "range", "additive"],
        "MultiplicativeExpression": ["expression", "operand", 0, "implies", "or", "xor", "and", "equality", "classification", "relational", "range", "additive", "multiplicitive"],
    }
    path = paths.get(top)
    if not path:
        return
    lhs_node = _walk_chain(lhs_chain, path)
    rhs_node = _walk_chain(rhs_chain, path)
    if not isinstance(lhs_node, dict) or not isinstance(rhs_node, dict):
        return
    # Copy operator-bearing fields only; don't overwrite sub-structure
    for k in ("operation", "operator", "operand"):
        if k in rhs_node:
            lhs_node[k] = rhs_node[k]


# Reverse map: layer name → one of its operators (for rank lookup)
_LAYER_TO_OPERATORS = {}
for _op, _layer in _OPERATOR_TO_LAYER.items():
    _LAYER_TO_OPERATORS.setdefault(_layer, []).append(_op)


def _unwrap_to_layer(rhs_chain, layer_name):
    """Walk an rhs OwnedExpression chain down to the sub-layer that
    matches the grammar class's operand expectation for ``layer_name``.
    E.g. for EqualityExpression the operand should be a
    ClassificationExpression dict; for AdditiveExpression it should
    be a MultiplicativeExpression dict.
    """
    if not _is_owned_chain(rhs_chain):
        return rhs_chain
    paths = {
        "EqualityExpression": ["expression", "operand", 0, "implies", "or", "xor", "and", "equality", "classification"],
        "RelationalExpression": ["expression", "operand", 0, "implies", "or", "xor", "and", "equality", "classification", "relational", "range"],
        "RangeExpression": ["expression", "operand", 0, "implies", "or", "xor", "and", "equality", "classification", "relational", "range", "additive"],
        "AdditiveExpression": ["expression", "operand", 0, "implies", "or", "xor", "and", "equality", "classification", "relational", "range", "additive", "multiplicitive"],
        "MultiplicativeExpression": ["expression", "operand", 0, "implies", "or", "xor", "and", "equality", "classification", "relational", "range", "additive", "multiplicitive", "exponential"],
        "ExponentiationExpression": ["expression", "operand", 0, "implies", "or", "xor", "and", "equality", "classification", "relational", "range", "additive", "multiplicitive", "exponential", "unary"],
    }
    path = paths.get(layer_name)
    if path is None:
        # For higher layers, return the chain at the layer BELOW the
        # current one (matching the grammar-class operand expectation).
        if layer_name in ("AndExpression",):
            path = ["expression", "operand", 0, "implies", "or", "xor", "and", "equality"]
        elif layer_name == "OrExpression":
            path = ["expression", "operand", 0, "implies", "or", "xor", "and"]
        elif layer_name == "XorExpression":
            path = ["expression", "operand", 0, "implies", "or"]
        elif layer_name == "ImpliesExpression":
            path = ["expression", "operand", 0]
            path = ["expression", "operand", 0, "implies", "or", "xor", "and", "equality", "classification", "relational", "range", "additive"]
    return _walk_chain(rhs_chain, path)


def _emit_structured_expression(oe_ctx):
    """Recursively emit a structured OwnedExpression dict for an ANTLR
    ownedExpression context, using precedence-climbing to recover the
    correct operator order.

    The vendored grammar uses left-associative same-precedence for all
    binary operators, so the ANTLR parse tree is NOT a correct precedence
    tree. We re-arrange operators by descending into the LHS sub-expression
    and checking if it has a lower-precedence operator at its top — if so,
    the LHS's operator is the actual top, and the current operator moves
    into the LHS's RHS.

    Returns a full OwnedExpression chain dict.
    """
    if oe_ctx is None:
        return None

    children = list(oe_ctx.getChildren()) if hasattr(oe_ctx, "getChildren") else []
    if not children:
        return None

    # Unary prefix form: first child is a terminal (op), rest is the operand
    if len(children) >= 2:
        first = children[0]
        if type(first).__name__ == "TerminalNodeImpl":
            text = first.getText().strip()
            if _is_unary_prefix_token(text):
                operand_chain = _emit_structured_expression(children[1])
                return _splice_unary(operand_chain, text)

    # Find the top-level operator in this OE's children
    op_idx, op_text = _find_split_index(children)
    if op_idx is None:
        # No binary operator — but check for field-access dot suffix
        # (a.b pattern: [OwnedExpr, DOT, QualifiedName])
        if len(children) == 3 and type(children[1]).__name__ == "TerminalNodeImpl" \
                and children[1].getText().strip() == "." \
                and type(children[2]).__name__ == "QualifiedNameContext":
            # Field access: emit as a single FeatureReferenceExpression
            # with the full text. The grammar class lacks a
            # FeatureChainExpression, so we fall back to text to
            # preserve round-trip.
            return _fallback_to_text(oe_ctx)
        # No binary operator — it's a base expression
        return _emit_base_expression(oe_ctx)

    # Logical operators (and/or/xor/implies/? ?) at the top level:
    # the grammar classes use list-based operand/operator fields which
    # don't fit the chain layout. Fall back to text preservation.
    if op_text in ("and", "or", "xor", "implies", "and_op"):
        return _fallback_to_text(oe_ctx)

    # Split LHS and RHS at the top-level op
    lhs_children = children[:op_idx]
    rhs_children = children[op_idx + 1:]
    if len(lhs_children) != 1 or len(rhs_children) != 1:
        return _fallback_to_text(oe_ctx)
    lhs_ctx = lhs_children[0]
    rhs_ctx = rhs_children[0]
    if type(lhs_ctx).__name__ != "OwnedExpressionContext" or type(rhs_ctx).__name__ != "OwnedExpressionContext":
        return _fallback_to_text(oe_ctx)

    # Recurse on the LHS first
    lhs_chain = _emit_structured_expression(lhs_ctx)
    if lhs_chain is None:
        return _fallback_to_text(oe_ctx)

    # Check if the LHS chain has a top operator with LOWER precedence
    # than the current op. If so, the LHS's top is the actual top, and
    # the current op moves into the LHS's RHS (as an additional sub-op).
    lhs_top_layer = _rhs_top_op_layer(lhs_chain)
    if lhs_top_layer is not None:
        lhs_top_rank = _layer_rank(lhs_top_layer)
        current_rank = _PRECEDENCE_RANK.get(op_text, 0)
        if lhs_top_rank < current_rank:
            # Re-arrange: the LHS chain becomes the new outer, and the
            # current op is added to the LHS's top op's RHS sub-dict.
            lhs_top_op = _get_top_op_text(lhs_chain)
            lhs_top_rhs = _get_top_op_rhs_chain(lhs_chain)
            if lhs_top_rhs is not None and isinstance(lhs_top_rhs, dict):
                # Find the layer for the current op
                current_layer = _OPERATOR_TO_LAYER.get(op_text)
                if current_layer is not None:
                    # Add the current op to the LHS's top op's RHS
                    _add_op_to_layer(lhs_top_rhs, current_layer, op_text, rhs_ctx)
                    # Also embed any higher-layer operators from the
                    # rhs_ctx into the lhs chain (e.g., `==` from `c==0`)
                    rhs_chain_for_embed = _emit_structured_expression(rhs_ctx)
                    if rhs_chain_for_embed is not None and _is_owned_chain(rhs_chain_for_embed):
                        # Find the top op layer in the rhs and embed it
                        rhs_top = _rhs_top_op_layer(rhs_chain_for_embed)
                        if rhs_top is not None and _layer_rank(rhs_top) < _layer_rank(current_layer):
                            _embed_layer_at_path(lhs_chain, rhs_chain_for_embed, rhs_top)
                    return lhs_chain
            # Fallback: try the old approach
            return _build_binary_chain(op_text, lhs_ctx, rhs_ctx)

    # Normal case: current op is the top
    return _build_binary_chain(op_text, lhs_ctx, rhs_ctx)


def _layer_rank(layer_name):
    """Return the precedence rank of a layer (using one of its operators)."""
    ops = _LAYER_TO_OPERATORS.get(layer_name, [])
    if not ops:
        return -1
    return _PRECEDENCE_RANK.get(ops[0], -1)


def _get_top_op_text(chain):
    """Return the operator text at the top op layer of a chain, or None."""
    top = _rhs_top_op_layer(chain)
    if top is None:
        return None
    path = _LAYER_PATHS.get(top)
    if not path:
        return None
    node = _walk_chain(chain, path)
    if not isinstance(node, dict):
        return None
    op_field = _LAYER_OP_FIELDS.get(top)
    if op_field == "operation":
        ops = node.get("operation", [])
        if ops:
            return ops[0].get("operator")
    elif op_field == "operator":
        op_val = node.get("operator")
        if isinstance(op_val, list) and op_val:
            return op_val[0]
        if isinstance(op_val, str) and op_val:
            return op_val
    return None


def _get_top_op_rhs_chain(chain):
    """Return the rhs chain at the top op layer of a chain, or None."""
    top = _rhs_top_op_layer(chain)
    if top is None:
        return None
    path = _LAYER_PATHS.get(top)
    if not path:
        return None
    node = _walk_chain(chain, path)
    if not isinstance(node, dict):
        return None
    op_field = _LAYER_OP_FIELDS.get(top)
    if op_field == "operation":
        ops = node.get("operation", [])
        if ops:
            return ops[0].get("operand")
    elif op_field == "operator":
        op_val = node.get("operand")
        if isinstance(op_val, list) and op_val:
            return op_val[0]
        if isinstance(op_val, dict):
            return op_val
    return None


def _add_op_to_layer(sub_dict, layer_name, op_text, rhs_ctx):
    """Add the operator ``op_text`` at the layer ``layer_name`` inside
    ``sub_dict``. The rhs_ctx is an ANTLR context that will be emitted
    as a chain to serve as the operator's rhs operand.

    This is used when re-arranging operators: the current op is added
    to an existing sub-dict that already contains the LHS data.
    """
    # The sub_dict is a layer dict (e.g., MultiplicativeExpression for
    # an additive's operand). We need to add the current op at the
    # matching layer inside it. For most cases, the current op's layer
    # IS the sub_dict's layer, so we just set the operation field.
    sub_layer = sub_dict.get("name", "")
    if sub_layer == layer_name:
        # The sub_dict IS the layer we want. Add the op.
        rhs_chain = _emit_structured_expression(rhs_ctx)
        if not _is_owned_chain(rhs_chain):
            rhs_chain = _wrap_expression_layers(rhs_chain)
        rhs_unwrapped = _unwrap_to_layer(rhs_chain, layer_name)
        op_field = _LAYER_OP_FIELDS.get(layer_name, "operation")
        if op_field == "operation":
            existing = sub_dict.get("operation", [])
            new_op = _make_op_dict(layer_name, op_text, rhs_unwrapped)
            sub_dict["operation"] = existing + [new_op]
        elif op_field == "operator":
            existing = sub_dict.get("operator", [])
            if not isinstance(existing, list):
                existing = [existing] if existing else []
            existing.append(op_text)
            sub_dict["operator"] = existing
            existing_op = sub_dict.get("operand", [])
            if not isinstance(existing_op, list):
                existing_op = [existing_op] if existing_op else []
            existing_op.append(rhs_unwrapped)
            sub_dict["operand"] = existing_op
        return
    # Otherwise, recurse into the sub-dict's child layer
    # (e.g., for MultiplicativeExpression, the child layer is exponential)
    child_paths = {
        "MultiplicativeExpression": ["exponential"],
        "AdditiveExpression": ["multiplicitive"],
        "ExponentiationExpression": ["unary"],
        "UnaryExpression": ["extent"],
        "ExtentExpression": ["primary"],
        "PrimaryExpression": ["base"],
    }
    path = child_paths.get(sub_layer, [])
    if not path:
        return
    child = sub_dict
    for step in path:
        if isinstance(child, dict):
            child = child.get(step)
        else:
            return
    if isinstance(child, dict):
        _add_op_to_layer(child, layer_name, op_text, rhs_ctx)


def _make_op_dict(layer_name, op_text, operand_dict):
    """Build an operand dict for a given layer."""
    if layer_name in ("EqualityExpression",):
        return {"name": "EqualityOperand", "operator": op_text, "operand": operand_dict}
    if layer_name in ("RelationalExpression",):
        return {"name": "RelationalOperand", "operator": op_text, "operand": operand_dict}
    if layer_name in ("AdditiveExpression",):
        return {"name": "AdditiveOperand", "operator": op_text, "operand": operand_dict}
    if layer_name in ("MultiplicativeExpression",):
        return {"name": "MultiplicativeOperand", "operator": op_text, "operand": operand_dict}
    if layer_name in ("AndExpression",):
        return {"name": "AndOperand", "operator": op_text, "operand": operand_dict}
    if layer_name in ("RangeExpression", "ExponentiationExpression", "OrExpression", "XorExpression", "ImpliesExpression"):
        return {"name": f"{layer_name.replace('Expression', '')}Operand", "operator": op_text, "operand": operand_dict}
    return {"name": "Operand", "operator": op_text, "operand": operand_dict}


def _embed_layer_at_path(lhs_chain, rhs_chain, layer_name):
    """Copy the operator-bearing fields from ``rhs_chain`` at
    ``layer_name`` into ``lhs_chain`` at the same layer."""
    lhs_node = _walk_chain(lhs_chain, _LAYER_PATHS.get(layer_name, []))
    rhs_node = _walk_chain(rhs_chain, _LAYER_PATHS.get(layer_name, []))
    if not isinstance(lhs_node, dict) or not isinstance(rhs_node, dict):
        return
    op_field = _LAYER_OP_FIELDS.get(layer_name, "operation")
    if op_field in rhs_node:
        lhs_node[op_field] = rhs_node[op_field]


_LAYER_PATHS = {
    "ConditionalExpression": ["expression"],
    "NullCoalescingExpression": ["expression", "operand", 0],
    "ImpliesExpression": ["expression", "operand", 0, "implies"],
    "OrExpression": ["expression", "operand", 0, "implies", "or"],
    "XorExpression": ["expression", "operand", 0, "implies", "or", "xor"],
    "AndExpression": ["expression", "operand", 0, "implies", "or", "xor", "and"],
    "EqualityExpression": ["expression", "operand", 0, "implies", "or", "xor", "and", "equality"],
    "RelationalExpression": ["expression", "operand", 0, "implies", "or", "xor", "and", "equality", "classification", "relational"],
    "RangeExpression": ["expression", "operand", 0, "implies", "or", "xor", "and", "equality", "classification", "relational", "range"],
    "AdditiveExpression": ["expression", "operand", 0, "implies", "or", "xor", "and", "equality", "classification", "relational", "range", "additive"],
    "MultiplicativeExpression": ["expression", "operand", 0, "implies", "or", "xor", "and", "equality", "classification", "relational", "range", "additive", "multiplicitive"],
}


def _fallback_to_text(oe_ctx):
    """Fallback: preserve the original text as a single
    FeatureReferenceMember (the v0.51.0 lossy behavior)."""
    text = oe_ctx.getText() if hasattr(oe_ctx, "getText") else ""
    return _wrap_expression_layers(_make_feature_reference_primary(text))


def _emit_unary_chain(operand_chain, op_text):
    """Populate the UnaryExpression layer of ``operand_chain`` with
    the unary operator ``op_text`` and return the chain."""
    if not _is_owned_chain(operand_chain):
        operand_chain = _wrap_expression_layers(operand_chain)
    unary_path = ["expression", "operand", 0, "implies", "or", "xor", "and", "equality", "classification", "relational", "range", "additive", "multiplicitive", "exponential", "unary"]
    node = _walk_chain(operand_chain, unary_path)
    if isinstance(node, dict):
        node["operator"] = op_text
    return operand_chain


def _splice_unary(operand_chain, op_text):
    """Build a chain with the unary operator applied. The unary operator
    is at the UnaryExpression layer in the chain."""
    return _emit_unary_chain(operand_chain, op_text)


def _emit_base_expression(oe_ctx):
    """Emit a base expression (no binary operators). This handles
    literal values, feature references, invocations, and the
    field-access chains (a.b.c)."""
    # Try literal first
    if hasattr(oe_ctx, "baseExpression") and oe_ctx.baseExpression():
        be_ctx = oe_ctx.baseExpression()
        text = be_ctx.getText().strip() if hasattr(be_ctx, "getText") else ""
        # Literal?
        if hasattr(be_ctx, "literalExpression") and be_ctx.literalExpression():
            lit_ctx = be_ctx.literalExpression()
            lit_text = lit_ctx.getText().strip() if hasattr(lit_ctx, "getText") else ""
            try:
                value = int(lit_text)
                primary = _make_literal_integer_primary(value)
                return _wrap_expression_layers(primary)
            except ValueError:
                pass
            try:
                value = float(lit_text)
                primary = _make_literal_real_primary(value)
                return _wrap_expression_layers(primary)
            except ValueError:
                pass
            if lit_text.startswith('"') and lit_text.endswith('"'):
                primary = _make_literal_string_primary(lit_text)
                return _wrap_expression_layers(primary)
        # Invocation: base has qualifiedName AND argumentList
        has_args = hasattr(be_ctx, "argumentList") and be_ctx.argumentList()
        if has_args and hasattr(be_ctx, "qualifiedName") and be_ctx.qualifiedName():
            qn_ctx = be_ctx.qualifiedName()
            names = _extract_qualified_name_parts(qn_ctx)
            primary = _build_invocation_primary(names, be_ctx.argumentList())
            return _wrap_expression_layers(primary)
        # Feature reference (possibly with field access)
        if hasattr(be_ctx, "qualifiedName") and be_ctx.qualifiedName():
            # Extract qualified name parts
            qn_ctx = be_ctx.qualifiedName()
            names = _extract_qualified_name_parts(qn_ctx)
            primary = _make_feature_reference_chain(names)
            return _wrap_expression_layers(primary)
    return _fallback_to_text(oe_ctx)


def _build_invocation_primary(names, arg_list_ctx):
    """Build a PrimaryExpression containing an InvocationExpression
    (function call like Power(args))."""
    return {
        "name": "PrimaryExpression",
        "operator": [],
        "operand": [],
        "base": {
            "name": "BaseExpression",
            "ownedRelationship": {
                "name": "InvocationExpression",
                "ownedRelationship": {
                    "name": "OwnedFeatureTyping",
                    "type": {
                        "name": "FeatureType",
                        "type": {
                            "name": "QualifiedName",
                            "names": names,
                        },
                        "ownedRelatedElement": [],
                    },
                },
                "arg_list": _build_arg_list_dict(arg_list_ctx),
            }
        },
        "ownedRelationship1": [],
        "ownedRelationship2": []
    }


def _build_arg_list_dict(arg_list_ctx):
    """Build an ArgumentList dict from an ANTLR argumentList context."""
    if arg_list_ctx is None:
        return {"name": "ArgumentList", "pos_list": None, "named_list": None}
    # Walk children to find the PositionalArgumentList
    pal = None
    for c in (arg_list_ctx.getChildren() if hasattr(arg_list_ctx, "getChildren") else []):
        if type(c).__name__ == "PositionalArgumentListContext":
            pal = c
            break
    if pal is None:
        return {"name": "ArgumentList", "pos_list": None, "named_list": None}
    args = []
    for am in (pal.getChildren() if hasattr(pal, "getChildren") else []):
        if type(am).__name__ == "OwnedExpressionContext":
            arg_text = am.getText() if hasattr(am, "getText") else ""
            primary = {
                "name": "PrimaryExpression",
                "operator": [],
                "operand": [],
                "base": {
                    "name": "BaseExpression",
                    "ownedRelationship": {
                        "name": "FeatureReferenceExpression",
                        "ownedRelationship": [
                            {
                                "name": "FeatureReferenceMember",
                                "memberElement": {
                                    "name": "QualifiedName",
                                    "names": [arg_text],
                                }
                            }
                        ]
                    }
                },
                "ownedRelationship1": [],
                "ownedRelationship2": []
            }
            chain = _wrap_expression_layers(primary)
            args.append({
                "name": "ArgumentMember",
                "ownedRelatedElement": {
                    "name": "Argument",
                    "ownedRelationship": {
                        "name": "ArgumentValue",
                        "ownedRelatedElement": chain,
                    }
                }
            })
    return {
        "name": "ArgumentList",
        "pos_list": {
            "name": "PositionalArgumentList",
            "ownedRelationship": args,
        },
        "named_list": None,
    }


def _extract_qualified_name_parts(qn_ctx):
    """Extract the name parts from a qualifiedName ANTLR context."""
    parts = []
    if qn_ctx is None:
        return parts
    for c in (qn_ctx.getChildren() if hasattr(qn_ctx, "getChildren") else []):
        tn = type(c).__name__
        if tn == "NameContext":
            text = c.getText().strip() if hasattr(c, "getText") else ""
            if text:
                parts.append(text)
        elif tn == "TerminalNodeImpl":
            text = c.getText().strip()
            if text and text not in ("::",):
                parts.append(text)
    return parts


def _make_feature_reference_chain(names):
    """Build a PrimaryExpression containing a FeatureReferenceExpression
    with the given qualified name parts. If multiple parts, they
    represent a qualified name (a::b::c) or a feature chain (a.b.c).
    The grammar class dumps qualified names with '::' separator and
    the parts list is preserved.
    """
    if not names:
        return _make_feature_reference_primary("")
    if len(names) == 1:
        return _make_feature_reference_primary(names[0])
    # Multiple parts: use a QualifiedName with the parts list.
    # The QualifiedName.dump() will join with '::' which matches
    # the original qualified-name syntax.
    return {
        "name": "PrimaryExpression",
        "operator": [],
        "operand": [],
        "base": {
            "name": "BaseExpression",
            "ownedRelationship": {
                "name": "FeatureReferenceExpression",
                "ownedRelationship": [
                    {
                        "name": "FeatureReferenceMember",
                        "memberElement": {
                            "name": "QualifiedName",
                            "names": names,
                        }
                    }
                ]
            }
        },
        "ownedRelationship1": [],
        "ownedRelationship2": []
    }


# Mapping for chain operator-bearing fields (used by _rhs_top_op_layer)
_LAYER_OP_FIELDS = {
    "ConditionalExpression": "operator",
    "NullCoalescingExpression": "operator",
    "ImpliesExpression": "operator",
    "OrExpression": "operator",
    "XorExpression": "operator",
    "AndExpression": "operation",
    "EqualityExpression": "operation",
    "RelationalExpression": "operation",
    "RangeExpression": "operator",
    "AdditiveExpression": "operation",
    "MultiplicativeExpression": "operation",
}


def _wrap_expression_layers(primary_expression):
    """Wrap a primary expression in all the intermediate expression layers.
    
    The SysML v2 grammar has deep nesting for expressions. This helper builds
    the full chain: OwnedExpression -> ConditionalExpression -> ... -> PrimaryExpression.
    """
    return {
        "name": "OwnedExpression",
        "expression": {
            "name": "ConditionalExpression",
            "operator": [],
            "operand": [
                {
                    "name": "NullCoalescingExpression",
                    "operator": [],
                    "operand": [],
                    "implies": {
                        "name": "ImpliesExpression",
                        "operator": [],
                        "operand": [],
                        "or": {
                            "name": "OrExpression",
                            "operator": [],
                            "operand": [],
                            "xor": {
                                "name": "XorExpression",
                                "operator": [],
                                "operand": [],
                                "and": {
                                    "name": "AndExpression",
                                    "operation": [],
                                    "equality": {
                                        "name": "EqualityExpression",
                                        "operation": [],
                                        "classification": {
                                            "name": "ClassificationExpression",
                                            "operator": None,
                                            "operand": [],
                                            "relational": {
                                                "name": "RelationalExpression",
                                                "operation": [],
                                                "range": {
                                                    "name": "RangeExpression",
                                                    "operand": None,
                                                    "additive": {
                                                        "name": "AdditiveExpression",
                                                        "multiplicitive": {
                                                            "name": "MultiplicativeExpression",
                                                            "operation": [],
                                                            "exponential": {
                                                                "name": "ExponentiationExpression",
                                                                "operator": [],
                                                                "operand": [],
                                                                "unary": {
                                                                    "name": "UnaryExpression",
                                                                    "operator": None,
                                                                    "operand": [],
                                                                    "extent": {
                                                                        "name": "ExtentExpression",
                                                                        "operator": "",
                                                                        "operand": [],
                                                                        "primary": primary_expression
                                                                    }
                                                                }
                                                            }
                                                        },
                                                        "operation": []
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            ]
        }
    }


def _make_literal_integer_primary(value):
    """Build a PrimaryExpression containing a LiteralInteger."""
    return {
        "name": "PrimaryExpression",
        "operator": [],
        "operand": [],
        "base": {
            "name": "BaseExpression",
            "ownedRelationship": {
                "name": "LiteralInteger",
                "value": str(value)
            }
        },
        "ownedRelationship1": [],
        "ownedRelationship2": []
    }


def _make_literal_real_primary(value):
    """Build a PrimaryExpression containing a LiteralReal."""
    return {
        "name": "PrimaryExpression",
        "operator": [],
        "operand": [],
        "base": {
            "name": "BaseExpression",
            "ownedRelationship": {
                "name": "LiteralReal",
                "value": str(value)
            }
        },
        "ownedRelationship1": [],
        "ownedRelationship2": []
    }


def _make_literal_string_primary(value):
    """Build a PrimaryExpression containing a LiteralString."""
    return {
        "name": "PrimaryExpression",
        "operator": [],
        "operand": [],
        "base": {
            "name": "BaseExpression",
            "ownedRelationship": {
                "name": "LiteralString",
                "value": value
            }
        },
        "ownedRelationship1": [],
        "ownedRelationship2": []
    }


def _make_feature_reference_primary(qualified_name):
    """Build a PrimaryExpression containing a FeatureReferenceExpression (for unit names, variable refs)."""
    return {
        "name": "PrimaryExpression",
        "operator": [],
        "operand": [],
        "base": {
            "name": "BaseExpression",
            "ownedRelationship": {
                "name": "FeatureReferenceExpression",
                "ownedRelationship": [
                    {
                        "name": "FeatureReferenceMember",
                        "memberElement": {
                            "name": "QualifiedName",
                            "names": [qualified_name]
                        }
                    }
                ]
            }
        },
        "ownedRelationship1": [],
        "ownedRelationship2": []
    }


def _make_primary_with_unit(literal_primary, unit_name):
    """Build a PrimaryExpression with a unit operator (e.g., "100 [kilogram]").
    
    This modifies the literal's primary to include the unit as an operator/operand.
    """
    # The unit is wrapped in SequenceExpression -> OwnedExpression -> ... -> PrimaryExpression
    unit_primary = _make_feature_reference_primary(unit_name)
    unit_expr = _wrap_expression_layers(unit_primary)
    
    sequence_expr = {
        "name": "SequenceExpression",
        "operation": [],
        "ownedRelationship": unit_expr
    }
    
    # Return a new primary that has the literal as base and unit as operand
    literal_primary_with_unit = dict(literal_primary)
    literal_primary_with_unit["operator"] = ["["]
    literal_primary_with_unit["operand"] = [sequence_expr]
    
    return literal_primary_with_unit


def _extract_number_value(text):
    """Try to parse text as an integer or float.
    
    Returns (value, is_integer) tuple. If text isn't numeric, returns (None, False).
    """
    if text is None:
        return None, False
    text = text.strip()
    # Try integer first
    try:
        return int(text), True
    except ValueError:
        pass
    try:
        return float(text), False
    except ValueError:
        pass
    return None, False


def _visit_owned_expression(oe_ctx):
    """Visit an ownedExpression context and return the OwnedExpression dict.

    Phase 1: for complex expressions, use precedence-climbing to recover
    the correct operator structure (per docs/v0.46.0_expression_capture_plan.md).
    This replaces the v0.51.0 lossy collapse-to-text behavior so a future
    name resolver can walk identifiers individually.
    """
    if oe_ctx is None:
        return None

    text = oe_ctx.getText().strip() if hasattr(oe_ctx, 'getText') else ''

    if not text:
        return None

    # Check for unit expression pattern: "value[unit]"
    if '[' in text and text.endswith(']') and not _contains_binary_op_outside_unit(text):
        # Split at '['
        idx = text.index('[')
        value_part = text[:idx].strip()
        unit_part = text[idx+1:-1].strip()

        # Try to get literal primary for value
        value, is_int = _extract_number_value(value_part)
        if value is not None:
            if is_int:
                literal_primary = _make_literal_integer_primary(value)
            else:
                literal_primary = _make_literal_real_primary(value)
            primary_with_unit = _make_primary_with_unit(literal_primary, unit_part)
            return _wrap_expression_layers(primary_with_unit)

    # Phase 1 path: try structured emit via precedence-climbing
    try:
        chain = _emit_structured_expression(oe_ctx)
        if chain is not None:
            return chain
    except Exception:
        # Defensive: if structured emit fails for any reason, fall back
        # to the v0.51.0 lossy behavior (preserves round-trip).
        pass

    # Simple literal (no operator, no qualified name with `.`)
    if not _contains_binary_op(text) and not _contains_field_access(text):
        value, is_int = _extract_number_value(text)
        if value is not None:
            if is_int:
                primary = _make_literal_integer_primary(value)
            else:
                primary = _make_literal_real_primary(value)
            return _wrap_expression_layers(primary)

        # String literal
        if text.startswith('"') and text.endswith('"'):
            primary = _make_literal_string_primary(text)
            return _wrap_expression_layers(primary)

    # Complex expression or feature reference - preserve raw text
    # Wrap as a single FeatureReferenceMember with the original text
    primary = _make_feature_reference_primary(text)
    return _wrap_expression_layers(primary)


def _contains_binary_op(text):
    """True if text contains any of the known binary operator characters
    (outside of bracket-delimited unit expressions)."""
    for op in _PRECEDENCE_RANK:
        if op in ("implies", "or", "xor", "and", "istype", "hastype"):
            continue
        if op in text:
            return True
    return False


def _contains_binary_op_outside_unit(text):
    """True if text contains binary operators OUTSIDE of any [unit] brackets."""
    # Strip all [unit] expressions
    import re
    stripped = re.sub(r'\[[^\]]*\]', '', text)
    return _contains_binary_op(stripped)


def _contains_field_access(text):
    """True if text contains field-access dots (a.b)."""
    # Simple heuristic: look for `.` not preceded by a digit
    import re
    return bool(re.search(r'\.\w', text))


def _visit_value_part(vp_ctx):
    """Visit a valuePart context and return the ValuePart dict.
    
    valuePart : featureValue ;
    featureValue : (EQ | COLON_EQ | DEFAULT ( EQ | COLON_EQ)?) ownedExpression ;
    """
    if vp_ctx is None:
        return None
    
    if not hasattr(vp_ctx, 'featureValue') or not vp_ctx.featureValue():
        return None
    
    fv = vp_ctx.featureValue()
    
    # Determine the equality flags based on the tokens
    is_default = False
    is_equal = False
    is_initial = False
    
    # Check if DEFAULT token is present
    if hasattr(fv, 'DEFAULT') and fv.DEFAULT():
        is_default = True
    
    # Check if COLON_EQ token is present (initial assignment)
    if hasattr(fv, 'COLON_EQ') and fv.COLON_EQ():
        is_initial = True
    
    # Check EQ token (though default is usually that it's equal if not default/initial)
    if hasattr(fv, 'EQ') and fv.EQ():
        is_equal = True
    
    # If neither default nor initial, reset is_equal to False to match the original pint-based structure
    # (which sets isEqual: false when value is just "= 100")
    if not is_default and not is_initial:
        is_equal = False
    
    # Get the ownedExpression
    oe = None
    if hasattr(fv, 'ownedExpression') and fv.ownedExpression():
        oe = fv.ownedExpression()
    
    owned_expr_dict = _visit_owned_expression(oe)
    if owned_expr_dict is None:
        return None
    
    return {
        "name": "ValuePart",
        "ownedRelationship": [
            {
                "name": "FeatureValue",
                "ownedRelatedElement": owned_expr_dict,
                "isEqual": is_equal,
                "isInitial": is_initial,
                "isDefault": is_default
            }
        ]
    }


def _get_usage_value_part(ctx):
    """Extract the valuePart from a usage context.
    
    Navigates usage().usageCompletion().valuePart().
    """
    if ctx is None:
        return None
    
    usage = None
    if hasattr(ctx, 'usage') and ctx.usage():
        usage = ctx.usage()
    
    if usage and hasattr(usage, 'usageCompletion') and usage.usageCompletion():
        uc = usage.usageCompletion()
        if hasattr(uc, 'valuePart') and uc.valuePart():
            vp_ctx = uc.valuePart()
            return _visit_value_part(vp_ctx)
    
    return None


def _make_default_reference_usage_dict(ctx):
    """Create a DefaultReferenceUsage dictionary (for directed features like 'in Fuel;').
    
    The grammar rule is: defaultReferenceUsage : refPrefix usage ;
    refPrefix can contain featureDirection (in, out, inout).
    
    Note: For enumerations like `simple { :>> code = "test"; }`, the value is
    in the usage body, not in a valuepart. We need to extract it from the body.
    """
    # Extract direction from refPrefix
    direction_in = ""
    direction_out = ""
    direction_inout = ""
    is_abstract = False
    is_variation = False
    is_readonly = False
    is_derived = False
    is_end = False
    
    if hasattr(ctx, 'refPrefix') and ctx.refPrefix():
        rp = ctx.refPrefix()
        if hasattr(rp, 'featureDirection') and rp.featureDirection():
            fd = rp.featureDirection()
            direction_text = fd.getText()
            if direction_text == 'in':
                direction_in = "in "
            elif direction_text == 'out':
                direction_out = "out"
            elif direction_text == 'inout':
                direction_inout = "inout"
    
    # Extract name from usage -> usageDeclaration -> identification
    name = None
    shortname = None
    if hasattr(ctx, 'usage') and ctx.usage():
        usage = ctx.usage()
        if hasattr(usage, 'usageDeclaration') and usage.usageDeclaration():
            ud = usage.usageDeclaration()
            if hasattr(ud, 'identification') and ud.identification():
                ident = ud.identification()
                if hasattr(ident, 'name'):
                    name_list = ident.name()
                    if name_list and isinstance(name_list, list):
                        if len(name_list) == 2:
                            shortname = name_list[0].getText()
                            name = name_list[1].getText()
                        elif len(name_list) == 1:
                            name_text = name_list[0].getText()
                            has_lt = hasattr(ident, 'LT') and ident.LT() is not None
                            if has_lt:
                                shortname = name_text
                            else:
                                name = name_text
    
    # Build specialization from usage declaration (handles :, :>>, etc.)
    specialization = _build_full_specialization_from_ctx(ctx)
    
    # Extract value part from usage completion (e.g., ="test" in :>> code = "test")
    valuepart = None
    if hasattr(ctx, 'usage') and ctx.usage():
        valuepart = _get_usage_value_part(ctx)
    
    # Extract body from usage completion
    # Note: For enumerations, the value is in the body (not in valuepart)
    body_items = []
    if hasattr(ctx, 'usage') and ctx.usage():
        usage = ctx.usage()
        if hasattr(usage, 'usageCompletion') and usage.usageCompletion():
            uc = usage.usageCompletion()
            if hasattr(uc, 'usageBody') and uc.usageBody():
                ub = uc.usageBody()
                if hasattr(ub, 'definitionBody') and ub.definitionBody():
                    db = ub.definitionBody()
                    body_items = _visit_definition_body_dict(db)
    
    return {
        "name": "NonOccurrenceUsageElement",
        "ownedRelatedElement": {
            "name": "DefaultReferenceUsage",
            "prefix": {
                "name": "RefPrefix",
                "isAbstract": is_abstract,
                "isVariation": is_variation,
                "isReadOnly": is_readonly,
                "isDerived": is_derived,
                "isEnd": is_end,
                "direction": {
                    "name": "FeatureDirection",
                    "in": direction_in,
                    "out": direction_out,
                    "inout": direction_inout
                }
            },
            "valuepart": valuepart,
            "declaration": {
                "name": "UsageDeclaration",
                "declaration": {
                    "name": "FeatureDeclaration",
                    "identification": {
                        "name": "Identification",
                        "declaredShortName": shortname,
                        "declaredName": name
                    },
                    "specialization": specialization
                }
            },
            "body": {
                "name": "UsageBody",
                "body": {
                    "name": "DefinitionBody",
                    "ownedRelatedElement": body_items
                }
            }
        }
    }


def _visit_nested_definition_element(def_elem):
    """Visit a nested definition element for body items."""
    if def_elem is None:
        return None
    
    # Handle various definition types
    if hasattr(def_elem, 'itemDefinition') and def_elem.itemDefinition():
        return _make_item_definition_dict(def_elem.itemDefinition(), None)
    elif hasattr(def_elem, 'partDefinition') and def_elem.partDefinition():
        return _make_part_definition_dict(def_elem.partDefinition(), None)
    elif hasattr(def_elem, 'attributeDefinition') and def_elem.attributeDefinition():
        return _make_attribute_definition_dict(def_elem.attributeDefinition(), None)
    elif hasattr(def_elem, 'portDefinition') and def_elem.portDefinition():
        return _make_port_definition_dict(def_elem.portDefinition(), None)
    elif hasattr(def_elem, 'interfaceDefinition') and def_elem.interfaceDefinition():
        return _make_interface_definition_dict(def_elem.interfaceDefinition(), None)
    elif hasattr(def_elem, 'annotatingElement') and def_elem.annotatingElement():
        ann_ctx = def_elem.annotatingElement()
        ann_dict = _visit_annotating_element_dict(ann_ctx)
        if ann_dict is None:
            return None
        return {
            "name": "PackageMember",
            "prefix": None,
            "ownedRelatedElement": {
                "name": "DefinitionElement",
                "ownedRelatedElement": ann_dict
            }
        }
    
    return None


def _make_nested_usage_element(usage_type, name, shortname, prefix, body_items=None, specialization=None, valuepart=None):
    """Build a nested usage element (not wrapped in PackageMember).
    
    Parameters
    ----------
    body_items : list or None
        Nested body items
    specialization : dict or None
        Pre-built FeatureSpecializationPart dict, or None.
    valuepart : dict or None
        Pre-built valuepart dict, or None.
    """
    if body_items is None:
        body_items = []
    
    return {
        "name": "UsageElement",
        "ownedRelatedElement": {
            "name": "OccurrenceUsageElement",
            "ownedRelatedElement": {
                "name": "StructureUsageElement",
                "ownedRelatedElement": {
                    "name": usage_type,
                    "prefix": prefix,
                    "usage": {
                        "name": "Usage",
                        "declaration": {
                            "name": "UsageDeclaration",
                            "declaration": {
                                "name": "FeatureDeclaration",
                                "identification": {
                                    "name": "Identification",
                                    "declaredShortName": shortname,
                                    "declaredName": name
                                },
                                "specialization": specialization
                            }
                        },
                        "completion": {
                            "name": "UsageCompletion",
                            "valuepart": valuepart,
                            "body": {
                                "name": "UsageBody",
                                "body": {
                                    "name": "DefinitionBody",
                                    "ownedRelatedElement": body_items
                                }
                            }
                        }
                    }
                }
            }
        }
    }


def _visit_nested_definition(def_elem_ctx):
    """Visit a nested definition within a body."""
    if hasattr(def_elem_ctx, 'partDefinition') and def_elem_ctx.partDefinition():
        ctx = def_elem_ctx.partDefinition()
        return _make_part_definition_dict(ctx)
    elif hasattr(def_elem_ctx, 'attributeDefinition') and def_elem_ctx.attributeDefinition():
        ctx = def_elem_ctx.attributeDefinition()
        return _make_attribute_definition_dict(ctx)
    elif hasattr(def_elem_ctx, 'portDefinition') and def_elem_ctx.portDefinition():
        ctx = def_elem_ctx.portDefinition()
        return _make_port_definition_dict(ctx)
    # Add more types as needed
    
    return None


def _visit_nested_usage(usage_elem_ctx):
    """Visit a nested usage within a body."""
    # Check for occurrence usage (part, item, port)
    if hasattr(usage_elem_ctx, 'occurrenceUsageElement') and usage_elem_ctx.occurrenceUsageElement():
        occ_elem = usage_elem_ctx.occurrenceUsageElement()
        
        # Check structure usage elements
        if hasattr(occ_elem, 'structureUsageElement') and occ_elem.structureUsageElement():
            struct_elem = occ_elem.structureUsageElement()
            
            if hasattr(struct_elem, 'partUsage') and struct_elem.partUsage():
                ctx = struct_elem.partUsage()
                name, shortname = _get_usage_identification(ctx)
                body_items = _get_usage_body_items(ctx)
                occ_prefix = _get_occurrence_usage_prefix(ctx)
                specialization = _build_full_specialization_from_ctx(ctx)
                valuepart = _get_usage_value_part(ctx)
                return _make_nested_usage_element("PartUsage", name, shortname, occ_prefix, body_items, specialization, valuepart)
            elif hasattr(struct_elem, 'itemUsage') and struct_elem.itemUsage():
                ctx = struct_elem.itemUsage()
                name, shortname = _get_usage_identification(ctx)
                body_items = _get_usage_body_items(ctx)
                occ_prefix = _get_occurrence_usage_prefix(ctx)
                specialization = _build_full_specialization_from_ctx(ctx)
                valuepart = _get_usage_value_part(ctx)
                return _make_nested_usage_element("ItemUsage", name, shortname, occ_prefix, body_items, specialization, valuepart)
            elif hasattr(struct_elem, 'portUsage') and struct_elem.portUsage():
                ctx = struct_elem.portUsage()
                name, shortname = _get_usage_identification(ctx)
                body_items = _get_usage_body_items(ctx)
                occ_prefix = _get_occurrence_usage_prefix(ctx)
                specialization = _build_full_specialization_from_ctx(ctx)
                valuepart = _get_usage_value_part(ctx)
                return _make_nested_usage_element("PortUsage", name, shortname, occ_prefix, body_items, specialization, valuepart)
            elif hasattr(struct_elem, 'portionUsage') and struct_elem.portionUsage():
                ctx = struct_elem.portionUsage()
                name, shortname = _get_usage_identification(ctx)
                body_items = _get_usage_body_items(ctx)
                occ_prefix = _make_portion_usage_prefix(ctx)
                specialization = _build_full_specialization_from_ctx(ctx)
                valuepart = _get_usage_value_part(ctx)
                return _make_nested_usage_element("PortionUsage", name, shortname, occ_prefix, body_items, specialization, valuepart)
            elif hasattr(struct_elem, 'individualUsage') and struct_elem.individualUsage():
                ctx = struct_elem.individualUsage()
                name, shortname = _get_usage_identification(ctx)
                body_items = _get_usage_body_items(ctx)
                occ_prefix = _make_portion_usage_prefix(ctx)
                specialization = _build_full_specialization_from_ctx(ctx)
                valuepart = _get_usage_value_part(ctx)
                return _make_nested_usage_element("PortionUsage", name, shortname, occ_prefix, body_items, specialization, valuepart)
        
        # Check behavior usage elements (action)
        if hasattr(occ_elem, 'behaviorUsageElement') and occ_elem.behaviorUsageElement():
            behav_elem = occ_elem.behaviorUsageElement()
            
            if hasattr(behav_elem, 'actionUsage') and behav_elem.actionUsage():
                ctx = behav_elem.actionUsage()
                name = None
                if ctx.actionUsageDeclaration():
                    aud = ctx.actionUsageDeclaration()
                    if hasattr(aud, 'usageDeclaration') and aud.usageDeclaration():
                        ud = aud.usageDeclaration()
                        if hasattr(ud, 'getText'):
                            text = ud.getText().strip()
                            if text and text != 'ACTION':
                                name = text
                return {
                    "name": "UsageElement",
                    "ownedRelatedElement": {
                        "name": "OccurrenceUsageElement",
                        "ownedRelatedElement": {
                            "name": "BehaviorUsageElement",
                            "ownedRelationship": {
                                "name": "ActionUsage",
                                "prefix": None,
                                "declaration": {
                                    "name": "ActionUsageDeclaration",
                                    "declaration": {
                                        "name": "UsageDeclaration",
                                        "declaration": {
                                            "name": "FeatureDeclaration",
                                            "identification": {
                                                "name": "Identification",
                                                "declaredShortName": None,
                                                "declaredName": name
                                            },
                                            "specialization": None
                                        }
                                    },
                                    "valuepart": None
                                },
                                "body": {
                                    "name": "ActionBody",
                                    "items": []
                                }
                            }
                        }
                    }
                }
            
            if hasattr(behav_elem, 'assertConstraintUsage') and behav_elem.assertConstraintUsage():
                ctx = behav_elem.assertConstraintUsage()
                result = _make_assert_constraint_usage_dict(ctx, None)
                if result:
                    return {
                        "name": "UsageElement",
                        "ownedRelatedElement": {
                            "name": "OccurrenceUsageElement",
                            "ownedRelatedElement": {
                                "name": "BehaviorUsageElement",
                                "ownedRelationship": result
                            }
                        }
                    }
                return None
            
            if hasattr(behav_elem, 'calculationUsage') and behav_elem.calculationUsage():
                ctx = behav_elem.calculationUsage()
                result = _make_calculation_usage_dict(ctx, None)
                if result and result.get("name") == "PackageMember":
                    return result.get("ownedRelatedElement")
                return result
            
            if hasattr(behav_elem, 'constraintUsage') and behav_elem.constraintUsage():
                ctx = behav_elem.constraintUsage()
                result = _make_constraint_usage_dict(ctx, None)
                if result and result.get("name") == "PackageMember":
                    return result.get("ownedRelatedElement")
                return result
    
    # Check for non-occurrence usage (attribute, calculation)
    if hasattr(usage_elem_ctx, 'nonOccurrenceUsageElement') and usage_elem_ctx.nonOccurrenceUsageElement():
        non_occ = usage_elem_ctx.nonOccurrenceUsageElement()
        
        if hasattr(non_occ, 'attributeUsage') and non_occ.attributeUsage():
            ctx = non_occ.attributeUsage()
            name = None
            if hasattr(ctx, 'identifier'):
                ids = ctx.identifier()
                if isinstance(ids, list) and ids:
                    name = ids[0].getText()
            return {
                "name": "UsageElement",
                "ownedRelatedElement": {
                    "name": "AttributeUsage",
                    "prefix": None,
                    "usage": {
                        "name": "Usage",
                        "declaration": {
                            "name": "UsageDeclaration",
                            "declaration": {
                                "name": "FeatureDeclaration",
                                "identification": {
                                    "name": "Identification",
                                    "declaredShortName": None,
                                    "declaredName": name
                                },
                                "specialization": None
                            }
                        },
                        "completion": {
                            "name": "UsageCompletion",
                            "valuepart": None,
                            "body": {
                                "name": "UsageBody",
                                "body": {
                                    "name": "DefinitionBody",
                                    "ownedRelatedElement": []
                                }
                            }
                        }
                    }
                }
            }
    
    return None


def _visit_usage_element_dict(usage_elem_ctx, prefix=None):
    """Visit a usage element context and return a dictionary."""
    # The usage element can be either:
    # 1. NonOccurrenceUsageElement (attribute, calculation, etc.)
    # 2. OccurrenceUsageElement -> StructureUsageElement or BehaviorUsageElement
    
    # First check for occurrence usage (part, item, port)
    if hasattr(usage_elem_ctx, 'occurrenceUsageElement') and usage_elem_ctx.occurrenceUsageElement():
        occ_elem = usage_elem_ctx.occurrenceUsageElement()
        
        # Check structure usage elements (part, item, port)
        if hasattr(occ_elem, 'structureUsageElement') and occ_elem.structureUsageElement():
            struct_elem = occ_elem.structureUsageElement()
            
            if hasattr(struct_elem, 'partUsage') and struct_elem.partUsage():
                ctx = struct_elem.partUsage()
                name, shortname = _get_usage_identification(ctx)
                body_items = _get_usage_body_items(ctx)
                occ_prefix = _get_occurrence_usage_prefix(ctx)
                specialization = _build_full_specialization_from_ctx(ctx)
                return _make_usage_dict("PartUsage", name, shortname, occ_prefix or prefix, structure=True, wrapped=True, body_items=body_items, specialization=specialization)
            elif hasattr(struct_elem, 'itemUsage') and struct_elem.itemUsage():
                ctx = struct_elem.itemUsage()
                name, shortname = _get_usage_identification(ctx)
                body_items = _get_usage_body_items(ctx)
                occ_prefix = _get_occurrence_usage_prefix(ctx)
                specialization = _build_full_specialization_from_ctx(ctx)
                return _make_usage_dict("ItemUsage", name, shortname, occ_prefix or prefix, structure=True, wrapped=True, body_items=body_items, specialization=specialization)
            elif hasattr(struct_elem, 'portUsage') and struct_elem.portUsage():
                ctx = struct_elem.portUsage()
                name, shortname = _get_usage_identification(ctx)
                body_items = _get_usage_body_items(ctx)
                occ_prefix = _get_occurrence_usage_prefix(ctx)
                specialization = _build_full_specialization_from_ctx(ctx)
                return _make_usage_dict("PortUsage", name, shortname, occ_prefix or prefix, structure=True, wrapped=True, body_items=body_items, specialization=specialization)
            elif hasattr(struct_elem, 'connectionUsage') and struct_elem.connectionUsage():
                ctx = struct_elem.connectionUsage()
                return _make_connection_usage_dict(ctx, prefix)
            elif hasattr(struct_elem, 'flowConnectionUsage') and struct_elem.flowConnectionUsage():
                ctx = struct_elem.flowConnectionUsage()
                return _make_nested_flow_connection_usage_dict(ctx, prefix)
            elif hasattr(struct_elem, 'flowUsage') and struct_elem.flowUsage():
                ctx = struct_elem.flowUsage()
                return _make_nested_flow_connection_usage_dict(ctx, prefix)
            elif hasattr(struct_elem, 'successionFlowUsage') and struct_elem.successionFlowUsage():
                ctx = struct_elem.successionFlowUsage()
                return _make_nested_succession_flow_usage_dict(ctx, prefix)
            elif hasattr(struct_elem, 'allocationUsage') and struct_elem.allocationUsage():
                ctx = struct_elem.allocationUsage()
                return _make_allocation_usage_dict(ctx, prefix)
            elif hasattr(struct_elem, 'renderingUsage') and struct_elem.renderingUsage():
                ctx = struct_elem.renderingUsage()
                return _make_rendering_usage_dict(ctx, prefix)
            elif hasattr(struct_elem, 'individualUsage') and struct_elem.individualUsage():
                ctx = struct_elem.individualUsage()
                return _make_individual_usage_dict(ctx, prefix)
            elif hasattr(struct_elem, 'portionUsage') and struct_elem.portionUsage():
                ctx = struct_elem.portionUsage()
                name, shortname = _get_usage_identification(ctx)
                body_items = _get_usage_body_items(ctx)
                occ_prefix = _make_portion_usage_prefix(ctx)
                specialization = _build_full_specialization_from_ctx(ctx)
                valuepart = _get_usage_value_part(ctx)
                inner = _make_nested_usage_element("PortionUsage", name, shortname, occ_prefix, body_items, specialization, valuepart)
                if inner:
                    return {
                        "name": "PackageMember",
                        "prefix": None,
                        "ownedRelatedElement": inner
                    }
                return None
            elif hasattr(struct_elem, 'viewUsage') and struct_elem.viewUsage():
                ctx = struct_elem.viewUsage()
                return _make_view_usage_dict(ctx, prefix)
            elif hasattr(struct_elem, 'interfaceUsage') and struct_elem.interfaceUsage():
                ctx = struct_elem.interfaceUsage()
                return _make_interface_usage_dict(ctx, prefix)
            elif hasattr(struct_elem, 'message') and struct_elem.message():
                ctx = struct_elem.message()
                return _make_message_dict(ctx, prefix)
        
        # Check behavior usage elements (action, state, etc.)
        if hasattr(occ_elem, 'behaviorUsageElement') and occ_elem.behaviorUsageElement():
            behav_elem = occ_elem.behaviorUsageElement()
            
            if hasattr(behav_elem, 'stateUsage') and behav_elem.stateUsage():
                ctx = behav_elem.stateUsage()
                return _make_state_usage_dict(ctx, prefix)
            elif hasattr(behav_elem, 'performActionUsage') and behav_elem.performActionUsage():
                ctx = behav_elem.performActionUsage()
                return _make_nested_perform_action_usage_dict(ctx, None)
            elif hasattr(behav_elem, 'calculationUsage') and behav_elem.calculationUsage():
                ctx = behav_elem.calculationUsage()
                return _make_calculation_usage_dict(ctx, prefix)
            elif hasattr(behav_elem, 'constraintUsage') and behav_elem.constraintUsage():
                ctx = behav_elem.constraintUsage()
                return _make_constraint_usage_dict(ctx, prefix)
            elif hasattr(behav_elem, 'requirementUsage') and behav_elem.requirementUsage():
                ctx = behav_elem.requirementUsage()
                return _make_requirement_usage_dict(ctx, prefix)
            elif hasattr(behav_elem, 'assertConstraintUsage') and behav_elem.assertConstraintUsage():
                ctx = behav_elem.assertConstraintUsage()
                result = _make_assert_constraint_usage_dict(ctx, prefix)
                if result:
                    return {
                        "name": "PackageMember",
                        "prefix": None,
                        "ownedRelatedElement": {
                            "name": "UsageElement",
                            "ownedRelatedElement": {
                                "name": "OccurrenceUsageElement",
                                "ownedRelatedElement": {
                                    "name": "BehaviorUsageElement",
                                    "ownedRelationship": result
                                }
                            }
                        }
                    }
                return result
            elif hasattr(behav_elem, 'satisfyRequirementUsage') and behav_elem.satisfyRequirementUsage():
                ctx = behav_elem.satisfyRequirementUsage()
                result = _make_satisfy_requirement_usage_dict(ctx, prefix)
                if result:
                    return {
                        "name": "PackageMember",
                        "prefix": None,
                        "ownedRelatedElement": {
                            "name": "UsageElement",
                            "ownedRelatedElement": {
                                "name": "OccurrenceUsageElement",
                                "ownedRelatedElement": {
                                    "name": "BehaviorUsageElement",
                                    "ownedRelationship": result
                                }
                            }
                        }
                    }
                return result
            elif hasattr(behav_elem, 'viewpointUsage') and behav_elem.viewpointUsage():
                ctx = behav_elem.viewpointUsage()
                return _make_viewpoint_usage_dict(ctx, prefix)
            elif hasattr(behav_elem, 'concernUsage') and behav_elem.concernUsage():
                ctx = behav_elem.concernUsage()
                return _make_concern_usage_dict(ctx, prefix)
            elif hasattr(behav_elem, 'analysisCaseUsage') and behav_elem.analysisCaseUsage():
                ctx = behav_elem.analysisCaseUsage()
                return _make_nested_analysis_case_usage_dict(ctx, prefix)
            elif hasattr(behav_elem, 'caseUsage') and behav_elem.caseUsage():
                ctx = behav_elem.caseUsage()
                return _make_nested_case_usage_dict(ctx, prefix)
            elif hasattr(behav_elem, 'useCaseUsage') and behav_elem.useCaseUsage():
                ctx = behav_elem.useCaseUsage()
                return _make_use_case_usage_dict(ctx, prefix)
            elif hasattr(behav_elem, 'actionUsage') and behav_elem.actionUsage():
                ctx = behav_elem.actionUsage()
                name = None
                shortname = None
                typed_by = None
                occ_prefix = None
                
                # Get name from actionUsageDeclaration -> usageDeclaration -> identification
                if ctx.actionUsageDeclaration():
                    aud = ctx.actionUsageDeclaration()
                    if hasattr(aud, 'usageDeclaration') and aud.usageDeclaration():
                        ud = aud.usageDeclaration()
                        if isinstance(ud, list):
                            ud = ud[0] if ud else None
                        if ud and hasattr(ud, 'identification') and ud.identification():
                            ident = ud.identification()
                            if hasattr(ident, 'name'):
                                name_list = ident.name()
                                if name_list and isinstance(name_list, list):
                                    if len(name_list) == 2:
                                        shortname = name_list[0].getText()
                                        name = name_list[1].getText()
                                    elif len(name_list) == 1:
                                        name_text = name_list[0].getText()
                                        name, shortname = _extract_name_shortname(name_text)
                        # Extract typed_by for the specialization
                        typed_by = _get_action_usage_typed_by(ctx)
                        if typed_by is None:
                            typed_by = _get_usage_subsetted_by(ctx)
                
                # Get body items
                action_items = _visit_action_body_items(ctx)
                
                # Full specialization (Typings + Subsettings + Redefinitions +
                # References); typed-by fallback for odd contexts.
                spec_full = _full_specialization_for_ctx(ctx)
                if spec_full is not None:
                    specialization = spec_full
                else:
                    specialization = _build_specialization(typed_by) if typed_by else None
                
                return {
                    "name": "PackageMember",
                    "prefix": None,
                    "ownedRelatedElement": {
                        "name": "UsageElement",
                        "ownedRelatedElement": {
                            "name": "OccurrenceUsageElement",
                            "ownedRelatedElement": {
                                "name": "BehaviorUsageElement",
                                "ownedRelationship": {
                                    "name": "ActionUsage",
                                    "prefix": occ_prefix,
                                    "declaration": {
                                        "name": "ActionUsageDeclaration",
                                        "declaration": {
                                            "name": "UsageDeclaration",
                                            "declaration": {
                                                "name": "FeatureDeclaration",
                                                "identification": {
                                                    "name": "Identification",
                                                    "declaredShortName": shortname,
                                                    "declaredName": name
                                                },
                                                "specialization": specialization
                                            }
                                        },
                                        "valuepart": None
                                    },
                                    "body": {
                                        "name": "ActionBody",
                                        "items": action_items
                                    }
                                }
                            }
                        }
                    }
                }
    
    # Fall back to checking non-occurrence usage types
    if hasattr(usage_elem_ctx, 'nonOccurrenceUsageElement') and usage_elem_ctx.nonOccurrenceUsageElement():
        non_occ = usage_elem_ctx.nonOccurrenceUsageElement()

        if hasattr(non_occ, 'attributeUsage') and non_occ.attributeUsage():
            ctx = non_occ.attributeUsage()
            name, shortname = _get_usage_identification(ctx)
            body_items = _get_usage_body_items(ctx)
            # Use the full specialization builder so re-declarations
            # (`:>`, `:>>`, `::>` / `references`) round-trip alongside typings.
            specialization = _build_full_specialization_from_ctx(ctx)
            valuepart = _get_usage_value_part(ctx)
            return {
                "name": "PackageMember",
                "prefix": None,
                "ownedRelatedElement": {
                    "name": "UsageElement",
                    "ownedRelatedElement": {
                        "name": "NonOccurrenceUsageElement",
                        "ownedRelatedElement": {
                            "name": "AttributeUsage",
                            "prefix": prefix,
                            "usage": {
                                "name": "Usage",
                                "declaration": {
                                    "name": "UsageDeclaration",
                                    "declaration": {
                                        "name": "FeatureDeclaration",
                                        "identification": {
                                            "name": "Identification",
                                            "declaredShortName": shortname,
                                            "declaredName": name
                                        },
                                        "specialization": specialization
                                    }
                                },
                                "completion": {
                                    "name": "UsageCompletion",
                                    "valuepart": valuepart,
                                    "body": {
                                        "name": "UsageBody",
                                        "body": {
                                            "name": "DefinitionBody",
                                            "ownedRelatedElement": body_items
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
    
    return None


def _make_usage_dict(usage_type, name, shortname, prefix, structure=True, wrapped=True, body_items=None, typed_by=None, specialization=None):
    """Build a usage dictionary for PartUsage/ItemUsage/PortUsage.
    
    Parameters
    ----------
    usage_type : str
        'PartUsage', 'ItemUsage', or 'PortUsage'
    name : str or None
        The long name
    shortname : str or None
        The short name
    prefix : str or None
        Prefix (redefines, conjugated, etc.)
    structure : bool
        True for StructureUsageElement wrapping
    wrapped : bool
        True if this should be wrapped in PackageMember (top-level),
        False for nested usages
    body_items : list
        List of nested body items
    typed_by : str
        Name of the type this usage is typed by (e.g., "Fuel" in "item Hydrogen : Fuel")
    specialization : dict or None
        Pre-built FeatureSpecializationPart dict (from _build_full_specialization_from_ctx)
    
    Returns
    -------
    dict
        The usage dictionary
    """
    if body_items is None:
        body_items = []
    
    # Build specialization - prefer pre-built specialization, fall back to typed_by
    if specialization is None and typed_by:
        specialization = _build_specialization(typed_by)
    
    inner_usage = {
        "name": usage_type,
        "prefix": prefix,
        "usage": {
            "name": "Usage",
            "declaration": {
                "name": "UsageDeclaration",
                "declaration": {
                    "name": "FeatureDeclaration",
                    "identification": {
                        "name": "Identification",
                        "declaredShortName": shortname,
                        "declaredName": name
                    },
                    "specialization": specialization
                }
            },
            "completion": {
                "name": "UsageCompletion",
                "valuepart": None,
                "body": {
                    "name": "UsageBody",
                    "body": {
                        "name": "DefinitionBody",
                        "ownedRelatedElement": body_items
                    }
                }
            }
        }
    }
    
    if wrapped:
        return {
            "name": "PackageMember",
            "prefix": None,
            "ownedRelatedElement": {
                "name": "UsageElement",
                "ownedRelatedElement": {
                    "name": "OccurrenceUsageElement",
                    "ownedRelatedElement": {
                        "name": "StructureUsageElement",
                        "ownedRelatedElement": inner_usage
                    }
                }
            }
        }
    else:
        return {
            "name": "UsageElement",
            "ownedRelatedElement": inner_usage
        }


def _get_action_usage_typed_by(ctx):
    """Extract the typed-by reference from a usage context.
    
    Can work with:
    - actionUsageDeclaration / constraintUsageDeclaration / calculationUsageDeclaration
    - constraintUsageDeclaration (which has usageDeclaration directly)
    
    Returns the qualified name of the type, or None.
    """
    if ctx is None:
        return None
    
    # First, try the *Declaration pattern (action, constraint, calculation)
    aud = None
    for attr in ('actionUsageDeclaration', 'constraintUsageDeclaration', 'calculationUsageDeclaration'):
        if hasattr(ctx, attr):
            method = getattr(ctx, attr)
            value = method()
            if value:
                aud = value
                break
    
    # If not found, check for direct usageDeclaration (e.g., in ConstraintUsageDeclaration)
    if aud is None and hasattr(ctx, 'usageDeclaration'):
        ud = ctx.usageDeclaration()
        if isinstance(ud, list):
            ud = ud[0] if ud else None
        if ud is not None:
            # This is the usageDeclaration directly, not wrapped in a *Declaration
            # We can use it directly for typing extraction
            aud = ud  # Treat the direct usageDeclaration as the context for typing extraction
    
    if aud is None:
        return None
    
    # Get usageDeclaration from the *Declaration context (or direct usageDeclaration)
    if hasattr(aud, 'usageDeclaration') and aud.usageDeclaration():
        ud = aud.usageDeclaration()
        if isinstance(ud, list):
            ud = ud[0] if ud else None
    else:
        # aud is already the usageDeclaration
        ud = aud if hasattr(aud, 'featureSpecializationPart') else None
    
    if ud is None:
        return None
    
    # Get featureSpecializationPart
    if hasattr(ud, 'featureSpecializationPart') and ud.featureSpecializationPart():
        fsp = ud.featureSpecializationPart()
        if hasattr(fsp, 'featureSpecialization') and fsp.featureSpecialization():
            specs = fsp.featureSpecialization()
            if not isinstance(specs, list):
                specs = [specs]
            for spec in specs:
                if hasattr(spec, 'typings') and spec.typings():
                    typings = spec.typings()
                    if isinstance(typings, list):
                        typings = typings[0] if typings else None
                    if typings and hasattr(typings, 'getText'):
                        text = typings.getText()
                        if text.startswith(':'):
                            text = text[1:].strip()
                        return text
    
    return None


def _get_action_usage_subsetted_by(ctx):
    """Extract the subsetted-by reference from an actionUsage context.
    
    ActionUsage has actionUsageDeclaration (not direct usageDeclaration),
    and actionUsageDeclaration can contain usageDeclaration.
    Returns the qualified name of the subsetting type, or None.
    """
    if ctx is None:
        return None
    
    # Get actionUsageDeclaration
    aud = None
    if hasattr(ctx, 'actionUsageDeclaration') and ctx.actionUsageDeclaration():
        aud = ctx.actionUsageDeclaration()
    
    if aud is None:
        return None
    
    # Get usageDeclaration from actionUsageDeclaration
    ud = None
    if hasattr(aud, 'usageDeclaration') and aud.usageDeclaration():
        ud = aud.usageDeclaration()
        if isinstance(ud, list):
            ud = ud[0] if ud else None
    
    if ud is None:
        return None
    
    # Get featureSpecializationPart
    if hasattr(ud, 'featureSpecializationPart') and ud.featureSpecializationPart():
        fsp = ud.featureSpecializationPart()
        if hasattr(fsp, 'featureSpecialization') and fsp.featureSpecialization():
            specs = fsp.featureSpecialization()
            if not isinstance(specs, list):
                specs = [specs]
            for spec in specs:
                if hasattr(spec, 'subsettings') and spec.subsettings():
                    subs = spec.subsettings()
                    if hasattr(subs, 'getText'):
                        text = subs.getText()
                        if text.startswith(':>'):
                            text = text[2:].strip()
                        return text
    
    return None


def _dotted_segments(owned_ctx):
    """Segments of an ownedSubsetting / ownedRedefinition /
    ownedReferenceSubsetting context.

    Grammar: qualifiedName (DOT qualifiedName)* — e.g. ``base.x`` yields
    ``['base', 'x']``. Each segment may itself be '::'-qualified.
    """
    segs = []
    if owned_ctx is None:
        return segs
    for c2 in owned_ctx.children:
        if type(c2).__name__ == 'QualifiedNameContext':
            segs.append(c2.getText())
    return segs


def _emit_owned_chain(dict_name, feature_key, segs):
    """Build an Owned{Subsetting,Redefinition,ReferenceSubsetting} dict
    from dotted segments: first segment becomes the direct feature, the
    remainder become an OwnedFeatureChain so chained forms like
    ``:> base.x`` survive round-trip."""
    head = {
        "name": "QualifiedName",
        "names": segs[0].split("::"),
    }
    owned_related = []
    if len(segs) > 1:
        chain_elements = [
            {
                "name": "OwnedFeatureChaining",
                "chainingFeature": {"name": "QualifiedName", "names": s.split("::")},
            }
            for s in segs[1:]
        ]
        owned_related.append({
            "name": "OwnedFeatureChain",
            "feature": {
                "name": "FeatureChain",
                "ownedRelationship": chain_elements,
            },
        })
    return {
        "name": dict_name,
        feature_key: head,
        "ownedRelatedElement": owned_related,
    }


def _collect_owned_contexts(wrapper_children, direct_type, wrapper_types):
    """Yield each Owned*Context found under a Subsettings/Redefinitions/
    References rule context. Handles both direct children and one of the
    keyword-wrapper contexts (SubsetsContext, RedefinesContext, …)."""
    for child in wrapper_children:
        child_name = type(child).__name__
        if child_name == direct_type:
            yield child
        elif child_name in wrapper_types:
            for c3 in child.children:
                if type(c3).__name__ == direct_type:
                    yield c3


def _full_specialization_for_ctx(ctx):
    """Best-effort full specialization for any usage-like context.

    Tries, in order:
      1. ctx.usage().usageDeclaration().featureSpecializationPart()
         (whole-usage contexts: attributeUsage, partUsage, …)
      2. ctx.usageDeclaration().featureSpecializationPart()
      3. ctx.<x>UsageDeclaration().usageDeclaration().featureSpecializationPart()
         for any ``*UsageDeclaration`` accessor on ctx
         (actionUsageDeclaration, constraintUsageDeclaration, …)

    Returns None when no path yields a featureSpecializationPart. Callers
    that previously did ``_build_specialization(typed_by)`` can call this
    instead to also capture Redefinitions / Subsettings / References.
    """
    if ctx is None:
        return None

    def _fsp_from_ud(ud):
        if ud is None:
            return None
        if isinstance(ud, list):
            ud = ud[0] if ud else None
        if ud is None:
            return None
        fsp_getter = getattr(ud, "featureSpecializationPart", None)
        if callable(fsp_getter) and fsp_getter():
            return _build_full_specialization_from_fsp(fsp_getter())
        return None

    # 1) whole-usage context
    usage = getattr(ctx, "usage", None)
    if callable(usage):
        u = usage()
        if u is not None and hasattr(u, "usageDeclaration"):
            spec = _fsp_from_ud(u.usageDeclaration())
            if spec is not None:
                return spec

    # 2) direct usageDeclaration on ctx
    ud_getter = getattr(ctx, "usageDeclaration", None)
    if callable(ud_getter):
        spec = _fsp_from_ud(ud_getter())
        if spec is not None:
            return spec

    # 3) any *UsageDeclaration holder (actionUsageDeclaration, …)
    for attr in sorted(dir(ctx)):
        if not attr.endswith("UsageDeclaration") or attr == "usageDeclaration":
            continue
        getter = getattr(ctx, attr, None)
        if callable(getter):
            try:
                holder = getter()
            except Exception:
                continue
            if holder is None:
                continue
            if callable(getattr(holder, "usageDeclaration", None)):
                spec = _fsp_from_ud(holder.usageDeclaration())
                if spec is not None:
                    return spec
            spec = _fsp_from_ud(holder)
            if spec is not None:
                return spec

    return None


def _build_specialization(typed_by):
    """Build the specialization dictionary structure for a typed-by reference."""
    if not typed_by:
        return None
    
    qn_names = typed_by.split("::")
    
    return {
        "name": "FeatureSpecializationPart",
        "specialization": [
            {
                "name": "FeatureSpecialization",
                "ownedRelationship": {
                    "name": "Typings",
                    "typedby": {
                        "name": "TypedBy",
                        "ownedRelationship": [
                            {
                                "name": "FeatureTyping",
                                "ownedRelationship": {
                                    "name": "OwnedFeatureTyping",
                                    "type": {
                                        "name": "FeatureType",
                                        "type": {
                                            "name": "QualifiedName",
                                            "names": qn_names
                                        },
                                        "ownedRelatedElement": []
                                    }
                                }
                            }
                        ]
                    },
                    "ownedRelationship": []
                }
            }
        ],
        "multiplicity": None,
        "specialization2": [],
        "multiplicity2": None,
    }


def _get_multiplicity_part(fsp_ctx):
    """Extract MultiplicityPart dict from featureSpecializationPart context.
    
    Handles [N], [N..M], [*] forms. Returns None if no multiplicity.
    """
    if fsp_ctx is None:
        return None
    
    for child in fsp_ctx.children:
        if type(child).__name__ == 'MultiplicityPartContext':
            mp_ctx = child
            break
    else:
        return None
    
    try:
        omc = mp_ctx.children[0]       # OwnedMultiplicityContext
        omrc = omc.children[0]          # OwnedMultiplicityRangeContext
        bounds = omrc.children[0]       # MultiplicityBoundsContext
        members = [c for c in bounds.children if 'ExpressionMember' in type(c).__name__]
        
        def _make_bound(value_text):
            if value_text == '*':
                return {
                    "name": "MultiplicityExpressionMember",
                    "ownedRelatedElement": [
                        {"name": "MultiplicityRelatedElement", "ownedRelatedElement":
                            {"name": "LiteralInfinity", "value": "*"}
                        }
                    ]
                }
            elif value_text.isdigit():
                return {
                    "name": "MultiplicityExpressionMember",
                    "ownedRelatedElement": [
                        {"name": "MultiplicityRelatedElement", "ownedRelatedElement":
                            {"name": "LiteralInteger", "value": int(value_text)}
                        }
                    ]
                }
            else:
                # Variable reference like 'i'
                return {
                    "name": "MultiplicityExpressionMember",
                    "ownedRelatedElement": [
                        {"name": "MultiplicityRelatedElement", "ownedRelatedElement":
                            {"name": "FeatureReferenceExpression", "ownedRelationship": [
                                {"name": "FeatureReferenceMember", "memberElement": value_text}
                            ]}
                        }
                    ]
                }
        
        if len(members) == 1:
            # [N] or [*]
            bound_dicts = [_make_bound(members[0].getText())]
        elif len(members) == 2:
            # [N..M]
            bound_dicts = [_make_bound(members[0].getText()), _make_bound(members[1].getText())]
        else:
            return None
        
        return {
            "name": "MultiplicityPart",
            "isOrdered": False,
            "isNonunique": False,
            "ownedRelationship": [
                {
                    "name": "OwnedMultiplicity",
                    "ownedRelatedElement": [
                        {
                            "name": "MultiplicityRange",
                            "ownedRelationship": bound_dicts
                        }
                    ]
                }
            ]
        }
    except (IndexError, AttributeError):
        return None


def _build_full_specialization_from_ctx(ctx):
    """Build a full FeatureSpecializationPart dict from a usage ANTLR context.
    
    Extracts all specializations (typings, redefinitions, subsets) from the
    featureSpecializationPart of the usage declaration.
    Returns None if there are no specializations.
    """
    if ctx is None:
        return None
    
    usage = None
    if hasattr(ctx, 'usage') and ctx.usage():
        usage = ctx.usage()
    
    ud = None
    if usage and hasattr(usage, 'usageDeclaration') and usage.usageDeclaration():
        ud = usage.usageDeclaration()
        # ud can be a list (multiple alternatives) or a single context
        if isinstance(ud, list):
            ud = ud[0] if ud else None
    
    if ud is None:
        return None
    
    fsp = None
    if hasattr(ud, 'featureSpecializationPart') and ud.featureSpecializationPart():
        fsp = ud.featureSpecializationPart()
    
    if fsp is None:
        return None
    
    specs = fsp.featureSpecialization() if hasattr(fsp, 'featureSpecialization') else []
    if not isinstance(specs, list):
        specs = [specs]
    
    # Extract multiplicity first (before the early return check)
    multiplicity = _get_multiplicity_part(fsp)
    
    # Only return None if there are neither specializations nor multiplicity
    if not specs and multiplicity is None:
        return None
    
    specialization_list = []
    
    for spec in specs:
        # Typings: ': TypeName'
        if hasattr(spec, 'typings') and spec.typings():
            typings = spec.typings()
            # Navigate to the type qualified name
            typed_by = None
            if hasattr(typings, 'typedBy') and typings.typedBy():
                tb = typings.typedBy()
                if hasattr(tb, 'featureTyping') and tb.featureTyping():
                    ft = tb.featureTyping()
                    if hasattr(ft, 'qualifiedName') and ft.qualifiedName():
                        typed_by = ft.qualifiedName().getText()
            if typed_by is None:
                # Fallback: extract from typings getText
                t_text = typings.getText()
                if t_text.startswith(':'):
                    typed_by = t_text[1:].strip()
            if typed_by:
                qn_names = typed_by.split("::")
                specialization_list.append({
                    "name": "FeatureSpecialization",
                    "ownedRelationship": {
                        "name": "Typings",
                        "typedby": {
                            "name": "TypedBy",
                            "ownedRelationship": [
                                {
                                    "name": "FeatureTyping",
                                    "ownedRelationship": {
                                        "name": "OwnedFeatureTyping",
                                        "type": {
                                            "name": "FeatureType",
                                            "type": {"name": "QualifiedName", "names": qn_names},
                                            "ownedRelatedElement": []
                                        }
                                    }
                                }
                            ]
                        },
                        "ownedRelationship": []
                    }
                })
        
        # Redefinitions: ':>> name' or 'redefines name'
        elif hasattr(spec, 'redefinitions') and spec.redefinitions():
            redef_ctx = spec.redefinitions()
            # redef_ctx can be a single RedefinitionsContext or a list
            if not isinstance(redef_ctx, list):
                redef_ctx = [redef_ctx]
            owned = []
            for rc in redef_ctx:
                # OwnedRedefinitionContext may be a dotted chain
                # (qualifiedName (DOT qualifiedName)*).
                for or_ctx in _collect_owned_contexts(
                    rc.children, 'OwnedRedefinitionContext',
                    ('RedefinesContext',),
                ):
                    segs = _dotted_segments(or_ctx)
                    if segs:
                        owned.append(_emit_owned_chain(
                            'OwnedRedefinition', 'redefinedFeature', segs))
            if owned:
                specialization_list.append({
                    "name": "FeatureSpecialization",
                    "ownedRelationship": {
                        "name": "Redefinitions",
                        "ownedRelationship": owned
                    }
                })
        
        # Subsettings: ':> name' or 'subsets name'
        elif hasattr(spec, 'subsettings') and spec.subsettings():
            sub_ctx = spec.subsettings()
            # sub_ctx can be a single SubsettingsContext or a list
            if not isinstance(sub_ctx, list):
                sub_ctx = [sub_ctx]
            owned = []
            for sc in sub_ctx:
                # Each Owned*Context may be a dotted chain
                # (qualifiedName (DOT qualifiedName)*).
                for os_ctx in _collect_owned_contexts(
                    sc.children, 'OwnedSubsettingContext',
                    ('SubsetsContext', 'SpecializesContext'),
                ):
                    segs = _dotted_segments(os_ctx)
                    if segs:
                        owned.append(_emit_owned_chain(
                            'OwnedSubsetting', 'subsettedFeature', segs))
            if owned:
                specialization_list.append({
                    "name": "FeatureSpecialization",
                    "ownedRelationship": {
                        "name": "Subsettings",
                        "ownedRelationship": owned
                    }
                })

        # References: '::> name' or 'references name'
        elif hasattr(spec, 'references') and spec.references():
            ref_ctx = spec.references()
            if not isinstance(ref_ctx, list):
                ref_ctx = [ref_ctx]
            owned = []
            for rc in ref_ctx:
                # OwnedReferenceSubsettingContext may be a dotted chain.
                for ors_ctx in _collect_owned_contexts(
                    rc.children, 'OwnedReferenceSubsettingContext',
                    ('ReferencesContext',),
                ):
                    segs = _dotted_segments(ors_ctx)
                    if segs:
                        owned.append(_emit_owned_chain(
                            'OwnedReferenceSubsetting', 'referencedFeature', segs))
            if owned:
                specialization_list.append({
                    "name": "FeatureSpecialization",
                    "ownedRelationship": {
                        "name": "References",
                        "ownedRelationship": owned
                    }
                })

    return {
        "name": "FeatureSpecializationPart",
        "specialization": specialization_list,
        "multiplicity": multiplicity,
        "specialization2": [],
        "multiplicity2": None,
    }


def _get_usage_body_items(ctx):
    """Extract body items from a usage context via usage().usageCompletion().usageBody().definitionBody().
    
    Returns a list of body items or empty list.
    """
    body_items = []
    if ctx is None:
        return body_items
    
    # Get usage -> usageCompletion -> usageBody -> definitionBody
    usage = None
    if hasattr(ctx, 'usage') and ctx.usage():
        usage = ctx.usage()
    
    if usage and hasattr(usage, 'usageCompletion') and usage.usageCompletion():
        uc = usage.usageCompletion()
        if hasattr(uc, 'usageBody') and uc.usageBody():
            ub = uc.usageBody()
            if hasattr(ub, 'definitionBody') and ub.definitionBody():
                db = ub.definitionBody()
                body_items = _visit_definition_body_dict(db)
    
    return body_items


def _extract_body_from_usage_ctx(ctx):
    """Extract body items directly from a usage context (not wrapped).
    
    For AttributeUsageContext: ctx -> usage() -> usageCompletion -> usageBody -> definitionBody
    Returns a list of body items or empty list.
    """
    if ctx is None:
        return []
    
    # Get usage from the context (e.g., AttributeUsageContext.usage())
    usage = None
    if hasattr(ctx, 'usage') and ctx.usage():
        usage = ctx.usage()
    
    if usage and hasattr(usage, 'usageCompletion') and usage.usageCompletion():
        uc = usage.usageCompletion()
        if hasattr(uc, 'usageBody') and uc.usageBody():
            ub = uc.usageBody()
            if hasattr(ub, 'definitionBody') and ub.definitionBody():
                db = ub.definitionBody()
                return _visit_definition_body_dict(db)
    
    return []


def _get_usage_typed_by(ctx):
    """Extract the typed-by reference from a usage context.
    
    Returns the qualified name of the type, or None.
    """
    if ctx is None:
        return None
    
    # Get usage -> usageDeclaration -> featureSpecializationPart
    usage = None
    if hasattr(ctx, 'usage') and ctx.usage():
        usage = ctx.usage()
    
    ud = None
    if usage and hasattr(usage, 'usageDeclaration') and usage.usageDeclaration():
        ud = usage.usageDeclaration()
    
    if ud and hasattr(ud, 'featureSpecializationPart') and ud.featureSpecializationPart():
        fsp = ud.featureSpecializationPart()
        # Only look for Typings (': TypeName'), not subsets/redefines/specializes
        if hasattr(fsp, 'featureSpecialization') and fsp.featureSpecialization():
            specs = fsp.featureSpecialization()
            if not isinstance(specs, list):
                specs = [specs]
            for spec in specs:
                if hasattr(spec, 'typings') and spec.typings():
                    typings = spec.typings()
                    if hasattr(typings, 'getText'):
                        text = typings.getText()
                        if text.startswith(':'):
                            text = text[1:].strip()
                        return text
        # NOTE: Do NOT fall back to fsp.getText() — that would return
        # 'redefines X', 'subsets X', or ':> X' which are NOT types.
    
    return None


def _get_usage_subsetted_by(ctx):
    """Extract the subsetted-by reference from a usage context.
    
    Returns the qualified name of the subsetting type, or None.
    """
    if ctx is None:
        return None
    
    # Get usage -> usageDeclaration -> featureSpecializationPart -> featureSpecialization
    usage = None
    if hasattr(ctx, 'usage') and ctx.usage():
        usage = ctx.usage()
    
    ud = None
    if usage and hasattr(usage, 'usageDeclaration') and usage.usageDeclaration():
        ud = usage.usageDeclaration()
    
    if ud and hasattr(ud, 'featureSpecializationPart') and ud.featureSpecializationPart():
        fsp = ud.featureSpecializationPart()
        if hasattr(fsp, 'featureSpecialization') and fsp.featureSpecialization():
            specs = fsp.featureSpecialization()
            if not isinstance(specs, list):
                specs = [specs]
            for spec in specs:
                if hasattr(spec, 'subsettings') and spec.subsettings():
                    subs = spec.subsettings()
                    if hasattr(subs, 'getText'):
                        text = subs.getText()
                        if text.startswith(':>'):
                            text = text[2:].strip()
                        return text
    
    return None


def _build_specialization_from_fsp(fsp):
    """Build specialization dict from a FeatureSpecializationPartContext directly."""
    if fsp is None:
        return None
    
    specs = fsp.featureSpecialization() if hasattr(fsp, 'featureSpecialization') else []
    if not specs:
        return None
    
    if not isinstance(specs, list):
        specs = [specs]
    
    specialization_list = []
    
    for spec in specs:
        # Typings: ': TypeName'
        if hasattr(spec, 'typings') and spec.typings():
            typings = spec.typings()
            typed_by = None
            if hasattr(typings, 'typedBy') and typings.typedBy():
                tb = typings.typedBy()
                if hasattr(tb, 'featureTyping') and tb.featureTyping():
                    ft = tb.featureTyping()
                    if hasattr(ft, 'ownedFeatureTyping') and ft.ownedFeatureTyping():
                        oft = ft.ownedFeatureTyping()
                        qns = oft.qualifiedName()
                        if isinstance(qns, list):
                            qns = [qn for qn in qns if qn]
                        if qns:
                            if isinstance(qns, list):
                                typed_by = qns[0].getText()
                            else:
                                typed_by = qns.getText()
                    elif hasattr(ft, 'qualifiedName') and ft.qualifiedName():
                        typed_by = ft.qualifiedName().getText()
            if typed_by is None:
                t_text = typings.getText()
                if t_text.startswith(':'):
                    typed_by = t_text[1:].strip()
            if typed_by:
                qn_names = typed_by.split("::")
                specialization_list.append({
                    "name": "FeatureSpecialization",
                    "ownedRelationship": {
                        "name": "Typings",
                        "ownedRelationship": [],
                        "typedby": {
                            "name": "TypedBy",
                            "ownedRelationship": [
                                {
                                    "name": "FeatureTyping",
                                    "ownedRelationship": {
                                        "name": "OwnedFeatureTyping",
                                        "type": {
                                            "name": "FeatureType",
                                            "type": {"name": "QualifiedName", "names": qn_names},
                                            "ownedRelatedElement": []
                                        }
                                    }
                                }
                            ]
                        },
                        "conjugated": None
                    }
                })
    
    if not specialization_list:
        return None
    
    return {
        "name": "FeatureSpecializationPart",
        "specialization": specialization_list,
        "specialization2": None,
        "multiplicity": None,
        "multiplicity2": None
    }


def _build_full_specialization_from_fsp(fsp):
    """Build a full FeatureSpecializationPart dict from a FeatureSpecializationPartContext.
    
    Handles typings, redefinitions, and subsettings.
    Returns None if there are no specializations.
    """
    if fsp is None:
        return None
    
    specs = fsp.featureSpecialization() if hasattr(fsp, 'featureSpecialization') else []
    if not specs:
        return None
    
    if not isinstance(specs, list):
        specs = [specs]
    
    specialization_list = []
    
    for spec in specs:
        # Typings: ': TypeName'
        if hasattr(spec, 'typings') and spec.typings():
            typings = spec.typings()
            typed_by = None
            if hasattr(typings, 'typedBy') and typings.typedBy():
                tb = typings.typedBy()
                if hasattr(tb, 'featureTyping') and tb.featureTyping():
                    ft = tb.featureTyping()
                    if hasattr(ft, 'ownedFeatureTyping') and ft.ownedFeatureTyping():
                        oft = ft.ownedFeatureTyping()
                        qns = oft.qualifiedName()
                        if isinstance(qns, list):
                            qns = [qn for qn in qns if qn]
                        if qns:
                            typed_by = qns[0].getText() if isinstance(qns, list) else qns.getText()
                    elif hasattr(ft, 'qualifiedName') and ft.qualifiedName():
                        typed_by = ft.qualifiedName().getText()
            if typed_by is None:
                t_text = typings.getText()
                if t_text.startswith(':'):
                    typed_by = t_text[1:].strip()
            if typed_by:
                qn_names = typed_by.split("::")
                specialization_list.append({
                    "name": "FeatureSpecialization",
                    "ownedRelationship": {
                        "name": "Typings",
                        "ownedRelationship": [],
                        "typedby": {
                            "name": "TypedBy",
                            "ownedRelationship": [
                                {
                                    "name": "FeatureTyping",
                                    "ownedRelationship": {
                                        "name": "OwnedFeatureTyping",
                                        "type": {
                                            "name": "FeatureType",
                                            "type": {"name": "QualifiedName", "names": qn_names},
                                            "ownedRelatedElement": []
                                        }
                                    }
                                }
                            ]
                        },
                        "conjugated": None
                    }
                })
        
        # Redefinitions: ':>> name' or 'redefines name'
        elif hasattr(spec, 'redefinitions') and spec.redefinitions():
            redef_ctx = spec.redefinitions()
            if not isinstance(redef_ctx, list):
                redef_ctx = [redef_ctx]
            owned = []
            for rc in redef_ctx:
                # OwnedRedefinitionContext may be a dotted chain
                # (qualifiedName (DOT qualifiedName)*).
                for or_ctx in _collect_owned_contexts(
                    rc.children, 'OwnedRedefinitionContext',
                    ('RedefinesContext',),
                ):
                    segs = _dotted_segments(or_ctx)
                    if segs:
                        owned.append(_emit_owned_chain(
                            'OwnedRedefinition', 'redefinedFeature', segs))
            if owned:
                specialization_list.append({
                    "name": "FeatureSpecialization",
                    "ownedRelationship": {
                        "name": "Redefinitions",
                        "ownedRelationship": owned
                    }
                })
        
        # Subsettings: ':> name' or 'subsets name'
        elif hasattr(spec, 'subsettings') and spec.subsettings():
            sub_ctx = spec.subsettings()
            if not isinstance(sub_ctx, list):
                sub_ctx = [sub_ctx]
            owned = []
            for sc in sub_ctx:
                # Each Owned*Context may be a dotted chain
                # (qualifiedName (DOT qualifiedName)*).
                for os_ctx in _collect_owned_contexts(
                    sc.children, 'OwnedSubsettingContext',
                    ('SubsetsContext', 'SpecializesContext'),
                ):
                    segs = _dotted_segments(os_ctx)
                    if segs:
                        owned.append(_emit_owned_chain(
                            'OwnedSubsetting', 'subsettedFeature', segs))
            if owned:
                specialization_list.append({
                    "name": "FeatureSpecialization",
                    "ownedRelationship": {
                        "name": "Subsettings",
                        "ownedRelationship": owned
                    }
                })

        # References: '::> name' or 'references name'
        elif hasattr(spec, 'references') and spec.references():
            ref_ctx = spec.references()
            if not isinstance(ref_ctx, list):
                ref_ctx = [ref_ctx]
            owned = []
            for rc in ref_ctx:
                # OwnedReferenceSubsettingContext may be a dotted chain.
                for ors_ctx in _collect_owned_contexts(
                    rc.children, 'OwnedReferenceSubsettingContext',
                    ('ReferencesContext',),
                ):
                    segs = _dotted_segments(ors_ctx)
                    if segs:
                        owned.append(_emit_owned_chain(
                            'OwnedReferenceSubsetting', 'referencedFeature', segs))
            if owned:
                specialization_list.append({
                    "name": "FeatureSpecialization",
                    "ownedRelationship": {
                        "name": "References",
                        "ownedRelationship": owned
                    }
                })

    if not specialization_list:
        return None

    return {
        "name": "FeatureSpecializationPart",
        "specialization": specialization_list,
        "specialization2": None,
        "multiplicity": None,
        "multiplicity2": None
    }


def _make_nested_analysis_case_usage_dict(ctx, prefix=None):
    """Create an AnalysisCaseUsage dict for nested usage."""
    if ctx is None:
        return None
    
    # Extract name and specialization from constraintUsageDeclaration
    name = None
    shortname = None
    specialization = None
    
    if hasattr(ctx, 'constraintUsageDeclaration') and ctx.constraintUsageDeclaration():
        cud = ctx.constraintUsageDeclaration()
        if hasattr(cud, 'usageDeclaration') and cud.usageDeclaration():
            ud = cud.usageDeclaration()
            if hasattr(ud, 'identification') and ud.identification():
                ident = ud.identification()
                if hasattr(ident, 'name'):
                    name_list = ident.name()
                    if name_list and isinstance(name_list, list):
                        if len(name_list) == 2:
                            shortname = name_list[0].getText()
                            name = name_list[1].getText()
                        elif len(name_list) == 1:
                            name_text = name_list[0].getText()
                            name, shortname = _extract_name_shortname(name_text)
        
        # Extract specialization (typing) from constraintUsageDeclaration
        typed_by = _get_action_usage_typed_by(cud)
        if typed_by:
            specialization = _build_specialization(typed_by)
    
    occ_prefix = _get_occurrence_usage_prefix(ctx) if ctx else None
    
    # Get body items from caseBody
    body_items = []
    if hasattr(ctx, 'caseBody') and ctx.caseBody():
        cb = ctx.caseBody()
        body_items = _visit_case_body_items(cb)
    
    return {
        "name": "UsageElement",
        "ownedRelatedElement": {
            "name": "OccurrenceUsageElement",
            "ownedRelatedElement": {
                "name": "BehaviorUsageElement",
                "ownedRelationship": {
                    "name": "AnalysisCaseUsage",
                    "prefix": occ_prefix or prefix,
                    "declaration": {
                        "name": "CalculationUsageDeclaration",
                        "declaration": {
                            "name": "UsageDeclaration",
                            "declaration": {
                                "name": "FeatureDeclaration",
                                "identification": {
                                    "name": "Identification",
                                    "declaredShortName": shortname,
                                    "declaredName": name
                                },
                                "specialization": specialization
                            }
                        },
                        "valuepart": None
                    },
                    "body": {
                        "name": "CaseBody",
                        "item": body_items
                    }
                }
            }
        }
    }


def _make_nested_case_usage_dict(ctx, prefix=None):
    """Create a CaseUsage dict for nested usage."""
    if ctx is None:
        return None
    
    name, shortname = _get_usage_identification(ctx)
    occ_prefix = _get_occurrence_usage_prefix(ctx) if ctx else None
    specialization = _build_full_specialization_from_ctx(ctx)
    
    # Get body items from caseBody
    body_items = []
    if hasattr(ctx, 'caseBody') and ctx.caseBody():
        cb = ctx.caseBody()
        body_items = _visit_case_body_items(cb)
    
    return {
        "name": "UsageElement",
        "ownedRelatedElement": {
            "name": "OccurrenceUsageElement",
            "ownedRelatedElement": {
                "name": "BehaviorUsageElement",
                "ownedRelationship": {
                    "name": "CaseUsage",
                    "prefix": occ_prefix or prefix,
                    "declaration": {
                        "name": "CalculationUsageDeclaration",
                        "declaration": {
                            "name": "UsageDeclaration",
                            "declaration": {
                                "name": "FeatureDeclaration",
                                "identification": {
                                    "name": "Identification",
                                    "declaredShortName": shortname,
                                    "declaredName": name
                                },
                                "specialization": specialization
                            }
                        },
                        "valuepart": None
                    },
                    "body": {
                        "name": "CaseBody",
                        "item": body_items
                    }
                }
            }
        }
    }


def _visit_case_body_items(case_body):
    """Visit case body items and return a list of dicts."""
    if case_body is None:
        return []
    
    items = []
    if hasattr(case_body, 'caseBodyItem') and case_body.caseBodyItem():
        cbi_list = case_body.caseBodyItem()
        if not isinstance(cbi_list, list):
            cbi_list = [cbi_list]
        for cbi in cbi_list:
            item_dict = _visit_case_body_item(cbi)
            if item_dict:
                items.append(item_dict)
    
    return items


def _visit_case_body_item(cbi):
    """Visit a single case body item and return a dict."""
    if cbi is None:
        return None
    
    # Handle subjectMember
    if hasattr(cbi, 'subjectMember') and cbi.subjectMember():
        sm = cbi.subjectMember()
        if isinstance(sm, list):
            sm = sm[0]
        if sm:
            inner = _visit_subject_member_dict(sm)
            if inner:
                return {
                    "name": "CaseBodyItem",
                    "item": None,
                    "ownedRelationship": inner
                }
    
    # Handle objectiveMember
    if hasattr(cbi, 'objectiveMember') and cbi.objectiveMember():
        om = cbi.objectiveMember()
        if isinstance(om, list):
            om = om[0]
        if om:
            inner = _visit_objective_member_dict(om)
            if inner:
                return {
                    "name": "CaseBodyItem",
                    "item": None,
                    "ownedRelationship": inner
                }
    
    # Handle returnParameterMember
    if hasattr(cbi, 'returnParameterMember') and cbi.returnParameterMember():
        rpm = cbi.returnParameterMember()
        if isinstance(rpm, list):
            rpm = rpm[0]
        if rpm:
            inner = _visit_return_parameter_member(rpm)
            if inner:
                return {
                    "name": "CaseBodyItem",
                    "item": inner,
                    "ownedRelationship": None
                }
    
    # Handle actionBodyItem (for nested calc/action usages)
    if hasattr(cbi, 'actionBodyItem') and cbi.actionBodyItem():
        abi = cbi.actionBodyItem()
        if isinstance(abi, list):
            abi = abi[0]
        if abi:
            inner = _visit_action_body_item(abi)
            if inner:
                return {
                    "name": "CaseBodyItem",
                    "item": inner,
                    "ownedRelationship": None
                }
    
    # Handle nonOccurrenceUsageMember (in/out params)
    if hasattr(cbi, 'nonOccurrenceUsageMember') and cbi.nonOccurrenceUsageMember():
        nom = cbi.nonOccurrenceUsageMember()
        if isinstance(nom, list):
            nom = nom[0]
        if nom:
            inner = _visit_non_occurrence_usage_member(nom)
            if inner:
                return {
                    "name": "CaseBodyItem",
                    "item": None,
                    "ownedRelationship": inner
                }
    
    return None


def _visit_non_occurrence_usage_member(nom):
    """Visit a nonOccurrenceUsageMember and return a dict."""
    if nom is None:
        return None
    
    prefix = None
    if hasattr(nom, 'memberPrefix') and nom.memberPrefix():
        mp = nom.memberPrefix()
        if hasattr(mp, 'visibilityIndicator') and mp.visibilityIndicator():
            prefix = {
                "name": "MemberPrefix",
                "visibility": _visit_visibility_indicator_dict(mp.visibilityIndicator())
            }
    
    # Find nonOccurrenceUsageElement
    element = None
    if hasattr(nom, 'nonOccurrenceUsageElement') and nom.nonOccurrenceUsageElement():
        non_occ = nom.nonOccurrenceUsageElement()
        inner = _visit_nested_non_occurrence_usage(non_occ)
        if inner:
            if inner.get("name") == "NonOccurrenceUsageElement":
                element = inner
            else:
                element = {
                    "name": "NonOccurrenceUsageElement",
                    "ownedRelatedElement": inner
                }
    
    return {
        "name": "NonOccurrenceUsageMember",
        "prefix": prefix,
        "ownedRelatedElement": element
    }


__all__ = ['parse_to_dict']