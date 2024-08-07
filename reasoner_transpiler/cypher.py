"""Tools for compiling QGraph into Cypher query."""
import os
import json
from functools import cache
from pathlib import Path

from .biolink import bmt
from .matching import match_query
from .exceptions import UnsupportedError

DIR_PATH = Path(__file__).parent

with open(DIR_PATH / "attribute_types.json", "r") as stream:
    ATTRIBUTE_TYPES = json.load(stream)

with open(DIR_PATH / "value_types.json", "r") as stream:
    VALUE_TYPES = json.load(stream)

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
    "subject"
]

# this should really be one representation or the other, or be configurable,
# but we have graphs with each now so temporarily (I hope, hope, hope) looking for both
EDGE_SOURCE_PROPS = [
    "aggregator_knowledge_source",
    "primary_knowledge_source",
    "biolink:aggregator_knowledge_source",
    "biolink:primary_knowledge_source"
]

PROVENANCE_TAG = os.environ.get('PROVENANCE_TAG', 'reasoner-transpiler')
NEO4J_PROTOCOL = os.environ.get('NEO4J_PROTOCOL', 'bolt')


def nest_op(operator, *args):
    """Generate a nested set of operations from a flat expression."""
    if len(args) > 2:
        return [operator, args[0], nest_op(operator, *args[1:])]
    else:
        return [operator, *args]


def assemble_results(qnodes, qedges, **kwargs):
    """Assemble results into Reasoner format."""
    clauses = []

    for qnode in qnodes.values():
        if qnode.get("set_interpretation", "") == "MANY":
            raise UnsupportedError(f'This feature is currently not supported: set_interpretation=MANY')

    """
    The following is the old way of assembling results within the cypher query, it doesn't work in neo4j 5 because
    it uses forms of implicit aggregation that aren't supported. Leaving it here though because it would be smart 
    to do something similar - especially regarding de-duplicating nodes and/or edges.
    
    # assemble result (bindings) and associated (result) kgraph
    node_bindings = [
        # when set_interpretation is ALL
        (
            "`{0}`: [ni IN collect(DISTINCT `{0}`.id) "
            "WHERE ni IS NOT null "
            "| {{id: ni}}]"
        ).format(
            qnode_id,
        ) if qnode.get("set_interpretation", "BATCH") == "ALL" else
        # when set_interpretation is BATCH, MANY  or missing
        (
            "`{0}`: (CASE "
            "WHEN `{0}` IS NOT NULL THEN [{{id: `{0}`.id{1}}}] "
            "ELSE [] "
            "END)"
        ).format(
            qnode_id,
            f", query_id: `{qnode_id}_superclass`.id" if f"{qnode_id}_superclass" in qnodes else "",
        )
        for qnode_id, qnode in qnodes.items()
        if qnode.get("_return", True)
    ]
    edge_bindings = [
        (
            "`{0}`: [ei IN collect(DISTINCT toString(id(`{0}`))) "
            "WHERE ei IS NOT null "
            "| {{id: ei}}]"
        ).format(
            qedge_id,
        ) if kwargs.get("relationship_id", "property") == "internal" else
        (
            "`{0}`: [ei IN collect(DISTINCT `{0}`.id) "
            "WHERE ei IS NOT null "
            "| {{id: ei}}]"
        ).format(
            qedge_id,
        )
        for qedge_id, qedge in qedges.items()
        if qedge.get("_return", True)
    ]
    knodes = [
        "collect(DISTINCT `{0}`)".format(qnode_id)
        for qnode_id, qnode in qnodes.items()
        if qnode.get("_return", True)
    ]
    kedges = [
        "collect(DISTINCT `{0}`)".format(qedge_id)
        for qedge_id, qedge in qedges.items()
        if qedge.get("_return", True)
    ]
    assemble_clause = (
        "WITH {{node_bindings: {{{0}}}, analyses: [{{edge_bindings: {{{1}}}}}]}} AS result, "
        "{{nodes: {2}, edges: {3}}} AS knowledge_graph"
    ).format(
        ", ".join(node_bindings) or "",
        ", ".join(edge_bindings) or "",
        " + ".join(knodes) or "[]",
        " + ".join(kedges) or "[]",
    )
    clauses.append(assemble_clause)

    # add SKIP and LIMIT sub-clauses
    clauses.extend(pagination(**kwargs))

    # collect results and aggregate kgraphs
    # also fetch extra knode/kedge properties
    if knodes:
        clauses.append("UNWIND knowledge_graph.nodes AS knode")
    if kedges:
        clauses.append("UNWIND knowledge_graph.edges AS kedge")
    aggregate_clause = "WITH collect(DISTINCT result) AS results, {"
    aggregate_clause += (
        (
            "nodes: apoc.map.fromLists("
            "[n IN collect(DISTINCT knode) | n.id], "
            "[n IN collect(DISTINCT knode) | {"
            "categories: labels(n), name: n.name, "
            "attributes: [key in apoc.coll.subtract(keys(n), "
            + cypher_expression.dumps(RESERVED_NODE_PROPS) +
            ") | {original_attribute_name: key, attribute_type_id: COALESCE("
            + cypher_expression.dumps(ATTRIBUTE_TYPES) +
            "[key], \"NA\"), value: n[key]}]}]), "
        )
        if qnodes else
        "nodes: [], "
    )
    aggregate_clause += (
        (
            "edges: apoc.map.fromLists(" + (
            "[e IN collect(DISTINCT kedge) | toString(ID(e)) ], " if kwargs.get("relationship_id", "property") == "internal" else
            "[e IN collect(DISTINCT kedge) | e.id], "
            ) +
            "[e IN collect(DISTINCT kedge) | {"
            "predicate: type(e), subject: startNode(e).id, object: endNode(e).id, "
            "attributes: [key in apoc.coll.subtract(keys(e), "
            + cypher_expression.dumps(RESERVED_EDGE_PROPS + EDGE_SOURCE_PROPS) +
            ") | {original_attribute_name: key, attribute_type_id: COALESCE("
            + cypher_expression.dumps(ATTRIBUTE_TYPES) +
            "[key], \"NA\"), value: e[key]}]," +
            "sources: [key IN " + cypher_expression.dumps(EDGE_SOURCE_PROPS) +" | "
            " {resource_id: e[key] , resource_role: key }]"
            "}])"
        )
        if kedges else
        "edges: []"
    )
    aggregate_clause += "} AS knowledge_graph"
    clauses.append(aggregate_clause)

    # return results and knowledge graph
    return_clause = "RETURN results, knowledge_graph"
    """

    nodes = [f"`{qnode_id}`" for qnode_id in qnodes]
    edges = [f"`{qedge_id}`" for qedge_id in qedges]
    return_clause = 'RETURN '
    if nodes:
        return_clause += ', '.join(nodes)
        if edges:
            return_clause += ', '
    if edges:
        return_clause += ', '.join(edges)
    if not (nodes or edges):
        return_clause += '1'
    clauses.append(return_clause)
    # add SKIP and LIMIT sub-clauses
    clauses.extend(pagination(**kwargs))
    return clauses


