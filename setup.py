"""Setup reasoner-transpiler package."""
from setuptools import setup

setup(
    name="reasoner-transpiler",
    version="1.7.1",
    author="Patrick Wang",
    author_email="patrick@covar.com",
    url="https://github.com/ranking-agent/reasoner-transpiler",
    description="TRAPI → Cypher transpiler",
    packages=["reasoner_transpiler"],
    package_data={"reasoner_transpiler": ["attribute_types.json"]},
    zip_safe=False,
    license="MIT",
    python_requires=">=3.6",
)
