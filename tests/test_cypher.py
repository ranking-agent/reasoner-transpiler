"""Test Reasoner->Cypher transpiler."""
import pytest
from neo4j import GraphDatabase

from reasoner.cypher import get_query, get_match_clause

uri = 'bolt://localhost:7687'
driver = GraphDatabase.driver(uri, auth=None)


with driver.session() as session:
    session.run("MATCH (m) DETACH DELETE m")
    session.run("LOAD CSV WITH HEADERS FROM 'file:///nodes.csv' "
                "AS row "
                "CALL apoc.create.node([row.label], {"
                "name: row.name, id: row.name,"
                "subtype: row.subtype, gender: row.gender,"
                "occurences: toInteger(row.occurences)"
                "}) YIELD node "
                "RETURN count(*)")
    session.run("LOAD CSV WITH HEADERS FROM 'file:///edges.csv' "
                "AS edge "
                "MATCH (source), (target) "
                "WHERE source.name = edge.source_id AND target.name = edge.target_id "
                "CALL apoc.create.relationship(source, toUpper(edge.predicate), {predicate: edge.predicate}, target) YIELD rel "
                "RETURN count(*)")
    print('Everything loaded')
    qgraph = {
        "nodes": [
            {
                "id": "n1",
                "type": "Weapon",
            },
            {
                "id": "n0",
                "curie": "Frodo",
                "type": "Person",
                "gender": "male",
                "occurences": 2040,
            },
            {
                "id": "n2",
                "type": "Person",
                "curie": [
                    "Bilbo",
                ],
            },
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
                "type": "INHERITS",
            },
            {
                "id": "e21",
                "source_id": "n2",
                "target_id": "n1",
                "type": [
                    "WIELDS",
                    "FINDS",
                ],
            }
        ],
    }
    records = session.run(get_query(qgraph))
    for record in records:
        print(record)


def test_match():
    """Test MATCH clause generation."""
    qgraph = {
        "nodes": [
            {
                "id": "n0",
                "curie": [
                    "Frodo",
                    "Sam",
                ],
                "type": "Person",
            },
            {
                "id": "n1",
                "curie": {
                    "Frodo",
                    "Sam",
                },
                "type": "Person",
            },
        ],
        "edges": [],
    }
    clause = get_match_clause(qgraph)
    print(clause)
    # assert get_match_clause(qgraph) == "MATCH (`n0`:`Person` {}) USING INDEX `n0`:Person(id) WHERE `n0`.id = \"Frodo\" OR `n0`.id = \"Sam\" MATCH (`n1`:`Person` {`id`: \"{'Frodo', 'Sam'}\"}) USING INDEX `n1`:Person(id)"


def test_query():
    """Test full query generation."""
    qgraph = {
        "nodes": [
            {
                "id": "n1",
                "type": "Weapon",
            },
            {
                "id": "n0",
                "curie": "Frodo",
                "type": "Person",
                "gender": "male",
                "occurences": 2040,
            },
            {
                "id": "n2",
                "type": "Person",
                "curie": [
                    "Bilbo",
                ],
            },
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
                "type": "INHERITS",
            },
            {
                "id": "e21",
                "source_id": "n2",
                "target_id": "n1",
                "type": [
                    "WIELDS",
                    "FINDS",
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