def pagination(skip=None, limit=None, **kwargs):
    """Get pagination clauses."""
    clauses = []
    if skip is not None:
        clauses.append(f"SKIP {skip}")
    if limit is not None:
        clauses.append(f"LIMIT {limit}")
    return clauses


def get_query(qgraph, **kwargs):
    """Generate a Cypher query to extract the answer maps for a question.

    Returns the query as a string.
    """
    # commented this out because now we rely on the altering the qgraph to transform results into TRAPI,
    # leaving as a reminder in case that breaks something
    # qgraph = copy.deepcopy(qgraph)
    clauses = []
    query = match_query(qgraph, **kwargs)
    clauses.extend(query.compile())
    where_clause = query.where_clause()
    if where_clause:
        if not clauses[-1].startswith("WITH"):
            clauses.append(query.with_clause())
        clauses.append(where_clause)

    if not kwargs.pop("reasoner", True):
        clauses.append(query.return_clause())
        # add SKIP and LIMIT sub-clauses
        clauses.extend(pagination(**kwargs))
    else:
        clauses.extend(assemble_results(
            query.qgraph["nodes"],
            query.qgraph["edges"],
            **kwargs,
        ))

    return " ".join(clauses)


def transform_result(cypher_result,
                     qgraph: dict,
                     protocol: str = None):
    # use the protocol parameter if it's provided, otherwise use NEO4J_PROTOCOL set by configuration
    if not protocol:
        protocol = NEO4J_PROTOCOL
    if protocol == 'bolt':
        # if the protcol is bolt (from the python driver) cypher_result is a neo4j.Result
        bolt_protocol = True
        # we could check for errors here, but it should happen around the actual driver calls (before this)
    else:
        # otherwise assume it's a jolt http response
        bolt_protocol = False
        # could check for errors like this, but it should happen around the http calls themselves
        # if cypher_result['errors']:
        #    raise Exception(f'Errors in http cypher result: {cypher_result["errors"]}')

    kg_nodes = {}
    kg_edges = {}
    all_qnode_ids = []
    qnode_ids_to_return = []
    qnodes_that_are_sets = set()
    for qnode_id, qnode in qgraph["nodes"].items():
        all_qnode_ids.append(qnode_id)
        if qnode.get('_return', True):
            qnode_ids_to_return.append(qnode_id)
            if qnode.get('set_interpretation', 'BATCH') == 'ALL':
                qnodes_that_are_sets.add(qnode_id)

    jolt_element_id_lookup = {}  # used by jolt implementation to look up nodes by their element ids
    results = {}  # results are grouped by unique sets of result node ids
    record_iterator = cypher_result if bolt_protocol else iterate_through_jolt_response(cypher_result)
    for cypher_record in record_iterator:
        result_nodes = {}
        if bolt_protocol:
            for qnode_id in all_qnode_ids:
                result_nodes[qnode_id] = convert_bolt_node_to_dict(cypher_record[qnode_id])
        else:
            for qnode_id in all_qnode_ids:
                jolt_node = convert_jolt_node_to_dict(cypher_record[qnode_id])
                jolt_element_id_lookup[jolt_node.pop('element_id')] = jolt_node['id']
                result_nodes[qnode_id] = jolt_node

        node_bindings = {}
        result_node_ids_key = ''
        for qnode_id in qnode_ids_to_return:
            result_node = result_nodes[qnode_id]
            if result_node is None:
                node_bindings[qnode_id] = []
                continue

            result_node_id = result_node['id']
            result_node_ids_key += result_node_id
            if qnode_id in qnodes_that_are_sets:
                # if qnode has set_interpretation=ALL there won't be any superclass bindings
                node_bindings[qnode_id] = [{'id': result_node_id, 'attributes': []}]
            else:
                # otherwise create a list of the id mappings including query_ids if they exist
                # and aren't the same as the actual id
                node_bindings[qnode_id] = \
                    [{'id': result_node_id,
                      'query_id': result_nodes[f'{qnode_id}_superclass']['id'],
                      'attributes': []}
                     if f'{qnode_id}_superclass' in all_qnode_ids and
                        result_nodes[f'{qnode_id}_superclass']['id'] != result_node_id else
                     {'id': result_node_id,
                      'attributes': []}]

            if result_node_id not in kg_nodes:
                kg_nodes[result_node_id] = {
                    'name': result_node['name'],
                    'categories': list(result_node.pop('labels'))
                }
                kg_nodes[result_node_id].update(transform_attributes(result_node, node=True))

        edge_bindings = {}
        for qedge_id, qedge in qgraph['edges'].items():
            if not cypher_record[qedge_id]:
                continue
            result_edges = convert_bolt_edge_to_dict(cypher_record[qedge_id]) if bolt_protocol \
                else convert_jolt_edge_to_dict(cypher_record[qedge_id], jolt_element_id_lookup)
            if qedge.get('_return', True):
                for result_edge in result_edges:
                    graph_edge_id = result_edge['id']
                    edge_bindings[qedge_id] = [{'id': graph_edge_id, 'attributes': []}]
                    if graph_edge_id not in kg_edges:
                        kg_edges[graph_edge_id] = {
                            'subject': result_edge['subject'],
                            'predicate': result_edge['predicate'],
                            'object': result_edge['object'],
                            # get properties matching EDGE_SOURCE_PROPS and remove biolink: if needed
                            # then pass (key, value) tuples to construct_sources_tree for formatting
                            'sources': construct_sources_tree([
                                (edge_source_prop.removeprefix('biolink:'), result_edge.get(edge_source_prop))
                                for edge_source_prop in EDGE_SOURCE_PROPS if result_edge.get(edge_source_prop, None)
                            ])
                        }
                        # grab other attributes from the edge and populate qualifiers and attributes
                        kg_edges[graph_edge_id].update(transform_attributes(result_edge, node=False))

        if result_node_ids_key != '':  # avoid adding results for the default node binding key ''
            # if we haven't encountered this specific group of result nodes before, create a new result
            if result_node_ids_key not in results:
                results[result_node_ids_key] = {'analyses': [{'edge_bindings': edge_bindings,
                                                              'resource_id': PROVENANCE_TAG}],
                                                'node_bindings': node_bindings}
            else:
                # otherwise append new edge bindings to the existing result
                for qedge_id, edge_binding_list in edge_bindings.items():
                    results[result_node_ids_key]['analyses'][0]['edge_bindings'][qedge_id].extend(
                        [new_edge_bind for new_edge_bind in edge_binding_list if new_edge_bind['id'] not in
                         [existing_edge_bind['id'] for existing_edge_bind in
                          results[result_node_ids_key]['analyses'][0]['edge_bindings'][qedge_id]]])

    knowledge_graph = {
            'nodes': kg_nodes,
            'edges': kg_edges
        }
    transformed_results = {
        'results': list(results.values()),  # convert the results dictionary to a flattened list
        'knowledge_graph': knowledge_graph
    }
    return transformed_results


