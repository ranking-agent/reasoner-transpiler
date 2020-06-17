#!/usr/bin/env python
"""Initialize neo4j database."""
import logging
import time

from neo4j import GraphDatabase
from neo4j.exceptions import ServiceUnavailable, DatabaseUnavailable

LOGGER = logging.getLogger(__name__)


def get_driver(url):
    """Get Neo4j driver.

    Wait up to ~512 seconds for Neo4j to be ready.
    """
    seconds = 1
    while True:
        try:
            driver = GraphDatabase.driver(url, auth=None)
            # make sure we can start and finish a session
            with driver.session() as session:
                session.run('CALL dbms.procedures()')
            return driver
        except (OSError, ServiceUnavailable, DatabaseUnavailable) as err:
            if seconds >= 256:
                raise err
            LOGGER.error(
                'Neo4j service unavailable. Trying again in %d seconds...',
                seconds
            )
            time.sleep(seconds)
            seconds *= 2


def main():
    """Delete any existing data and initialize with dummy data."""
    url = 'bolt://localhost:7687'
    driver = get_driver(url)
    LOGGER.info('Connected to Neo4j. Initializing...')
    with driver.session() as session:
        session.run("MATCH (m) DETACH DELETE m")
        session.run("LOAD CSV WITH HEADERS FROM 'file:///nodes.csv' "
                    "AS row "
                    "CALL apoc.create.node([row.label], {"
                    "name: row.name, id: row.id,"
                    "subtype: row.subtype, gender: row.gender,"
                    "occurences: toInteger(row.occurences),"
                    "good: toBoolean(row.good)"
                    "}) YIELD node "
                    "RETURN count(*)")
        session.run("LOAD CSV WITH HEADERS FROM 'file:///edges.csv' "
                    "AS edge "
                    "MATCH (source), (target) "
                    "WHERE source.id = edge.source_id AND target.id = edge.target_id "
                    "CALL apoc.create.relationship(source, toUpper(edge.predicate), "
                    "{predicate: edge.predicate, id: edge.id}, target) YIELD rel "
                    "RETURN count(*)")
    LOGGER.info('Done. Neo4j is ready for testing.')


if __name__ == '__main__':
    main()
