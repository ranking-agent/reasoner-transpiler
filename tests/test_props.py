"""Test querying with properties."""
import pytest
from .fixtures import fixture_neo4j_driver
from reasoner_transpiler.attributes import set_custom_attribute_types, set_custom_attribute_skip_list, \
    reset_custom_attribute_types, DEFAULT_ATTRIBUTE_TYPE
from reasoner_transpiler.cypher import get_query


def test_numeric(neo4j_driver):
    """Test querying with numeric property."""
    qgraph = {
        "nodes": {
            "n0": {
                "categories": "biolink:Gene",
                "constraints": [
                    {"id": "length",
                     "value": 277,
                     "operator": "==="}
                ]
            },
        },
        "edges": {},
    }
    output = neo4j_driver.run(get_query(qgraph), convert_to_trapi=True, qgraph=qgraph)
    assert len(output["results"]) == 1

    node_1 = list(output["knowledge_graph"]["nodes"].values())[0]
    assert node_1["name"] == "CASP3"
    assert "length" not in node_1
    assert "element_id" not in node_1


def test_string(neo4j_driver):
    """Test querying with string property."""
    qgraph = {
        "nodes": {
            "n0": {
                "categories": "biolink:Gene",
                "constraints": [
                    {"id": "chromosome",
                     "value": "17",
                     "operator": "==="}
                ]
            },
        },
        "edges": {},
    }
    output = neo4j_driver.run(get_query(qgraph), convert_to_trapi=True, qgraph=qgraph)
    assert len(output["results"]) == 1
    results = sorted(
        output["knowledge_graph"]["nodes"].values(),
        key=lambda node: node["name"],
    )
    expected_nodes = [
        "BRCA1",
    ]
    for ind, result in enumerate(results):
        assert result["name"] == expected_nodes[ind]


def test_bool(neo4j_driver):
    """Test querying with boolean property."""
    qgraph = {
        "nodes": {
            "n0": {
                "categories": "biolink:ChemicalSubstance",
            },
            "n1": {
                "categories": "biolink:Disease",
            },
        },
        "edges": {
            "e01": {
                "subject": "n0",
                "object": "n1",
                "predicates": "biolink:treats",
                "attribute_constraints": [
                    {"id": "fda_approved",
                     "value": True,
                     "operator": "==="}
                ]
            },
        },
    }
    output = neo4j_driver.run(get_query(qgraph), convert_to_trapi=True, qgraph=qgraph)
    assert len(output["results"]) == 1
    results = sorted(
        output["knowledge_graph"]["nodes"].values(),
        key=lambda node: node["name"],
    )
    expected_nodes = [
        "metformin", "type 2 diabetes mellitus",
    ]
    for ind, result in enumerate(results):
        assert result["name"] == expected_nodes[ind]


def test_publications(neo4j_driver):
    """Test publications."""
    qgraph = {
        "nodes": {
            "n0": {
                "ids": ["NCBIGene:836"],
            },
            "n1": {
                "ids": ["NCBIGene:841"],
            },
        },
        "edges": {
            "e01": {
                "subject": "n0",
                "object": "n1",
            },
        },
    }
    output = neo4j_driver.run(get_query(qgraph), convert_to_trapi=True, qgraph=qgraph)
    edges = output["knowledge_graph"]["edges"]
    assert len(edges) == 1
    attributes = list(edges.values())[0]["attributes"]
    assert any([attribute == {
        "original_attribute_name": "publications",
        "attribute_type_id": "biolink:publications",
        "value": ["xxx"],
        "value_type_id": "linkml:Uriorcurie"
    } for attribute in attributes])


def test_empty_constraints(neo4j_driver):
    """Test querying with empty 'constraints' property."""
    qgraph = {
        "nodes": {
            "n0": {
                "categories": "biolink:Gene",
                "constraints": [],
            },
            "n1": {
                "constraints": [],
            },
        },
        "edges": {
            "e01": {
                "subject": "n0",
                "object": "n1",
                "attribute_constraints": [],
            },
        },
    }
    output = neo4j_driver.run(get_query(qgraph), convert_to_trapi=True, qgraph=qgraph)
    assert len(output["results"]) == 10


def test_valid_biolink_attribute_without_mapping(neo4j_driver):
    """publications is included in the default attribute types mapping included in the codebase,
    but here we test that it still gets recognized as being biolink compliant when it's not in the mapping"""
    qgraph = {
        "nodes": {
            "n0": {
                "ids": ["MONDO:0005148"],
            },
            "n1": {
                "ids": ["NCBIGene:841"],
            },
        },
        "edges": {
            "e01": {
                "subject": "n0",
                "object": "n1",
            },
        },
    }
    output = neo4j_driver.run(get_query(qgraph), convert_to_trapi=True, qgraph=qgraph)
    edges = output["knowledge_graph"]["edges"]
    assert len(edges) == 1
    edge = list(edges.values())[0]
    assert "p_value" not in edge
    attributes = edge["attributes"]
    assert any([attribute == {
        "original_attribute_name": "p_value",
        "attribute_type_id": "biolink:p_value",
        "value": 0.000007,
        "value_type_id": DEFAULT_ATTRIBUTE_TYPE['value_type_id']
    } for attribute in attributes])
    reset_custom_attribute_types()


