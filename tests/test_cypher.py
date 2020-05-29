"""Test Reasoner->Cypher transpiler."""
import pytest

from reasoner.cypher import get_query, get_match_clause
from initialize_db import initialize_db


def test_db_initialize():
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
        print(record)
        assert len(record['results']) == 1
        print(record['results'])
        assert record['results'][0]['node_bindings'], [{'kg_id': 'Sting', 'qg_id': 'n1'}, {'kg_id': 'Frodo', 'qg_id': 'n0'}, {'kg_id': 'Bilbo', 'qg_id': 'n2'}]
    session.close()


def test_match():
    """Test MATCH clause generation."""
    qgraph = {
        "nodes": [
            {
                "id": "n0",
                "curie": [
                    "Frodo",
                    "Sam",
                ],
                "type": "Person",
            },
            {
                "id": "n1",
                "curie": {
                    "Frodo",
                    "Sam",
                },
                "type": "Person",
            },
        ],
        "edges": [],
    }
    clause = get_match_clause(qgraph)
    print(clause)
    # assert get_match_clause(qgraph) == "MATCH (`n0`:`Person` {}) USING INDEX `n0`:Person(id) WHERE `n0`.id = \"Frodo\" OR `n0`.id = \"Sam\" MATCH (`n1`:`Person` {`id`: \"{'Frodo', 'Sam'}\"}) USING INDEX `n1`:Person(id)"


def test_query():
    """Test full query generation."""
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
    clause = get_query(
        qgraph,
    )
    print(clause)
    clause = get_query(
        qgraph,
        max_connectivity=3,
        relationship_id='internal',
        skip=2,
        limit=10,
    )
    print(clause)

    qgraph['nodes'][0]['dict'] = {'a': 1}
    with pytest.raises(ValueError):
        get_query(qgraph)
