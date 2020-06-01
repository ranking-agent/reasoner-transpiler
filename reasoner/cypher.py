"""Tools for compiling QGraph into Cypher query."""
from functools import reduce
from operator import and_

from reasoner.matching import match_query
from reasoner.util import mapize


def transpile_compound(qgraph):
    """Transpile compound qgraph."""
    def nest_op(operator, *args):
        """Generate a nested set of operations from a flat expression."""
        if len(args) > 2:
            return [operator, args[0], nest_op(operator, *args[1:])]
        else:
            return [operator, *args]

    if isinstance(qgraph, dict):
        return match_query(
            qgraph,
        )
    if qgraph[0] == 'OR':
        qgraph = nest_op(*qgraph)

    args = [
        transpile_compound(arg)
        for arg in qgraph[1:]
    ]
    if qgraph[0] == 'AND':
        return reduce(and_, args)
    elif qgraph[0] == 'OR':
        if len(args) != 2:
            raise ValueError('OR must have exactly two operands')
        return args[0] | args[1]
    elif qgraph[0] == 'XOR':
        if len(args) != 2:
            raise ValueError('XOR must have exactly two operands')
        return args[0] ^ args[1]
    raise ValueError(f'Unrecognized operator "{qgraph[0]}"')


def get_query(qgraph, **kwargs):
    """Generate a Cypher query to extract the answer maps for a question.

    Returns the query as a string.
    """
    # convert all component simple qgraphs into map-form
    mapize(qgraph)

    clauses = []
    query = transpile_compound(qgraph)
    clauses.append(query.compile())
    clauses.append(query.where_clause())
    qnodes = query.qgraph['nodes']
    qedges = query.qgraph['edges']

    # assemble result (bindings) and associated (result) kgraph
    node_bindings = [
        (
            '[ni IN collect(DISTINCT `{0}`.id) '
            '| {{qg_id:"{0}", kg_id:ni}}]'
        ).format(
            qnode_id,
        ) if qnode.get('set', False) else
        '[{{qg_id:"{0}", kg_id:`{0}`.id}}]'.format(qnode_id)
        for qnode_id, qnode in qnodes.items()
    ]
    edge_bindings = [
        (
            '[ei IN collect(DISTINCT toString(id(`{0}`))) '
            '| {{qg_id:"{0}", kg_id:ei}}]'
        ).format(
            qedge_id,
        ) if kwargs.get('relationship_id', 'property') == 'internal' else
        (
            '[ei IN collect(DISTINCT `{0}`.id) '
            '| {{qg_id:"{0}", kg_id:ei}}]'
        ).format(
            qedge_id,
        )
        for qedge_id in qedges
    ]
    knodes = ' + '.join([
        'collect(DISTINCT `{0}`)'.format(qnode_id)
        for qnode_id in qnodes
    ])
    kedges = ' + '.join([
        'collect(DISTINCT `{0}`)'.format(qedge_id)
        for qedge_id in qedges
    ])
    assemble_clause = (
        'WITH {{node_bindings: {0}, edge_bindings: {1}}} AS result, '
        '{{nodes:{2}, edges: {3}}} AS knowledge_graph'
    ).format(
        ' + '.join(node_bindings) or '[]',
        ' + '.join(edge_bindings) or '[]',
        knodes,
        kedges,
    )
    clauses.append(assemble_clause)

    # add SKIP and LIMIT sub-clauses
    if 'skip' in kwargs:
        clauses.append(f'SKIP {kwargs["skip"]}')
    if 'limit' in kwargs:
        clauses.append(f'LIMIT {kwargs["limit"]}')

    # collect results and aggregate kgraphs
    # also fetch extra knode/kedge properties
    aggregate_clause = (
        'UNWIND knowledge_graph.nodes AS knode '
        'UNWIND knowledge_graph.edges AS kedge '
        'WITH collect(DISTINCT result) AS results, {'
        'nodes: [n IN collect(DISTINCT knode) | n{.*, type:labels(n)}], '
        'edges: [e IN collect(DISTINCT kedge) | e{.*, type:type(e), '
        'source_id: startNode(e).id, target_id: endNode(e).id}]'
        '} AS knowledge_graph'
    )
    clauses.append(aggregate_clause)

    # return results and knowledge graph
    return_clause = 'RETURN results, knowledge_graph'
    clauses.append(return_clause)

    return ' '.join(clauses)
