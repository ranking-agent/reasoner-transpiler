"""Test predicate handling."""
import pytest

from reasoner_transpiler.cypher import get_query
from .fixtures import fixture_db_driver


def test_symmetric(db_driver):
    """Test symmetric predicate."""
    qgraph = {
        "nodes": {
            "n0": {},
            "n1": {
                "ids": ["NCBIGene:836"]
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
    dialect, driver = db_driver
    output = driver.run(get_query(qgraph, dialect=dialect), convert_to_trapi=True, qgraph=qgraph)
    assert len(output["results"]) == 2


def test_any(db_driver):
    """Test any predicate."""
    qgraph = {
        "nodes": {
            "n0": {},
            "n1": {
                "ids": ["NCBIGene:836"]
            },
        },
        "edges": {
            "e10a": {
                "subject": "n1",
                "object": "n0",
            },
        },
    }
    dialect, driver = db_driver
    output = driver.run(get_query(qgraph, dialect=dialect), convert_to_trapi=True, qgraph=qgraph)
    assert len(output["results"]) == 4

def test_root_predicate(db_driver):
    """Test root/related_to predicate."""
    qgraph = {
        "nodes": {
            "n0": {},
            "n1": {
                "ids": ["NCBIGene:836"]
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
    dialect, driver = db_driver
    output = driver.run(get_query(qgraph, dialect=dialect), convert_to_trapi=True, qgraph=qgraph)
    assert len(output["results"]) == 4

def test_sub(db_driver):
    """Test sub predicate."""
    qgraph = {
        "nodes": {
            "n0": {
                "ids": ["MONDO:0004993"]
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
    dialect, driver = db_driver
    output = driver.run(get_query(qgraph,dialect=dialect), convert_to_trapi=True, qgraph=qgraph)
    assert len(output["results"]) == 2


def test_inverse(db_driver):
    """Test inverse predicate."""
    qgraph = {
        "nodes": {
            "n0": {
                "ids": ["NCBIGene:672"]
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
    dialect, driver = db_driver
    output = driver.run(get_query(qgraph,dialect=dialect), convert_to_trapi=True, qgraph=qgraph)
    assert len(output["results"]) == 1
