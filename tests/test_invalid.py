"""Test invalid query graphs."""
import pytest

from reasoner_transpiler.cypher import get_query
from reasoner_transpiler.exceptions import InvalidPredicateError, InvalidQualifierError, \
    InvalidQualifierValueError, UnsupportedError


def test_invalid_node():
    """Test that an invalid node property value throws an error."""
    qgraph = {
        "nodes": {
            "n0": {
                "categories": "biolink:BiologicalEntity",
                "constraints": [
                    {"id": "test:invalid_constraint",
                     "value": {"a": 1}}
                ]
            },
        },
        "edges": dict(),
    }
    with pytest.raises(UnsupportedError):
        get_query(qgraph)


def test_invalid_predicate():
    """Test that an invalid edge predicate throws an error."""
    qgraph = {
        "nodes": {
            "n0": {
                "ids": ["MONDO:0005148"],
            },
            "n1": {
                "categories": ["biolink:PhenotypicFeature"],
            },
        },
        "edges": {
            "e0": {
                "subject": "n0",
                "object": "n1",
                "predicates": ["biolink:invalid_predicate"],
            },
        },
    }
    with pytest.raises(InvalidPredicateError):
        query = get_query(qgraph)

    """Test that an invalid edge predicate throws an error, along with a valid predicate."""
    qgraph = {
        "nodes": {
            "n0": {
                "ids": ["MONDO:0005148"],
            },
            "n1": {
                "categories": ["biolink:PhenotypicFeature"],
            },
        },
        "edges": {
            "e0": {
                "subject": "n0",
                "object": "n1",
                "predicates": ["biolink:invalid_predicate", "biolink:associated_with"],
            },
        },
    }
    with pytest.raises(InvalidPredicateError):
        query = get_query(qgraph)


def test_invalid_qualifier():
    """Test that an invalid edge qualifier throws an error."""
    qgraph = {
        "nodes": {
            "n0": {},
            "n1": {
                "ids": "NCBIGene:283871"
            },
        },
        "edges": {
            "e0": {
                "subject": "n0",
                "object": "n1",
                "predicates": ["biolink:affects"],
                "qualifier_constraints": [
                    {
                        "qualifier_set": [
                            {
                                "qualifier_type_id": "bogus_qualifier_1",
                                "qualifier_value": "abundance"
                            },
                        ]
                    },
                ]
            },
        },
    }
    with pytest.raises(InvalidQualifierError):
        query = get_query(qgraph)


def test_invalid_qualifier_value():
    """Test that an invalid edge qualifier value throws an error."""
    qgraph = {
        "nodes": {
            "n0": {},
            "n1": {
                "ids": "NCBIGene:283871"
            },
        },
        "edges": {
            "e0": {
                "subject": "n0",
                "object": "n1",
                "predicates": ["biolink:affects"],
                "qualifier_constraints": [
                    {
                        "qualifier_set": [
                            {
                                "qualifier_type_id": "object_aspect_qualifier",
                                "qualifier_value": "bogus_value"
                            },
                        ]
                    },
                ]
            },
        },
    }
    with pytest.raises(InvalidQualifierValueError):
        query = get_query(qgraph)
