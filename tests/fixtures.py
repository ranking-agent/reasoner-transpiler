"""Initialize neo4j database helper function."""
import pytest
import requests
import base64

from neo4j import GraphDatabase
from reasoner_transpiler.cypher import transform_result


@pytest.fixture(name="neo4j_driver", scope="module")
def fixture_neo4j_driver():
    driver = TranspilerNeo4jBoltDriver()
    yield driver
    driver.close()


class TranspilerNeo4jBoltDriver:
    def __init__(self):
        """Pytest fixture for Neo4j database connection."""
        url = "bolt://localhost:7687"
        self.driver = GraphDatabase.driver(url, auth=("neo4j", "plater_testing_pw"))

    @staticmethod
    def _cypher_tx_function(tx,
                            cypher,
                            query_parameters=None,
                            convert_to_trapi=False,
                            qgraph=None):
        if not query_parameters:
            query_parameters = {}

        neo4j_result = tx.run(cypher, parameters=query_parameters)
        if convert_to_trapi:
            return transform_result(neo4j_result, qgraph)
        return neo4j_result

    def run(self,
            query,
            query_parameters: dict = None,
            convert_to_trapi=False,
            qgraph=None):

        if not query_parameters:
            query_parameters = {}

        with self.driver.session(database="neo4j") as session:
            result = session.execute_read(self._cypher_tx_function,
                                          cypher=query,
                                          query_parameters=query_parameters,
                                          convert_to_trapi=convert_to_trapi,
                                          qgraph=qgraph)
            return result

    def close(self):
        self.driver.close()
