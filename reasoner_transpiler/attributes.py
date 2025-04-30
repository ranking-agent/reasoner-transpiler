import json
import os
from pathlib import Path

from .biolink import bmt, is_biolink_slot, is_biolink_class, get_slot_uri, get_class_uri

DIR_PATH = Path(__file__).parent


def get_attribute_types_from_config():
    with open(DIR_PATH / "attribute_types.json", "r") as stream:
        return json.load(stream)


ATTRIBUTE_TYPES = get_attribute_types_from_config()

DEFAULT_ATTRIBUTE_TYPE = {
    "attribute_type_id": "biolink:Attribute"
}

ATTRIBUTE_SKIP_LIST = []

PRIMARY_KNOWLEDGE_SOURCE = "primary_knowledge_source"
AGGREGATOR_KNOWLEDGE_SOURCE = "aggregator_knowledge_source"

PROVENANCE_TAG = os.environ.get('PROVENANCE_TAG', 'reasoner-transpiler')


# This function takes EDGE_SOURCE_PROPS properties from results, converts them into proper
# TRAPI dictionaries, and assigns the proper upstream ids to each resource. It does not currently attempt to avoid
# duplicate aggregator results, which shouldn't exist in the graphs.
def construct_sources_tree(primary_knowledge_source, aggregator_knowledge_sources):

    if not primary_knowledge_source:
        return [{"resource_id": PROVENANCE_TAG,
                 "resource_role": "primary_knowledge_source"}]

    # set the primary knowledge source
    formatted_sources = [{"resource_id": primary_knowledge_source,
                          "resource_role": "primary_knowledge_source"}]

    # walk through the aggregator lists and construct the chains of provenance
    terminal_aggregators = set()
    for aggregator_list in aggregator_knowledge_sources:
        # each aggregator list should be in order, so we can deduce the upstream chains
        last_aggregator = None
        for aggregator_knowledge_source in aggregator_list:
            formatted_sources.append({
                "resource_id": aggregator_knowledge_source,
                "resource_role": "aggregator_knowledge_source",
                "upstream_resource_ids": [last_aggregator] if last_aggregator else [primary_knowledge_source]
            })
            last_aggregator = aggregator_knowledge_source
        # store the last aggregator in the list, because this will be an upstream source for the plater one
        terminal_aggregators.add(last_aggregator)
    # add PROVENANCE_TAG as the most downstream aggregator,
    # it will have as upstream either the primary ks or all of the furthest downstream aggregators if they exist
    # this will be used by applications like Plater which need to append themselves as an aggregator
    formatted_sources.append({
        "resource_id": PROVENANCE_TAG,
        "resource_role": "aggregator_knowledge_source",
        "upstream_resource_ids": list(terminal_aggregators) if terminal_aggregators else [primary_knowledge_source]
    })
    return formatted_sources


def transform_attributes(result_entity, node=False):

    # construct a valid TRAPI entity to return in trapi_entity
    trapi_entity = {}

    for attribute in ATTRIBUTE_SKIP_LIST:
        result_entity.pop(attribute, None)

    # an "attributes" attribute in neo4j should be a list of json strings,
    # attempt to start the attributes section of transformed attributes with its contents,
    # here we are assuming the attributes in "attributes" are already valid trapi
    json_attributes = []
    json_attributes_attribute = result_entity.pop('attributes', None)
    if json_attributes_attribute:
        if isinstance(json_attributes_attribute, list):
            try:
                json_attributes = [json.loads(json_attribute_string)
                                   for json_attribute_string in json_attributes_attribute]
            except json.JSONDecodeError:
                print(f'!!! JSONDecodeError while parsing attributes property, ignoring: {json_attributes_attribute}')
        else:
            print(f'!!! the attributes edge property should be a list, ignoring: {json_attributes_attribute}')
        trapi_attributes = json_attributes
    else:
        trapi_attributes = []

    # if it's an edge handle provenance (sources) and qualifiers
    if not node:
        # extract properties for provenance, construct the sources section
        primary_knowledge_source = result_entity.pop(PRIMARY_KNOWLEDGE_SOURCE, None)
        # get any properties that start with AGGREGATOR_KNOWLEDGE_SOURCE, this handles the possibility of edges
        # with multiple aggregator knowledge source lists like aggregator_knowledge_source_2
        aggregator_knowledge_source_keys = [ks_attribute for ks_attribute in result_entity.keys()
                                            if ks_attribute.startswith(AGGREGATOR_KNOWLEDGE_SOURCE)]
        aggregator_knowledge_sources = [result_entity[key] for key in aggregator_knowledge_source_keys]
        for ks_property in aggregator_knowledge_source_keys:
            result_entity.pop(ks_property)
        trapi_entity["sources"] = construct_sources_tree(primary_knowledge_source, aggregator_knowledge_sources)

        # find and format attributes that are qualifiers
        qualifiers = [key for key in result_entity if bmt.is_qualifier(key)]
        if qualifiers:
            trapi_entity["qualifiers"] = [{"qualifier_type_id": f"biolink:{qualifier}",
                                          "qualifier_value": result_entity.pop(qualifier)}
                                          for qualifier in qualifiers]

    # for attributes that aren't in ATTRIBUTE_TYPES, see if they are valid biolink attributes
    # TODO this is still inefficient - we should really map all the possible attributes on start up
    for attribute in result_entity:
        if attribute not in ATTRIBUTE_TYPES:
            bmt_element = bmt.get_element(attribute)
            if not bmt_element:
                ATTRIBUTE_TYPES[attribute] = DEFAULT_ATTRIBUTE_TYPE
            else:
                # This looks in the biolink model for the slot_uri or class_uri depending on if the element
                # is a slot or a class and attempts to populate the attribute_type_id and value_type_id with something
                # useful. Technically classes probably shouldn't be included as attribute_type_id but examples exist
                # and it seems better than having a default value that also isn't compliant.
                attribute_type_id = f'biolink:{attribute}'
                value_type_id = None
                if is_biolink_slot(bmt_element):
                    bl_slot_uri = get_slot_uri(bmt_element)
                    value_type_id = bl_slot_uri if bl_slot_uri != attribute_type_id else None
                elif is_biolink_class(bmt_element):
                    attribute_type_id = get_class_uri(bmt_element)
                attribute_mapping = {
                    'attribute_type_id': attribute_type_id,
                    **({'value_type_id': value_type_id} if value_type_id else {})
                }
                # add it to ATTRIBUTE_TYPES, so we don't need to check biolink again
                ATTRIBUTE_TYPES[attribute] = attribute_mapping

    # format the rest of the attributes, look up their attribute type and value type
    trapi_attributes.extend([
        {'original_attribute_name': key,
         'value': value,
         # ATTRIBUTE_TYPES is a mapping for things like attribute_type_id, value_type_id or other TRAPI fields
         **ATTRIBUTE_TYPES.get(key)}
        for key, value in result_entity.items()
    ])
    if trapi_attributes:
        trapi_entity["attributes"] = trapi_attributes
    return trapi_entity


def set_custom_attribute_types(attribute_types: dict):
    global ATTRIBUTE_TYPES
    ATTRIBUTE_TYPES = attribute_types


def set_custom_attribute_skip_list(skip_list: list):
    global ATTRIBUTE_SKIP_LIST
    ATTRIBUTE_SKIP_LIST = skip_list


def reset_custom_attribute_types():
    global ATTRIBUTE_TYPES
    ATTRIBUTE_TYPES = get_attribute_types_from_config()

