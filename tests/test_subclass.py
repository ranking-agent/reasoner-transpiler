"""Test entity subclassing."""
import copy
import pytest
import json
from reasoner_transpiler.cypher import get_query
from .fixtures import fixture_db_driver


def get_node_binding_ids_from_neo4j_driver_output(output):
    return [binding["id"] for result in output["results"]
            for binding_list in result["node_bindings"].values()
            for binding in binding_list]


def test_node_subclass(db_driver):
    """Test node-only subclass query."""
    # for queries without edges, we don't include subclasses of the query node or subclass edges
    qgraph = {
        "nodes": {"n0": {"ids": ["MONDO:0000001"]}},
        "edges": dict(),
    }
    original_qgraph = copy.deepcopy(qgraph)
    dialect, driver = db_driver
    query = get_query(qgraph, dialect=dialect)
    # assert qgraph != original_qgraph  # subclass queries should change the qgraph and add qnodes etc
    output = driver.run(query, convert_to_trapi=True, qgraph=qgraph)
    assert len(output['results']) == 1
    assert len(output['knowledge_graph']['nodes']) == 1
    assert len(output['knowledge_graph']['edges']) == 0

    node_binding_ids = get_node_binding_ids_from_neo4j_driver_output(output)
    assert 'MONDO:0015967' not in node_binding_ids
    assert 'MONDO:0005148' not in node_binding_ids

def jsort(j):
    """Sort JSON object."""
    isorted = json.loads(json.dumps(j, sort_keys=True))
    #This takes care of the dicts, but there's still potentially a list of dicts that needs to be sorted by the value of their id
    isorted["analyses"][0]["edge_bindings"]["e01"]=sorted(isorted["analyses"][0]["edge_bindings"]["e01"],key=lambda x:x["id"])
    return isorted

def test_onehop_subclass(db_driver):
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
    dialect, driver = db_driver
    output = driver.run(get_query(qgraph, dialect=dialect), convert_to_trapi=True, qgraph=qgraph)
    assert len(output['results']) == 12
    assert len(output['auxiliary_graphs']) == 11
    expected_result = jsort({'analyses': [{'edge_bindings': {'e01': [{'id': 't2d_invalid_predicate_albuminaria_t2d_isa_disease', 'attributes': []}, {'id': 't2d_has_phenotype_albuminaria_t2d_isa_disease', 'attributes': []}]}, 'resource_id': 'reasoner-transpiler'}], 'node_bindings': {'n0': [{'id': 'MONDO:0000001', 'attributes': []}], 'n1': [{'id': 'HP:0012592', 'attributes': []}]}})
    assert any(expected_result == jsort(result) for result in output['results'])
    assert 'aux_t2d_has_phenotype_albuminaria_t2d_isa_disease' in output['auxiliary_graphs']
    assert 't2d_has_phenotype_albuminaria_t2d_isa_disease' in output['knowledge_graph']['edges']
    assert {"attribute_type_id": "biolink:support_graphs", "value": ["aux_anagliptin_treats_t2d_t2d_isa_disease"]}\
           in output['knowledge_graph']['edges']['anagliptin_treats_t2d_t2d_isa_disease']['attributes']


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
    clause = query.split('WITH')[0]
    elements = clause.split('-')
    checked = False
    for element in elements:
        if '`n0`' in element:
            checked = True
            assert 'PhenotypicFeature' not in element
    assert checked


def test_backward_subclass(db_driver):
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
    dialect, driver = db_driver
    output = driver.run(get_query(qgraph, dialect=dialect), convert_to_trapi=True, qgraph=qgraph)
    assert len(output['results']) == 12
    assert len(output['auxiliary_graphs']) == 11


def test_pinned_subclass(db_driver):
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
    dialect, driver = db_driver
    output = driver.run(get_query(qgraph, dialect=dialect), convert_to_trapi=True, qgraph=qgraph)
    assert len(output['results']) == 1
    assert output["results"][0]["node_bindings"] == {
        "n0": [{"id": "MONDO:0000001", "attributes": []}],
        "n1": [{"id": "HP:0000118", "attributes": []}],
    }


def test_same_pinned_subclass(db_driver):
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
    dialect, driver = db_driver
    output = driver.run(get_query(qgraph, dialect=dialect), convert_to_trapi=True, qgraph=qgraph)
    assert len(output['results']) == 1
    assert len(output['knowledge_graph']['nodes']) == 3
    assert len(output['knowledge_graph']['edges']) == 4
    assert len(output['auxiliary_graphs']) == 2


def test_multihop_subclass(db_driver):
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
    dialect, driver = db_driver
    output = driver.run(get_query(qgraph, dialect=dialect), convert_to_trapi=True, qgraph=qgraph)
    assert len(output['results']) == 35


def test_dont_subclass(db_driver):
    """Test disallowing subclassing."""
    qgraph = {
        "nodes": {"n0": {"ids": ["MONDO:0000001"]}},
        "edges": dict(),
    }
    dialect, driver = db_driver
    output = driver.run(get_query(qgraph, dialect=dialect, subclass=False), convert_to_trapi=True, qgraph=qgraph)
    assert len(output['results']) == 1
    assert output["results"][0]["node_bindings"] == {
        "n0": [{"id": "MONDO:0000001", "attributes": []}],
    }


