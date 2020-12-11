"""Test transpiler edge cases."""
from reasoner.cypher import get_query
from .fixtures import fixture_database


def test_empty(database):
    """Test empty qgraph."""
    qgraph = {
        "nodes": dict(),
        "edges": dict(),
    }
    output = list(database.run(get_query(qgraph)))[0]
    assert len(output['results']) == 1
    assert output['results'][0]['node_bindings'] == dict()
    assert output['results'][0]['edge_bindings'] == dict()
    assert output['knowledge_graph']['nodes'] == []
    assert output['knowledge_graph']['edges'] == []


def test_type_none(database):
    """Test node with type None."""
    qgraph = {
        "nodes": {
            "n0": {
                "id": "MONDO:0005148",
                "category": None,
            }
        },
        "edges": dict(),
    }
    cypher = get_query(qgraph)
    output = list(database.run(cypher))[0]
    assert len(output['results']) == 1
