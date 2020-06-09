"""Test Reasoner->Cypher transpiler."""
import pytest

from reasoner.cypher import get_query
from fixtures import fixture_database


def test_and(database):
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
            'edges': [],
        },
        {
            'nodes': [],
            'edges': [
                {
                    'id': 'e01',
                    'source_id': 'n0',
                    'target_id': 'n1',
                    'type': 'IS_MEMBER',
                },
            ],
        },
    ]
    output = database.run(get_query(qgraph))
    for record in output:
        # 9 for the members, 1 for the Fellowship node
        assert len(record['knowledge_graph']['nodes']) == 10


def test_or(database):
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
    output = database.run(get_query(qgraph))
    for record in output:
        assert len(record['results']) == 11
        results = sorted(record['knowledge_graph']['nodes'], key=lambda node: node['name'])
        expected_nodes = [
            'Aragorn', 'Bilbo', 'Boromir', 'Faramir', 'Fellowship', 'Frodo', 'Gandalf',
            'Gimli', 'Legolas', 'Merry', 'Pippin', 'Sam'
        ]
        assert len(record['knowledge_graph']['nodes']) == 12
        for ind, node in enumerate(results):
            assert node['name'] == expected_nodes[ind]


def test_xor(database):
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
    output = database.run(get_query(qgraph))
    for record in output:
        assert len(record['results']) == 5
        assert len(record['knowledge_graph']['nodes']) == 9


def test_not(database):
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
                        'type': [
                            'Creature',
                            'Group',
                            'Person',
                        ],
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
    output = database.run(get_query(qgraph))
    for record in output:
        results = sorted(record['knowledge_graph']['nodes'], key=lambda node: node['name'])
        expected_nodes = ['Aragorn', 'Boromir', 'Fellowship', 'Frodo', 'Gandalf', 'Gimli', 'Legolas', 'Merry', 'Pippin', 'Sam']
        for ind, node in enumerate(results):
            assert node['name'] == expected_nodes[ind]


def test_multiple_conditions(database):
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
                        'type': [
                            'Group',
                        ],
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
        [
            'NOT',
            {
                'nodes': [
                    {
                        'id': 'n3',
                        'type': 'Weapon',
                    },
                ],
                'edges': [
                    {
                        'id': 'e30',
                        'source_id': 'n0',
                        'target_id': 'n3',
                        'type': ['WIELDS'],
                    },
                ],
            },
        ],
    ]
    output = database.run(get_query(qgraph))
    for record in output:
        results = sorted(record['knowledge_graph']['nodes'], key=lambda node: node['name'])
        expected_nodes = ['Fellowship', 'Merry', 'Pippin', 'Sam']
        for ind, node in enumerate(results):
            assert node['name'] == expected_nodes[ind]


def test_not_or(database):
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
            [
                'OR',
                {
                    'nodes': [
                        {
                            'id': 'n2',
                            'type': 'Group',
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
                {
                    'nodes': [
                        {
                            'id': 'n3',
                            'type': 'Creature',
                        },
                    ],
                    'edges': [
                        {
                            'id': 'e30',
                            'source_id': 'n3',
                            'target_id': 'n0',
                            'type': 'KILLS',
                        },
                    ],
                },
                {
                    'nodes': [
                        {
                            'id': 'n4',
                            'type': 'Person',
                        },
                    ],
                    'edges': [
                        {
                            'id': 'e40',
                            'source_id': 'n4',
                            'target_id': 'n0',
                            'type': 'KILLS',
                        },
                    ],
                },
            ],
        ],
    ]
    output = dict(list(database.run(get_query(qgraph)))[0])
    assert len(output['results']) == 7
    results = sorted(output['knowledge_graph']['nodes'], key=lambda node: node['name'])
    expected_nodes = ['Aragorn', 'Fellowship', 'Frodo', 'Gimli', 'Legolas', 'Merry', 'Pippin', 'Sam']
    for ind, node in enumerate(results):
        assert node['name'] == expected_nodes[ind]
