# Generated from src/sysml2py/grammar/antlr4/SysMLv2Parser.g4 by ANTLR 4.13.2
from antlr4 import *
if "." in __name__:
    from .SysMLv2Parser import SysMLv2Parser
else:
    from SysMLv2Parser import SysMLv2Parser

# This class defines a complete generic visitor for a parse tree produced by SysMLv2Parser.

class SysMLv2ParserVisitor(ParseTreeVisitor):

    # Visit a parse tree produced by SysMLv2Parser#ownedExpression.
    def visitOwnedExpression(self, ctx:SysMLv2Parser.OwnedExpressionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#typeReference.
    def visitTypeReference(self, ctx:SysMLv2Parser.TypeReferenceContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#sequenceExpressionList.
    def visitSequenceExpressionList(self, ctx:SysMLv2Parser.SequenceExpressionListContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#baseExpression.
    def visitBaseExpression(self, ctx:SysMLv2Parser.BaseExpressionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#nullExpression.
    def visitNullExpression(self, ctx:SysMLv2Parser.NullExpressionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#featureReferenceExpression.
    def visitFeatureReferenceExpression(self, ctx:SysMLv2Parser.FeatureReferenceExpressionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#metadataAccessExpression.
    def visitMetadataAccessExpression(self, ctx:SysMLv2Parser.MetadataAccessExpressionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#invocationExpression.
    def visitInvocationExpression(self, ctx:SysMLv2Parser.InvocationExpressionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#constructorExpression.
    def visitConstructorExpression(self, ctx:SysMLv2Parser.ConstructorExpressionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#bodyExpression.
    def visitBodyExpression(self, ctx:SysMLv2Parser.BodyExpressionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#argumentList.
    def visitArgumentList(self, ctx:SysMLv2Parser.ArgumentListContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#positionalArgumentList.
    def visitPositionalArgumentList(self, ctx:SysMLv2Parser.PositionalArgumentListContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#namedArgumentList.
    def visitNamedArgumentList(self, ctx:SysMLv2Parser.NamedArgumentListContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#namedArgument.
    def visitNamedArgument(self, ctx:SysMLv2Parser.NamedArgumentContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#literalExpression.
    def visitLiteralExpression(self, ctx:SysMLv2Parser.LiteralExpressionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#literalBoolean.
    def visitLiteralBoolean(self, ctx:SysMLv2Parser.LiteralBooleanContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#literalString.
    def visitLiteralString(self, ctx:SysMLv2Parser.LiteralStringContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#literalInteger.
    def visitLiteralInteger(self, ctx:SysMLv2Parser.LiteralIntegerContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#literalReal.
    def visitLiteralReal(self, ctx:SysMLv2Parser.LiteralRealContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#literalInfinity.
    def visitLiteralInfinity(self, ctx:SysMLv2Parser.LiteralInfinityContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#argumentMember.
    def visitArgumentMember(self, ctx:SysMLv2Parser.ArgumentMemberContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#argumentExpressionMember.
    def visitArgumentExpressionMember(self, ctx:SysMLv2Parser.ArgumentExpressionMemberContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#name.
    def visitName(self, ctx:SysMLv2Parser.NameContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#unreservedKeyword.
    def visitUnreservedKeyword(self, ctx:SysMLv2Parser.UnreservedKeywordContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#identification.
    def visitIdentification(self, ctx:SysMLv2Parser.IdentificationContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#relationshipBody.
    def visitRelationshipBody(self, ctx:SysMLv2Parser.RelationshipBodyContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#relationshipOwnedElement.
    def visitRelationshipOwnedElement(self, ctx:SysMLv2Parser.RelationshipOwnedElementContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#ownedRelatedElement.
    def visitOwnedRelatedElement(self, ctx:SysMLv2Parser.OwnedRelatedElementContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#dependency.
    def visitDependency(self, ctx:SysMLv2Parser.DependencyContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#annotation.
    def visitAnnotation(self, ctx:SysMLv2Parser.AnnotationContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#ownedAnnotation.
    def visitOwnedAnnotation(self, ctx:SysMLv2Parser.OwnedAnnotationContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#annotatingElement.
    def visitAnnotatingElement(self, ctx:SysMLv2Parser.AnnotatingElementContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#comment.
    def visitComment(self, ctx:SysMLv2Parser.CommentContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#documentation.
    def visitDocumentation(self, ctx:SysMLv2Parser.DocumentationContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#textualRepresentation.
    def visitTextualRepresentation(self, ctx:SysMLv2Parser.TextualRepresentationContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#rootNamespace.
    def visitRootNamespace(self, ctx:SysMLv2Parser.RootNamespaceContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#namespace.
    def visitNamespace(self, ctx:SysMLv2Parser.NamespaceContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#namespaceDeclaration.
    def visitNamespaceDeclaration(self, ctx:SysMLv2Parser.NamespaceDeclarationContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#namespaceBody.
    def visitNamespaceBody(self, ctx:SysMLv2Parser.NamespaceBodyContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#namespaceBodyElement.
    def visitNamespaceBodyElement(self, ctx:SysMLv2Parser.NamespaceBodyElementContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#memberPrefix.
    def visitMemberPrefix(self, ctx:SysMLv2Parser.MemberPrefixContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#visibilityIndicator.
    def visitVisibilityIndicator(self, ctx:SysMLv2Parser.VisibilityIndicatorContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#namespaceMember.
    def visitNamespaceMember(self, ctx:SysMLv2Parser.NamespaceMemberContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#nonFeatureMember.
    def visitNonFeatureMember(self, ctx:SysMLv2Parser.NonFeatureMemberContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#namespaceFeatureMember.
    def visitNamespaceFeatureMember(self, ctx:SysMLv2Parser.NamespaceFeatureMemberContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#aliasMember.
    def visitAliasMember(self, ctx:SysMLv2Parser.AliasMemberContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#qualifiedName.
    def visitQualifiedName(self, ctx:SysMLv2Parser.QualifiedNameContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#importRule.
    def visitImportRule(self, ctx:SysMLv2Parser.ImportRuleContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#importDeclaration.
    def visitImportDeclaration(self, ctx:SysMLv2Parser.ImportDeclarationContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#membershipImport.
    def visitMembershipImport(self, ctx:SysMLv2Parser.MembershipImportContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#namespaceImport.
    def visitNamespaceImport(self, ctx:SysMLv2Parser.NamespaceImportContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#filterPackage.
    def visitFilterPackage(self, ctx:SysMLv2Parser.FilterPackageContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#filterPackageMember.
    def visitFilterPackageMember(self, ctx:SysMLv2Parser.FilterPackageMemberContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#memberElement.
    def visitMemberElement(self, ctx:SysMLv2Parser.MemberElementContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#nonFeatureElement.
    def visitNonFeatureElement(self, ctx:SysMLv2Parser.NonFeatureElementContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#featureElement.
    def visitFeatureElement(self, ctx:SysMLv2Parser.FeatureElementContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#type.
    def visitType(self, ctx:SysMLv2Parser.TypeContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#typePrefix.
    def visitTypePrefix(self, ctx:SysMLv2Parser.TypePrefixContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#typeDeclaration.
    def visitTypeDeclaration(self, ctx:SysMLv2Parser.TypeDeclarationContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#specializationPart.
    def visitSpecializationPart(self, ctx:SysMLv2Parser.SpecializationPartContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#conjugationPart.
    def visitConjugationPart(self, ctx:SysMLv2Parser.ConjugationPartContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#typeRelationshipPart.
    def visitTypeRelationshipPart(self, ctx:SysMLv2Parser.TypeRelationshipPartContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#disjoiningPart.
    def visitDisjoiningPart(self, ctx:SysMLv2Parser.DisjoiningPartContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#unioningPart.
    def visitUnioningPart(self, ctx:SysMLv2Parser.UnioningPartContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#intersectingPart.
    def visitIntersectingPart(self, ctx:SysMLv2Parser.IntersectingPartContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#differencingPart.
    def visitDifferencingPart(self, ctx:SysMLv2Parser.DifferencingPartContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#typeBody.
    def visitTypeBody(self, ctx:SysMLv2Parser.TypeBodyContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#typeBodyElement.
    def visitTypeBodyElement(self, ctx:SysMLv2Parser.TypeBodyElementContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#specialization.
    def visitSpecialization(self, ctx:SysMLv2Parser.SpecializationContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#ownedSpecialization.
    def visitOwnedSpecialization(self, ctx:SysMLv2Parser.OwnedSpecializationContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#specificType.
    def visitSpecificType(self, ctx:SysMLv2Parser.SpecificTypeContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#generalType.
    def visitGeneralType(self, ctx:SysMLv2Parser.GeneralTypeContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#conjugation.
    def visitConjugation(self, ctx:SysMLv2Parser.ConjugationContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#ownedConjugation.
    def visitOwnedConjugation(self, ctx:SysMLv2Parser.OwnedConjugationContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#disjoining.
    def visitDisjoining(self, ctx:SysMLv2Parser.DisjoiningContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#ownedDisjoining.
    def visitOwnedDisjoining(self, ctx:SysMLv2Parser.OwnedDisjoiningContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#unioning.
    def visitUnioning(self, ctx:SysMLv2Parser.UnioningContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#intersecting.
    def visitIntersecting(self, ctx:SysMLv2Parser.IntersectingContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#differencing.
    def visitDifferencing(self, ctx:SysMLv2Parser.DifferencingContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#featureMember.
    def visitFeatureMember(self, ctx:SysMLv2Parser.FeatureMemberContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#typeFeatureMember.
    def visitTypeFeatureMember(self, ctx:SysMLv2Parser.TypeFeatureMemberContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#ownedFeatureMember.
    def visitOwnedFeatureMember(self, ctx:SysMLv2Parser.OwnedFeatureMemberContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#classifier.
    def visitClassifier(self, ctx:SysMLv2Parser.ClassifierContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#classifierDeclaration.
    def visitClassifierDeclaration(self, ctx:SysMLv2Parser.ClassifierDeclarationContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#superclassingPart.
    def visitSuperclassingPart(self, ctx:SysMLv2Parser.SuperclassingPartContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#subclassification.
    def visitSubclassification(self, ctx:SysMLv2Parser.SubclassificationContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#ownedSubclassification.
    def visitOwnedSubclassification(self, ctx:SysMLv2Parser.OwnedSubclassificationContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#feature.
    def visitFeature(self, ctx:SysMLv2Parser.FeatureContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#endFeaturePrefix.
    def visitEndFeaturePrefix(self, ctx:SysMLv2Parser.EndFeaturePrefixContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#basicFeaturePrefix.
    def visitBasicFeaturePrefix(self, ctx:SysMLv2Parser.BasicFeaturePrefixContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#featurePrefix.
    def visitFeaturePrefix(self, ctx:SysMLv2Parser.FeaturePrefixContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#ownedCrossFeatureMember.
    def visitOwnedCrossFeatureMember(self, ctx:SysMLv2Parser.OwnedCrossFeatureMemberContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#ownedCrossFeature.
    def visitOwnedCrossFeature(self, ctx:SysMLv2Parser.OwnedCrossFeatureContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#featureDirection.
    def visitFeatureDirection(self, ctx:SysMLv2Parser.FeatureDirectionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#featureDeclaration.
    def visitFeatureDeclaration(self, ctx:SysMLv2Parser.FeatureDeclarationContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#featureIdentification.
    def visitFeatureIdentification(self, ctx:SysMLv2Parser.FeatureIdentificationContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#featureRelationshipPart.
    def visitFeatureRelationshipPart(self, ctx:SysMLv2Parser.FeatureRelationshipPartContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#chainingPart.
    def visitChainingPart(self, ctx:SysMLv2Parser.ChainingPartContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#invertingPart.
    def visitInvertingPart(self, ctx:SysMLv2Parser.InvertingPartContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#typeFeaturingPart.
    def visitTypeFeaturingPart(self, ctx:SysMLv2Parser.TypeFeaturingPartContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#featureSpecializationPart.
    def visitFeatureSpecializationPart(self, ctx:SysMLv2Parser.FeatureSpecializationPartContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#multiplicityPart.
    def visitMultiplicityPart(self, ctx:SysMLv2Parser.MultiplicityPartContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#featureSpecialization.
    def visitFeatureSpecialization(self, ctx:SysMLv2Parser.FeatureSpecializationContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#typings.
    def visitTypings(self, ctx:SysMLv2Parser.TypingsContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#typedBy.
    def visitTypedBy(self, ctx:SysMLv2Parser.TypedByContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#subsettings.
    def visitSubsettings(self, ctx:SysMLv2Parser.SubsettingsContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#subsets.
    def visitSubsets(self, ctx:SysMLv2Parser.SubsetsContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#references.
    def visitReferences(self, ctx:SysMLv2Parser.ReferencesContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#crosses.
    def visitCrosses(self, ctx:SysMLv2Parser.CrossesContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#redefinitions.
    def visitRedefinitions(self, ctx:SysMLv2Parser.RedefinitionsContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#redefines.
    def visitRedefines(self, ctx:SysMLv2Parser.RedefinesContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#featureTyping.
    def visitFeatureTyping(self, ctx:SysMLv2Parser.FeatureTypingContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#ownedFeatureTyping.
    def visitOwnedFeatureTyping(self, ctx:SysMLv2Parser.OwnedFeatureTypingContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#subsetting.
    def visitSubsetting(self, ctx:SysMLv2Parser.SubsettingContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#ownedSubsetting.
    def visitOwnedSubsetting(self, ctx:SysMLv2Parser.OwnedSubsettingContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#ownedReferenceSubsetting.
    def visitOwnedReferenceSubsetting(self, ctx:SysMLv2Parser.OwnedReferenceSubsettingContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#ownedCrossSubsetting.
    def visitOwnedCrossSubsetting(self, ctx:SysMLv2Parser.OwnedCrossSubsettingContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#redefinition.
    def visitRedefinition(self, ctx:SysMLv2Parser.RedefinitionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#ownedRedefinition.
    def visitOwnedRedefinition(self, ctx:SysMLv2Parser.OwnedRedefinitionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#ownedFeatureChain.
    def visitOwnedFeatureChain(self, ctx:SysMLv2Parser.OwnedFeatureChainContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#featureChain.
    def visitFeatureChain(self, ctx:SysMLv2Parser.FeatureChainContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#ownedFeatureChaining.
    def visitOwnedFeatureChaining(self, ctx:SysMLv2Parser.OwnedFeatureChainingContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#featureInverting.
    def visitFeatureInverting(self, ctx:SysMLv2Parser.FeatureInvertingContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#ownedFeatureInverting.
    def visitOwnedFeatureInverting(self, ctx:SysMLv2Parser.OwnedFeatureInvertingContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#typeFeaturing.
    def visitTypeFeaturing(self, ctx:SysMLv2Parser.TypeFeaturingContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#ownedTypeFeaturing.
    def visitOwnedTypeFeaturing(self, ctx:SysMLv2Parser.OwnedTypeFeaturingContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#dataType.
    def visitDataType(self, ctx:SysMLv2Parser.DataTypeContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#class.
    def visitClass(self, ctx:SysMLv2Parser.ClassContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#structure.
    def visitStructure(self, ctx:SysMLv2Parser.StructureContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#association.
    def visitAssociation(self, ctx:SysMLv2Parser.AssociationContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#associationStructure.
    def visitAssociationStructure(self, ctx:SysMLv2Parser.AssociationStructureContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#connector.
    def visitConnector(self, ctx:SysMLv2Parser.ConnectorContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#connectorDeclaration.
    def visitConnectorDeclaration(self, ctx:SysMLv2Parser.ConnectorDeclarationContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#binaryConnectorDeclaration.
    def visitBinaryConnectorDeclaration(self, ctx:SysMLv2Parser.BinaryConnectorDeclarationContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#naryConnectorDeclaration.
    def visitNaryConnectorDeclaration(self, ctx:SysMLv2Parser.NaryConnectorDeclarationContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#connectorEndMember.
    def visitConnectorEndMember(self, ctx:SysMLv2Parser.ConnectorEndMemberContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#connectorEnd.
    def visitConnectorEnd(self, ctx:SysMLv2Parser.ConnectorEndContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#ownedCrossMultiplicityMember.
    def visitOwnedCrossMultiplicityMember(self, ctx:SysMLv2Parser.OwnedCrossMultiplicityMemberContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#ownedCrossMultiplicity.
    def visitOwnedCrossMultiplicity(self, ctx:SysMLv2Parser.OwnedCrossMultiplicityContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#bindingConnector.
    def visitBindingConnector(self, ctx:SysMLv2Parser.BindingConnectorContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#bindingConnectorDeclaration.
    def visitBindingConnectorDeclaration(self, ctx:SysMLv2Parser.BindingConnectorDeclarationContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#succession.
    def visitSuccession(self, ctx:SysMLv2Parser.SuccessionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#successionDeclaration.
    def visitSuccessionDeclaration(self, ctx:SysMLv2Parser.SuccessionDeclarationContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#behavior.
    def visitBehavior(self, ctx:SysMLv2Parser.BehaviorContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#step.
    def visitStep(self, ctx:SysMLv2Parser.StepContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#function.
    def visitFunction(self, ctx:SysMLv2Parser.FunctionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#functionBody.
    def visitFunctionBody(self, ctx:SysMLv2Parser.FunctionBodyContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#functionBodyPart.
    def visitFunctionBodyPart(self, ctx:SysMLv2Parser.FunctionBodyPartContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#returnFeatureMember.
    def visitReturnFeatureMember(self, ctx:SysMLv2Parser.ReturnFeatureMemberContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#resultExpressionMember.
    def visitResultExpressionMember(self, ctx:SysMLv2Parser.ResultExpressionMemberContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#expression.
    def visitExpression(self, ctx:SysMLv2Parser.ExpressionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#predicate.
    def visitPredicate(self, ctx:SysMLv2Parser.PredicateContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#booleanExpression.
    def visitBooleanExpression(self, ctx:SysMLv2Parser.BooleanExpressionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#invariant.
    def visitInvariant(self, ctx:SysMLv2Parser.InvariantContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#ownedExpressionMember.
    def visitOwnedExpressionMember(self, ctx:SysMLv2Parser.OwnedExpressionMemberContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#metadataReference.
    def visitMetadataReference(self, ctx:SysMLv2Parser.MetadataReferenceContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#typeReferenceMember.
    def visitTypeReferenceMember(self, ctx:SysMLv2Parser.TypeReferenceMemberContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#typeResultMember.
    def visitTypeResultMember(self, ctx:SysMLv2Parser.TypeResultMemberContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#referenceTyping.
    def visitReferenceTyping(self, ctx:SysMLv2Parser.ReferenceTypingContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#emptyResultMember.
    def visitEmptyResultMember(self, ctx:SysMLv2Parser.EmptyResultMemberContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#sequenceOperatorExpression.
    def visitSequenceOperatorExpression(self, ctx:SysMLv2Parser.SequenceOperatorExpressionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#sequenceExpressionListMember.
    def visitSequenceExpressionListMember(self, ctx:SysMLv2Parser.SequenceExpressionListMemberContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#bodyArgumentMember.
    def visitBodyArgumentMember(self, ctx:SysMLv2Parser.BodyArgumentMemberContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#bodyArgument.
    def visitBodyArgument(self, ctx:SysMLv2Parser.BodyArgumentContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#bodyArgumentValue.
    def visitBodyArgumentValue(self, ctx:SysMLv2Parser.BodyArgumentValueContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#functionReferenceArgumentMember.
    def visitFunctionReferenceArgumentMember(self, ctx:SysMLv2Parser.FunctionReferenceArgumentMemberContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#functionReferenceArgument.
    def visitFunctionReferenceArgument(self, ctx:SysMLv2Parser.FunctionReferenceArgumentContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#functionReferenceArgumentValue.
    def visitFunctionReferenceArgumentValue(self, ctx:SysMLv2Parser.FunctionReferenceArgumentValueContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#functionReferenceExpression.
    def visitFunctionReferenceExpression(self, ctx:SysMLv2Parser.FunctionReferenceExpressionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#functionReferenceMember.
    def visitFunctionReferenceMember(self, ctx:SysMLv2Parser.FunctionReferenceMemberContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#functionReference.
    def visitFunctionReference(self, ctx:SysMLv2Parser.FunctionReferenceContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#featureChainMember.
    def visitFeatureChainMember(self, ctx:SysMLv2Parser.FeatureChainMemberContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#ownedFeatureChainMember.
    def visitOwnedFeatureChainMember(self, ctx:SysMLv2Parser.OwnedFeatureChainMemberContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#featureReferenceMember.
    def visitFeatureReferenceMember(self, ctx:SysMLv2Parser.FeatureReferenceMemberContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#featureReference.
    def visitFeatureReference(self, ctx:SysMLv2Parser.FeatureReferenceContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#elementReferenceMember.
    def visitElementReferenceMember(self, ctx:SysMLv2Parser.ElementReferenceMemberContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#constructorResultMember.
    def visitConstructorResultMember(self, ctx:SysMLv2Parser.ConstructorResultMemberContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#constructorResult.
    def visitConstructorResult(self, ctx:SysMLv2Parser.ConstructorResultContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#instantiatedTypeMember.
    def visitInstantiatedTypeMember(self, ctx:SysMLv2Parser.InstantiatedTypeMemberContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#instantiatedTypeReference.
    def visitInstantiatedTypeReference(self, ctx:SysMLv2Parser.InstantiatedTypeReferenceContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#namedArgumentMember.
    def visitNamedArgumentMember(self, ctx:SysMLv2Parser.NamedArgumentMemberContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#parameterRedefinition.
    def visitParameterRedefinition(self, ctx:SysMLv2Parser.ParameterRedefinitionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#expressionBodyMember.
    def visitExpressionBodyMember(self, ctx:SysMLv2Parser.ExpressionBodyMemberContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#expressionBody.
    def visitExpressionBody(self, ctx:SysMLv2Parser.ExpressionBodyContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#booleanValue.
    def visitBooleanValue(self, ctx:SysMLv2Parser.BooleanValueContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#realValue.
    def visitRealValue(self, ctx:SysMLv2Parser.RealValueContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#interaction.
    def visitInteraction(self, ctx:SysMLv2Parser.InteractionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#flow.
    def visitFlow(self, ctx:SysMLv2Parser.FlowContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#successionFlow.
    def visitSuccessionFlow(self, ctx:SysMLv2Parser.SuccessionFlowContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#flowDeclaration.
    def visitFlowDeclaration(self, ctx:SysMLv2Parser.FlowDeclarationContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#payloadFeatureMember.
    def visitPayloadFeatureMember(self, ctx:SysMLv2Parser.PayloadFeatureMemberContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#payloadFeature.
    def visitPayloadFeature(self, ctx:SysMLv2Parser.PayloadFeatureContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#payloadFeatureSpecializationPart.
    def visitPayloadFeatureSpecializationPart(self, ctx:SysMLv2Parser.PayloadFeatureSpecializationPartContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#flowEndMember.
    def visitFlowEndMember(self, ctx:SysMLv2Parser.FlowEndMemberContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#flowEnd.
    def visitFlowEnd(self, ctx:SysMLv2Parser.FlowEndContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#flowFeatureMember.
    def visitFlowFeatureMember(self, ctx:SysMLv2Parser.FlowFeatureMemberContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#flowFeature.
    def visitFlowFeature(self, ctx:SysMLv2Parser.FlowFeatureContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#flowFeatureRedefinition.
    def visitFlowFeatureRedefinition(self, ctx:SysMLv2Parser.FlowFeatureRedefinitionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#valuePart.
    def visitValuePart(self, ctx:SysMLv2Parser.ValuePartContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#featureValue.
    def visitFeatureValue(self, ctx:SysMLv2Parser.FeatureValueContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#multiplicity.
    def visitMultiplicity(self, ctx:SysMLv2Parser.MultiplicityContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#multiplicitySubset.
    def visitMultiplicitySubset(self, ctx:SysMLv2Parser.MultiplicitySubsetContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#multiplicityRange.
    def visitMultiplicityRange(self, ctx:SysMLv2Parser.MultiplicityRangeContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#ownedMultiplicity.
    def visitOwnedMultiplicity(self, ctx:SysMLv2Parser.OwnedMultiplicityContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#ownedMultiplicityRange.
    def visitOwnedMultiplicityRange(self, ctx:SysMLv2Parser.OwnedMultiplicityRangeContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#multiplicityBounds.
    def visitMultiplicityBounds(self, ctx:SysMLv2Parser.MultiplicityBoundsContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#multiplicityExpressionMember.
    def visitMultiplicityExpressionMember(self, ctx:SysMLv2Parser.MultiplicityExpressionMemberContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#metaclass.
    def visitMetaclass(self, ctx:SysMLv2Parser.MetaclassContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#prefixMetadataAnnotation.
    def visitPrefixMetadataAnnotation(self, ctx:SysMLv2Parser.PrefixMetadataAnnotationContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#prefixMetadataMember.
    def visitPrefixMetadataMember(self, ctx:SysMLv2Parser.PrefixMetadataMemberContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#prefixMetadataFeature.
    def visitPrefixMetadataFeature(self, ctx:SysMLv2Parser.PrefixMetadataFeatureContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#metadataFeature.
    def visitMetadataFeature(self, ctx:SysMLv2Parser.MetadataFeatureContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#metadataFeatureDeclaration.
    def visitMetadataFeatureDeclaration(self, ctx:SysMLv2Parser.MetadataFeatureDeclarationContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#metadataBody.
    def visitMetadataBody(self, ctx:SysMLv2Parser.MetadataBodyContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#metadataBodyElement.
    def visitMetadataBodyElement(self, ctx:SysMLv2Parser.MetadataBodyElementContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#metadataBodyFeatureMember.
    def visitMetadataBodyFeatureMember(self, ctx:SysMLv2Parser.MetadataBodyFeatureMemberContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#metadataBodyFeature.
    def visitMetadataBodyFeature(self, ctx:SysMLv2Parser.MetadataBodyFeatureContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#package.
    def visitPackage(self, ctx:SysMLv2Parser.PackageContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#libraryPackage.
    def visitLibraryPackage(self, ctx:SysMLv2Parser.LibraryPackageContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#packageDeclaration.
    def visitPackageDeclaration(self, ctx:SysMLv2Parser.PackageDeclarationContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#packageBody.
    def visitPackageBody(self, ctx:SysMLv2Parser.PackageBodyContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#elementFilterMember.
    def visitElementFilterMember(self, ctx:SysMLv2Parser.ElementFilterMemberContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#dependencyDeclaration.
    def visitDependencyDeclaration(self, ctx:SysMLv2Parser.DependencyDeclarationContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#annotatingMember.
    def visitAnnotatingMember(self, ctx:SysMLv2Parser.AnnotatingMemberContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#packageBodyElement.
    def visitPackageBodyElement(self, ctx:SysMLv2Parser.PackageBodyElementContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#packageMember.
    def visitPackageMember(self, ctx:SysMLv2Parser.PackageMemberContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#definitionElement.
    def visitDefinitionElement(self, ctx:SysMLv2Parser.DefinitionElementContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#usageElement.
    def visitUsageElement(self, ctx:SysMLv2Parser.UsageElementContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#basicDefinitionPrefix.
    def visitBasicDefinitionPrefix(self, ctx:SysMLv2Parser.BasicDefinitionPrefixContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#definitionExtensionKeyword.
    def visitDefinitionExtensionKeyword(self, ctx:SysMLv2Parser.DefinitionExtensionKeywordContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#definitionPrefix.
    def visitDefinitionPrefix(self, ctx:SysMLv2Parser.DefinitionPrefixContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#definition.
    def visitDefinition(self, ctx:SysMLv2Parser.DefinitionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#definitionDeclaration.
    def visitDefinitionDeclaration(self, ctx:SysMLv2Parser.DefinitionDeclarationContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#definitionBody.
    def visitDefinitionBody(self, ctx:SysMLv2Parser.DefinitionBodyContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#definitionBodyItem.
    def visitDefinitionBodyItem(self, ctx:SysMLv2Parser.DefinitionBodyItemContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#definitionBodyItemContent.
    def visitDefinitionBodyItemContent(self, ctx:SysMLv2Parser.DefinitionBodyItemContentContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#definitionMember.
    def visitDefinitionMember(self, ctx:SysMLv2Parser.DefinitionMemberContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#variantUsageMember.
    def visitVariantUsageMember(self, ctx:SysMLv2Parser.VariantUsageMemberContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#nonOccurrenceUsageMember.
    def visitNonOccurrenceUsageMember(self, ctx:SysMLv2Parser.NonOccurrenceUsageMemberContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#occurrenceUsageMember.
    def visitOccurrenceUsageMember(self, ctx:SysMLv2Parser.OccurrenceUsageMemberContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#structureUsageMember.
    def visitStructureUsageMember(self, ctx:SysMLv2Parser.StructureUsageMemberContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#behaviorUsageMember.
    def visitBehaviorUsageMember(self, ctx:SysMLv2Parser.BehaviorUsageMemberContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#refPrefix.
    def visitRefPrefix(self, ctx:SysMLv2Parser.RefPrefixContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#basicUsagePrefix.
    def visitBasicUsagePrefix(self, ctx:SysMLv2Parser.BasicUsagePrefixContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#endUsagePrefix.
    def visitEndUsagePrefix(self, ctx:SysMLv2Parser.EndUsagePrefixContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#usageExtensionKeyword.
    def visitUsageExtensionKeyword(self, ctx:SysMLv2Parser.UsageExtensionKeywordContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#unextendedUsagePrefix.
    def visitUnextendedUsagePrefix(self, ctx:SysMLv2Parser.UnextendedUsagePrefixContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#usagePrefix.
    def visitUsagePrefix(self, ctx:SysMLv2Parser.UsagePrefixContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#usage.
    def visitUsage(self, ctx:SysMLv2Parser.UsageContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#usageDeclaration.
    def visitUsageDeclaration(self, ctx:SysMLv2Parser.UsageDeclarationContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#usageCompletion.
    def visitUsageCompletion(self, ctx:SysMLv2Parser.UsageCompletionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#usageBody.
    def visitUsageBody(self, ctx:SysMLv2Parser.UsageBodyContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#defaultReferenceUsage.
    def visitDefaultReferenceUsage(self, ctx:SysMLv2Parser.DefaultReferenceUsageContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#referenceUsage.
    def visitReferenceUsage(self, ctx:SysMLv2Parser.ReferenceUsageContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#endFeatureUsage.
    def visitEndFeatureUsage(self, ctx:SysMLv2Parser.EndFeatureUsageContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#variantReference.
    def visitVariantReference(self, ctx:SysMLv2Parser.VariantReferenceContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#nonOccurrenceUsageElement.
    def visitNonOccurrenceUsageElement(self, ctx:SysMLv2Parser.NonOccurrenceUsageElementContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#endOccurrenceUsageElement.
    def visitEndOccurrenceUsageElement(self, ctx:SysMLv2Parser.EndOccurrenceUsageElementContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#occurrenceUsageElement.
    def visitOccurrenceUsageElement(self, ctx:SysMLv2Parser.OccurrenceUsageElementContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#structureUsageElement.
    def visitStructureUsageElement(self, ctx:SysMLv2Parser.StructureUsageElementContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#behaviorUsageElement.
    def visitBehaviorUsageElement(self, ctx:SysMLv2Parser.BehaviorUsageElementContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#variantUsageElement.
    def visitVariantUsageElement(self, ctx:SysMLv2Parser.VariantUsageElementContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#subclassificationPart.
    def visitSubclassificationPart(self, ctx:SysMLv2Parser.SubclassificationPartContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#attributeDefinition.
    def visitAttributeDefinition(self, ctx:SysMLv2Parser.AttributeDefinitionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#attributeUsage.
    def visitAttributeUsage(self, ctx:SysMLv2Parser.AttributeUsageContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#enumerationDefinition.
    def visitEnumerationDefinition(self, ctx:SysMLv2Parser.EnumerationDefinitionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#enumerationBody.
    def visitEnumerationBody(self, ctx:SysMLv2Parser.EnumerationBodyContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#enumerationUsageMember.
    def visitEnumerationUsageMember(self, ctx:SysMLv2Parser.EnumerationUsageMemberContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#enumeratedValue.
    def visitEnumeratedValue(self, ctx:SysMLv2Parser.EnumeratedValueContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#enumerationUsage.
    def visitEnumerationUsage(self, ctx:SysMLv2Parser.EnumerationUsageContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#occurrenceDefinitionPrefix.
    def visitOccurrenceDefinitionPrefix(self, ctx:SysMLv2Parser.OccurrenceDefinitionPrefixContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#occurrenceDefinition.
    def visitOccurrenceDefinition(self, ctx:SysMLv2Parser.OccurrenceDefinitionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#individualDefinition.
    def visitIndividualDefinition(self, ctx:SysMLv2Parser.IndividualDefinitionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#emptyMultiplicityMember.
    def visitEmptyMultiplicityMember(self, ctx:SysMLv2Parser.EmptyMultiplicityMemberContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#occurrenceUsagePrefix.
    def visitOccurrenceUsagePrefix(self, ctx:SysMLv2Parser.OccurrenceUsagePrefixContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#occurrenceUsage.
    def visitOccurrenceUsage(self, ctx:SysMLv2Parser.OccurrenceUsageContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#individualUsage.
    def visitIndividualUsage(self, ctx:SysMLv2Parser.IndividualUsageContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#portionUsage.
    def visitPortionUsage(self, ctx:SysMLv2Parser.PortionUsageContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#portionKind.
    def visitPortionKind(self, ctx:SysMLv2Parser.PortionKindContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#eventOccurrenceUsage.
    def visitEventOccurrenceUsage(self, ctx:SysMLv2Parser.EventOccurrenceUsageContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#sourceSuccessionMember.
    def visitSourceSuccessionMember(self, ctx:SysMLv2Parser.SourceSuccessionMemberContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#sourceSuccession.
    def visitSourceSuccession(self, ctx:SysMLv2Parser.SourceSuccessionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#sourceEndMember.
    def visitSourceEndMember(self, ctx:SysMLv2Parser.SourceEndMemberContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#sourceEnd.
    def visitSourceEnd(self, ctx:SysMLv2Parser.SourceEndContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#itemDefinition.
    def visitItemDefinition(self, ctx:SysMLv2Parser.ItemDefinitionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#itemUsage.
    def visitItemUsage(self, ctx:SysMLv2Parser.ItemUsageContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#partDefinition.
    def visitPartDefinition(self, ctx:SysMLv2Parser.PartDefinitionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#partUsage.
    def visitPartUsage(self, ctx:SysMLv2Parser.PartUsageContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#portDefinition.
    def visitPortDefinition(self, ctx:SysMLv2Parser.PortDefinitionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#conjugatedPortDefinitionMember.
    def visitConjugatedPortDefinitionMember(self, ctx:SysMLv2Parser.ConjugatedPortDefinitionMemberContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#conjugatedPortDefinition.
    def visitConjugatedPortDefinition(self, ctx:SysMLv2Parser.ConjugatedPortDefinitionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#portUsage.
    def visitPortUsage(self, ctx:SysMLv2Parser.PortUsageContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#conjugatedPortTyping.
    def visitConjugatedPortTyping(self, ctx:SysMLv2Parser.ConjugatedPortTypingContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#connectionDefinition.
    def visitConnectionDefinition(self, ctx:SysMLv2Parser.ConnectionDefinitionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#connectionUsage.
    def visitConnectionUsage(self, ctx:SysMLv2Parser.ConnectionUsageContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#connectorPart.
    def visitConnectorPart(self, ctx:SysMLv2Parser.ConnectorPartContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#binaryConnectorPart.
    def visitBinaryConnectorPart(self, ctx:SysMLv2Parser.BinaryConnectorPartContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#naryConnectorPart.
    def visitNaryConnectorPart(self, ctx:SysMLv2Parser.NaryConnectorPartContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#bindingConnectorAsUsage.
    def visitBindingConnectorAsUsage(self, ctx:SysMLv2Parser.BindingConnectorAsUsageContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#successionAsUsage.
    def visitSuccessionAsUsage(self, ctx:SysMLv2Parser.SuccessionAsUsageContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#interfaceDefinition.
    def visitInterfaceDefinition(self, ctx:SysMLv2Parser.InterfaceDefinitionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#interfaceBody.
    def visitInterfaceBody(self, ctx:SysMLv2Parser.InterfaceBodyContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#interfaceBodyItem.
    def visitInterfaceBodyItem(self, ctx:SysMLv2Parser.InterfaceBodyItemContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#interfaceNonOccurrenceUsageMember.
    def visitInterfaceNonOccurrenceUsageMember(self, ctx:SysMLv2Parser.InterfaceNonOccurrenceUsageMemberContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#interfaceNonOccurrenceUsageElement.
    def visitInterfaceNonOccurrenceUsageElement(self, ctx:SysMLv2Parser.InterfaceNonOccurrenceUsageElementContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#interfaceOccurrenceUsageMember.
    def visitInterfaceOccurrenceUsageMember(self, ctx:SysMLv2Parser.InterfaceOccurrenceUsageMemberContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#interfaceOccurrenceUsageElement.
    def visitInterfaceOccurrenceUsageElement(self, ctx:SysMLv2Parser.InterfaceOccurrenceUsageElementContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#defaultInterfaceEnd.
    def visitDefaultInterfaceEnd(self, ctx:SysMLv2Parser.DefaultInterfaceEndContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#interfaceUsage.
    def visitInterfaceUsage(self, ctx:SysMLv2Parser.InterfaceUsageContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#interfaceUsageDeclaration.
    def visitInterfaceUsageDeclaration(self, ctx:SysMLv2Parser.InterfaceUsageDeclarationContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#interfacePart.
    def visitInterfacePart(self, ctx:SysMLv2Parser.InterfacePartContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#binaryInterfacePart.
    def visitBinaryInterfacePart(self, ctx:SysMLv2Parser.BinaryInterfacePartContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#naryInterfacePart.
    def visitNaryInterfacePart(self, ctx:SysMLv2Parser.NaryInterfacePartContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#interfaceEndMember.
    def visitInterfaceEndMember(self, ctx:SysMLv2Parser.InterfaceEndMemberContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#interfaceEnd.
    def visitInterfaceEnd(self, ctx:SysMLv2Parser.InterfaceEndContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#allocationDefinition.
    def visitAllocationDefinition(self, ctx:SysMLv2Parser.AllocationDefinitionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#allocationUsage.
    def visitAllocationUsage(self, ctx:SysMLv2Parser.AllocationUsageContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#allocationUsageDeclaration.
    def visitAllocationUsageDeclaration(self, ctx:SysMLv2Parser.AllocationUsageDeclarationContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#flowDefinition.
    def visitFlowDefinition(self, ctx:SysMLv2Parser.FlowDefinitionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#message.
    def visitMessage(self, ctx:SysMLv2Parser.MessageContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#messageDeclaration.
    def visitMessageDeclaration(self, ctx:SysMLv2Parser.MessageDeclarationContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#messageEventMember.
    def visitMessageEventMember(self, ctx:SysMLv2Parser.MessageEventMemberContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#messageEvent.
    def visitMessageEvent(self, ctx:SysMLv2Parser.MessageEventContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#flowUsage.
    def visitFlowUsage(self, ctx:SysMLv2Parser.FlowUsageContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#successionFlowUsage.
    def visitSuccessionFlowUsage(self, ctx:SysMLv2Parser.SuccessionFlowUsageContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#flowPayloadFeatureMember.
    def visitFlowPayloadFeatureMember(self, ctx:SysMLv2Parser.FlowPayloadFeatureMemberContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#flowPayloadFeature.
    def visitFlowPayloadFeature(self, ctx:SysMLv2Parser.FlowPayloadFeatureContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#flowEndSubsetting.
    def visitFlowEndSubsetting(self, ctx:SysMLv2Parser.FlowEndSubsettingContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#featureChainPrefix.
    def visitFeatureChainPrefix(self, ctx:SysMLv2Parser.FeatureChainPrefixContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#actionDefinition.
    def visitActionDefinition(self, ctx:SysMLv2Parser.ActionDefinitionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#actionBody.
    def visitActionBody(self, ctx:SysMLv2Parser.ActionBodyContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#actionBodyItem.
    def visitActionBodyItem(self, ctx:SysMLv2Parser.ActionBodyItemContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#nonBehaviorBodyItem.
    def visitNonBehaviorBodyItem(self, ctx:SysMLv2Parser.NonBehaviorBodyItemContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#actionBehaviorMember.
    def visitActionBehaviorMember(self, ctx:SysMLv2Parser.ActionBehaviorMemberContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#initialNodeMember.
    def visitInitialNodeMember(self, ctx:SysMLv2Parser.InitialNodeMemberContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#actionNodeMember.
    def visitActionNodeMember(self, ctx:SysMLv2Parser.ActionNodeMemberContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#actionTargetSuccessionMember.
    def visitActionTargetSuccessionMember(self, ctx:SysMLv2Parser.ActionTargetSuccessionMemberContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#guardedSuccessionMember.
    def visitGuardedSuccessionMember(self, ctx:SysMLv2Parser.GuardedSuccessionMemberContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#actionUsage.
    def visitActionUsage(self, ctx:SysMLv2Parser.ActionUsageContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#actionUsageDeclaration.
    def visitActionUsageDeclaration(self, ctx:SysMLv2Parser.ActionUsageDeclarationContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#performActionUsage.
    def visitPerformActionUsage(self, ctx:SysMLv2Parser.PerformActionUsageContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#performActionUsageDeclaration.
    def visitPerformActionUsageDeclaration(self, ctx:SysMLv2Parser.PerformActionUsageDeclarationContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#actionNode.
    def visitActionNode(self, ctx:SysMLv2Parser.ActionNodeContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#actionNodeUsageDeclaration.
    def visitActionNodeUsageDeclaration(self, ctx:SysMLv2Parser.ActionNodeUsageDeclarationContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#actionNodePrefix.
    def visitActionNodePrefix(self, ctx:SysMLv2Parser.ActionNodePrefixContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#controlNode.
    def visitControlNode(self, ctx:SysMLv2Parser.ControlNodeContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#controlNodePrefix.
    def visitControlNodePrefix(self, ctx:SysMLv2Parser.ControlNodePrefixContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#mergeNode.
    def visitMergeNode(self, ctx:SysMLv2Parser.MergeNodeContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#decisionNode.
    def visitDecisionNode(self, ctx:SysMLv2Parser.DecisionNodeContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#joinNode.
    def visitJoinNode(self, ctx:SysMLv2Parser.JoinNodeContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#forkNode.
    def visitForkNode(self, ctx:SysMLv2Parser.ForkNodeContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#acceptNode.
    def visitAcceptNode(self, ctx:SysMLv2Parser.AcceptNodeContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#acceptNodeDeclaration.
    def visitAcceptNodeDeclaration(self, ctx:SysMLv2Parser.AcceptNodeDeclarationContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#acceptParameterPart.
    def visitAcceptParameterPart(self, ctx:SysMLv2Parser.AcceptParameterPartContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#payloadParameterMember.
    def visitPayloadParameterMember(self, ctx:SysMLv2Parser.PayloadParameterMemberContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#payloadParameter.
    def visitPayloadParameter(self, ctx:SysMLv2Parser.PayloadParameterContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#triggerValuePart.
    def visitTriggerValuePart(self, ctx:SysMLv2Parser.TriggerValuePartContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#triggerFeatureValue.
    def visitTriggerFeatureValue(self, ctx:SysMLv2Parser.TriggerFeatureValueContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#triggerExpression.
    def visitTriggerExpression(self, ctx:SysMLv2Parser.TriggerExpressionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#sendNode.
    def visitSendNode(self, ctx:SysMLv2Parser.SendNodeContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#sendNodeDeclaration.
    def visitSendNodeDeclaration(self, ctx:SysMLv2Parser.SendNodeDeclarationContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#senderReceiverPart.
    def visitSenderReceiverPart(self, ctx:SysMLv2Parser.SenderReceiverPartContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#nodeParameterMember.
    def visitNodeParameterMember(self, ctx:SysMLv2Parser.NodeParameterMemberContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#nodeParameter.
    def visitNodeParameter(self, ctx:SysMLv2Parser.NodeParameterContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#featureBinding.
    def visitFeatureBinding(self, ctx:SysMLv2Parser.FeatureBindingContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#emptyParameterMember.
    def visitEmptyParameterMember(self, ctx:SysMLv2Parser.EmptyParameterMemberContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#assignmentNode.
    def visitAssignmentNode(self, ctx:SysMLv2Parser.AssignmentNodeContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#assignmentNodeDeclaration.
    def visitAssignmentNodeDeclaration(self, ctx:SysMLv2Parser.AssignmentNodeDeclarationContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#assignmentTargetMember.
    def visitAssignmentTargetMember(self, ctx:SysMLv2Parser.AssignmentTargetMemberContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#assignmentTargetParameter.
    def visitAssignmentTargetParameter(self, ctx:SysMLv2Parser.AssignmentTargetParameterContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#assignmentTargetBinding.
    def visitAssignmentTargetBinding(self, ctx:SysMLv2Parser.AssignmentTargetBindingContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#terminateNode.
    def visitTerminateNode(self, ctx:SysMLv2Parser.TerminateNodeContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#ifNode.
    def visitIfNode(self, ctx:SysMLv2Parser.IfNodeContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#expressionParameterMember.
    def visitExpressionParameterMember(self, ctx:SysMLv2Parser.ExpressionParameterMemberContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#actionBodyParameterMember.
    def visitActionBodyParameterMember(self, ctx:SysMLv2Parser.ActionBodyParameterMemberContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#actionBodyParameter.
    def visitActionBodyParameter(self, ctx:SysMLv2Parser.ActionBodyParameterContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#ifNodeParameterMember.
    def visitIfNodeParameterMember(self, ctx:SysMLv2Parser.IfNodeParameterMemberContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#whileLoopNode.
    def visitWhileLoopNode(self, ctx:SysMLv2Parser.WhileLoopNodeContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#forLoopNode.
    def visitForLoopNode(self, ctx:SysMLv2Parser.ForLoopNodeContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#forVariableDeclarationMember.
    def visitForVariableDeclarationMember(self, ctx:SysMLv2Parser.ForVariableDeclarationMemberContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#forVariableDeclaration.
    def visitForVariableDeclaration(self, ctx:SysMLv2Parser.ForVariableDeclarationContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#actionTargetSuccession.
    def visitActionTargetSuccession(self, ctx:SysMLv2Parser.ActionTargetSuccessionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#targetSuccession.
    def visitTargetSuccession(self, ctx:SysMLv2Parser.TargetSuccessionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#guardedTargetSuccession.
    def visitGuardedTargetSuccession(self, ctx:SysMLv2Parser.GuardedTargetSuccessionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#defaultTargetSuccession.
    def visitDefaultTargetSuccession(self, ctx:SysMLv2Parser.DefaultTargetSuccessionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#guardedSuccession.
    def visitGuardedSuccession(self, ctx:SysMLv2Parser.GuardedSuccessionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#stateDefinition.
    def visitStateDefinition(self, ctx:SysMLv2Parser.StateDefinitionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#stateDefBody.
    def visitStateDefBody(self, ctx:SysMLv2Parser.StateDefBodyContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#stateBodyItem.
    def visitStateBodyItem(self, ctx:SysMLv2Parser.StateBodyItemContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#entryActionMember.
    def visitEntryActionMember(self, ctx:SysMLv2Parser.EntryActionMemberContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#doActionMember.
    def visitDoActionMember(self, ctx:SysMLv2Parser.DoActionMemberContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#exitActionMember.
    def visitExitActionMember(self, ctx:SysMLv2Parser.ExitActionMemberContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#entryTransitionMember.
    def visitEntryTransitionMember(self, ctx:SysMLv2Parser.EntryTransitionMemberContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#stateActionUsage.
    def visitStateActionUsage(self, ctx:SysMLv2Parser.StateActionUsageContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#statePerformActionUsage.
    def visitStatePerformActionUsage(self, ctx:SysMLv2Parser.StatePerformActionUsageContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#stateAcceptActionUsage.
    def visitStateAcceptActionUsage(self, ctx:SysMLv2Parser.StateAcceptActionUsageContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#stateSendActionUsage.
    def visitStateSendActionUsage(self, ctx:SysMLv2Parser.StateSendActionUsageContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#stateAssignmentActionUsage.
    def visitStateAssignmentActionUsage(self, ctx:SysMLv2Parser.StateAssignmentActionUsageContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#transitionUsageMember.
    def visitTransitionUsageMember(self, ctx:SysMLv2Parser.TransitionUsageMemberContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#targetTransitionUsageMember.
    def visitTargetTransitionUsageMember(self, ctx:SysMLv2Parser.TargetTransitionUsageMemberContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#stateUsage.
    def visitStateUsage(self, ctx:SysMLv2Parser.StateUsageContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#stateUsageBody.
    def visitStateUsageBody(self, ctx:SysMLv2Parser.StateUsageBodyContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#exhibitStateUsage.
    def visitExhibitStateUsage(self, ctx:SysMLv2Parser.ExhibitStateUsageContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#transitionUsage.
    def visitTransitionUsage(self, ctx:SysMLv2Parser.TransitionUsageContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#targetTransitionUsage.
    def visitTargetTransitionUsage(self, ctx:SysMLv2Parser.TargetTransitionUsageContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#triggerActionMember.
    def visitTriggerActionMember(self, ctx:SysMLv2Parser.TriggerActionMemberContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#triggerAction.
    def visitTriggerAction(self, ctx:SysMLv2Parser.TriggerActionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#guardExpressionMember.
    def visitGuardExpressionMember(self, ctx:SysMLv2Parser.GuardExpressionMemberContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#effectBehaviorMember.
    def visitEffectBehaviorMember(self, ctx:SysMLv2Parser.EffectBehaviorMemberContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#effectBehaviorUsage.
    def visitEffectBehaviorUsage(self, ctx:SysMLv2Parser.EffectBehaviorUsageContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#transitionPerformActionUsage.
    def visitTransitionPerformActionUsage(self, ctx:SysMLv2Parser.TransitionPerformActionUsageContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#transitionAcceptActionUsage.
    def visitTransitionAcceptActionUsage(self, ctx:SysMLv2Parser.TransitionAcceptActionUsageContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#transitionSendActionUsage.
    def visitTransitionSendActionUsage(self, ctx:SysMLv2Parser.TransitionSendActionUsageContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#transitionAssignmentActionUsage.
    def visitTransitionAssignmentActionUsage(self, ctx:SysMLv2Parser.TransitionAssignmentActionUsageContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#transitionSuccessionMember.
    def visitTransitionSuccessionMember(self, ctx:SysMLv2Parser.TransitionSuccessionMemberContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#transitionSuccession.
    def visitTransitionSuccession(self, ctx:SysMLv2Parser.TransitionSuccessionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#emptyEndMember.
    def visitEmptyEndMember(self, ctx:SysMLv2Parser.EmptyEndMemberContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#calculationDefinition.
    def visitCalculationDefinition(self, ctx:SysMLv2Parser.CalculationDefinitionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#calculationUsage.
    def visitCalculationUsage(self, ctx:SysMLv2Parser.CalculationUsageContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#calculationBody.
    def visitCalculationBody(self, ctx:SysMLv2Parser.CalculationBodyContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#calculationBodyPart.
    def visitCalculationBodyPart(self, ctx:SysMLv2Parser.CalculationBodyPartContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#calculationBodyItem.
    def visitCalculationBodyItem(self, ctx:SysMLv2Parser.CalculationBodyItemContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#returnParameterMember.
    def visitReturnParameterMember(self, ctx:SysMLv2Parser.ReturnParameterMemberContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#constraintDefinition.
    def visitConstraintDefinition(self, ctx:SysMLv2Parser.ConstraintDefinitionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#constraintUsage.
    def visitConstraintUsage(self, ctx:SysMLv2Parser.ConstraintUsageContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#assertConstraintUsage.
    def visitAssertConstraintUsage(self, ctx:SysMLv2Parser.AssertConstraintUsageContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#constraintUsageDeclaration.
    def visitConstraintUsageDeclaration(self, ctx:SysMLv2Parser.ConstraintUsageDeclarationContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#requirementDefinition.
    def visitRequirementDefinition(self, ctx:SysMLv2Parser.RequirementDefinitionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#requirementBody.
    def visitRequirementBody(self, ctx:SysMLv2Parser.RequirementBodyContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#requirementBodyItem.
    def visitRequirementBodyItem(self, ctx:SysMLv2Parser.RequirementBodyItemContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#subjectMember.
    def visitSubjectMember(self, ctx:SysMLv2Parser.SubjectMemberContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#subjectUsage.
    def visitSubjectUsage(self, ctx:SysMLv2Parser.SubjectUsageContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#requirementConstraintMember.
    def visitRequirementConstraintMember(self, ctx:SysMLv2Parser.RequirementConstraintMemberContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#requirementKind.
    def visitRequirementKind(self, ctx:SysMLv2Parser.RequirementKindContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#requirementConstraintUsage.
    def visitRequirementConstraintUsage(self, ctx:SysMLv2Parser.RequirementConstraintUsageContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#framedConcernMember.
    def visitFramedConcernMember(self, ctx:SysMLv2Parser.FramedConcernMemberContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#framedConcernUsage.
    def visitFramedConcernUsage(self, ctx:SysMLv2Parser.FramedConcernUsageContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#actorMember.
    def visitActorMember(self, ctx:SysMLv2Parser.ActorMemberContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#actorUsage.
    def visitActorUsage(self, ctx:SysMLv2Parser.ActorUsageContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#stakeholderMember.
    def visitStakeholderMember(self, ctx:SysMLv2Parser.StakeholderMemberContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#stakeholderUsage.
    def visitStakeholderUsage(self, ctx:SysMLv2Parser.StakeholderUsageContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#requirementUsage.
    def visitRequirementUsage(self, ctx:SysMLv2Parser.RequirementUsageContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#satisfyRequirementUsage.
    def visitSatisfyRequirementUsage(self, ctx:SysMLv2Parser.SatisfyRequirementUsageContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#satisfactionSubjectMember.
    def visitSatisfactionSubjectMember(self, ctx:SysMLv2Parser.SatisfactionSubjectMemberContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#satisfactionParameter.
    def visitSatisfactionParameter(self, ctx:SysMLv2Parser.SatisfactionParameterContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#satisfactionFeatureValue.
    def visitSatisfactionFeatureValue(self, ctx:SysMLv2Parser.SatisfactionFeatureValueContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#satisfactionReferenceExpression.
    def visitSatisfactionReferenceExpression(self, ctx:SysMLv2Parser.SatisfactionReferenceExpressionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#concernDefinition.
    def visitConcernDefinition(self, ctx:SysMLv2Parser.ConcernDefinitionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#concernUsage.
    def visitConcernUsage(self, ctx:SysMLv2Parser.ConcernUsageContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#caseDefinition.
    def visitCaseDefinition(self, ctx:SysMLv2Parser.CaseDefinitionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#caseUsage.
    def visitCaseUsage(self, ctx:SysMLv2Parser.CaseUsageContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#caseBody.
    def visitCaseBody(self, ctx:SysMLv2Parser.CaseBodyContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#caseBodyItem.
    def visitCaseBodyItem(self, ctx:SysMLv2Parser.CaseBodyItemContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#objectiveMember.
    def visitObjectiveMember(self, ctx:SysMLv2Parser.ObjectiveMemberContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#objectiveRequirementUsage.
    def visitObjectiveRequirementUsage(self, ctx:SysMLv2Parser.ObjectiveRequirementUsageContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#analysisCaseDefinition.
    def visitAnalysisCaseDefinition(self, ctx:SysMLv2Parser.AnalysisCaseDefinitionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#analysisCaseUsage.
    def visitAnalysisCaseUsage(self, ctx:SysMLv2Parser.AnalysisCaseUsageContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#verificationCaseDefinition.
    def visitVerificationCaseDefinition(self, ctx:SysMLv2Parser.VerificationCaseDefinitionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#verificationCaseUsage.
    def visitVerificationCaseUsage(self, ctx:SysMLv2Parser.VerificationCaseUsageContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#requirementVerificationMember.
    def visitRequirementVerificationMember(self, ctx:SysMLv2Parser.RequirementVerificationMemberContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#requirementVerificationUsage.
    def visitRequirementVerificationUsage(self, ctx:SysMLv2Parser.RequirementVerificationUsageContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#useCaseDefinition.
    def visitUseCaseDefinition(self, ctx:SysMLv2Parser.UseCaseDefinitionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#useCaseUsage.
    def visitUseCaseUsage(self, ctx:SysMLv2Parser.UseCaseUsageContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#includeUseCaseUsage.
    def visitIncludeUseCaseUsage(self, ctx:SysMLv2Parser.IncludeUseCaseUsageContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#viewDefinition.
    def visitViewDefinition(self, ctx:SysMLv2Parser.ViewDefinitionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#viewDefinitionBody.
    def visitViewDefinitionBody(self, ctx:SysMLv2Parser.ViewDefinitionBodyContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#viewDefinitionBodyItem.
    def visitViewDefinitionBodyItem(self, ctx:SysMLv2Parser.ViewDefinitionBodyItemContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#viewRenderingMember.
    def visitViewRenderingMember(self, ctx:SysMLv2Parser.ViewRenderingMemberContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#viewRenderingUsage.
    def visitViewRenderingUsage(self, ctx:SysMLv2Parser.ViewRenderingUsageContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#viewUsage.
    def visitViewUsage(self, ctx:SysMLv2Parser.ViewUsageContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#viewBody.
    def visitViewBody(self, ctx:SysMLv2Parser.ViewBodyContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#viewBodyItem.
    def visitViewBodyItem(self, ctx:SysMLv2Parser.ViewBodyItemContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#expose.
    def visitExpose(self, ctx:SysMLv2Parser.ExposeContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#membershipExpose.
    def visitMembershipExpose(self, ctx:SysMLv2Parser.MembershipExposeContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#namespaceExpose.
    def visitNamespaceExpose(self, ctx:SysMLv2Parser.NamespaceExposeContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#viewpointDefinition.
    def visitViewpointDefinition(self, ctx:SysMLv2Parser.ViewpointDefinitionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#viewpointUsage.
    def visitViewpointUsage(self, ctx:SysMLv2Parser.ViewpointUsageContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#renderingDefinition.
    def visitRenderingDefinition(self, ctx:SysMLv2Parser.RenderingDefinitionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#renderingUsage.
    def visitRenderingUsage(self, ctx:SysMLv2Parser.RenderingUsageContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#metadataDefinition.
    def visitMetadataDefinition(self, ctx:SysMLv2Parser.MetadataDefinitionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#prefixMetadataUsage.
    def visitPrefixMetadataUsage(self, ctx:SysMLv2Parser.PrefixMetadataUsageContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#metadataUsage.
    def visitMetadataUsage(self, ctx:SysMLv2Parser.MetadataUsageContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#metadataUsageDeclaration.
    def visitMetadataUsageDeclaration(self, ctx:SysMLv2Parser.MetadataUsageDeclarationContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#metadataBodyUsageMember.
    def visitMetadataBodyUsageMember(self, ctx:SysMLv2Parser.MetadataBodyUsageMemberContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#metadataBodyUsage.
    def visitMetadataBodyUsage(self, ctx:SysMLv2Parser.MetadataBodyUsageContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#extendedDefinition.
    def visitExtendedDefinition(self, ctx:SysMLv2Parser.ExtendedDefinitionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#extendedUsage.
    def visitExtendedUsage(self, ctx:SysMLv2Parser.ExtendedUsageContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#filterPackageImportDeclaration.
    def visitFilterPackageImportDeclaration(self, ctx:SysMLv2Parser.FilterPackageImportDeclarationContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#namespaceImportDirect.
    def visitNamespaceImportDirect(self, ctx:SysMLv2Parser.NamespaceImportDirectContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#calculationUsageDeclaration.
    def visitCalculationUsageDeclaration(self, ctx:SysMLv2Parser.CalculationUsageDeclarationContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#emptyActionUsage_.
    def visitEmptyActionUsage_(self, ctx:SysMLv2Parser.EmptyActionUsage_Context):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#emptyFeature_.
    def visitEmptyFeature_(self, ctx:SysMLv2Parser.EmptyFeature_Context):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#emptyMultiplicity_.
    def visitEmptyMultiplicity_(self, ctx:SysMLv2Parser.EmptyMultiplicity_Context):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#emptyUsage_.
    def visitEmptyUsage_(self, ctx:SysMLv2Parser.EmptyUsage_Context):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#filterPackageImport.
    def visitFilterPackageImport(self, ctx:SysMLv2Parser.FilterPackageImportContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#nonFeatureChainPrimaryExpression.
    def visitNonFeatureChainPrimaryExpression(self, ctx:SysMLv2Parser.NonFeatureChainPrimaryExpressionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SysMLv2Parser#portConjugation.
    def visitPortConjugation(self, ctx:SysMLv2Parser.PortConjugationContext):
        return self.visitChildren(ctx)



del SysMLv2Parser