def test_invalid_biolink_attribute_without_mapping(neo4j_driver):
    """Test to make sure an attribute that isn't biolink compliant, and isn't custom mapped, returns correctly."""
    qgraph = {
        "nodes": {
            "n0": {
                "ids": ["NCBIGene:836"]
            },
            "n1": {
                "ids": ["MONDO:0005148"]
            },
        },
        "edges": {
            "e01": {
                "subject": "n0",
                "object": "n1"
            },
        },
    }
    output = neo4j_driver.run(get_query(qgraph), convert_to_trapi=True, qgraph=qgraph)
    edges = output["knowledge_graph"]["edges"]
    attributes = list(edges.values())[0]["attributes"]
    expected_attribute = {
        "original_attribute_name": "non_biolink_attribute",
        "attribute_type_id": DEFAULT_ATTRIBUTE_TYPE['attribute_type_id'],
        "value": "xxx123",
        "value_type_id": DEFAULT_ATTRIBUTE_TYPE['value_type_id']
    }
    assert any([attribute == expected_attribute for attribute in attributes])


def test_json_attributes(neo4j_driver):
    qgraph = {
        "nodes": {
            "n0": {
                "ids": ["NCBIGene:672"]
            },
            "n1": {
                "ids": ["MONDO:0004993"]
            },
        },
        "edges": {
            "e01": {
                "subject": "n0",
                "object": "n1",
                "predicates": "biolink:gene_associated_with_condition"
            },
        },
    }
    output = neo4j_driver.run(get_query(qgraph), convert_to_trapi=True, qgraph=qgraph)
    edges = output["knowledge_graph"]["edges"]
    assert len(edges) == 1
    correct_attributes = 0
    attributes = list(edges.values())[0]["attributes"]
    for attribute in attributes:
        if attribute.get("original_attribute_name", None) == "publications":
            assert attribute["value"] == ["xxx"]
            correct_attributes += 1
        elif attribute["attribute_type_id"] == "json_attribute_1":
            assert attribute["value"] == "json_value_1"
            correct_attributes += 1
        elif attribute["attribute_type_id"] == "json_attribute_2":
            correct_attributes += 1
        elif attribute["attribute_type_id"] == "json_attribute_3":
            assert attribute["value"] == "json_value_3"
            nested_attribute = attribute["attributes"][0]
            assert nested_attribute["attribute_type_id"] == "nested_json_attribute_1"
            assert nested_attribute["value"] == "nested_json_value_1"
            correct_attributes += 1
    assert correct_attributes == 4


def test_props_customization(neo4j_driver):
    qgraph = {
        "nodes": {
            "n0": {
                "ids": ["NCBIGene:836"],
            },
            "n1": {
                "ids": ["NCBIGene:841"],
            },
        },
        "edges": {
            "e01": {
                "subject": "n0",
                "object": "n1",
            },
        },
    }

    # put publications in the skip list and make sure it doesn't get included
    set_custom_attribute_skip_list(['publications'])
    output = neo4j_driver.run(get_query(qgraph), convert_to_trapi=True, qgraph=qgraph)
    edges = output["knowledge_graph"]["edges"]
    assert len(edges) == 1
    attributes = list(edges.values())[0]["attributes"]
    assert not any([attribute["attribute_type_id"] == "biolink:publications" for attribute in attributes])
    assert not any([attribute["attribute_type_id"] == "publications" for attribute in attributes])

    # reset the skip list
    set_custom_attribute_skip_list([])

    # set custom attribute and value types for publications and make sure they get used instead of biolink or defaults
    set_custom_attribute_types({
        "publications": {
            "attribute_type_id": "transpiler:custom_attribute_type",
            "value_type_id": "transpiler:custom_value_type"
        }
    })
    output = neo4j_driver.run(get_query(qgraph), convert_to_trapi=True, qgraph=qgraph)
    edges = output["knowledge_graph"]["edges"]
    assert len(edges) == 1
    attributes = list(edges.values())[0]["attributes"]
    assert any([attribute == {
        "original_attribute_name": "publications",
        "attribute_type_id": "transpiler:custom_attribute_type",
        "value": ["xxx"],
        "value_type_id": "transpiler:custom_value_type"
    } for attribute in attributes])
    reset_custom_attribute_types()
