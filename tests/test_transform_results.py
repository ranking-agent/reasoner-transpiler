from .fixtures import fixture_neo4j_driver, fixture_neo4j_http_driver
from reasoner_transpiler.cypher import get_query


def test_bolt_driver_transform_results(neo4j_driver):
    qgraph = {
        "nodes": {
            "n0": {"ids": [
                "MONDO:0000001",
                "HP:0000118",
            ]},
            "n1": {},
        },
        "edges": {
            "e01": {
                "subject": "n0",
                "object": "n1",
            },
        },
    }
    output = neo4j_driver.run(get_query(qgraph), convert_to_trapi=True, qgraph=qgraph)
    assert len(output['results']) == 13
    for result in output["results"]:
        assert len(result["node_bindings"]) == 2
        assert len(result["analyses"]) == 1
    assert len(output['knowledge_graph']['nodes']) == 13
    assert len(output['auxiliary_graphs']) == 11


def test_http_driver_transform_results(neo4j_http_driver):
    qgraph = {
        "nodes": {
            "n0": {"ids": [
                "MONDO:0000001",
                "HP:0000118",
            ]},
            "n1": {},
        },
        "edges": {
            "e01": {
                "subject": "n0",
                "object": "n1",
            },
        },
    }
    output = neo4j_http_driver.run(get_query(qgraph), convert_to_trapi=True, qgraph=qgraph)
    assert len(output['results']) == 16
    for result in output["results"]:
        assert len(result["node_bindings"]) == 2
        assert len(result["analyses"]) == 1
    assert len(output['knowledge_graph']['nodes']) == 13