# This function takes EDGE_SOURCE_PROPS properties from results, converts them into proper
# TRAPI dictionaries, and assigns the proper upstream ids to each resource. It does not currently attempt to avoid
# duplicate aggregator results, which shouldn't exist in the graphs.
def construct_sources_tree(sources):

    # first find the primary knowledge source, there should always be one
    primary_knowledge_source = None
    formatted_sources = None
    for resource_role, resource_id in sources:
        if resource_role == "primary_knowledge_source":
            primary_knowledge_source = resource_id
            # add it to the formatted TRAPI output
            formatted_sources = [{
                "resource_id": primary_knowledge_source,
                "resource_role": "primary_knowledge_source"
            }]
    if not primary_knowledge_source:
        # we could hard fail here, every edge should have a primary ks, but I haven't fixed all the tests yet
        #     raise KeyError(f'primary_knowledge_source missing from sources section of cypher results! '
        #                    f'sources: {sources}')
        return []

    # then find any aggregator lists
    aggregator_list_sources = []
    for resource_role, resource_id in sources:
        # this looks weird but the idea is that you could have a few parallel lists like:
        # aggregator_knowledge_source, aggregator_knowledge_source_2, aggregator_knowledge_source_3
        if resource_role.startswith("aggregator_knowledge_source"):
            aggregator_list_sources.append(resource_id)
    # walk through the aggregator lists and construct the chains of provenance
    terminal_aggregators = set()
    for aggregator_list in aggregator_list_sources:
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
    return list(formatted_sources)


