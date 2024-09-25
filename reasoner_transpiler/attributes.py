import json
from pathlib import Path

from .biolink import bmt

DIR_PATH = Path(__file__).parent


def get_attribute_types_from_config():
    with open(DIR_PATH / "attribute_types.json", "r") as stream:
        return json.load(stream)


ATTRIBUTE_TYPES = get_attribute_types_from_config()

DEFAULT_ATTRIBUTE_TYPE = {
    "attribute_type_id": "biolink:Attribute",
    "value_type_id": "EDAM:data_0006",
}

ATTRIBUTE_SKIP_LIST = []

RESERVED_NODE_PROPS = [
    "id",
    "name",
    "labels",
    "element_id"
]
RESERVED_EDGE_PROPS = [
    "id",
    "predicate",
    "object",
    "subject",
    "sources"
]

# this should really be one representation or the other, or be configurable,
# but we have graphs with each now so temporarily (I hope, hope, hope) looking for both
EDGE_SOURCE_PROPS = [
    "aggregator_knowledge_source",
    "primary_knowledge_source",
    "biolink:aggregator_knowledge_source",
    "biolink:primary_knowledge_source"
]


def transform_attributes(result_item, node=False):

    # make a list of attributes to ignore while processing
    ignore_list = RESERVED_NODE_PROPS if node else EDGE_SOURCE_PROPS + RESERVED_EDGE_PROPS
    ignore_list += ATTRIBUTE_SKIP_LIST

    # an "attributes" attribute in neo4j should be a list of json strings,
    # attempt to start the attributes section of transformed attributes with its contents,
    # here we are assuming the attributes in "attributes" are already valid trapi
    json_attributes = []
    json_attributes_attribute = result_item.pop('attributes', None)
    if json_attributes_attribute:
        if isinstance(json_attributes_attribute, list):
            try:
                json_attributes = [json.loads(json_attribute_string)
                                   for json_attribute_string in json_attributes_attribute]
            except json.JSONDecodeError:
                print(f'!!! JSONDecodeError while parsing attributes property, ignoring: {json_attributes_attribute}')
        else:
            print(f'!!! the attributes edge property should be a list, ignoring: {json_attributes_attribute}')
    transformed_attributes = {
        'attributes': json_attributes
    }

    if not node:
        # for edges, find and format attributes that are qualifiers
        qualifiers = [key for key in result_item if key not in ignore_list
                      and bmt.is_qualifier(key)]
        transformed_attributes['qualifiers'] = [
            {"qualifier_type_id": f"biolink:{key}",
             "qualifier_value": value}
            for key, value in result_item.items() if key in qualifiers
        ]
    else:
        qualifiers = []

    # for attributes that aren't in ATTRIBUTE_TYPES, see if they are valid biolink attributes
    # add them to ATTRIBUTE_TYPES, so we don't need to look again
    for attribute in \
            [key for key in result_item.keys() if key not in ignore_list + qualifiers + list(ATTRIBUTE_TYPES.keys())]:
        attribute_mapping = DEFAULT_ATTRIBUTE_TYPE
        bmt_element = bmt.get_element(attribute)
        if bmt_element:
            if 'slot_uri' in bmt_element:
                attribute_mapping['attribute_type_id'] = bmt_element['slot_uri']
            elif 'class_uri' in bmt_element:
                attribute_mapping['attribute_type_id'] = bmt_element['class_uri']
        ATTRIBUTE_TYPES[attribute] = attribute_mapping

    # format the rest of the attributes, look up their attribute type and value type
    transformed_attributes['attributes'].extend([
        {'original_attribute_name': key,
         'value': value,
         # the following function will return
         # 'attribute_type_id': 'biolink-ified attribute type id'
         # 'value_type_id': 'biolink-ified value type id'
         **ATTRIBUTE_TYPES.get(key)}
        for key, value in result_item.items()
        if key not in ignore_list + qualifiers
    ])
    return transformed_attributes


def set_custom_attribute_types(attribute_types: dict):
    global ATTRIBUTE_TYPES
    ATTRIBUTE_TYPES = attribute_types


def set_custom_attribute_skip_list(skip_list: list):
    global ATTRIBUTE_SKIP_LIST
    ATTRIBUTE_SKIP_LIST = skip_list


def reset_custom_attribute_types():
    global ATTRIBUTE_TYPES
    ATTRIBUTE_TYPES = get_attribute_types_from_config()

