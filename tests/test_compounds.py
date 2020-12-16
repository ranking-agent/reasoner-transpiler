"""Test Reasoner->Cypher transpiler."""
import pytest

from reasoner.cypher import get_query
from .fixtures import fixture_database


def test_multiedge_or_complicated(database):
    """Test parsing of compound qgraph."""
    qgraph = [
        'OR',
        {
            "nodes": {
                "n0": {},
                "n1a": {
                    "id": ["NCBIGene:836"]
                },
            },
            "edges": {
                "e10a": {
                    'subject': 'n0',
                    'object': 'n1a',
                    "predicate": "biolink:related_to",
                },
            },
        },
        {
            "nodes": {
                "n0": {},
                "n1b": {
                    "id": "NCBIGene:841"
                },
                "n2b": {
                    "id": "HP:0012592"
                },
            },
            "edges": {
                "e10b": {
                    'subject': 'n0',
                    'object': 'n1b',
                    "predicate": "biolink:related_to",
                },
                "e20b": {
                    'subject': 'n0',
                    'object': 'n2b',
                    "predicate": "biolink:has_phenotype",
                },
            },
        },
    ]
    output = database.run(get_query(qgraph))
    for record in output:
        assert len(record['results']) == 2
        results = sorted(
            record['knowledge_graph']['nodes'].values(),
            key=lambda node: node['name'],
        )
        expected_nodes = [
            "CASP3", "CASP8", 'albuminaria', 'obesity disorder',
            'type 2 diabetes mellitus',
        ]
        assert len(record['knowledge_graph']['nodes']) == 5
        for ind, node in enumerate(results):
            assert node['name'] == expected_nodes[ind]


def test_multiedge_or(database):
    """Test parsing of compound qgraph."""
    qgraph = [
        'AND',
        {
            "nodes": {
                "n0": {},
            },
            "edges": dict(),
        },
        [
            'OR',
            {
                "nodes": {
                    "n0": {},
                    "n1a": {
                        "id": ["NCBIGene:836"]
                    },
                },
                "edges": {
                    "e10a": {
                        'subject': 'n0',
                        'object': 'n1a',
                        "predicate": "biolink:related_to",
                    },
                },
            },
            {
                "nodes": {
                    "n0": {},
                    "n1b": {
                        "id": "NCBIGene:841"
                    },
                    "n2b": {
                        "id": "HP:0012592"
                    },
                },
                "edges": {
                    "e10b": {
                        'subject': 'n0',
                        'object': 'n1b',
                        "predicate": "biolink:related_to",
                    },
                    "e20b": {
                        'subject': 'n0',
                        'object': 'n2b',
                        "predicate": "biolink:has_phenotype",
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
            "CASP3", "CASP8", 'albuminaria', 'obesity disorder',
            'type 2 diabetes mellitus',
        ]
        assert len(record['knowledge_graph']['nodes']) == 5
        for ind, node in enumerate(results):
            assert node['name'] == expected_nodes[ind]


def test_or(database):
    """Test parsing of compound qgraph."""
    qgraph = [
        'AND',
        {
            "nodes": {
                "n0": {}
            },
            "edges": dict(),
        },
        [
            'OR',
            {
                "nodes": {
                    "n1a": {
                        "id": "NCBIGene:836"
                    },
                },
                "edges": {
                    "e10a": {
                        'subject': 'n0',
                        'object': 'n1a',
                        "predicate": "biolink:related_to",
                    },
                },
            },
            {
                "nodes": {
                    "n1b": {
                        "id": "NCBIGene:841"
                    },
                },
                "edges": {
                    "e10b": {
                        'subject': 'n0',
                        'object': 'n1b',
                        "predicate": "biolink:related_to",
                    },
                },
            },
            {
                "nodes": {
                    "n1c": {
                        "id": "MONDO:0005148"
                    },
                },
                "edges": {
                    "e10c": {
                        'subject': 'n1c',
                        'object': 'n0',
                        "predicate": "biolink:has_phenotype",
                    },
                },
            },
        ],
    ]
    output = database.run(get_query(qgraph))
    for record in output:
        assert len(record['results']) == 5
        results = sorted(
            record['knowledge_graph']['nodes'].values(),
            key=lambda node: node['name'],
        )
        expected_nodes = [
            "CASP3", "CASP8", 'albuminaria', 'carcinoma',
            'increased body weight', 'obesity disorder',
            'type 2 diabetes mellitus',
        ]
        assert len(record['knowledge_graph']['nodes']) == 7
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
                    "e02": {
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
        assert len(record['results']) == 2
        assert len(record['knowledge_graph']['nodes']) == 3


def test_not(database):
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
            "edges": {
                "e01": {
                    'subject': 'n0',
                    'object': 'n1',
                    "predicate": 'biolink:treats',
                },
            },
        },
        [
            'NOT',
            {
                'nodes': {
                    "n2": {
                        "category": [
                            'biolink:Disease',
                        ],
                        "id": "MONDO:0011122"
                    },
                },
                "edges": {
                    "e20": {
                        'subject': 'n0',
                        'object': 'n2',
                        "predicate": 'biolink:treats',
                    },
                },
            },
        ],
    ]
    output = database.run(get_query(qgraph))
    for record in output:
        results = sorted(
            record['knowledge_graph']['nodes'].values(),
            key=lambda node: node['name'],
        )
        expected_nodes = ['anagliptin', "type 2 diabetes mellitus"]
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
                    "category": 'biolink:Disease',
                },
                "n1": {
                    "category": 'biolink:ChemicalSubstance',
                    'id': 'CHEBI:6801',
                },
            },
            "edges": {
                "e01": {
                    'subject': 'n1',
                    'object': 'n0',
                    "predicate": 'biolink:treats',
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
                            "category": 'biolink:PhenotypicFeature',
                            "id": "HP:0012592",
                        },
                    },
                    "edges": {
                        "e20": {
                            'subject': 'n0',
                            'object': 'n2',
                            "predicate": 'biolink:has_phenotype',
                        },
                    },
                },
                {
                    "nodes": {
                        "n3": {
                            "category": 'biolink:Gene',
                            "id": "NCBIGene:672",
                        },
                    },
                    "edges": {
                        "e30": {
                            'subject': 'n0',
                            'object': 'n3',
                            "predicate": 'biolink:related_to',
                        },
                    },
                },
            ],
        ],
    ]
    output = dict(list(database.run(get_query(qgraph)))[0])
    assert len(output['results']) == 1
    results = sorted(
        output['knowledge_graph']['nodes'].values(),
        key=lambda node: node['name'],
    )
    expected_nodes = ['metformin', "obesity disorder"]
    for ind, node in enumerate(results):
        assert node['name'] == expected_nodes[ind]
