"""Test transpiler edge cases."""
from reasoner_transpiler.cypher import get_query
from .fixtures import db_fixture#, fixture_neo4j_driver
import pytest


def test_categories(db_fixture):
    driver, dialect = db_fixture
    """Test multiple categories."""
    qgraph = {
        "nodes": {"n0": {"categories": [
            "biolink:Disease",
            "biolink:Gene",
        ]}},
        "edges": dict(),
    }
    output = driver.run(get_query(qgraph,dialect=dialect), convert_to_trapi=True, qgraph=qgraph)
    assert len(output['results']) == 12


def test_empty(db_fixture):
    """Test empty qgraph."""
    qgraph = {
        "nodes": dict(),
        "edges": dict(),
    }
    output = db_fixture.run(get_query(qgraph), convert_to_trapi=True, qgraph=qgraph)
    assert len(output["results"]) == 0
    assert output["knowledge_graph"]["nodes"] == {}
    assert output["knowledge_graph"]["edges"] == {}


def test_category_not_specified(db_fixture):
    """Test node with type None."""
    qgraph = {
        "nodes": {
            "n0": {
                "ids": ["MONDO:0014488"]
            }
        },
        "edges": dict(),
    }
    cypher = get_query(qgraph)
    assert "NamedThing" in cypher
    output = db_fixture.run(cypher, convert_to_trapi=True, qgraph=qgraph)
    assert len(output["results"]) == 1


def test_category_none(db_fixture):
    """Test node with type None."""
    qgraph = {
        "nodes": {
            "n0": {
                "ids": ["MONDO:0014488"],
                "categories": None
            }
        },
        "edges": dict(),
    }
    cypher = get_query(qgraph)
    assert "NamedThing" in cypher
    output = db_fixture.run(cypher, convert_to_trapi=True, qgraph=qgraph)
    assert len(output["results"]) == 1


def test_relation_none(db_fixture):
    """Test edge with relation None."""
    qgraph = {
        "nodes": {
            "n0": {
                "categories": "biolink:Disease",
            },
            "n1": {
                "categories": "biolink:Gene",
            },
        },
        "edges": {
            "e01": {
                "subject": "n0",
                "object": "n1",
                "relation": None,
            }
        },
    }
    output = db_fixture.run(get_query(qgraph), convert_to_trapi=True, qgraph=qgraph)
    assert len(output["results"]) == 5


def test_qnode_addl_null(db_fixture):
    """Test qnode with null-valued additional property."""
    qgraph = {
        "nodes": {
            "n0": {
                "categories": "biolink:Disease",
            },
            "n1": {
                "categories": "biolink:Gene",
                "chromosome": None,
            },
        },
        "edges": {
            "e01": {
                "subject": "n0",
                "object": "n1",
            }
        },
    }
    output = db_fixture.run(get_query(qgraph), convert_to_trapi=True, qgraph=qgraph)
    assert len(output["results"]) == 5


def test_predicate_none(db_fixture):
    """Test edge with predicate None."""
    qgraph = {
        "nodes": {
            "n0": {
                "categories": "biolink:Disease",
            },
            "n1": {
                "categories": "biolink:Gene",
            },
        },
        "edges": {
            "e01": {
                "subject": "n0",
                "object": "n1",
                "predicates": None,
            }
        },
    }
    output = db_fixture.run(get_query(qgraph), convert_to_trapi=True, qgraph=qgraph)
    assert len(output["results"]) == 5


def test_fancy_key(db_fixture):
    """Test qnode/qedge keys with unusual characters."""
    qgraph = {
        "nodes": {
            "type-2 diabetes": {
                "categories": "biolink:Disease",
            },
            "n1": {
                "categories": "biolink:Gene",
            },
        },
        "edges": {
            "interacts with": {
                "subject": "type-2 diabetes",
                "object": "n1",
            }
        },
    }
    output = db_fixture.run(get_query(qgraph), convert_to_trapi=True, qgraph=qgraph)
    assert len(output["results"]) == 5


def test_backwards_predicate(db_fixture):
    """Test an extra backwards predicate."""
    qgraph = {
        "nodes": {
            "type-2 diabetes": {
                "ids": ["MONDO:0005148"],
                "categories": "biolink:Disease",
            },
            "drug": {
                "categories": "biolink:ChemicalEntity",
            },
        },
        "edges": {
            "related to": {
                "subject": "type-2 diabetes",
                "object": "drug",
                "predicates": ["biolink:related_to", "biolink:treats"]
            }
        }
    }
    output = db_fixture.run(get_query(qgraph), convert_to_trapi=True, qgraph=qgraph)
    assert len(output["results"]) == 3


def test_index_usage_empty_labels():
    """
    Test when using single labels, checks if id index is with the node type is used
    """
    qgraph = {
        "nodes": {
            "n0": {
                "ids": ["MONDO:0005148"],
                "categories": [],
            }
        },
        "edges": {}
    }
    cypher = get_query(qgraph, **{"use_hints": True})
    # superclass node_id is suffixed with _superclass
    assert "USING INDEX `n0`:`biolink:NamedThing`(id)" in cypher


def test_index_usage_missing_labels():
    """
    Test when using single labels, checks if id index is with the node type is used
    """
    qgraph = {
        "nodes": {
            "n0": {
                "ids": ["MONDO:0005148"]
            }
        },
        "edges": {}
    }
    cypher = get_query(qgraph, **{"use_hints": True})
    # superclass node_id is suffixed with _superclass
    assert "USING INDEX `n0`:`biolink:NamedThing`(id)" in cypher


def test_index_usage_single_labels():
    """
    Test when using single labels, checks if id index is with the node type is used
    """
    qgraph = {
        "nodes": {
            "n0": {
                "ids": ["MONDO:0005148"],
                "categories": "biolink:Disease",
            }
        },
        "edges": {}
    }
    cypher = get_query(qgraph, **{"use_hints": True})
    # superclass node_id is suffixed with _superclass
    assert "USING INDEX `n0`:`biolink:Disease`(id)" in cypher


def test_index_usage_multiple_labels():
    """
    When multiple labels are used `biolink:NamedThing` index to be used
    """
    qgraph = {
        "nodes": {
            "n0": {
                "ids": ["MONDO:0005148"],
                "categories": ["biolink:Disease", "biolink:PhenotypicFeature"]
            }
        },
        "edges": {}
    }
    cypher = get_query(qgraph, **{"use_hints": True})
    # superclass node_id is suffixed with _superclass
    assert "USING INDEX `n0`:`biolink:NamedThing`(id)" in cypher


def test_index_usage_with_subclass():
    """Test an extra backwards predicate."""
    qgraph = {
        "nodes": {
            "n0": {
                "ids": ["MONDO:0005148"],
                "categories": "biolink:Disease",
            },
            "n1": {
                "categories": "biolink:ChemicalEntity",
            },
        },
        "edges": {
            "related to": {
                "subject": "type-2 diabetes",
                "object": "drug",
                "predicates": ["biolink:related_to", "biolink:treats"]
            }
        }
    }
    cypher = get_query(qgraph, **{"use_hints": True})
    # superclass node_id is suffixed with _superclass
    assert "USING INDEX `n0_superclass`:`biolink:Disease`(id)" in cypher
