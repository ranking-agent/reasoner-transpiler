"""Setup reasoner-transpiler package."""
from setuptools import setup

setup(
    name="reasoner-transpiler",
    version="2.2.2",
    author="Patrick Wang",
    author_email="patrick@covar.com",
    maintainer="Evan Morris",
    maintainer_email="emorris@renci.org",
    url="https://github.com/ranking-agent/reasoner-transpiler",
    description="TRAPI → Cypher transpiler",
    packages=["reasoner_transpiler"],
    package_data={"reasoner_transpiler": ["attribute_types.json", "value_types.json"]},
    install_requires=[
        "bmt==1.4.4",
    ],
    zip_safe=False,
    license="MIT",
    python_requires=">=3.9",
)
