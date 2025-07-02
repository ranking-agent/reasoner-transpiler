#!/usr/bin/env python
"""Initialize memgraph database."""
import argparse
import logging
import time

from neo4j import GraphDatabase
from neo4j.exceptions import ServiceUnavailable, DatabaseUnavailable, ClientError

LOGGER = logging.getLogger(__name__)

def get_driver(url):
    """Get Memgraph driver.

    Wait up to ~512 seconds for Memgraph to be ready.
    """
    seconds = 1
    while True:
        try:
            driver = GraphDatabase.driver(url)
            driver.verify_connectivity()
            return driver
        except (OSError, ServiceUnavailable, DatabaseUnavailable, ClientError) as err:
            if seconds >= 256:
                raise err
            LOGGER.error(
                "Memgraph service unavailable. Trying again in %d seconds...",
                seconds
            )
            time.sleep(seconds)
            seconds *= 2

def main(hash: str = None):
    """Delete any existing data and initialize with dummy data."""
    url = "bolt://localhost:7687"
    driver = get_driver(url)
    LOGGER.info("Connected to Memgraph. Initializing...")
    if hash is not None:
        node_file = f"https://raw.githubusercontent.com/ranking-agent/reasoner-transpiler/{hash}/tests/memgraph_csv/nodes.csv"
        gene_file = f"https://raw.githubusercontent.com/ranking-agent/reasoner-transpiler/{hash}/tests/memgraph_csv/gene_nodes.csv"
        edge_file = f"https://raw.githubusercontent.com/ranking-agent/reasoner-transpiler/{hash}/tests/memgraph_csv/edges.csv"
    else:
        node_file = f"file:///nodes.csv"
        edge_file = f"file:///edges.csv"
    with driver.session() as session:
        session.run("MATCH (m) DETACH DELETE m")
        print(node_file)
        result = session.run(f"LOAD CSV FROM \"{node_file}\" WITH HEADER AS row "
                    "CREATE (a:row.category:`biolink:NamedThing` {id:row.id, name:row.name}); ")
        result = session.run(f"LOAD CSV FROM \"{gene_file}\" WITH HEADER AS row "
                             "CREATE (a:row.category:`biolink:NamedThing` {id:row.id, name:row.name, length: toInteger(row.length), chromosome: row.chromosome}); ")
        print(f'Nodes added')
        result.consume()  # this looks like it doesn't do anything, but it's needed to throw errors if they occur
        result = session.run(f"LOAD CSV FROM \"{edge_file}\" WITH HEADER AS row "
                    "MATCH (subject {id:row.subject}), (object {id:row.object}) "
                    "CREATE (subject)-[:row.predicate]->(object);" )
        print(f'Edges added')
        result.consume()  # this looks like it doesn't do anything, but it's needed to throw errors if they occur

    driver.close()
    LOGGER.info("Done. Neo4j is ready for testing.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Initialize Memgraph.")
    parser.add_argument(
        "commit_hash",
        type=str,
        help="a commit hash from github.com/ranking-agent/reasoner",
        nargs="?",
    )

    args = parser.parse_args()
    main(args.commit_hash)
