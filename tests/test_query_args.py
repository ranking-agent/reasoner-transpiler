"""Test query arguments."""
from reasoner.cypher import get_query
from .fixtures import fixture_database


def test_skip_limit(database):
    """Test SKIP and LIMIT."""
    qgraph = {
        "nodes": {
            "n0": {
                "category": "biolink:Disease",
                "id": "MONDO:0005148",
            },
            "n1": {
                "category": "biolink:ChemicalSubstance",
            },
        },
        "edges": {
            "e01": {
                "subject": "n1",
                "object": "n0",
                "predicate": "biolink:treats",
            },
        },
    }
    all_results = []
    output = database.run(get_query(qgraph, limit=2))
    for record in output:
        all_results.extend(record["results"])
        assert len(record["results"]) == 2
    output = database.run(get_query(qgraph, skip=2, limit=2))
    for record in output:
        all_results.extend(record["results"])
        assert len(record["results"]) == 1
    assert {
        "CHEBI:6801", "CHEBI:47612", "CHEBI:136043",
    } == set(
        result["node_bindings"]["n1"][0]["id"]
        for result in all_results
    )


def test_max_connectivity(database):
    """Test max_connectivity option."""
    qgraph = {
        "nodes": {
            "n0": {
                "category": "biolink:Disease",
            },
            "n1": {
                "category": "biolink:ChemicalSubstance",
                "id": "CHEBI:6801",
            },
        },
        "edges": {
            "e01": {
                "predicate": "biolink:treats",
                "subject": "n1",
                "object": "n0",
            },
        },
    }
    output = database.run(get_query(
        qgraph,
        max_connectivity=5,
    ))
    for record in output:
        assert len(record["results"]) == 2
        results = sorted(
            record["knowledge_graph"]["nodes"].values(),
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
                "id": [
                    "NCBIGene:841",
                ],
                "category": "biolink:Gene",
            },
            "n1": {
            },
        },
        "edges": {
            "e01": {
                "predicate": [
                    "biolink:molecularly_interacts_with",
                    "biolink:increases_expression_of",
                ],
                "subject": "n1",
                "object": "n0",
            },
        },
    }
    clause = get_query(qgraph, use_hints=True, reasoner=False)
    assert "USING INDEX" in clause
