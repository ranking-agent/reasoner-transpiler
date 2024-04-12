"""Setup reasoner-transpiler package."""
from setuptools import setup

setup(
    name="reasoner-transpiler",
    version="2.0.11",
    author="Patrick Wang",
    author_email="patrick@covar.com",
    maintainer="Yaphet Kebede",
    maintainer_email="kebedey@renci.org",
    url="https://github.com/ranking-agent/reasoner-transpiler",
    description="TRAPI → Cypher transpiler",
    packages=["reasoner_transpiler"],
    package_data={"reasoner_transpiler": ["attribute_types.json"]},
    install_requires=[
        "bmt==1.3.0",
    ],
    zip_safe=False,
    license="MIT",
    python_requires=">=3.9",
)
