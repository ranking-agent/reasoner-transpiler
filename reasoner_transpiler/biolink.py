import os
from bmt import Toolkit


BIOLINK_MODEL_VERSION = os.environ.get('BL_VERSION', '4.2.1')
BIOLINK_MODEL_SCHEMA_URL = f"https://raw.githubusercontent.com/biolink/biolink-model/v{BIOLINK_MODEL_VERSION}/biolink-model.yaml"
PREDICATE_MAP_URL = f"https://raw.githubusercontent.com/biolink/biolink-model/v{BIOLINK_MODEL_VERSION}/predicate_mapping.yaml"

bmt = Toolkit(schema=BIOLINK_MODEL_SCHEMA_URL, predicate_map=PREDICATE_MAP_URL)
ALL_BIOLINK_ENUMS = bmt.view.all_enums().keys()
