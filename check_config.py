#!/usr/bin/env python
"""
Simple script to verify the ba_config.py file works correctly.
This script imports from config.ba_config and prints some basic information.
"""

from config.ba_config import (
    CategoryType, 
    BusinessArtefactType,
    CATEGORY_MAPPINGS,
    INFERENCE_RULES,
    ARTEFACT_RULES
)

if __name__ == "__main__":
    # Check CategoryType
    print(f"Found {len(list(CategoryType))} categories:")
    for cat in CategoryType:
        print(f"  - {cat.name}: {cat.value}")
    
    # Check BusinessArtefactType
    print(f"\nFound {len(list(BusinessArtefactType))} business artefact types:")
    for art in BusinessArtefactType:
        print(f"  - {art.name}: {art.value}")
    
    # Check category mappings
    print(f"\nCategory mappings:")
    for cat, mapping in CATEGORY_MAPPINGS.items():
        print(f"  - {cat.value}:")
        print(f"    - Description: {mapping['description']}")
        print(f"    - Allowed types: {len(mapping['allowed_types'])}")
        print(f"    - Examples: {len(mapping['examples'])}")
    
    # Check inference rules
    print(f"\nInference rules: {len(INFERENCE_RULES)}")
    
    # Check artefact rules
    print(f"\nArtefact rules:")
    for art, rules in ARTEFACT_RULES.items():
        print(f"  - {art.value}: {len(rules)} rules")
    
    print("\nConfig check completed successfully!")
