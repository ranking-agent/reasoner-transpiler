"""Test invalid query graphs."""
import pytest

from reasoner.cypher import get_query


def test_too_many_xor():
    """Test too many XOR operands."""
    qgraph = [
        "XOR",
        {
            "nodes": dict(),
            "edges": dict(),
        },
        {
            "nodes": dict(),
            "edges": dict(),
        },
        {
            "nodes": dict(),
            "edges": dict(),
        },
    ]
    with pytest.raises(ValueError) as excinfo:
        get_query(qgraph)
    assert "XOR must have exactly two operands" in str(excinfo.value)


def test_too_many_not():
    """Test too many NOT operands."""
    qgraph = [
        "NOT",
        {
            "nodes": dict(),
            "edges": dict(),
        },
        {
            "nodes": dict(),
            "edges": dict(),
        },
    ]
    with pytest.raises(ValueError) as excinfo:
        get_query(qgraph)
    assert "NOT must have exactly one operand" in str(excinfo.value)


def test_unknown_operator():
    """Test unknown operator."""
    qgraph = [
        "DNE",
        {
            "nodes": dict(),
            "edges": dict(),
        },
    ]
    with pytest.raises(ValueError) as excinfo:
        get_query(qgraph)
    assert "Unrecognized operator" in str(excinfo.value)


def test_invalid_node():
    """Test that an invalid node property value throws an error."""
    qgraph = {
        "nodes": {
            "n0": {
                "categories": "biolink:BiologicalEntity",
                "dict": {"a": 1},
            },
        },
        "edges": dict(),
    }
    with pytest.raises(ValueError):
        get_query(qgraph)
