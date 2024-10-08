"""Test query arguments."""
import pytest
from reasoner_transpiler.cypher import get_query
from .fixtures import fixture_neo4j_driver


def test_skip_limit(neo4j_driver):
    """Test SKIP and LIMIT."""
    qgraph = {
        "nodes": {
            "n0": {
                "categories": "biolink:Disease",
                "ids": ["MONDO:0005148"],
            },
            "n1": {
                "categories": "biolink:ChemicalSubstance",
            },
        },
        "edges": {
            "e01": {
                "subject": "n1",
                "object": "n0",
                "predicates": "biolink:treats",
            },
        },
    }
    all_results = []
    with pytest.raises(NotImplementedError):
        output = neo4j_driver.run(get_query(qgraph, limit=2), convert_to_trapi=True, qgraph=qgraph)
    with pytest.raises(NotImplementedError):
        output = neo4j_driver.run(get_query(qgraph, skip=2), convert_to_trapi=True, qgraph=qgraph)

    """
    the following should pass if skip and limit are implemented
    output = neo4j_driver.run(get_query(qgraph, limit=2), convert_to_trapi=True, qgraph=qgraph)
    all_results.extend(output["results"])
    assert len(output["results"]) == 2
    output = neo4j_driver.run(get_query(qgraph, skip=2, limit=2), convert_to_trapi=True, qgraph=qgraph)
    all_results.extend(output["results"])
    assert len(output["results"]) == 1
    assert {
        "CHEBI:6801", "CHEBI:47612", "CHEBI:136043",
    } == set(
        result["node_bindings"]["n1"][0]["id"]
        for result in all_results
    )
    """


def test_max_connectivity(neo4j_driver):
    """Test max_connectivity option."""
    qgraph = {
        "nodes": {
            "n0": {
                "categories": "biolink:Disease",
            },
            "n1": {
                "categories": "biolink:ChemicalSubstance",
                "ids": ["CHEBI:6801"],
            },
        },
        "edges": {
            "e01": {
                "predicates": "biolink:treats",
                "subject": "n1",
                "object": "n0",
            },
        },
    }
    output = neo4j_driver.run(get_query(
        qgraph,
        max_connectivity=5,
    ), convert_to_trapi=True, qgraph=qgraph)
    assert len(output["results"]) == 2
    results = sorted(
        output["knowledge_graph"]["nodes"].values(),
        key=lambda node: node["name"],
    )
    expected_nodes = ["carcinoma", "metformin", "obesity disorder"]
    for ind, node in enumerate(results):
        assert node["name"] == expected_nodes[ind]


def test_use_hints():
    """Test unusual curie formats."""
    qgraph = {
        "nodes": {
            "n0": {
                "ids": [
                    ["NCBIGene:841"],
                ],
                "categories": "biolink:Gene",
            },
            "n1": {
            },
        },
        "edges": {
            "e01": {
                "predicates": [
                    "biolink:interacts_with",
                ],
                "subject": "n1",
                "object": "n0",
            },
        },
    }
    clause = get_query(qgraph, use_hints=True, reasoner=False)
    assert "USING INDEX" in clause

    clause = get_query(qgraph, use_hints=False, reasoner=False)
    assert "USING INDEX" not in clause
