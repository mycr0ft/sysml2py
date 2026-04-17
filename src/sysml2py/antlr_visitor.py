#!/usr/bin/env python3
"""
ANTLR4 to dictionary converter for SysML v2.0.

This module converts the ANTLR4 parse tree to the same dictionary format
that the textX parser produces, allowing use with the existing class hierarchy.
"""
import uuid


def parse_to_dict(source):
    """Parse SysML source and return a dictionary (textX-compatible format).
    
    Parameters
    ----------
    source : str or file-like
        Either a string containing SysML v2.0 code, or a file object.
    
    Returns
    -------
    dict
        A dictionary representation of the SysML model in textX format.
    """
    from sysml2py import antlr_parser
    
    tree = antlr_parser.parse(source)
    return _visit_package_dict(tree)


def _visit_package_dict(tree):
    """Visit a package context and return a dictionary."""
    # Get package name from identification
    pkg_name = "Package"
    if tree.packageDeclaration():
        decl = tree.packageDeclaration()
        if hasattr(decl, 'identification'):
            ident = decl.identification()
            if ident and hasattr(ident, 'name'):
                name_list = ident.name()
                if name_list and isinstance(name_list, list):
                    pkg_name = name_list[0].getText()
    
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
    
    # Build the complete package dictionary (matching textX format)
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
                                "declaredShortName": None,
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


def _visit_package_body_element_dict(elem_ctx):
    """Visit a package body element and return a dictionary."""
    if not hasattr(elem_ctx, 'packageMember'):
        return None
    
    member = elem_ctx.packageMember()
    if not member:
        return None
    
    # Get prefix if present
    prefix = None
    if hasattr(member, 'memberPrefix'):
        mp = member.memberPrefix()
        if mp:
            if hasattr(mp, 'redefines'):
                prefix = 'redefines'
            elif hasattr(mp, 'conjugated'):
                prefix = 'conjugated'
    
    # Check if it's a definition or usage element
    if hasattr(member, 'definitionElement'):
        def_elem = member.definitionElement()
        if def_elem:
            return _visit_definition_element_dict(def_elem, prefix)
    elif hasattr(member, 'usageElement'):
        usage_elem = member.usageElement()
        if usage_elem:
            return _visit_usage_element_dict(usage_elem, prefix)
    
    return None


def _visit_definition_element_dict(def_elem_ctx, prefix=None):
    """Visit a definition element context and return a dictionary."""
    # Try different definition types
    if hasattr(def_elem_ctx, 'partDefinition') and def_elem_ctx.partDefinition():
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
    elif hasattr(def_elem_ctx, 'interfaceDefinition') and def_elem_ctx.interfaceDefinition():
        ctx = def_elem_ctx.interfaceDefinition()
        return _make_interface_definition_dict(ctx, prefix)
    
    return None


