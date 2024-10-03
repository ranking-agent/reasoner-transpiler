import pytest

from reasoner_transpiler.cypher import get_query
from .fixtures import fixture_neo4j_driver


def test_primary_source(neo4j_driver):
    qgraph = {
            "nodes": {
                "n0": {
                    "categories": ["biolink:ChemicalSubstance"]
                },
                "n1": {
                    "categories": ["biolink:Disease"],
                    "ids": ["MONDO:0005148"]
                }

            },
            "edges": {
                "e0": {
                    "subject": "n0",
                    "object": "n1",
                    "predicate": "biolink:treats"
                }
            }
        }
    output = neo4j_driver.run(get_query(qgraph), convert_to_trapi=True, qgraph=qgraph)
    assert len(output["results"]) == 3
    assert len(output["knowledge_graph"]["edges"]) == 3

    edge_sources = {
        e: edge["sources"] for e, edge in output["knowledge_graph"]["edges"].items()
    }
    assert not any(['primary_knowledge_source' in edge for edge in output["knowledge_graph"]["edges"].values()])
    assert edge_sources["metformin_treats_t2d"] == [
        {'resource_id': 'infores:test', 'resource_role': 'primary_knowledge_source'},
        {'resource_id': 'infores:ctd', 'resource_role': 'aggregator_knowledge_source',
         'upstream_resource_ids': ['infores:test']},
        {'resource_id': 'reasoner-transpiler', 'resource_role': 'aggregator_knowledge_source',
         'upstream_resource_ids': ['infores:ctd']}]
    assert edge_sources["bezafibrate_treats_t2d"] == [
        {'resource_id': 'infores:test', 'resource_role': 'primary_knowledge_source'},
        {'resource_id': 'reasoner-transpiler', 'resource_role': 'aggregator_knowledge_source',
         'upstream_resource_ids': ['infores:test']}]
    assert edge_sources["anagliptin_treats_t2d"] == [
        {'resource_id': 'infores:test2', 'resource_role': 'primary_knowledge_source'},
        {'resource_id': 'reasoner-transpiler', 'resource_role': 'aggregator_knowledge_source',
         'upstream_resource_ids': ['infores:test2']}]


# if there is no primary knowledge source on the edge, provenance will be just the transpiler/plater
def test_missing_primary_source(neo4j_driver):
    qgraph = {
            "nodes": {
                "n0": {
                    "ids": ["MESH:D014612"]
                },
                "n1": {
                    "categories": ["biolink:Disease"],
                    "ids": ["MONDO:0005260"]
                }

            },
            "edges": {
                "e0": {
                    "subject": "n0",
                    "object": "n1",
                    "predicate": "biolink:causes"
                }
            }
        }
    output = neo4j_driver.run(get_query(qgraph), convert_to_trapi=True, qgraph=qgraph)
    edge_sources = output["knowledge_graph"]["edges"]["invalid_provenance"]["sources"]
    assert edge_sources == [{'resource_id': 'reasoner-transpiler', 'resource_role': 'primary_knowledge_source'}]
