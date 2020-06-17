"""Test query arguments."""
from reasoner.cypher import get_query
from fixtures import fixture_database


def test_skip_limit(database):
    """Test SKIP and LIMIT."""
    qgraph = {
        "nodes": [
            {
                "id": "n0",
                "type": "Group",
                "curie": "TGATE:Fellowship",
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
    output = database.run(get_query(qgraph, limit=5))
    for record in output:
        all_results.extend(record['results'])
        assert len(record['results']) == 5
    output = database.run(get_query(qgraph, skip=5, limit=5))
    for record in output:
        all_results.extend(record['results'])
        assert len(record['results']) == 4
    assert {
        'TGATE:Aragorn', 'TGATE:Boromir', 'TGATE:Frodo',
        'TGATE:Gandalf', 'TGATE:Gimli', 'TGATE:Legolas',
        'TGATE:Merry', 'TGATE:Pippin', 'TGATE:Sam',
    } == set(
        result['node_bindings'][1]['kg_id']
        for result in all_results
    )


def test_max_connectivity(database):
    """Test max_connectivity option."""
    qgraph = {
        "nodes": [
            {
                "id": "n0",
                "type": "Person",
            },
            {
                "id": "n1",
                "type": "Place",
                "curie": "TGATE:Shire",
            },
        ],
        "edges": [
            {
                "id": "e01",
                "type": "LIVES_IN",
                "source_id": "n0",
                "target_id": "n1",
            },
        ],
    }
    output = database.run(get_query(
        qgraph,
        max_connectivity=5,
    ))
    for record in output:
        assert len(record['results']) == 3
        results = sorted(record['knowledge_graph']['nodes'], key=lambda node: node['name'])
        expected_nodes = ['Merry', 'Pippin', 'Sam', 'Shire']
        for ind, node in enumerate(results):
            assert node['name'] == expected_nodes[ind]


def test_use_hints():
    """Test unusual curie formats."""
    qgraph = {
        "nodes": [
            {
                "id": "n0",
                "curie": [
                    "TGATE:Frodo",
                    "TGATE:Sam",
                    "TGATE:Merry",
                    "TGATE:Pippin",
                ],
                "type": "Person",
            },
            {
                "id": "n1",
                "type": "Place",
                "curie": 12,
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
    clause = get_query(qgraph, use_hints=True, reasoner=False)
    assert "USING INDEX" in clause
