"""Tools for compiling QGraph into Cypher query."""
import os
import json

from pathlib import Path
from collections import defaultdict

from .biolink import bmt
from .matching import match_query

DIR_PATH = Path(__file__).parent

with open(DIR_PATH / "attribute_types.json", "r") as stream:
    ATTRIBUTE_TYPES = json.load(stream)

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
            raise NotImplementedError(f'This feature is currently not implemented: set_interpretation=MANY')

    # TODO - implement pagination (SKIP and LIMIT)
    #  right now SKIP and LIMIT are unsupported and this will throw NotImplementedError if they are requested
    pagination(**kwargs)

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

    nodes = [f"`{qnode_id}`.id" for qnode_id, qnode in qnodes.items()]
    edges = [f"elementId(`{qedge_id}`)" if not qedge.get('_subclass', False) else f"[x in `{qedge_id}` | elementId(x)]"
             for qedge_id, qedge in qedges.items()]
    if nodes or edges:
        nodes_assemble = " + ".join([
            f"collect(`{qnode_id}`)"
            for qnode_id, qnode in qnodes.items()
        ])
        if not nodes_assemble:
            nodes_assemble = '[]'
        edges_assemble = " + ".join([
            f"collect([elementId(`{qedge_id}`), startNode(`{qedge_id}`).id, "
            f"type(`{qedge_id}`), endNode(`{qedge_id}`).id, properties(`{qedge_id}`)])"
            if not qedge.get('_subclass', False) else
            f"collect([x in `{qedge_id}` | [elementId(x), startNode(x).id, "
            f"type(x), endNode(x).id, properties(x)]])"
            for qedge_id, qedge in qedges.items()
        ])
        if not edges_assemble:
            edges_assemble = '[]'
        assemble_clause = f"WITH apoc.coll.toSet({nodes_assemble}) AS nodes, apoc.coll.toSet({edges_assemble}) AS edges, collect(DISTINCT ["

        if nodes:
            assemble_clause += ', '.join(nodes)
            if edges:
                assemble_clause += ', '
        if edges:
            assemble_clause += ', '.join(edges)
        assemble_clause += "]) AS paths "
        clauses.append(assemble_clause)
        return_clause = "RETURN nodes, edges, paths"
    else:
        return_clause = 'RETURN [] as nodes, [] as edges, [] as paths'

    clauses.append(return_clause)
    return clauses


