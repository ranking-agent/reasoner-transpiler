"""Tools for compiling QGraph into Cypher query."""
from functools import reduce
from operator import and_

from reasoner.matching import match_query
from reasoner.util import mapize


def nest_op(operator, *args):
    """Generate a nested set of operations from a flat expression."""
    if len(args) > 2:
        return [operator, args[0], nest_op(operator, *args[1:])]
    else:
        return [operator, *args]


def transpile_compound(qgraph, **kwargs):
    """Transpile compound qgraph."""
    if isinstance(qgraph, dict):
        return match_query(
            qgraph,
            **kwargs,
        )
    if qgraph[0] == 'OR':
        qgraph = nest_op(*qgraph)

    args = [
        transpile_compound(arg, **kwargs)
        for arg in qgraph[1:]
    ]
    if qgraph[0] == 'AND':
        return reduce(and_, args)
    elif qgraph[0] == 'OR':
        return args[0] | args[1]
    elif qgraph[0] == 'XOR':
        if len(args) != 2:
            raise ValueError('XOR must have exactly two operands')
        return args[0] ^ args[1]
    elif qgraph[0] == 'NOT':
        if len(args) != 1:
            raise ValueError('NOT must have exactly one operand')
        return ~args[0]
    raise ValueError(f'Unrecognized operator "{qgraph[0]}"')


def assemble_results(qnodes, qedges, **kwargs):
    """Assemble results into Reasoner format."""
    clauses = []

    # assemble result (bindings) and associated (result) kgraph
    node_bindings = [
        (
            '[ni IN collect(DISTINCT `{0}`.id) '
            'WHERE ni IS NOT null '
            '| {{qg_id:"{0}", kg_id:ni}}]'
        ).format(
            qnode_id,
        ) if qnode.get('set', False) else
        (
            '(CASE '
            'WHEN {0} IS NOT NULL THEN [{{qg_id:"{0}", kg_id:{0}.id}}] '
            'ELSE [] '
            'END)'
        ).format(qnode_id)
        for qnode_id, qnode in qnodes.items()
    ]
    edge_bindings = [
        (
            '[ei IN collect(DISTINCT toString(id(`{0}`))) '
            'WHERE ei IS NOT null '
            '| {{qg_id:"{0}", kg_id:ei}}]'
        ).format(
            qedge_id,
        ) if kwargs.get('relationship_id', 'property') == 'internal' else
        (
            '[ei IN collect(DISTINCT `{0}`.id) '
            'WHERE ei IS NOT null '
            '| {{qg_id:"{0}", kg_id:ei}}]'
        ).format(
            qedge_id,
        )
        for qedge_id in qedges
    ]
    knodes = [
        'collect(DISTINCT `{0}`)'.format(qnode_id)
        for qnode_id in qnodes
    ]
    kedges = [
        'collect(DISTINCT `{0}`)'.format(qedge_id)
        for qedge_id in qedges
    ]
    assemble_clause = (
        'WITH {{node_bindings: {0}, edge_bindings: {1}}} AS result, '
        '{{nodes:{2}, edges: {3}}} AS knowledge_graph'
    ).format(
        ' + '.join(node_bindings) or '[]',
        ' + '.join(edge_bindings) or '[]',
        ' + '.join(knodes) or '[]',
        ' + '.join(kedges) or '[]',
    )
    clauses.append(assemble_clause)

    # add SKIP and LIMIT sub-clauses
    clauses.extend(pagination(**kwargs))

    # collect results and aggregate kgraphs
    # also fetch extra knode/kedge properties
    if qnodes:
        clauses.append('UNWIND knowledge_graph.nodes AS knode')
    if qedges:
        clauses.append('UNWIND knowledge_graph.edges AS kedge')
    aggregate_clause = 'WITH collect(DISTINCT result) AS results, {'
    aggregate_clause += (
        'nodes: [n IN collect(DISTINCT knode) | n{.*, type:labels(n)}], '
        if qnodes else
        'nodes: [], '
    )
    aggregate_clause += (
        'edges: [e IN collect(DISTINCT kedge) | e{.*, type:type(e), '
        'source_id: startNode(e).id, target_id: endNode(e).id}]'
        if qedges else
        'edges: []'
    )
    aggregate_clause += '} AS knowledge_graph'
    clauses.append(aggregate_clause)

    # return results and knowledge graph
    return_clause = 'RETURN results, knowledge_graph'
    clauses.append(return_clause)
    return clauses


def pagination(**kwargs):
    """Get pagination clauses."""
    clauses = []
    if 'skip' in kwargs:
        clauses.append(f'SKIP {kwargs["skip"]}')
    if 'limit' in kwargs:
        clauses.append(f'LIMIT {kwargs["limit"]}')
    return clauses


def get_query(qgraph, **kwargs):
    """Generate a Cypher query to extract the answer maps for a question.

    Returns the query as a string.
    """
    # convert all component simple qgraphs into map-form
    qgraph = mapize(qgraph)

    clauses = []
    query = transpile_compound(qgraph, **kwargs)
    clauses.extend(query.compile())
    where_clause = query.where_clause()
    if where_clause:
        if not clauses[-1].startswith('WITH'):
            clauses.append(query.with_clause())
        clauses.append(where_clause)

    if not kwargs.pop('reasoner', True):
        clauses.append(query.return_clause())
        # add SKIP and LIMIT sub-clauses
        clauses.extend(pagination(**kwargs))
    else:
        clauses.extend(assemble_results(
            query.qgraph['nodes'],
            query.qgraph['edges'],
            **kwargs,
        ))

    return ' '.join(clauses)
