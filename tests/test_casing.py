"""Test casing."""
import pytest

from reasoner_transpiler.util import pascal_case, snake_case, space_case


def test_space():
    """Test conversion to space case."""
    assert space_case("ChemicalEntity") == "chemical entity"
    assert space_case([
        "ChemicalEntity",
        "biological_process"
    ]) == [
        "chemical entity",
        "biological process",
    ]
    with pytest.raises(ValueError):
        space_case({"a": "ChemicalEntity"})


def test_snake():
    """Test conversion to snake_case."""
    assert snake_case("ChemicalEntity") == "chemical_entity"
    assert snake_case([
        "ChemicalEntity",
        "Biological Process"
    ]) == [
        "chemical_entity",
        "biological_process",
    ]
    with pytest.raises(ValueError):
        snake_case({"a": "ChemicalEntity"})


def test_pascal():
    """Test conversion to PascalCase."""
    assert pascal_case("chemical_entity") == "ChemicalEntity"
    assert pascal_case([
        "chemical_entity",
        "biological process",
    ]) == [
        "ChemicalEntity",
        "BiologicalProcess"
    ]
    with pytest.raises(ValueError):
        pascal_case({"a": "ChemicalEntity"})