def pagination(skip=None, limit=None, **kwargs):
    """Get pagination clauses."""
    clauses = []
    if skip is not None:
        raise NotImplementedError(f'SKIP is not currently implemented.')
        # clauses.append(f"SKIP {skip}")
    if limit is not None:
        raise NotImplementedError(f'LIMIT is not currently implemented.')
        # clauses.append(f"LIMIT {limit}")
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

    nodes, edges, paths = unpack_bolt_result(cypher_result) if bolt_protocol else unpack_jolt_result(cypher_result)

    # Convert the list of unique result nodes from cypher results to dictionaries
    # then convert them to TRAPI format, constructing the knowledge_graph["nodes"] section of the TRAPI response
    kg_nodes = transform_nodes_list(nodes)

    # Convert the list of unique edges from cypher results to dictionaries
    # then convert them to TRAPI format, constructing the knowledge_graph["edges"] section of the TRAPI response.
    # Also make a mapping of the neo4j element_id to the edge id to be used in the TRAPI edge bindings
    # the edge id used in TRAPI is the 'id' property on the edge if there is one, otherwise assigned integers 0,1,2..
    kg_edges, element_id_to_edge_id = transform_edges_list(edges)

    results = {}  # results are grouped by unique sets of result node ids
    aux_graphs = {}  # auxiliary_graphs

    qgraph_nodes = qgraph["nodes"]
    qnodes_with_set_interpretation_all = {qnode_id for qnode_id, qnode in qgraph_nodes.items()
                                          if qnode.get('set_interpretation', 'BATCH') == 'ALL'}
    qnodes_with_superclass_nodes = {qnode_id for qnode_id, qnode in qgraph_nodes.items()
                                    if f'{qnode_id}_superclass' in qgraph_nodes}

    qgraph_edges = qgraph["edges"]
    qedges_with_attached_subclass_edges = defaultdict(list)
    for qedge_id, qedge in qgraph_edges.items():
        if not qedge.get('_subclass', False):
            if qedge["subject"] in qnodes_with_superclass_nodes:
                qedges_with_attached_subclass_edges[qedge_id].append(
                    ('subject', f'{qedge["subject"]}_subclass_edge', f'{qedge["subject"]}_superclass'))
            if qedge["object"] in qnodes_with_superclass_nodes:
                qedges_with_attached_subclass_edges[qedge_id].append(
                    ('object', f'{qedge["object"]}_subclass_edge',  f'{qedge["object"]}_superclass'))

    # Each path is an array of nodes and edges like [n1, n2, n3, e1, e2, e3],
    # where nodes are node_ids from the graph and edges are element_ids of relationships from the graph.
    for path in paths:
        skip_this_path = False

        # Map results/paths to their corresponding qnodes and qedges
        qnode_id_to_results = {qnode_id: (qnode, result_node_id) for (qnode_id, qnode), result_node_id in
                               zip(qgraph_nodes.items(), path[:len(qgraph_nodes)])}
        qedge_id_to_results = {qedge_id: (qedge, result_edge_id) for (qedge_id, qedge), result_edge_id in
                               zip(qgraph_edges.items(), path[-len(qgraph_edges):])}

        # results are grouped by unique sets of nodes, concatenating node ids to this string generates the key
        result_key = ""

        # create TRAPI node bindings
        edge_bindings = {}
        node_bindings = {}
        support_graphs = set()
        for qnode_id, (qnode, result_node_id) in qnode_id_to_results.items():

            # don't return superclass qnodes in the node bindings
            if qnode.get('_superclass', False):
                continue
            # if there isn't a result for this node set an empty node binding
            if not result_node_id:
                node_bindings[qnode_id] = []
                continue

            # create a node binding
            if qnode_id in qnodes_with_set_interpretation_all:
                # if qnode has set_interpretation=ALL there won't be any superclass bindings
                node_bindings[qnode_id] = [{'id': result_node_id, 'attributes': []}]

            elif qnode_id in qnodes_with_superclass_nodes:
                # If the qnode has a superclass node, and it has a different result node id,
                # use the superclass result node id instead, because it's the actual query id.
                # We used to include the query_id property here to show that, but now we're making a support graph
                # that can represent the underlying subclass edge(s).
                superclass_qnode, superclass_result_id = qnode_id_to_results[f'{qnode_id}_superclass']
                if superclass_result_id == result_node_id:
                    node_bindings[qnode_id] = \
                        [{'id': result_node_id,
                          'attributes': []}]
                else:
                    node_bindings[qnode_id] = \
                        [{'id': superclass_result_id,
                          'attributes': []}]
                    # for cases where we have a node with a superclass node, but no qedges_with_attached_subclass_edges,
                    # it means the query had unconnected nodes we need to make support graphs for
                    if not qedges_with_attached_subclass_edges:
                        # find the results for the subclass edge
                        subclass_qedge = f'{qnode_id}_subclass_edge'
                        qedge, subclass_edge_element_ids = qedge_id_to_results[subclass_qedge]
                        # make a list of ids for the subclass edges
                        composite_edges = [element_id_to_edge_id[ele_id] for ele_id in subclass_edge_element_ids]
                        # make a composite id with all of their kg edge ids
                        composite_edge_id = "_".join(composite_edges)
                        aux_graph_id = f"aux_{composite_edge_id}"
                        support_graphs.add(aux_graph_id)
                        if composite_edge_id not in aux_graphs:
                            aux_graphs[f"aux_{composite_edge_id}"] = {
                                "edges": composite_edges,
                                "attributes": []
                            }
            else:
                # Otherwise, create a normal node binding.
                node_bindings[qnode_id] = \
                    [{'id': result_node_id,
                      'attributes': []}]

            # add the result node id to the result key
            result_key += node_bindings[qnode_id][0]['id']

        # Create TRAPI edge bindings
        for qedge_id, (qedge, path_edge) in qedge_id_to_results.items():

            # skip empty results
            if not path_edge or skip_this_path:
                continue
            # don't return subclass qedges in the edge bindings
            if qedge.get("_subclass", False):
                continue

            # find the knowledge graph edge id for the element id from the path edge
            edge_element_id = path_edge
            graph_edge_id = element_id_to_edge_id[edge_element_id]

            # Check to see if the edge has subclass edges that are connected to it
            subclass_edge_ids = []
            superclass_node_ids = {}
            for (subclass_subject_or_object, subclass_qedge_id, superclass_qnode_id) in qedges_with_attached_subclass_edges.get(qedge_id, []):
                # If so, check to see if there are results for it
                qedge, subclass_edge_element_ids = qedge_id_to_results[subclass_qedge_id]
                # This handles cases where a subclass edge is part of the actual result but is also getting included
                # in the subclass inference edge which creates a useless and weird result using the same edge twice.
                # Just ignore them instead, because the result with one subclass edge should still be accounted for
                # separately with the direct path.
                if edge_element_id in subclass_edge_element_ids:
                    skip_this_path = True
                    continue
                if subclass_edge_element_ids:
                    # If path_edge is Truthy, it means the subclass was used in the result.
                    # For subclass edges, path result is a list of element ids, due to being a variable length edge.
                    # make a list of the subclass edges plus the result edge from the query.
                    subclass_edge_ids.extend([element_id_to_edge_id[ele_id] for ele_id in subclass_edge_element_ids])

                    qnode, superclass_result_node_id = qnode_id_to_results[superclass_qnode_id]
                    superclass_node_ids[subclass_subject_or_object] = superclass_result_node_id

            if subclass_edge_ids:
                # make a composite id with all of their kg edge ids
                composite_edge_ids = [graph_edge_id] + subclass_edge_ids
                composite_edge_id = "_".join(composite_edge_ids)
                aux_graph_id = f"aux_{composite_edge_id}"
                support_graphs.add(aux_graph_id)
                if composite_edge_id not in kg_edges:
                    aux_graphs[f"aux_{composite_edge_id}"] = {
                        "edges": composite_edge_ids,
                        "attributes": []
                    }
                    real_edge = kg_edges[graph_edge_id]
                    inferred_result_edge = {"subject": real_edge["subject"],
                                            "predicate": real_edge["predicate"],
                                            "object": real_edge["object"],
                                            "attributes": [
                                                {
                                                    "value": "logical_entailment",
                                                    "attribute_type_id": "biolink:knowledge_level"
                                                },
                                                {
                                                    "value": "automated_agent",
                                                    "attribute_type_id": "biolink:agent_type"
                                                }
                                            ],
                                            "sources": [
                                                {
                                                    "resource_id": PROVENANCE_TAG,
                                                    "resource_role": "primary_knowledge_source"
                                                }
                                            ],
                                            **superclass_node_ids}
                    kg_edges[composite_edge_id] = inferred_result_edge

                # make an edge binding with the inferred subclass edge
                edge_bindings[qedge_id] = [{'id': composite_edge_id, 'attributes': []}]
            else:
                # if no subclass edges for this edge make a normal edge binding
                edge_bindings[qedge_id] = [{'id': graph_edge_id, 'attributes': []}]

        if result_key != '' and not skip_this_path:  # avoid adding results for the default node binding key ''
            # if we haven't encountered this specific group of result nodes before, create a new result
            if result_key not in results:
                results[result_key] = {'analyses': [{'edge_bindings': edge_bindings,
                                                     'resource_id': PROVENANCE_TAG}],
                                       'node_bindings': node_bindings}
                if support_graphs:
                    results[result_key]['analyses'][0]['support_graphs'] = sorted(support_graphs)

            else:
                # otherwise append new edge bindings to the existing result
                for qedge_id, edge_binding_list in edge_bindings.items():
                    results[result_key]['analyses'][0]['edge_bindings'][qedge_id].extend(
                        [new_edge_bind for new_edge_bind in edge_binding_list if new_edge_bind['id'] not in
                         [existing_edge_bind['id'] for existing_edge_bind in
                          results[result_key]['analyses'][0]['edge_bindings'][qedge_id]]])
                if support_graphs:
                    if 'support_graphs' not in results[result_key]['analyses'][0]:
                        results[result_key]['analyses'][0]['support_graphs'] = sorted(support_graphs)
                    else:
                        support_graphs.update(results[result_key]['analyses'][0]['support_graphs'])
                        results[result_key]['analyses'][0]['support_graphs'] = sorted(support_graphs)

    knowledge_graph = {
        'nodes': kg_nodes,
        'edges': kg_edges
    }
    transformed_results = {
        'results': list(results.values()),  # convert the results dictionary to a flattened list
        'knowledge_graph': knowledge_graph,
        'auxiliary_graphs': aux_graphs
    }
    return transformed_results


