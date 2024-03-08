# TRAPI → Cypher transpiler

[![Test status via GitHub Actions](https://github.com/ranking-agent/reasoner/workflows/test/badge.svg)](https://github.com/ranking-agent/reasoner/actions?query=workflow%3Atest)
[![Code coverage on Codecov](https://codecov.io/gh/ranking-agent/reasoner-transpiler/branch/main/graph/badge.svg)](https://app.codecov.io/gh/ranking-agent/reasoner-transpiler/branch/main)

## Installation

```bash
pip install reasoner-transpiler
```

## Usage

```python
from reasoner_transpiler.cypher import get_query

qgraph = {
    "nodes": {
        "diabetes": {
            "ids": ["MONDO:0005148"],
        },
        "phenotype": {
            "categories": ["biolink:PhenotypicFeature"],
        },
    },
    "edges": {
        "has phenotype": {
            "subject": "diabetes",
            "predicates": ["biolink:has_phenotype"],
            "object": "phenotype",
        },
    },
}

cypher = get_query(qgraph)
```

## Biolink Model
This package uses the Biolink Model Toolkit to access the Biolink Model. Optionally, choose a specific version of the Biolink Model with the environment variable BL_VERSION. Otherwise, the latest version used by the Biolink Model Toolkit will be used.
```commandline
export BL_VERSION=4.1.6
```
