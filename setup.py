"""Setup file for reasoner package."""
from setuptools import setup

setup(
    name='reasoner',
    version='0.1.0-dev',
    author='Patrick Wang',
    author_email='patrick@covar.com',
    url='https://github.com/ranking-agent/reasoner',
    description='Utilities for working with the Reasoner format',
    packages=['reasoner'],
    include_package_data=True,
    zip_safe=False,
    license='MIT',
    python_requires='>=3.6',
)
