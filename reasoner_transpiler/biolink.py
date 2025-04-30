import os
from bmt import Toolkit

from bmt.toolkit import ClassDefinition
from bmt.toolkit import SlotDefinition

BIOLINK_MODEL_VERSION = os.environ.get('BL_VERSION', '4.2.6-rc5')
BIOLINK_MODEL_SCHEMA_URL = f"https://raw.githubusercontent.com/biolink/biolink-model/v{BIOLINK_MODEL_VERSION}/biolink-model.yaml"
PREDICATE_MAP_URL = f"https://raw.githubusercontent.com/biolink/biolink-model/v{BIOLINK_MODEL_VERSION}/predicate_mapping.yaml"

bmt = Toolkit(schema=BIOLINK_MODEL_SCHEMA_URL, predicate_map=PREDICATE_MAP_URL)
ALL_BIOLINK_ENUMS = bmt.view.all_enums().keys()


def is_biolink_slot(obj):
    return isinstance(obj, SlotDefinition)


def get_slot_uri(obj):
    return obj["slot_uri"]


def is_biolink_class(obj):
    return isinstance(obj, ClassDefinition)


def get_class_uri(obj):
    return obj["class_uri"]
