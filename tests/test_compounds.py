"""Test Reasoner->Cypher transpiler."""
import pytest

from reasoner.cypher import get_query
from .fixtures import fixture_database


def test_and(database):
    """Test transpiling of compound qgraph."""
    qgraph = [
        'AND',
        {
            "nodes": {
                "n0": {
                    "category": 'biolink:ChemicalSubstance',
                },
                "n1": {
                    "category": 'biolink:Disease',
                    'id': 'MONDO:0005148',
                },
            },
            "edges": dict(),
        },
        {
            "nodes": dict(),
            "edges": {
                "e01": {
                    'subject': 'n0',
                    'object': 'n1',
                    "predicate": 'biolink:treats',
                },
            },
        },
    ]
    output = database.run(get_query(qgraph))
    for record in output:
        assert len(record['knowledge_graph']['nodes']) == 4


def test_or(database):
    """Test parsing of compound qgraph."""
    qgraph = [
        'AND',
        {
            "nodes": {
                "n0": {
                    "category": 'biolink:Disease',
                    'id': 'MONDO:0005148',
                },
                "n2": {
                    "category": 'biolink:Disease',
                    "id": "MONDO:0011122"
                },
            },
            "edges": dict(),
        },
        [
            'OR',
            {
                "nodes": {
                    "n1": {
                        "category": 'biolink:ChemicalSubstance',
                    },
                },
                "edges": {
                    "e10": {
                        'subject': 'n1',
                        'object': 'n0',
                        "predicate": 'biolink:treats',
                    },
                    "e21": {
                        'subject': 'n1',
                        'object': 'n2',
                        "predicate": 'biolink:treats',
                    },
                },
            },
            {
                "nodes": {
                    "n1b": {
                        "category": 'biolink:PhenotypicFeature',
                    },
                },
                "edges": {
                    "e10b": {
                        'subject': 'n0',
                        'object': 'n1b',
                        "predicate": 'biolink:has_phenotype',
                    },
                    "e21b": {
                        'subject': 'n2',
                        'object': 'n1b',
                        "predicate": 'biolink:has_phenotype',
                    },
                },
            },
        ],
    ]
    output = database.run(get_query(qgraph))
    for record in output:
        assert len(record['results']) == 2
        results = sorted(
            record['knowledge_graph']['nodes'].values(),
            key=lambda node: node['name'],
        )
        expected_nodes = [
            'bezafibrate', 'increased body weight', 'metformin',
            'obesity disorder', 'type 2 diabetes mellitus',
        ]
        assert len(record['knowledge_graph']['nodes']) == 5
        for ind, node in enumerate(results):
            assert node['name'] == expected_nodes[ind]


def test_xor(database):
    """Test transpiling of compound qgraph."""
    qgraph = [
        'AND',
        {
            "nodes": {
                "n0": {
                    "category": 'biolink:Disease',
                },
            },
            "edges": {},
        },
        [
            'XOR',
            {
                "nodes": {
                    "n1": {
                        "category": "biolink:ChemicalSubstance",
                        "id": "CHEBI:6801",
                    }
                },
                "edges": {
                    "e01": {
                        'subject': 'n1',
                        'object': 'n0',
                        "predicate": 'biolink:treats',
                    },
                },
            },
            {
                "nodes": {
                    "n2": {
                        "category": "biolink:ChemicalSubstance",
                        "id": "CHEBI:136043",
                    }
                },
                "edges": {
                    "e01": {
                        'subject': 'n2',
                        'object': 'n0',
                        "predicate": 'biolink:treats',
                    },
                },
            },
        ],
    ]
    output = database.run(get_query(qgraph))
    for record in output:
        assert len(record['results']) == 1
        assert len(record['knowledge_graph']['nodes']) == 2


def test_not(database):
    """Test transpiling of compound qgraph."""
    qgraph = [
        'AND',
        {
            "nodes": {
                "n0": {
                    "category": 'Person',
                },
                "n1": {
                    "category": 'Group',
                    'curie': 'TGATE:Fellowship',
                },
            },
            "edges": {
                "e01": {
                    'subject': 'n0',
                    'object': 'n1',
                    "predicate": 'IS_MEMBER',
                },
            },
        },
        [
            'NOT',
            {
                'nodes': {
                    "n2": {
                        "category": [
                            'Creature',
                            'Group',
                            'Person',
                        ],
                    },
                },
                "edges": {
                    "e20": {
                        'subject': 'n2',
                        'object': 'n0',
                        "predicate": 'KILLS',
                    },
                },
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
            "nodes": {
                "n0": {
                    "category": 'Person',
                },
                "n1": {
                    "category": 'Group',
                    'curie': 'TGATE:Fellowship',
                },
            },
            "edges": {
                "e01": {
                    'subject': 'n0',
                    'object': 'n1',
                    "predicate": 'IS_MEMBER',
                },
            },
        },
        [
            'NOT',
            {
                'nodes': {
                    "n2": {
                        "category": [
                            'Group',
                        ],
                    },
                },
                "edges": {
                    "e20": {
                        'subject': 'n2',
                        'object': 'n0',
                        "predicate": 'KILLS',
                    },
                },
            },
        ],
        [
            'NOT',
            {
                "nodes": {
                    "n3": {
                        "category": 'Weapon',
                    },
                },
                'edges': {
                    "e30": {
                        'subject': 'n0',
                        'object': 'n3',
                        "predicate": ['WIELDS'],
                    },
                },
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
            "nodes": {
                "n0": {
                    "category": 'Person',
                },
                "n1": {
                    "category": 'Group',
                    'curie': 'TGATE:Fellowship',
                },
            },
            "edges": {
                "e01": {
                    'subject': 'n0',
                    'object': 'n1',
                    "predicate": 'IS_MEMBER',
                },
            },
        },
        [
            'NOT',
            [
                'OR',
                {
                    "nodes": {
                        "n2": {
                            "category": 'Group',
                        },
                    },
                    "edges": {
                        "e20": {
                            'subject': 'n2',
                            'object': 'n0',
                            "predicate": 'KILLS',
                        },
                    },
                },
                {
                    "nodes": {
                        "n3": {
                            "category": 'Creature',
                        },
                    },
                    "edges": {
                        "e30": {
                            'subject': 'n3',
                            'object': 'n0',
                            "predicate": 'KILLS',
                        },
                    },
                },
                {
                    "nodes": {
                        "n4": {
                            "category": 'Person',
                        },
                    },
                    "edges": {
                        "e40": {
                            'subject': 'n4',
                            'object': 'n0',
                            "predicate": 'KILLS',
                        },
                    },
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
