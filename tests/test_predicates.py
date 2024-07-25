"""Test predicate handling."""
import pytest

from reasoner_transpiler.cypher import get_query
from .fixtures import fixture_neo4j_driver


def test_symmetric(neo4j_driver):
    """Test symmetric predicate."""
    qgraph = {
        "nodes": {
            "n0": {},
            "n1": {
                "ids": "NCBIGene:836"
            },
        },
        "edges": {
            "e10a": {
                "subject": "n1",
                "object": "n0",
                "predicates": "biolink:genetically_associated_with",
            },
        },
    }
    output = neo4j_driver.run(get_query(qgraph), convert_to_trapi=True, qgraph=qgraph)
    assert len(output["results"]) == 2


def test_any(neo4j_driver):
    """Test any predicate."""
    qgraph = {
        "nodes": {
            "n0": {},
            "n1": {
                "ids": "NCBIGene:836"
            },
        },
        "edges": {
            "e10a": {
                "subject": "n1",
                "object": "n0",
            },
        },
    }
    output = neo4j_driver.run(get_query(qgraph), convert_to_trapi=True, qgraph=qgraph)
    assert len(output["results"]) == 4


def test_root_predicate(neo4j_driver):
    """Test root/related_to predicate."""
    qgraph = {
        "nodes": {
            "n0": {},
            "n1": {
                "ids": "NCBIGene:836"
            },
        },
        "edges": {
            "e10a": {
                "subject": "n1",
                "object": "n0",
                "predicates": "biolink:related_to"
            },
        },
    }
    output = neo4j_driver.run(get_query(qgraph), convert_to_trapi=True, qgraph=qgraph)
    assert len(output["results"]) == 4


def test_sub(neo4j_driver):
    """Test sub predicate."""
    qgraph = {
        "nodes": {
            "n0": {
                "ids": "MONDO:0004993",
            },
            "n1": {},
        },
        "edges": {
            "e10": {
                "subject": "n0",
                "object": "n1",
                "predicates": "biolink:genetically_associated_with",
            },
        },
    }
    output = neo4j_driver.run(get_query(qgraph), convert_to_trapi=True, qgraph=qgraph)
    assert len(output["results"]) == 2


def test_inverse(neo4j_driver):
    """Test inverse predicate."""
    qgraph = {
        "nodes": {
            "n0": {
                "ids": "NCBIGene:672",
            },
            "n1": {},
        },
        "edges": {
            "e10": {
                "subject": "n0",
                "object": "n1",
                "predicates": "biolink:gene_associated_with_condition",
            },
        },
    }
    output = neo4j_driver.run(get_query(qgraph), convert_to_trapi=True, qgraph=qgraph)
    assert len(output["results"]) == 1
