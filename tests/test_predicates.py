"""Test predicate handling."""
import pytest

from reasoner.cypher import get_query
from .fixtures import fixture_database


def test_symmetric(database):
    """Test symmetric predicate."""
    qgraph = {
        "nodes": {
            "n0": {},
            "n1": {
                "id": "NCBIGene:836"
            },
        },
        "edges": {
            "e10a": {
                'subject': 'n1',
                'object': 'n0',
                "predicate": "biolink:genetic_association",
            },
        },
    }
    output = database.run(get_query(qgraph))
    for record in output:
        assert len(record['results']) == 2


def test_any(database):
    """Test any predicate."""
    qgraph = {
        "nodes": {
            "n0": {},
            "n1": {
                "id": "NCBIGene:836"
            },
        },
        "edges": {
            "e10a": {
                'subject': 'n1',
                'object': 'n0',
            },
        },
    }
    output = database.run(get_query(qgraph))
    for record in output:
        assert len(record['results']) == 4
