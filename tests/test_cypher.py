"""Test Reasoner->Cypher transpiler."""
import pytest

from reasoner.cypher import get_query
from initialize_db import initialize_db


def test_skip_limit():
    """Test SKIP and LIMIT."""
    session = initialize_db()
    qgraph = {
        "nodes": [
            {
                "id": "n0",
                "type": "Group",
                "curie": "Fellowship",
            },
            {
                "id": "n1",
                "type": "Person",
            },
        ],
        "edges": [
            {
                "id": "e10",
                "source_id": "n1",
                "target_id": "n0",
                "type": "IS_MEMBER",
            },
        ],
    }
    all_results = []
    output = session.run(get_query(qgraph, limit=5))
    for record in output:
        all_results.extend(record['results'])
        assert len(record['results']) == 5
    output = session.run(get_query(qgraph, skip=5, limit=5))
    for record in output:
        all_results.extend(record['results'])
        assert len(record['results']) == 4
    session.close()
    assert {
        'Aragorn', 'Boromir', 'Frodo',
        'Gandalf', 'Gimli', 'Legolas',
        'Merry', 'Pippin', 'Sam',
    } == set(
        result['node_bindings'][1]['kg_id']
        for result in all_results
    )


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
    print(get_query(qgraph, reasoner=False))
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


def test_or():
    """Test parsing of compound qgraph."""
    qgraph = [
        'AND',
        {
            'nodes': [
                {
                    'id': 'n0',
                    'type': 'Group',
                    'curie': 'Fellowship',
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
                        'type': 'Person',
                    },
                    {
                        'id': 'n2',
                        'type': 'Person',
                    },
                ],
                'edges': [
                    {
                        'id': 'e10',
                        'source_id': 'n1',
                        'target_id': 'n0',
                        'type': 'IS_MEMBER',
                    },
                    {
                        'id': 'e21',
                        'source_id': 'n2',
                        'target_id': 'n1',
                        'type': 'IS_SIBLING',
                    },
                ],
            },
            {
                'nodes': [
                    {
                        'id': 'n1b',
                        'type': 'Person',
                    },
                    {
                        'id': 'n2',
                        'type': 'Person',
                    },
                ],
                'edges': [
                    {
                        'id': 'e10b',
                        'source_id': 'n1b',
                        'target_id': 'n0',
                        'type': 'IS_MEMBER',
                    },
                    {
                        'id': 'e21b',
                        'source_id': 'n2',
                        'target_id': 'n1b',
                        'type': 'IS_UNCLE',
                    },
                ],
            },
            {
                'nodes': [
                    {
                        'id': 'n2',
                        'type': 'Person',
                    },
                ],
                'edges': [
                    {
                        'id': 'e20',
                        'source_id': 'n2',
                        'target_id': 'n0',
                        'type': 'IS_MEMBER',
                    },
                ],
            },
        ],
    ]
    print(get_query(qgraph, reasoner=False))


def test_xor():
    """Test transpiling of compound qgraph."""
    qgraph = [
        'AND',
        {
            'nodes': [
                {
                    'id': 'n0',
                    'type': 'Person',
                },
                {
                    'id': 'n1',
                    'type': 'Group',
                    'curie': 'Fellowship',
                },
            ],
            'edges': [
                {
                    'id': 'e01',
                    'source_id': 'n0',
                    'target_id': 'n1',
                    'type': 'IS_MEMBER',
                },
            ],
        },
        [
            'XOR',
            {
                'nodes': [
                    {
                        'id': 'n2',
                        'type': 'Place',
                        'curie': 'Shire',
                    },
                ],
                'edges': [
                    {
                        'id': 'e02',
                        'source_id': 'n0',
                        'target_id': 'n2',
                        'type': 'LIVES_IN',
                    },
                ],
            },
            {
                'nodes': [
                    {
                        'id': 'n3',
                        'type': 'Weapon',
                        'subtype': 'sword',
                    },
                ],
                'edges': [
                    {
                        'id': 'e03',
                        'source_id': 'n0',
                        'target_id': 'n3',
                        'type': 'WIELDS',
                    },
                ],
            },
        ],
    ]
    print(get_query(qgraph, reasoner=False))


def test_not():
    """Test transpiling of compound qgraph."""
    qgraph = [
        'AND',
        {
            'nodes': [
                {
                    'id': 'n0',
                    'type': 'Person',
                },
                {
                    'id': 'n1',
                    'type': 'Group',
                    'curie': 'Fellowship',
                },
            ],
            'edges': [
                {
                    'id': 'e01',
                    'source_id': 'n0',
                    'target_id': 'n1',
                    'type': 'IS_MEMBER',
                },
            ],
        },
        [
            'NOT',
            {
                'nodes': [
                    {
                        'id': 'n2',
                    },
                ],
                'edges': [
                    {
                        'id': 'e20',
                        'source_id': 'n2',
                        'target_id': 'n0',
                        'type': 'KILLS',
                    },
                ],
            },
        ],
    ]
    print(get_query(qgraph, reasoner=False))
