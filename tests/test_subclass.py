"""Test entity subclassing."""
from reasoner_transpiler.cypher import get_query
from .fixtures import fixture_database


def test_node_subclass(database):
    """Test node-only subclass query."""
    qgraph = {
        "nodes": {"n0": {"ids": ["MONDO:0000001"]}},
        "edges": dict(),
    }
    query = get_query(qgraph)
    output = list(database.run(query))[0]
    assert len(output['results']) == 2


def test_onehop_subclass(database):
    """Test one-hop subclass query."""
    qgraph = {
        "nodes": {
            "n0": {"ids": ["MONDO:0000001"]},
            "n1": {},
        },
        "edges": {
            "e01": {
                "subject": "n0",
                "object": "n1",
            },
        },
    }
    query = get_query(qgraph)
    output = list(database.run(query))[0]
    assert len(output['results']) == 9


def test_backward_subclass(database):
    """Test pinned-object one-hop subclass query."""
    qgraph = {
        "nodes": {
            "n0": {"ids": ["MONDO:0000001"]},
            "n1": {},
        },
        "edges": {
            "e01": {
                "subject": "n1",
                "object": "n0",
            },
        },
    }
    query = get_query(qgraph)
    output = list(database.run(query))[0]
    assert len(output['results']) == 9


def test_pinned_subclass(database):
    """Test both-pinned subclass query."""
    qgraph = {
        "nodes": {
            "n0": {"ids": ["MONDO:0000001"]},
            "n1": {"ids": ["HP:0000118"]},
        },
        "edges": {
            "e01": {
                "subject": "n0",
                "object": "n1",
            },
        },
    }
    query = get_query(qgraph)
    output = list(database.run(query))[0]
    assert len(output['results']) == 1


def test_same_pinned_subclass(database):
    """Test both-pinned subclass query."""
    qgraph = {
        "nodes": {
            "n0": {"ids": ["MONDO:0000001"]},
            "n1": {"ids": ["MONDO:0000001"]},
        },
        "edges": {
            "e01": {
                "subject": "n0",
                "object": "n1",
            },
        },
    }
    query = get_query(qgraph)
    output = list(database.run(query))[0]
    assert len(output['results']) == 2


def test_multihop_subclass(database):
    """Test multi-hop subclass query."""
    qgraph = {
        "nodes": {
            "n0": {"ids": ["MONDO:0000001"]},
            "n1": {},
            "n2": {},
        },
        "edges": {
            "e01": {
                "subject": "n0",
                "object": "n1",
            },
            "e12": {
                "subject": "n1",
                "object": "n2",
            },
        },
    }
    query = get_query(qgraph)
    output = list(database.run(query))[0]
    assert output['results']