"""Initialize neo4j database helper function."""
import pytest
import neo4j
import asyncio

from reasoner_transpiler.cypher import transform_result


@pytest.fixture(name="neo4j_driver", scope="module")
def fixture_neo4j_driver():
    driver = TranspilerNeo4jBoltDriver()
    yield driver
    driver.close()


@pytest.fixture(name="async_neo4j_driver", scope="module")
def fixture_async_neo4j_driver():
    driver = TranspilerAsyncNeo4jBoltDriver()
    yield driver


class TranspilerNeo4jBoltDriver:
    def __init__(self):
        """Pytest fixture for Neo4j database connection."""
        url = "bolt://localhost:7687"
        self.driver = neo4j.GraphDatabase.driver(url, auth=("neo4j", "plater_testing_pw"))

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
            neo4j_record = neo4j_result.single()
            return transform_result(neo4j_record, qgraph)
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


class TranspilerAsyncNeo4jBoltDriver:

    def __init__(self):
        """Pytest fixture for Neo4j database connection."""
        self.driver = asyncio.run(self.get_async_driver())

    async def get_async_driver(self):
        url = "bolt://localhost:7687"
        return neo4j.AsyncGraphDatabase.driver(url, auth=("neo4j", "plater_testing_pw"))

    @staticmethod
    async def _cypher_tx_function(tx,
                                  cypher,
                                  query_parameters=None,
                                  convert_to_trapi=False,
                                  qgraph=None):
        if not query_parameters:
            query_parameters = {}

        neo4j_result: neo4j.AsyncResult = await tx.run(cypher, parameters=query_parameters)
        if convert_to_trapi:
            neo4j_record = await neo4j_result.single()
            return transform_result(neo4j_record, qgraph)
        return neo4j_result

    async def run(self,
                  query,
                  query_parameters: dict = None,
                  convert_to_trapi=False,
                  qgraph=None):

        if not query_parameters:
            query_parameters = {}

        async with self.driver.session(database="neo4j") as session:
            result = await session.execute_read(self._cypher_tx_function,
                                                cypher=query,
                                                query_parameters=query_parameters,
                                                convert_to_trapi=convert_to_trapi,
                                                qgraph=qgraph)
            return result

    async def close(self):
        await self.driver.close()