def test_batch_subclass(db_driver):
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
    dialect, driver = db_driver
    output = driver.run(get_query(qgraph, dialect=dialect), convert_to_trapi=True, qgraph=qgraph)
    assert len(output['results']) == 15
    for result in output["results"]:
        for binding in result["node_bindings"]["n0"]:
            assert binding["id"] in ["MONDO:0000001", "HP:0000118"]


def test_hierarchy_inference_on_superclass_queries(db_driver):
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
    dialect, driver = db_driver
    output = driver.run(get_query(qgraph, dialect=dialect), convert_to_trapi=True, qgraph=qgraph)
    assert len(output['results']) == 2
    node_binding_ids = get_node_binding_ids_from_neo4j_driver_output(output)
    assert "MONDO:0000001" in node_binding_ids
    assert "MONDO:0005148" in node_binding_ids
    assert "MONDO:0015967" in node_binding_ids
    # note that for graphs where redundant subclass edges are added results would show MONDO:0000001 as a superclass
    # of MONDO:0014488, but because that explicit edge is not included in the test data MONDO:0014488 is excluded from
    # the results, as it's a subclass of a subclass of MONDO:0000001
    assert "MONDO:0014488" not in node_binding_ids


def test_hierarchy_inference_on_subclass_queries(db_driver):
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
    dialect, driver = db_driver
    output = driver.run(get_query(qgraph, dialect=dialect), convert_to_trapi=True, qgraph=qgraph)
    assert len(output['results']) == 1
    node_binding_ids = [binding["id"] for binding_list in output["results"][0]["node_bindings"].values() for binding in
                        binding_list]
    assert "MONDO:0000001" in node_binding_ids
    assert "MONDO:0005148" in node_binding_ids
    assert "MONDO:0014488" not in node_binding_ids


def test_subclass_depth_default(db_driver):
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
    dialect, driver = db_driver
    output = driver.run(get_query(qgraph, dialect=dialect), convert_to_trapi=True, qgraph=qgraph)
    assert len(output['results']) == 0


def test_subclass_depth_2(db_driver):
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
    dialect, driver = db_driver
    output = driver.run(get_query(qgraph, subclass_depth=2, dialect=dialect), convert_to_trapi=True, qgraph=qgraph)
    assert len(output['results']) == 1


def test_inverse_predicate_subclass(db_driver):
    """Test that subclass inference works correctly with non-canonical (inverse) predicates.

    Querying with phenotype_of (inverse of has_phenotype) and a pinned phenotype node
    should produce an inferred edge with the correct subject/object orientation.
    The stored edge is: MONDO:0005148 -[has_phenotype]-> HP:0012592
    The subclass edge is: HP:0012592 -[subclass_of]-> HP:0000118
    The inferred edge should be: MONDO:0005148 -[has_phenotype]-> HP:0000118
    """
    qgraph = {
        "nodes": {
            "n0": {"ids": ["HP:0000118"], "categories": ["biolink:PhenotypicFeature"]},
            "n1": {},
        },
        "edges": {
            "e01": {
                "subject": "n0",
                "object": "n1",
                "predicates": ["biolink:phenotype_of"],
            },
        },
    }
    dialect, driver = db_driverok care
    output = driver.run(get_query(qgraph, dialect=dialect), convert_to_trapi=True, qgraph=qgraph)
    assert len(output['results']) > 0
    assert len(output['auxiliary_graphs']) > 0

    # Check expected node bindings: n0=HP:0000118 (pinned phenotype), n1=MONDO:0005148 (disease)
    result_n1_ids = {result['node_bindings']['n1'][0]['id'] for result in output['results']}
    assert 'MONDO:0005148' in result_n1_ids
    for result in output['results']:
        assert result['node_bindings']['n0'][0]['id'] == 'HP:0000118'

    # Check the inferred edge has the expected subject and object:
    # MONDO:0005148 -[has_phenotype]-> HP:0000118
    for edge_id, edge in output['knowledge_graph']['edges'].items():
        if 'attributes' in edge and any(
            attr.get('attribute_type_id') == 'biolink:knowledge_level' and attr.get('value') == 'logical_entailment'
            for attr in edge['attributes']
        ):
            assert edge['subject'] != 'HP:0000118', \
                f"Inferred edge {edge_id} has superclass phenotype as subject - subject/object are swapped"
            assert edge['object'] == 'HP:0000118', \
                f"Inferred edge {edge_id} should have HP:0000118 (queried phenotype) as object"

    # Verify node bindings are consistent with inferred edges
    # The qedge is n0 -[phenotype_of]-> n1, but canonical direction is has_phenotype,
    # so the real edge subject should be n1's binding and object should be n0's binding
    for result in output['results']:
        n0_id = result['node_bindings']['n0'][0]['id']
        n1_id = result['node_bindings']['n1'][0]['id']
        for edge_binding in result['analyses'][0]['edge_bindings']['e01']:
            bound_edge = output['knowledge_graph']['edges'][edge_binding['id']]
            assert bound_edge['subject'] == n1_id, \
                f"Edge {edge_binding['id']} subject is {bound_edge['subject']}, expected {n1_id}"
            assert bound_edge['object'] == n0_id, \
                f"Edge {edge_binding['id']} object is {bound_edge['object']}, expected {n0_id}"


def test_invalid_subclass_depth(db_driver):
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
    dialect, driver = db_driver
    with pytest.raises(TypeError):
        query = get_query(qgraph, subclass_depth="bad_value_type", dialect=dialect)
    with pytest.raises(ValueError):
        query = get_query(qgraph, subclass_depth=-1, dialect=dialect)
