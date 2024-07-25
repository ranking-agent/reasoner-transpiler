"""Test entity subclassing."""
import copy
import pytest
from reasoner_transpiler.cypher import get_query
from .fixtures import fixture_neo4j_driver


def get_node_binding_ids_from_neo4j_driver_output(output):
    return [binding["id"] for result in output["results"]
            for binding_list in result["node_bindings"].values()
            for binding in binding_list]


def test_node_subclass(neo4j_driver):
    """Test node-only subclass query."""
    qgraph = {
        "nodes": {"n0": {"ids": ["MONDO:0000001"]}},
        "edges": dict(),
    }
    original_qgraph = copy.deepcopy(qgraph)
    query = get_query(qgraph)
    assert qgraph != original_qgraph  # subclass queries should change the qgraph and add qnodes etc
    output = neo4j_driver.run(get_query(qgraph), convert_to_trapi=True, qgraph=qgraph)
    assert len(output['results']) == 3
    node_binding_ids = get_node_binding_ids_from_neo4j_driver_output(output)
    assert 'MONDO:0015967' in node_binding_ids
    assert any(
        result["node_bindings"]["n0"] == [{"id": "MONDO:0005148", "query_id": "MONDO:0000001"}]
        for result in output["results"]
    )


def test_onehop_subclass(neo4j_driver):
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
    output = neo4j_driver.run(get_query(qgraph), convert_to_trapi=True, qgraph=qgraph)
    assert len(output['results']) == 13


def test_onehop_subclass_categories():
    """Test one-hop subclass query."""
    qgraph = {
        "nodes": {
            "n0": {"ids": ["HP:0011015"], "categories": ["biolink:PhenotypicFeature"]},
            "n1": {},
        },
        "edges": {
            "e01": {
                "subject": "n1",
                "object": "n0",
                "predicates": ["biolink:treats"]
            },
        },
    }
    query = get_query(qgraph)
    #make sure that the class (PhenotypicFeature) has been removed from n0
    clause = query.split('RETURN')[0]
    elements = clause.split('-')
    checked = False
    for element in elements:
        if '`n0`' in element:
            checked = True
            assert 'PhenotypicFeature' not in element
    assert checked


def test_backward_subclass(neo4j_driver):
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
    output = neo4j_driver.run(get_query(qgraph), convert_to_trapi=True, qgraph=qgraph)
    assert len(output['results']) == 13


def test_pinned_subclass(neo4j_driver):
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
    output = neo4j_driver.run(get_query(qgraph), convert_to_trapi=True, qgraph=qgraph)
    # assert len(output['results']) == 1
    assert output["results"][0]["node_bindings"] == {
        "n0": [{"id": "MONDO:0005148", "query_id": "MONDO:0000001"}],
        "n1": [{"id": "HP:0012592", "query_id": "HP:0000118"}],
    }


def test_same_pinned_subclass(neo4j_driver):
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
    output = neo4j_driver.run(get_query(qgraph), convert_to_trapi=True, qgraph=qgraph)
    assert len(output['results']) == 4


def test_multihop_subclass(neo4j_driver):
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
    output = neo4j_driver.run(get_query(qgraph), convert_to_trapi=True, qgraph=qgraph)
    assert output['results']


def test_dont_subclass(neo4j_driver):
    """Test disallowing subclassing."""
    qgraph = {
        "nodes": {"n0": {"ids": ["MONDO:0000001"]}},
        "edges": dict(),
    }
    output = neo4j_driver.run(get_query(qgraph, subclass=False), convert_to_trapi=True, qgraph=qgraph)
    assert len(output['results']) == 1
    assert output["results"][0]["node_bindings"] == {
        "n0": [{"id": "MONDO:0000001"}],
    }


def test_batch_subclass(neo4j_driver):
    """Test batched subclass query."""
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
    assert len(output['results']) == 16
    for result in output["results"]:
        for binding in result["node_bindings"]["n0"]:
            assert "query_id" in binding
            assert (binding["query_id"] == "HP:0000118") if binding["id"].startswith("HP") else (binding["query_id"] == "MONDO:0000001")


def test_hierarchy_inference_on_superclass_queries(neo4j_driver):
    """ Test that subclass edges should not be added to explicit subclass/superclass predicate queries  """
    qgraph = {
        "nodes": {"n0": {"ids": ["MONDO:0000001"]},
                  "n1": {}},
        "edges": {
            "e01": {
                "subject": "n0",
                "object": "n1",
                "predicates": ['biolink:superclass_of']
            },
        }
    }
    output = neo4j_driver.run(get_query(qgraph), convert_to_trapi=True, qgraph=qgraph)
    assert len(output['results']) == 2
    node_binding_ids = get_node_binding_ids_from_neo4j_driver_output(output)
    assert "MONDO:0000001" in node_binding_ids
    assert "MONDO:0005148" in node_binding_ids
    assert "MONDO:0015967" in node_binding_ids
    # note that for graphs where redundant subclass edges are added results would show MONDO:0000001 as a superclass
    # of MONDO:0014488, but because that explicit edge is not included in the test data MONDO:0014488 is excluded from
    # the results, as it's a subclass of a subclass of MONDO:0000001
    assert "MONDO:0014488" not in node_binding_ids


def test_hierarchy_inference_on_subclass_queries(neo4j_driver):
    qgraph = {
        "nodes": {"n0": {"ids": ["MONDO:0005148"]},
                  "n1": {}},
        "edges": {
            "e01": {
                "subject": "n0",
                "object": "n1",
                "predicates": ['biolink:subclass_of']
            },
        }
    }
    output = neo4j_driver.run(get_query(qgraph), convert_to_trapi=True, qgraph=qgraph)
    assert len(output['results']) == 1
    node_binding_ids = [binding["id"] for binding_list in output["results"][0]["node_bindings"].values() for binding in
                        binding_list]
    assert "MONDO:0000001" in node_binding_ids
    assert "MONDO:0005148" in node_binding_ids
    assert "MONDO:0014488" not in node_binding_ids


def test_subclass_depth_default(neo4j_driver):
    """Test one-hop subclass query."""
    qgraph = {
        "nodes": {"n0": {"ids": ["CHEBI:136043"]},
                  "n1": {"ids": ["MONDO:0000000"]}},
        "edges": {
            "e01": {
                "subject": "n0",
                "object": "n1",
                "predicates": ['biolink:treats']
            },
        }
    }
    output = neo4j_driver.run(get_query(qgraph), convert_to_trapi=True, qgraph=qgraph)
    assert len(output['results']) == 0


def test_subclass_depth_2(neo4j_driver):
    """Test one-hop subclass query."""
    qgraph = {
        "nodes": {"n0": {"ids": ["CHEBI:136043"]},
                  "n1": {"ids": ["MONDO:0000000"]}},
        "edges": {
            "e01": {
                "subject": "n0",
                "object": "n1",
                "predicates": ['biolink:treats']
            },
        }
    }
    output = neo4j_driver.run(get_query(qgraph, subclass_depth=2), convert_to_trapi=True, qgraph=qgraph)
    assert len(output['results']) == 1


def test_invalid_subclass_depth(neo4j_driver):
    qgraph = {
        "nodes": {"n0": {"ids": ["CHEBI:136043"]},
                  "n1": {"ids": ["MONDO:0000000"]}},
        "edges": {
            "e01": {
                "subject": "n0",
                "object": "n1",
                "predicates": ['biolink:treats']
            },
        }
    }
    with pytest.raises(TypeError):
        query = get_query(qgraph, subclass_depth="bad_value_type")
    with pytest.raises(ValueError):
        query = get_query(qgraph, subclass_depth=-1)
