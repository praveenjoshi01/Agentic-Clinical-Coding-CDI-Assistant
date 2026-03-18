"""
Knowledge graph edge type constants and type aliases.

Defines the four relationship types used in the CDI knowledge graph
and the node type constant for ICD-10 code nodes.
"""

# Edge type constants
COMMONLY_CO_CODED = "COMMONLY_CO_CODED"
CONFLICTS_WITH = "CONFLICTS_WITH"
HAS_PARENT = "HAS_PARENT"
REQUIRES_QUALIFIER = "REQUIRES_QUALIFIER"

EDGE_TYPES = [COMMONLY_CO_CODED, CONFLICTS_WITH, HAS_PARENT, REQUIRES_QUALIFIER]

# Node type constants
NODE_TYPE_ICD = "icd_code"