def transform_nodes_list(nodes):
    kg_nodes = {}
    for cypher_node in nodes:
        node = convert_bolt_node_to_dict(cypher_node)
        kg_nodes[node['id']] = {
            'name': node['name'],
            'categories': list(node.pop('labels')),
            **transform_attributes(node, node=True)}
    return kg_nodes


def transform_edges_list(edges):
    kg_edges = {}
    element_id_to_edge_id = {}
    for edge_index, cypher_edge_result in enumerate(edges):
        # skip an empty list
        if len(cypher_edge_result) == 0:
            cypher_edges = []
        # check to see if it's a list of lists (multiple edges)
        elif isinstance(cypher_edge_result[0], list):
            cypher_edges = cypher_edge_result
        else:
            # otherwise it's just one list (one edge)
            cypher_edges = list()  # this looks weird, but it's necessary to make a list of one list (I think?)
            cypher_edges.append(cypher_edge_result)

        # transform the edge into TRAPI
        for cypher_edge in cypher_edges:
            edge_element_id, edge_dict = convert_bolt_edge_to_dict(cypher_edge)
            edge_id = edge_dict.get('id', edge_index)
            element_id_to_edge_id[edge_element_id] = edge_id
            # get properties matching EDGE_SOURCE_PROPS keys, remove biolink: if needed,
            # then pass (key, value) tuples to construct_sources_tree for formatting, constructing the 'sources' section
            edge_dict['sources'] = construct_sources_tree([
                    (edge_source_prop.removeprefix('biolink:'), edge_dict.get(edge_source_prop))
                    for edge_source_prop in EDGE_SOURCE_PROPS if edge_dict.get(edge_source_prop, None)])
            # convert all remaining attributes to TRAPI format
            edge_dict.update(transform_attributes(edge_dict, node=False))
            kg_edges[edge_id] = edge_dict
    return kg_edges, element_id_to_edge_id


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

    # an "attributes" attribute in neo4j should be a list of json strings,
    # attempt to start the attributes section of transformed attributes with its contents
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

    # format the rest of the attributes, look up their attribute type and value type
    transformed_attributes['attributes'].extend([
        {'original_attribute_name': key,
         'value': value,
         # the following function will return
         # 'attribute_type_id': 'biolink-ified attribute type id'
         # 'value_type_id': 'biolink-ified value type id'
         **ATTRIBUTE_TYPES.get(key, DEFAULT_ATTRIBUTE_TYPE)}
        for key, value in result_item.items()
        if key not in ignore_list + qualifiers
    ])
    return transformed_attributes


