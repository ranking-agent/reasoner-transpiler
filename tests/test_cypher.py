"""Test Reasoner->Cypher transpiler."""
import pytest

from reasoner.cypher import get_query, get_match_clause


def test_match():
    """Test MATCH clause generation."""
    qgraph = {
        "nodes": [
            {
                "id": "n0",
                "curie": [
                    "MONDO:0100096",
                    "DOID:4325",
                ],
                "type": "disease",
            },
            {
                "id": "n1",
                "curie": {
                    "MONDO:0100096",
                    "DOID:4325",
                },
                "type": "disease",
            },
        ],
        "edges": [],
    }
    clause = get_match_clause(qgraph)
    print(clause)


def test_query():
    """Test full query generation."""
    qgraph = {
        "nodes": [
            {
                "id": "n1",
                "type": "gene",
            },
            {
                "id": "n0",
                "curie": "MONDO:0100096",
                "type": "disease",
                "communicable": True,
                "US deaths": 75000,
            },
            {
                "id": "n2",
                "curie": [
                    "MONDO:0004979",
                ],
            }
        ],
        "edges": [
            {
                "id": "e02",
                "source_id": "n0",
                "target_id": "n2",
            },
            {
                "id": "e01",
                "source_id": "n0",
                "target_id": "n1",
                "type": "related_to",
            },
            {
                "id": "e21",
                "source_id": "n2",
                "target_id": "n1",
                "type": [
                    "related_to",
                    "associated_with",
                ],
            }
        ],
    }
    clause = get_query(
        qgraph,
    )
    print(clause)
    clause = get_query(
        qgraph,
        max_connectivity=3,
        relationship_id='internal',
        skip=2,
        limit=10,
    )
    print(clause)

    qgraph['nodes'][0]['dict'] = {'a': 1}
    with pytest.raises(ValueError):
        get_query(qgraph)
