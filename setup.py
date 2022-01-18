"""Setup reasoner-transpiler package."""
from setuptools import setup

setup(
    name="reasoner-transpiler",
    version="1.10.3",
    author="Patrick Wang",
    author_email="patrick@covar.com",
    url="https://github.com/ranking-agent/reasoner-transpiler",
    description="TRAPI → Cypher transpiler",
    packages=["reasoner_transpiler"],
    package_data={"reasoner_transpiler": ["attribute_types.json"]},
    install_requires=[
        "bmt-lite-2.1.0>=2.0.0,<3.0",
    ],
    zip_safe=False,
    license="MIT",
    python_requires=">=3.6",
)
