"""Test query graph formats."""
import pytest

from reasoner.cypher import get_query
from initialize_db import initialize_db


def test_curie_formats():
    """Test unusual curie formats."""
    session = initialize_db()
    qgraph = {
        "nodes": [
            {
                "id": "n0",
                "curie": [
                    "Frodo",
                    "Sam",
                    "Merry",
                    "Pippin",
                ],
                "type": "Person",
            },
            {
                "id": "n1",
                "type": "Place",
            },
        ],
        "edges": [
            {
                "id": "e01",
                "type": [
                    "LIVES_IN",
                    "RULES",
                ],
                "source_id": "n0",
                "target_id": "n1",
            },
        ],
    }
    output = session.run(get_query(qgraph))
    for record in output:
        assert len(record['results']) == 4
        results = sorted(record['knowledge_graph']['nodes'], key=lambda node: node['name'])
        expected_nodes = ['Frodo', 'Merry', 'Pippin', 'Sam', 'Shire']
        for ind, result in enumerate(results):
            assert result['name'] == expected_nodes[ind]

    session.close()


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
        assert record['results'][0]['node_bindings'] == [{'kg_id': 'Sting', 'qg_id': 'n1'}, {'kg_id': 'Frodo', 'qg_id': 'n0'}, {'kg_id': 'Bilbo', 'qg_id': 'n2'}]
    session.close()


def test_single_edge_type_list():
    """Test that an edge with a edge type list of one works properly."""
    session = initialize_db()
    qgraph = {
        "nodes": [
            {
                "id": "n0",
                "type": "Person",
            },
            {
                "id": "n1",
                "type": "Weapon",
            },
        ],
        "edges": [
            {
                "id": "e0",
                "type": ["WIELDS"],
                "source_id": "n0",
                "target_id": "n1",
            },
        ],
    }
    clause = get_query(qgraph, reasoner=False)
    # edges with types should be directed
    assert "(`n0`:`Person`)-[`e0`:WIELDS]->(`n1`:`Weapon`)" in clause


def test_curie_int():
    """Test unusual curie formats."""
    qgraph = {
        "nodes": [
            {
                "id": "n0",
                "type": "Place",
                "curie": 12,
            },
        ],
        "edges": [],
    }
    clause = get_query(qgraph, reasoner=False)
    # the curie integer should be converted to a string
    assert clause == 'MATCH (`n0`:`Place` {`id`: "12"}) RETURN n0'
