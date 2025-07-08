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
    url = "bolt://localhost:7688"
    driver = get_driver(url)
    LOGGER.info("Connected to Memgraph. Initializing...")
    if hash is not None:
        node_file = f"https://raw.githubusercontent.com/ranking-agent/reasoner-transpiler/{hash}/tests/memgraph_json/nodes.json"
        edge_file = f"https://raw.githubusercontent.com/ranking-agent/reasoner-transpiler/{hash}/tests/memgraph_json/edges.json"
    else:
        node_file = f"file:///nodes.csv"
        edge_file = f"file:///edges.csv"
    with driver.session() as session:
        print(edge_file)
        session.run("MATCH (m) DETACH DELETE m")
        result = session.run(f"CALL json_util.load_from_url(\"{node_file}\") YIELD objects "
                             "UNWIND objects AS node "
                             "CREATE (n:`biolink:NamedThing`:node.category {id: node.id, name: node.name, length: node.length, chromosome: node.chromosome})"
                             "RETURN count(*);")
        print(f'Nodes added: {result.single()["count(*)"]}')
        result = session.run(f"CALL json_util.load_from_url(\"{edge_file}\") YIELD objects "
                             "UNWIND objects AS edge "
                             "MATCH (s {id: edge.subject}), (o {id: edge.object}) "
                             "CREATE (s)-[x:edge.predicate "
                             "{ id: edge.id,"
                                "primary_knowledge_source: edge.primary_knowledge_source, fda_approved: edge.fda_approved,"
                                "aggregator_knowledge_source: edge.aggregator_knowledge_source, "
                                "publications: edge.publications, p_value: edge.p_value, "
                                "non_biolink_attribute: edge.non_biolink_attribute, attributes: edge.attributes, "
                                "qualified_predicate: edge.qualified_predicate, "
                                "object_aspect_qualifier: edge.object_aspect_qualifier, "
                                "object_direction_qualifier: edge.object_direction_qualifier, "
                                "bogus_knowledge_source: edge.bogus_knowledge_source}] "
                            "->(o)"
                             "RETURN count(*);")
        print(f'Edges added: {result.single()["count(*)"]}')
    driver.close()
    LOGGER.info("Done. Memgraph is ready for testing.")


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
