"""Initialize neo4j database helper function."""
from neo4j import GraphDatabase

uri = 'bolt://localhost:7687'
driver = GraphDatabase.driver(uri, auth=None)


def initialize_db():
    """
    Delete any existing data and initialize with dummy data.

    Returns:
        a new neo4j session with freshly initialized data.
    """
    session = driver.session()
    session.run("MATCH (m) DETACH DELETE m")
    session.run("LOAD CSV WITH HEADERS FROM 'file:///nodes.csv' "
                "AS row "
                "CALL apoc.create.node([row.label], {"
                "name: row.name, id: row.name,"
                "subtype: row.subtype, gender: row.gender,"
                "occurences: toInteger(row.occurences),"
                "good: toBoolean(row.good)"
                "}) YIELD node "
                "RETURN count(*)")
    session.run("LOAD CSV WITH HEADERS FROM 'file:///edges.csv' "
                "AS edge "
                "MATCH (source), (target) "
                "WHERE source.name = edge.source_id AND target.name = edge.target_id "
                "CALL apoc.create.relationship(source, toUpper(edge.predicate), {predicate: edge.predicate}, target) YIELD rel "
                "RETURN count(*)")
    return session
