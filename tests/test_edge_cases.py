"""Test transpiler edge cases."""
from reasoner.cypher import get_query
from fixtures import fixture_database


def test_empty(database):
    """Test empty qgraph."""
    qgraph = {
        'nodes': [],
        'edges': [],
    }
    output = list(database.run(get_query(qgraph)))[0]
    assert len(output['results']) == 1
    assert output['results'][0]['node_bindings'] == []
    assert output['results'][0]['edge_bindings'] == []
    assert output['knowledge_graph']['nodes'] == []
    assert output['knowledge_graph']['edges'] == []
