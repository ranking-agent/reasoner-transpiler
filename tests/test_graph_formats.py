"""Test query graph formats."""
from reasoner_transpiler.cypher import get_query
from .fixtures import fixture_database


def test_curie_formats(database):
    """Test unusual curie formats."""
    qgraph = {
        "nodes": {
            "n0": {
                "ids": [
                    "MONDO:0005148",
                    "MONDO:0011122",
                ],
                "categories": "biolink:Disease",
            },
            "n1": {
                "categories": "biolink:ChemicalSubstance",
            },
        },
        "edges": {
            "e01": {
                "predicates": [
                    "biolink:treats",
                ],
                "subject": "n1",
                "object": "n0",
            },
        },
    }
    output = database.run(get_query(qgraph))
    for record in output:
        assert len(record["results"]) == 5
        results = sorted(
            record["knowledge_graph"]["nodes"].values(),
            key=lambda node: node["name"],
        )
        expected_nodes = [
            "anagliptin",
            "bezafibrate",
            "metformin",
            "obesity disorder",
            "type 2 diabetes mellitus",
        ]
        for ind, result in enumerate(results):
            assert result["name"] == expected_nodes[ind]


# def test_complex_query(database):
#     """Test that db get"s initialized successfully."""
#     qgraph = {
#         "nodes": {
#             "n1": {
#                 "categories": "biolink:PhenotypicFeature",
#             },
#             "n0": {
#                 "categories": "biolink:Disease",
#                 "ids": "MONDO:0005148",
#             },
#             "n2": {
#                 "categories": "biolink:ChemicalSubstance",
#                 "ids": [
#                     "CHEBI:6801",
#                 ],
#             },
#         },
#         "edges": {
#             "e02": {
#                 "subject": "n2",
#                 "object": "n0",
#             },
#             "e01": {
#                 "subject": "n0",
#                 "object": "n1",
#                 "predicates": "INHERITS",
#             },
#             "e21": {
#                 "subject": "n2",
#                 "object": "n1",
#                 "predicates": [
#                     "WIELDS",
#                     "FINDS",
#                 ],
#             }
#         },
#     }
#     output = database.run(get_query(qgraph))
#     for record in output:
#         assert len(record["results"]) == 1
#         assert record["results"][0]["node_bindings"] == [
#             {"kg_id": "TGATE:Sting", "qg_id": "n1"},
#             {"kg_id": "TGATE:Frodo", "qg_id": "n0"},
#             {"kg_id": "TGATE:Bilbo", "qg_id": "n2"},
#         ]


def test_predicate_list():
    """Test that an edge with a list of predicates works properly."""
    qgraph = {
        "nodes": {
            "n0": {
                "categories": "biolink:Disease",
            },
            "n1": {
                "categories": "biolink:PhenotypicFeature",
            },
        },
        "edges": {
            "e01": {
                "predicates": ["biolink:capable_of", "biolink:biomarker_for"],
                "subject": "n0",
                "object": "n1",
            },
        },
    }
    clause = get_query(qgraph, reasoner=False)
    # edges with types should be directed
    assert "(`n0`:`biolink:Disease`)-[`e01`:`biolink:biomarker_for`|`biolink:capable_of`]->(`n1`:`biolink:PhenotypicFeature`)" in clause


def test_single_edge_type_list():
    """Test that an edge with a edge type list of one works properly."""
    qgraph = {
        "nodes": {
            "n0": {
                "categories": "biolink:Disease",
            },
            "n1": {
                "categories": "biolink:PhenotypicFeature",
            },
        },
        "edges": {
            "e01": {
                "predicates": ["biolink:capable_of"],
                "subject": "n0",
                "object": "n1",
            },
        },
    }
    clause = get_query(qgraph, reasoner=False)
    # edges with types should be directed
    assert "(`n0`:`biolink:Disease`)-[`e01`:`biolink:capable_of`]->(`n1`:`biolink:PhenotypicFeature`)" in clause

def test_invertible():
    """Test edge predicate inversion ca. biolink model 3.2.0."""
    qgraph = {
        "nodes": {
            "n0": {
                "categories": "biolink:Disease",
            },
            "n1": {
                "categories": "biolink:PhenotypicFeature",
            },
        },
        "edges": {
            "e01": {
                "predicates": "biolink:phenotype_of",
                "subject": "n0",
                "object": "n1",
            },
        },
    }
    clause = get_query(qgraph, reasoner=False)
    # edges with types should be directed
    assert "(`n1`:`biolink:PhenotypicFeature`)-[`e01`:`biolink:has_phenotype`]->(`n0`:`biolink:Disease`)" in clause


def test_curie_int():
    """Test unusual curie formats."""
    qgraph = {
        "nodes": {
            "n0": {
                "categories": "biolink:Disease",
                "ids": 12,
            },
        },
        "edges": dict(),
    }
    clause = get_query(qgraph, reasoner=False)
    # the curie integer should be converted to a string
    assert "{`id`: \"12\"}" in clause
