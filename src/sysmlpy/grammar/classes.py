#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Jun  3 12:37:27 2023

@author: mycr0ft
"""

import json


def valid_definition(definition, name):
    if isinstance(definition, dict):
        if "name" in definition:
            if definition["name"] == name:
                return True
            else:
                print(definition["name"])  # pragma: no cover
                raise ValueError(
                    "The name of the element did not match."
                )  # pragma: no cover

        else:
            raise AttributeError("This does not seem to be valid.")  # pragma: no cover
    else:  # pragma: no cover
        print("------------")
        print("\n\nDefinition: {}".format(definition))
        raise TypeError("This does not seem to be valid.")


def beautify(string):
    level = 0
    lines = string.split("\n")
    ns = []
    # print(lines)
    for line in lines:
        line = line.rstrip()
        if line == "}":
            level += -1

        ns.append(level * "   " + line)
        # print("\n\n\n\n-----\n{}|\n".format(line))
        if len(line) > 0:
            if line[-1] == "{":
                # Last character is new bracket
                level += 1

    return "\n".join(ns)


class RootNamespace:
    def __init__(self, definition):
        self.children = []
        try:
            if valid_definition(definition, "PackageBodyElement"):
                # This is a SysML Element
                self.load_package_body(definition["ownedRelationship"])
        except ValueError:
            try:
                if valid_definition(definition, "NamespaceBodyElement"):
                    # This is a KerML Element
                    pass
            except ValueError:  # pragma: no cover
                print(definition)
                raise ValueError("Not expecting any other root node names.")

    def load_package_body(self, definition):
        for member in definition:
            if isinstance(member, dict):
                # Options here are PackageMember, ElementFilterMember, AliasMember, Import
                if member["name"] == "PackageMember":
                    memberclass = PackageMember(member)
                elif member["name"] == "ElementFilterMember":
                    pass  # pragma: no cover
                elif member["name"] == "AliasMember":
                    memberclass = AliasMember(member)
                elif member["name"] == "Import":
                    memberclass = Import(member)
                else:
                    print(member["name"])  # pragma: no cover
                    raise AttributeError("Error")  # pragma: no cover

                self.children.append(memberclass)
            else:
                print(member)  # pragma: no cover
                raise TypeError(
                    "Invalid definition, member was not type dict"
                )  # pragma: no cover

    def dump(self):
        output = []
        for child in self.children:
            output.append(child.dump())
        return beautify("\n".join(output))

    def get_definition(self):
        # Root namespace can be either PackageBodyElement (SysML) or NamespaceBodyElement (KerML)
        # Default to PackageBodyElement for SysML documents
        output = {
            "name": "PackageBodyElement",
            "ownedRelationship": [],
        }
        for member in self.children:
            output["ownedRelationship"].append(member.get_definition())
        return output


class DefinitionElement:
    def __init__(self, definition):
        self.children = []
        if valid_definition(definition, "DefinitionElement"):
            # This is a SysML Element
            if isinstance(definition["ownedRelatedElement"], str):
                print(f"DefinitionElement string element: {definition['ownedRelatedElement']}")  # pragma: no cover
                return

            de = definition["ownedRelatedElement"]["name"]
            if de == "Package":
                self.children.append(Package(definition["ownedRelatedElement"]))
            elif de == "PartDefinition":
                self.children.append(PartDefinition(definition["ownedRelatedElement"]))
            elif de == "AttributeDefinition":
                self.children.append(
                    AttributeDefinition(definition["ownedRelatedElement"])
                )
            elif de == "AnnotatingElement":
                self.children.append(
                    AnnotatingElement(definition["ownedRelatedElement"])
                )

            elif de == "EnumerationDefinition":
                self.children.append(
                    EnumerationDefinition(definition["ownedRelatedElement"])
                )
            elif de == "ItemDefinition":
                self.children.append(ItemDefinition(definition["ownedRelatedElement"]))
            elif de == "ConnectionDefinition":
                self.children.append(
                    ConnectionDefinition(definition["ownedRelatedElement"])
                )
            elif de == "PortDefinition":
                self.children.append(PortDefinition(definition["ownedRelatedElement"]))
            elif de == "InterfaceDefinition":
                self.children.append(
                    InterfaceDefinition(definition["ownedRelatedElement"])
                )
            elif de == "FlowConnectionDefinition":
                self.children.append(
                    FlowConnectionDefinition(definition["ownedRelatedElement"])
                )
            elif de == "ActionDefinition":
                self.children.append(
                    ActionDefinition(definition["ownedRelatedElement"])
                )
            elif de == "CalculationDefinition":
                self.children.append(
                    CalculationDefinition(definition["ownedRelatedElement"])
                )
            elif de == "StateDefinition":
                self.children.append(StateDefinition(definition["ownedRelatedElement"]))
            elif de == "ConstraintDefinition":
                self.children.append(
                    ConstraintDefinition(definition["ownedRelatedElement"])
                )
            elif de == "RequirementDefinition":
                self.children.append(
                    RequirementDefinition(definition["ownedRelatedElement"])
                )
            elif de == "AnalysisCaseDefinition":
                self.children.append(
                    AnalysisCaseDefinition(definition["ownedRelatedElement"])
                )
            elif de == "UseCaseDefinition":
                self.children.append(
                    UseCaseDefinition(definition["ownedRelatedElement"])
                )
            elif de == "AllocationDefinition":
                self.children.append(
                    AllocationDefinition(definition["ownedRelatedElement"])
                )
            elif de == "MetadataDefinition":
                self.children.append(
                    MetadataDefinition(definition["ownedRelatedElement"])
                )
            elif de == "RenderingDefinition":
                self.children.append(
                    RenderingDefinition(definition["ownedRelatedElement"])
                )
            elif de == "IndividualDefinition":
                self.children.append(
                    IndividualDefinition(definition["ownedRelatedElement"])
                )
            elif de == "FlowDefinition":
                self.children.append(
                    FlowDefinition(definition["ownedRelatedElement"])
                )
            elif de == "ViewDefinition":
                self.children.append(
                    ViewDefinition(definition["ownedRelatedElement"])
                )
            elif de == "ViewpointDefinition":
                self.children.append(
                    ViewpointDefinition(definition["ownedRelatedElement"])
                )
            elif de == "ConcernDefinition":
                self.children.append(
                    ConcernDefinition(definition["ownedRelatedElement"])
                )
            elif de == "CaseDefinition":
                self.children.append(
                    CaseDefinition(definition["ownedRelatedElement"])
                )
            elif de == "VerificationCaseDefinition":
                self.children.append(
                    VerificationCaseDefinition(definition["ownedRelatedElement"])
                )
            elif de == "RequirementUsage":
                self.children.append(
                    RequirementUsage(definition["ownedRelatedElement"])
                )
            elif de == "SatisfyRequirementUsage":
                self.children.append(
                    SatisfyRequirementUsage(definition["ownedRelatedElement"])
                )
            elif de == "InterfaceUsage":
                self.children.append(
                    InterfaceUsage(definition["ownedRelatedElement"])
                )
            elif de == "Dependency":
                # Issue #4: dependency statements were silently dropped
                # because no visitor dispatch produced a Dependency dict and
                # no DefinitionElement branch constructed it.
                self.children.append(Dependency(definition["ownedRelatedElement"]))
            elif de == "LibraryPackage":
                # `standard library package Foo { ... }` shares the same
                # {identification, body} shape as `package Foo { ... }` plus
                # an isStandardLibrary flag. Reuse Package; the flag is read
                # from the dict in Package.__init__.
                self.children.append(Package(definition["ownedRelatedElement"]))
            else:
                print(f"Unknown DefinitionElement type: {de}")  # pragma: no cover

    def dump(self):
        output = []
        for child in self.children:
            output.append(child.dump())

        return " ".join(filter(None, (output)))

    def get_definition(self):
        output = {"name": self.__class__.__name__, "ownedRelatedElement": []}

        for item in self.children:
            output["ownedRelatedElement"] = item.get_definition()
        return output


class AnalysisCaseDefinition:
    # AnalysisCaseDefinition :
    # 	prefix=OccurrenceDefinitionPrefix AnalysisCaseDefKeyword
    #   declaration=DefinitionDeclaration body=CaseBody
    # ;
    def __init__(self, definition=None):
        self.prefix = None
        self.keyword = "analysis def"
        self.declaration = None
        self.body = None
        if definition is not None:
            if valid_definition(definition, self.__class__.__name__):
                if definition["prefix"] is not None:
                    self.prefix = OccurrenceDefinitionPrefix(definition["prefix"])
                if definition["declaration"] is not None:
                    self.declaration = DefinitionDeclaration(definition["declaration"])
                self.body = CaseBody(definition["body"])
        else:
            self.declaration = DefinitionDeclaration()
            self.body = CaseBody()

    def dump(self):
        output = []
        if self.prefix is not None:
            output.append(self.prefix.dump())
        output.append(self.keyword)
        if self.declaration is not None:
            output.append(self.declaration.dump())
        output.append(self.body.dump())
        return " ".join(output)

    def get_definition(self):
        output = {"name": self.__class__.__name__, "prefix": None, "declaration": None}
        if self.prefix is not None:
            output["prefix"] = self.prefix.get_definition()
        if self.declaration is not None:
            output["declaration"] = self.declaration.get_definition()
        output["body"] = self.body.get_definition() if self.body else None
        return output


class UseCaseDefinition:
    # UseCaseDefinition :
    # 	OccurrenceDefinitionPrefix UseCaseDefKeyword DefinitionDeclaration CaseBody
    # ;
    def __init__(self, definition=None):
        self.prefix = None
        self.keyword = "use case def"
        self.declaration = None
        if definition is not None:
            if valid_definition(definition, self.__class__.__name__):
                if definition["prefix"] is not None:
                    self.prefix = OccurrenceDefinitionPrefix(definition["prefix"])
                if definition["declaration"] is not None:
                    self.declaration = DefinitionDeclaration(definition["declaration"])
                self.body = CaseBody(definition["body"])
        else:
            self.declaration = DefinitionDeclaration()
            self.body = CaseBody(None)

    def dump(self):
        output = []
        if self.prefix is not None:
            output.append(self.prefix.dump())
        output.append(self.keyword)
        if self.declaration is not None:
            output.append(self.declaration.dump())
        output.append(self.body.dump())
        return " ".join(output)

    def get_definition(self):
        output = {
            "name": self.__class__.__name__,
            "prefix": None,
        }
        if self.prefix is not None:
            output["prefix"] = self.prefix.get_definition()
        if self.declaration is not None:
            output["declaration"] = self.declaration.get_definition()
        else:
            output["declaration"] = None
        output["body"] = self.body.get_definition()
        return output


class UseCaseUsage:
    # UseCaseUsage :
    # 	OccurrenceUsagePrefix UseCaseUsageKeyword CalculationUsageDeclaration CaseBody
    # ;
    def __init__(self, definition=None):
        self.prefix = None
        self.keyword = "use case"
        if definition is not None:
            if valid_definition(definition, self.__class__.__name__):
                if definition["prefix"] is not None:
                    self.prefix = OccurrenceUsagePrefix(definition["prefix"])
                self.declaration = CalculationUsageDeclaration(definition["declaration"])
                self.body = CaseBody(definition["body"])
        else:
            self.declaration = CalculationUsageDeclaration(None)
            self.body = CaseBody(None)

    def dump(self):
        output = []
        if self.prefix is not None:
            output.append(self.prefix.dump())
        output.append(self.keyword)
        output.append(self.declaration.dump())
        output.append(self.body.dump())
        return " ".join(output)

    def get_definition(self):
        output = {
            "name": self.__class__.__name__,
            "prefix": None,
        }
        if self.prefix is not None:
            output["prefix"] = self.prefix.get_definition()
        output["declaration"] = self.declaration.get_definition()
        output["body"] = self.body.get_definition()
        return output


class CaseBody:
    def __init__(self, definition=None):
        self.items = []
        self.child = None
        if definition is not None:
            if valid_definition(definition, self.__class__.__name__):
                if "item" in definition:
                    for item in definition["item"]:
                        self.items.append(CaseBodyItem(item))

                if definition.get("ownedRelationship") is not None:
                    self.child = ResultExpressionMember(definition["ownedRelationship"])

    def dump(self):
        if len(self.items) == 0:
            return ";"
        else:
            if self.child is not None:
                output = [self.child.dump()]
            else:
                output = [None]
            return (
                "{\n"
                + "\n".join(
                    filter(None, [child.dump() for child in self.items] + output)
                )
                + "\n}"
            )

    def get_definition(self):
        result = {"name": self.__class__.__name__, "item": [item.get_definition() for item in self.items]}
        if self.child is not None:
            result["ownedRelationship"] = self.child.get_definition()
        else:
            result["ownedRelationship"] = None
        return result


class CaseBodyItem:
    #  CaseBodyItem :
    # 	  ownedRelationship = CalculationBodyItem
    # 	| ownedRelationship = SubjectMember
    # 	| ownedRelationship = ActorMember
    # 	| ownedRelationship = ObjectiveMember
    #   | actionBodyItem
    #   | returnParameterMember
    # ;
    def __init__(self, definition):
        self.child = None
        if definition is not None and valid_definition(definition, self.__class__.__name__):
            if "ownedRelationship" in definition and definition["ownedRelationship"] is not None:
                child = definition["ownedRelationship"]
                name = child["name"]
                if name == "CalculationBodyItem":
                    self.child = CalculationBodyItem(child)
                elif name == "SubjectMember":
                    self.child = SubjectMember(child)
                elif name == "ActorMember":
                    self.child = ActorMember(child)
                elif name == "ObjectiveMember":
                    self.child = ObjectiveMember(child)
                else:  # pragma: no cover
                    raise ValueError("Invalid child name")
            elif "item" in definition:
                item = definition["item"]
                if item is not None:
                    name = item.get("name")
                    if name == "ActionBodyItem":
                        self.child = ActionBodyItem(item)
                    elif name == "ReturnParameterMember":
                        self.child = ReturnParameterMember(item)

    def dump(self):
        if self.child is None:
            return ""
        return self.child.dump()

    def get_definition(self):
        if self.child is None:
            return {"name": self.__class__.__name__, "ownedRelationship": None, "item": None}
        child_name = self.child.__class__.__name__
        if child_name in ("ActionBodyItem", "ReturnParameterMember"):
            return {
                "name": self.__class__.__name__,
                "ownedRelationship": None,
                "item": self.child.get_definition()
            }
        return {
            "name": self.__class__.__name__,
            "ownedRelationship": self.child.get_definition()
        }


class ObjectiveMember:
    # ObjectiveMember :
    # 	prefix=MemberPrefix 'objective' ownedRelatedElement=ObjectiveRequirementUsage
    # ;
    def __init__(self, definition):
        self.prefix = None
        self.keyword = "objective"
        if valid_definition(definition, self.__class__.__name__):
            if definition["prefix"] is not None:
                self.prefix = MemberPrefix(definition["prefix"])
            self.child = ObjectiveRequirementUsage(definition["ownedRelatedElement"])

    def dump(self):
        if self.prefix is None:
            return " ".join([self.keyword, self.child.dump()])
        else:
            return " ".join([self.prefix.dump(), self.keyword, self.child.dump()])

    def get_definition(self):
        return {
            "name": self.__class__.__name__,
            "prefix": self.prefix.get_definition() if self.prefix else None,
            "ownedRelatedElement": self.child.get_definition() if self.child else None,
        }


class ObjectiveRequirementUsage:
    # ObjectiveRequirementUsage :
    # 	keyword+=UsageExtensionKeyword* declaration=CalculationUsageDeclaration body=RequirementBody
    # ;
    def __init__(self, definition):
        self.keyword = []
        if valid_definition(definition, self.__class__.__name__):
            for keyword in definition["keyword"]:
                self.keyword.append(UsageExtensionKeyword(keyword))
            self.declaration = CalculationUsageDeclaration(definition["declaration"])
            self.body = RequirementBody(definition["body"])

    def dump(self):
        output = []
        for keyword in self.keyword:
            output.append(keyword.dump())
        output.append(self.declaration.dump())
        output.append(self.body.dump())
        return " ".join(output)

    def get_definition(self):
        return {
            "name": self.__class__.__name__,
            "keyword": [k.get_definition() for k in self.keyword],
            "declaration": self.declaration.get_definition() if self.declaration else None,
            "body": self.body.get_definition() if self.body else None,
        }


class RequirementDefinition:
    # RequirementDefinition :
    # 	prefix=OccurrenceDefinitionPrefix RequirementDefKeyword
    #   declaration=DefinitionDeclaration body=RequirementBody
    # ;
    def __init__(self, definition=None):
        self.prefix = None
        self.keyword = "requirement def"
        self.declaration = None
        self.body = RequirementBody(None)
        if definition is not None and valid_definition(definition, self.__class__.__name__):
            if definition.get("prefix") is not None:
                prefix_name = definition["prefix"].get("name", "OccurrenceDefinitionPrefix")
                self.prefix = globals()[prefix_name](definition["prefix"])
            if definition.get("declaration") is not None:
                decl_def = definition["declaration"]
                if isinstance(decl_def, dict) and decl_def.get("name") == "DefinitionDeclaration":
                    self.declaration = DefinitionDeclaration(decl_def)
                else:
                    self.declaration = DefinitionDeclaration(None)
            if definition.get("body") is not None:
                self.body = RequirementBody(definition["body"])

    def dump(self):
        output = []
        if self.prefix is not None:
            output.append(self.prefix.dump())
        output.append(self.keyword)
        if self.declaration is not None:
            output.append(self.declaration.dump())
        output.append(self.body.dump())
        return " ".join(output)

    def get_definition(self):
        output = {"name": self.__class__.__name__, "prefix": None}
        if self.prefix is not None:
            output["prefix"] = self.prefix.get_definition()
        
        # RequirementDefinition uses 'declaration' directly
        output["declaration"] = self.declaration.get_definition() if self.declaration else None
        output["body"] = self.body.get_definition() if hasattr(self.body, 'get_definition') else {"name": "RequirementBody", "item": []}
        
        return output


class RequirementBody:
    def __init__(self, definition):
        self.items = []
        if definition is not None:
            if isinstance(definition, dict) and definition.get("name") == "RequirementBody":
                if "item" in definition:
                    for item in definition["item"]:
                        self.items.append(RequirementBodyItem(item))

    def dump(self):
        if len(self.items) == 0:
            return ";"
        else:
            return "{\n" + "\n".join([child.dump() for child in self.items]) + "\n}"

    def get_definition(self):
        return {
            "name": self.__class__.__name__,
            "item": [item.get_definition() for item in self.items]
        }


class RequirementBodyItem:
    # RequirementBodyItem :
    # 	  ownedRelationship = DefinitionBodyItem
    # 	| ownedRelationship = SubjectMember
    # 	| ownedRelationship = RequirementConstraintMember
    # 	| ownedRelationship = FramedConcernMember
    # 	| ownedRelationship = RequirementVerificationMember
    # 	| ownedRelationship = ActorMember
    # 	| ownedRelationship = StakeholderMember
    # ;
    def __init__(self, definition):
        self.child = None
        if definition is not None and valid_definition(definition, self.__class__.__name__):
            child = definition["ownedRelationship"]
            name = child["name"]
            if name == "DefinitionBodyItem":
                self.child = DefinitionBodyItem(child)
            elif name == "SubjectMember":
                self.child = SubjectMember(child)
            elif name == "RequirementConstraintMember":
                self.child = RequirementConstraintMember(child)
            elif name == "FramedConcernMember":
                self.child = FramedConcernMember(child)
            elif name == "RequirementVerificationMember":
                self.child = RequirementVerificationMember(child)
            elif name == "ActorMember":
                self.child = ActorMember(child)
            elif name == "StakeholderMember":
                self.child = StakeholderMember(child)
            else:  # pragma: no cover
                raise ValueError("Invalid child name")

    def dump(self):
        return self.child.dump()

    def get_definition(self):
        return {
            "name": self.__class__.__name__,
            "ownedRelationship": self.child.get_definition()
        }


class SubjectMember:
    # SubjectMember :
    # 	prefix=MemberPrefix ownedRelatedElement = SubjectUsage
    # ;
    def __init__(self, definition):
        self.prefix = None
        if valid_definition(definition, self.__class__.__name__):
            if definition["prefix"] is not None:
                self.prefix = MemberPrefix(definition["prefix"])
            self.child = SubjectUsage(definition["ownedRelatedElement"])

    def dump(self):
        if self.prefix is None:
            return self.child.dump()
        else:
            return " ".join([self.prefix.dump(), self.child.dump()])

    def get_definition(self):
        return {
            "name": self.__class__.__name__,
            "prefix": self.prefix.get_definition() if self.prefix else None,
            "ownedRelatedElement": self.child.get_definition() if self.child else None,
        }


class SubjectUsage:
    # SubjectUsage :
    # 	'subject' keyword+=UsageExtensionKeyword* usage=Usage
    # ;
    def __init__(self, definition):
        self.subject = "subject"
        self.keyword = []
        if valid_definition(definition, self.__class__.__name__):
            for keyword in definition["keyword"]:
                self.keyword.append(UsageExtensionKeyword(keyword))
            self.child = Usage(definition["usage"])

    def dump(self):
        parts = [self.subject]
        parts.extend([x.dump() for x in self.keyword])
        child_dump = self.child.dump()
        parts.append(child_dump)
        return " ".join(filter(None, parts))

    def get_definition(self):
        return {
            "name": self.__class__.__name__,
            "keyword": [k.get_definition() for k in self.keyword],
            "usage": self.child.get_definition() if self.child else None,
        }


class RequirementConstraintMember:
    # RequirementConstraintMember :
    # 	prefix=MemberPrefix kind = RequirementConstraintKind
    # 	ownedRelatedElement = RequirementConstraintUsage
    # ;
    def __init__(self, definition):
        self.prefix = None
        if valid_definition(definition, self.__class__.__name__):
            if definition["prefix"] is not None:
                self.prefix = MemberPrefix(definition["prefix"])
            self.kind = RequirementConstraintKind(definition["kind"])
            self.child = RequirementConstraintUsage(definition["ownedRelatedElement"])

    def dump(self):
        output = []
        if self.prefix is not None:
            output.append(self.prefix.dump())
        output.append(self.kind.dump())
        output.append(self.child.dump())
        return " ".join(output)

    def get_definition(self):
        return {
            "name": self.__class__.__name__,
            "prefix": self.prefix.get_definition() if self.prefix else None,
            "kind": self.kind.get_definition(),
            "ownedRelatedElement": self.child.get_definition(),
        }


class RequirementConstraintKind:
    #  RequirementConstraintKind :
    # 	assumption = 'assume' | requirement = 'require'
    # ;
    def __init__(self, definition):
        self.requirement = None
        if valid_definition(definition, self.__class__.__name__):
            assumption = definition.get("assumption")
            req_value = definition.get("requirement")
            if assumption == "assume" and not req_value:
                self.requirement = False
            elif not assumption and req_value == "require":
                self.requirement = True
            elif assumption or req_value:
                raise ValueError

    def dump(self):
        if self.requirement is not None:
            if self.requirement:
                return "require"
            else:
                return "assume"
        else:  # pragma: no cover
            raise ValueError

    def get_definition(self):
        return {
            "name": self.__class__.__name__,
            "assumption": "assume" if self.requirement is False else None,
            "requirement": "require" if self.requirement is True else None,
        }


class RequirementConstraintUsage:
    # RequirementConstraintUsage :
    #     (
    #       ownedRelationship = OwnedReferenceSubsetting fs+=FeatureSpecialization*
    #       body=RequirementBody
    #     )
    #     |
    #     (
    #       (
    #         keyword+=UsageExtensionKeyword* ConstraintUsageKeyword
    #         |
    #         keyword+=UsageExtensionKeyword+
    #       )
    #       declaration=CalculationUsageDeclaration body=CalculationBody
    #     )
    # ;
    def __init__(self, definition):
        self.reference = None
        if valid_definition(definition, self.__class__.__name__):
            if definition["ownedRelationship"] is not None:
                # Type 1
                self.reference = OwnedReferenceSubsetting(
                    definition["ownedRelationship"]
                )
                self.fs = []
                for child in definition["fs"]:
                    self.fs.append(FeatureSpecialization(child))
                self.body = RequirementBody(definition["body"])

            else:
                self.keyword = []
                self.declaration = None
                if len(definition["keyword2"]) == 0:
                    for keyword in definition["keyword1"]:
                        self.keyword.append(UsageExtensionKeyword(keyword))
                    self.constraint = "constraint"
                else:
                    for keyword in definition["keyword2"]:
                        self.keyword.append(UsageExtensionKeyword(keyword))
                    self.constraint = None
                if definition["declaration"] is not None:
                    self.declaration = CalculationUsageDeclaration(
                        definition["declaration"]
                    )
                self.body = CalculationBody(definition["body"])

    def dump(self):
        output = []
        if self.reference is not None:
            output.append(self.reference.dump())
            for fs in self.fs:
                output.append(fs.dump())
            output.append(self.body.dump())
        else:
            for keyword in self.keyword:
                output.append(keyword.dump())
            output.append(self.constraint)
            if self.declaration is not None:
                output.append(self.declaration.dump())
            output.append(self.body.dump())
        return " ".join(filter(None, output))

    def get_definition(self):
        output = {
            "name": self.__class__.__name__,
            "ownedRelationship": None,
            "fs": [],
            "body": None,
        }
        if self.reference is not None:
            output["ownedRelationship"] = self.reference.get_definition()
            output["fs"] = [fs.get_definition() for fs in self.fs]
            output["body"] = self.body.get_definition()
        else:
            output["keyword1"] = [kw.get_definition() for kw in self.keyword] if hasattr(self, 'keyword1') else []
            output["keyword2"] = []
            output["constraint"] = self.constraint
            output["declaration"] = self.declaration.get_definition() if self.declaration else None
            output["body"] = self.body.get_definition()
        return output


class ConstraintDefinition:
    # ConstraintDefinition :
    # 	prefix=OccurrenceDefinitionPrefix ConstraintDefKeyword declaration=DefinitionDeclaration body=CalculationBody
    # ;
    def __init__(self, definition=None):
        self.prefix = None
        self.keyword = "constraint def"
        if definition is not None:
            if valid_definition(definition, self.__class__.__name__):
                if definition["prefix"] is not None:
                    self.prefix = OccurrenceDefinitionPrefix(definition["prefix"])
                self.declaration = DefinitionDeclaration(definition["declaration"])
                self.body = CalculationBody(definition["body"])
        else:
            self.declaration = DefinitionDeclaration()
            self.body = CalculationBody()

    def dump(self):
        output = []
        if self.prefix is not None:
            output.append(self.prefix.dump())
        output.append(self.keyword)
        output.append(self.declaration.dump())
        output.append(self.body.dump())
        return " ".join(output)

    def get_definition(self):
        output = {"name": self.__class__.__name__, "prefix": None}
        if self.prefix is not None:
            output["prefix"] = self.prefix.get_definition()
        output["declaration"] = self.declaration.get_definition()
        output["body"] = self.body.get_definition()
        return output


class StateDefinition:
    def __init__(self, definition=None):
        self.prefix = None
        self.keyword = "state def"
        if definition is not None:
            if valid_definition(definition, self.__class__.__name__):
                if definition["prefix"] is not None:
                    self.prefix = OccurrenceDefinitionPrefix(definition["prefix"])

                self.declaration = DefinitionDeclaration(definition["declaration"])
                self.body = StateDefBody(definition["body"])
        else:
            self.declaration = DefinitionDeclaration()
            self.body = StateDefBody()

    def dump(self):
        output = []
        if self.prefix is not None:
            output.append(self.prefix.dump())
        output.append(self.keyword)
        output.append(self.declaration.dump())
        output.append(self.body.dump())
        return " ".join(output)

    def get_definition(self):
        output = {"name": self.__class__.__name__, "prefix": None}
        if self.prefix is not None:
            output["prefix"] = self.prefix.get_definition()
        output["declaration"] = self.declaration.get_definition()
        output["body"] = self.body.get_definition()
        return output


class StateDefBody:
    #     StateDefBody :
    # 	';' | ( isParallel ?= 'parallel' )? '{' part=StateBodyPart '}'
    # ;
    def __init__(self, definition=None):
        self.children = None
        self.isParallel = None
        if definition is not None:
            if valid_definition(definition, self.__class__.__name__):
                if definition.get("part") is not None:
                    self.children = StateBodyPart(definition["part"])
                    self.isParallel = definition.get("isParallel")

    def dump(self):
        if self.children is None:
            return ";"
        else:
            output = []
            if self.isParallel is not None:
                if self.isParallel:
                    output.append("parallel")

            output.append("{\n")
            output.append(self.children.dump())
            output.append("\n}")
            return " ".join(output)

    def get_definition(self):
        output = {"name": self.__class__.__name__, "part": None, "isParallel": self.isParallel}
        if self.children is not None:
            output["part"] = self.children.get_definition()
        return output


class StateBodyPart:
    def __init__(self, definition=None):
        self.children = []
        if definition is not None:
            if valid_definition(definition, self.__class__.__name__):
                for child in definition["item"]:
                    self.children.append(StateBodyItem(child))

    def dump(self):
        return "\n".join([x.dump() for x in self.children])

    def get_definition(self):
        output = {"name": self.__class__.__name__, "item": []}
        for child in self.children:
            output["item"].append(child.get_definition())
        return output


class SourceSuccessionMember:
    def __init__(self, definition=None):
        self.prefix = None
        self.child = None
        if definition is not None:
            if valid_definition(definition, self.__class__.__name__):
                if definition.get("prefix") is not None:
                    self.prefix = MemberPrefix(definition["prefix"])
                if definition.get("ownedRelatedElement") is not None:
                    self.child = SourceSuccession(definition["ownedRelatedElement"])

    def dump(self):
        output = []
        if self.child:
            output.append(self.child.dump())
        return " ".join(output)

    def get_definition(self):
        return {
            "name": self.__class__.__name__,
            "prefix": self.prefix.get_definition() if self.prefix else None,
            "ownedRelatedElement": self.child.get_definition() if self.child else None,
        }


class SourceSuccession:
    def __init__(self, definition=None):
        self.children = []
        if definition is not None:
            if valid_definition(definition, self.__class__.__name__):
                owned_rel = definition.get("ownedRelationship")
                if owned_rel:
                    if isinstance(owned_rel, list):
                        for child in owned_rel:
                            self.children.append(SourceEndMember(child))
                    else:
                        self.children.append(SourceEndMember(owned_rel))

    def dump(self):
        return "then " + " ".join([c.dump() for c in self.children])

    def get_definition(self):
        return {
            "name": self.__class__.__name__,
            "ownedRelationship": [c.get_definition() for c in self.children],
        }


class SourceEndMember:
    def __init__(self, definition=None):
        self.children = []
        if definition is not None:
            if valid_definition(definition, self.__class__.__name__):
                owned_rel = definition.get("ownedRelatedElement")
                if owned_rel:
                    if isinstance(owned_rel, list):
                        for child in owned_rel:
                            if child.get("name") == "BehaviorUsageElement":
                                self.children.append(BehaviorUsageElement(child))
                    else:
                        if owned_rel.get("name") == "BehaviorUsageElement":
                            self.children.append(BehaviorUsageElement(owned_rel))

    def dump(self):
        return " ".join([c.dump() for c in self.children])

    def get_definition(self):
        return {
            "name": self.__class__.__name__,
            "ownedRelatedElement": [c.get_definition() for c in self.children],
        }


class StateBodyItem:
    def __init__(self, definition=None):
        self.children = []
        if definition is not None:
            if valid_definition(definition, self.__class__.__name__):
                for child in definition["ownedRelationship"]:
                    self.children.append(globals()[child["name"]](child))

    def dump(self):
        return "\n".join([x.dump() for x in self.children])

    def get_definition(self):
        output = {"name": self.__class__.__name__, "ownedRelationship": []}
        for child in self.children:
            output["ownedRelationship"].append(child.get_definition())
        return output


class StateUsage:
    # prefix=OccurrenceUsagePrefix StateUsageKeyword
    # declaration=ActionUsageDeclaration body=StateUsageBody
    def __init__(self, definition=None):
        self.prefix = None
        self.keyword = "state"
        if definition is not None:
            if valid_definition(definition, self.__class__.__name__):
                if definition["prefix"] is not None:
                    self.prefix = OccurrenceUsagePrefix(definition["prefix"])
                self.declaration = ActionUsageDeclaration(definition["declaration"])
                self.body = StateUsageBody(definition["body"])
        else:
            self.declaration = ActionUsageDeclaration()
            self.body = StateUsageBody()

    def dump(self):
        output = []
        if self.prefix is not None:
            output.append(self.prefix.dump())
        output.append(self.keyword)
        output.append(self.declaration.dump())
        output.append(self.body.dump())
        return " ".join(output)

    def get_definition(self):
        output = {"name": self.__class__.__name__, "prefix": None}
        if self.prefix is not None:
            output["prefix"] = self.prefix.get_definition()
        output["declaration"] = self.declaration.get_definition()
        output["body"] = self.body.get_definition()
        return output


class StateUsageBody:
    def __init__(self, definition=None):
        if definition is not None:
            if valid_definition(definition, self.__class__.__name__):
                self.children = StateDefBody(definition["body"])
        else:
            self.children = StateDefBody()

    def dump(self):
        return self.children.dump()

    def get_definition(self):
        return {"name": self.__class__.__name__, "body": self.children.get_definition()}


class DoActionMember:
    # DoActionMember :
    # 	prefix=MemberPrefix DoActionKind ownedRelatedElement=StateActionUsage
    # ;
    def __init__(self, definition):
        self.prefix = None
        self.keyword = "do"
        self.children = None
        if valid_definition(definition, self.__class__.__name__):
            if definition["prefix"] is not None:
                self.prefix = MemberPrefix(definition["prefix"])

            related = definition["ownedRelatedElement"]
            if related is not None:
                cls_name = related.get("name", "StateActionUsage")
                if cls_name in globals():
                    self.children = globals()[cls_name](related)
                else:
                    self.children = StateActionUsage(related)

    def dump(self):
        output = []
        if self.prefix is not None:
            output.append(self.prefix.dump())
        if self.children is not None:
            output.append(self.keyword)
            output.append(self.children.dump())
        return " ".join(output)

    def get_definition(self):
        output = {
            "name": self.__class__.__name__,
            "prefix": None,
            "ownedRelatedElement": None,
        }
        if self.prefix is not None:
            output["prefix"] = self.prefix.get_definition()
        if self.children is not None:
            output["ownedRelatedElement"] = self.children.get_definition()
        return output


class ExitActionMember:
    # ExitActionMember :
    # 	prefix=MemberPrefix DoActionKind ownedRelatedElement=StateActionUsage
    # ;
    def __init__(self, definition):
        self.prefix = None
        self.keyword = "exit"
        self.children = None
        if valid_definition(definition, self.__class__.__name__):
            if definition["prefix"] is not None:
                self.prefix = MemberPrefix(definition["prefix"])

            related = definition["ownedRelatedElement"]
            if related is not None:
                cls_name = related.get("name", "StateActionUsage")
                if cls_name in globals():
                    self.children = globals()[cls_name](related)
                else:
                    self.children = StateActionUsage(related)

    def dump(self):
        output = []
        if self.prefix is not None:
            output.append(self.prefix.dump())
        if self.children is not None:
            output.append(self.keyword)
            output.append(self.children.dump())
        return " ".join(output)

    def get_definition(self):
        output = {
            "name": self.__class__.__name__,
            "prefix": None,
            "ownedRelatedElement": None,
        }
        if self.prefix is not None:
            output["prefix"] = self.prefix.get_definition()
        if self.children is not None:
            output["ownedRelatedElement"] = self.children.get_definition()
        return output


class EntryActionMember:
    # EntryActionMember :
    # 	prefix=MemberPrefix EntryActionKind ownedRelatedElement=StateActionUsage
    # ;
    def __init__(self, definition):
        self.prefix = None
        self.keyword = "entry"
        self.children = None
        if valid_definition(definition, self.__class__.__name__):
            if definition["prefix"] is not None:
                self.prefix = MemberPrefix(definition["prefix"])

            related = definition["ownedRelatedElement"]
            if related is not None:
                cls_name = related.get("name", "StateActionUsage")
                if cls_name in globals():
                    self.children = globals()[cls_name](related)
                else:
                    self.children = StateActionUsage(related)

    def dump(self):
        output = []
        if self.prefix is not None:
            output.append(self.prefix.dump())

        if self.children is not None:
            output.append(self.keyword)
            output.append(self.children.dump())
        return " ".join(output)

    def get_definition(self):
        output = {
            "name": self.__class__.__name__,
            "prefix": None,
            "ownedRelatedElement": None,
        }
        if self.prefix is not None:
            output["prefix"] = self.prefix.get_definition()
        if self.children is not None:
            output["ownedRelatedElement"] = self.children.get_definition()
        return output


class StateActionUsage:
    # StateActionUsage :
    # 	';' | pau=PerformedActionUsage body=ActionBody
    # ;
    def __init__(self, definition):
        self.pau = None
        self.body = None
        if valid_definition(definition, self.__class__.__name__):
            if definition["body"] is not None:
                self.body = ActionBody(definition["body"])

            if definition.get("pau") is not None:
                self.pau = PerformedActionUsage(definition["pau"])

    def dump(self):
        if self.body is None:
            return ";"
        else:
            return "".join([self.pau.dump(), self.body.dump()])

    def get_definition(self):
        output = {
            "name": self.__class__.__name__,
            "pau": None,
            "body": None,
        }
        if self.pau is not None:
            output["pau"] = self.pau.get_definition()
        if self.body is not None:
            output["body"] = self.body.get_definition()
        return output


class StateAcceptActionUsage:
    # StateAcceptActionUsage :
    # 	declaration=AcceptNodeDeclaration body=ActionBody
    # ;
    def __init__(self, definition):
        self.declaration = None
        self.body = None
        if valid_definition(definition, self.__class__.__name__):
            if definition.get("declaration") is not None:
                self.declaration = AcceptNodeDeclaration(definition["declaration"])
            if definition.get("body") is not None:
                self.body = ActionBody(definition["body"])

    def dump(self):
        output = []
        if self.declaration is not None:
            output.append(self.declaration.dump())
        if self.body is not None:
            output.append(self.body.dump())
        return " ".join(output)

    def get_definition(self):
        output = {
            "name": self.__class__.__name__,
            "declaration": self.declaration.get_definition() if self.declaration else None,
            "body": self.body.get_definition() if self.body else None,
        }
        return output


class StateSendActionUsage:
    # StateSendActionUsage :
    # 	declaration=SendNodeDeclaration body=ActionBody
    # ;
    def __init__(self, definition):
        self.declaration = None
        self.body = None
        if valid_definition(definition, self.__class__.__name__):
            if definition.get("declaration") is not None:
                self.declaration = SendNodeDeclaration(definition["declaration"])
            if definition.get("body") is not None:
                self.body = ActionBody(definition["body"])

    def dump(self):
        output = []
        if self.declaration is not None:
            output.append(self.declaration.dump())
        if self.body is not None:
            output.append(self.body.dump())
        return " ".join(output)

    def get_definition(self):
        output = {
            "name": self.__class__.__name__,
            "declaration": self.declaration.get_definition() if self.declaration else None,
            "body": self.body.get_definition() if self.body else None,
        }
        return output


class StateAssignmentActionUsage:
    # StateAssignmentActionUsage :
    # 	declaration=AssignmentNodeDeclaration body=ActionBody
    # ;
    def __init__(self, definition):
        self.declaration = None
        self.body = None
        if valid_definition(definition, self.__class__.__name__):
            if definition["declaration"] is not None:
                self.declaration = AssignmentNodeDeclaration(definition["declaration"])
            if definition["body"] is not None:
                self.body = ActionBody(definition["body"])

    def dump(self):
        output = []
        if self.declaration is not None:
            output.append(self.declaration.dump())
        if self.body is not None:
            output.append(self.body.dump())
        return " ".join(output)

    def get_definition(self):
        output = {
            "name": self.__class__.__name__,
            "declaration": None,
            "body": None,
        }
        if self.declaration is not None:
            output["declaration"] = self.declaration.get_definition()
        if self.body is not None:
            output["body"] = self.body.get_definition()
        return output


class AssignmentNode:
    # AssignmentNode :
    # 	prefix=OccurrenceUsagePrefix declaration=AssignmentNodeDeclaration body=ActionBody
    # ;
    def __init__(self, definition):
        self.prefix = None
        if valid_definition(definition, self.__class__.__name__):
            if definition["prefix"] is not None:
                self.prefix = OccurrenceUsagePrefix(definition["prefix"])
            self.declaration = AssignmentNodeDeclaration(definition["declaration"])
            self.body = ActionBody(definition["body"])

    def dump(self):
        output = []
        if self.prefix is not None:
            output.append(self.prefix.dump())
        output.append(self.declaration.dump())
        output.append(self.body.dump())
        return "".join(output)

    def get_definition(self):
        return {
            "name": self.__class__.__name__,
            "prefix": self.prefix.get_definition() if self.prefix else None,
            "declaration": self.declaration.get_definition(),
            "body": self.body.get_definition(),
        }


class AssignmentNodeDeclaration:
    #  AssignmentNodeDeclaration :
    # 	declaration=ActionNodeUsageDeclaration? 'assign'
    # 	ownedRelationship1 = FeatureChainMember ':='
    # 	ownedRelationship2 = NodeParameterMember
    # ;
    def __init__(self, definition):
        self.declaration = None
        self.keyword = "assign"
        self.keyword2 = ":="
        self.target = None
        if valid_definition(definition, self.__class__.__name__):
            if definition["declaration"] is not None:
                self.declaration = ActionNodeUsageDeclaration(definition["declaration"])
            if definition.get("target") is not None:
                self.target = QualifiedName(definition["target"])
            self.fcm = FeatureChainMember(definition["ownedRelationship1"])
            self.npm = NodeParameterMember(definition["ownedRelationship2"])

    def dump(self):
        output = []
        if self.declaration is not None:
            output.append(self.declaration.dump())
        output.append(self.keyword)
        # Build the full target path: target.fcm (no space between)
        if self.target is not None:
            target_path = self.target.dump() + "." + self.fcm.dump()
        else:
            target_path = self.fcm.dump()
        output.append(target_path)
        output.append(self.keyword2)
        output.append(self.npm.dump())
        return " ".join(output)

    def get_definition(self):
        return {
            "name": self.__class__.__name__,
            "declaration": self.declaration.get_definition() if self.declaration else None,
            "target": self.target.get_definition() if self.target else None,
            "ownedRelationship1": self.fcm.get_definition() if self.fcm else None,
            "ownedRelationship2": self.npm.get_definition() if self.npm else None,
        }


class ActionNodeUsageDeclaration:
    #  ActionNodeUsageDeclaration :
    # 	ActionUsageKeyword declaration=UsageDeclaration?
    # ;
    def __init__(self, definition):
        self.declaration = None
        self.keyword = "action"
        if valid_definition(definition, self.__class__.__name__):
            if definition["declaration"] is not None:
                self.declaration = UsageDeclaration(definition["declaration"])

    def dump(self):
        # Only output keyword if there's a declaration (explicit "action" keyword)
        if self.declaration is not None:
            return " ".join([self.keyword, self.declaration.dump()])
        else:
            return ""  # No keyword when no declaration

    def get_definition(self):
        return {
            "name": self.__class__.__name__,
            "declaration": self.declaration.get_definition() if self.declaration else None,
        }


class IfNodeDeclaration:
    # IfNodeDeclaration :
    # 	ActionNodeUsageDeclaration? IF nodeParameterMember
    # ;
    def __init__(self, definition):
        self.declaration = None
        self.keyword = "if"
        self.nodeParameter = None
        if valid_definition(definition, self.__class__.__name__):
            if definition.get("declaration") is not None:
                self.declaration = ActionNodeUsageDeclaration(definition["declaration"])
            if definition.get("nodeParameter") is not None:
                self.nodeParameter = NodeParameterMember(definition["nodeParameter"])

    def dump(self):
        output = []
        if self.declaration is not None:
            output.append(self.declaration.dump())
        output.append(self.keyword)
        if self.nodeParameter is not None:
            output.append(self.nodeParameter.dump())
        return " ".join(output)

    def get_definition(self):
        return {
            "name": self.__class__.__name__,
            "declaration": self.declaration.get_definition() if self.declaration else None,
            "nodeParameter": self.nodeParameter.get_definition() if self.nodeParameter else None,
        }


class WhileLoopNodeDeclaration:
    # WhileLoopNodeDeclaration :
    # 	ActionNodeUsageDeclaration? WHILE nodeParameterMember
    # ;
    def __init__(self, definition):
        self.declaration = None
        self.keyword = "while"
        self.nodeParameter = None
        if valid_definition(definition, self.__class__.__name__):
            if definition.get("declaration") is not None:
                self.declaration = ActionNodeUsageDeclaration(definition["declaration"])
            if definition.get("nodeParameter") is not None:
                self.nodeParameter = NodeParameterMember(definition["nodeParameter"])

    def dump(self):
        output = []
        if self.declaration is not None:
            output.append(self.declaration.dump())
        output.append(self.keyword)
        if self.nodeParameter is not None:
            output.append(self.nodeParameter.dump())
        return " ".join(output)

    def get_definition(self):
        return {
            "name": self.__class__.__name__,
            "declaration": self.declaration.get_definition() if self.declaration else None,
            "nodeParameter": self.nodeParameter.get_definition() if self.nodeParameter else None,
        }


class ForLoopNodeDeclaration:
    # ForLoopNodeDeclaration :
    # 	ActionNodeUsageDeclaration? FOR nodeParameterMember
    # ;
    def __init__(self, definition):
        self.declaration = None
        self.keyword = "for"
        self.nodeParameter = None
        if valid_definition(definition, self.__class__.__name__):
            if definition.get("declaration") is not None:
                self.declaration = ActionNodeUsageDeclaration(definition["declaration"])
            if definition.get("nodeParameter") is not None:
                self.nodeParameter = NodeParameterMember(definition["nodeParameter"])

    def dump(self):
        output = []
        if self.declaration is not None:
            output.append(self.declaration.dump())
        output.append(self.keyword)
        if self.nodeParameter is not None:
            output.append(self.nodeParameter.dump())
        return " ".join(output)

    def get_definition(self):
        return {
            "name": self.__class__.__name__,
            "declaration": self.declaration.get_definition() if self.declaration else None,
            "nodeParameter": self.nodeParameter.get_definition() if self.nodeParameter else None,
        }


class ControlNodeDeclaration:
    # ControlNodeDeclaration :
    # 	ActionNodeUsageDeclaration? (JOIN | FORK | MERGE | DECIDE)
    # ;
    def __init__(self, definition):
        self.declaration = None
        self.keyword = None
        if valid_definition(definition, self.__class__.__name__):
            if definition.get("declaration") is not None:
                self.declaration = ActionNodeUsageDeclaration(definition["declaration"])
            self.keyword = definition.get("keyword")

    def dump(self):
        output = []
        if self.declaration is not None:
            output.append(self.declaration.dump())
        if self.keyword is not None:
            output.append(self.keyword)
        return " ".join(output)

    def get_definition(self):
        return {
            "name": self.__class__.__name__,
            "declaration": self.declaration.get_definition() if self.declaration else None,
            "keyword": self.keyword,
        }


class AcceptNodeDeclaration:
    # AcceptNodeDeclaration :
    # 	(actionNodeUsageDeclaration)? ACCEPT acceptParameterPart
    # ;
    def __init__(self, definition):
        self.declaration = None
        self.keyword = "accept"
        if valid_definition(definition, self.__class__.__name__):
            if definition.get("declaration") is not None:
                self.declaration = ActionNodeUsageDeclaration(definition["declaration"])
            self.acceptParameter = AcceptParameterPart(definition["acceptParameter"]) if definition.get("acceptParameter") else None

    def dump(self):
        output = []
        if self.declaration is not None:
            output.append(self.declaration.dump())
        output.append(self.keyword)
        if self.acceptParameter is not None:
            output.append(self.acceptParameter.dump())
        return " ".join(output)

    def get_definition(self):
        return {
            "name": self.__class__.__name__,
            "declaration": self.declaration.get_definition() if self.declaration else None,
            "acceptParameter": self.acceptParameter.get_definition() if self.acceptParameter else None,
        }


class SendNodeDeclaration:
    # SendNodeDeclaration :
    # 	(actionNodeUsageDeclaration)? SEND nodeParameterMember senderReceiverPart?
    # ;
    def __init__(self, definition):
        self.declaration = None
        self.keyword = "send"
        if valid_definition(definition, self.__class__.__name__):
            if definition.get("declaration") is not None:
                self.declaration = ActionNodeUsageDeclaration(definition["declaration"])
            self.nodeParameter = NodeParameterMember(definition["nodeParameter"]) if definition.get("nodeParameter") else None
            self.senderReceiver = SenderReceiverPart(definition["senderReceiver"]) if definition.get("senderReceiver") else None

    def dump(self):
        output = []
        if self.declaration is not None:
            output.append(self.declaration.dump())
        output.append(self.keyword)
        if self.nodeParameter is not None:
            output.append(self.nodeParameter.dump())
        if self.senderReceiver is not None:
            output.append(self.senderReceiver.dump())
        return " ".join(output)

    def get_definition(self):
        return {
            "name": self.__class__.__name__,
            "declaration": self.declaration.get_definition() if self.declaration else None,
            "nodeParameter": self.nodeParameter.get_definition() if self.nodeParameter else None,
            "senderReceiver": self.senderReceiver.get_definition() if self.senderReceiver else None,
        }


class NodeParameterMember:
    # NodeParameterMember :
    # 	ownedRelatedElement = NodeParameter
    # ;
    def __init__(self, definition):
        self.children = None
        if valid_definition(definition, self.__class__.__name__):
            if definition.get("ownedRelatedElement") is not None:
                self.children = NodeParameter(definition["ownedRelatedElement"])

    def dump(self):
        if self.children is not None:
            return self.children.dump()
        return ""

    def get_definition(self):
        return {
            "name": self.__class__.__name__,
            "ownedRelatedElement": self.children.get_definition() if self.children else None,
        }


class NodeParameter:
    # NodeParameter :
    # 	 ownedRelationship = FeatureBinding
    # ;
    def __init__(self, definition):
        self.children = None
        if valid_definition(definition, self.__class__.__name__):
            if definition.get("ownedRelationship") is not None:
                self.children = FeatureBinding(definition["ownedRelationship"])
            elif definition.get("memberElement") is not None:
                self.children = QualifiedName(definition["memberElement"])

    def dump(self):
        if self.children is not None:
            return self.children.dump()
        return ""

    def get_definition(self):
        return {
            "name": self.__class__.__name__,
            "ownedRelationship": self.children.get_definition() if self.children else None,
            "memberElement": None,
        }


class FeatureBinding:
    # FeatureBinding :
    # 	ownedRelatedElement = OwnedExpression
    # ;
    def __init__(self, definition):
        if valid_definition(definition, self.__class__.__name__):
            self.children = OwnedExpression(definition["ownedRelatedElement"])

    def dump(self):
        return self.children.dump()

    def get_definition(self):
        output = {
            "name": self.__class__.__name__,
            "ownedRelatedElement": self.children.get_definition(),
        }
        return output


class PerformedActionUsage:
    # PerformedActionUsage :
    # 	   declaration=PerformActionUsageDeclaration
    # 	|  declaration=AcceptNodeDeclaration
    # 	|  declaration=SendNodeDeclaration
    # 	|  declaration=AssignmentNodeDeclaration
    # ;
    def __init__(self, definition):
        self.declaration = None
        if valid_definition(definition, self.__class__.__name__):
            self.declaration = globals()[definition["declaration"]["name"]](
                definition["declaration"]
            )

    def dump(self):
        return self.declaration.dump()

    def get_definition(self):
        output = {
            "name": self.__class__.__name__,
            "declaration": None,
        }
        if self.declaration is not None:
            output["declaration"] = self.declaration.get_definition()
        return output


class PerformActionUsageDeclaration:
    # PerformActionUsageDeclaration :
    #    	( ownedRelationship = OwnedReferenceSubsetting fspart=FeatureSpecializationPart?
    #    	| ActionUsageKeyword declaration=UsageDeclaration? )
    #     valuepart=ValuePart?
    # ;
    def __init__(self, definition):
        self.valuepart = None
        self.children = []
        if valid_definition(definition, self.__class__.__name__):
            if definition["ownedRelationship"] is not None:
                self.children.append(
                    OwnedReferenceSubsetting(definition["ownedRelationship"])
                )
                if definition["fspart"] is not None:
                    self.children.append(
                        FeatureSpecializationPart(definition["fspart"])
                    )
            else:
                if definition["declaration"] is not None:
                    self.children.append(UsageDeclaration(definition["declaration"]))

            if definition["valuepart"] is not None:
                self.valuepart = ValuePart(definition["valuepart"])

    def dump(self):
        if self.valuepart is not None:
            vpdump = " " + self.valuepart.dump()
        else:
            vpdump = ""

        if len(self.children) == 0:
            return "action" + vpdump
        else:
            if self.children[0].__class__.__name__ == "UsageDeclaration":
                return "action " + self.children[0].dump() + vpdump
            else:
                return " ".join([x.dump() for x in self.children]) + vpdump

    def get_definition(self):
        output = {
            "name": self.__class__.__name__,
            "ownedRelationship": None,
            "fspart": None,
            "declaration": None,
            "valuepart": None,
        }
        if self.children:
            if self.children[0].__class__.__name__ == "OwnedReferenceSubsetting":
                output["ownedRelationship"] = self.children[0].get_definition()
                if len(self.children) > 1:
                    output["fspart"] = self.children[1].get_definition()
            else:
                output["declaration"] = self.children[0].get_definition()
        if self.valuepart is not None:
            output["valuepart"] = self.valuepart.get_definition()
        return output


class EntryTransitionMember:
    # EntryTransitionMember :
    # 	prefix=MemberPrefix
    # 	( ownedRelatedElement=GuardedTargetSuccession
    # 	| 'then' ownedRelatedElement=TransitionSuccession
    # 	) ';'
    # ;
    def __init__(self, definition):
        self.prefix = None
        self.body = ";"
        self.children = None
        if valid_definition(definition, self.__class__.__name__):
            if definition["prefix"] is not None:
                self.prefix = MemberPrefix(definition["prefix"])

            if definition["ownedRelatedElement"]["name"] == "GuardedTargetSuccession":
                self.children = GuardedTargetSuccession(
                    definition["ownedRelatedElement"]
                )
            else:
                self.children = TransitionSuccession(definition["ownedRelatedElement"])

    def dump(self):
        output = []
        if self.prefix is not None:
            output.append(self.prefix.dump())
        if self.children.__class__.__name__ == "TransitionSuccession":
            output.append("then")
        output.append(self.children.dump())
        output.append(self.body)
        return " ".join(output)

    def get_definition(self):
        output = {
            "name": self.__class__.__name__,
            "prefix": None,
            "ownedRelatedElement": None,
        }
        if self.prefix is not None:
            output["prefix"] = self.prefix.get_definition()
        if self.children is not None:
            output["ownedRelatedElement"] = self.children.get_definition()
        return output


class GuardedTargetSuccession:
    # GuardedTargetSuccession :
    # 	ownedRelationship += GuardExpressionMember
    # 	'then' ownedRelationship += TransitionSuccessionMember
    # ;
    def __init__(self, definition):
        self.children = []
        if valid_definition(definition, self.__class__.__name__):
            for child in definition["ownedRelationship"]:
                if child["name"] == "GuardExpressionMember":
                    self.children.append(GuardExpressionMember(child))
                elif child["name"] == "TransitionSuccessionMember":
                    self.children.append(TransitionSuccessionMember(child))

    def dump(self):
        return " then ".join([x.dump() for x in self.children])

    def get_definition(self):
        output = {
            "name": self.__class__.__name__,
            "ownedRelationship": [],
        }
        for child in self.children:
            output["ownedRelationship"].append(child.get_definition())
        return output


class GuardExpressionMember:
    # GuardExpressionMember :
    # 	(IF | GUARD) ownedExpression
    # ;
    def __init__(self, definition):
        self.keyword = "if"
        self.children = None
        if valid_definition(definition, self.__class__.__name__):
            if definition.get("keyword") is not None:
                self.keyword = definition["keyword"]
            if definition.get("ownedRelatedElement") is not None:
                self.children = OwnedExpression(definition["ownedRelatedElement"])

    def dump(self):
        if self.children is not None:
            return " ".join([self.keyword, self.children.dump()])
        return ""

    def get_definition(self):
        output = {
            "name": self.__class__.__name__,
            "keyword": self.keyword,
            "ownedRelatedElement": None,
        }
        if self.children is not None:
            output["ownedRelatedElement"] = self.children.get_definition()
        return output


class TransitionSuccessionMember:
    # TransitionSuccessionMember :
    # 	ownedRelatedElement = TransitionSuccession
    # ;
    def __init__(self, definition):
        if valid_definition(definition, self.__class__.__name__):
            self.children = TransitionSuccession(definition["ownedRelatedElement"])

    def dump(self):
        return self.children.dump()

    def get_definition(self):
        output = {
            "name": self.__class__.__name__,
            "ownedRelatedElement": None,
        }
        if self.children is not None:
            output["ownedRelatedElement"] = self.children.get_definition()
        return output


class TransitionSuccession:
    # TransitionSuccession :
    # 	ownedRelationship = ConnectorEndMember
    # ;
    def __init__(self, definition):
        if valid_definition(definition, self.__class__.__name__):
            # ownedRelationship can be a list (from visitor) or a dict (from grammar)
            rel = definition["ownedRelationship"]
            if isinstance(rel, list):
                rel = rel[0] if rel else {"name": "ConnectorEndMember", "ownedRelatedElement": []}
            self.children = ConnectorEndMember(rel)

    def dump(self):
        return self.children.dump()

    def get_definition(self):
        output = {
            "name": self.__class__.__name__,
            "ownedRelationship": None,
        }
        if self.children is not None:
            output["ownedRelationship"] = self.children.get_definition()
        return output


class TransitionUsageMember:
    # TransitionUsageMember :
    # 	prefix=MemberPrefix ownedRelatedElement=TransitionUsage
    # ;
    def __init__(self, definition):
        self.prefix = None
        if valid_definition(definition, self.__class__.__name__):
            if definition["prefix"] is not None:
                self.prefix = MemberPrefix(definition["prefix"])

            self.children = TransitionUsage(definition["ownedRelatedElement"])

    def dump(self):
        output = []
        if self.prefix is not None:
            output.append(self.prefix.dump())
        output.append(self.children.dump())
        return " ".join(output)

    def get_definition(self):
        output = {
            "name": self.__class__.__name__,
            "prefix": None,
            "ownedRelatedElement": None,
        }
        if self.prefix is not None:
            output["prefix"] = self.prefix.get_definition()
        if self.children is not None:
            output["ownedRelatedElement"] = self.children.get_definition()
        return output


class TargetTransitionUsageMember:
    # This is a special class version of the previous, but it assumes the
    # previous node as a target
    # TargetTransitionUsageMember :
    # 	prefix=MemberPrefix ownedRelatedElement = TargetTransitionUsage
    # ;
    def __init__(self, definition):
        self.prefix = None
        if valid_definition(definition, self.__class__.__name__):
            if definition["prefix"] is not None:
                self.prefix = MemberPrefix(definition["prefix"])
            self.children = TargetTransitionUsage(definition["ownedRelatedElement"])

    def dump(self):
        output = []
        if self.prefix is not None:
            output.append(self.prefix.dump())
        output.append(self.children.dump())
        return " ".join(output)

    def get_definition(self):
        output = {
            "name": self.__class__.__name__,
            "prefix": None,
            "ownedRelatedElement": None,
        }
        if self.prefix is not None:
            output["prefix"] = self.prefix.get_definition()
        if self.children is not None:
            output["ownedRelatedElement"] = self.children.get_definition()
        return output


class TargetTransitionUsage:
    # TargetTransitionUsage :
    # 	TransitionUsageKeyword?
    # 	(
    #     (ownedRelationship1 = TriggerActionMember)
    # 	  (ownedRelationship2 = GuardExpressionMember)?
    # 	  (ownedRelationship3 = EffectBehaviorMember)?
    #   ) | (
    #     (ownedRelationship2 = GuardExpressionMember)
    #     (ownedRelationship3 = EffectBehaviorMember)?
    #   ) | (
    #     (ownedRelationship3 = EffectBehaviorMember)
    #   )
    # 	'then' ownedRelationship4 = TransitionSuccessionMember
    # 	body=ActionBody
    # ;
    # Here transition is optional
    def __init__(self, definition):
        self.children = []
        self.body = None
        if valid_definition(definition, self.__class__.__name__):
            child = definition.get("ownedRelationship1")
            if child is not None and child.get("name") == "TriggerActionMember":
                self.children.append(TriggerActionMember(child))

            child = definition.get("ownedRelationship2")
            if child is not None and child.get("name") == "GuardExpressionMember":
                self.children.append(GuardExpressionMember(child))
            child = definition.get("ownedRelationship3")
            if child is not None and child.get("name") == "EffectBehaviorMember":
                self.children.append(EffectBehaviorMember(child))
            child = definition.get("ownedRelationship4")
            if child is not None and child.get("name") == "TransitionSuccessionMember":
                self.children.append(TransitionSuccessionMember(child))

            self.body = ActionBody(definition["body"])

    def dump(self):
        output = []
        # Skip the transition keyword here.
        for child in self.children:
            if child.__class__.__name__ == "TransitionSuccessionMember":
                output.append("\n   then")
            output.append(child.dump())
        output.append(self.body.dump())
        return " ".join(output)

    def get_definition(self):
        output = {
            "name": self.__class__.__name__,
            "ownedRelationship1": None,
            "ownedRelationship2": None,
            "ownedRelationship3": None,
            "ownedRelationship4": None,
            "body": None,
        }
        if len(self.children) > 0:
            output["ownedRelationship1"] = self.children[0].get_definition()
        if len(self.children) > 1:
            output["ownedRelationship2"] = self.children[1].get_definition()
        if len(self.children) > 2:
            output["ownedRelationship3"] = self.children[2].get_definition()
        if len(self.children) > 3:
            output["ownedRelationship4"] = self.children[3].get_definition()
        if self.body is not None:
            output["body"] = self.body.get_definition()
        return output


class TransitionUsage:
    # TransitionUsage :
    # 	TransitionUsageKeyword ( declaration=UsageDeclaration? 'first' )?
    # 	ownedRelationship += TransitionSourceMember
    # 	( ownedRelationship += TriggerActionMember )?
    # 	( ownedRelationship += GuardExpressionMember )?
    # 	( ownedRelationship += EffectBehaviorMember )?
    # 	'then' ownedRelationship += TransitionSuccessionMember
    # 	body=ActionBody
    # ;
    def __init__(self, definition):
        self.keyword = "transition"
        self.declaration = None
        self.has_first = False
        self.children = []
        if valid_definition(definition, self.__class__.__name__):
            if definition["declaration"] is not None:
                self.declaration = UsageDeclaration(definition["declaration"])
            self.has_first = bool(definition.get("hasFirst"))

            self.body = ActionBody(definition["body"])

            for child in definition["ownedRelationship"]:
                if child["name"] == "TransitionSourceMember":
                    self.children.append(TransitionSourceMember(child))
                elif child["name"] == "TriggerActionMember":
                    self.children.append(TriggerActionMember(child))
                elif child["name"] == "GuardExpressionMember":
                    self.children.append(GuardExpressionMember(child))
                elif child["name"] == "EffectBehaviorMember":
                    self.children.append(EffectBehaviorMember(child))
                else:
                    self.children.append(TransitionSuccessionMember(child))

    def dump(self):
        output = [self.keyword]
        if self.declaration is not None:
            output.append(self.declaration.dump())
        # grammar: TRANSITION ( usageDeclaration? FIRST )? — a declared
        # name is only allowed together with 'first', and 'first' may
        # also appear on its own
        if self.declaration is not None or self.has_first:
            output.append("\n   first")

        for child in self.children:
            if child.__class__.__name__ == "TransitionSuccessionMember":
                output.append("\n   then")
            output.append(child.dump())

        output.append(self.body.dump())
        return " ".join(output)

    def get_definition(self):
        output = {
            "name": self.__class__.__name__,
            "keyword": self.keyword,
            "declaration": None,
            "hasFirst": self.has_first,
            "body": None,
            "ownedRelationship": [],
        }
        if self.declaration is not None:
            output["declaration"] = self.declaration.get_definition()
        if self.body is not None:
            output["body"] = self.body.get_definition()
        for child in self.children:
            output["ownedRelationship"].append(child.get_definition())
        return output


class EffectBehaviorMember:
    # EffectBehaviorMember :
    # 	EffectFeatureKind ownedRelatedElement=EffectBehaviorUsage
    # ;
    def __init__(self, definition):
        self.keyword = "do"
        self.children = None
        if valid_definition(definition, self.__class__.__name__):
            if definition.get("ownedRelatedElement") is not None:
                self.children = EffectBehaviorUsage(definition["ownedRelatedElement"])

    def dump(self):
        if self.children is not None:
            return " ".join([self.keyword, self.children.dump()])
        return ""

    def get_definition(self):
        output = {
            "name": self.__class__.__name__,
            "ownedRelatedElement": None,
        }
        if self.children is not None:
            output["ownedRelatedElement"] = self.children.get_definition()
        return output


class EffectBehaviorUsage:
    # EffectBehaviorUsage :
    # 	  usage=PerformedActionUsage ( '{' item+=ActionBodyItem* '}' )?
    # ;
    def __init__(self, definition):
        self.children = []
        if valid_definition(definition, self.__class__.__name__):
            self.usage = PerformedActionUsage(definition["usage"])
            for item in definition["item"]:
                self.children.append(ActionBodyItem(item))

    def dump(self):
        output = [self.usage.dump()]
        if len(self.children) > 0:
            output.append("{\n")
            for child in self.children:
                output.append(child.dump())
            output.append("\n}")
        return " ".join(output)

    def get_definition(self):
        return {
            "name": self.__class__.__name__,
            "usage": self.usage.get_definition(),
            "item": [x.get_definition() for x in self.children],
        }


class TransitionSourceMember:
    # TransitionSourceMember :
    # 	  ownedRelatedElement += OwnedFeatureChain
    # 	| memberElement = QualifiedName
    # ;
    def __init__(self, definition):
        self.children = []
        if valid_definition(definition, self.__class__.__name__):
            if definition["memberElement"] is not None:
                self.children.append(QualifiedName(definition["memberElement"]))
            else:
                for child in definition["ownedRelatedElement"]:
                    self.children.append(OwnedFeatureChain(child))

    def dump(self):
        return "".join([x.dump() for x in self.children])

    def get_definition(self):
        output = {
            "name": self.__class__.__name__,
            "memberElement": None,
            "ownedRelatedElement": [],
        }
        for child in self.children:
            if child.__class__.__name__ == "QualifiedName":
                output["memberElement"] = child.get_definition()
            else:
                output["ownedRelatedElement"].append(child.get_definition())
        return output


class TriggerActionMember:
    # TriggerActionMember :
    # 	TriggerFeatureKind ownedRelatedElement=TriggerAction
    # ;
    def __init__(self, definition):
        self.keyword = "accept"
        if valid_definition(definition, self.__class__.__name__):
            self.children = TriggerAction(definition["ownedRelatedElement"])

    def dump(self):
        return " ".join([self.keyword, self.children.dump()])

    def get_definition(self):
        output = {
            "name": self.__class__.__name__,
            "ownedRelatedElement": None,
        }
        if self.children is not None:
            output["ownedRelatedElement"] = self.children.get_definition()
        return output


class TriggerAction:
    # TriggerAction :
    # 	part=AcceptParameterPart
    # ;
    def __init__(self, definition):
        if valid_definition(definition, self.__class__.__name__):
            self.children = AcceptParameterPart(definition["part"])

    def dump(self):
        return self.children.dump()

    def get_definition(self):
        output = {
            "name": self.__class__.__name__,
            "part": None,
        }
        if self.children is not None:
            output["part"] = self.children.get_definition()
        return output


class AcceptParameterPart:
    # AcceptParameterPart :
    # 	ownedRelationship += PayloadParameterMember 'via'
    #   ownedRelationship += NodeParameterMember
    # ;
    def __init__(self, definition):
        self.keyword = "via"
        self.children = []
        if valid_definition(definition, self.__class__.__name__):
            for child in definition["ownedRelationship"]:
                if child["name"] == "PayloadParameterMember":
                    self.children.append(PayloadParameterMember(child))
                else:
                    self.children.append(NodeParameterMember(child))

    def dump(self):
        return (" " + self.keyword + " ").join([x.dump() for x in self.children])

    def get_definition(self):
        output = {
            "name": self.__class__.__name__,
            "ownedRelationship": [],
        }
        for child in self.children:
            output["ownedRelationship"].append(child.get_definition())
        return output


class SenderReceiverPart:
    # SenderReceiverPart :
    # 	'via' nodeParameterMember 'to' nodeParameterMember
    # 	| 'to' nodeParameterMember
    # ;
    def __init__(self, definition):
        self.via = None
        self.to = None
        if valid_definition(definition, self.__class__.__name__):
            if definition.get("via") is not None:
                self.via = NodeParameterMember(definition["via"])
            if definition.get("to") is not None:
                self.to = NodeParameterMember(definition["to"])

    def dump(self):
        output = []
        if self.via is not None:
            output.append("via")
            output.append(self.via.dump())
        if self.to is not None:
            output.append("to")
            output.append(self.to.dump())
        return " ".join(output)

    def get_definition(self):
        return {
            "name": self.__class__.__name__,
            "via": self.via.get_definition() if self.via else None,
            "to": self.to.get_definition() if self.to else None,
        }


class EmptyParameterMember:
    # EmptyParameterMember :
    # 	emptyUsage_
    # ;
    def __init__(self, definition):
        self.featureChain = None
        if valid_definition(definition, self.__class__.__name__):
            if definition.get("featureChain") is not None:
                self.featureChain = FeatureChainMember(definition["featureChain"])

    def dump(self):
        if self.featureChain is not None:
            return self.featureChain.dump()
        return ""

    def get_definition(self):
        return {
            "name": self.__class__.__name__,
            "featureChain": self.featureChain.get_definition() if self.featureChain else None,
        }


class PayloadParameterMember:
    # PayloadParameterMember :
    # 	ownedRelatedElement = PayloadParameter
    # ;
    def __init__(self, definition):
        self.children = None
        if valid_definition(definition, self.__class__.__name__):
            self.children = PayloadParameter(definition["ownedRelatedElement"])

    def dump(self):
        return self.children.dump()

    def get_definition(self):
        output = {
            "name": self.__class__.__name__,
            "ownedRelatedElement": None,
        }
        if self.children is not None:
            output["ownedRelatedElement"] = self.children.get_definition()
        return output


class PayloadParameter:
    # PayloadParameter :
    # 	  feature=PayloadFeature
    # 	| identification=Identification? pfsp=PayloadFeatureSpecializationPart? tvp=TriggerValuePart
    # ;
    def __init__(self, definition):
        self.children = None
        self.identification = None
        self.pfsp = None
        if valid_definition(definition, self.__class__.__name__):
            if definition["feature"] is not None:
                self.children = PayloadFeature(definition["feature"])
            else:
                if definition["identification"] is not None:
                    self.identification = Identification(definition["identification"])

                if definition["pfsp"] is not None:
                    self.pfsp = PayloadFeatureSpecializationPart(definition["pfsp"])

                self.children = TriggerValuePart(definition["tvp"])

    def dump(self):
        output = []
        if self.identification is not None:
            output.append(self.identification.dump())
        if self.pfsp is not None:
            output.append(self.pfsp.dump())

        if self.children is not None:
            output.append(self.children.dump())
        return " ".join(output)

    def get_definition(self):
        output = {
            "name": self.__class__.__name__,
            "feature": None,
            "identification": None,
            "pfsp": None,
            "tvp": None,
        }
        if self.children is not None:
            if self.children.__class__.__name__ == "PayloadFeature":
                output["feature"] = self.children.get_definition()
            else:
                output["tvp"] = self.children.get_definition()
        if self.identification is not None:
            output["identification"] = self.identification.get_definition()
        if self.pfsp is not None:
            output["pfsp"] = self.pfsp.get_definition()
        return output


class TriggerValuePart:
    # TriggerValuePart :
    # 	ownedRelationship = TriggerFeatureValue
    # ;
    def __init__(self, definition):
        self.children = None
        if valid_definition(definition, self.__class__.__name__):
            rel = definition.get("ownedRelationship")
            if rel and isinstance(rel, dict):
                self.children = TriggerFeatureValue(rel)

    def dump(self):
        if self.children:
            return self.children.dump()
        return ""

    def get_definition(self):
        return {
            "name": self.__class__.__name__,
            "ownedRelationship": self.children.get_definition() if self.children else None,
        }


class TriggerFeatureValue:
    # TriggerFeatureValue :
    # 	ownedRelatedElement = TriggerExpression
    # ;
    def __init__(self, definition):
        self.children = None
        if valid_definition(definition, self.__class__.__name__):
            rel = definition.get("ownedRelatedElement")
            if rel and isinstance(rel, dict):
                self.children = TriggerExpression(rel)

    def dump(self):
        if self.children:
            return self.children.dump()
        return ""

    def get_definition(self):
        return {
            "name": self.__class__.__name__,
            "ownedRelatedElement": self.children.get_definition() if self.children else None,
        }


class TriggerExpression:
    # TriggerExpression :
    # 	  kind = TimeTriggerKind
    # 	  ownedRelationship = OwnedExpressionMember
    # 	| ChangeTriggerKind
    # 	  ownedRelationship = ChangeExpressionMember
    # ;
    def __init__(self, definition):
        self.kind = None
        self.children = None
        if valid_definition(definition, self.__class__.__name__):
            rel = definition.get("ownedRelationship")
            if isinstance(rel, dict):
                self.children = OwnedExpressionMember(rel)
            kind = definition.get("kind")
            if isinstance(kind, dict):
                if kind.get("isWhen") and not (
                    kind.get("isAt") or kind.get("isAfter")
                ):
                    # WHEN triggers carry a change expression
                    self.kind = "when"
                else:
                    self.kind = TimeTriggerKind(kind)

    def dump(self):
        if isinstance(self.kind, str):
            kind = self.kind
        else:
            kind = self.kind.dump()

        if self.children is None:
            return kind
        return " ".join([kind, self.children.dump()])

    def get_definition(self):
        output = {"name": self.__class__.__name__, "kind": None, "ownedRelationship": None}
        if isinstance(self.kind, str):
            output["kind"] = {"name": "TimeTriggerKind", "isAt": False, "isAfter": False, "isWhen": True}
        elif self.kind is not None:
            output["kind"] = self.kind.get_definition()
        if self.children is not None:
            output["ownedRelationship"] = self.children.get_definition()
        return output


class TimeTriggerKind:
    def __init__(self, definition):
        if valid_definition(definition, self.__class__.__name__):
            self.isAt = definition.get("isAt", False)
            self.isAfter = definition.get("isAfter", False)
            self.isWhen = definition.get("isWhen", False)

    def dump(self):
        if self.isAt:
            return "at"
        elif self.isWhen:
            return "when"
        else:
            return "after"

    def get_definition(self):
        return {
            "name": self.__class__.__name__,
            "isAt": self.isAt,
            "isAfter": self.isAfter,
            "isWhen": self.isWhen,
        }


class OwnedExpressionMember:
    # OwnedExpressionMember :
    # 	ownedRelatedElement = OwnedExpression
    # ;
    def __init__(self, definition):
        if valid_definition(definition, self.__class__.__name__):
            self.children = OwnedExpression(definition["ownedRelatedElement"])

    def dump(self):
        return self.children.dump()

    def get_definition(self):
        return {
            "name": self.__class__.__name__,
            "ownedRelatedElement": self.children.get_definition(),
        }


class ChangeExpressionMember:
    # ChangeExpressionMember :
    # 	ownedRelatedElement = ChangeExpression
    # ;
    def __init__(self, definition):
        if valid_definition(definition, self.__class__.__name__):
            self.children = ChangeExpression(definition["ownedRelatedElement"])

    def dump(self):
        return self.children.dump()

    def get_definition(self):
        return {
            "name": self.__class__.__name__,
            "ownedRelatedElement": self.children.get_definition(),
        }


class ChangeExpression:
    # ChangeExpression :
    # 	ownedRelationship = ChangeResultExpressionMember
    # ;
    def __init__(self, definition):
        if valid_definition(definition, self.__class__.__name__):
            self.children = ChangeResultExpressionMember(
                definition["ownedRelationship"]
            )

    def dump(self):
        return self.children.dump()

    def get_definition(self):
        return {
            "name": self.__class__.__name__,
            "ownedRelationship": self.children.get_definition(),
        }


class ChangeResultExpressionMember:
    # ChangeResultExpressionMember :
    # 	ownedRelatedElement = OwnedExpression
    # ;
    def __init__(self, definition):
        if valid_definition(definition, self.__class__.__name__):
            self.children = OwnedExpression(definition["ownedRelatedElement"])

    def dump(self):
        return self.children.dump()

    def get_definition(self):
        return {
            "name": self.__class__.__name__,
            "ownedRelatedElement": self.children.get_definition(),
        }


class CalculationDefinition:
    def __init__(self, definition=None):
        self.prefix = None
        self.keyword = "calc def"
        if definition is not None:
            if valid_definition(definition, self.__class__.__name__):
                if definition["prefix"] is not None:
                    self.prefix = OccurrenceDefinitionPrefix(definition["prefix"])

                self.declaration = DefinitionDeclaration(definition["declaration"])
                self.body = CalculationBody(definition["body"])
        else:
            self.declaration = DefinitionDeclaration()
            self.body = CalculationBody()

    def dump(self):
        output = []
        if self.prefix is not None:
            output.append(self.prefix.dump())
        output.append(self.keyword)
        output.append(self.declaration.dump())
        output.append(self.body.dump())
        return " ".join(output)

    def get_definition(self):
        output = {"name": self.__class__.__name__, "prefix": None}
        if self.prefix is not None:
            output["prefix"] = self.prefix.get_definition()
        output["declaration"] = self.declaration.get_definition()
        output["body"] = self.body.get_definition()
        return output


class ActionDefinition:
    def __init__(self, definition=None):
        self.prefix = None
        self.keyword = "action def"
        if definition is not None:
            if valid_definition(definition, self.__class__.__name__):
                if definition["prefix"] is not None:
                    prefix_name = definition["prefix"].get("name", "DefinitionPrefix")
                    self.prefix = globals()[prefix_name](definition["prefix"])
                self.declaration = DefinitionDeclaration(definition["declaration"])
                self.body = ActionBody(definition["body"])
        else:
            self.declaration = DefinitionDeclaration(None)
            self.body = ActionBody(None)

    def dump(self):
        output = []
        if self.prefix is not None:
            output.append(self.prefix.dump())
        output.append(self.keyword)
        output.append(self.declaration.dump())
        return " ".join(filter(None, output)) + self.body.dump()

    def get_definition(self):
        output = {"name": self.__class__.__name__, "prefix": None}
        if self.prefix is not None:
            output["prefix"] = self.prefix.get_definition()
        
        # ActionDefinition uses 'declaration' directly (not wrapped in 'definition')
        output["declaration"] = self.declaration.get_definition()
        output["body"] = self.body.get_definition()
        
        return output


class ActionBody:
    def __init__(self, definition=None):
        self.children = []
        if definition is not None:
            if valid_definition(definition, self.__class__.__name__):
                # Support both "items" (from get_definition) and "item" (from visitor)
                items = definition.get("items") or definition.get("item") or []
                for item in items:
                    self.children.append(ActionBodyItem(item))

    def dump(self):
        if len(self.children) == 0:
            return ";"
        else:
            return " {\n" + "\n".join([x.dump() for x in self.children]) + "\n}"

    def get_definition(self):
        return {
            "name": self.__class__.__name__,
            "items": [child.get_definition() for child in self.children]
        }


class ActionBodyItem:
    def __init__(self, definition):
        self.children = []
        if valid_definition(definition, self.__class__.__name__):
            if isinstance(definition["ownedRelationship"], list):
                for child in definition["ownedRelationship"]:
                    self.children.append(globals()[child["name"]](child))
            else:
                self.children.append(
                    globals()[definition["ownedRelationship"]["name"]](
                        definition["ownedRelationship"]
                    )
                )

    def dump(self):
        output = []
        for child in self.children:
            output.append(child.dump())
            if child.__class__.__name__ != "EmptySuccessionMember":
                output.append("\n")
            else:
                output.append(" ")

        if output and output[-1] == "\n":
            output = output[:-1]
        text = "".join(output)
        # Succession-style members (first/then/guard) form bare statements
        # that need a terminating semicolon; members with bodies ({...}),
        # their own ";", or a trailing doc comment terminate themselves.
        if text and not text.rstrip().endswith((";", "}", "*/")):
            text += ";"
        return text

    def get_definition(self):
        return {
            "name": self.__class__.__name__,
            "ownedRelationship": [child.get_definition() for child in self.children]
        }


class ActionBodyItemTarget:
    # ActionBodyItemTarget :
    #     ( member=BehaviorUsageMember | member=ActionNodeMember )
    # ;
    def __init__(self, definition):
        if valid_definition(definition, self.__class__.__name__):
            if definition["member"]["name"] == "BehaviorUsageMember":
                self.children = BehaviorUsageMember(definition["member"])
            else:
                self.children = ActionNodeMember(definition["member"])

    def dump(self):
        return self.children.dump()

    def get_definition(self):
        return {
            "name": self.__class__.__name__,
            "member": self.children.get_definition(),
        }


class ActionNodeMember:
    # ActionNodeMember :
    # 	prefix=MemberPrefix ownedRelatedElement = ActionNode
    # ;
    def __init__(self, definition):
        self.prefix = None
        if valid_definition(definition, self.__class__.__name__):
            if definition["prefix"] is not None:
                self.prefix = MemberPrefix(definition["prefix"])
            self.children = ActionNode(definition["ownedRelatedElement"])

    def dump(self):
        output = []
        if self.prefix is not None:
            output.append(self.prefix.dump())
        output.append(self.children.dump())
        return " ".join(output)

    def get_definition(self):
        output = {
            "name": self.__class__.__name__,
            "prefix": None,
            "ownedRelatedElement": None,
        }
        if self.prefix is not None:
            output["prefix"] = self.prefix.get_definition()
        if self.children is not None:
            output["ownedRelatedElement"] = self.children.get_definition()
        return output


class InitialNodeMember:
    # initialNodeMember : memberPrefix FIRST qualifiedName relationshipBody
    # Visitor dict shape (antlr_visitor.py _visit_initial_node_member):
    #   {"name": "InitialNodeMember", "prefix": ...,
    #    "ownedRelatedElement": {"name": "InitialNode", "declaredName": ...}}
    def __init__(self, definition):
        self.prefix = None
        self.declared_name = None
        self.has_semi = False
        if valid_definition(definition, self.__class__.__name__):
            if definition.get("prefix") is not None:
                self.prefix = MemberPrefix(definition["prefix"])
            ore = definition.get("ownedRelatedElement") or {}
            if isinstance(ore, dict):
                self.declared_name = ore.get("declaredName")
                self.has_semi = bool(ore.get("hasSemi"))

    def dump(self):
        output = []
        if self.prefix is not None:
            output.append(self.prefix.dump())
        output.append("first")
        if self.declared_name:
            output.append(self.declared_name)
        text = " ".join(output)
        if self.has_semi and not text.rstrip().endswith(";"):
            text += ";"
        return text

    def get_definition(self):
        return {
            "name": self.__class__.__name__,
            "prefix": self.prefix.get_definition() if self.prefix else None,
            "ownedRelatedElement": {
                "name": "InitialNode",
                "declaredName": self.declared_name,
                "hasSemi": self.has_semi,
                "ownedRelationship": [],
            },
        }


class ActionTargetSuccessionMember:
    # actionTargetSuccessionMember : memberPrefix actionTargetSuccession
    # Visitor dict shape (_visit_action_target_succession_member).
    # keyword is "then" (targetSuccession) or "else" (defaultTargetSuccession).
    # has_semi records whether the succession carried its own usageBody ";".
    def __init__(self, definition):
        self.prefix = None
        self.keyword = "then"
        self.declared_name = None
        self.condition = None
        self.has_semi = False
        if valid_definition(definition, self.__class__.__name__):
            if definition.get("prefix") is not None:
                self.prefix = MemberPrefix(definition["prefix"])
            ore = definition.get("ownedRelatedElement") or {}
            if isinstance(ore, dict):
                self.keyword = ore.get("keyword") or self.keyword
                self.declared_name = ore.get("declaredName")
                self.condition = ore.get("condition")
                self.has_semi = bool(ore.get("hasSemi"))

    def dump(self):
        output = []
        if self.prefix is not None:
            output.append(self.prefix.dump())
        # `if <cond> then X` guarded form
        if self.condition:
            output.extend(["if", self.condition])
        output.append(self.keyword)
        if self.declared_name:
            output.append(self.declared_name)
        text = " ".join(output)
        if self.has_semi and not text.rstrip().endswith(";"):
            text += ";"
        return text

    def get_definition(self):
        return {
            "name": self.__class__.__name__,
            "prefix": self.prefix.get_definition() if self.prefix else None,
            "ownedRelatedElement": {
                "name": "ActionTargetSuccession",
                "keyword": self.keyword,
                "declaredName": self.declared_name,
                "condition": self.condition,
                "hasSemi": self.has_semi,
                "ownedRelationship": [],
            },
        }


class GuardedSuccessionMember:
    # guardedSuccessionMember : memberPrefix guardedSuccession
    # guardedSuccession: (SUCCESSION usageDeclaration?)? FIRST featureChainMember
    #   guardExpressionMember? THEN transitionSuccessionMember usageBody?
    # Dump form: `succession S first A1 if <cond> then A2;`
    def __init__(self, definition):
        self.prefix = None
        self.keyword = "succession"
        self.declared_name = None
        self.source_name = None
        self.condition = None
        self.target_name = None
        self.has_semi = False
        if valid_definition(definition, self.__class__.__name__):
            if definition.get("prefix") is not None:
                self.prefix = MemberPrefix(definition["prefix"])
            ore = definition.get("ownedRelatedElement") or {}
            if isinstance(ore, dict):
                self.keyword = ore.get("keyword") or self.keyword
                self.declared_name = ore.get("declaredName")
                self.source_name = ore.get("sourceName")
                self.condition = ore.get("condition")
                self.target_name = ore.get("targetName")
                self.has_semi = bool(ore.get("hasSemi"))

    def dump(self):
        output = []
        if self.prefix is not None:
            output.append(self.prefix.dump())
        if self.keyword and self.declared_name:
            output.extend([self.keyword, self.declared_name])
        if self.source_name:
            output.extend(["first", self.source_name])
        if self.condition:
            output.extend(["if", self.condition])
        if self.target_name:
            output.extend(["then", self.target_name])
        text = " ".join(output)
        if text and not text.rstrip().endswith(";"):
            text += ";"
        return text

    def get_definition(self):
        return {
            "name": self.__class__.__name__,
            "prefix": self.prefix.get_definition() if self.prefix else None,
            "ownedRelatedElement": {
                "name": "GuardedSuccession",
                "keyword": self.keyword,
                "declaredName": self.declared_name,
                "sourceName": self.source_name,
                "condition": self.condition,
                "targetName": self.target_name,
                "hasSemi": self.has_semi,
                "ownedRelationship": [],
            },
        }


class SendNode:
    # SendNode :
    # 	prefix=OccurrenceUsagePrefix declaration=SendNodeDeclaration body=ActionBody
    # ;
    def __init__(self, definition):
        self.prefix = None
        self.declaration = None
        self.body = None
        if valid_definition(definition, self.__class__.__name__):
            if definition.get("prefix") is not None:
                self.prefix = OccurrenceUsagePrefix(definition["prefix"])
            if definition.get("declaration") is not None:
                self.declaration = SendNodeDeclaration(definition["declaration"])
            if definition.get("body") is not None:
                self.body = ActionBody(definition["body"])

    def dump(self):
        output = []
        if self.prefix is not None:
            output.append(self.prefix.dump())
        if self.declaration is not None:
            output.append(self.declaration.dump())
        if self.body is not None:
            output.append(self.body.dump())
        return " ".join(output)

    def get_definition(self):
        output = {
            "name": self.__class__.__name__,
            "prefix": None,
            "declaration": None,
            "body": None,
        }
        if self.prefix is not None:
            output["prefix"] = self.prefix.get_definition()
        if self.declaration is not None:
            output["declaration"] = self.declaration.get_definition()
        if self.body is not None:
            output["body"] = self.body.get_definition()
        return output


class AcceptNode:
    # AcceptNode :
    # 	prefix=OccurrenceUsagePrefix declaration=AcceptNodeDeclaration body=ActionBody
    # ;
    def __init__(self, definition):
        self.prefix = None
        self.declaration = None
        self.body = None
        if valid_definition(definition, self.__class__.__name__):
            if definition.get("prefix") is not None:
                self.prefix = OccurrenceUsagePrefix(definition["prefix"])
            if definition.get("declaration") is not None:
                self.declaration = AcceptNodeDeclaration(definition["declaration"])
            if definition.get("body") is not None:
                self.body = ActionBody(definition["body"])

    def dump(self):
        output = []
        if self.prefix is not None:
            output.append(self.prefix.dump())
        if self.declaration is not None:
            output.append(self.declaration.dump())
        if self.body is not None:
            output.append(self.body.dump())
        return " ".join(output)

    def get_definition(self):
        output = {
            "name": self.__class__.__name__,
            "prefix": None,
            "declaration": None,
            "body": None,
        }
        if self.prefix is not None:
            output["prefix"] = self.prefix.get_definition()
        if self.declaration is not None:
            output["declaration"] = self.declaration.get_definition()
        if self.body is not None:
            output["body"] = self.body.get_definition()
        return output


class IfNode:
    # IfNode :
    # 	prefix=OccurrenceUsagePrefix IF condition thenBody (ELSE elseBody)?
    # ;
    def __init__(self, definition):
        self.prefix = None
        self.condition = None
        self.thenBody = None
        self.elseBody = None
        self.elseIf = None
        if valid_definition(definition, self.__class__.__name__):
            if definition.get("prefix") is not None:
                self.prefix = OccurrenceUsagePrefix(definition["prefix"])
            self.condition = definition.get("condition")
            if definition.get("thenBody") is not None:
                self.thenBody = ActionBody(definition["thenBody"])
            if definition.get("elseBody") is not None:
                self.elseBody = ActionBody(definition["elseBody"])
            if definition.get("elseIf") is not None:
                self.elseIf = IfNode(definition["elseIf"])

    def dump(self):
        output = []
        if self.prefix is not None:
            output.append(self.prefix.dump())
        output.append("if")
        if self.condition is not None:
            output.append(self.condition)
        if self.thenBody is not None and len(self.thenBody.children) > 0:
            output.append(self.thenBody.dump())
        if self.elseIf is not None:
            output.append("else")
            output.append(self.elseIf.dump())
        elif self.elseBody is not None:
            output.append("else")
            output.append(self.elseBody.dump())
        return " ".join(output)

    def get_definition(self):
        output = {
            "name": self.__class__.__name__,
            "prefix": None,
            "condition": None,
            "thenBody": None,
            "elseBody": None,
            "elseIf": None,
        }
        if self.prefix is not None:
            output["prefix"] = self.prefix.get_definition()
        output["condition"] = self.condition
        if self.thenBody is not None:
            output["thenBody"] = self.thenBody.get_definition()
        if self.elseBody is not None:
            output["elseBody"] = self.elseBody.get_definition()
        if self.elseIf is not None:
            output["elseIf"] = self.elseIf.get_definition()
        return output


class WhileLoopNode:
    # WhileLoopNode :
    # 	prefix=OccurrenceUsagePrefix (WHILE condition | LOOP) body (UNTIL untilCondition)?
    # ;
    def __init__(self, definition):
        self.prefix = None
        self.keyword = None
        self.condition = None
        self.body = None
        self.until = None
        if valid_definition(definition, self.__class__.__name__):
            if definition.get("prefix") is not None:
                self.prefix = OccurrenceUsagePrefix(definition["prefix"])
            self.keyword = definition.get("keyword")
            self.condition = definition.get("condition")
            if definition.get("body") is not None:
                self.body = ActionBody(definition["body"])
            self.until = definition.get("until")

    def dump(self):
        output = []
        if self.prefix is not None:
            output.append(self.prefix.dump())
        if self.keyword is not None:
            output.append(self.keyword)
        if self.condition is not None:
            output.append(self.condition)
        if self.body is not None:
            output.append(self.body.dump())
        if self.until is not None:
            output.append("until")
            output.append(self.until)
            output.append(";")
        return " ".join(output)

    def get_definition(self):
        output = {
            "name": self.__class__.__name__,
            "prefix": None,
            "keyword": None,
            "condition": None,
            "body": None,
            "until": None,
        }
        if self.prefix is not None:
            output["prefix"] = self.prefix.get_definition()
        output["keyword"] = self.keyword
        output["condition"] = self.condition
        if self.body is not None:
            output["body"] = self.body.get_definition()
        output["until"] = self.until
        return output


class ForLoopNode:
    # ForLoopNode :
    # 	prefix=OccurrenceUsagePrefix forLoopNodeDeclaration actionBody
    # ;
    def __init__(self, definition):
        self.prefix = None
        self.declaration = None
        self.body = None
        if valid_definition(definition, self.__class__.__name__):
            if definition.get("prefix") is not None:
                self.prefix = OccurrenceUsagePrefix(definition["prefix"])
            if definition.get("declaration") is not None:
                self.declaration = ForLoopNodeDeclaration(definition["declaration"])
            if definition.get("body") is not None:
                self.body = ActionBody(definition["body"])

    def dump(self):
        output = []
        if self.prefix is not None:
            output.append(self.prefix.dump())
        if self.declaration is not None:
            output.append(self.declaration.dump())
        if self.body is not None:
            output.append(self.body.dump())
        return " ".join(output)

    def get_definition(self):
        output = {
            "name": self.__class__.__name__,
            "prefix": None,
            "declaration": None,
            "body": None,
        }
        if self.prefix is not None:
            output["prefix"] = self.prefix.get_definition()
        if self.declaration is not None:
            output["declaration"] = self.declaration.get_definition()
        if self.body is not None:
            output["body"] = self.body.get_definition()
        return output


class ControlNode:
    # ControlNode :
    # 	prefix=OccurrenceUsagePrefix keyword actionBody
    # ;
    def __init__(self, definition):
        self.prefix = None
        self.keyword = None
        self.declared_name = None
        self.body = None
        if valid_definition(definition, self.__class__.__name__):
            if definition.get("prefix") is not None:
                self.prefix = OccurrenceUsagePrefix(definition["prefix"])
            self.keyword = definition.get("keyword")
            self.declared_name = definition.get("declaredName")
            if definition.get("body") is not None:
                self.body = ActionBody(definition["body"])

    def dump(self):
        output = []
        if self.prefix is not None:
            output.append(self.prefix.dump())
        if self.keyword is not None:
            output.append(self.keyword)
        if self.declared_name:
            output.append(self.declared_name)
        if self.body is not None:
            output.append(self.body.dump())
        return " ".join(output)

    def get_definition(self):
        output = {
            "name": self.__class__.__name__,
            "prefix": None,
            "keyword": None,
            "declaredName": None,
            "body": None,
        }
        if self.prefix is not None:
            output["prefix"] = self.prefix.get_definition()
        output["keyword"] = self.keyword
        output["declaredName"] = self.declared_name
        if self.body is not None:
            output["body"] = self.body.get_definition()
        return output


class TerminateNode:
    # TerminateNode :
    # 	prefix=OccurrenceUsagePrefix actionNodeUsageDeclaration? TERMINATE nodeParameterMember? actionBody
    # ;
    def __init__(self, definition):
        self.prefix = None
        self.declaration = None
        self.target = None
        self.body = None
        if valid_definition(definition, self.__class__.__name__):
            if definition.get("prefix") is not None:
                self.prefix = OccurrenceUsagePrefix(definition["prefix"])
            if definition.get("declaration") is not None:
                self.declaration = ActionNodeUsageDeclaration(definition["declaration"])
            if definition.get("target") is not None:
                self.target = NodeParameterMember(definition["target"])
            if definition.get("body") is not None:
                self.body = ActionBody(definition["body"])

    def dump(self):
        output = []
        if self.prefix is not None:
            output.append(self.prefix.dump())
        if self.declaration is not None:
            output.append(self.declaration.dump())
        output.append("terminate")
        if self.target is not None:
            output.append(self.target.dump())
        if self.body is not None:
            output.append(self.body.dump())
        return " ".join(output)

    def get_definition(self):
        output = {
            "name": self.__class__.__name__,
            "prefix": None,
            "declaration": None,
            "target": None,
            "body": None,
        }
        if self.prefix is not None:
            output["prefix"] = self.prefix.get_definition()
        if self.declaration is not None:
            output["declaration"] = self.declaration.get_definition()
        if self.target is not None:
            output["target"] = self.target.get_definition()
        if self.body is not None:
            output["body"] = self.body.get_definition()
        return output


class ActionNode:
    # ActionNode :
    # 	  node=SendNode
    #   | node=AcceptNode
    #   | node=AssignmentNode
    # 	| node=IfNode
    #   | node=WhileLoopNode
    #   | node=ForLoopNode
    # 	| node=ControlNode
    #   | node=TerminateNode
    # ;
    def __init__(self, definition):
        if valid_definition(definition, self.__class__.__name__):
            self.children = globals()[definition["node"]["name"]](definition["node"])

    def dump(self):
        return self.children.dump()

    def get_definition(self):
        return {
            "name": self.__class__.__name__,
            "node": self.children.get_definition() if self.children else None,
        }


class EmptySuccessionMember:
    def __init__(self, definition):
        if valid_definition(definition, self.__class__.__name__):
            self.children = EmptySuccession(definition["ownedRelatedElement"][0])

    def dump(self):
        return self.children.dump()

    def get_definition(self):
        return {
            "name": self.__class__.__name__,
            "ownedRelatedElement": [self.children.get_definition()] if self.children else [],
        }


class EmptySuccession:
    def __init__(self, definition):
        self.children = None
        if definition is not None and valid_definition(definition, self.__class__.__name__):
            owned_rel = definition.get("ownedRelationship")
            if owned_rel and len(owned_rel) > 0:
                self.children = MultiplicitySourceEndMember(owned_rel)

    def dump(self):
        output = ["then"]
        if self.children:
            output.append(self.children.dump())
        return " ".join(output)

    def get_definition(self):
        return {
            "name": self.__class__.__name__,
            "ownedRelationship": [self.children.get_definition()] if self.children else [],
        }


class MultiplicitySourceEndMember:
    def __init__(self, definition):
        if valid_definition(definition, self.__class__.__name__):
            self.children = MultiplicitySourceEnd(definition["ownedRelatedElement"])

    def dump(self):
        return self.children.dump()

    def get_definition(self):
        return {
            "name": self.__class__.__name__,
            "ownedRelatedElement": self.children.get_definition() if self.children else None,
        }


class MultiplicitySourceEnd:
    def __init__(self, definition):
        self.children = []
        if valid_definition(definition, self.__class__.__name__):
            for child in definition["ownedRelatedElement"]:
                self.children.append(OwnedMultiplicity(child))

    def dump(self):
        return " ".join([x.dump() for x in self.children])

    def get_definition(self):
        return {
            "name": self.__class__.__name__,
            "ownedRelatedElement": [x.get_definition() for x in self.children],
        }


class StructureUsageMember:
    def __init__(self, definition):
        self.prefix = None
        self.children = []
        if valid_definition(definition, self.__class__.__name__):
            if definition["prefix"] is not None:
                self.prefix = MemberPrefix(definition["prefix"])
            for child in definition["ownedRelatedElement"]:
                self.children.append(StructureUsageElement(child))

    def dump(self):
        output = []
        if self.prefix is not None:
            output.append(self.prefix.dump())
        o2 = []
        for child in self.children:
            o2.append(child.dump())
        output.append("\n".join(o2))
        return "".join(output)

    def get_definition(self):
        return {
            "name": self.__class__.__name__,
            "prefix": self.prefix.get_definition() if self.prefix else None,
            "ownedRelatedElement": [x.get_definition() for x in self.children],
        }


class BehaviorUsageMember:
    def __init__(self, definition):
        self.prefix = None
        self.children = []
        if valid_definition(definition, self.__class__.__name__):
            if definition["prefix"] is not None:
                self.prefix = MemberPrefix(definition["prefix"])
            if definition["ownedRelatedElement"] is not None:
                rel = definition["ownedRelatedElement"]
                if isinstance(rel, list):
                    rel = rel[0] if rel else None
                if rel is not None:
                    self.children.append(
                        BehaviorUsageElement(rel)
                    )

    def dump(self):
        output = []
        if self.prefix is not None:
            output.append(self.prefix.dump())
        for child in self.children:
            output.append(child.dump())
        return " ".join(output)

    def get_definition(self):
        output = {
            "name": self.__class__.__name__,
            "prefix": None,
            "ownedRelatedElement": [],
        }
        if self.prefix is not None:
            output["prefix"] = self.prefix.get_definition()

        for child in self.children:
            output["ownedRelatedElement"].append(child.get_definition())

        return output


class ConstraintUsage:
    # ConstraintUsage :
    # 	prefix=OccurrenceUsagePrefix ConstraintUsageKeyword declaration=CalculationUsageDeclaration body=CalculationBody
    # ;
    def __init__(self, definition=None):
        self.prefix = None
        self.declaration = None
        self.keyword = "constraint"
        if definition is not None:
            if valid_definition(definition, self.__class__.__name__):
                if definition["prefix"] is not None:
                    self.prefix = OccurrenceUsagePrefix(definition["prefix"])
                if definition["declaration"] is not None:
                    self.declaration = CalculationUsageDeclaration(
                        definition["declaration"]
                    )
                self.body = CalculationBody(definition["body"])
        else:
            self.declaration = CalculationUsageDeclaration()
            self.body = CalculationBody()

    def dump(self):
        output = []
        if self.prefix is not None:
            output.append(self.prefix.dump())
        output.append(self.keyword)
        if self.declaration is not None:
            output.append(self.declaration.dump())
        output.append(self.body.dump())
        return " ".join(output)

    def get_definition(self):
        output = {"name": self.__class__.__name__, "prefix": None, "declaration": None}
        if self.prefix is not None:
            output["prefix"] = self.prefix.get_definition()
        if self.declaration is not None:
            output["declaration"] = self.declaration.get_definition()
        output["body"] = self.body.get_definition()
        return output


class AssertConstraintUsage:
    def __init__(self, definition):
        self.prefix = None
        self.keyword = "assert"
        self.keyword_constraint = "constraint"
        self.children = []
        self.fsp = None
        self.declaration = None
        if valid_definition(definition, self.__class__.__name__):
            if definition["prefix"] is not None:
                self.prefix = OccurrenceUsagePrefix(definition["prefix"])

            self.isNegated = definition["isNegated"]
            if len(definition["ownedRelationship"]) > 0:
                if definition["featurespecializationpart"] is not None:
                    self.fsp = FeatureSpecializationPart(
                        definition["featurespecializationpart"]
                    )
                for child in definition["ownedRelationship"]:
                    self.children.append(OwnedReferenceSubsetting(child))
            else:
                if definition["declaration"] is not None:
                    self.declaration = UsageDeclaration(definition["declaration"])
            self.body = CalculationBody(definition["body"])

    def dump(self):
        output = []
        if self.prefix is not None:
            output.append(self.prefix.dump())

        output.append(self.keyword)
        if self.isNegated:
            output.append("not")

        if len(self.children) == 0:
            output.append(self.keyword_constraint)
            if self.declaration is not None:
                output.append(self.declaration.dump())
        else:
            for child in self.children:
                output.append(child.dump())
            if self.fsp is not None:
                output.append(self.fsp.dump())

        output.append(self.body.dump())

        return " ".join(output)

    def get_definition(self):
        output = {
            "name": self.__class__.__name__,
            "prefix": self.prefix.get_definition() if self.prefix else None,
            "isNegated": self.isNegated,
            "ownedRelationship": [child.get_definition() for child in self.children],
            "featurespecializationpart": self.fsp.get_definition() if self.fsp else None,
            "declaration": self.declaration.get_definition() if self.declaration else None,
            "body": self.body.get_definition(),
        }
        return output


class CalculationBody:
    def __init__(self, definition=None):
        self.children = []
        if definition is not None:
            if valid_definition(definition, self.__class__.__name__):
                for child in definition["part"]:
                    self.children.append(CalculationBodyPart(child))

    def dump(self):
        if len(self.children) == 0:
            return ";"
        else:
            return "{\n" + "\n".join([x.dump() for x in self.children]) + "\n}"

    def get_definition(self):
        output = {"name": self.__class__.__name__, "part": []}
        for child in self.children:
            output["part"].append(child.get_definition())
        return output


class CalculationBodyPart:
    def __init__(self, definition=None):
        self.children = []
        self.rem = []
        if definition is not None:
            if valid_definition(definition, self.__class__.__name__):
                for child in definition["item"]:
                    self.children.append(CalculationBodyItem(child))
                for child in definition["ownedRelationship"]:
                    self.rem.append(ResultExpressionMember(child))

    def dump(self):
        output = []
        for child in self.children:
            output.append(child.dump())
        for child in self.rem:
            output.append(child.dump())
        return "\n".join(output)

    def get_definition(self):
        output = {"name": self.__class__.__name__, "item": [], "ownedRelationship": []}
        for child in self.children:
            output["item"].append(child.get_definition())
        for child in self.rem:
            output["ownedRelationship"].append(child.get_definition())
        return output


class CalculationBodyItem:
    def __init__(self, definition=None):
        self.children = []
        if definition is not None:
            if valid_definition(definition, self.__class__.__name__):
                if definition["item"] is not None:
                    self.children.append(ActionBodyItem(definition["item"]))
                elif definition["ownedRelationship"] is not None:
                    self.children.append(
                        ReturnParameterMember(definition["ownedRelationship"])
                    )

    def dump(self):
        return "".join([x.dump() for x in self.children])

    def get_definition(self):
        output = {"name": self.__class__.__name__, "item": None, "ownedRelationship": None}
        if len(self.children) > 0:
            child = self.children[0]
            if hasattr(child, 'get_definition'):
                child_def = child.get_definition()
                if child_def.get("name") == "ActionBodyItem":
                    output["item"] = child_def
                elif child_def.get("name") == "ReturnParameterMember":
                    output["ownedRelationship"] = child_def
        return output


class ReturnParameterMember:
    def __init__(self, definition):
        self.prefix = None
        self.keyword = "return"
        self.children = []
        if valid_definition(definition, self.__class__.__name__):
            if definition["prefix"] is not None:
                self.prefix = MemberPrefix(definition["prefix"])
            self.children.append(UsageElement(definition["ownedRelatedElement"]))

    def dump(self):
        output = []
        if self.prefix is not None:
            output.append(self.prefix.dump())
        output.append(self.keyword)
        for child in self.children:
            output.append(child.dump())
        return " ".join(output)

    def get_definition(self):
        return {
            "name": self.__class__.__name__,
            "prefix": self.prefix.get_definition() if self.prefix else None,
            "ownedRelatedElement": self.children[0].get_definition() if self.children else None,
        }


class ResultExpressionMember:
    def __init__(self, definition):
        self.prefix = None
        if valid_definition(definition, self.__class__.__name__):
            if definition["prefix"] is not None:
                self.prefix = MemberPrefix(definition["prefix"])
            self.children = OwnedExpression(definition["ownedRelatedElement"])

    def dump(self):
        output = []
        if self.prefix is not None:
            output.append(self.prefix.dump())
        output.append(self.children.dump())
        return "".join(output)

    def get_definition(self):
        output = {
            "name": self.__class__.__name__,
            "prefix": self.prefix.get_definition() if self.prefix else None,
            "ownedRelatedElement": self.children.get_definition(),
        }
        return output


class AnalysisCaseUsage:
    # AnalysisCaseUsage :
    # 	prefix=OccurrenceUsagePrefix AnalysisCaseUsageKeyword
    #   declaration=CalculationUsageDeclaration body=CaseBody
    # ;
    def __init__(self, definition=None):
        self.prefix = None
        self.keyword = "analysis"
        self.declaration = None
        self.body = None
        if definition is not None:
            if valid_definition(definition, self.__class__.__name__):
                if definition["prefix"] is not None:
                    self.prefix = OccurrenceUsagePrefix(definition["prefix"])
                self.declaration = CalculationUsageDeclaration(definition["declaration"])
                self.body = CaseBody(definition["body"])
        else:
            self.declaration = CalculationUsageDeclaration()
            self.body = CaseBody()

    def dump(self):
        output = []
        if self.prefix is not None:
            output.append(self.prefix.dump())
        output.append(self.keyword)
        output.append(self.declaration.dump())
        output.append(self.body.dump())
        return " ".join(output)

    def get_definition(self):
        output = {"name": self.__class__.__name__, "prefix": None}
        if self.prefix is not None:
            output["prefix"] = self.prefix.get_definition()
        output["declaration"] = self.declaration.get_definition()
        output["body"] = self.body.get_definition()
        return output


class CaseUsage:
    # caseUsage : occurrenceUsagePrefix CASE constraintUsageDeclaration caseBody
    def __init__(self, definition=None):
        self.prefix = None
        self.keyword = "case"
        self.declaration = None
        self.body = None
        if definition is not None:
            if valid_definition(definition, self.__class__.__name__):
                if definition["prefix"] is not None:
                    self.prefix = OccurrenceUsagePrefix(definition["prefix"])
                self.declaration = CalculationUsageDeclaration(definition["declaration"])
                self.body = CaseBody(definition["body"])
        else:
            self.declaration = CalculationUsageDeclaration()
            self.body = CaseBody()

    def dump(self):
        output = []
        if self.prefix is not None:
            output.append(self.prefix.dump())
        output.append(self.keyword)
        output.append(self.declaration.dump())
        output.append(self.body.dump())
        return " ".join(output)

    def get_definition(self):
        output = {"name": self.__class__.__name__, "prefix": None}
        if self.prefix is not None:
            output["prefix"] = self.prefix.get_definition()
        output["declaration"] = self.declaration.get_definition()
        output["body"] = self.body.get_definition()
        return output


class VerificationCaseUsage:
    # verificationCaseUsage : occurrenceUsagePrefix VERIFICATION constraintUsageDeclaration caseBody
    def __init__(self, definition=None):
        self.prefix = None
        self.keyword = "verification"
        self.declaration = None
        self.body = None
        if definition is not None:
            if valid_definition(definition, self.__class__.__name__):
                if definition["prefix"] is not None:
                    self.prefix = OccurrenceUsagePrefix(definition["prefix"])
                self.declaration = CalculationUsageDeclaration(definition["declaration"])
                self.body = CaseBody(definition["body"])
        else:
            self.declaration = CalculationUsageDeclaration()
            self.body = CaseBody()

    def dump(self):
        output = []
        if self.prefix is not None:
            output.append(self.prefix.dump())
        output.append(self.keyword)
        output.append(self.declaration.dump())
        output.append(self.body.dump())
        return " ".join(output)

    def get_definition(self):
        output = {"name": self.__class__.__name__, "prefix": None}
        if self.prefix is not None:
            output["prefix"] = self.prefix.get_definition()
        output["declaration"] = self.declaration.get_definition()
        output["body"] = self.body.get_definition()
        return output


class BehaviorUsageElement:
    def __init__(self, definition):
        if valid_definition(definition, self.__class__.__name__):
            rel = definition["ownedRelationship"]
            if isinstance(rel, list):
                rel = rel[0] if rel else {"name": "StateUsage", "prefix": None}
            self.children = globals()[rel["name"]](rel)

    def dump(self):
        return self.children.dump()

    def get_definition(self):
        return {
            "name": self.__class__.__name__,
            "ownedRelationship": self.children.get_definition(),
        }


class RequirementUsage:
    # RequirementUsage :
    # 	prefix=OccurrenceUsagePrefix RequirementUsageKeyword declaration=CalculationUsageDeclaration body=RequirementBody
    # ;
    def __init__(self, definition):
        self.prefix = None
        self.keyword = "requirement"
        if valid_definition(definition, self.__class__.__name__):
            if definition["prefix"] is not None:
                self.prefix = OccurrenceUsagePrefix(definition["prefix"])
            self.declaration = CalculationUsageDeclaration(definition["declaration"])
            self.body = RequirementBody(definition["body"])

    def dump(self):
        output = []
        if self.prefix is not None:
            output.append(self.prefix.dump())
        output.append(self.keyword)
        output.append(self.declaration.dump())
        output.append(self.body.dump())
        return " ".join(output)

    def get_definition(self):
        output = {
            "name": self.__class__.__name__,
            "prefix": self.prefix.get_definition() if self.prefix else None,
            "declaration": self.declaration.get_definition(),
            "body": self.body.get_definition() if hasattr(self.body, 'get_definition') else {"name": "RequirementBody", "item": []},
        }
        return output


class PerformActionUsage:
    # PerformActionUsage :
    # 	prefix=OccurrenceUsagePrefix 'perform' declaration=PerformActionUsageDeclaration body=ActionBody
    # ;
    def __init__(self, definition):
        self.prefix = None
        self.keyword = "perform"
        if valid_definition(definition, self.__class__.__name__):
            if definition["prefix"] is not None:
                self.prefix = OccurrenceUsagePrefix(definition["prefix"])
            self.declaration = PerformActionUsageDeclaration(definition["declaration"])
            self.body = ActionBody(definition["body"])

    def dump(self):
        output = []
        if self.prefix is not None:
            output.append(self.prefix.dump())
        output.append(self.keyword)
        output.append(self.declaration.dump())
        output.append(self.body.dump())
        return " ".join(output)

    def get_definition(self):
        output = {
            "name": self.__class__.__name__,
            "prefix": self.prefix.get_definition() if self.prefix else None,
            "declaration": self.declaration.get_definition(),
            "body": self.body.get_definition(),
        }
        return output


class CalculationUsage:
    def __init__(self, definition=None):
        self.prefix = None
        self.keyword = "calc"
        self.owned_relationship = []
        if definition is not None:
            if valid_definition(definition, self.__class__.__name__):
                if definition["prefix"] is not None:
                    self.prefix = OccurrenceUsagePrefix(definition["prefix"])
                self.declaration = CalculationUsageDeclaration(definition["declaration"])
                self.body = CalculationBody(definition["body"])
                if "ownedRelationship" in definition and definition["ownedRelationship"]:
                    for rel in definition["ownedRelationship"]:
                        if rel["name"] == "OwnedReferenceSubsetting":
                            self.owned_relationship.append(OwnedReferenceSubsetting(rel))
        else:
            self.declaration = CalculationUsageDeclaration()
            self.body = CalculationBody()

    def dump(self):
        output = []
        if self.prefix is not None:
            output.append(self.prefix.dump())
        output.append(self.keyword)
        if self.owned_relationship:
            for rel in self.owned_relationship:
                output.append(":>> " + rel.dump())
        else:
            output.append(self.declaration.dump())
        output.append(self.body.dump())
        return " ".join(output)

    def get_definition(self):
        output = {"name": self.__class__.__name__, "prefix": None}
        if self.prefix is not None:
            output["prefix"] = self.prefix.get_definition()
        output["declaration"] = self.declaration.get_definition()
        output["body"] = self.body.get_definition()
        if self.owned_relationship:
            output["ownedRelationship"] = [rel.get_definition() for rel in self.owned_relationship]
        return output


class CalculationUsageDeclaration:
    def __init__(self, definition=None):
        self.declaration = None
        self.valuepart = None
        if definition is not None:
            if valid_definition(definition, self.__class__.__name__):
                if definition["declaration"] is not None:
                    self.declaration = UsageDeclaration(definition["declaration"])
                if definition["valuepart"] is not None:
                    self.valuepart = ValuePart(definition["valuepart"])
        else:
            self.declaration = UsageDeclaration()

    def dump(self):
        output = []
        if self.declaration is not None:
            output.append(self.declaration.dump())
        if self.valuepart is not None:
            output.append(self.valuepart.dump())
        return "".join(output)

    def get_definition(self):
        output = {"name": self.__class__.__name__, "declaration": None, "valuepart": None}
        if self.declaration is not None:
            output["declaration"] = self.declaration.get_definition()
        if self.valuepart is not None:
            output["valuepart"] = self.valuepart.get_definition()
        return output


class ActionUsage:
    def __init__(self, definition=None):
        self.prefix = None
        if definition is None:
            self.prefix = None
            self.keyword = "action"
            self.declaration = ActionUsageDeclaration()
            self.body = ActionBody()
        elif valid_definition(definition, self.__class__.__name__):
            if definition["prefix"] is not None:
                self.prefix = OccurrenceUsagePrefix(definition["prefix"])
            self.keyword = "action"
            self.declaration = ActionUsageDeclaration(definition["declaration"])
            self.body = ActionBody(definition["body"])
        else:
            raise TypeError("This does not seem to be valid.")

    def dump(self):
        output = []
        if self.prefix is not None:
            output.append(self.prefix.dump())
        output.append(self.keyword)
        output.append(self.declaration.dump())
        output.append(self.body.dump())
        return " ".join(output)

    def get_definition(self):
        output = {"name": self.__class__.__name__, "prefix": None}
        if self.prefix is not None:
            output["prefix"] = self.prefix.get_definition()
        output["declaration"] = self.declaration.get_definition()
        output["body"] = self.body.get_definition()
        return output


class ActionUsageDeclaration:
    def __init__(self, definition=None):
        self.declaration = None
        self.valuepart = None
        if definition is not None:
            if valid_definition(definition, self.__class__.__name__):
                if definition["declaration"] is not None:
                    self.declaration = UsageDeclaration(definition["declaration"])

                if definition["valuepart"] is not None:
                    self.valuepart = ValuePart(definition["valuepart"])
        else:
            self.declaration = UsageDeclaration()

    def dump(self):
        output = []
        if self.declaration is not None:
            output.append(self.declaration.dump())
        if self.valuepart is not None:
            output.append(self.valuepart.dump())
        return " ".join(output)

    def get_definition(self):
        output = {"name": self.__class__.__name__, "declaration": None, "valuepart": None}
        if self.declaration is not None:
            output["declaration"] = self.declaration.get_definition()
        if self.valuepart is not None:
            output["valuepart"] = self.valuepart.get_definition()
        return output


class FlowConnectionDefinition:
    def __init__(self, definition=None):
        self.prefix = None
        self.keyword = "flow def"
        if definition is not None:
            if valid_definition(definition, self.__class__.__name__):
                if definition["prefix"] is not None:
                    prefix_name = definition["prefix"].get("name", "DefinitionPrefix")
                    self.prefix = globals()[prefix_name](definition["prefix"])

                self.definition = Definition(definition["definition"])
        else:
            self.definition = Definition()

    def dump(self):
        output = []
        if self.prefix is not None:
            output.append(self.prefix.dump())
        output.append(self.keyword)
        output.append(self.definition.dump())
        return " ".join(output)

    def get_definition(self):
        output = {"name": self.__class__.__name__, "prefix": None}
        if self.prefix is not None:
            output["prefix"] = self.prefix.get_definition()
        output["definition"] = self.definition.get_definition()
        return output


class InterfaceDefinition:
    def __init__(self, definition):
        if valid_definition(definition, self.__class__.__name__):
            self.prefix = None
            self.keyword = "interface def"
            self.declaration = None
            self.body = None

            if definition["prefix"] is not None:
                self.prefix = OccurrenceDefinitionPrefix(definition["prefix"])

            # Handle both flat format (declaration/body at top level)
            # and nested format (declaration/body inside "definition" key)
            if "definition" in definition and definition["definition"] is not None:
                def_dict = definition["definition"]
                if isinstance(def_dict, dict) and def_dict.get("declaration") is not None:
                    self.declaration = DefinitionDeclaration(def_dict["declaration"])
                if isinstance(def_dict, dict) and def_dict.get("body") is not None:
                    body_dict = def_dict["body"]
                    if isinstance(body_dict, dict) and body_dict.get("name") in ("DefinitionBody", "InterfaceBody"):
                        self.body = InterfaceBody({"name": "InterfaceBody", "item": body_dict.get("ownedRelatedElement", [])})
                    else:
                        self.body = InterfaceBody(body_dict)
            else:
                if definition.get("declaration") is not None:
                    self.declaration = DefinitionDeclaration(definition["declaration"])
                if definition.get("body") is not None:
                    self.body = InterfaceBody(definition["body"])

    def dump(self):
        output = []
        if self.prefix is not None:
            output.append(self.prefix.dump())
        output.append(self.keyword)
        if self.declaration is not None:
            output.append(self.declaration.dump())
        if self.body is not None:
            output.append(self.body.dump())
        return " ".join(output)

    def get_definition(self):
        output = {"name": self.__class__.__name__, "prefix": None}
        if self.prefix is not None:
            output["prefix"] = self.prefix.get_definition()
        output["definition"] = {
            "name": "Definition",
            "declaration": self.declaration.get_definition() if self.declaration else None,
            "body": self.body.get_definition() if self.body else None
        }
        return output


class InterfaceBody:
    def __init__(self, definition):
        if valid_definition(definition, self.__class__.__name__):
            self.items = []
            for item in definition["item"]:
                self.items.append(InterfaceBodyItem(item))

    def dump(self):
        if len(self.items) == 0:
            return ";"
        else:
            return "{\n" + "\n".join([child.dump() for child in self.items]) + "\n}"

    def get_definition(self):
        output = {"name": self.__class__.__name__, "item": []}
        for item in self.items:
            output["item"].append(item.get_definition())
        return output


class InterfaceBodyItem:
    def __init__(self, definition):
        if valid_definition(definition, self.__class__.__name__):
            self.children = []
            for relationship in definition["ownedRelationship"]:
                if relationship["name"] == "DefinitionMember":
                    self.children.append(DefinitionMember(relationship))
                elif relationship["name"] == "VariantUsageMember":
                    print("InterfaceBodyItem: VariantUsageMember ignored")  # pragma: no cover
                elif relationship["name"] == "InterfaceNonOccurrenceUsageMember":
                    print("InterfaceBodyItem: InterfaceNonOccurrenceUsageMember ignored")  # pragma: no cover
                elif relationship["name"] == "EmptySuccessionMember":
                    print("InterfaceBodyItem: EmptySuccessionMember ignored")  # pragma: no cover
                elif relationship["name"] == "InterfaceOccurrenceUsageMember":
                    self.children.append(InterfaceOccurrenceUsageMember(relationship))
                elif relationship["name"] == "AliasMember":
                    self.children.append(AliasMember(relationship))
                elif relationship["name"] == "Import":
                    self.children.append(Import(relationship))

    def dump(self):
        return "\n".join([child.dump() for child in self.children])

    def get_definition(self):
        output = {"name": self.__class__.__name__}
        items = []
        for child in self.children:
            items.append(child.get_definition())
        output["ownedRelationship"] = items
        return output


class InterfaceOccurrenceUsageMember:
    def __init__(self, definition):
        if valid_definition(definition, self.__class__.__name__):
            self.prefix = None
            self.elements = []
            if definition["prefix"] is not None:
                self.prefix = MemberPrefix(definition["prefix"])

            for element in definition["ownedRelatedElement"]:
                self.elements.append(InterfaceOccurrenceUsageElement(element))

    def dump(self):
        output = []
        if self.prefix is not None:
            output.append(self.prefix.dump())

        for element in self.elements:
            output.append(element.dump())

        return "\n".join(output)

    def get_definition(self):
        output = {
            "name": self.__class__.__name__,
            "prefix": self.prefix.get_definition() if self.prefix else None,
            "ownedRelatedElement": [element.get_definition() for element in self.elements]
        }
        return output


class InterfaceOccurrenceUsageElement:
    def __init__(self, definition):
        if valid_definition(definition, self.__class__.__name__):
            if definition["element"]["name"] == "DefaultInterfaceEnd":
                self.element = DefaultInterfaceEnd(definition["element"])
            elif definition["element"]["name"] == "StructureUsageElement":
                self.element = StructureUsageElement(definition["element"])
            else:
                print(f"Unknown InterfaceOccurrenceUsageElement: {definition['element']['name']}")  # pragma: no cover
                self.element = None  # pragma: no cover

    def dump(self):
        if self.element is None:
            return ""
        return self.element.dump()

    def get_definition(self):
        output = {
            "name": self.__class__.__name__
        }
        if self.element is not None:
            output["element"] = self.element.get_definition()
        # Add isAbstract, isVariation, isEnd if they exist
        if hasattr(self, 'isAbstract'):
            output["isAbstract"] = self.isAbstract
        if hasattr(self, 'isVariation'):
            output["isVariation"] = self.isVariation
        if hasattr(self, 'isEnd'):
            output["isEnd"] = self.isEnd
        return output


class DefaultInterfaceEnd:
    def __init__(self, definition):
        if valid_definition(definition, self.__class__.__name__):
            self.direction = None
            self.isAbstract = definition.get("isAbstract")
            self.isVariation = definition.get("isVariation")
            self.isEnd = definition.get("isEnd")
            self.keyword = definition.get("keyword")
            self.usage = None

            if definition.get("direction") is not None:
                self.direction = FeatureDirection(definition["direction"])

            if definition.get("usage"):
                self.usage = Usage(definition["usage"])

    def dump(self):
        output = []
        if self.direction is not None:
            output.append(self.direction.dump())
        if self.isAbstract:
            output.append("abstract")
        elif self.isVariation:
            output.append("variation")
        if self.isEnd:
            output.append("end")
        if self.keyword is not None:
            output.append(self.keyword)
        if self.usage is not None:
            output.append(self.usage.dump())
        return " ".join(output)

    def get_definition(self):
        return {
            "name": self.__class__.__name__,
            "direction": self.direction.get_definition() if self.direction else None,
            "isAbstract": self.isAbstract,
            "isVariation": self.isVariation,
            "isEnd": self.isEnd,
            "keyword": self.keyword,
            "usage": self.usage.get_definition() if self.usage else None,
        }


class PortDefinition:
    def __init__(self, definition=None):
        self.keyword = "port def"
        self.prefix = None
        if definition is not None:
            if valid_definition(definition, self.__class__.__name__):
                if definition["prefix"] is not None:
                    self.prefix = DefinitionPrefix(definition["prefix"])

                if definition["definition"] is not None:
                    self.definition = Definition(definition["definition"])
                else:
                    raise AttributeError("Definition is required.")  # pragma: no cover
        else:
            self.definition = Definition()

    def dump(self):
        output = []
        if self.prefix is not None:
            output.append(self.prefix.dump())

        output.append(self.keyword)

        if self.definition is not None:
            output.append(self.definition.dump())

        return " ".join(output)

    def get_definition(self):
        output = {"name": self.__class__.__name__, "prefix": None}
        if self.prefix is not None:
            output["prefix"] = self.prefix.get_definition()

        output["definition"] = self.definition.get_definition()
        return output


class DefinitionPrefix:
    def __init__(self, definition):
        if valid_definition(definition, self.__class__.__name__):
            self.prefix = None
            self.keywords = []

            if definition["prefix"] is not None:
                self.prefix = MemberPrefix(definition["prefix"])

            for keyword in definition["keyword"]:
                self.keywords.append(DefinitionExtensionKeyword(keyword))

    def dump(self):
        output = []
        if self.prefix is not None:
            output.append(self.prefix.dump())

        for keyword in self.keywords:
            output.append(keyword.dump())
        return "".join(output)

    def get_definition(self):
        return {
            "name": self.__class__.__name__,
            "prefix": self.prefix.get_definition() if self.prefix else None,
            "keyword": [x.get_definition() for x in self.keywords],
        }


class DefinitionExtensionKeyword:
    def __init__(self, definition):
        if valid_definition(definition, self.__class__.__name__):
            self.relationships = []
            for relationship in definition["ownedRelationship"]:
                self.relationships.append(PrefixMetadataMember(relationship))

    def dump(self):
        return "".join([child.dump() for child in self.relationships])

    def get_definition(self):
        return {
            "name": self.__class__.__name__,
            "ownedRelationship": [x.get_definition() for x in self.relationships],
        }


class PrefixMetadataMember:
    def __init__(self, definition):
        self.memberElement = None
        if valid_definition(definition, self.__class__.__name__):
            if definition.get("memberElement") is not None:
                self.memberElement = QualifiedName(definition["memberElement"])

    def dump(self):
        if self.memberElement is not None:
            return "@" + self.memberElement.dump()
        return ""

    def get_definition(self):
        output = {"name": self.__class__.__name__, "memberElement": None}
        if self.memberElement is not None:
            output["memberElement"] = self.memberElement.get_definition()
        return output


class ConnectionDefinition:
    def __init__(self, definition=None):
        self.keyword = "connection def"
        self.prefix = None
        self.definition = None
        if definition is not None:
            if valid_definition(definition, self.__class__.__name__):
                if definition["prefix"] is not None:
                    self.prefix = OccurrenceDefinitionPrefix(definition["prefix"])

                if definition["definition"] is not None:
                    self.definition = Definition(definition["definition"])
        else:
            self.definition = Definition()

    def dump(self):
        output = []
        if self.prefix is not None:
            output.append(self.prefix.dump())

        output.append(self.keyword)
        if self.definition is not None:
            output.append(self.definition.dump())

        return " ".join(output)

    def get_definition(self):
        output = {"name": self.__class__.__name__, "prefix": None, "definition": None}
        if self.prefix is not None:
            output["prefix"] = self.prefix.get_definition()
        if self.definition is not None:
            output["definition"] = self.definition.get_definition()
        return output


class ItemDefinition:
    def __init__(self, definition=None):
        self.keyword = "item def"
        if definition is not None:
            if valid_definition(definition, self.__class__.__name__):
                if definition["prefix"] is not None:
                    self.prefix = OccurrenceDefinitionPrefix(definition["prefix"])
                else:
                    self.prefix = None
                self.definition = Definition(definition["definition"])
        else:
            self.prefix = None
            self.definition = Definition()

    def dump(self):
        output = []
        if self.prefix is not None:
            output.append(self.prefix.dump())

        output.append(self.keyword)
        output.append(self.definition.dump())
        return " ".join(output)

    def get_definition(self):
        output = {"name": self.__class__.__name__, "prefix": None}
        if self.prefix is not None:
            output["prefix"] = self.prefix.get_definition()
        output["definition"] = self.definition.get_definition()
        return output


class EnumerationDefinition:
    def __init__(self, definition=None):
        self.keyword = "enum def"
        if definition is not None:
            if valid_definition(definition, self.__class__.__name__):
                self.declaration = DefinitionDeclaration(definition["declaration"])
                self.body = EnumerationBody(definition["body"])
        else:
            self.declaration = DefinitionDeclaration()
            self.body = EnumerationBody()

    def dump(self):
        return " ".join([self.keyword, self.declaration.dump() + self.body.dump()])

    def get_definition(self):
        output = {"name": self.__class__.__name__}
        output["declaration"] = self.declaration.get_definition()
        output["body"] = self.body.get_definition()
        return output


class EnumerationBody:
    def __init__(self, definition=None):
        self.relationships = None
        if definition is not None:
            if valid_definition(definition, self.__class__.__name__):
                if len(definition["ownedRelationship"]) == 0:
                    self.relationships = None
                else:
                    self.relationships = []
                    for relationship in definition["ownedRelationship"]:
                        if relationship["name"] == "AnnotatingMember":
                            self.relationships.append(AnnotatingMember(relationship))
                        else:
                            self.relationships.append(EnumerationUsageMember(relationship))

    def dump(self):
        if self.relationships is None:
            return ";"
        else:
            return (
                "{\n"
                + "\n".join([child.dump() for child in self.relationships])
                + "\n}"
            )

    def get_definition(self):
        output = {"name": self.__class__.__name__, "ownedRelationship": []}
        if self.relationships is not None:
            for rel in self.relationships:
                output["ownedRelationship"].append(rel.get_definition())
        return output


class EnumerationUsageMember:
    def __init__(self, definition):
        if valid_definition(definition, self.__class__.__name__):
            if definition["prefix"] is not None:
                self.prefix = MemberPrefix(definition["prefix"])
            else:
                self.prefix = None

            self.relationships = []
            for element in definition.get("ownedRelatedElement", []):
                self.relationships.append(EnumeratedValue(element))

    def dump(self):
        output = [child.dump() for child in self.relationships]
        if self.prefix is not None:
            output.insert(0, self.prefix.dump())

        return " ".join(output)

    def get_definition(self):
        return {
            "name": self.__class__.__name__,
            "prefix": self.prefix.get_definition() if self.prefix else None,
            "ownedRelatedElement": [rel.get_definition() for rel in self.relationships]
        }


class EnumeratedValue:
    def __init__(self, definition):
        if valid_definition(definition, self.__class__.__name__):
            if definition["keyword"] is not None:
                self.keyword = definition["keyword"]
            else:
                self.keyword = None
            self.usage = Usage(definition["usage"])

    def dump(self):
        if self.keyword is not None:
            return self.keyword + " " + self.usage.dump()
        else:
            return self.usage.dump()

    def get_definition(self):
        return {
            "name": self.__class__.__name__,
            "keyword": self.keyword,
            "usage": self.usage.get_definition()
        }


class AnnotatingMember:
    def __init__(self, definition):
        if valid_definition(definition, self.__class__.__name__):
            self.children = []
            for element in definition.get("ownedRelatedElement", []):
                self.children.append(AnnotatingElement(element))

    def dump(self):
        return " ".join([child.dump() for child in self.children])

    def get_definition(self):
        return {
            "name": self.__class__.__name__,
            "ownedRelatedElement": [child.get_definition() for child in self.children],
        }


class AnnotatingElement:
    def __init__(self, definition):
        if valid_definition(definition, "AnnotatingElement"):
            if definition["ownedRelatedElement"]["name"] == "Documentation":
                self.children = Documentation(definition["ownedRelatedElement"])
            elif definition["ownedRelatedElement"]["name"] == "CommentSysML":
                self.children = CommentSysML(definition["ownedRelatedElement"])
            elif definition["ownedRelatedElement"]["name"] == "MetadataFeature":
                self.children = MetadataFeature(definition["ownedRelatedElement"])
            elif definition["ownedRelatedElement"]["name"] == "TextualRepresentation":
                self.children = TextualRepresentation(definition["ownedRelatedElement"])
            else:
                print(f"Unknown AnnotatingElement: {definition['ownedRelatedElement']['name']}")  # pragma: no cover
                self.children = None  # pragma: no cover

    def dump(self):
        return self.children.dump() if self.children is not None else ""

    def get_definition(self):
        return {
            "name": self.__class__.__name__,
            "ownedRelatedElement": self.children.get_definition()
        }


class CommentSysML:
    def __init__(self, definition):
        if valid_definition(definition, "CommentSysML"):
            self.body = definition["body"]
            if definition["identification"] is not None:
                self.identification = Identification(definition["identification"])
            else:
                self.identification = None

            self.children = []
            for relationship in definition["ownedRelationship"]:
                self.children.append(Annotation(relationship))

    def dump(self):
        if len(self.children) > 0:
            if self.identification is not None:
                id_part = self.identification.dump() + " "
            else:
                id_part = ""
            return (
                "comment "
                + id_part
                + "about "
                + ", ".join([child.dump() for child in self.children])
                + " " + self.body
            )
        else:
            if self.identification is not None:
                return "comment " + self.identification.dump() + " " + self.body
            else:
                import re
                # Anonymous block comment — no 'comment' keyword, just the raw block comment
                return re.sub(r"\n[\s]*", "\n", self.body)

    def get_definition(self):
        output = {"name": self.__class__.__name__}
        output["body"] = self.body
        if self.identification is not None:
            output["identification"] = self.identification.get_definition()
        else:
            output["identification"] = None
        owned_rel = []
        for child in self.children:
            owned_rel.append(child.get_definition())
        output["ownedRelationship"] = owned_rel
        return output


class Annotation:
    def __init__(self, definition):
        if valid_definition(definition, "Annotation"):
            self.annotation = QualifiedName(definition["annotatedElement"])

    def dump(self):
        return self.annotation.dump()

    def get_definition(self):
        return {
            "name": self.__class__.__name__,
            "annotatedElement": self.annotation.get_definition()
        }


class Documentation:
    def __init__(self, definition):
        if valid_definition(definition, "Documentation"):
            self.keyword = "doc"
            if definition["identification"] is not None:
                self.identification = Identification(definition["identification"])
            else:
                self.identification = None

            self.body = definition["body"]

    def dump(self):
        if self.identification is not None:
            return " ".join([self.keyword, self.identification.dump(), self.body])
        else:
            return " ".join([self.keyword, self.body])

    def get_definition(self):
        output = {"name": self.__class__.__name__}
        output["body"] = self.body
        if self.identification is not None:
            output["identification"] = self.identification.get_definition()
        else:
            output["identification"] = None
        output["ownedRelationship"] = []
        return output


class TextualRepresentation:
    # textualRepresentation
    #   : (REP identification?)? LANGUAGE DOUBLE_STRING REGULAR_COMMENT
    #   ;
    def __init__(self, definition):
        if valid_definition(definition, "TextualRepresentation"):
            self.identification = None
            if definition.get("identification") is not None:
                self.identification = Identification(definition["identification"])
            
            self.language = definition.get("language", "")
            self.body = definition.get("body", "")

    def dump(self):
        output = []
        if self.identification is not None:
            output.append("rep")
            output.append(self.identification.dump())
        output.append("language")
        output.append(f'"{self.language}"')
        output.append(self.body)
        return " ".join(output)

    def get_definition(self):
        output = {
            "name": self.__class__.__name__,
            "identification": self.identification.get_definition() if self.identification else None,
            "language": self.language,
            "body": self.body
        }
        return output


class MetadataFeature:
    # metadataFeature
    #   : (prefixMetadataMember)* (AT_SIGN | METADATA) metadataFeatureDeclaration (
    #       ABOUT annotation ( COMMA annotation)*
    #   )? metadataBody
    #   ;
    def __init__(self, definition):
        if valid_definition(definition, self.__class__.__name__):
            self.prefix = []
            for p in definition.get("prefixMetadataMember", []):
                self.prefix.append(PrefixMetadataMember(p))

            self.identification = None
            if definition.get("identification") is not None:
                self.identification = Identification(definition["identification"])

            self.typing = None
            if definition.get("ownedFeatureTyping") is not None:
                self.typing = OwnedFeatureTyping(definition["ownedFeatureTyping"])

            self.annotations = []
            for ann in definition.get("ownedRelationship_about", []):
                self.annotations.append(Annotation(ann))

            self.body = definition.get("body", "")
            # Issue #8: structured per-element capture so consumers can
            # read individual key = value features without re-parsing
            # the raw body text. ``dump()`` continues to use the raw
            # ``self.body`` so whitespace is preserved exactly.
            self.bodyFeatures = list(definition.get("bodyFeatures", []))

    def dump(self):
        output = []
        for p in self.prefix:
            output.append(p.dump())
        output.append("@")
        if self.identification is not None:
            output.append(self.identification.dump())
        if self.typing is not None:
            output.append(":")
            output.append(self.typing.dump())
        if self.annotations:
            output.append("about")
            output.append(", ".join([a.dump() for a in self.annotations]))
        if self.body:
            output.append(self.body)
        return " ".join(output)

    def get_definition(self):
        output = {
            "name": self.__class__.__name__,
            "prefixMetadataMember": [p.get_definition() for p in self.prefix],
            "identification": self.identification.get_definition() if self.identification else None,
            "ownedFeatureTyping": self.typing.get_definition() if self.typing else None,
            "ownedRelationship_about": [a.get_definition() for a in self.annotations],
            "body": self.body,
            "bodyFeatures": list(self.bodyFeatures),
        }
        return output


class PrefixMetadataMember:
    def __init__(self, definition):
        if valid_definition(definition, "PrefixMetadataMember"):
            self.visibility = definition.get("visibility", "")
            self.direction = definition.get("direction", "")

    def dump(self):
        output = []
        if self.visibility:
            output.append(self.visibility)
        if self.direction:
            output.append(self.direction)
        return " ".join(output)

    def get_definition(self):
        return {
            "name": self.__class__.__name__,
            "visibility": self.visibility,
            "direction": self.direction
        }


class OccurrenceUsageBody:
    # OccurrenceUsageBody — used by non-action occurrence usages
    # Similar to ActionBody but for general occurrence usages
    def __init__(self, definition):
        if valid_definition(definition, "OccurrenceUsageBody"):
            self.children = []
            for item in definition.get("ownedRelationship", []):
                if item.get("name") == "InitialNodeMember":
                    self.children.append(InitialNodeMember(item))
                elif item.get("name") == "ActionNodeMember":
                    self.children.append(ActionNodeMember(item))
                else:
                    print(f"OccurrenceUsageBody: Unknown item type {item.get('name')}")

    def dump(self):
        if not self.children:
            return ";"
        return " { " + "; ".join([c.dump() for c in self.children]) + " }"

    def get_definition(self):
        return {
            "name": self.__class__.__name__,
            "ownedRelationship": [c.get_definition() for c in self.children]
        }


class AttributeDefinition:
    def __init__(self, definition=None):
        self.keyword = "attribute def"
        if definition is not None:
            if valid_definition(definition, "AttributeDefinition"):
                if definition["prefix"] is not None:
                    self.prefix = OccurrenceDefinitionPrefix(definition["prefix"])
                else:
                    self.prefix = None
                self.definition = Definition(definition["definition"])
        else:
            self.prefix = None
            self.definition = Definition()

    def dump(self):
        return " ".join(
            filter(None, (self.prefix, self.keyword, self.definition.dump()))
        )

    def get_definition(self):
        output = {"name": self.__class__.__name__, "prefix": None}
        if self.prefix is not None:
            output["prefix"] = self.prefix.get_definition()
        output["definition"] = self.definition.get_definition()
        return output


class PartDefinition:
    def __init__(self, definition=None):
        if definition is not None:
            if valid_definition(definition, "PartDefinition"):
                if definition["prefix"] is not None:
                    self.prefix = OccurrenceDefinitionPrefix(definition["prefix"])
                else:
                    self.prefix = None
                self.keyword = "part def"
                self.definition = Definition(definition["definition"])
        else:
            self.prefix = None
            self.keyword = "part def"
            self.definition = Definition()

    def dump(self):
        output = []
        if self.prefix is not None:
            output.append(self.prefix.dump())

        output.append(self.keyword)
        output.append(self.definition.dump())

        return " ".join(output)

    def get_definition(self):
        output = {"name": self.__class__.__name__, "prefix": None}
        if self.prefix is not None:
            output["prefix"] = self.prefix.get_definition()

        output["definition"] = self.definition.get_definition()

        return output


class OccurrenceDefinitionPrefix:
    def __init__(self, definition):
        if valid_definition(definition, "OccurrenceDefinitionPrefix"):
            if definition["prefix"] is not None:
                self.prefix = BasicDefinitionPrefix(definition["prefix"])
            else:
                self.prefix = None

            self.isIndividual = definition["isIndividual"]

            self.children = []
            if len(definition["ownedRelationship"]) > 0:
                for relationship in definition["ownedRelationship"]:
                    self.children.append(LifeClassMembership(relationship))

            if len(definition["keyword"]) > 0:
                self.keywords = []
                for kw in definition["keyword"]:
                    self.keywords.append(kw)
            else:
                self.keywords = []

    def dump(self):
        output = []
        if self.prefix is not None:
            output.append(self.prefix.dump())

        if self.isIndividual:
            output.append("individual")

        for kw in self.keywords:
            output.append(kw)

        for child in self.children:
            output.append(child.dump())

        return " ".join(output)

    def get_definition(self):
        return {
            "name": self.__class__.__name__,
            "prefix": self.prefix.get_definition() if self.prefix else None,
            "isIndividual": self.isIndividual,
            "ownedRelationship": [c.get_definition() for c in self.children],
            "keyword": self.keywords,
        }


class BasicDefinitionPrefix:
    def __init__(self, definition):
        if valid_definition(definition, "BasicDefinitionPrefix"):
            self.isAbstract = definition["isAbstract"]
            self.isVariation = definition["isVariation"]

    def dump(self):
        # Only one or the other
        if self.isAbstract:
            output = "abstract"
        if self.isVariation:
            output = "variation"
        return output

    def get_definition(self):
        return {
            "name": self.__class__.__name__,
            "isAbstract": self.isAbstract,
            "isVariation": self.isVariation,
        }


class LifeClassMembership:
    def __init__(self, definition):
        self.memberElement = None
        if valid_definition(definition, "LifeClassMembership"):
            if definition.get("memberElement") is not None:
                self.memberElement = QualifiedName(definition["memberElement"])

    def dump(self):
        if self.memberElement is not None:
            return "lifeClass " + self.memberElement.dump()
        return ""

    def get_definition(self):
        output = {"name": self.__class__.__name__, "memberElement": None}
        if self.memberElement is not None:
            output["memberElement"] = self.memberElement.get_definition()
        return output


class Definition:
    def __init__(self, definition=None):
        if definition is not None:
            if valid_definition(definition, "Definition"):
                self.declaration = DefinitionDeclaration(definition["declaration"])
                self.body = DefinitionBody(definition["body"])
        else:
            self.declaration = DefinitionDeclaration()
            self.body = DefinitionBody()

    def dump(self):
        return "".join([self.declaration.dump(), self.body.dump()])

    def get_definition(self):
        return {
            "name": self.__class__.__name__,
            "body": self.body.get_definition(),
            "declaration": self.declaration.get_definition(),
        }


class DefinitionDeclaration:
    def __init__(self, definition=None):
        if definition is not None:
            if valid_definition(definition, self.__class__.__name__):
                if "identification" in definition:
                    if definition["identification"] is not None:
                        self.identification = Identification(
                            definition["identification"]
                        )
                    else:
                        self.identification = None
                else:
                    self.identification = None

                if "subclassificationpart" in definition:
                    if definition["subclassificationpart"] is not None:
                        self.subclassificationpart = SubclassificationPart(
                            definition["subclassificationpart"]
                        )
                    else:
                        self.subclassificationpart = None
                else:
                    self.subclassificationpart = None

        else:
            self.identification = Identification()
            self.subclassificationpart = None

    def dump(self):
        output = []
        if self.identification is not None:
            output.append(self.identification.dump())
        if self.subclassificationpart is not None:
            output.append(self.subclassificationpart.dump())
        return " ".join(output)

    def get_definition(self):
        output = {
            "name": self.__class__.__name__,
            "identification": None,
            "subclassificationpart": None,
        }
        if self.identification is not None:
            output["identification"] = self.identification.get_definition()

        if self.subclassificationpart is not None:
            output["subclassificationpart"] = (
                self.subclassificationpart.get_definition()
            )

        return output


class SubclassificationPart:
    def __init__(self, definition):
        if valid_definition(definition, "SubclassificationPart"):
            self.keyword = ":> "
            self.children = []
            for relationship in definition["ownedRelationship"]:
                self.children.append(OwnedSubclassification(relationship))

    def dump(self):
        return self.keyword + ", ".join([child.dump() for child in self.children])

    def get_definition(self):
        output = {
            "name": self.__class__.__name__,
            "ownedRelationship": [],
        }
        for child in self.children:
            output["ownedRelationship"].append(child.get_definition())
        return output


class OwnedSubclassification:
    def __init__(self, definition):
        if valid_definition(definition, "OwnedSubclassification"):
            self.name = QualifiedName(definition["superclassifier"])

    def dump(self):
        return self.name.dump()

    def get_definition(self):
        return {
            "name": self.__class__.__name__,
            "superclassifier": self.name.get_definition(),
        }


class DefinitionBody:
    def __init__(self, definition=None):
        if definition is not None:
            if valid_definition(definition, "DefinitionBody"):
                self.children = []
                if len(definition["ownedRelatedElement"]) > 0:
                    for item in definition["ownedRelatedElement"]:
                        self.children.append(DefinitionBodyItem(item))
        else:
            self.children = []

    def dump(self):
        if len(self.children) == 0:
            return ";"
        else:
            output = []
            for child in self.children:
                output.append(child.dump())
            return " {\n" + "\n".join(output) + "\n}"

    def get_definition(self):
        output = {"name": self.__class__.__name__, "ownedRelatedElement": []}
        for child in self.children:
            output["ownedRelatedElement"].append(child.get_definition())

        return output


class DefinitionBodyItem:
    def __init__(self, definition):
        if valid_definition(definition, "DefinitionBodyItem"):
            self.children = []
            if len(definition["ownedRelationship"]) > 0:
                for item in definition["ownedRelationship"]:
                    if item["name"] == "OccurrenceUsageMember":
                        self.children.append(OccurrenceUsageMember(item))
                    elif item["name"] == "NonOccurrenceUsageMember":
                        self.children.append(NonOccurrenceUsageMember(item))
                    elif item["name"] == "DefinitionMember":
                        self.children.append(DefinitionMember(item))
                    else:
                        print(f"DefinitionBodyItem: unknown relationship {definition}")  # pragma: no cover

    def dump(self):
        return "\n".join([x.dump() for x in self.children])

    def get_definition(self):
        output = {"name": self.__class__.__name__}
        items = []
        for item in self.children:
            items.append(item.get_definition())
        output["ownedRelationship"] = items
        return output


class DefinitionMember:
    def __init__(self, definition):
        if valid_definition(definition, "DefinitionMember"):
            if definition["prefix"] is not None:
                self.prefix = MemberPrefix(definition["prefix"])
            else:
                self.prefix = None

            self.children = []
            for element in definition["ownedRelatedElement"]:
                self.children.append(DefinitionElement(element))

    def dump(self):
        return "\n".join([child.dump() for child in self.children])

    def get_definition(self):
        output = {
            "name": self.__class__.__name__,
            "prefix": None,
            "ownedRelatedElement": [],
        }
        if self.prefix is not None:
            output["prefix"] = self.prefix.get_definition()

        for item in self.children:
            output["ownedRelatedElement"].append(item.get_definition())
        return output


class OccurrenceUsageMember:
    def __init__(self, definition):
        if valid_definition(definition, "OccurrenceUsageMember"):
            if definition["prefix"] is not None:
                self.prefix = MemberPrefix(definition["prefix"])
            else:
                self.prefix = None

            self.children = []
            for element in definition["ownedRelatedElement"]:
                self.children.append(OccurrenceUsageElement(element))

    def dump(self):
        output = []
        for child in self.children:
            output.append(child.dump())
        return "\n".join(output)

    def get_definition(self):
        output = {
            "name": self.__class__.__name__,
            "prefix": None,
            "ownedRelatedElement": [],
        }
        if self.prefix is not None:
            output["prefix"] = self.prefix.get_definition()

        for child in self.children:
            output["ownedRelatedElement"].append(child.get_definition())

        return output


class NonOccurrenceUsageMember:
    def __init__(self, definition):
        if valid_definition(definition, "NonOccurrenceUsageMember"):
            if definition["prefix"] is not None:
                self.prefix = MemberPrefix(definition["prefix"])
            else:
                self.prefix = None

            self.children = []
            for element in definition["ownedRelatedElement"]:
                self.children.append(NonOccurrenceUsageElement(element))

    def dump(self):
        output = []
        for child in self.children:
            output.append(child.dump())
        return "\n".join(output)

    def get_definition(self):
        output = {
            "name": self.__class__.__name__,
            "prefix": None,
            "ownedRelatedElement": [],
        }
        if self.prefix is not None:
            output["prefix"] = self.prefix.get_definition()

        for child in self.children:
            output["ownedRelatedElement"].append(child.get_definition())

        return output


class UsageElement:
    def __init__(self, definition):
        if valid_definition(definition, "UsageElement"):
            if definition["ownedRelatedElement"]["name"] == "NonOccurrenceUsageElement":
                self.children = NonOccurrenceUsageElement(
                    definition["ownedRelatedElement"]
                )
            elif definition["ownedRelatedElement"]["name"] == "OccurrenceUsageElement":
                self.children = OccurrenceUsageElement(
                    definition["ownedRelatedElement"]
                )
            else:
                raise AttributeError(
                    "This does not seem to be valid."
                )  # pragma: no cover

    def dump(self):
        return self.children.dump()

    def get_definition(self):
        output = {
            "name": self.__class__.__name__,
            "ownedRelatedElement": self.children.get_definition(),
        }
        return output


class NonOccurrenceUsageElement:
    def __init__(self, definition):
        if valid_definition(definition, self.__class__.__name__):
            name = definition["ownedRelatedElement"]["name"]
            if name == "DefaultReferenceUsage":
                self.children = DefaultReferenceUsage(definition["ownedRelatedElement"])
            elif name == "AttributeUsage":
                self.children = AttributeUsage(definition["ownedRelatedElement"])
            elif name == "BindingConnector":
                self.children = BindingConnector(definition["ownedRelatedElement"])
            elif name == "Succession":
                self.children = Succession(definition["ownedRelatedElement"])
            elif name == "ReferenceUsage":
                self.children = ReferenceUsage(definition["ownedRelatedElement"])
            elif name == "ConstraintUsage":
                self.children = ConstraintUsage(definition["ownedRelatedElement"])
            elif name == "CalculationUsage":
                self.children = CalculationUsage(definition["ownedRelatedElement"])
            elif name == "MetadataUsage":
                self.children = MetadataUsage(definition["ownedRelatedElement"])
            elif name == "EndFeatureUsage":
                self.children = EndFeatureUsage(definition["ownedRelatedElement"])
            elif name == "AssertConstraintUsage":
                self.children = AssertConstraintUsage(definition["ownedRelatedElement"])
            else:
                print(f"NonOccurrenceUsageElement: unhandled {name}")  # pragma: no cover

    def dump(self):
        return self.children.dump()

    def get_definition(self):
        output = {"name": self.__class__.__name__}
        output["ownedRelatedElement"] = self.children.get_definition()
        return output


class ReferenceUsage:
    # ReferenceUsage :
    # 	prefix=RefPrefix ReferenceUsageKeyword usage=Usage
    # ;
    def __init__(self, definition):
        self.prefix = None
        self.keyword = "ref"
        if valid_definition(definition, self.__class__.__name__):
            if definition["prefix"] is not None:
                self.prefix = RefPrefix(definition["prefix"])
            self.child = Usage(definition["usage"])

    def dump(self):
        output = []
        if self.prefix is not None:
            output.append(self.prefix.dump())
        output.append(self.keyword)
        output.append(self.child.dump())
        return " ".join(output)

    def get_definition(self):
        output = {
            "name": self.__class__.__name__,
            "prefix": self.prefix.get_definition() if self.prefix else None,
            "usage": self.child.get_definition(),
        }
        return output


class EndFeatureUsage:
    # EndFeatureUsage :
    # 	prefix=EndUsagePrefix featureDeclaration usageCompletion
    # ;
    def __init__(self, definition):
        self.prefix = None
        if valid_definition(definition, self.__class__.__name__):
            if definition["prefix"] is not None:
                self.prefix = EndUsagePrefix(definition["prefix"])
            self.declaration = FeatureDeclaration(definition["usage"]["declaration"]["declaration"])
            self.completion = UsageCompletion(definition["usage"]["completion"])

    def dump(self):
        output = []
        if self.prefix is not None:
            output.append(self.prefix.dump())
        output.append(self.declaration.dump())
        output.append(self.completion.dump())
        return " ".join(output)

    def get_definition(self):
        return {
            "name": self.__class__.__name__,
            "prefix": self.prefix.get_definition() if self.prefix else None,
            "usage": {
                "declaration": {"declaration": self.declaration.get_definition() if self.declaration else None},
                "completion": self.completion.get_definition() if self.completion else None,
            },
        }


class EndUsagePrefix:
    def __init__(self, definition):
        self.prefix = None
        if valid_definition(definition, self.__class__.__name__):
            if definition["prefix"] is not None:
                self.prefix = RefPrefix(definition["prefix"])

    def dump(self):
        if self.prefix is not None:
            return self.prefix.dump()
        return ""

    def get_definition(self):
        return {
            "name": self.__class__.__name__,
            "prefix": self.prefix.get_definition() if self.prefix else None,
        }


class SatisfyRequirementUsage:
    # SatisfyRequirementUsage :
    # 	prefix=OccurrenceUsagePrefix (isAssert ?= 'assert')? ( isNegated ?= 'not' )? 'satisfy'
    # 	( ors = OwnedReferenceSubsetting fsp=FeatureSpecializationPart?
    #     | RequirementUsageKeyword declaration=UsageDeclaration?
    #   )
    #   valuepart=ValuePart? ( 'by' ssm = SatisfactionSubjectMember )?
    #   body=RequirementBody
    # ;
    def __init__(self, definition):
        self.prefix = None
        self.keyword = ["satisfy"]
        self.ors = None
        self.valuepart = None
        if valid_definition(definition, self.__class__.__name__):
            if definition["prefix"] is not None:
                self.prefix = OccurrenceUsagePrefix(definition["prefix"])
            if definition["isAssert"]:
                self.keyword.append("assert")
            else:
                self.keyword.append(None)

            if definition["isNegated"]:
                self.keyword.append("not")
            else:
                self.keyword.append(None)

            if definition["declaration"] is not None:
                self.keyword.append("requirement")
                self.declaration = UsageDeclaration(definition["declaration"])
            else:
                self.keyword.append(None)
                self.ors = OwnedReferenceSubsetting(definition["ors"])
                if definition["fsp"] is not None:
                    self.fsp = FeatureSpecializationPart(definition["fsp"])
                else:
                    self.fsp = None
            if definition["valuepart"] is not None:
                self.valuepart = ValuePart(definition["valuepart"])
            if definition["ssm"] is not None:
                self.keyword.append("by")
                self.ssm = SatisfactionSubjectMember(definition["ssm"])
            else:
                self.keyword.append(None)
                self.ssm = None
            self.body = RequirementBody(definition["body"])

    def dump(self):
        output = []
        if self.prefix is not None:
            output.append(self.prefix.dump())
        output.append(self.keyword[1])
        output.append(self.keyword[2])
        output.append(self.keyword[0])
        output.append(self.keyword[3])
        if self.ors is not None:
            output.append(self.ors.dump())
            if self.fsp is not None:
                output.append(self.fsp.dump())
        else:
            if self.declaration is not None:
                output.append(self.declaration.dump())
        if self.valuepart is not None:
            output.append(self.valuepart.dump())
        output.append(self.keyword[4])
        if self.ssm is not None:
            output.append(self.ssm.dump())
        output.append(self.body.dump())
        return " ".join(filter(None, output))

    def get_definition(self):
        output = {
            "name": self.__class__.__name__,
            "prefix": self.prefix.get_definition() if self.prefix else None,
            "isAssert": self.keyword[1] == "assert",
            "isNegated": self.keyword[2] == "not",
            "declaration": self.declaration.get_definition() if hasattr(self, 'declaration') and self.declaration else None,
            "ors": self.ors.get_definition() if self.ors else None,
            "fsp": self.fsp.get_definition() if hasattr(self, 'fsp') and self.fsp else None,
            "valuepart": self.valuepart.get_definition() if self.valuepart else None,
            "ssm": self.ssm.get_definition() if self.ssm else None,
            "body": self.body.get_definition() if hasattr(self.body, 'get_definition') else {"name": "RequirementBody", "item": []},
        }
        return output


class SatisfactionSubjectMember:
    # SatisfactionSubjectMember :
    # 	ownedRelatedElement = SatisfactionParameter
    # ;
    def __init__(self, definition):
        if valid_definition(definition, self.__class__.__name__):
            self.child = SatisfactionParameter(definition["ownedRelatedElement"])

    def dump(self):
        return self.child.dump()

    def get_definition(self):
        return {
            "name": self.__class__.__name__,
            "ownedRelatedElement": self.child.get_definition(),
        }


class SatisfactionParameter:
    # SatisfactionParameter :
    # 	ownedRelationship = SatisfactionFeatureValue
    # ;
    def __init__(self, definition):
        if valid_definition(definition, self.__class__.__name__):
            self.child = SatisfactionFeatureValue(definition["ownedRelationship"])

    def dump(self):
        return self.child.dump()

    def get_definition(self):
        return {
            "name": self.__class__.__name__,
            "ownedRelationship": self.child.get_definition(),
        }


class SatisfactionFeatureValue:
    # SatisfactionFeatureValue :
    # 	ownedRelatedElement = SatisfactionReferenceExpression
    # ;
    def __init__(self, definition):
        if valid_definition(definition, self.__class__.__name__):
            self.child = SatisfactionReferenceExpression(
                definition["ownedRelatedElement"]
            )

    def dump(self):
        return self.child.dump()

    def get_definition(self):
        return {
            "name": self.__class__.__name__,
            "ownedRelatedElement": self.child.get_definition(),
        }


class SatisfactionReferenceExpression:
    # SatisfactionReferenceExpression :
    # 	ownedRelationship = FeatureChainMember
    # ;
    def __init__(self, definition):
        if valid_definition(definition, self.__class__.__name__):
            self.child = FeatureChainMember(definition["ownedRelatedElement"])

    def dump(self):
        return self.child.dump()

    def get_definition(self):
        return {
            "name": self.__class__.__name__,
            "ownedRelatedElement": self.child.get_definition(),
        }
        return self.child.dump()


class Succession:
    def __init__(self, definition):
        self.prefix = None
        self.declaration = None
        self.keyword = "succession"
        self.children = []
        if valid_definition(definition, self.__class__.__name__):
            if definition["prefix"] is not None:
                self.prefix = MemberPrefix(definition["prefix"])

            if definition["declaration"] is not None:
                self.declaration = UsageDeclaration(definition["declaration"])

            for child in definition["ownedRelationship"]:
                self.children.append(ConnectorEndMember(child))

            self.body = DefinitionBody(definition["body"])

    def dump(self):
        output = []
        if self.prefix is not None:
            output.append(self.prefix.dump())

        if self.declaration is not None:
            output.append(self.keyword)
            output.append(self.declaration.dump())

        output.append("first")
        output.append(self.children[0].dump())
        output.append("then")
        output.append(self.children[1].dump())

        output.append(self.body.dump())

        return " ".join(output)

    def get_definition(self):
        return {
            "name": self.__class__.__name__,
            "prefix": self.prefix.get_definition() if self.prefix else None,
            "declaration": self.declaration.get_definition() if self.declaration else None,
            "ownedRelationship": [x.get_definition() for x in self.children],
            "body": self.body.get_definition(),
        }


class BindingConnector:
    def __init__(self, definition=None):
        self.prefix = None
        self.declaration = None
        self.keyword = "bind"
        self.children = []
        self.body = None
        if definition is not None:
            if valid_definition(definition, self.__class__.__name__):
                if definition.get("declaration") is not None:
                    self.declaration = UsageDeclaration(definition["declaration"])
                owned_rel = definition.get("ownedRelationship")
                if owned_rel and len(owned_rel) == 2:
                    for child in owned_rel:
                        self.children.append(ConnectorEndMember(child))
                if definition.get("body") is not None:
                    self.body = DefinitionBody(definition["body"])

    def dump(self):
        output = []
        if self.prefix is not None:
            output.append(self.prefix.dump())
        if self.declaration is not None:
            output.append("binding")
            output.append(self.declaration.dump())
        output.append(self.keyword)

        connectors = []
        for child in self.children:
            connectors.append(child.dump())
        output.append(" = ".join(connectors))

        if self.body:
            output.append(self.body.dump())

        return " ".join(output)

    def get_definition(self):
        return {
            "name": self.__class__.__name__,
            "prefix": None,
            "declaration": self.declaration.get_definition() if self.declaration else None,
            "ownedRelationship": [c.get_definition() for c in self.children],
            "body": self.body.get_definition() if self.body else None,
        }


class DefaultReferenceUsage:
    def __init__(self, definition=None):
        self.prefix = None
        self.valuepart = None
        if definition is not None:
            if valid_definition(definition, "DefaultReferenceUsage"):
                if definition["prefix"] is not None:
                    self.prefix = RefPrefix(definition["prefix"])

                self.declaration = UsageDeclaration(definition["declaration"])
                if definition["valuepart"] is not None:
                    self.valuepart = ValuePart(definition["valuepart"])

                self.body = UsageBody(definition["body"])
        else:
            self.declaration = UsageDeclaration()
            self.body = UsageBody()

    def dump(self):
        output = []
        if self.prefix is not None:
            output.append(self.prefix.dump())
        output.append(self.declaration.dump())
        if self.valuepart is not None:
            output.append(self.valuepart.dump())
        output.append(self.body.dump())

        return " ".join(output)

    def get_definition(self):
        output = {"name": self.__class__.__name__, "prefix": None, "valuepart": None}
        if self.prefix is not None:
            output["prefix"] = self.prefix.get_definition()

        if self.valuepart is not None:
            output["valuepart"] = self.valuepart.get_definition()
        output["declaration"] = self.declaration.get_definition()
        output["body"] = self.body.get_definition()
        return output


class ValuePart:
    def __init__(self, definition):
        if valid_definition(definition, "ValuePart"):
            self.relationships = []
            for relationship in definition.get("ownedRelationship", []):
                if relationship["name"] == "FeatureValue":
                    self.relationships.append(FeatureValue(relationship))
                elif relationship["name"] == "FeatureValueExpression":
                    print("ValuePart: FeatureValueExpression not yet implemented")  # pragma: no cover
                elif relationship["name"] == "EmptyAssignmentActionMember":
                    print("ValuePart: EmptyAssignmentActionMember not yet implemented")  # pragma: no cover
                else:
                    print(f"ValuePart: unknown relationship {relationship['name']}")  # pragma: no cover

    def dump(self):
        return "".join([child.dump() for child in self.relationships])

    def get_definition(self):
        output = {"name": self.__class__.__name__, "ownedRelationship": []}
        for child in self.relationships:
            output["ownedRelationship"].append(child.get_definition())
        return output


class FeatureValue:
    def __init__(self, definition):
        if valid_definition(definition, self.__class__.__name__):
            self.isDefault = definition["isDefault"]
            self.isInitial = definition["isInitial"]
            self.isEqual = definition["isEqual"]
            self.element = OwnedExpression(definition["ownedRelatedElement"])

    def dump(self):
        output = []
        if self.isDefault:
            output.append("default")
            if self.isEqual:
                output.append("=")
            elif self.isInitial:
                output.append(":=")
        else:
            output.append("=")
        output.append(self.element.dump())
        return " ".join(output)

    def get_definition(self):
        output = {"name": self.__class__.__name__}
        output["ownedRelatedElement"] = self.element.get_definition()
        output["isEqual"] = self.isEqual
        output["isInitial"] = self.isInitial
        output["isDefault"] = self.isDefault
        return output


class OwnedExpression:
    def __init__(self, definition):
        if valid_definition(definition, self.__class__.__name__):
            self.expression = ConditionalExpression(definition["expression"])

    def dump(self):
        return self.expression.dump()

    def get_definition(self):
        return {
            "name": self.__class__.__name__,
            "expression": self.expression.get_definition(),
        }


class ConditionalExpression:
    def __init__(self, definition):
        self.operands = []
        if valid_definition(definition, self.__class__.__name__):
            if definition["operand"] is not None:
                for op in definition["operand"]:
                    self.operands.append(NullCoalescingExpression(op))

    def dump(self):
        return "".join(child.dump() for child in self.operands)

    def get_definition(self):
        output = {"name": self.__class__.__name__, "operator": [], "operand": []}
        for child in self.operands:
            output["operand"].append(child.get_definition())
        return output


class NullCoalescingExpression:
    def __init__(self, definition):
        self.implies = None
        self.operand = []
        self.operator = []
        if valid_definition(definition, self.__class__.__name__):
            if definition["implies"] is not None:
                self.implies = ImpliesExpression(definition["implies"])
            self.operand = definition.get("operand", [])
            self.operator = definition.get("operator", [])

    def dump(self):
        if self.implies is not None:
            return self.implies.dump()
        return ""

    def get_definition(self):
        output = {
            "name": self.__class__.__name__,
            "operator": self.operator,
            "operand": self.operand,
        }
        if self.implies is not None:
            output["implies"] = self.implies.get_definition()
        return output


class ImpliesExpression:
    def __init__(self, definition):
        self.orexpression = None
        self.operand = []
        self.operator = []
        if valid_definition(definition, self.__class__.__name__):
            if definition["or"] is not None:
                self.orexpression = OrExpression(definition["or"])
            self.operand = definition.get("operand", [])
            self.operator = definition.get("operator", [])

    def dump(self):
        if self.orexpression is not None and self.operator and self.operand:
            output = [self.orexpression.dump()]
            for op, rhs in zip(self.operator, self.operand):
                output.append(op)
                if isinstance(rhs, dict):
                    try:
                        output.append(OrExpression(rhs).dump())
                    except Exception:
                        output.append(str(rhs))
                else:
                    output.append(str(rhs))
            return " ".join(output)
        if self.orexpression is not None:
            return self.orexpression.dump()
        return ""

    def get_definition(self):
        output = {
            "name": self.__class__.__name__,
            "operator": self.operator,
            "operand": self.operand,
        }
        if self.orexpression is not None:
            output["or"] = self.orexpression.get_definition()
        return output


class OrExpression:
    def __init__(self, definition):
        self.xor = None
        self.operand = []
        self.operator = []
        if valid_definition(definition, self.__class__.__name__):
            if definition["xor"] is not None:
                self.xor = XorExpression(definition["xor"])
            self.operand = definition.get("operand", [])
            self.operator = definition.get("operator", [])

    def dump(self):
        if self.xor is not None and self.operator and self.operand:
            output = [self.xor.dump()]
            for op, rhs in zip(self.operator, self.operand):
                output.append(op)
                if isinstance(rhs, dict):
                    try:
                        output.append(XorExpression(rhs).dump())
                    except Exception:
                        output.append(str(rhs))
                else:
                    output.append(str(rhs))
            return " ".join(output)
        if self.xor is not None:
            return self.xor.dump()
        return ""

    def get_definition(self):
        output = {
            "name": self.__class__.__name__,
            "operator": self.operator,
            "operand": self.operand,
        }
        if self.xor is not None:
            output["xor"] = self.xor.get_definition()
        return output


class XorExpression:
    def __init__(self, definition):
        self.andexpression = None
        self.operand = []
        self.operator = []
        if valid_definition(definition, self.__class__.__name__):
            if definition["and"] is not None:
                self.andexpression = AndExpression(definition["and"])
            self.operand = definition.get("operand", [])
            self.operator = definition.get("operator", [])

    def dump(self):
        if self.andexpression is not None and self.operator and self.operand:
            output = [self.andexpression.dump()]
            for op, rhs in zip(self.operator, self.operand):
                output.append(op)
                if isinstance(rhs, dict):
                    try:
                        output.append(AndExpression(rhs).dump())
                    except Exception:
                        output.append(str(rhs))
                else:
                    output.append(str(rhs))
            return " ".join(output)
        if self.andexpression is not None:
            return self.andexpression.dump()
        return ""

    def get_definition(self):
        output = {
            "name": self.__class__.__name__,
            "operator": self.operator,
            "operand": self.operand,
            "and": self.andexpression.get_definition(),
        }
        return output


class EqualityExpressionReference:
    # EqualityExpressionReference :
    # 	ownedRelationship = EqualityExpressionMember
    # ;
    def __init__(self, definition):
        self.children = []
        if valid_definition(definition, self.__class__.__name__):
            self.children.append(
                EqualityExpressionMember(definition["ownedRelationship"])
            )

    def dump(self):
        return "".join([x.dump() for x in self.children])

    def get_definition(self):
        return {
            "name": self.__class__.__name__,
            "ownedRelationship": self.children[0].get_definition() if self.children else None,
        }


class EqualityExpressionMember:
    # EqualityExpressionMember :
    # 	ownedRelatedElement = EqualityExpression
    # ;
    def __init__(self, definition):
        self.children = []
        if valid_definition(definition, self.__class__.__name__):
            self.children.append(EqualityExpression(definition["ownedRelatedElement"]))

    def dump(self):
        return "\n".join([x.dump() for x in self.children])

    def get_definition(self):
        return {
            "name": self.__class__.__name__,
            "ownedRelatedElement": self.children[0].get_definition() if self.children else None,
        }


class AndOperand:
    def __init__(self, definition):
        self.operations = []
        if valid_definition(definition, self.__class__.__name__):
            self.operator = definition["operator"]
            if self.operator == "&":
                self.operand = EqualityExpression(definition["operand"])
            else:
                self.operand = EqualityExpressionReference(definition["operand"])

    def dump(self):
        return "".join([self.operator, "\n   ", self.operand.dump()])

    def get_definition(self):
        output = {
            "name": self.__class__.__name__,
            "operator": self.operator,
            "operand": self.operand.get_definition(),
        }
        return output


class AndExpression:
    def __init__(self, definition):
        self.operations = []
        if valid_definition(definition, self.__class__.__name__):
            self.equality = EqualityExpression(definition["equality"])
            for op in definition["operation"]:
                self.operations.append(AndOperand(op))

    def dump(self):
        output = [self.equality.dump()]
        for op in self.operations:
            output.append(" ")
            output.append(op.dump())

        return "".join(output)

    def get_definition(self):
        output = {
            "name": self.__class__.__name__,
            "operation": [x.get_definition() for x in self.operations],
            "equality": self.equality.get_definition(),
        }
        return output


class EqualityOperand:
    # EqualityOperand:
    #   operator=EqualityOperator operand=ClassificationExpression
    # ;
    def __init__(self, definition):
        if valid_definition(definition, self.__class__.__name__):
            self.operator = definition["operator"]
            self.operand = ClassificationExpression(definition["operand"])

    def dump(self):
        return " ".join([self.operator, self.operand.dump()])

    def get_definition(self):
        output = {
            "name": self.__class__.__name__,
            "operator": self.operator,
            "operand": self.operand.get_definition(),
        }
        return output


class EqualityExpression:
    def __init__(self, definition):
        self.operations = []
        if valid_definition(definition, self.__class__.__name__):
            self.classification = ClassificationExpression(definition["classification"])
            for op in definition["operation"]:
                self.operations.append(EqualityOperand(op))

    def dump(self):
        output = [self.classification.dump()]
        for op in self.operations:
            output.append(op.dump())
        return " ".join(output)

    def get_definition(self):
        output = {
            "name": self.__class__.__name__,
            "operation": [x.get_definition() for x in self.operations],
            "classification": self.classification.get_definition(),
        }
        return output


class ClassificationExpression:
    def __init__(self, definition):
        self.relational = None
        self.operand = []
        self.operator = None
        if valid_definition(definition, self.__class__.__name__):
            if definition["relational"] is not None:
                self.relational = RelationalExpression(definition["relational"])
            self.operand = definition.get("operand", [])
            self.operator = definition.get("operator")

    def dump(self):
        if self.relational is not None:
            return self.relational.dump()
        return ""

    def get_definition(self):
        output = {
            "name": self.__class__.__name__,
            "operator": self.operator,
            "operand": self.operand,
        }
        if self.relational is not None:
            output["relational"] = self.relational.get_definition()
        return output


class RelationalOperand:
    def __init__(self, definition):
        if valid_definition(definition, self.__class__.__name__):
            self.operator = definition["operator"]
            self.operand = RangeExpression(definition["operand"])

    def dump(self):
        return " ".join([self.operator, self.operand.dump()])

    def get_definition(self):
        output = {
            "name": self.__class__.__name__,
            "operator": self.operator,
            "operand": self.operand.get_definition(),
        }
        return output


class RelationalExpression:
    def __init__(self, definition):
        if valid_definition(definition, self.__class__.__name__):
            self.range = RangeExpression(definition["range"])
            self.operations = []
            for child in definition["operation"]:
                self.operations.append(RelationalOperand(child))

    def dump(self):
        output = [self.range.dump()]
        for child in self.operations:
            output.append(child.dump())

        return " ".join(output)

    def get_definition(self):
        output = {
            "name": self.__class__.__name__,
            "operation": [x.get_definition() for x in self.operations],
            "range": self.range.get_definition(),
        }
        return output


class RangeExpression:
    # RangeExpression :
    # 	additive=AdditiveExpression ('..' operand = AdditiveExpression )?
    # ;
    def __init__(self, definition):
        if valid_definition(definition, self.__class__.__name__):
            self.additive = AdditiveExpression(definition["additive"])
            self.operator = ".."
            if definition["operand"] is not None:
                self.operand = AdditiveExpression(definition["operand"])
            else:
                self.operand = None

    def dump(self):
        if self.operand is None:
            return self.additive.dump()
        else:
            return " ".join([self.additive.dump(), self.operator, self.operand.dump()])

    def get_definition(self):
        if self.operand is not None:
            output = {
                "name": self.__class__.__name__,
                "operand": self.operand.get_definition(),
                "additive": self.additive.get_definition(),
            }
        else:
            output = {
                "name": self.__class__.__name__,
                "operand": None,
                "additive": self.additive.get_definition(),
            }
        return output


class AdditiveOperand:
    def __init__(self, definition):
        if valid_definition(definition, self.__class__.__name__):
            self.operator = definition["operator"]
            self.operand = MultiplicativeExpression(definition["operand"])

    def dump(self):
        return " ".join([self.operator, self.operand.dump()])

    def get_definition(self):
        return {
            "name": self.__class__.__name__,
            "operator": self.operator,
            "operand": self.operand.get_definition(),
        }


class AdditiveExpression:
    def __init__(self, definition):
        if valid_definition(definition, self.__class__.__name__):
            # This is the left hand statement
            self.left_hand = MultiplicativeExpression(definition["multiplicitive"])
            self.operations = []
            if len(definition["operation"]) > 0:
                for child in definition["operation"]:
                    self.operations.append(AdditiveOperand(child))

    def dump(self):
        if len(self.operations) == 0:
            return self.left_hand.dump()
        else:
            output = [self.left_hand.dump()]
            output.append(" ".join([x.dump() for x in self.operations]))
            return " ".join(output)

    def get_definition(self):
        output = {
            "name": self.__class__.__name__,
            "multiplicitive": self.left_hand.get_definition(),
            "operation": [x.get_definition() for x in self.operations],
        }
        return output


class MultiplicativeOperand:
    def __init__(self, definition):
        if valid_definition(definition, self.__class__.__name__):
            self.operator = definition["operator"]
            self.operand = ExponentiationExpression(definition["operand"])

    def dump(self):
        return " ".join([self.operator, self.operand.dump()])

    def get_definition(self):
        output = {
            "name": self.__class__.__name__,
            "operator": self.operator,
            "operand": self.operand.get_definition(),
        }
        return output


class MultiplicativeExpression:
    def __init__(self, definition):
        if valid_definition(definition, self.__class__.__name__):
            self.exponential = ExponentiationExpression(definition["exponential"])
            self.operators = []
            for child in definition["operation"]:
                self.operators.append(MultiplicativeOperand(child))

    def dump(self):
        return "".join([self.exponential.dump()] + [x.dump() for x in self.operators])

    def get_definition(self):
        output = {
            "name": self.__class__.__name__,
            "operation": [x.get_definition() for x in self.operators],
            "exponential": self.exponential.get_definition(),
        }
        return output


class ExponentiationExpression:
    def __init__(self, definition):
        self.unary = None
        self.operand = []
        self.operator = []
        if valid_definition(definition, self.__class__.__name__):
            if definition["unary"] is not None:
                self.unary = UnaryExpression(definition["unary"])
            self.operand = definition.get("operand", [])
            self.operator = definition.get("operator", [])

    def dump(self):
        if self.unary is not None and self.operator and self.operand:
            output = [self.unary.dump()]
            for op, rhs in zip(self.operator, self.operand):
                output.append(op)
                if isinstance(rhs, dict):
                    try:
                        output.append(ExponentiationExpression(rhs).dump())
                    except Exception:
                        output.append(str(rhs))
                else:
                    output.append(str(rhs))
            return " ".join(output)
        if self.unary is not None:
            return self.unary.dump()
        return ""

    def get_definition(self):
        output = {
            "name": self.__class__.__name__,
            "operator": self.operator,
            "operand": self.operand,
        }
        if self.unary is not None:
            output["unary"] = self.unary.get_definition()
        return output


class UnaryExpression:
    def __init__(self, definition):
        self.extent = None
        self.operand = []
        self.operator = None
        if valid_definition(definition, self.__class__.__name__):
            if definition["extent"] is not None:
                self.extent = ExtentExpression(definition["extent"])
            self.operand = definition.get("operand", [])
            self.operator = definition.get("operator")

    def dump(self):
        if self.extent is not None:
            if self.operator:
                # prefix operator: no space for symbol operators
                # ('-x'), one for keyword operators ('not flag')
                if self.operator in ("+", "-", "~"):
                    return "{}{}".format(self.operator, self.extent.dump())
                return "{} {}".format(self.operator, self.extent.dump())
            return self.extent.dump()
        return ""

    def get_definition(self):
        output = {
            "name": self.__class__.__name__,
            "operator": self.operator,
            "operand": self.operand,
        }
        if self.extent is not None:
            output["extent"] = self.extent.get_definition()
        return output


class ExtentExpression:
    def __init__(self, definition):
        self.primary = None
        self.nested = None
        self.operator = ""
        if valid_definition(definition, self.__class__.__name__):
            if definition.get("primary") is not None:
                self.primary = PrimaryExpression(definition["primary"])
            nested = definition.get("ownedRelationship")
            if isinstance(nested, dict):
                self.nested = globals()[nested["name"]](nested)
            self.operator = definition.get("operator", "")

    def dump(self):
        if self.primary is not None:
            return self.primary.dump()
        if self.nested is not None:
            return self.nested.dump()
        return ""

    def get_definition(self):
        output = {
            "name": self.__class__.__name__,
            "operator": self.operator,
            "operand": [],
        }
        if self.primary is not None:
            output["primary"] = self.primary.get_definition()
        if self.nested is not None:
            output["ownedRelationship"] = self.nested.get_definition()
        return output


class ReferenceTyping:
    # ReferenceTyping :
    # 	  type = QualifiedName
    # ;
    def __init__(self, definition):
        if valid_definition(definition, self.__class__.__name__):
            self.child = QualifiedName(definition["type"])

    def dump(self):
        return self.child.dump()

    def get_definition(self):
        return {
            "name": self.__class__.__name__,
            "type": self.child.get_definition(),
        }


class PrimaryExpression:
    def __init__(self, definition):
        if valid_definition(definition, self.__class__.__name__):
            self.base = BaseExpression(definition["base"])

            self.children1 = None
            self.children2 = None

            if len(definition["ownedRelationship1"]) > 0:
                self.children1 = FeatureChainMember(definition["ownedRelationship1"][0])

            if len(definition["ownedRelationship2"]) > 0:
                self.children2 = FeatureChainMember(definition["ownedRelationship2"][0])

            self.operator = []
            self.operand = []

            if not (definition["operand"] == [] and definition["operator"] == []):
                for k, child in enumerate(definition["operator"]):
                    self.operator.append(child)
                    if child == "->":
                        self.reference = ReferenceTyping(
                            definition["ownedRelationship"][k]
                        )
                    operand = definition["operand"][k]
                    if operand["name"] == "SequenceExpression":
                        self.operand.append(SequenceExpression(operand))
                    elif operand["name"] == "BodyExpression":
                        self.operand.append(BodyExpression(operand))
                    elif operand["name"] == "ArgumentList":
                        self.operand.append(ArgumentList(operand))

    def dump(self):
        output = [self.base.dump()]
        if self.children1 is not None:
            output.append("." + self.children1.dump())
        for k, v in enumerate(self.operator):
            if v == "#":
                output.append("# ({})".format(self.operand[k].dump()))

            if v == "[":
                output.append("[{}]".format(self.operand[k].dump()))

            if v == "." or v == ".?":
                output.append("{}{}".format(v, self.operand[k].dump()))

            if v == "->":
                output.append(
                    "{}{}{}".format(v, self.reference.dump(), self.operand[k].dump())
                )

        if self.children2 is not None:
            output.append("." + self.children2.dump())

        return "".join(output)

    def get_definition(self):
        output = {
            "name": self.__class__.__name__,
            "operator": [],
            "operand": [],
            "base": self.base.get_definition(),
            "ownedRelationship1": [],
            "ownedRelationship2": [],
        }
        for child in self.operand:
            output["operand"].append(child.get_definition())

        for child in self.operator:
            output["operator"].append(child)

        if self.children1 is not None:
            output["ownedRelationship1"].append(self.children1.get_definition())

        if self.children2 is not None:
            output["ownedRelationship2"].append(self.children2.get_definition())
        return output


class BodyExpression:
    def __init__(self, definition):
        self.children = None
        if valid_definition(definition, self.__class__.__name__):
            self.children = ExpressionBodyMember(definition["ownedRelationship"])

    def dump(self):
        return self.children.dump()

    def get_definition(self):
        return {
            "name": self.__class__.__name__,
            "ownedRelationship": self.children.get_definition() if self.children else None,
        }


class ExpressionBodyMember:
    def __init__(self, definition):
        self.children = None
        if valid_definition(definition, self.__class__.__name__):
            self.children = ExpressionBody(definition["ownedRelatedElement"])

    def dump(self):
        return self.children.dump()

    def get_definition(self):
        return {
            "name": self.__class__.__name__,
            "ownedRelatedElement": self.children.get_definition() if self.children else None,
        }


class ExpressionBody:
    def __init__(self, definition):
        self.children = None
        if valid_definition(definition, self.__class__.__name__):
            self.children = CalculationBody(definition["body"])

    def dump(self):
        return self.children.dump()

    def get_definition(self):
        return {
            "name": self.__class__.__name__,
            "body": self.children.get_definition() if self.children else None,
        }


class FeatureChainMember:
    def __init__(self, definition):
        self.children = None
        if valid_definition(definition, self.__class__.__name__):
            if definition.get("memberElement") is not None:
                self.children = QualifiedName(definition["memberElement"])
            elif definition.get("ownedRelatedElement") is not None:
                self.children = OwnedFeatureChain(definition["ownedRelatedElement"])

    def dump(self):
        if self.children is not None:
            return self.children.dump()
        return ""

    def get_definition(self):
        output = {
            "name": self.__class__.__name__,
        }
        if self.children is not None:
            # Determine which key to use based on child type
            if isinstance(self.children, QualifiedName):
                output["memberElement"] = self.children.get_definition()
            else:
                output["ownedRelatedElement"] = self.children.get_definition()
        return output


class SequenceOperand:
    # SequenceOperand:
    #   (',' operand = OwnedExpression)
    #   |
    #   ','
    # ; // Allow trailing comma
    def __init__(self, definition):
        if valid_definition(definition, self.__class__.__name__):
            self.operand = OwnedExpression(definition["operand"])

    def dump(self):
        return ", " + self.operand.dump()

    def get_definition(self):
        output = {
            "name": self.__class__.__name__,
            "operand": self.operand.get_definition(),
        }
        return output


class SequenceExpression:
    # SequenceExpression :
    # 	ownedRelationship=OwnedExpression operation+=SequenceOperand*
    # ;
    def __init__(self, definition):
        self.operations = []
        if valid_definition(definition, self.__class__.__name__):
            self.relationship = OwnedExpression(definition["ownedRelationship"])
            for op in definition["operation"]:
                self.operations.append(SequenceOperand(op))

    def dump(self):
        output = [self.relationship.dump()]
        for op in self.operations:
            output.append(op.dump())
        return "".join(output)

    def get_definition(self):
        output = {
            "name": self.__class__.__name__,
            "operation": [x.get_definition() for x in self.operations],
            "ownedRelationship": self.relationship.get_definition(),
        }
        return output


class BaseExpression:
    def __init__(self, definition):
        if valid_definition(definition, self.__class__.__name__):
            if definition["ownedRelationship"]["name"] == "FeatureReferenceExpression":
                self.relationship = FeatureReferenceExpression(
                    definition["ownedRelationship"]
                )
            elif definition["ownedRelationship"]["name"] == "LiteralInteger":
                self.relationship = LiteralInteger(definition["ownedRelationship"])
            elif definition["ownedRelationship"]["name"] == "LiteralString":
                self.relationship = LiteralString(definition["ownedRelationship"])
            elif definition["ownedRelationship"]["name"] == "LiteralReal":
                self.relationship = LiteralReal(definition["ownedRelationship"])
            elif definition["ownedRelationship"]["name"] == "LiteralBoolean":
                self.relationship = LiteralBoolean(definition["ownedRelationship"])
            elif definition["ownedRelationship"]["name"] == "SequenceExpression":
                self.relationship = SequenceExpression(definition["ownedRelationship"])
            elif definition["ownedRelationship"]["name"] == "InvocationExpression":
                self.relationship = InvocationExpression(
                    definition["ownedRelationship"]
                )
            else:
                print(f"PrimaryExpression: unhandled {definition['ownedRelationship']['name']}")  # pragma: no cover
                self.relationship = None  # pragma: no cover

    def dump(self):
        if self.relationship is None:
            return ""
        if self.relationship.__class__.__name__ != "SequenceExpression":
            return self.relationship.dump()
        else:
            return "(" + self.relationship.dump() + ")"

    def get_definition(self):
        output = {
            "name": self.__class__.__name__,
            "ownedRelationship": self.relationship.get_definition(),
        }
        return output


class InvocationExpression:
    def __init__(self, definition):
        if valid_definition(definition, self.__class__.__name__):
            self.relationship = OwnedFeatureTyping(definition["ownedRelationship"])
            self.children = ArgumentList(definition["arg_list"])

    def dump(self):
        return "".join([self.relationship.dump(), self.children.dump()])

    def get_definition(self):
        return {
            "name": self.__class__.__name__,
            "ownedRelationship": self.relationship.get_definition(),
            "arg_list": self.children.get_definition(),
        }


class ArgumentList:
    def __init__(self, definition):
        if valid_definition(definition, self.__class__.__name__):
            if definition["pos_list"] is not None:
                self.children = PositionalArgumentList(definition["pos_list"])
            elif definition["named_list"] is not None:
                # Only one, the other, or none
                self.children = NamedArgumentList(definition["named_list"])
            else:
                self.children = None

    def dump(self):
        output = ["("]
        if self.children is not None:
            output.append(self.children.dump())
        output.append(")")
        return "".join(output)

    def get_definition(self):
        return {
            "name": self.__class__.__name__,
            "pos_list": self.children.get_definition() if self.children is not None else None,
            "named_list": None,
        }


class PositionalArgumentList:
    def __init__(self, definition):
        self.children = []
        if valid_definition(definition, self.__class__.__name__):
            for child in definition["ownedRelationship"]:
                self.children.append(ArgumentMember(child))

    def dump(self):
        return ",".join([x.dump() for x in self.children])

    def get_definition(self):
        return {
            "name": self.__class__.__name__,
            "ownedRelationship": [c.get_definition() for c in self.children],
        }


class ArgumentMember:
    def __init__(self, definition):
        self.children = None
        if valid_definition(definition, self.__class__.__name__):
            self.children = Argument(definition["ownedRelatedElement"])

    def dump(self):
        return self.children.dump()

    def get_definition(self):
        return {
            "name": self.__class__.__name__,
            "ownedRelatedElement": self.children.get_definition() if self.children is not None else None,
        }


class Argument:
    def __init__(self, definition):
        self.children = None
        if valid_definition(definition, self.__class__.__name__):
            self.children = ArgumentValue(definition["ownedRelationship"])

    def dump(self):
        return self.children.dump()

    def get_definition(self):
        return {
            "name": self.__class__.__name__,
            "ownedRelationship": self.children.get_definition() if self.children is not None else None,
        }


class ArgumentValue:
    def __init__(self, definition):
        self.children = None
        if valid_definition(definition, self.__class__.__name__):
            self.children = OwnedExpression(definition["ownedRelatedElement"])

    def dump(self):
        return self.children.dump()

    def get_definition(self):
        return {
            "name": self.__class__.__name__,
            "ownedRelatedElement": self.children.get_definition() if self.children is not None else None,
        }


class NamedArgumentList:
    def __init__(self, definition):
        self.children = []
        if valid_definition(definition, self.__class__.__name__):
            for child in definition["ownedRelationship"]:
                self.children.append(NamedArgumentMember(child))

    def dump(self):
        return ",".join([x.dump() for x in self.children])

    def get_definition(self):
        return {
            "name": self.__class__.__name__,
            "ownedRelationship": [x.get_definition() for x in self.children],
        }


class NamedArgumentMember:
    def __init__(self, definition):
        self.children = None
        if valid_definition(definition, self.__class__.__name__):
            self.children = NamedArgument(definition["ownedRelatedElement"])

    def dump(self):
        return self.children.dump()

    def get_definition(self):
        return {
            "name": self.__class__.__name__,
            "ownedRelatedElement": self.children.get_definition() if self.children else None,
        }


class NamedArgument:
    def __init__(self, definition):
        if valid_definition(definition, self.__class__.__name__):
            self.redefinition = ParameterRedefinition(definition["redefinition"])
            self.value = ArgumentValue(definition["value"])

    def dump(self):
        return "".join([self.redefinition.dump(), self.value.dump()])

    def get_definition(self):
        return {
            "name": self.__class__.__name__,
            "redefinition": self.redefinition.get_definition(),
            "value": self.value.get_definition(),
        }


class ParameterRedefinition:
    def __init__(self, definition):
        if valid_definition(definition, self.__class__.__name__):
            self.children = QualifiedName(definition["redefinedFeature"])

    def dump(self):
        return self.children.dump()

    def get_definition(self):
        return {
            "name": self.__class__.__name__,
            "redefinedFeature": self.children.get_definition() if self.children else None,
        }


class FeatureReferenceExpression:
    def __init__(self, definition):
        if valid_definition(definition, self.__class__.__name__):
            self.children = []
            for relationship in definition["ownedRelationship"]:
                self.children.append(FeatureReferenceMember(relationship))

    def dump(self):
        return "".join([child.dump() for child in self.children])

    def get_definition(self):
        output = {
            "name": self.__class__.__name__,
            "ownedRelationship": [],
        }
        for child in self.children:
            output["ownedRelationship"].append(child.get_definition())
        return output


class FeatureReferenceMember:
    def __init__(self, definition):
        if valid_definition(definition, self.__class__.__name__):
            member_element = definition["memberElement"]
            if isinstance(member_element, str):
                self.memberElement = QualifiedName({"name": "QualifiedName", "parts": [member_element]})
            else:
                self.memberElement = QualifiedName(member_element)

    def dump(self):
        return self.memberElement.dump()

    def get_definition(self):
        output = {
            "name": self.__class__.__name__,
            "memberElement": self.memberElement.get_definition(),
        }
        return output


class OccurrenceUsageElement:
    def __init__(self, definition):
        if valid_definition(definition, "OccurrenceUsageElement"):
            ore_name = definition["ownedRelatedElement"]["name"]
            if ore_name == "StructureUsageElement":
                self.children = StructureUsageElement(definition["ownedRelatedElement"])
            elif ore_name == "BehaviorUsageElement":
                self.children = BehaviorUsageElement(definition["ownedRelatedElement"])
            elif ore_name == "InterfaceUsage":
                self.children = InterfaceUsage(definition["ownedRelatedElement"])
            else:
                print(f"OccurrenceUsageElement: unhandled {ore_name}")  # pragma: no cover
                self.children = None  # pragma: no cover

    def dump(self):
        if self.children is None:
            return ""
        return self.children.dump()

    def get_definition(self):
        if self.children is None:
            return {"name": self.__class__.__name__, "ownedRelatedElement": None}
        return {
            "name": self.__class__.__name__,
            "ownedRelatedElement": self.children.get_definition(),
        }


class StructureUsageElement:
    def __init__(self, definition):
        if valid_definition(definition, self.__class__.__name__):
            name = definition["ownedRelatedElement"]["name"]
            if name == "ItemUsage":
                self.children = ItemUsage(definition["ownedRelatedElement"])
            elif name == "PartUsage":
                self.children = PartUsage(definition["ownedRelatedElement"])
            elif name == "ConnectionUsage":
                self.children = ConnectionUsage(definition["ownedRelatedElement"])
            elif name == "PortUsage":
                self.children = PortUsage(definition["ownedRelatedElement"])
            elif name == "InterfaceUsage":
                self.children = InterfaceUsage(definition["ownedRelatedElement"])
            elif name == "FlowConnectionUsage":
                self.children = FlowConnectionUsage(definition["ownedRelatedElement"])
            elif name == "IndividualUsage":
                self.children = IndividualUsage(definition["ownedRelatedElement"])
            elif name == "IndividualUsageSimple":
                self.children = IndividualUsageSimple(definition["ownedRelatedElement"])
            elif name == "FlowUsageSimple":
                self.children = FlowUsageSimple(definition["ownedRelatedElement"])
            elif name == "AllocationUsage":
                self.children = AllocationUsage(definition["ownedRelatedElement"])
            elif name == "RenderingUsage":
                self.children = RenderingUsage(definition["ownedRelatedElement"])
            elif name == "PortionUsage":
                self.children = PortionUsage(definition["ownedRelatedElement"])
            elif name == "ViewUsage":
                self.children = ViewUsage(definition["ownedRelatedElement"])
            elif name == "SuccessionFlowConnectionUsage":
                self.children = SuccessionFlowConnectionUsage(
                    definition["ownedRelatedElement"]
                )
            elif name == "Message":
                self.children = Message(definition["ownedRelatedElement"])
            else:
                print(f"NonOccurrenceUsageElement: unhandled {name}")  # pragma: no cover

    def dump(self):
        return self.children.dump()

    def get_definition(self):
        return {
            "name": self.__class__.__name__,
            "ownedRelatedElement": self.children.get_definition(),
        }


class SuccessionFlowConnectionUsage:
    def __init__(self, definition):
        self.keyword = "succession flow"
        self.prefix = None
        self.declaration = None
        self.body = None
        if valid_definition(definition, self.__class__.__name__):
            if definition["prefix"] is not None:
                self.prefix = OccurrenceUsagePrefix(definition["prefix"])

            if definition["declaration"] is not None:
                self.declaration = FlowConnectionDeclaration(definition["declaration"])

            if definition["body"] is not None:
                self.body = DefinitionBody(definition["body"])

    def dump(self):
        output = []
        if self.prefix is not None:
            output.append(self.prefix.dump())

        output.append(self.keyword)

        if self.declaration is not None:
            output.append(self.declaration.dump())

        if self.body is not None:
            output.append(self.body.dump())
        return " ".join(output)

    def get_definition(self):
        output = {
            "name": self.__class__.__name__,
            "prefix": self.prefix.get_definition() if self.prefix else None,
            "declaration": self.declaration.get_definition() if self.declaration else None,
            "body": self.body.get_definition() if self.body else None,
        }
        return output


class IndividualUsage:
    def __init__(self, definition):
        self.prefix = None
        self.children = []
        if valid_definition(definition, self.__class__.__name__):
            if definition["prefix"] is not None:
                self.prefix = BasicUsagePrefix(definition["prefix"])
            self.isIndividual = definition["isIndividual"]
            for child in definition["usageExtension"]:
                self.children.append(UsageExtensionKeyword(child))
            self.usage = Usage(definition["usage"])

    def dump(self):
        output = []
        if self.prefix is not None:
            output.append(self.prefix.dump())
        if self.isIndividual:
            output.append("individual")
        for child in self.children:
            output.append(child.dump())
        output.append(self.usage.dump())

        return " ".join(output)

    def get_definition(self):
        output = {
            "name": self.__class__.__name__,
            "prefix": self.prefix.get_definition() if self.prefix else None,
            "isIndividual": self.isIndividual,
            "usageExtension": [x.get_definition() for x in self.children],
            "usage": self.usage.get_definition(),
        }
        return output


class UsageExtensionKeyword:
    def __init__(self, definition):
        if valid_definition(definition, self.__class__.__name__):
            if "keyword" in definition:
                self.keyword = definition["keyword"]
            elif "ownedRelationship" in definition:
                self.children = PrefixMetadataMember(definition["ownedRelationship"])

    def dump(self):
        if hasattr(self, 'keyword'):
            return self.keyword
        return self.children.dump()

    def get_definition(self):
        if hasattr(self, 'keyword'):
            return {"name": self.__class__.__name__, "keyword": self.keyword}
        return {
            "name": self.__class__.__name__,
            "ownedRelationship": self.children.get_definition() if self.children else None,
        }


class Message:
    # Message :
    # 	prefix=OccurrenceUsagePrefix MessageKeyword
    #   declaration=MessageDeclaration body=DefinitionBody
    # ;
    def __init__(self, definition=None):
        self.prefix = None
        self.keyword = "message"
        self.declaration = None
        self.body = None
        if definition is not None:
            if valid_definition(definition, self.__class__.__name__):
                if definition["prefix"] is not None:
                    self.prefix = OccurrenceUsagePrefix(definition["prefix"])
                if definition["declaration"] is not None:
                    self.declaration = MessageDeclaration(definition["declaration"])
                if definition["body"] is not None:
                    self.body = DefinitionBody(definition["body"])
        else:
            self.declaration = None
            self.body = DefinitionBody()

    def dump(self):
        output = []
        if self.prefix is not None:
            output.append(self.prefix.dump())
        output.append(self.keyword)
        if self.declaration is not None:
            output.append(self.declaration.dump())
        if self.body is not None:
            output.append(self.body.dump())
        return " ".join(output)

    def get_definition(self):
        output = {
            "name": self.__class__.__name__,
            "prefix": None,
            "declaration": None,
            "body": None,
        }
        if self.prefix is not None:
            output["prefix"] = self.prefix.get_definition()
        if self.declaration is not None:
            output["declaration"] = self.declaration.get_definition()
        if self.body is not None:
            output["body"] = self.body.get_definition()
        return output


class MessageDeclaration:
    # MessageDeclaration :
    # 	  UsageDeclaration? ValuePart?
    #     ( 'of' ownedRelationship += ItemFeatureMember )?
    #     ( 'from' ownedRelationship += MessageEventMember
    #       'to' ownedRelationship += MessageEventMember
    #     )?
    #   | ownedRelationship += MessageEventMember 'to'
    # 	  ownedRelationship += MessageEventMember
    # ;
    def __init__(self, definition):
        self.declaration = None
        self.valuepart = None
        self.of_item = None
        self.from_event = None
        self.to_event = None
        if valid_definition(definition, self.__class__.__name__):
            if definition.get("declaration") is not None:
                self.declaration = UsageDeclaration(definition["declaration"])
            if definition.get("valuepart") is not None:
                self.valuepart = ValuePart(definition["valuepart"])

            # Parse from/to from ownedRelationship list
            relationships = definition.get("ownedRelationship", [])
            if len(relationships) >= 2:
                self.from_event = MessageEventMember(relationships[0])
                self.to_event = MessageEventMember(relationships[1])
            elif len(relationships) == 1:
                self.to_event = MessageEventMember(relationships[0])

    def dump(self):
        output = []
        if self.declaration is not None:
            output.append(self.declaration.dump())
        if self.valuepart is not None:
            output.append(self.valuepart.dump())
        if self.from_event is not None and self.to_event is not None:
            output.append("from")
            output.append(self.from_event.dump())
            output.append("to")
            output.append(self.to_event.dump())
        elif self.to_event is not None:
            output.append("to")
            output.append(self.to_event.dump())
        return " ".join(output)

    def get_definition(self):
        output = {
            "name": self.__class__.__name__,
            "declaration": None,
            "valuepart": None,
            "ownedRelationship": [],
        }
        if self.declaration is not None:
            output["declaration"] = self.declaration.get_definition()
        if self.valuepart is not None:
            output["valuepart"] = self.valuepart.get_definition()
        if self.from_event is not None:
            output["ownedRelationship"].append(self.from_event.get_definition())
        if self.to_event is not None:
            output["ownedRelationship"].append(self.to_event.get_definition())
        return output


class MessageEventMember:
    def __init__(self, definition):
        self.children = []
        if valid_definition(definition, self.__class__.__name__):
            for element in definition["ownedRelatedElement"]:
                self.children.append(MessageEvent(element))

    def dump(self):
        return " ".join([child.dump() for child in self.children])

    def get_definition(self):
        output = {
            "name": self.__class__.__name__,
            "ownedRelatedElement": [],
        }
        for child in self.children:
            output["ownedRelatedElement"].append(child.get_definition())
        return output


class MessageEvent:
    def __init__(self, definition):
        self.children = []
        if valid_definition(definition, self.__class__.__name__):
            for relationship in definition["ownedRelationship"]:
                self.children.append(OwnedReferenceSubsetting(relationship))

    def dump(self):
        return " ".join([child.dump() for child in self.children])

    def get_definition(self):
        output = {
            "name": self.__class__.__name__,
            "ownedRelationship": [],
        }
        for child in self.children:
            output["ownedRelationship"].append(child.get_definition())
        return output


class FlowConnectionUsage:
    def __init__(self, definition=None):
        self.prefix = None
        self.keyword = "flow"
        if definition is not None:
            if valid_definition(definition, self.__class__.__name__):
                if definition["prefix"] is not None:
                    self.prefix = OccurrenceUsagePrefix(definition["prefix"])
                self.declaration = FlowConnectionDeclaration(definition["declaration"])
                self.body = DefinitionBody(definition["body"])
        else:
            self.declaration = FlowConnectionDeclaration()
            self.body = DefinitionBody()

    def dump(self):
        output = []
        if self.prefix is not None:
            output.append(self.prefix.dump())
        output.append(self.keyword)
        output.append(self.declaration.dump())
        output.append(self.body.dump())
        return " ".join(output)

    def get_definition(self):
        output = {"name": self.__class__.__name__, "prefix": None}
        if self.prefix is not None:
            output["prefix"] = self.prefix.get_definition()
        output["declaration"] = self.declaration.get_definition()
        output["body"] = self.body.get_definition()
        return output


class FlowConnectionDeclaration:
    def __init__(self, definition=None):
        self.declaration = None
        self.valuepart = None
        self.children = [None, None, None]
        if definition is not None:
            if valid_definition(definition, self.__class__.__name__):
                if definition["declaration"] is not None:
                    self.declaration = UsageDeclaration(definition["declaration"])
                if definition["valuepart"] is not None:
                    self.declaration = ValuePart(definition["valuepart"])

                if definition["ownedRelationship_of"] is not None:
                    self.children[0] = ItemFeatureMember(definition["ownedRelationship_of"])

                if definition["ownedRelationship_from"] is not None:
                    self.children[1] = FlowEndMember(definition["ownedRelationship_from"])

                if definition["ownedRelationship_to"] is not None:
                    self.children[2] = FlowEndMember(definition["ownedRelationship_to"])
        else:
            self.declaration = UsageDeclaration()

    def dump(self):
        output = []
        if self.declaration is not None:
            decl_dump = self.declaration.dump()
            if decl_dump:
                output.append(decl_dump)
        if self.valuepart is not None:
            output.append(self.valuepart.dump())

        if self.children[0] is not None:
            output.append("of")
            output.append(self.children[0].dump())

        if self.children[1] is not None:
            # Add 'from' if there's content before the from-end (e.g. 'of Fuel from ...')
            if len(output) > 0:
                output.append("from")
            output.append(self.children[1].dump())
        if self.children[2] is not None:
            output.append("to")
            output.append(self.children[2].dump())

        return " ".join(output)

    def get_definition(self):
        output = {"name": self.__class__.__name__, "declaration": None, "valuepart": None,
                  "ownedRelationship_of": None, "ownedRelationship_from": None, "ownedRelationship_to": None}
        if self.declaration is not None:
            output["declaration"] = self.declaration.get_definition()
        if self.valuepart is not None:
            output["valuepart"] = self.valuepart.get_definition()
        if self.children[0] is not None:
            output["ownedRelationship_of"] = self.children[0].get_definition()
        if self.children[1] is not None:
            output["ownedRelationship_from"] = self.children[1].get_definition()
        if self.children[2] is not None:
            output["ownedRelationship_to"] = self.children[2].get_definition()
        return output


class ItemFeatureMember:
    def __init__(self, definition):
        if valid_definition(definition, self.__class__.__name__):
            self.children = ItemFeature(definition["ownedRelatedElement"][0])

    def dump(self):
        return self.children.dump()

    def get_definition(self):
        return {
            "name": self.__class__.__name__,
            "ownedRelatedElement": [self.children.get_definition()] if self.children else [],
        }


class ItemFeature:
    def __init__(self, definition):
        if valid_definition(definition, self.__class__.__name__):
            self.children = PayloadFeature(definition["ownedRelatedElement"])

    def dump(self):
        return self.children.dump()

    def get_definition(self):
        return {
            "name": self.__class__.__name__,
            "ownedRelatedElement": self.children.get_definition() if self.children else None,
        }


class PayloadFeature:
    def __init__(self, definition):
        self.identification = None
        self.valuepart = None
        self.multiplicity1 = None
        self.multiplicity2 = None
        self.children = None
        self.pfsp = None
        if valid_definition(definition, self.__class__.__name__):
            if definition["identification"] is not None:
                self.identification = Identification(definition["identification"])

            if definition["valuepart"] is not None:
                self.valuepart = ValuePart(definition["valuepart"])

            if definition["multiplicity1"] is not None:
                self.multiplicity1 = OwnedMultiplicity(definition["multiplicity1"])

            if definition["multiplicity2"] is not None:
                self.multiplicity2 = OwnedMultiplicity(definition["multiplicity2"])

            if definition["ownedRelationship"] is not None:
                self.children = OwnedFeatureTyping(definition["ownedRelationship"])

            if definition["pfsp"] is not None:
                self.pfsp = PayloadFeatureSpecializationPart(definition["pfsp"])

    def dump(self):
        output = []
        if self.pfsp is not None:
            if self.identification is not None:
                output.append(self.identification.dump())
            output.append(self.pfsp.dump())
            if self.valuepart is not None:
                output.append(self.valuepart.dump())
        elif self.valuepart is not None:
            if self.identification is not None:
                output.append(self.identification.dump())
            output.append(self.valuepart.dump())
        else:
            if self.multiplicity1 is None:
                if self.children is not None:
                    output.append(self.children.dump())
                if self.multiplicity2 is not None:
                    output.append(self.multiplicity2.dump())
            else:
                output.append(self.multiplicity1.dump())
                if self.children is not None:
                    output.append(self.children.dump())
        return "".join(output)

    def get_definition(self):
        output = {
            "name": self.__class__.__name__,
            "identification": None,
            "valuepart": None,
            "multiplicity1": None,
            "multiplicity2": None,
            "ownedRelationship": None,
            "pfsp": None,
        }
        if self.identification is not None:
            output["identification"] = self.identification.get_definition()
        if self.valuepart is not None:
            output["valuepart"] = self.valuepart.get_definition()
        if self.multiplicity1 is not None:
            output["multiplicity1"] = self.multiplicity1.get_definition()
        if self.multiplicity2 is not None:
            output["multiplicity2"] = self.multiplicity2.get_definition()
        if self.children is not None:
            output["ownedRelationship"] = self.children.get_definition()
        if self.pfsp is not None:
            output["pfsp"] = self.pfsp.get_definition()
        return output


class PayloadFeatureSpecializationPart:
    def __init__(self, definition):
        self.children = []
        self.children2 = []
        self.mp = None
        if valid_definition(definition, self.__class__.__name__):
            for child in definition["ownedRelationship"]:
                self.children.append(FeatureSpecialization(child))

            for child in definition["ownedRelationship2"]:
                self.children2.append(FeatureSpecialization(child))

            if definition["mp"] is not None:
                self.mp = MultiplicityPart(definition["mp"])

    def dump(self):
        output = []
        if self.mp is None:
            for child in self.children:
                output.append(child.dump())
        else:
            if len(self.children2) == 0:
                output.append(self.mp.dump())
                for child in self.children:
                    output.append(child.dump())
            else:
                for child in self.children:
                    output.append(child.dump())
                output.append(self.mp.dump())
                for child in self.children2:
                    output.append(child.dump())
        return "".join(output)

    def get_definition(self):
        return {
            "name": self.__class__.__name__,
            "ownedRelationship": [x.get_definition() for x in self.children],
            "ownedRelationship2": [x.get_definition() for x in self.children2],
            "mp": self.mp.get_definition() if self.mp else None,
        }


class FlowEndMember:
    def __init__(self, definition):
        if valid_definition(definition, self.__class__.__name__):
            ore = definition["ownedRelatedElement"]
            self.children = FlowEnd(ore[0] if isinstance(ore, list) else ore)

    def dump(self):
        return self.children.dump()

    def get_definition(self):
        return {
            "name": self.__class__.__name__,
            "ownedRelatedElement": [self.children.get_definition()] if self.children else [],
        }


class FlowEnd:
    def __init__(self, definition):
        self.children = []
        if valid_definition(definition, self.__class__.__name__):
            for child in definition["fes"]:
                self.children.append(FlowEndSubsetting(child))
            for child in definition["ffm"]:
                self.children.append(FlowFeatureMember(child))

    def dump(self):
        output = []
        ffm_parts = []
        for child in self.children:
            if child.__class__.__name__ == "FlowEndSubsetting":
                output.append(child.dump())
            else:
                ffm_parts.append(child.dump())
        if ffm_parts:
            output.append(".".join(ffm_parts))
        return "".join(output)

    def get_definition(self):
        fes = [c.get_definition() for c in self.children if c.__class__.__name__ == "FlowEndSubsetting"]
        ffm = [c.get_definition() for c in self.children if c.__class__.__name__ == "FlowFeatureMember"]
        return {"name": self.__class__.__name__, "fes": fes, "ffm": ffm}


class FlowEndSubsetting:
    def __init__(self, definition):
        if valid_definition(definition, self.__class__.__name__):
            if definition["referencedFeature"] is not None:
                self.children = QualifiedName(definition["referencedFeature"])
            else:
                self.children = FeatureChainPrefix(definition["ownedRelatedElement"])

    def dump(self):
        if self.children.__class__.__name__ == "QualifiedName":
            return self.children.dump() + "."
        else:
            return self.children.dump()

    def get_definition(self):
        if self.children.__class__.__name__ == "QualifiedName":
            return {"name": self.__class__.__name__, "referencedFeature": self.children.get_definition(), "ownedRelatedElement": None}
        else:
            return {"name": self.__class__.__name__, "referencedFeature": None, "ownedRelatedElement": self.children.get_definition()}


class FeatureChainPrefix:
    def __init__(self, definition):
        self.children = []
        if valid_definition(definition, self.__class__.__name__):
            for child in definition["ownedRelationship"]:
                self.children.append(
                    OwnedFeatureChaining(definition["ownedRelationship"])
                )

    def dump(self):
        return "".join([x.dump() + "." for x in self.children])

    def get_definition(self):
        return {
            "name": self.__class__.__name__,
            "ownedRelationship": [x.get_definition() for x in self.children],
        }


class FlowFeatureMember:
    def __init__(self, definition):
        if valid_definition(definition, self.__class__.__name__):
            ore = definition["ownedRelatedElement"]
            self.children = FlowFeature(ore[0] if isinstance(ore, list) else ore)

    def dump(self):
        return self.children.dump()

    def get_definition(self):
        return {"name": self.__class__.__name__, "ownedRelatedElement": [self.children.get_definition()] if self.children else []}


class FlowFeature:
    def __init__(self, definition):
        if valid_definition(definition, self.__class__.__name__):
            self.children = FlowRedefinition(definition["ownedRelationship"][0])

    def dump(self):
        return self.children.dump()

    def get_definition(self):
        return {"name": self.__class__.__name__, "ownedRelationship": [self.children.get_definition()] if self.children else []}


class FlowRedefinition:
    def __init__(self, definition):
        if valid_definition(definition, self.__class__.__name__):
            self.children = QualifiedName(definition["redefinedFeature"])

    def dump(self):
        return self.children.dump()

    def get_definition(self):
        return {"name": self.__class__.__name__, "redefinedFeature": self.children.get_definition() if self.children else None}


class InterfaceUsage:
    def __init__(self, definition):
        if valid_definition(definition, self.__class__.__name__):
            self.prefix = None
            self.keyword = "interface"
            self.declaration = None
            self.body = None

            if definition["prefix"] is not None:
                self.prefix = OccurrenceUsagePrefix(definition["prefix"])

            # Handle both flat and nested formats
            if "usage" in definition and definition["usage"] is not None:
                usage_dict = definition["usage"]
                if isinstance(usage_dict, dict) and usage_dict.get("declaration") is not None:
                    self.declaration = InterfaceUsageDeclaration(usage_dict["declaration"])
            else:
                if definition.get("declaration") is not None:
                    self.declaration = InterfaceUsageDeclaration(definition["declaration"])

            if definition.get("body") is not None:
                body_dict = definition["body"]
                if isinstance(body_dict, dict) and body_dict.get("name") == "InterfaceBody":
                    self.body = InterfaceBody(body_dict)
                elif isinstance(body_dict, dict) and body_dict.get("name") == "DefinitionBody":
                    self.body = InterfaceBody({"name": "InterfaceBody", "item": body_dict.get("ownedRelatedElement", [])})
                else:
                    self.body = InterfaceBody(body_dict)

    def dump(self):
        output = []
        if self.prefix is not None:
            output.append(self.prefix.dump())
        output.append(self.keyword)
        if self.declaration is not None:
            output.append(self.declaration.dump())
        if self.body is not None:
            output.append(self.body.dump())

        return " ".join(output)

    def get_definition(self):
        output = {"name": self.__class__.__name__, "prefix": None}
        if self.prefix is not None:
            output["prefix"] = self.prefix.get_definition()
        output["usage"] = {
            "name": "Usage",
            "declaration": self.declaration.get_definition() if self.declaration else None
        }
        output["body"] = self.body.get_definition() if self.body else None
        return output


class InterfaceUsageDeclaration:
    def __init__(self, definition):
        if valid_definition(definition, self.__class__.__name__):
            self.declaration = None
            self.keyword = None
            self.part = None

            if definition["declaration"] is not None:
                self.declaration = UsageDeclaration(definition["declaration"])

            if definition["part1"] is not None:
                self.part = InterfacePart(definition["part1"])
                # The connect usage was optional and it was used here.
                self.keyword = "connect\n"
            elif definition["part2"] is not None:
                self.part = InterfacePart(definition["part2"])

    def dump(self):
        output = []
        if self.declaration is not None:
            output.append(self.declaration.dump())

        if self.keyword is not None:
            output.append(self.keyword)

        if self.part is not None:
            output.append(self.part.dump())

        return " ".join(output)

    def get_definition(self):
        output = {"name": self.__class__.__name__}
        output["declaration"] = self.declaration.get_definition() if self.declaration else None
        output["part1"] = self.part.get_definition() if self.part else None
        output["part2"] = None
        return output


class InterfacePart:
    def __init__(self, definition):
        if valid_definition(definition, self.__class__.__name__):
            if definition["binarypart"] is not None:
                self.children = BinaryInterfacePart(definition["binarypart"])
            elif definition["narypart"] is not None:
                print("InterfacePart: narypart not yet implemented")  # pragma: no cover
                self.children = None  # pragma: no cover
            else:
                print("InterfacePart: neither binarypart nor narypart")  # pragma: no cover
                self.children = None  # pragma: no cover

    def dump(self):
        if self.children is None:
            return ""
        return self.children.dump()

    def get_definition(self):
        if self.children is None:
            return {"name": self.__class__.__name__, "binarypart": None, "narypart": None}
        return {
            "name": self.__class__.__name__,
            "binarypart": self.children.get_definition() if self.children else None,
            "narypart": None
        }


class BinaryInterfacePart:
    def __init__(self, definition):
        if valid_definition(definition, self.__class__.__name__):
            self.children = []
            for relationship in definition["ownedRelationship"]:
                self.children.append(InterfaceEndMember(relationship))

    def dump(self):
        # Graceful fallback: a malformed/invalid interface part may yield
        # fewer than the expected two ends (e.g. InterfaceUsage_Invalid).
        if not self.children:
            return ""
        if len(self.children) == 1:
            return self.children[0].dump()
        if len(self.children) > 2:
            print("BinaryInterfacePart: more than 2 children")  # pragma: no cover
            return " to ".join([c.dump() for c in self.children[:2]])

        return self.children[0].dump() + " to " + self.children[1].dump()

    def get_definition(self):
        return {
            "name": self.__class__.__name__,
            "ownedRelationship": [c.get_definition() for c in self.children]
        }


class InterfaceEndMember:
    def __init__(self, definition):
        if valid_definition(definition, self.__class__.__name__):
            self.child = InterfaceEnd(definition["ownedRelatedElement"])

    def dump(self):
        return self.child.dump()

    def get_definition(self):
        return {
            "name": self.__class__.__name__,
            "ownedRelatedElement": self.child.get_definition()
        }


class InterfaceEnd:
    def __init__(self, definition):
        if valid_definition(definition, self.__class__.__name__):
            if definition["declaredName"] is not None:
                self.name = definition["declaredName"]
                self.keyword = "::>"
            else:
                self.name = None

            self.relationships = []
            for relationship in definition["ownedRelationship"]:
                if relationship["name"] == "OwnedReferenceSubsetting":
                    self.relationships.append(OwnedReferenceSubsetting(relationship))
                elif relationship["name"] == "OwnedMultiplicity":
                    self.relationships.append(OwnedMultiplicity(relationship))
                else:
                    print(f"InterfaceEnd: Unknown relationship type {relationship['name']}")

    def dump(self):
        output = []
        if self.name is not None:
            output.append(self.name)
            output.append(self.keyword)

        for relationship in self.relationships:
            output.append(relationship.dump())

        return " ".join(output)

    def get_definition(self):
        return {
            "name": self.__class__.__name__,
            "declaredName": self.name,
            "ownedRelationship": [r.get_definition() for r in self.relationships]
        }


class PortUsage:
    def __init__(self, definition=None):
        self.keyword = "port"
        if definition is not None:
            if valid_definition(definition, self.__class__.__name__):
                self.prefix = None
                self.usage = None

                if definition["prefix"] is not None:
                    self.prefix = OccurrenceUsagePrefix(definition["prefix"])

                if definition["usage"] is not None:
                    self.usage = Usage(definition["usage"])
        else:
            self.prefix = None
            self.usage = Usage()

    def dump(self):
        output = []
        if self.prefix is not None:
            output.append(self.prefix.dump())

        output.append(self.keyword)

        if self.usage is not None:
            output.append(self.usage.dump())

        return " ".join(output)

    def get_definition(self):
        output = {"name": self.__class__.__name__, "prefix": None}
        if self.prefix is not None:
            output["prefix"] = self.prefix.get_definition()

        output["usage"] = self.usage.get_definition()

        return output


class ConnectionUsage:
    def __init__(self, definition=None):
        self.prefix = None
        self.declaration = None
        self.keyword = "connection"
        self.keyword2 = "connect\n"
        self.part = None
        if definition is not None:
            if valid_definition(definition, self.__class__.__name__):
                if definition["prefix"] is not None:
                    self.prefix = OccurrenceUsagePrefix(definition["prefix"])

                if definition["declaration"] is not None:
                    self.declaration = UsageDeclaration(definition["declaration"])

                if definition["part"] is not None:
                    self.part = ConnectorPart(definition["part"])

                self.body = UsageBody(definition["body"])
        else:
            self.declaration = UsageDeclaration()
            self.body = UsageBody()

    def dump(self):
        output = []
        if self.prefix is not None:
            output.append(self.prefix.dump())

        if self.declaration is not None:
            output.append(self.keyword)
            output.append(self.declaration.dump())

        if self.part is not None:
            output.append(self.keyword2)
            output.append(self.part.dump())

        output.append(self.body.dump())

        return " ".join(output)

    def get_definition(self):
        output = {"name": self.__class__.__name__, "prefix": None, "declaration": None, "part": None}
        if self.prefix is not None:
            output["prefix"] = self.prefix.get_definition()
        if self.declaration is not None:
            output["declaration"] = self.declaration.get_definition()
        if self.part is not None:
            output["part"] = self.part.get_definition()
        output["body"] = self.body.get_definition()
        return output


class ConnectorPart:
    def __init__(self, definition):
        if valid_definition(definition, self.__class__.__name__):
            if definition["part"]["name"] == "BinaryConnectorPart":
                self.part = BinaryConnectorPart(definition["part"])
            elif definition["part"]["name"] == "NaryConnectorPart":
                self.part = NaryConnectorPart(definition["part"])
            else:
                print(f"ConnectorPart: unhandled {definition['part']['name']}")  # pragma: no cover
                self.part = None  # pragma: no cover

    def dump(self):
        return self.part.dump()

    def get_definition(self):
        return {
            "name": self.__class__.__name__,
            "part": self.part.get_definition() if self.part else None,
        }


class BinaryConnectorPart:
    def __init__(self, definition):
        if valid_definition(definition, self.__class__.__name__):
            self.children = []
            for relationship in definition["ownedRelationship"]:
                self.children.append(ConnectorEndMember(relationship))

    def dump(self):
        return " to ".join([child.dump() for child in self.children])

    def get_definition(self):
        return {
            "name": self.__class__.__name__,
            "ownedRelationship": [c.get_definition() for c in self.children],
        }


class NaryConnectorPart:
    def __init__(self, definition):
        if valid_definition(definition, self.__class__.__name__):
            self.children = []
            for relationship in definition["ownedRelationship"]:
                self.children.append(ConnectorEndMember(relationship))

    def dump(self):
        return "(" + ", ".join([child.dump() for child in self.children]) + ")"

    def get_definition(self):
        return {
            "name": self.__class__.__name__,
            "ownedRelationship": [c.get_definition() for c in self.children],
        }


class ConnectorEndMember:
    def __init__(self, definition):
        if valid_definition(definition, self.__class__.__name__):
            self.children = []
            # Handle both list (from visitor) and dict (from grammar) formats
            rel = definition["ownedRelatedElement"]
            if isinstance(rel, list):
                for element in rel:
                    if element.get("name") == "ConnectorEnd":
                        self.children.append(ConnectorEnd(element))
                    elif element.get("name") == "ConnectorEndMember":
                        # Nested structure from visitor
                        nested = element.get("ownedRelatedElement", [])
                        if isinstance(nested, list):
                            for child in nested:
                                self.children.append(ConnectorEnd(child))

    def dump(self):
        return "".join([child.dump() for child in self.children])

    def get_definition(self):
        output = {
            "name": self.__class__.__name__,
            "ownedRelatedElement": [],
        }
        for child in self.children:
            output["ownedRelatedElement"].append(child.get_definition())
        return output


class ConnectorEnd:
    def __init__(self, definition):
        if valid_definition(definition, self.__class__.__name__):
            self.declaredName = None
            if definition["declaredName"] is not None:
                self.declaredName = definition["declaredName"]

            self.children = []
            for relationship in definition["ownedRelationship"]:
                if relationship["name"] == "OwnedReferenceSubsetting":
                    self.children.append(OwnedReferenceSubsetting(relationship))
                else:
                    self.children.append(OwnedMultiplicity(relationship))

    def dump(self):
        output = []
        if self.declaredName is not None:
            output.append(self.declaredName)
            output.append("references")

        for child in self.children:
            output.append(child.dump())

        return " ".join(output)

    def get_definition(self):
        output = {
            "name": self.__class__.__name__,
            "declaredName": self.declaredName,
            "ownedRelationship": [],
        }
        for child in self.children:
            output["ownedRelationship"].append(child.get_definition())
        return output


class OwnedReferenceSubsetting:
    def __init__(self, definition):
        if valid_definition(definition, self.__class__.__name__):
            self.referencedFeature = None
            if definition["referencedFeature"] is not None:
                self.referencedFeature = QualifiedName(definition["referencedFeature"])

            self.elements = []
            for element in definition["ownedRelatedElement"]:
                self.elements.append(OwnedFeatureChain(element))

    def dump(self):
        parts = []
        if self.referencedFeature is not None:
            parts.append(self.referencedFeature.dump())
        if self.elements:
            parts.extend([child.dump() for child in self.elements])
        return ".".join(parts) if parts else ""

    def get_definition(self):
        output = {
            "name": self.__class__.__name__,
            "referencedFeature": None,
            "ownedRelatedElement": [],
        }
        if self.referencedFeature is not None:
            output["referencedFeature"] = self.referencedFeature.get_definition()
        for element in self.elements:
            output["ownedRelatedElement"].append(element.get_definition())
        return output


class AttributeUsage:
    def __init__(self, definition=None):
        self.prefix = None
        self.keyword = "attribute"
        if definition is not None:
            if valid_definition(definition, self.__class__.__name__):
                if definition["prefix"] is not None:
                    self.prefix = UsagePrefix(definition["prefix"])
                else:
                    self.prefix = None
                self.usage = Usage(definition["usage"])
        else:
            self.usage = Usage()

    def dump(self):
        if self.prefix is None:
            return " ".join([self.keyword, self.usage.dump()])
        else:
            return " ".join([self.prefix.dump(), self.keyword, self.usage.dump()])

    def get_definition(self):
        output = {"name": self.__class__.__name__, "prefix": None}
        if self.prefix is not None:
            output["prefix"] = self.prefix.get_definition()

        output["usage"] = self.usage.get_definition()

        return output


class UsagePrefix:
    #  UsagePrefix :
    # 	prefix=BasicUsagePrefix usageKeyword += UsageExtensionKeyword*
    # ;
    def __init__(self, definition):
        self.prefix = None
        self.keyword = []
        if valid_definition(definition, self.__class__.__name__):
            if definition["prefix"] is not None:
                self.prefix = BasicUsagePrefix(definition["prefix"])
            for keyword in definition["usageKeyword"]:
                self.keyword.append(UsageExtensionKeyword(keyword))

    def dump(self):
        if self.prefix is not None:
            return " ".join([self.prefix.dump()] + [x.dump() for x in self.keyword])
        else:
            return " ".join([x.dump() for x in self.keyword])

    def get_definition(self):
        output = {
            "name": self.__class__.__name__,
            "prefix": self.prefix.get_definition() if self.prefix else None,
            "usageKeyword": [kw.get_definition() for kw in self.keyword],
        }
        return output


class PartUsage:
    def __init__(self, definition=None):
        if definition is not None:
            if valid_definition(definition, "PartUsage"):
                if definition["prefix"] is not None:
                    prefix_name = definition["prefix"].get("name", "OccurrenceUsagePrefix")
                    self.prefix = globals()[prefix_name](definition["prefix"])
                else:
                    self.prefix = None

                self.keyword = "part"
                self.usage = Usage(definition["usage"])
        else:
            self.prefix = None
            self.keyword = "part"
            self.usage = Usage()

    def dump(self):
        output = []
        if self.prefix is not None:
            output.append(self.prefix.dump())

        output.append(self.keyword)
        output.append(self.usage.dump())
        return " ".join(output)

    def get_definition(self):
        pre = None
        if self.prefix is not None:
            pre = self.prefix.get_definition()

        u = None
        if self.usage is not None:
            u = self.usage.get_definition()

        return {"name": self.__class__.__name__, "prefix": pre, "usage": u}


class OccurrenceUsagePrefix:
    def __init__(self, definition):
        if valid_definition(definition, "OccurrenceUsagePrefix"):
            self.prefix = BasicUsagePrefix(definition["prefix"])
            self.isIndividual = definition["isIndividual"]
            if definition["portionKind"] is not None:
                self.portionKind = PortionKind(definition["portionKind"])
            else:
                self.portionKind = None

            if len(definition["usageExtension"]) > 0:
                self.usageExtension = []
                for ext in definition["usageExtension"]:
                    self.usageExtension.append(UsageExtensionKeyword(ext))
            else:
                self.usageExtension = []

    def dump(self):
        output = []
        output.append(self.prefix.dump())
        if self.isIndividual:
            output.append("individual")

        if self.portionKind is not None:
            output.append(self.portionKind.dump())

        for ext in self.usageExtension:
            output.append(ext.dump())

        return " ".join(output)

    def get_definition(self):
        return {
            "name": self.__class__.__name__,
            "prefix": self.prefix.get_definition() if self.prefix else None,
            "isIndividual": self.isIndividual,
            "portionKind": self.portionKind.get_definition() if self.portionKind else None,
            "usageExtension": [e.get_definition() for e in self.usageExtension],
        }


class PortionKind:
    def __init__(self, definition):
        self.kind = None
        if valid_definition(definition, "PortionKind"):
            self.kind = definition.get("kind")

    def dump(self):
        return self.kind or ""

    def get_definition(self):
        return {"name": self.__class__.__name__, "kind": self.kind}


class BasicUsagePrefix:
    def __init__(self, definition):
        if valid_definition(definition, "BasicUsagePrefix"):
            if definition["prefix"] is not None:
                self.prefix = RefPrefix(definition["prefix"])
            else:
                # This happens when nothing was found in RefPrefix.
                self.prefix = None
            self.isReference = definition["isReference"]

    def dump(self):
        output = []
        if self.prefix is not None:
            output.append(self.prefix.dump())

        if self.isReference:
            output.append("ref")

        return " ".join(output)

    def get_definition(self):
        output = {
            "name": self.__class__.__name__,
            "prefix": self.prefix.get_definition() if self.prefix else None,
            "isReference": self.isReference,
        }
        return output


class RefPrefix:
    def __init__(self, definition=None):
        self.direction = None
        if definition is not None:
            if valid_definition(definition, self.__class__.__name__):
                if definition["direction"] is not None:
                    self.direction = FeatureDirection(definition["direction"])

                self.isAbstract = definition["isAbstract"]
                self.isVariation = definition["isVariation"]
                self.isReadOnly = definition["isReadOnly"]
                self.isDerived = definition["isDerived"]
                self.isEnd = definition["isEnd"]

        else:
            self.direction = FeatureDirection()
            self.isAbstract = False
            self.isVariation = False
            self.isReadOnly = False
            self.isDerived = False
            self.isEnd = False

    def dump(self):
        output = []
        if self.direction is not None:
            direction = self.direction.dump()
            if not direction == "":
                output.append(direction)

        if self.isAbstract:
            output.append("abstract")
        elif self.isVariation:
            output.append("variation")

        if self.isReadOnly:
            output.append("readonly")

        if self.isDerived:
            output.append("derived")

        if self.isEnd:
            output.append("end")

        return " ".join(output)

    def get_definition(self):
        output = {"name": self.__class__.__name__}
        output["isAbstract"] = self.isAbstract
        output["isVariation"] = self.isVariation
        output["isReadOnly"] = self.isReadOnly
        output["isDerived"] = self.isDerived
        output["isEnd"] = self.isEnd
        output["direction"] = self.direction.get_definition()
        return output


class FeatureDirection:
    def __init__(self, definition=None):
        if definition is not None:
            if valid_definition(definition, self.__class__.__name__):
                self.isIn = definition["in"] == "in "
                self.isOut = definition["out"] == "out"
                self.isInOut = definition["inout"] == "inout"
        else:
            self.isIn = False
            self.isOut = False
            self.isInOut = False

    def dump(self):
        if self.isInOut:
            return "inout"
        elif self.isIn:
            return "in"
        elif self.isOut:
            return "out"
        else:
            return ""

    def get_definition(self):
        output = {"name": self.__class__.__name__, "in": "", "out": "", "inout": ""}
        if self.isIn:
            output["in"] = "in "

        if self.isOut:
            output["out"] = "out"

        if self.isInOut:
            output["inout"] = "inout"
        return output


class ItemUsage:
    def __init__(self, definition=None):
        if definition is not None:
            if valid_definition(definition, "ItemUsage"):
                self.prefix = None
                if definition["prefix"] is not None:
                    self.prefix = OccurrenceUsagePrefix(definition["prefix"])
                self.keyword = "item"
                self.usage = Usage(definition["usage"])
        else:
            # Create an empty item
            self.prefix = None
            self.keyword = "item"
            self.usage = Usage()

    def dump(self):
        output = []
        if self.prefix is not None:
            output.append(self.prefix.dump())
        output.append(self.keyword)
        output.append(self.usage.dump())
        return " ".join(output)

    def get_definition(self):
        output = {}
        output["name"] = self.__class__.__name__
        if self.prefix is not None:
            output["prefix"] = self.prefix.get_definition()
        else:
            output["prefix"] = None
        output["usage"] = self.usage.get_definition()
        return output


class Usage:
    def __init__(self, definition=None):
        if definition is not None:
            if valid_definition(definition, "Usage"):
                self.declaration = UsageDeclaration(definition["declaration"])
                self.completion = UsageCompletion(definition["completion"]) if "completion" in definition else None
        else:
            self.declaration = UsageDeclaration()
            self.completion = UsageCompletion()

    def dump(self):
        output = []
        if self.completion is not None:
            output.append(self.completion.dump())
        return self.declaration.dump() + "".join(output)

    def get_definition(self):
        output = {}
        output["name"] = self.__class__.__name__
        output["declaration"] = self.declaration.get_definition()
        if self.completion is not None:
            output["completion"] = self.completion.get_definition()
        return output


class UsageDeclaration:
    def __init__(self, definition=None):
        if definition is not None:
            if valid_definition(definition, "UsageDeclaration"):
                self.declaration = FeatureDeclaration(definition["declaration"])
        else:
            self.declaration = FeatureDeclaration()

    def dump(self):
        return self.declaration.dump()

    def get_definition(self):
        return {
            "name": self.__class__.__name__,
            "declaration": self.declaration.get_definition(),
        }


class FeatureDeclaration:
    def __init__(self, definition=None):
        if definition is not None:
            if valid_definition(definition, "FeatureDeclaration"):
                if definition["identification"] is not None:
                    self.identification = Identification(definition["identification"])
                else:
                    self.identification = None

                if definition["specialization"] is not None:
                    self.specialization = FeatureSpecializationPart(
                        definition["specialization"]
                    )
                else:
                    self.specialization = None
        else:
            self.identification = None
            self.specialization = None

    def dump(self):
        output = []
        if self.identification is not None:
            output.append(self.identification.dump())

        if self.specialization is not None:
            output.append(self.specialization.dump())

        return "".join(output)

    def get_definition(self):
        iden = None
        spec = None
        if self.identification is not None:
            iden = self.identification.get_definition()

        if self.specialization is not None:
            spec = self.specialization.get_definition()

        return {
            "name": self.__class__.__name__,
            "identification": iden,
            "specialization": spec,
        }


class FeatureSpecializationPart:
    def __init__(self, definition=None):
        if definition is not None:
            if valid_definition(definition, "FeatureSpecializationPart"):
                if definition["multiplicity"] is not None:
                    # We found the set where one specialization came first
                    # ( specialization+=FeatureSpecialization )+
                    #    multiplicity=MultiplicityPart?
                    #    specialization2+=FeatureSpecialization*
                    self.multiplicity = MultiplicityPart(definition["multiplicity"])
                elif definition["multiplicity2"] is not None:
                    # We found the set where the multiplicity came first
                    # multiplicity2=MultiplicityPart specialization+=FeatureSpecialization*
                    self.multiplicity = MultiplicityPart(definition["multiplicity2"])
                else:
                    # We found the case where none were specified
                    self.multiplicity = None

                self.specializations = []
                for specialization in definition["specialization"]:
                    self.specializations.append(FeatureSpecialization(specialization))

                self.specializations2 = []
                if definition["specialization2"] is not None:
                    for specialization in definition["specialization2"]:
                        self.specializations2.append(
                            FeatureSpecialization(specialization)
                        )
        else:
            self.multiplicity = None
            self.specializations = []
            self.specializations2 = []

    def dump(self):
        if len(self.specializations2) > 0:
            # Multiplicity in between
            output = [child.dump() for child in self.specializations]
            if self.multiplicity is not None:
                output.append(self.multiplicity.dump())

            for child in self.specializations2:
                output.append(child.dump())

        elif len(self.specializations) == 1 and self.multiplicity is not None:
            # Case 1 - modified for the case where specializations2 would be empty
            output = [child.dump() for child in self.specializations]
            output.append(self.multiplicity.dump())

        elif len(self.specializations) > 1 and self.multiplicity is not None:
            # Multiple specializations with multiplicity - put multiplicity after first
            output = [self.specializations[0].dump()]
            output.append(self.multiplicity.dump())
            for child in self.specializations[1:]:
                output.append(child.dump())

        else:
            # Multiplicity at start or no multiplicity found
            output = []
            if self.multiplicity is not None:
                output.append(self.multiplicity.dump())

            for child in self.specializations:
                output.append(child.dump())

        return " ".join(output)

    def get_definition(self):
        output = {
            "name": self.__class__.__name__,
            "multiplicity": None,
            "multiplicity2": None,  # This is never used in this fashion.
            "specialization": [],
            "specialization2": [],
        }

        if self.multiplicity is not None:
            output["multiplicity"] = self.multiplicity.get_definition()

        if len(self.specializations) > 0:
            for child in self.specializations:
                output["specialization"].append(child.get_definition())

        if len(self.specializations2) > 0:
            for child in self.specializations2:
                output["specialization2"].append(child.get_definition())

        return output


class MultiplicityPart:
    def __init__(self, definition):
        if valid_definition(definition, "MultiplicityPart"):
            self.isOrdered = definition["isOrdered"]
            self.isNonunique = definition["isNonunique"]
            self.isOrdered2 = definition["isOrdered"]
            self.isNonunique2 = definition["isNonunique"]

            self.children = []
            for relationship in definition["ownedRelationship"]:
                self.children.append(OwnedMultiplicity(relationship))

    def dump(self):
        output = [child.dump() for child in self.children]

        if self.isOrdered and not self.isOrdered2:
            output.append("ordered")

        if self.isNonunique or self.isNonunique2:
            output.append("nonunique")

        if self.isOrdered2 and not self.isOrdered:
            output.append("ordered")

        return " ".join(output)

    def get_definition(self):
        output = {
            "name": self.__class__.__name__,
            "isOrdered": self.isOrdered,
            "isNonunique": self.isNonunique,
            "ownedRelationship": []
        }
        for child in self.children:
            output["ownedRelationship"].append(child.get_definition())
        return output


class OwnedMultiplicity:
    def __init__(self, definition):
        if valid_definition(definition, "OwnedMultiplicity"):
            self.children = []
            for element in definition["ownedRelatedElement"]:
                self.children.append(MultiplicityRange(element))

    def dump(self):
        output = [child.dump() for child in self.children]
        return "".join(output)

    def get_definition(self):
        output = {"name": self.__class__.__name__, "ownedRelatedElement": []}
        for child in self.children:
            output["ownedRelatedElement"].append(child.get_definition())
        return output


class MultiplicityRange:
    def __init__(self, definition):
        if valid_definition(definition, "MultiplicityRange"):
            self.children = []
            for relationship in definition["ownedRelationship"]:
                self.children.append(MultiplicityExpressionMember(relationship))

    def dump(self):
        output = [child.dump() for child in self.children]
        return "[" + "..".join(output) + "]"

    def get_definition(self):
        output = {"name": self.__class__.__name__, "ownedRelationship": []}
        for child in self.children:
            output["ownedRelationship"].append(child.get_definition())
        return output


class MultiplicityExpressionMember:
    def __init__(self, definition):
        if valid_definition(definition, "MultiplicityExpressionMember"):
            self.children = []
            for element in definition["ownedRelatedElement"]:
                self.children.append(MultiplicityRelatedElement(element))

    def dump(self):
        return "".join([child.dump() for child in self.children])

    def get_definition(self):
        output = {"name": self.__class__.__name__, "ownedRelatedElement": []}
        for child in self.children:
            output["ownedRelatedElement"].append(child.get_definition())
        return output


class MultiplicityRelatedElement:
    def __init__(self, definition):
        if valid_definition(definition, "MultiplicityRelatedElement"):
            if "name" in definition["ownedRelatedElement"]:
                if definition["ownedRelatedElement"]["name"] == "LiteralInteger":
                    self.element = LiteralInteger(definition["ownedRelatedElement"])
                elif definition["ownedRelatedElement"]["name"] == "LiteralInfinity":
                    self.element = LiteralInfinity(definition["ownedRelatedElement"])
                elif definition["ownedRelatedElement"]["name"] == "FeatureReferenceExpression":
                    self.element = FeatureReferenceExpression(definition["ownedRelatedElement"])
                else:
                    print(f"MultiplicityRelatedElement: unhandled {definition['ownedRelatedElement']['name']}")  # pragma: no cover
                    self.element = None  # pragma: no cover

    def dump(self):
        if self.element is None:
            return ""
        return str(self.element.dump())

    def get_definition(self):
        if self.element is None:
            return {"name": self.__class__.__name__, "ownedRelatedElement": None}
        return {
            "name": self.__class__.__name__,
            "ownedRelatedElement": self.element.get_definition()
        }


class LiteralString:
    def __init__(self, definition):
        if valid_definition(definition, self.__class__.__name__):
            self.element = definition["value"]

    def dump(self):
        return self.element

    def get_definition(self):
        return {"name": self.__class__.__name__, "value": self.element}


class LiteralBoolean:
    def __init__(self, definition):
        if valid_definition(definition, self.__class__.__name__):
            self.element = definition["value"]

    def dump(self):
        return self.element

    def get_definition(self):
        return {"name": self.__class__.__name__, "value": self.element}


class LiteralInteger:
    def __init__(self, definition):
        if valid_definition(definition, "LiteralInteger"):
            self.element = definition["value"]

    def dump(self):
        return self.element

    def get_definition(self):
        return {"name": self.__class__.__name__, "value": self.element}


class LiteralReal:
    def __init__(self, definition):
        if valid_definition(definition, self.__class__.__name__):
            self.element = definition["value"]

    def dump(self):
        return self.element

    def get_definition(self):
        return {"name": self.__class__.__name__, "value": self.element}


class LiteralInfinity:
    def __init__(self, definition):
        if valid_definition(definition, self.__class__.__name__):
            self.element = "*"

    def dump(self):
        return self.element

    def get_definition(self):
        return {"name": self.__class__.__name__, "value": self.element}


class FeatureSpecialization:
    def __init__(self, definition):
        self.relationship = None
        if valid_definition(definition, "FeatureSpecialization"):
            if definition["ownedRelationship"]["name"] == "Typings":
                self.relationship = Typings(definition["ownedRelationship"])
            elif definition["ownedRelationship"]["name"] == "Subsettings":
                self.relationship = Subsettings(definition["ownedRelationship"])
            elif definition["ownedRelationship"]["name"] == "References":
                self.relationship = References(definition["ownedRelationship"])
            elif definition["ownedRelationship"]["name"] == "Redefinitions":
                self.relationship = Redefinitions(definition["ownedRelationship"])
            else:
                print(f"FeatureSpecialization: unhandled {definition['ownedRelationship']['name']}")  # pragma: no cover

    def dump(self):
        if self.relationship is None:
            return ""
        return self.relationship.dump()

    def get_definition(self):
        if self.relationship is None:
            return {"name": self.__class__.__name__}
        return {
            "name": self.__class__.__name__,
            "ownedRelationship": self.relationship.get_definition(),
        }


class Redefinitions:
    def __init__(self, definition):
        if valid_definition(definition, self.__class__.__name__):
            self.keyword = ":>>"
            self.children = []
            for relationship in definition["ownedRelationship"]:
                self.children.append(OwnedRedefinition(relationship))

    def dump(self):
        output = [child.dump() for child in self.children]
        output.insert(0, self.keyword)
        return " ".join(output)

    def get_definition(self):
        output = {
            "name": self.__class__.__name__,
            "ownedRelationship": [],
        }
        for child in self.children:
            output["ownedRelationship"].append(child.get_definition())
        return output


class References:
    """``references`` / ``::>`` type-only reference.

    A Reference points at a type without inheriting its features (no
    redefinition semantics, no subsetting). The source form is::

        attribute ::> Type;        # operator
        attribute references Type; # keyword

    Both produce the same parse tree and the same dump shape.
    """

    KEYWORD = "::>"

    def __init__(self, definition):
        if valid_definition(definition, self.__class__.__name__):
            self.keyword = self.KEYWORD
            self.children = []
            for relationship in definition.get("ownedRelationship", []):
                self.children.append(OwnedReferenceSubsetting(relationship))

    def dump(self):
        output = [child.dump() for child in self.children]
        output.insert(0, self.keyword)
        return " ".join(output)

    def get_definition(self):
        output = {
            "name": self.__class__.__name__,
            "ownedRelationship": [],
        }
        for child in self.children:
            output["ownedRelationship"].append(child.get_definition())
        return output


class OwnedRedefinition:
    def __init__(self, definition):
        if valid_definition(definition, "OwnedRedefinition"):
            # A dotted chain (:>> base.x) carries BOTH the head
            # qualifiedName and one OwnedFeatureChain per remaining
            # segment. Keep both so chained forms survive round-trip.
            self.redefinedFeature = None
            if definition["redefinedFeature"] is not None:
                self.redefinedFeature = QualifiedName(definition["redefinedFeature"])
            self.elements = []
            for element in definition.get("ownedRelatedElement", []) or []:
                self.elements.append(OwnedFeatureChain(element))

    def dump(self):
        parts = []
        if self.redefinedFeature is not None:
            parts.append(self.redefinedFeature.dump())
        parts.extend([e.dump() for e in self.elements])
        return ".".join(parts) if parts else ""

    def get_definition(self):
        if self.redefinedFeature is not None and not self.elements:
            return {
                "name": self.__class__.__name__,
                "redefinedFeature": self.redefinedFeature.get_definition(),
                "ownedRelatedElement": [],
            }
        else:
            output = {
                "name": self.__class__.__name__,
                "redefinedFeature": self.redefinedFeature.get_definition() if self.redefinedFeature is not None else None,
                "ownedRelatedElement": [e.get_definition() for e in self.elements],
            }
            if self.redefinedFeature is None and not self.elements:
                # Fully empty: keep legacy shape
                pass
            return output


class Subsettings:
    def __init__(self, definition):
        if valid_definition(definition, "Subsettings"):
            # Subsets ( ',' ownedRelationship += OwnedSubsetting )*
            self.keyword = ":>"
            self.children = []
            for relationship in definition.get("ownedRelationship", []):
                self.children.append(OwnedSubsetting(relationship))

    def dump(self):
        return self.keyword + ", ".join([child.dump() for child in self.children])

    def get_definition(self):
        output = {
            "name": self.__class__.__name__,
            "ownedRelationship": [],
        }
        for child in self.children:
            output["ownedRelationship"].append(child.get_definition())
        return output


class OwnedSubsetting:
    def __init__(self, definition):
        if valid_definition(definition, "OwnedSubsetting"):
            # subsettedFeature = QualifiedName | ownedRelatedElement += OwnedFeatureChain
            # A dotted chain (:> base.x) carries BOTH: the head qualifiedName
            # plus one OwnedFeatureChain per remaining segment. Keep both so
            # chained forms survive round-trip (v0.42.0).
            self.elements = []
            if definition["subsettedFeature"] is not None:
                self.elements.append(QualifiedName(definition["subsettedFeature"]))
            for element in definition.get("ownedRelatedElement", []) or []:
                self.elements.append(OwnedFeatureChain(element))

    def dump(self):
        return ".".join([child.dump() for child in self.elements])

    def get_definition(self):
        output = {
            "name": self.__class__.__name__,
            "subsettedFeature": None,
            "ownedRelatedElement": [],
        }
        for element in self.elements:
            if isinstance(element, QualifiedName):
                output["subsettedFeature"] = element.get_definition()
            else:
                output["ownedRelatedElement"].append(element.get_definition())
        return output


class OwnedFeatureChain:
    def __init__(self, definition):
        if valid_definition(definition, self.__class__.__name__):
            self.feature = FeatureChain(definition["feature"])

    def dump(self):
        return self.feature.dump()

    def get_definition(self):
        output = {
            "name": self.__class__.__name__,
            "feature": None,
        }
        if self.feature is not None:
            output["feature"] = self.feature.get_definition()
        return output


class FeatureChain:
    def __init__(self, definition):
        if valid_definition(definition, self.__class__.__name__):
            self.children = []
            for relationship in definition["ownedRelationship"]:
                self.children.append(OwnedFeatureChaining(relationship))

    def dump(self):
        return ".".join([child.dump() for child in self.children])

    def get_definition(self):
        output = {
            "name": self.__class__.__name__,
            "ownedRelationship": [],
        }
        for child in self.children:
            output["ownedRelationship"].append(child.get_definition())
        return output


class OwnedFeatureChaining:
    def __init__(self, definition):
        if valid_definition(definition, self.__class__.__name__):
            self.chainingFeature = QualifiedName(definition["chainingFeature"])

    def dump(self):
        return self.chainingFeature.dump()

    def get_definition(self):
        output = {
            "name": self.__class__.__name__,
            "chainingFeature": None,
        }
        if self.chainingFeature is not None:
            output["chainingFeature"] = self.chainingFeature.get_definition()
        return output


class Typings:
    def __init__(self, definition):
        if valid_definition(definition, "Typings"):
            self.relationships = []
            for rel in definition.get("ownedRelationship", []):
                self.relationships.append(rel)
            self.typing = TypedBy(definition["typedby"])

    def dump(self):
        return self.typing.dump()

    def get_definition(self):
        output = {
            "name": self.__class__.__name__,
            "ownedRelationship": self.relationships,
            "typedby": self.typing.get_definition(),
        }
        return output


class TypedBy:
    def __init__(self, definition):
        if valid_definition(definition, "TypedBy"):
            self.keyword = ": "

            self.relationships = []
            for relationship in definition["ownedRelationship"]:
                if "FeatureTyping" == relationship["name"]:
                    self.relationships.append(FeatureTyping(relationship))
                else:
                    print(f"TypedBy: unhandled {relationship['name']}")  # pragma: no cover

    def dump(self):
        output = []
        for relationship in self.relationships:
            output.append(relationship.dump())
        return self.keyword + "".join(output)

    def get_definition(self):
        output = {"name": self.__class__.__name__, "ownedRelationship": []}
        for child in self.relationships:
            output["ownedRelationship"].append(child.get_definition())

        return output


class FeatureTyping:
    def __init__(self, definition):
        if valid_definition(definition, self.__class__.__name__):
            if definition["ownedRelationship"]["name"] == "OwnedFeatureTyping":
                self.relationship = OwnedFeatureTyping(definition["ownedRelationship"])
            elif definition["ownedRelationship"]["name"] == "ConjugatedPortTyping":
                self.relationship = ConjugatedPortTyping(
                    definition["ownedRelationship"]
                )
            else:
                print(f"FeatureTyping: unhandled {definition['ownedRelationship']['name']}")  # pragma: no cover
                self.relationship = None  # pragma: no cover

    def dump(self):
        if self.relationship is None:
            return ""
        return self.relationship.dump()

    def get_definition(self):
        if self.relationship is None:
            return {"name": self.__class__.__name__}
        output = {
            "name": self.__class__.__name__,
            "ownedRelationship": self.relationship.get_definition(),
        }

        return output


class ConjugatedPortTyping:
    def __init__(self, definition):
        if valid_definition(definition, self.__class__.__name__):
            self.keyword = "~"
            # We skip a step in the grammar here.
            self.name = QualifiedName(definition["conjugatedPortDefinition"])

    def dump(self):
        return self.keyword + self.name.dump()

    def get_definition(self):
        return {
            "name": self.__class__.__name__,
            "conjugatedPortDefinition": self.name.get_definition(),
        }


class OwnedFeatureTyping:
    def __init__(self, definition):
        if valid_definition(definition, self.__class__.__name__):
            self.type = FeatureType(definition["type"])

    def dump(self):
        return self.type.dump()

    def get_definition(self):
        output = {"name": self.__class__.__name__, "type": self.type.get_definition()}

        return output


class FeatureType:
    def __init__(self, definition):
        if valid_definition(definition, "FeatureType"):
            if definition["type"] is not None:
                self.type = QualifiedName(definition["type"])
            else:
                self.type = None
                self.elements = []
                for element in definition["ownedRelatedElement"]:
                    self.elements.append(OwnedFeatureChain(element))

    def dump(self):
        if self.type is not None:
            return self.type.dump()
        else:
            return ".".join([e.dump() for e in self.elements])

    def get_definition(self):
        if self.type is not None:
            output = {
                "name": self.__class__.__name__,
                "ownedRelatedElement": [],
                "type": self.type.get_definition(),
            }
        else:
            output = {
                "name": self.__class__.__name__,
                "ownedRelatedElement": [e.get_definition() for e in self.elements],
                "type": None,
            }
        return output


class UsageCompletion:
    def __init__(self, definition=None):
        if definition is not None:
            if valid_definition(definition, "UsageCompletion"):
                if definition["valuepart"] is None:
                    self.valuepart = None
                else:
                    self.valuepart = ValuePart(definition["valuepart"])
                self.body = UsageBody(definition["body"])
        else:
            self.valuepart = None
            self.body = UsageBody()

    def dump(self):
        output = []
        if self.valuepart is not None:
            output.append(self.valuepart.dump())

        output.append(self.body.dump())
        return "".join(output)

    def get_definition(self):
        vp = None
        if self.valuepart is not None:
            vp = self.valuepart.get_definition()

        return {
            "name": self.__class__.__name__,
            "valuepart": vp,
            "body": self.body.get_definition(),
        }


class UsageBody:
    def __init__(self, definition=None):
        if definition is not None:
            if valid_definition(definition, "UsageBody"):
                body_dict = definition["body"]
                if isinstance(body_dict, dict) and body_dict.get("name") == "ViewBody":
                    self.body = ViewBody(body_dict)
                else:
                    self.body = DefinitionBody(body_dict)
        else:
            self.body = DefinitionBody()

    def dump(self):
        return self.body.dump()

    def get_definition(self):
        return {"name": self.__class__.__name__, "body": self.body.get_definition()}


class PackageMember:
    def __init__(self, definition):
        self.children = []
        if valid_definition(definition, "PackageMember"):
            # This is a SysML Element
            if definition["prefix"] is not None:
                self.prefix = MemberPrefix(definition["prefix"])
            else:
                self.prefix = None

            if definition["ownedRelatedElement"]["name"] == "DefinitionElement":
                self.children.append(
                    DefinitionElement(definition["ownedRelatedElement"])
                )
            elif definition["ownedRelatedElement"]["name"] == "UsageElement":
                self.children.append(UsageElement(definition["ownedRelatedElement"]))
            else:
                raise AttributeError(
                    "This does not seem to be valid."
                )  # pragma: no cover

    def dump(self):
        output = []
        for child in self.children:
            output.append(child.dump())

        if self.prefix is not None:
            return " ".join(filter(None, (self.prefix.dump(), "".join(output))))
        else:
            return "".join(output)

    def get_definition(self):
        output = {
            "name": self.__class__.__name__,
            "prefix": None,
            "ownedRelationship": [],
        }
        if self.prefix is not None:
            output["prefix"] = self.prefix.get_definition()

        for child in self.children:
            output["ownedRelatedElement"] = child.get_definition()

        return output


class MemberPrefix:
    def __init__(self, definition):
        if valid_definition(definition, "MemberPrefix"):
            self.visibility = VisibilityIndicator(definition["visibility"])

    def dump(self):
        return self.visibility.dump()

    def get_definition(self):
        output = {"name": self.__class__.__name__}
        output["visibility"] = self.visibility.get_definition()
        return output


class Package:
    def __init__(self, definition=None):
        self.is_standard_library = False
        if definition is not None:
            if valid_definition(definition, self.__class__.__name__):
                # Elements inside of a package
                # ownedRelationship += PrefixMetadataMember
                # declaration = PackageDeclaration
                # body = PackageBody
                self.relationships = []
                for rel in definition["ownedRelationship"]:
                    self.relationships.append(json.dumps(rel))
                self.declaration = PackageDeclaration(definition["declaration"])
                self.body = PackageBody(definition["body"])
                self.is_standard_library = bool(definition.get("isStandardLibrary", False))
        else:
            self.relationships = []
            self.declaration = PackageDeclaration()
            self.body = PackageBody()

    def dump(self):
        prefix = "standard library " if self.is_standard_library else ""
        return prefix + "".join([self.declaration.dump(), self.body.dump()])

    def get_definition(self):
        output = {"name": self.__class__.__name__, "ownedRelationship": []}
        for rel in self.relationships:
            output["ownedRelationship"] = rel.get_definition()
        output["declaration"] = self.declaration.get_definition()
        output["body"] = self.body.get_definition()
        output["isStandardLibrary"] = self.is_standard_library

        return output


class Identification:
    def __init__(self, definition=None):
        if definition is not None:
            if valid_definition(definition, "Identification"):
                if definition["declaredShortName"] == None:
                    self.declaredShortName = None
                else:
                    if definition["declaredShortName"][0] == "<":
                        definition["declaredShortName"] = definition[
                            "declaredShortName"
                        ][1:]
                    if definition["declaredShortName"][-1] == ">":
                        definition["declaredShortName"] = definition[
                            "declaredShortName"
                        ][:-1]
                    self.declaredShortName = "<" + definition["declaredShortName"] + ">"
                self.declaredName = definition["declaredName"]
        else:
            self.declaredName = None
            self.declaredShortName = None

    def dump(self):
        return " ".join(filter(None, (self.declaredShortName, self.declaredName)))

    def get_definition(self):
        output = {"name": self.__class__.__name__}
        output["declaredShortName"] = self.declaredShortName
        output["declaredName"] = self.declaredName
        return output


class PackageDeclaration:
    def __init__(self, definition=None):
        if definition is not None:
            if valid_definition(definition, "PackageDeclaration"):
                self.identification = Identification(definition["identification"])
        else:
            self.identification = Identification()

    def dump(self):
        return "package " + self.identification.dump()

    def get_definition(self):
        return {
            "name": self.__class__.__name__,
            "identification": self.identification.get_definition(),
        }


class PackageBody:
    def __init__(self, definition=None):
        self.children = []
        if definition is not None:
            if valid_definition(definition, "PackageBody"):
                if "ownedRelationship" in definition:
                    for relationship in definition["ownedRelationship"]:
                        if "name" in relationship:
                            if relationship["name"] == "PackageMember":
                                self.children.append(PackageMember(relationship))
                            elif relationship["name"] == "ElementFilterMember":
                                pass  # pragma: no cover
                            elif relationship["name"] == "AliasMember":
                                self.children.append(AliasMember(relationship))
                            elif relationship["name"] == "Import":
                                self.children.append(Import(relationship))
                            elif relationship["name"] == "UsageElement":
                                self.children.append(UsageElement(relationship))
                            elif relationship["name"] == "DefinitionElement":
                                self.children.append(DefinitionElement(relationship))
                            else:
                                print(f"Unknown relationship in PackageBody: {json.dumps(relationship, indent=2, default=str)[:500]}")
                                raise AttributeError(
                                    "Failed to match this relationship"
                                )  # pragma: no cover
                        else:
                            print(f"PackageBody relationship without name key: {json.dumps(relationship, default=str)[:200]}")  # pragma: no cover
                else:
                    print("PackageBody without ownedRelationship key")  # pragma: no cover
            # else: handled inside function
        # else: no new definitions needed

    def dump(self):
        if len(self.children) == 0:
            return ";"
        else:
            output = []
            for child in self.children:
                output.append(child.dump())
            return " {\n" + "\n".join(output) + "\n}"

    def get_definition(self):
        output = {"name": self.__class__.__name__, "ownedRelationship": []}
        for child in self.children:
            output["ownedRelationship"].append(child.get_definition())
        return output


class AliasMember:
    def __init__(self, definition):
        if valid_definition(definition, "AliasMember"):
            if definition["prefix"] is not None:
                self.prefix = MemberPrefix(definition["prefix"])
            else:
                self.prefix = None

            self.body = RelationshipBody(definition["body"])

            self.memberShortName = definition["memberShortName"]
            self.memberName = definition["memberName"]
            self.memberElement = QualifiedName(definition["memberElement"])

    def dump(self):
        if self.memberShortName is None:
            shortName = ""
        else:
            shortName = "<" + self.memberShortName + "> "

        if self.prefix is None:
            prefix = ""
        else:
            prefix = self.prefix.dump() + " "

        return (
            prefix
            + "alias "
            + shortName
            + self.memberName
            + " for "
            + self.memberElement.dump()
            + self.body.dump()
        )

    def get_definition(self):
        return {
            "name": self.__class__.__name__,
            "prefix": None,
            "body": self.body.get_definition(),
            "memberShortName": self.memberShortName,
            "memberName": self.memberName,
            "memberElement": self.memberElement.get_definition()
        }


class RelationshipBody:
    def __init__(self, definition):
        self.children = []
        if isinstance(definition, dict) and "ownedRelationship" in definition:
            for relationship in definition["ownedRelationship"]:
                if relationship["name"] == "OwnedAnnotation":
                    self.children.append(OwnedAnnotation(relationship))
                else:
                    print(f"RelationshipBody: unhandled {relationship['name']}")  # pragma: no cover

    def dump(self):
        if len(self.children) == 0:
            return ";"
        else:
            return "{" + "\n".join([child.dump() for child in self.children]) + "}"

    def get_definition(self):
        return {
            "name": self.__class__.__name__,
            "ownedRelationship": [c.get_definition() for c in self.children]
        }


class OwnedAnnotation:
    def __init__(self, definition):
        if valid_definition(definition, "OwnedAnnotation"):
            self.children = []
            for element in definition["ownedRelatedElement"]:
                self.children.append(AnnotatingElement(element))

    def dump(self):
        return "\n".join([child.dump() for child in self.children])

    def get_definition(self):
        return {
            "name": self.__class__.__name__,
            "ownedRelatedElement": [c.get_definition() for c in self.children]
        }


class Import:
    def __init__(self, definition):
        if valid_definition(definition, "Import"):
            self.body = RelationshipBody(definition["body"])
            self.children = []
            relationship = definition["ownedRelationship"]
            if relationship["name"] == "NamespaceImport":
                self.children.append(NamespaceImport(relationship))
            elif relationship["name"] == "MembershipImport":
                self.children.append(MembershipImport(relationship))
            else:
                raise AttributeError(
                    "This does not seem to be valid"
                )  # pragma: no cover

    def dump(self):
        output = []
        for child in self.children:
            output.append(child.dump())
        return "".join(output) + self.body.dump()

    def get_definition(self):
        return {
            "name": self.__class__.__name__,
            "body": self.body.get_definition(),
            "ownedRelationship": self.children[0].get_definition() if self.children else None
        }


class MembershipImport:
    def __init__(self, definition):
        if valid_definition(definition, "MembershipImport"):
            self.prefix = ImportPrefix(definition["prefix"])
            self.membership = ImportedMembership(definition["membership"])

    def dump(self):
        return self.prefix.dump() + self.membership.dump()

    def get_definition(self):
        return {
            "name": self.__class__.__name__,
            "prefix": self.prefix.get_definition(),
            "membership": self.membership.get_definition()
        }


class ImportedMembership:
    def __init__(self, definition):
        if valid_definition(definition, "ImportedMembership"):
            self.name = QualifiedName(definition["importedMembership"])
            self.isRecursive = definition["isRecursive"]

    def dump(self):
        if not self.isRecursive:
            return self.name.dump()
        else:
            return self.name.dump() + "::**"

    def get_definition(self):
        return {
            "name": self.__class__.__name__,
            "importedMembership": self.name.get_definition(),
            "isRecursive": self.isRecursive
        }


class NamespaceImport:
    def __init__(self, definition):
        if valid_definition(definition, "NamespaceImport"):
            self.prefix = ImportPrefix(definition["prefix"])

            if len(definition["ownedRelatedElement"]) > 0:
                self.children = []
                for element in definition["ownedRelatedElement"]:
                    self.children.append(element)
            else:
                self.children = []

            self.namespace = ImportedNamespace(definition["namespace"])

    def dump(self):
        return self.prefix.dump() + self.namespace.dump()

    def get_definition(self):
        return {
            "name": self.__class__.__name__,
            "prefix": self.prefix.get_definition(),
            "ownedRelatedElement": [],
            "namespace": self.namespace.get_definition()
        }


class ImportPrefix:
    def __init__(self, definition):
        if valid_definition(definition, "ImportPrefix"):
            self.visibility = None
            if definition["visibility"] is not None:
                self.visibility = VisibilityIndicator(definition["visibility"])

            if definition["isImportAll"]:
                self.keyword = "import all "
            else:
                self.keyword = "import "

    def dump(self):
        if self.visibility is None:
            return self.keyword
        else:
            return self.visibility.dump() + self.keyword

    def get_definition(self):
        output = {"name": self.__class__.__name__}
        output["visibility"] = self.visibility.get_definition() if self.visibility else None
        output["isImportAll"] = (self.keyword == "import all ")
        return output


class ImportedNamespace:
    # The grammar for this file is currently broken.
    def __init__(self, definition):
        if valid_definition(definition, self.__class__.__name__):
            self.namespaces = QualifiedName(definition["namespace"])
            self.isRecursive = definition.get("isRecursive", False)

    def dump(self):
        suffix = "::*"
        if getattr(self, 'isRecursive', False):
            suffix = "::*::**"
        return self.namespaces.dump() + suffix

    def get_definition(self):
        return {
            "name": self.__class__.__name__,
            "namespace": self.namespaces.get_definition(),
            "isRecursive": getattr(self, 'isRecursive', False)
        }


class QualifiedName:
    def __init__(self, definition):
        self.names = []
        if valid_definition(definition, self.__class__.__name__):
            names = definition.get("names", definition.get("parts", []))
            if isinstance(names, str):
                self.names = [names]
            else:
                for name in names:
                    self.names.append(name)

    def dump(self):
        return "::".join(self.names)

    def get_definition(self):
        output = {"name": self.__class__.__name__}
        output["names"] = self.names
        return output


class VisibilityIndicator:
    def __init__(self, definition):
        if valid_definition(definition, "VisibilityIndicator"):
            if (
                definition["private"] == "private"
                and definition["protected"] == ""
                and definition["public"] == ""
            ):
                self.keyword = "private "
            elif (
                definition["private"] == ""
                and definition["protected"] == "protected"
                and definition["public"] == ""
            ):
                self.keyword = "protected "
            elif (
                definition["private"] == ""
                and definition["protected"] == ""
                and definition["public"] == "public"
            ):
                self.keyword = "public "
            else:
                self.keyword = ""

    def dump(self):
        return self.keyword

    def get_definition(self):
        kw = self.keyword or ""
        return {
            "name": self.__class__.__name__,
            "private": "private" if kw == "private " else "",
            "protected": "protected" if kw == "protected " else "",
            "public": "public" if kw == "public " else ""
        }


class _PrefixedDefinitionBase:
    """Base class for definitions that have: prefix + keyword + Definition body."""
    keyword = "def"

    def __init__(self, definition=None):
        self.prefix = None
        self.definition = None
        if definition is not None:
            if valid_definition(definition, self.__class__.__name__):
                if definition.get("prefix") is not None:
                    self.prefix = OccurrenceDefinitionPrefix(definition["prefix"])
                if definition.get("definition") is not None:
                    self.definition = Definition(definition["definition"])
        else:
            self.definition = Definition()

    def dump(self):
        output = []
        if self.prefix is not None:
            output.append(self.prefix.dump())
        output.append(self.keyword)
        if self.definition is not None:
            output.append(self.definition.dump())
        return " ".join(output)

    def get_definition(self):
        return {
            "name": self.__class__.__name__,
            "prefix": self.prefix.get_definition() if self.prefix else None,
            "definition": self.definition.get_definition() if self.definition else None,
        }


class FlowDefinition(_PrefixedDefinitionBase):
    # flowDefinition : occurrenceDefinitionPrefix FLOW DEF definition
    keyword = "flow def"


class AllocationDefinition(_PrefixedDefinitionBase):
    # allocationDefinition : occurrenceDefinitionPrefix ALLOCATION DEF definition
    keyword = "allocation def"


class RenderingDefinition(_PrefixedDefinitionBase):
    # renderingDefinition : occurrenceDefinitionPrefix RENDERING DEF definition
    keyword = "rendering def"


class IndividualDefinition:
    # individualDefinition : basicDefinitionPrefix? INDIVIDUAL definitionExtensionKeyword* DEF definition emptyMultiplicityMember
    def __init__(self, definition=None):
        self.prefix = None
        self.keyword = "individual def"
        self.definition = None
        if definition is not None:
            if valid_definition(definition, self.__class__.__name__):
                if definition.get("prefix") is not None:
                    self.prefix = MemberPrefix(definition["prefix"])
                if definition.get("definition") is not None:
                    self.definition = Definition(definition["definition"])
        else:
            self.definition = Definition()

    def dump(self):
        output = []
        if self.prefix is not None:
            output.append(self.prefix.dump())
        output.append(self.keyword)
        if self.definition is not None:
            output.append(self.definition.dump())
        return " ".join(output)

    def get_definition(self):
        return {
            "name": self.__class__.__name__,
            "prefix": self.prefix.get_definition() if self.prefix else None,
            "definition": self.definition.get_definition() if self.definition else None,
        }


class MetadataDefinition:
    # metadataDefinition : (ABSTRACT)? definitionExtensionKeyword* METADATA DEF definition
    def __init__(self, definition=None):
        self.is_abstract = False
        self.keyword = "metadata def"
        self.extension_keywords = []
        self.definition = None
        if definition is not None:
            if valid_definition(definition, self.__class__.__name__):
                self.is_abstract = definition.get("isAbstract", False)
                for keyword in definition.get("keyword", []):
                    self.extension_keywords.append(DefinitionExtensionKeyword(keyword))
                if definition.get("definition") is not None:
                    self.definition = Definition(definition["definition"])
        else:
            self.definition = Definition()

    def dump(self):
        output = []
        if self.is_abstract:
            output.append("abstract")
        output.extend([kw.dump() for kw in self.extension_keywords])
        output.append(self.keyword)
        if self.definition is not None:
            output.append(self.definition.dump())
        return " ".join(output)

    def get_definition(self):
        return {
            "name": self.__class__.__name__,
            "isAbstract": self.is_abstract,
            "keyword": [kw.get_definition() for kw in self.extension_keywords],
            "definition": self.definition.get_definition() if self.definition else None,
        }


class LibraryPackage:
    # libraryPackage : (STANDARD)? LIBRARY (prefixMetadataMember)* packageDeclaration packageBody
    def __init__(self, definition=None):
        self.is_standard = False
        self.keyword = "library package"
        self.declaration = None
        self.body = None
        if definition is not None:
            if valid_definition(definition, self.__class__.__name__):
                self.is_standard = definition.get("isStandard", False)
                if definition.get("declaration") is not None:
                    self.declaration = PackageDeclaration(definition["declaration"])
                if definition.get("body") is not None:
                    self.body = PackageBody(definition["body"])
        else:
            self.declaration = PackageDeclaration(None)
            self.body = PackageBody(None)

    def dump(self):
        output = []
        if self.is_standard:
            output.append("standard")
        output.append(self.keyword)
        if self.declaration is not None:
            output.append(self.declaration.dump())
        if self.body is not None:
            output.append(self.body.dump())
        return " ".join(output)

    def get_definition(self):
        return {
            "name": self.__class__.__name__,
            "isStandard": self.is_standard,
            "declaration": self.declaration.get_definition() if self.declaration else None,
            "body": self.body.get_definition() if self.body else None,
        }


# ==========================================================================
# Case, View, Concern definitions (use declaration + body structure)
# ==========================================================================


class _DeclaredDefinitionBase:
    """Base class for definitions with: prefix + keyword + declaration + body."""
    keyword = "def"
    body_class = None  # Must be set in subclass

    def __init__(self, definition=None):
        self.prefix = None
        self.declaration = None
        self.body = None
        if definition is not None:
            if valid_definition(definition, self.__class__.__name__):
                if definition.get("prefix") is not None:
                    self.prefix = OccurrenceDefinitionPrefix(definition["prefix"])
                if definition.get("declaration") is not None:
                    self.declaration = DefinitionDeclaration(definition["declaration"])
                if definition.get("body") is not None:
                    self.body = self.body_class(definition["body"])
        else:
            self.declaration = DefinitionDeclaration()
            self.body = self.body_class(None) if self.body_class else None

    def dump(self):
        output = []
        if self.prefix is not None:
            output.append(self.prefix.dump())
        output.append(self.keyword)
        if self.declaration is not None:
            output.append(self.declaration.dump())
        if self.body is not None:
            output.append(self.body.dump())
        return " ".join(output)

    def get_definition(self):
        return {
            "name": self.__class__.__name__,
            "prefix": self.prefix.get_definition() if self.prefix else None,
            "declaration": self.declaration.get_definition() if self.declaration else None,
            "body": self.body.get_definition() if self.body else None,
        }


class CaseDefinition(_DeclaredDefinitionBase):
    # caseDefinition : occurrenceDefinitionPrefix CASE DEF definitionDeclaration caseBody
    keyword = "case def"
    body_class = CaseBody


class VerificationCaseDefinition(_DeclaredDefinitionBase):
    # verificationCaseDefinition : occurrenceDefinitionPrefix VERIFICATION DEF definitionDeclaration caseBody
    keyword = "verification case def"
    body_class = CaseBody


class ElementFilterMember:
    # Stub for elementFilterMember — not yet fully implemented
    def __init__(self, definition=None):
        self.children = []
        if definition is not None:
            if valid_definition(definition, "ElementFilterMember"):
                pass  # TODO: parse filter expression

    def dump(self):
        return ""

    def get_definition(self):
        return {"name": self.__class__.__name__}


class Expose:
    # Stub for expose — not yet fully implemented
    def __init__(self, definition=None):
        self.children = []
        if definition is not None:
            if valid_definition(definition, "Expose"):
                pass  # TODO: parse expose

    def dump(self):
        return ""

    def get_definition(self):
        return {"name": self.__class__.__name__}


class RenderStateMember:
    # renderStateMember : memberPrefix RENDER STATE name renderStateBody
    def __init__(self, definition=None):
        self.prefix = None
        self.state_name = None
        self.body_items = []
        if definition is not None:
            if valid_definition(definition, "RenderStateMember"):
                if definition.get("prefix") is not None:
                    self.prefix = MemberPrefix(definition["prefix"])
                self.state_name = definition.get("stateName")
                for item in definition.get("body", []):
                    self.body_items.append(item)

    def dump(self):
        output = []
        if self.prefix is not None:
            output.append(self.prefix.dump())
        output.append("render state")
        if self.state_name is not None:
            output.append(self.state_name)
        if len(self.body_items) == 0:
            output.append(";")
            return " ".join(output)
        body_parts = []
        for item in self.body_items:
            name = item.get("name", "")
            if name == "ShapeDirective":
                body_parts.append(f"shape {item.get('shape', '')};")
            elif name == "ColorDirective":
                body_parts.append(f"color {item.get('color', '')};")
            elif name == "ShowDirective":
                body_parts.append(f"show {item.get('target', '')};")
            elif name == "AnnotationDirective":
                body_parts.append(f"annotation {item.get('text', '')};")
        return " ".join(output) + " {\n" + "\n".join(body_parts) + "\n}"

    def get_definition(self):
        return {
            "name": self.__class__.__name__,
            "prefix": self.prefix.get_definition() if self.prefix else None,
            "stateName": self.state_name,
            "body": self.body_items,
        }


class ViewRenderingUsage:
    # viewRenderingUsage
    #     : ownedReferenceSubsetting featureSpecializationPart? usageBody
    #     | ( usageExtensionKeyword* RENDERING | usageExtensionKeyword+) usage
    #     ;
    def __init__(self, definition=None):
        self.reference = None
        self.specialization = None
        self.body = None
        self.has_rendering_keyword = False
        self.usage_name = None
        if definition is not None:
            if valid_definition(definition, "ViewRenderingUsage"):
                if definition.get("reference") is not None:
                    self.reference = QualifiedName(definition["reference"])
                if definition.get("specialization") is not None:
                    self.specialization = FeatureSpecializationPart(definition["specialization"])
                if definition.get("body") is not None:
                    self.body = UsageBody(definition["body"])
                if definition.get("renderingUsage") is not None:
                    self.has_rendering_keyword = True
                    ru = definition["renderingUsage"]
                    if isinstance(ru, dict):
                        decl = ru.get("declaration", {})
                        if isinstance(decl, dict):
                            inner_decl = decl.get("declaration", {})
                            if isinstance(inner_decl, dict):
                                ident = inner_decl.get("identification", {})
                                if isinstance(ident, dict):
                                    self.usage_name = ident.get("declaredName")
                if definition.get("usage") is not None:
                    u = definition["usage"]
                    if isinstance(u, dict):
                        decl = u.get("declaration", {})
                        if isinstance(decl, dict):
                            inner_decl = decl.get("declaration", {})
                            if isinstance(inner_decl, dict):
                                ident = inner_decl.get("identification", {})
                                if isinstance(ident, dict):
                                    self.usage_name = ident.get("declaredName")

    def dump(self):
        output = []
        if self.reference is not None:
            output.append(self.reference.dump())
        if self.specialization is not None:
            output.append(self.specialization.dump())
        if self.body is not None:
            output.append(self.body.dump())
        if self.has_rendering_keyword:
            output.append("rendering")
        if self.usage_name is not None:
            output.append(self.usage_name)
        return " ".join(output)

    def get_definition(self):
        return {
            "name": self.__class__.__name__,
            "reference": self.reference.get_definition() if self.reference else None,
            "specialization": self.specialization.get_definition() if self.specialization else None,
            "body": self.body.get_definition() if self.body else None,
            "renderingUsage": None,
            "usage": None,
        }


class ViewRenderingMember:
    # viewRenderingMember : memberPrefix RENDER viewRenderingUsage
    def __init__(self, definition=None):
        self.prefix = None
        self.usage = None
        if definition is not None:
            if valid_definition(definition, "ViewRenderingMember"):
                if definition.get("prefix") is not None:
                    self.prefix = MemberPrefix(definition["prefix"])
                if definition.get("usage") is not None:
                    self.usage = ViewRenderingUsage(definition["usage"])

    def dump(self):
        output = []
        if self.prefix is not None:
            output.append(self.prefix.dump())
        output.append("render")
        if self.usage is not None:
            output.append(self.usage.dump())
            if self.usage.body is None:
                output.append(";")
        return " ".join(output)

    def get_definition(self):
        return {
            "name": self.__class__.__name__,
            "prefix": self.prefix.get_definition() if self.prefix else None,
            "usage": self.usage.get_definition() if self.usage else None,
        }


class ViewDefinitionBody:
    # viewDefinitionBody : SEMI | LBRACE viewDefinitionBodyItem* RBRACE
    def __init__(self, definition=None):
        self.children = []
        if definition is not None:
            if valid_definition(definition, "ViewDefinitionBody"):
                for item in definition.get("ownedRelatedElement", []):
                    item_name = item.get("name")
                    if item_name == "DefinitionBodyItem":
                        self.children.append(DefinitionBodyItem(item))
                    elif item_name == "ViewRenderingMember":
                        self.children.append(ViewRenderingMember(item))
                    elif item_name == "RenderStateMember":
                        self.children.append(RenderStateMember(item))
                    elif item_name == "ElementFilterMember":
                        self.children.append(ElementFilterMember(item))
                    else:
                        print(f"ViewDefinitionBody: unknown item {item_name}")  # pragma: no cover

    def dump(self):
        if len(self.children) == 0:
            return ";"
        output = []
        for child in self.children:
            output.append(child.dump())
        return " {\n" + "\n".join(output) + "\n}"

    def get_definition(self):
        return {
            "name": self.__class__.__name__,
            "ownedRelatedElement": [child.get_definition() for child in self.children],
        }


class ViewBody:
    # viewBody : SEMI | LBRACE viewBodyItem* RBRACE
    def __init__(self, definition=None):
        self.children = []
        if definition is not None:
            if valid_definition(definition, "ViewBody"):
                for item in definition.get("ownedRelatedElement", []):
                    item_name = item.get("name")
                    if item_name == "DefinitionBodyItem":
                        self.children.append(DefinitionBodyItem(item))
                    elif item_name == "ViewRenderingMember":
                        self.children.append(ViewRenderingMember(item))
                    elif item_name == "RenderStateMember":
                        self.children.append(RenderStateMember(item))
                    elif item_name == "ElementFilterMember":
                        self.children.append(ElementFilterMember(item))
                    elif item_name == "Expose":
                        self.children.append(Expose(item))
                    else:
                        print(f"ViewBody: unknown item {item_name}")  # pragma: no cover

    def dump(self):
        if len(self.children) == 0:
            return ";"
        output = []
        for child in self.children:
            output.append(child.dump())
        return " {\n" + "\n".join(output) + "\n}"

    def get_definition(self):
        return {
            "name": self.__class__.__name__,
            "ownedRelatedElement": [child.get_definition() for child in self.children],
        }


class ViewDefinition(_DeclaredDefinitionBase):
    # viewDefinition : occurrenceDefinitionPrefix VIEW DEF definitionDeclaration viewDefinitionBody
    keyword = "view def"
    body_class = ViewDefinitionBody


class ViewpointDefinition(_DeclaredDefinitionBase):
    # viewpointDefinition : occurrenceDefinitionPrefix VIEWPOINT DEF definitionDeclaration requirementBody
    keyword = "viewpoint def"
    body_class = RequirementBody


class ConcernDefinition(_DeclaredDefinitionBase):
    # concernDefinition : occurrenceDefinitionPrefix CONCERN DEF definitionDeclaration requirementBody
    keyword = "concern def"
    body_class = RequirementBody


# ==========================================================================
# Type System Definition classes
# Simplified implementations of core SysML v2 type hierarchy elements.
# They use Definition as the underlying body structure.
# ==========================================================================


class _TypeDefinitionBase:
    """Base class for simple type definitions that use Definition as body."""
    keyword = "type"  # Override in subclass

    def __init__(self, definition=None):
        self.definition = None
        if definition is not None:
            if valid_definition(definition, self.__class__.__name__):
                if definition.get("definition") is not None:
                    self.definition = Definition(definition["definition"])
        else:
            self.definition = Definition()

    def dump(self):
        output = [self.keyword]
        if self.definition is not None:
            output.append(self.definition.dump())
        return " ".join(output)

    def get_definition(self):
        return {
            "name": self.__class__.__name__,
            "definition": self.definition.get_definition() if self.definition else None,
        }


class Type(_TypeDefinitionBase):
    keyword = "type"


class Classifier(_TypeDefinitionBase):
    keyword = "classifier"


class DataType(_TypeDefinitionBase):
    keyword = "datatype"


class Class(_TypeDefinitionBase):
    keyword = "class"


class Structure(_TypeDefinitionBase):
    keyword = "struct"


class Association(_TypeDefinitionBase):
    keyword = "assoc"


class AssociationStructure(_TypeDefinitionBase):
    keyword = "assoc struct"


class Metaclass(_TypeDefinitionBase):
    keyword = "metaclass"


class Behavior(_TypeDefinitionBase):
    keyword = "behavior"


class Function(_TypeDefinitionBase):
    keyword = "function"


class Predicate(_TypeDefinitionBase):
    keyword = "predicate"


class Interaction(_TypeDefinitionBase):
    keyword = "interaction"


class Invariant:
    # invariant : featurePrefix INV (TRUE | FALSE)? featureDeclaration valuePart? functionBody
    def __init__(self, definition=None):
        self.keyword = "inv"
        self.truth = None  # 'true' or 'false' if present
        self.definition = None
        if definition is not None:
            if valid_definition(definition, self.__class__.__name__):
                self.truth = definition.get("truth")
                if definition.get("definition") is not None:
                    self.definition = Definition(definition["definition"])
        else:
            self.definition = Definition()

    def dump(self):
        output = [self.keyword]
        if self.truth is not None:
            output.append(self.truth)
        if self.definition is not None:
            output.append(self.definition.dump())
        return " ".join(output)

    def get_definition(self):
        return {
            "name": self.__class__.__name__,
            "truth": self.truth,
            "definition": self.definition.get_definition() if self.definition else None,
        }


class OccurrenceDefinition:
    # occurrenceDefinition : occurrenceDefinitionPrefix OCCURRENCE DEF definition
    def __init__(self, definition=None):
        self.prefix = None
        self.keyword = "occurrence def"
        self.definition = None
        if definition is not None:
            if valid_definition(definition, self.__class__.__name__):
                if definition.get("prefix") is not None:
                    self.prefix = OccurrenceDefinitionPrefix(definition["prefix"])
                if definition.get("definition") is not None:
                    self.definition = Definition(definition["definition"])
        else:
            self.definition = Definition()

    def dump(self):
        output = []
        if self.prefix is not None:
            output.append(self.prefix.dump())
        output.append(self.keyword)
        if self.definition is not None:
            output.append(self.definition.dump())
        return " ".join(output)

    def get_definition(self):
        return {
            "name": self.__class__.__name__,
            "prefix": self.prefix.get_definition() if self.prefix else None,
            "definition": self.definition.get_definition() if self.definition else None,
        }


# ==========================================================================
# Relationship Definition classes
# ==========================================================================


class _RelationshipDefinitionBase:
    """Base class for binary relationship definitions with source and target."""
    keyword = "relationship"
    source_key = "source"
    target_key = "target"
    connector_keyword = ""  # e.g., "specializes", "subsets", "redefines"

    def __init__(self, definition=None):
        self.identification = None
        self.source = None
        self.target = None
        self.body = None
        if definition is not None:
            if valid_definition(definition, self.__class__.__name__):
                if definition.get("identification") is not None:
                    self.identification = Identification(definition["identification"])
                if definition.get(self.source_key) is not None:
                    self.source = QualifiedName(definition[self.source_key])
                if definition.get(self.target_key) is not None:
                    self.target = QualifiedName(definition[self.target_key])
                if definition.get("body") is not None:
                    self.body = RelationshipBody(definition["body"])

    def dump(self):
        output = [self.keyword]
        if self.identification is not None:
            output.append(self.identification.dump())
        if self.source is not None:
            output.append(self.source.dump())
        if self.connector_keyword:
            output.append(self.connector_keyword)
        if self.target is not None:
            output.append(self.target.dump())
        if self.body is not None:
            output.append(self.body.dump())
        return " ".join(output)

    def get_definition(self):
        return {
            "name": self.__class__.__name__,
            "identification": self.identification.get_definition() if self.identification else None,
            self.source_key: self.source.get_definition() if self.source else None,
            self.target_key: self.target.get_definition() if self.target else None,
            "body": self.body.get_definition() if self.body else None,
        }


class Specialization(_RelationshipDefinitionBase):
    keyword = "specialization"
    source_key = "subtype"
    target_key = "supertype"
    connector_keyword = "specializes"


class Conjugation(_RelationshipDefinitionBase):
    keyword = "conjugation"
    source_key = "conjugate"
    target_key = "conjugatedType"
    connector_keyword = "conjugates"


class Subsetting(_RelationshipDefinitionBase):
    keyword = "subset"
    source_key = "subset"
    target_key = "superset"
    connector_keyword = "subsets"


class Redefinition(_RelationshipDefinitionBase):
    keyword = "redefinition"
    source_key = "redefining"
    target_key = "redefined"
    connector_keyword = "redefines"


class FeatureInverting(_RelationshipDefinitionBase):
    keyword = "inverting"
    source_key = "inverting"
    target_key = "inverted"
    connector_keyword = "inverse of"


class TypeFeaturing(_RelationshipDefinitionBase):
    keyword = "featuring"
    source_key = "feature"
    target_key = "featuringType"
    connector_keyword = "of"


class Dependency:
    # dependency : (DEPENDENCY identification?)? qualifiedName (COMMA qualifiedName)* TO qualifiedName (COMMA qualifiedName)* relationshipBody
    def __init__(self, definition=None):
        self.keyword = "dependency"
        self.identification = None
        self.clients = []
        self.suppliers = []
        self.body = None
        if definition is not None:
            if valid_definition(definition, self.__class__.__name__):
                if definition.get("identification") is not None:
                    self.identification = Identification(definition["identification"])
                for client in definition.get("clients", []):
                    self.clients.append(QualifiedName(client))
                for supplier in definition.get("suppliers", []):
                    self.suppliers.append(QualifiedName(supplier))
                if definition.get("body") is not None:
                    self.body = RelationshipBody(definition["body"])

    def dump(self):
        output = [self.keyword]
        if self.identification is not None:
            output.append(self.identification.dump())
            # Issue #4: the ANTLR grammar ambiguity means an unnamed-form
            # `dependency name a to X;` is unparseable — `name` is taken as
            # the identification and `a` then has nowhere to go. To round-trip
            # safely we always emit `from` between the identification and the
            # client list.
            output.append("from")
        output.append(", ".join([c.dump() for c in self.clients]))
        output.append("to")
        output.append(", ".join([s.dump() for s in self.suppliers]))
        if self.body is not None:
            output.append(self.body.dump())
        return " ".join(output)

    def get_definition(self):
        return {
            "name": self.__class__.__name__,
            "identification": self.identification.get_definition() if self.identification else None,
            "clients": [c.get_definition() for c in self.clients],
            "suppliers": [s.get_definition() for s in self.suppliers],
            "body": self.body.get_definition() if self.body else None,
        }


# ==========================================================================
# Usage classes for Allocation, Metadata, Rendering, Individual, Flow
# (using simple prefix + keyword + usage pattern)
# ==========================================================================


class _PrefixedUsageBase:
    """Base class for usages with: prefix + keyword + Usage."""
    keyword = "usage"
    body_class = None  # Set in subclass, defaults to UsageBody

    def __init__(self, definition=None):
        self.prefix = None
        self.declaration = None
        self.body = None
        body_cls = self.body_class if self.body_class else UsageBody
        if definition is not None:
            if valid_definition(definition, self.__class__.__name__):
                if definition.get("prefix") is not None:
                    self.prefix = OccurrenceUsagePrefix(definition["prefix"])
                if definition.get("declaration") is not None:
                    self.declaration = UsageDeclaration(definition["declaration"])
                if definition.get("body") is not None:
                    self.body = body_cls(definition["body"])
        else:
            self.declaration = UsageDeclaration()
            self.body = body_cls(None)

    def dump(self):
        output = []
        if self.prefix is not None:
            output.append(self.prefix.dump())
        output.append(self.keyword)
        if self.declaration is not None:
            output.append(self.declaration.dump())
        if self.body is not None:
            output.append(self.body.dump())
        return " ".join(output)

    def get_definition(self):
        return {
            "name": self.__class__.__name__,
            "prefix": self.prefix.get_definition() if self.prefix else None,
            "declaration": self.declaration.get_definition() if self.declaration else None,
            "body": self.body.get_definition() if self.body else None,
        }


class AllocationUsage(_PrefixedUsageBase):
    # allocationUsage : occurrenceUsagePrefix ALLOCATION usageDeclaration? usageBody
    # allocationUsageDeclaration : ALLOCATION usageDeclaration? (ALLOCATE connectorPart)?
    #                          | ALLOCATE connectorPart
    keyword = "allocation"

    def __init__(self, definition=None):
        super().__init__(definition)
        # Issue #5 / PR #6: stores the connectorPart (the `allocate X to Y`
        # endpoints) on the same `part` key ConnectionUsage already uses, so
        # downstream consumers share one shape across connector-bearing
        # usages. Initialized from `definition["part"]` for round-trip
        # compatibility with the visitor; legacy `definition["connectorPart"]`
        # is also accepted as a fallback so callers that built dicts using
        # the v0.47.0 contract keep working until they migrate.
        self.connectorPart = None
        if definition is not None and valid_definition(definition, self.__class__.__name__):
            raw = definition.get("part", definition.get("connectorPart"))
            if raw is not None:
                self.connectorPart = ConnectorPart(raw)

    def dump(self):
        parts = []
        if self.prefix is not None:
            parts.append(self.prefix.dump())
        # Render as `allocation [name] [allocate X to Y]`
        parts.append(self.keyword)
        if self.declaration is not None:
            decl_dump = self.declaration.dump()
            if decl_dump:
                parts.append(decl_dump)
        if self.connectorPart is not None:
            parts.append("allocate")
            parts.append(self.connectorPart.dump())
        if self.body is not None:
            parts.append(self.body.dump())
        return " ".join(parts)

    def get_definition(self):
        # Emit under the `part` key (matching ConnectionUsage convention
        # from PR #6). The legacy `connectorPart` alias is no longer emitted
        # but ``__init__`` still accepts it for back-compat reads.
        output = super().get_definition()
        output["part"] = self.connectorPart.get_definition() if self.connectorPart else None
        return output


class RenderingUsage(_PrefixedUsageBase):
    # renderingUsage : occurrenceUsagePrefix RENDERING usage
    keyword = "rendering"


class MetadataUsage(_PrefixedUsageBase):
    # metadataUsage : usageExtensionKeyword* METADATA metadataUsageDeclaration metadataBody
    keyword = "metadata"


class IndividualUsageSimple(_PrefixedUsageBase):
    """Simpler IndividualUsage for the user-facing API."""
    keyword = "individual"


class PortionUsage:
    """Portion usage (timeslice or snapshot) inside a body."""

    def __init__(self, definition=None):
        if definition is not None:
            if valid_definition(definition, "PortionUsage"):
                if definition.get("prefix") is not None:
                    prefix_name = definition["prefix"].get("name", "OccurrenceUsagePrefix")
                    self.prefix = globals()[prefix_name](definition["prefix"])
                else:
                    self.prefix = None
                self.usage = Usage(definition.get("usage"))
        else:
            self.prefix = None
            self.usage = Usage()

    def dump(self):
        output = []
        if self.prefix is not None:
            output.append(self.prefix.dump())
        if self.usage is not None:
            output.append(self.usage.dump())
        return " ".join(output)

    def get_definition(self):
        pre = None
        if self.prefix is not None:
            pre = self.prefix.get_definition()
        u = None
        if self.usage is not None:
            u = self.usage.get_definition()
        return {"name": self.__class__.__name__, "prefix": pre, "usage": u}


class FlowUsageSimple(_PrefixedUsageBase):
    """Alternative FlowUsage (flow without connection - simple usage)."""
    keyword = "flow"


class ViewUsage(_PrefixedUsageBase):
    # viewUsage : occurrenceUsagePrefix VIEW usageDeclaration? valuePart? viewBody
    keyword = "view"
    body_class = ViewBody


class ViewpointUsage(_PrefixedUsageBase):
    # viewpointUsage : occurrenceUsagePrefix VIEWPOINT constraintUsageDeclaration requirementBody
    keyword = "viewpoint"


class ConcernUsage(_PrefixedUsageBase):
    # concernUsage : occurrenceUsagePrefix CONCERN constraintUsageDeclaration requirementBody
    keyword = "concern"
