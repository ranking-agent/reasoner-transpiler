import pytest

from reasoner_transpiler.cypher import get_query
from .fixtures import fixture_neo4j_driver


def test_single_qualifier(neo4j_driver):
    """Test edge satisfying one set of qualifier constraints is returned """
    qgraph = {
        "nodes": {
            "n0": {},
            "n1": {
                "ids": ["NCBIGene:283871"]
            },
        },
        "edges": {
            "e10a": {
                "subject": "n0",
                "object": "n1",
                "predicates": "biolink:affects",
                "qualifier_constraints": [
                    {
                        "qualifier_set": [
                            {
                                "qualifier_type_id": "biolink:qualified_predicate",
                                "qualifier_value": "biolink:causes"
                            }, {
                                "qualifier_type_id": "biolink:object_aspect_qualifier",
                                "qualifier_value": "activity"
                            }
                        ]
                    }
                ]
            },
        },
    }
    output = neo4j_driver.run(get_query(qgraph), convert_to_trapi=True, qgraph=qgraph)
    assert len(output["results"]) == 1
    assert len(output["results"][0]["analyses"][0]["edge_bindings"]["e10a"]) == 1
    qualified_predicate_output = {'qualifier_type_id': 'biolink:qualified_predicate', 'qualifier_value': 'biolink:causes'}
    qualifier_output = output["knowledge_graph"]["edges"]["qualified_edge_multiple_qualifier"]["qualifiers"]
    assert qualified_predicate_output in qualifier_output
    assert "qualified_predicate" not in output["knowledge_graph"]["edges"]["qualified_edge_multiple_qualifier"]
    assert "biolink:qualified_predicate" not in output["knowledge_graph"]["edges"]["qualified_edge_multiple_qualifier"]


def test_multi_qualifier(neo4j_driver):
    """Test if edges satisfying constraints are returned with multiple qualifier sets"""
    qgraph = {
        "nodes": {
            "n0": {},
            "n1": {
                "ids": ["NCBIGene:283871"]
            },
        },
        "edges": {
            "e10a": {
                "subject": "n0",
                "object": "n1",
                "predicates": "biolink:affects",
                "qualifier_constraints": [
                    {
                        "qualifier_set": [
                            {
                                "qualifier_type_id": "biolink:object_aspect_qualifier",
                                "qualifier_value": "activity"
                            },
                        ]
                    },{
                        "qualifier_set": [
                            {
                                "qualifier_type_id": "biolink:qualified_predicate",
                                "qualifier_value": "biolink:causes"
                            }
                        ]
                    }
                ]
            },
        },
    }
    output = neo4j_driver.run(get_query(qgraph), convert_to_trapi=True, qgraph=qgraph)
    assert len(output["results"]) == 1
    assert len(output["results"][0]["analyses"][0]["edge_bindings"]["e10a"]) == 2
    direction_qualifier_output = {'qualifier_type_id': 'biolink:object_direction_qualifier', 'qualifier_value': 'decreased'}
    qualified_predicate_output = {'qualifier_type_id': 'biolink:qualified_predicate', 'qualifier_value': 'biolink:causes'}
    aspect_qualifier_output = {'qualifier_type_id': 'biolink:object_aspect_qualifier', 'qualifier_value': 'activity'}
    qualifier_output = output["knowledge_graph"]["edges"]["qualified_edge_multiple_qualifier"]["qualifiers"]
    assert direction_qualifier_output in qualifier_output
    assert aspect_qualifier_output in qualifier_output
    assert qualified_predicate_output in qualifier_output


def test_qualifier_heirarchy(neo4j_driver):
    """Test if edges satisfying constraints are returned when a qualifier has a value
    that is an ancestor of the value expected in the test data edge"""
    qgraph = {
        "nodes": {
            "n0": {},
            "n1": {
                "ids": ["NCBIGene:283871"]
            },
        },
        "edges": {
            "e10a": {
                "subject": "n0",
                "object": "n1",
                "predicates": "biolink:affects",
                "qualifier_constraints": [
                    {
                        "qualifier_set": [
                            {
                                "qualifier_type_id": "biolink:object_aspect_qualifier",
                                "qualifier_value": "activity_or_abundance"
                            },
                        ]
                    }
                ]
            },
        },
    }
    output = neo4j_driver.run(get_query(qgraph), convert_to_trapi=True, qgraph=qgraph)
    assert len(output["results"]) == 1
    assert len(output["results"][0]["analyses"][0]["edge_bindings"]["e10a"]) == 1


def test_mismatch_qualifier_value(neo4j_driver):
    """ test that no edges are returned with a qualifier value that doesn't match any edges"""
    qgraph = {
        "nodes": {
            "n0": {},
            "n1": {
                "ids": ["NCBIGene:283871"]
            },
        },
        "edges": {
            "e10a": {
                "subject": "n0",
                "object": "n1",
                "predicates": "biolink:affects",
                "qualifier_constraints": [
                    {
                        "qualifier_set": [
                            {
                                "qualifier_type_id": "biolink:object_aspect_qualifier",
                                "qualifier_value": "abundance"
                            },
                        ]
                    },
                ]
            },
        },
    }
    output = neo4j_driver.run(get_query(qgraph), convert_to_trapi=True, qgraph=qgraph)
    assert len(output["results"]) == 0


def test_empty_qualifier_set(neo4j_driver):
    """Test if edges satisfying all constraints are returned"""
    qgraph = {
        "nodes": {
            "n0": {},
            "n1": {
                "ids": ["NCBIGene:283871"]
            },
        },
        "edges": {
            "e10a": {
                "subject": "n0",
                "object": "n1",
                "predicates": "biolink:affects",
                "qualifier_constraints": [
                    {
                        "qualifier_set": [
                        ]
                    },
                ]
            },
        },
    }
    output = neo4j_driver.run(get_query(qgraph), convert_to_trapi=True, qgraph=qgraph)
    assert len(output["results"]) == 1