def convert_bolt_node_to_dict(bolt_node):
    if not bolt_node:
        return None
    node = {key: value for key, value in bolt_node.items()}
    # node['element_id'] = bolt_node.element_id
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
        print(f'Tried to convert a missing edge: {bolt_edge}')
        return None, None

    # Convert a list representing an edge from cypher results into a dictionary.
    # This is not a standard Edge object from the bolt driver, it's a list product of a specific cypher return format.
    # This is done to prevent including redundant node information on every edge.
    # See the cypher generated in the edges_assemble clause in assemble_results() for more details.
    element_id = bolt_edge[0]
    converted_edge = {
        'subject': bolt_edge[1],
        'predicate': bolt_edge[2],
        'object': bolt_edge[3],
        **bolt_edge[4]
    }
    return element_id, converted_edge


def convert_jolt_edge_to_dict(jolt_edges, jolt_element_id_lookup):
    if not jolt_edges:
        return None
    convert_edges = []
    jolt_edges = [jolt_edges] if not isinstance(jolt_edges, list) else jolt_edges
    for jolt_edge in jolt_edges:
        jolt_edge = next(iter(jolt_edge.values()))
        edge = jolt_edge[4]  # start with the properties
        # add the SPO from the other items of the jolt edge list
        edge.update({
            'subject': jolt_element_id_lookup[jolt_edge[1]],
            'predicate': jolt_edge[2],
            'object': jolt_element_id_lookup[jolt_edge[3]]})
        if 'id' not in edge:
            edge['id'] = jolt_edge[0]  # if the edge didn't have an "id" use the neo4j element id
        convert_edges.append(edge)
    return convert_edges


def unpack_bolt_result(bolt_response):
    record = bolt_response.single()
    return record['nodes'], record['edges'], record['paths']


def unpack_jolt_result(jolt_response):
    headers = []
    for line in jolt_response.split("\n"):
        line = json.loads(line)
        if 'header' in line:
            headers = line['header']['fields']
        elif 'data' in line:
            data = {header: data_item for (header, data_item) in zip(headers, line['data'])}
            return data['nodes'], data['edges'], data['paths']


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


def set_custom_attribute_skip_list(skip_list: list):
    global ATTRIBUTE_SKIP_LIST
    ATTRIBUTE_SKIP_LIST = skip_list
