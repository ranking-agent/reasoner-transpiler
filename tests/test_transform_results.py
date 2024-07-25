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
    print(get_query(qgraph))
    output = neo4j_driver.run(get_query(qgraph), convert_to_trapi=True, qgraph=qgraph)
    assert len(output['results']) == 16
    for result in output["results"]:
        for binding in result["node_bindings"]["n0"]:
            assert "query_id" in binding
            assert (binding["query_id"] == "HP:0000118") if binding["id"].startswith("HP") else (binding["query_id"] == "MONDO:0000001")


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
    print(get_query(qgraph))
    output = neo4j_http_driver.run(get_query(qgraph), convert_to_trapi=True, qgraph=qgraph)
    assert len(output['results']) == 16
    for result in output["results"]:
        for binding in result["node_bindings"]["n0"]:
            assert "query_id" in binding
            assert (binding["query_id"] == "HP:0000118") if binding["id"].startswith("HP") else (binding["query_id"] == "MONDO:0000001")
