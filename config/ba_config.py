"""
Configuration file for business architecture data categories and class definitions.
This centralized configuration is based on an RDF/OWL ontology stored in ba_ontology.ttl.
"""

import os
from enum import Enum
from pathlib import Path
from typing import Dict, Any, List, Tuple, TypedDict, Optional, Set

import rdflib
from rdflib import Graph, URIRef, Literal, Namespace
from rdflib.namespace import RDF, RDFS, XSD, OWL


# Define namespace
BASE = Namespace("http://capsifi.com/doc2ba/")


class OntologyConfig:
    """Configuration class that loads and queries the BA ontology."""
    
    def __init__(self, ttl_path: Optional[str] = None):
        """Initialize the ontology configuration."""
        if ttl_path is None:
            # Use the default path relative to this file
            base_dir = Path(__file__).parent
            ttl_path = str(base_dir / "ba_ontology.ttl")
        
        self.graph = Graph()
        self.graph.parse(ttl_path, format="turtle")
        
        # Bind the namespaces for easier querying
        self.graph.bind("", BASE)
        
        # Initialize categories and artefacts
        self._init_enums()
    
    def _init_enums(self):
        """Initialize the CategoryType and BusinessArtefactType enums from the ontology."""
        # Create CategoryType enum dynamically
        category_values = {}
        for s in self.graph.subjects(RDF.type, BASE.Category):
            label = str(self.graph.value(s, RDFS.label))
            uri = str(s).replace(str(BASE), "")
            category_values[uri] = label
        
        self.CategoryType = Enum('CategoryType', category_values)
        
        # Create BusinessArtefactType enum dynamically
        artefact_values = {}
        for s in self.graph.subjects(RDF.type, BASE.BusinessArtefact):
            label = str(self.graph.value(s, RDFS.label))
            uri = str(s).replace(str(BASE), "")
            artefact_values[uri] = label
        
        self.BusinessArtefactType = Enum('BusinessArtefactType', artefact_values)
    
    def get_category_mappings(self) -> Dict[Enum, Dict[str, Any]]:
        """Get category mappings."""
        mappings = {}
        
        for category in self.graph.subjects(RDF.type, BASE.Category):
            category_name = str(category).replace(str(BASE), "")
            category_enum = getattr(self.CategoryType, category_name)
            description = str(self.graph.value(category, RDFS.comment))
            
            # Get allowed types for this category
            allowed_types = []
            for artefact in self.graph.subjects(RDFS.subClassOf, category):
                artefact_name = str(artefact).replace(str(BASE), "")
                allowed_types.append(getattr(self.BusinessArtefactType, artefact_name))
            
            # Special handling for Unknown category - include all business artefact types
            if category_name == "Unknown":
                allowed_types = list(self.BusinessArtefactType)
            
            # Get examples from the ontology
            examples = []
            for ex in self.graph.objects(category, BASE.hasExample):
                examples.append(str(ex))
            
            mappings[category_enum] = {
                "description": description,
                "allowed_types": allowed_types,
                "examples": examples
            }
        
        return mappings
    
    def get_inference_rules(self) -> List[Tuple[Enum, Enum, str, str]]:
        """Get inference rules from RDF properties with domain and range."""
        rules = []
        
        # Handle properties that connect business artefacts
        for prop in self.graph.subjects(RDF.type, RDF.Property):
            prop_name = str(prop).replace(str(BASE), "")
            description = str(self.graph.value(prop, RDFS.comment) or "")
            
            # Get domain and range
            domain = self.graph.value(prop, RDFS.domain)
            range_value = self.graph.value(prop, RDFS.range)
            
            if domain and range_value:
                # Handle multiple domains/ranges which might be blank nodes
                domains = self._get_class_values(domain)
                ranges = self._get_class_values(range_value)
                
                for domain_value in domains:
                    for range_value in ranges:
                        domain_name = str(domain_value).replace(str(BASE), "")
                        range_name = str(range_value).replace(str(BASE), "")
                        
                        # Convert to enum values
                        try:
                            source_type = getattr(self.BusinessArtefactType, domain_name)
                            target_type = getattr(self.BusinessArtefactType, range_name)
                            rules.append((source_type, target_type, prop_name, description))
                        except AttributeError:
                            # Skip if not a valid BusinessArtefactType
                            pass
        
        return rules
    
    def _get_class_values(self, node) -> Set[URIRef]:
        """Helper method to get class values from a node which might be a list."""
        if isinstance(node, URIRef):
            return {node}
        
        # It might be a blank node with alternatives
        result = set()
        if node in self.graph.subjects():
            for item in self.graph.objects(node, None):
                if isinstance(item, URIRef):
                    result.add(item)
        
        return result if result else {node}
    
    def get_artefact_rules(self) -> Dict[Enum, List[Dict[str, Any]]]:
        """Get artefact rules."""
        rules = {}
        
        # Query for classification rules
        for rule in self.graph.subjects(RDF.type, BASE.ClassificationRule):
            applies_to = self.graph.value(rule, BASE.appliesTo)
            
            if not applies_to:
                continue
                
            artefact_name = str(applies_to).replace(str(BASE), "")
            
            try:
                artefact_enum = getattr(self.BusinessArtefactType, artefact_name)
                
                condition = str(self.graph.value(rule, BASE.condition) or "")
                conclusion = str(self.graph.value(rule, BASE.conclusion) or "")
                
                # Get examples
                examples = []
                for example in self.graph.objects(rule, BASE.hasExample):
                    examples.append(str(example))
                
                # Get counter-examples
                counter_examples = []
                for counter in self.graph.objects(rule, BASE.hasCounterExample):
                    counter_examples.append(str(counter))
                
                rule_dict = {
                    "condition": condition,
                    "conclusion": conclusion,
                    "examples": examples,
                    "counter_examples": counter_examples
                }
                
                if artefact_enum not in rules:
                    rules[artefact_enum] = []
                
                rules[artefact_enum].append(rule_dict)
                
            except AttributeError:
                # Skip if not a valid BusinessArtefactType
                pass
        
        return rules

    def get_artefact_definitions(self) -> Dict[Enum, str]:
        """Return ontology definitions keyed by business artefact type."""
        definitions = {}
        for artefact in self.graph.subjects(RDF.type, BASE.BusinessArtefact):
            artefact_name = str(artefact).replace(str(BASE), "")
            try:
                artefact_enum = getattr(self.BusinessArtefactType, artefact_name)
            except AttributeError:
                continue
            definitions[artefact_enum] = str(
                self.graph.value(artefact, RDFS.comment) or ""
            )
        return definitions


# Create a global instance for easy import
ontology_config = OntologyConfig()

# Export the types and configuration
CategoryType = ontology_config.CategoryType
BusinessArtefactType = ontology_config.BusinessArtefactType
CATEGORY_MAPPINGS = ontology_config.get_category_mappings()
INFERENCE_RULES = ontology_config.get_inference_rules()
ARTEFACT_RULES = ontology_config.get_artefact_rules()
ARTEFACT_DEFINITIONS = ontology_config.get_artefact_definitions()

# Define RippleDownRule type for type checking
class RippleDownRule(TypedDict):
    """A rule structure for differentiating business architecture concepts."""
    condition: str  # The IF part of the rule
    conclusion: str  # The THEN part of the rule
    examples: List[str]  # Optional examples that match this rule
    counter_examples: List[str]  # Optional examples that don't match this rule