def transform_attributes(result_item, node=False):

    # make a list of attributes to ignore while processing
    ignore_list = RESERVED_NODE_PROPS if node else EDGE_SOURCE_PROPS + RESERVED_EDGE_PROPS
    ignore_list += ATTRIBUTE_SKIP_LIST

    # an "attributes" attribute in neo4j should be a json list,
    # attempt to start the attributes section of transformed attributes with its contents
    json_attributes_attribute = result_item.pop('attributes', None)
    json_attributes = []
    if json_attributes_attribute:
        try:
            json_attributes = json.loads(json_attributes_attribute)
            if not isinstance(json_attributes, list):
                print(f'! attributes property was not a list, ignoring: {json_attributes_attribute}')
        except json.JSONDecodeError as e:
            print(f'! JSONDecodeError parsing attributes property, it should be a json list, ignoring: {json_attributes_attribute}')
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

    # format the rest of the attributes, look up their attribute type and value type
    transformed_attributes['attributes'].extend([
        {'original_attribute_name': key,
         'value': value,
         # the following function will return
         # 'attribute_type_id': 'biolink-ified attribute type id'
         # 'value_type_id': 'biolink-ified value type id'
         **get_attribute_type_and_value_type(key)}
        for key, value in result_item.items()
        if key not in ignore_list + qualifiers
    ])
    return transformed_attributes


