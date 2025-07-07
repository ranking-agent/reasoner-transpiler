"""Initialize neo4j database helper function."""
import pytest
import neo4j
import asyncio

from reasoner_transpiler.cypher import transform_result


#@pytest.fixture(name="db_driver", params=["neo4j", "memgraph"], scope="module")
@pytest.fixture(name="db_driver", params=["memgraph"], scope="module")
def fixture_db_driver(request):
    database = request.param
    driver = TranspilerNeo4jBoltDriver(database)
    yield database, driver
    driver.close()


#@pytest.fixture(name="async_db_driver", params=["neo4j","memgraph"], scope="module")
@pytest.fixture(name="async_db_driver", params=["memgraph"], scope="module")
def fixture_async_db_driver(request):
    database = request.param
    driver = TranspilerAsyncNeo4jBoltDriver(database)
    yield database, driver

class TranspilerNeo4jBoltDriver:
    def __init__(self, database):
        """Pytest fixture for database connection."""
        self.database = database
        if database == "neo4j":
            url = "bolt://localhost:7687"
            self.driver = neo4j.GraphDatabase.driver(url, auth=("neo4j", "plater_testing_pw"))
        elif database == "memgraph":
            url = "bolt://localhost:7688"
            self.driver = neo4j.GraphDatabase.driver(url)

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

        with self.driver.session(database=self.database) as session:
            result = session.execute_read(self._cypher_tx_function,
                                          cypher=query,
                                          query_parameters=query_parameters,
                                          convert_to_trapi=convert_to_trapi,
                                          qgraph=qgraph)
            return result

    def close(self):
        self.driver.close()


class TranspilerAsyncNeo4jBoltDriver:

    def __init__(self, database):
        """Pytest fixture for Neo4j database connection."""
        self.database = database
        self.driver = asyncio.run(self.get_async_driver())

    async def get_async_driver(self):
        if self.database == "neo4j":
            url = "bolt://localhost:7687"
            return neo4j.AsyncGraphDatabase.driver(url, auth=("neo4j", "plater_testing_pw"))
        elif self.database == "memgraph":
            url = "bolt://localhost:7688"
            return neo4j.AsyncGraphDatabase.driver(url)

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

        async with self.driver.session(database=self.database) as session:
            result = await session.execute_read(self._cypher_tx_function,
                                                cypher=query,
                                                query_parameters=query_parameters,
                                                convert_to_trapi=convert_to_trapi,
                                                qgraph=qgraph)
            return result

    async def close(self):
        await self.driver.close()
