"""Test Reasoner->Cypher transpiler."""
import pytest

from reasoner.cypher import get_query, get_match_clause
from initialize_db import initialize_db


def test_complex_query():
    """Test that db get's initialized successfully."""
    session = initialize_db()
    qgraph = {
        "nodes": [
            {
                "id": "n1",
                "type": "Weapon",
            },
            {
                "id": "n0",
                "curie": "Frodo",
                "type": "Person",
                "gender": "male",
                "occurences": 2040,
            },
            {
                "id": "n2",
                "type": "Person",
                "curie": [
                    "Bilbo",
                ],
                "good": True
            },
        ],
        "edges": [
            {
                "id": "e02",
                "source_id": "n0",
                "target_id": "n2",
            },
            {
                "id": "e01",
                "source_id": "n0",
                "target_id": "n1",
                "type": "INHERITS",
            },
            {
                "id": "e21",
                "source_id": "n2",
                "target_id": "n1",
                "type": [
                    "WIELDS",
                    "FINDS",
                ],
            }
        ],
    }
    output = session.run(get_query(qgraph))
    for record in output:
        assert len(record['results']) == 1
        assert record['results'][0]['node_bindings'], [{'kg_id': 'Sting', 'qg_id': 'n1'}, {'kg_id': 'Frodo', 'qg_id': 'n0'}, {'kg_id': 'Bilbo', 'qg_id': 'n2'}]
    session.close()


def test_invalid_node():
    """Test that an invalid node property value throws an error."""
    qgraph = {
        "nodes": [
            {
                "id": "n0",
                "type": "Thing",
                "dict": {"a": 1},
            },
        ],
        "edges": [],
    }
    with pytest.raises(ValueError):
        get_query(qgraph)


def test_query_limit():
    """Test query limit property."""
    session = initialize_db()
    qgraph = {
        "nodes": [
            {
                "id": "n1",
                "type": "Place",
            },
        ],
        "edges": [],
    }
    clause = get_query(
        qgraph,
        limit=3,
    )
    print(clause)
    output = session.run(clause)
    for record in output:
        print(record)


# clause = get_query(qgraph, max_connectivity=3, relationship_id='internal', skip=2, limit=10)
