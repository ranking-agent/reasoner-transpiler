"""Test transpiler edge cases."""
from reasoner_transpiler.cypher import get_query
from .fixtures import fixture_db_driver
#import pytest


def test_categories(db_driver):
    """Test multiple categories."""
    qgraph = {
        "nodes": {"n0": {"categories": [
            "biolink:Disease",
            "biolink:Gene",
        ]}},
        "edges": dict(),
    }
    dialect, driver = db_driver
    output = driver.run(get_query(qgraph, dialect=dialect), convert_to_trapi=True, qgraph=qgraph)
    assert len(output['results']) == 12


def test_empty(db_driver):
    """Test empty qgraph."""
    qgraph = {
        "nodes": dict(),
        "edges": dict(),
    }
    dialect, driver = db_driver
    output = driver.run(get_query(qgraph, dialect=dialect), convert_to_trapi=True, qgraph=qgraph)
    assert len(output["results"]) == 0
    assert output["knowledge_graph"]["nodes"] == {}
    assert output["knowledge_graph"]["edges"] == {}


def test_category_not_specified(db_driver):
    """Test node with type None."""
    qgraph = {
        "nodes": {
            "n0": {
                "ids": ["MONDO:0014488"]
            }
        },
        "edges": dict(),
    }
    dialect, driver = db_driver
    cypher = get_query(qgraph, dialect=dialect)
    assert "NamedThing" in cypher
    output = driver.run(cypher, convert_to_trapi=True, qgraph=qgraph)
    assert len(output["results"]) == 1


def test_category_none(db_driver):
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
    dialect, driver = db_driver
    cypher = get_query(qgraph, dialect=dialect)
    assert "NamedThing" in cypher
    output = driver.run(cypher, convert_to_trapi=True, qgraph=qgraph)
    assert len(output["results"]) == 1


def test_relation_none(db_driver):
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
    dialect, driver = db_driver
    output = driver.run(get_query(qgraph, dialect=dialect), convert_to_trapi=True, qgraph=qgraph)
    assert len(output["results"]) == 5


def test_qnode_addl_null(db_driver):
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
    dialect, driver = db_driver
    output = driver.run(get_query(qgraph,dialect=dialect), convert_to_trapi=True, qgraph=qgraph)
    assert len(output["results"]) == 5


def test_predicate_none(db_driver):
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
    dialect, driver = db_driver
    output = driver.run(get_query(qgraph,dialect=dialect), convert_to_trapi=True, qgraph=qgraph)
    assert len(output["results"]) == 5


def test_fancy_key(db_driver):
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
    dialect, driver = db_driver
    output = driver.run(get_query(qgraph, dialect=dialect), convert_to_trapi=True, qgraph=qgraph)
    assert len(output["results"]) == 5


#This one kills memgraph 3.3.0.  See https://github.com/memgraph/memgraph/issues/3080
def x_test_backwards_predicate(db_driver):
    """Test an extra backwards predicate."""
    qgraph = {
        "nodes": {
            "type-2 diabetes": {
                "ids": ["MONDO:0005148"],
                "categories": "biolink:Disease",
            },
            "drug": {
                "categories": "biolink:ChemicalSubstance",
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
    dialect, driver = db_driver
    output = driver.run(get_query(qgraph, dialect=dialect), convert_to_trapi=True, qgraph=qgraph)
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
                "categories": "biolink:ChemicalSubstance",
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