@cache
def get_attribute_type_and_value_type(attribute_name):
    # Determine the attribute_type_id and value_type_id for an attribute.
    # Look in biolink model for the correct values,
    # override biolink model if custom mappings exist in ATTRIBUTE_TYPES or VALUE_TYPES.

    # set defaults, these will be used if neither the biolink model nor custom mappings recognize the attribute
    attr_meta_data = {
        "attribute_type_id": "biolink:Attribute",
        "value_type_id": "EDAM:data_0006",
    }

    # the following section using bmt was borrowed from Plater, it could probably use some work
    # lookup the biolink info
    bl_info = bmt.get_element(attribute_name)

    # does attribute_name exist in the biolink model?
    if bl_info is not None:
        # if there are exact mappings use the first one
        if 'slot_uri' in bl_info:
            attr_meta_data['attribute_type_id'] = bl_info['slot_uri']

            # was there a range value
            if 'range' in bl_info and bl_info['range'] is not None:
                # try to get the type of data
                new_type = bmt.get_element(bl_info['range'])
                # check if new_type is not None. For eg. bl_info['range'] = 'uriorcurie' for things
                # for `relation` .
                if new_type:
                    if 'uri' in new_type and new_type['uri'] is not None:
                        # get the real data type
                        attr_meta_data["value_type_id"] = new_type['uri']
        elif 'class_uri' in bl_info:
            attr_meta_data['attribute_type_id'] = bl_info['class_uri']

    # check custom mappings and override the biolink model if they exist
    if attribute_name in ATTRIBUTE_TYPES:
        attr_meta_data['attribute_type_id'] = ATTRIBUTE_TYPES[attribute_name]
    if attribute_name in VALUE_TYPES:
        attr_meta_data['value_type_id'] = VALUE_TYPES[attribute_name]
    return attr_meta_data


def convert_bolt_node_to_dict(bolt_node):
    if not bolt_node:
        return None
    node = {key: value for key, value in bolt_node.items()}
    node['labels'] = bolt_node.labels
    return node


def convert_jolt_node_to_dict(jolt_node):
    if not jolt_node:
        return None
    node = jolt_node['()'][2]
    node['element_id'] = jolt_node['()'][0]
    node['labels'] = jolt_node['()'][1]
    return node


def convert_bolt_edge_to_dict(bolt_edge):
    if not bolt_edge:
        return None
    # print(bolt_edge)
    bolt_edges = [bolt_edge] if not isinstance(bolt_edge, list) else bolt_edge

    converted_edges = []
    for bolt_edge in bolt_edges:
        edge = {key: value for key, value in bolt_edge.items()}  # start with the properties
        edge.update({  #
            'subject': bolt_edge.start_node.get('id'),
            'predicate': bolt_edge.type,
            'object': bolt_edge.end_node.get('id')})  # add the SPO from the other properties of the bolt response list
        if 'id' not in edge:
            edge['id'] = bolt_edge.element_id  # if the edge didn't have an "id" use the neo4j element id
        converted_edges.append(edge)
    return converted_edges


def convert_jolt_edge_to_dict(jolt_edges, jolt_element_id_lookup):
    if not jolt_edges:
        return None
    # print(jolt_edge)
    convert_edges = []
    jolt_edges = [jolt_edges] if not isinstance(jolt_edges, list) else jolt_edges
    for jolt_edge in jolt_edges:
        jolt_edge = next(iter(jolt_edge.values()))
        edge = jolt_edge[4]  # start with the properties
        edge.update({
            'subject': jolt_element_id_lookup[jolt_edge[1]],
            'predicate': jolt_edge[2],
            'object': jolt_element_id_lookup[jolt_edge[3]]})  # add the SPO from the other items of the jolt response list
        if 'id' not in edge:
            edge['id'] = jolt_edge[0]  # if the edge didn't have an "id" use the neo4j element id
        convert_edges.append(edge)
    return convert_edges


def iterate_through_jolt_response(jolt_response):
    headers = []
    for line in jolt_response.split("\n"):
        line = json.loads(line)
        if 'header' in line:
            headers = line['header']['fields']
        elif 'data' in line:
            data = {header: data_item for (header, data_item) in zip(headers, line['data'])}
            yield data
        elif 'info' in line:
            break


def convert_http_results_to_dict(results: dict) -> list:
    converted_results = []
    if results:
        for result in results:
            cols = result.get('columns')
            if cols:
                data_items = result.get('data')
                for item in data_items:
                    new_row = {}
                    row = item.get('row')
                    for col_name, col_value in zip(cols, row):
                        new_row[col_name] = col_value
                    converted_results.append(new_row)
    return converted_results


def set_custom_attribute_types(attribute_types: dict):
    global ATTRIBUTE_TYPES
    ATTRIBUTE_TYPES = attribute_types


def set_custom_attribute_value_types(value_types: dict):
    global VALUE_TYPES
    VALUE_TYPES = value_types


def set_custom_attribute_skip_list(skip_list: list):
    global ATTRIBUTE_SKIP_LIST
    ATTRIBUTE_SKIP_LIST = skip_list
