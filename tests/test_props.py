"""Test querying with properties."""
import pytest
from reasoner_transpiler.cypher import get_query
from .fixtures import fixture_neo4j_driver


def test_numeric(neo4j_driver):
    """Test querying with numeric property."""
    qgraph = {
        "nodes": {
            "n0": {
                "categories": "biolink:Gene",
                "constraints": [
                    {"id": "length",
                     "value": 277,
                     "operator": "==="}
                ]
            },
        },
        "edges": {},
    }
    output = neo4j_driver.run(get_query(qgraph), convert_to_trapi=True, qgraph=qgraph)
    assert len(output["results"]) == 1
    results = sorted(
        output["knowledge_graph"]["nodes"].values(),
        key=lambda node: node["name"],
    )
    expected_nodes = [
        "CASP3",
    ]
    for ind, result in enumerate(results):
        assert result["name"] == expected_nodes[ind]


def test_string(neo4j_driver):
    """Test querying with string property."""
    qgraph = {
        "nodes": {
            "n0": {
                "categories": "biolink:Gene",
                "constraints": [
                    {"id": "chromosome",
                     "value": "17",
                     "operator": "==="}
                ]
            },
        },
        "edges": {},
    }
    output = neo4j_driver.run(get_query(qgraph), convert_to_trapi=True, qgraph=qgraph)
    assert len(output["results"]) == 1
    results = sorted(
        output["knowledge_graph"]["nodes"].values(),
        key=lambda node: node["name"],
    )
    expected_nodes = [
        "BRCA1",
    ]
    for ind, result in enumerate(results):
        assert result["name"] == expected_nodes[ind]


def test_bool(neo4j_driver):
    """Test querying with boolean property."""
    qgraph = {
        "nodes": {
            "n0": {
                "categories": "biolink:ChemicalSubstance",
            },
            "n1": {
                "categories": "biolink:Disease",
            },
        },
        "edges": {
            "e01": {
                "subject": "n0",
                "object": "n1",
                "predicates": "biolink:treats",
                "attribute_constraints": [
                    {"id": "fda_approved",
                     "value": True,
                     "operator": "==="}
                ]
            },
        },
    }
    output = neo4j_driver.run(get_query(qgraph), convert_to_trapi=True, qgraph=qgraph)
    assert len(output["results"]) == 1
    results = sorted(
        output["knowledge_graph"]["nodes"].values(),
        key=lambda node: node["name"],
    )
    expected_nodes = [
        "metformin", "type 2 diabetes mellitus",
    ]
    for ind, result in enumerate(results):
        assert result["name"] == expected_nodes[ind]


def test_publications(neo4j_driver):
    """Test publications."""
    qgraph = {
        "nodes": {
            "n0": {
                "ids": "NCBIGene:836",
            },
            "n1": {
                "ids": "NCBIGene:841",
            },
        },
        "edges": {
            "e01": {
                "subject": "n0",
                "object": "n1",
            },
        },
    }
    output = neo4j_driver.run(get_query(qgraph), convert_to_trapi=True, qgraph=qgraph)
    edges = output["knowledge_graph"]["edges"]
    assert len(edges) == 1
    attributes = list(edges.values())[0]["attributes"]
    assert len(attributes) == 1
    assert attributes[0] == {
        "original_attribute_name": "publications",
        "attribute_type_id": "EDAM:data_0971",
        "value": ["xxx"],
    }



def test_constraints(neo4j_driver):
    """Test querying with 'constraints' property."""
    qgraph = {
        "nodes": {
            "n0": {
                "categories": "biolink:Gene",
                "constraints": [],
            },
            "n1": {
                "constraints": [],
            },
        },
        "edges": {
            "e01": {
                "subject": "n0",
                "object": "n1",
                "attribute_constraints": [],
            },
        },
    }
    output = neo4j_driver.run(get_query(qgraph), convert_to_trapi=True, qgraph=qgraph)
    assert len(output["results"]) == 10
