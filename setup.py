"""Setup file for reasoner package."""
from setuptools import setup

setup(
    name="reasoner",
    version="1.7.1",
    author="Patrick Wang",
    author_email="patrick@covar.com",
    url="https://github.com/ranking-agent/reasoner",
    description="Utilities for working with the Reasoner format",
    packages=["reasoner"],
    package_data={"reasoner": ["attribute_types.json"]},
    zip_safe=False,
    license="MIT",
    python_requires=">=3.6",
)
