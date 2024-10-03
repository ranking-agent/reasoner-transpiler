"""Tools for compiling QGraph into Cypher query."""
import json

from collections import defaultdict

from .attributes import transform_attributes, PROVENANCE_TAG
from .matching import match_query


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
        assemble_clause = f"WITH apoc.coll.toSet({nodes_assemble}) AS nodes, " \
                          f"apoc.coll.toSet({edges_assemble}) AS edges, collect(DISTINCT ["

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


def transform_result(cypher_record,
                     qgraph: dict):

    nodes, edges, paths = unpack_bolt_record(cypher_record)

    # Construct the knowledge_graph["nodes"] section of the TRAPI response
    kg_nodes = {}
    for cypher_node in nodes:
        # Convert the list of unique result nodes from cypher results to dictionaries
        node = convert_bolt_node_to_dict(cypher_node)
        # Convert nodes to TRAPI format
        # id, name, and labels are removed before transform_attributes
        node_id = node.pop('id')
        kg_nodes[node_id] = {
            'name': node.pop('name'),
            'categories': sorted(node.pop('labels'))}
        kg_nodes[node_id].update(**transform_attributes(node, node=True))

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
                node_bindings[qnode_id] = \
                    [{'id': result_node_id if superclass_result_id == result_node_id else superclass_result_id,
                      'attributes': []}]
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
            if not path_edge:
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
            for (subclass_subject_or_object, subclass_qedge_id, superclass_qnode_id) in \
                    qedges_with_attached_subclass_edges.get(qedge_id, []):
                # If so, check to see if there are results for it
                qedge, subclass_edge_element_ids = qedge_id_to_results[subclass_qedge_id]
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
                if aux_graph_id not in aux_graphs:
                    aux_graphs[aux_graph_id] = {
                        "edges": composite_edge_ids,
                        "attributes": []
                    }
                if composite_edge_id not in kg_edges:
                    real_edge = kg_edges[graph_edge_id]
                    inferred_result_edge = {"subject": real_edge["subject"],
                                            "predicate": real_edge["predicate"],
                                            "object": real_edge["object"],
                                            "attributes": [
                                                {
                                                    "attribute_type_id": "biolink:knowledge_level",
                                                    "value": "logical_entailment"
                                                },
                                                {
                                                    "attribute_type_id": "biolink:agent_type",
                                                    "value": "automated_agent",
                                                },
                                                {
                                                    "attribute_type_id": "biolink:support_graphs",
                                                    "value": [aux_graph_id]
                                                }
                                            ],
                                            "sources": [
                                                {
                                                    "resource_id": PROVENANCE_TAG,
                                                    "resource_role": "primary_knowledge_source"
                                                }
                                            ],
                                            # this overwrites subject and/or object with the superclass node ids
                                            # if they exist
                                            **superclass_node_ids}
                    kg_edges[composite_edge_id] = inferred_result_edge

                # make an edge binding with the inferred subclass edge
                edge_bindings[qedge_id] = [{'id': composite_edge_id, 'attributes': []}]
            else:
                # if no subclass edges for this edge make a normal edge binding
                edge_bindings[qedge_id] = [{'id': graph_edge_id, 'attributes': []}]

        if result_key != '':  # avoid adding results for the default node binding key ''
            # if we haven't encountered this specific group of result nodes before, create a new result
            if result_key not in results:
                results[result_key] = {'node_bindings': node_bindings,
                                       'analyses': [{'edge_bindings': edge_bindings,
                                                     'resource_id': PROVENANCE_TAG}]}
            else:
                # otherwise append new edge bindings to the existing result
                for qedge_id, edge_binding_list in edge_bindings.items():
                    results[result_key]['analyses'][0]['edge_bindings'][qedge_id].extend(
                        [new_edge_bind for new_edge_bind in edge_binding_list if new_edge_bind['id'] not in
                         [existing_edge_bind['id'] for existing_edge_bind in
                          results[result_key]['analyses'][0]['edge_bindings'][qedge_id]]])

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


def transform_edges_list(edges):
    # See convert_bolt_edge_to_dict() for details on the contents of edges,
    # it is a list of lists (which can also be lists), representing unique edges from the graph
    kg_edges = {}
    element_id_to_edge_id = {}
    edge_index = 1
    for cypher_edge_result in edges:
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

        # transform the edge(s) into TRAPI
        for cypher_edge in cypher_edges:
            # get the element id from the cypher results (see convert_bolt_edge_to_dict for more details)
            edge_element_id = cypher_edge[0]
            # skip the edge if we already processed it
            # this prevents duplicating effort for cases where a subclass edge is included multiple times in a result
            # this can happen because neo4j tries to deduplicate, but variable length subclass edges fail
            # to match a single edge even when the single edge is part of the variable length edge
            if edge_element_id in element_id_to_edge_id:
                continue

            # transform the edge into TRAPI and return:
            # edge_id - the edge id that will be used for edges in the TRAPI knowledge graph and edge bindings
            # trapi_edge - a dictionary that represents an edge in the knowledge_graph part of the TRAPI response
            edge_id, trapi_edge = convert_bolt_edge_to_trapi(cypher_edge)
            if not edge_id:
                edge_id = f'e_{edge_index}'
            # make a mapping that will be used to look up the edge id by element id later
            element_id_to_edge_id[edge_element_id] = edge_id
            # add it to the knowledge graph
            kg_edges[edge_id] = trapi_edge
            edge_index += 1
    # returns the TRAPI knowledge graph edges and a lookup mapping of edge element id -> TRAPI edge id
    return kg_edges, element_id_to_edge_id


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


# Convert a list representing an edge from cypher results into a dictionary.
# This is not any standard object from the bolt driver, it's a list generated by a specific cypher return clause, like:
# [elementId(edge_1), startNode(edge_1).id, type(edge_1), endNode(edge_1).id, properties(edge_1)]
# This is done to prevent including often redundant node and edge properties on nodes and edges in pathway results.
# See the cypher generated in the edges_assemble clause in assemble_results() for more details.
def convert_bolt_edge_to_trapi(bolt_edge):
    if not bolt_edge:
        print(f'Tried to convert a missing edge: {bolt_edge}')
        return None, None

    converted_edge = {
        'subject': bolt_edge[1],
        'predicate': bolt_edge[2],
        'object': bolt_edge[3],
    }
    # edge_props - any other properties from the edge
    edge_props = {**bolt_edge[4]}

    # retrieve and remove the id if there is one on the edge
    edge_id = edge_props.pop('id', None)

    # convert all remaining attributes to TRAPI format, constructing the attributes and sources sections
    converted_edge.update(transform_attributes(edge_props, node=False))

    # return the edge id if there was one, and a TRAPI edge
    return edge_id, converted_edge


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


def unpack_bolt_record(bolt_record):
    return bolt_record['nodes'], bolt_record['edges'], bolt_record['paths']


def unpack_jolt_result(jolt_response):
    headers = []
    for line in jolt_response.split("\n"):
        line = json.loads(line)
        if 'header' in line:
            headers = line['header']['fields']
        elif 'data' in line:
            data = {header: data_item for (header, data_item) in zip(headers, line['data'])}
            return data['nodes'], data['edges'], data['paths']