def _make_part_definition_dict(ctx, prefix=None):
    """Create a PartDefinition dictionary in textX format."""
    # Get name
    name = "Unknown"
    if hasattr(ctx, 'definition'):
        defn = ctx.definition()
        if defn and hasattr(defn, 'definitionDeclaration'):
            decl = defn.definitionDeclaration()
            if decl and hasattr(decl, 'identification'):
                ident = decl.identification()
                if ident and hasattr(ident, 'name'):
                    name_list = ident.name()
                    if name_list and isinstance(name_list, list):
                        name = name_list[0].getText()
    
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
        "prefix": None,
        "ownedRelatedElement": {
            "name": "DefinitionElement",
            "ownedRelatedElement": {
                "name": "PartDefinition",
                "prefix": prefix,
                "definition": {
                    "name": "Definition",
                    "declaration": {
                        "name": "DefinitionDeclaration",
                        "identification": {
                            "name": "Identification",
                            "declaredShortName": None,
                            "declaredName": name
                        },
                        "subclassificationpart": None
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


def _make_attribute_definition_dict(ctx, prefix=None):
    """Create an AttributeDefinition dictionary in textX format."""
    name = "Unknown"
    if hasattr(ctx, 'definition'):
        defn = ctx.definition()
        if defn and hasattr(defn, 'definitionDeclaration'):
            decl = defn.definitionDeclaration()
            if decl and hasattr(decl, 'identification'):
                ident = decl.identification()
                if ident and hasattr(ident, 'name'):
                    name_list = ident.name()
                    if name_list and isinstance(name_list, list):
                        name = name_list[0].getText()
    
    return {
        "name": "PackageMember",
        "prefix": None,
        "ownedRelatedElement": {
            "name": "DefinitionElement",
            "ownedRelatedElement": {
                "name": "AttributeDefinition",
                "prefix": prefix,
                "definition": {
                    "name": "Definition",
                    "declaration": {
                        "name": "DefinitionDeclaration",
                        "identification": {
                            "name": "Identification",
                            "declaredShortName": None,
                            "declaredName": name
                        },
                        "subclassificationpart": None
                    },
                    "body": {
                        "name": "DefinitionBody",
                        "ownedRelatedElement": []
                    }
                }
            }
        }
    }


def _make_port_definition_dict(ctx, prefix=None):
    """Create a PortDefinition dictionary in textX format."""
    name = "Unknown"
    if hasattr(ctx, 'definition'):
        defn = ctx.definition()
        if defn and hasattr(defn, 'definitionDeclaration'):
            decl = defn.definitionDeclaration()
            if decl and hasattr(decl, 'identification'):
                ident = decl.identification()
                if ident and hasattr(ident, 'name'):
                    name_list = ident.name()
                    if name_list and isinstance(name_list, list):
                        name = name_list[0].getText()
    
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
        "prefix": None,
        "ownedRelatedElement": {
            "name": "DefinitionElement",
            "ownedRelatedElement": {
                "name": "PortDefinition",
                "prefix": prefix,
                "definition": {
                    "name": "Definition",
                    "declaration": {
                        "name": "DefinitionDeclaration",
                        "identification": {
                            "name": "Identification",
                            "declaredShortName": None,
                            "declaredName": name
                        },
                        "subclassificationpart": None
                    },
                    "body": {
                        "name": "DefinitionBody",
                        "ownedRelatedElement": body_items
                    }
                }
            }
        }
    }


def _make_requirement_definition_dict(ctx, prefix=None):
    """Create a RequirementDefinition dictionary in textX format."""
    name = "Requirement_" + str(uuid.uuid4())[:8]
    shortname = None
    
    # Get name from definition declaration
    if hasattr(ctx, 'definitionDeclaration'):
        decl = ctx.definitionDeclaration()
        if decl and hasattr(decl, 'identification'):
            ident = decl.identification()
            if ident and hasattr(ident, 'name'):
                name_list = ident.name()
                if name_list and isinstance(name_list, list):
                    name = name_list[0].getText()
            if ident and hasattr(ident, 'shortName'):
                short_list = ident.shortName()
                if short_list and isinstance(short_list, list):
                    shortname = short_list[0].getText()
    
    # Note: RequirementDefinition uses 'declaration' not 'definition'
    return {
        "name": "PackageMember",
        "prefix": None,
        "ownedRelatedElement": {
            "name": "DefinitionElement",
            "ownedRelatedElement": {
                "name": "RequirementDefinition",
                "prefix": prefix,
                "declaration": {
                    "name": "DefinitionDeclaration",
                    "identification": {
                        "name": "Identification",
                        "declaredShortName": shortname,
                        "declaredName": name
                    },
                    "subclassificationpart": None
                },
                "body": {
                    "name": "RequirementBody",
                    "item": []
                }
            }
        }
    }


def _make_use_case_definition_dict(ctx, prefix=None):
    """Create a UseCaseDefinition dictionary in textX format."""
    name = "UseCase_" + str(uuid.uuid4())[:8]
    shortname = None
    
    # Get name from definition declaration
    if hasattr(ctx, 'definitionDeclaration'):
        decl = ctx.definitionDeclaration()
        if decl and hasattr(decl, 'identification'):
            ident = decl.identification()
            if ident and hasattr(ident, 'name'):
                name_list = ident.name()
                if name_list and isinstance(name_list, list):
                    name = name_list[0].getText()
            if ident and hasattr(ident, 'shortName'):
                short_list = ident.shortName()
                if short_list and isinstance(short_list, list):
                    shortname = short_list[0].getText()
    
    # Note: UseCaseDefinition uses 'declaration' not 'definition'
    return {
        "name": "PackageMember",
        "prefix": None,
        "ownedRelatedElement": {
            "name": "DefinitionElement",
            "ownedRelatedElement": {
                "name": "UseCaseDefinition",
                "prefix": prefix,
                "declaration": {
                    "name": "DefinitionDeclaration",
                    "identification": {
                        "name": "Identification",
                        "declaredShortName": shortname,
                        "declaredName": name
                    },
                    "subclassificationpart": None
                },
                "body": {
                    "name": "CaseBody",
                    "item": [],
                    "ownedRelationship": None
                }
            }
        }
    }


def _make_interface_definition_dict(ctx, prefix=None):
    """Create an InterfaceDefinition dictionary in textX format."""
    name = "Interface_" + str(uuid.uuid4())[:8]
    
    return {
        "name": "PackageMember",
        "prefix": None,
        "ownedRelatedElement": {
            "name": "DefinitionElement",
            "ownedRelatedElement": {
                "name": "InterfaceDefinition",
                "prefix": prefix,
                "definition": {
                    "name": "Definition",
                    "declaration": {
                        "name": "DefinitionDeclaration",
                        "identification": {
                            "name": "Identification",
                            "declaredShortName": None,
                            "declaredName": name
                        },
                        "subclassificationpart": None
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
    """Visit a definition body and return list of body items."""
    if not body_ctx:
        return []
    
    items = []
    
    if hasattr(body_ctx, 'definitionBodyItem'):
        body_items = body_ctx.definitionBodyItem()
        if body_items:
            for item in body_items:
                item_dict = _visit_definition_body_item_dict(item)
                if item_dict:
                    items.append(item_dict)
    
    return items


def _visit_definition_body_item_dict(item_ctx):
    """Visit a definition body item and return a dictionary."""
    if not hasattr(item_ctx, 'ownedRelationship'):
        return None
    
    rels = item_ctx.ownedRelationship()
    if not rels:
        return None
    
    inner_elements = []
    
    for rel in rels:
        if hasattr(rel, 'ownedRelatedElement'):
            related = rel.ownedRelatedElement()
            if related:
                # Check what type of element this is
                if hasattr(related, 'definitionElement'):
                    def_elem = related.definitionElement()
                    if def_elem:
                        nested = _visit_nested_definition(def_elem)
                        if nested:
                            inner_elements.append(nested)
                elif hasattr(related, 'usageElement'):
                    usage_elem = related.usageElement()
                    if usage_elem:
                        usage_dict = _visit_nested_usage(usage_elem)
                        if usage_dict:
                            inner_elements.append(usage_dict)
    
    if not inner_elements:
        return None
    
    return {
        "name": "DefinitionBodyItem",
        "ownedRelationship": [
            {
                "name": "DefinitionMember",
                "prefix": None,
                "ownedRelatedElement": inner_elements
            }
        ]
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
    if hasattr(usage_elem_ctx, 'partUsage') and usage_elem_ctx.partUsage():
        ctx = usage_elem_ctx.partUsage()
        name = "Part"
        if hasattr(ctx, 'identifier'):
            ids = ctx.identifier()
            if isinstance(ids, list) and ids:
                name = ids[0].getText()
        return {
            "name": "UsageElement",
            "ownedRelatedElement": {
                "name": "PartUsage",
                "prefix": None,
                "usage": {
                    "name": "Usage",
                    "declaration": {
                        "name": "UsageDeclaration",
                        "identification": {
                            "name": "Identification",
                            "declaredShortName": None,
                            "declaredName": name
                        }
                    },
                    "body": {
                        "name": "UsageBody",
                        "ownedRelationship": []
                    }
                }
            }
        }
    elif hasattr(usage_elem_ctx, 'attributeUsage') and usage_elem_ctx.attributeUsage():
        ctx = usage_elem_ctx.attributeUsage()
        name = "Attribute"
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
                        "identification": {
                            "name": "Identification",
                            "declaredShortName": None,
                            "declaredName": name
                        }
                    },
                    "body": {
                        "name": "UsageBody",
                        "ownedRelationship": []
                    }
                }
            }
        }
    
    return None


def _visit_usage_element_dict(usage_elem_ctx, prefix=None):
    """Visit a usage element context and return a dictionary."""
    # Try different usage types
    if hasattr(usage_elem_ctx, 'partUsage') and usage_elem_ctx.partUsage():
        ctx = usage_elem_ctx.partUsage()
        name = "Part"
        if hasattr(ctx, 'identifier'):
            ids = ctx.identifier()
            if isinstance(ids, list) and ids:
                name = ids[0].getText()
        return {
            "name": "PackageMember",
            "prefix": None,
            "ownedRelatedElement": {
                "name": "UsageElement",
                "ownedRelatedElement": {
                    "name": "PartUsage",
                    "prefix": prefix,
                    "usage": {
                        "name": "Usage",
                        "declaration": {
                            "name": "UsageDeclaration",
                            "identification": {
                                "name": "Identification",
                                "declaredShortName": None,
                                "declaredName": name
                            }
                        },
                        "body": {
                            "name": "UsageBody",
                            "ownedRelationship": []
                        }
                    }
                }
            }
        }
    elif hasattr(usage_elem_ctx, 'attributeUsage') and usage_elem_ctx.attributeUsage():
        ctx = usage_elem_ctx.attributeUsage()
        name = "Attribute"
        if hasattr(ctx, 'identifier'):
            ids = ctx.identifier()
            if isinstance(ids, list) and ids:
                name = ids[0].getText()
        return {
            "name": "PackageMember",
            "prefix": None,
            "ownedRelatedElement": {
                "name": "UsageElement",
                "ownedRelatedElement": {
                    "name": "AttributeUsage",
                    "prefix": prefix,
                    "usage": {
                        "name": "Usage",
                        "declaration": {
                            "name": "UsageDeclaration",
                            "identification": {
                                "name": "Identification",
                                "declaredShortName": None,
                                "declaredName": name
                            }
                        },
                        "body": {
                            "name": "UsageBody",
                            "ownedRelationship": []
                        }
                    }
                }
            }
        }
    
    return None


__all__ = ['parse_to_dict']