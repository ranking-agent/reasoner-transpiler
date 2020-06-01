"""Test Reasoner->Cypher transpiler."""
import pytest

from reasoner.cypher import get_query
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


def test_compound():
    """Test parsing of compound qgraph."""
    qgraph = [
        'AND',
        {
            'nodes': [
                {
                    'id': 'n0',
                    'type': 'disease',
                    'curie': 'MONDO:0005015',
                },
            ],
            'edges': [],
        },
        [
            'OR',
            {
                'nodes': [
                    {
                        'id': 'n1',
                        'type': 'gene',
                    },
                    {
                        'id': 'n2',
                        'type': 'chemical_substance',
                    },
                ],
                'edges': [
                    {
                        'id': 'e10',
                        'source_id': 'n1',
                        'target_id': 'n0',
                        'type': 'gene_associated_with_condition',
                    },
                    {
                        'id': 'e21',
                        'source_id': 'n2',
                        'target_id': 'n1',
                        'type': 'decreases_activity_of',
                    },
                ],
            },
            {
                'nodes': [],
                'edges': [
                    {
                        'id': 'e20',
                        'source_id': 'n2',
                        'target_id': 'n0',
                        'type': 'treats',
                    },
                ],
            },
        ],
    ]
    print(get_query(qgraph))
