"""Tools for compiling QGraph into Cypher query."""
from collections import ChainMap
from functools import reduce
from operator import and_
import re

from jinja2 import Template


def cypher_prop_string(value):
    """Convert property value to cypher string representation."""
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, str):
        return '"{0}"'.format(
            value.replace('"', '\\"')
        )
    if isinstance(value, (float, int)):
        return str(value)
    raise ValueError(f'Unsupported property type: {type(value).__name__}.')


class NodeReference():
    """Node reference object."""

    def __init__(self, node, anonymous=False):
        """Create a node reference.

        All node properties of types [str, bool, float/int] will be enforced
        verbatim EXCEPT for the following reserved properties:
        * id
        * type
        * curie
        * name
        * set
        Un-reserved properties with other types will be coerced to str.
        """
        node = dict(node)  # shallow copy
        self.name = '`' + node.pop('id') + '`' if not anonymous else ''
        self.labels = node.pop('type', ['named_thing'])
        if not isinstance(self.labels, list):
            self.labels = [self.labels]

        props = {}
        self._filters = ''
        curie = node.pop('curie', None)
        if isinstance(curie, list) and len(curie) == 1:
            curie = curie[0]
        if isinstance(curie, str):
            props['id'] = curie
        elif isinstance(curie, list):
            self._filters = ' OR '.join([
                '{0}.id = {1}'.format(
                    self.name,
                    cypher_prop_string(ci)
                )
                for ci in curie
            ])
        elif curie is not None:
            # coerce to a string
            props['id'] = str(curie)

        props.update(
            (key, value)
            for key, value in node.items()
            if key not in ('name', 'set')
        )

        self.prop_string = ' {' + ', '.join([
            f'`{key}`: {cypher_prop_string(props[key])}' for key in props
        ]) + '}' if props else ''
        self._extras = ''
        if curie:
            self._extras = f' USING INDEX {self.name}:{self.labels[0]}(id)'
        self._num = 0

    def __str__(self):
        """Return the cypher node reference."""
        self._num += 1
        if self._num > 1:
            return f'({self.name})'
        return f'({self.name}' \
            + ''.join(f':`{label}`' for label in self.labels) \
            + f'{self.prop_string})'

    @property
    def filters(self):
        """Return filters for the cypher node reference.

        To be used in a WHERE clause following the MATCH clause.
        """
        if self._num > 1:
            return ''
        return self._filters

    @property
    def extras(self):
        """Return extras for the cypher node reference.

        To be appended to the MATCH clause.
        """
        if self._num > 1:
            return ''
        return self._extras


class MissingReference(NodeReference):
    """Missing node reference object."""

    def __init__(self, name):  # pylint: disable=super-init-not-called
        """Initialize."""
        self.name = f'`{name}`'
        self._num = 1


class EdgeReference():
    """Edge reference object."""

    def __init__(self, edge, anonymous=False):
        """Create an edge reference."""
        self.name = edge['id'] if not anonymous else ''
        self.label = edge.get('type', None)
        self.filters = ''

        if isinstance(self.label, list):
            self.filters = ' OR '.join(
                f'type({self.name}) = "{predicate}"'
                for predicate in self.label
            )
            self.label = None

        self.directed = edge.get('directed', bool(self.label))

    def __str__(self):
        """Return the cypher edge reference."""
        return '-[`{0}`{1}]-'.format(
            self.name,
            ':' + self.label if self.label else '',
        ) + ('>' if self.directed else '')


def get_match_clause(qgraph, max_connectivity=-1, **kwargs):
    """Generate a Cypher MATCH clause.

    Returns the query fragment as a string.
    """
    nodes, edges = qgraph['nodes'], qgraph['edges']

    # generate internal node and edge variable names
    node_references = {n['id']: NodeReference(n) for n in nodes}

    clauses = []

    # match orphaned nodes
    all_nodes = {n['id'] for n in nodes}
    all_referenced_nodes = set(
        [e['source_id'] for e in edges]
        + [e['target_id'] for e in edges]
    )
    orphaned_nodes = all_nodes - all_referenced_nodes
    missing_nodes = all_referenced_nodes - all_nodes
    for node_id in missing_nodes:
        node_references[node_id] = MissingReference(node_id)
    for node_id in orphaned_nodes:
        clauses.append(
            f'OPTIONAL MATCH {node_references[node_id]}'
            + node_references[node_id].extras
        )
        if node_references[node_id].filters:
            clauses.append('WHERE ' + node_references[node_id].filters)

    # match edges
    for edge in edges:
        eref = EdgeReference(edge)
        source_node = node_references[edge['source_id']]
        target_node = node_references[edge['target_id']]
        clauses.append(
            f'OPTIONAL MATCH {source_node}{eref}{target_node}'
            + source_node.extras + target_node.extras
        )
        filters = [f'({c})' for c in [
            source_node.filters, target_node.filters, eref.filters
        ] if c]
        if max_connectivity > -1:
            filters.append('(size( {0}-[]-() ) < {1})'.format(
                target_node,
                max_connectivity,
            ))
        if filters:
            clauses.append('WHERE ' + ' AND '.join(filters))

    return Query(
        ' '.join(clauses),
        nodes={node['id']: node['id'] for node in qgraph['nodes']},
        edges={edge['id']: edge['id'] for edge in qgraph['edges']},
    )


def get_qids(qgraph):
    """Get all qids in qgraph."""
    return {node['id'] for node in qgraph['nodes']} \
        | {edge['id'] for edge in qgraph['edges']}


class Query():
    """Cypher query segment."""

    def __init__(
            self,
            string,
            nodes=None, edges=None,
    ):
        """Initialize."""
        self._string = string
        self._nodes = nodes
        self._edges = edges
        self.context = None

    @property
    def logic(self):
        """Return whether qid is required."""
        conditions = [
            f'{qid} IS NOT null' for qid in self.qids
        ]
        if len(self.qids) > 1:
            conditions = [
                f'({condition})' for condition in conditions
            ]
        return ' AND '.join(conditions)

    def __str__(self):
        """Return query string."""
        return self._string

    @property
    def nodes(self):
        """Get nodes."""
        return self._nodes

    @property
    def edges(self):
        """Get edges."""
        return self._edges

    @property
    def qids(self):
        """Return all qids."""
        return {**self.nodes, **self.edges}

    def where_clause(self, context=None):
        """Get WHERE clause."""
        if context is None:
            context = set()
        return 'WHERE ' + self.logic

    def return_clause(self, context=None):
        """Get RETURN clause."""
        if context is None:
            context = set()
        return 'RETURN ' + ', '.join(set(self.qids) - set(context))

    def __and__(self, other):
        """AND two queries together."""
        return AndQuery(self, other)

    def __invert__(self):
        """NOT query."""
        return NotQuery(self)

    def add_context(self, context):
        """Add nodes to query context."""

    def __or__(self, other):
        """OR queries."""
        return OrQuery(self, other)

    def __xor__(self, other):
        """XOR queries."""
        return XorQuery(self, other)

    def set_context(self, context):
        """Set context."""
        self.context = context


class CompoundQuery(Query):
    """Compound query."""

    def __init__(self, *subqueries):
        """Initialize."""
        self.subqueries = subqueries

    @property
    def nodes(self):
        """Get nodes."""
        return dict(ChainMap(*(
            subquery.nodes
            for subquery in self.subqueries
        )))

    @property
    def edges(self):
        """Get edges."""
        return dict(ChainMap(*(
            subquery.edges
            for subquery in self.subqueries
        )))

    @property
    def logic(self):
        """Return whether qid is required."""
        return ' AND '.join(
            query.logic for query in self.subqueries
            if query.logic
        )


class WrapQuery(CompoundQuery):
    """Query wrapped in apoc.cypher.run()."""

    def __init__(self, *args, **kwargs):
        """Initialize."""
        super().__init__(*args, **kwargs)
        assert len(self.subqueries) == 1

    @property
    def params(self):
        """Get params."""
        if self.context is not None:
            return ', '.join(
                f'`id({var})`: id({var})'
                for var in self.context
            )
        else:
            return ''

    @property
    def nodes(self):
        """Get nodes."""
        return {
            qid: f'value.{qid}'
            for qid in super().nodes
        }

    @property
    def edges(self):
        """Get edges."""
        return {
            qid: f'value.{qid}'
            for qid in super().edges
        }

    def __str__(self, **kwargs):
        """Wrap a Cypher query in apoc.cypher.run()."""
        return (
            'CALL apoc.cypher.run(\'{query}\', {{{params}}}) '
            'YIELD value'
        ).format(
            query=str(self.subqueries[0]).replace('\\', '\\\\').replace('\'', '\\\''),
            params=self.params,
        )


class AndQuery(CompoundQuery):
    """Compound query segment."""

    def __init__(self, *subqueries):
        """Initialize."""
        # super().__init__(*subqueries)

        self.subqueries = []
        for query in subqueries:
            query.set_context(self.nodes)
            if isinstance(query, (OrQuery, XorQuery)):
                query = WrapQuery(query)
                query.set_context(self.nodes)
            self.subqueries.append(query)

    def __str__(self):
        """Get query string."""
        return ' '.join(
            str(query) for query in self.subqueries
        ) + ' WITH ' + ', '.join(
            qid if qid == accessor else f'{accessor} AS {qid}'
            for qid, accessor in self.qids.items()
        )


class NotQuery(CompoundQuery):
    """Not query segment."""

    def __str__(self):
        """Return query string."""
        return str(self.subqueries[0])

    @property
    def logic(self):
        """Return whether qid is required."""
        return f'NOT ({super().logic})'


def union_string(query0, query1, context=None):
    """Assemble UNION query."""
    if context is not None:
        prefix = ''.join(
            f'CALL apoc.get.nodes($`id({var})`) YIELD node as {var} '
            for var in context
        )
    else:
        prefix = ''
    return (
        '{prefix}{query0}'
        ' UNION '
        '{prefix}{query1}'
    ).format(
        prefix=prefix,
        query0=' '.join((str(query0), query0.return_clause(context))),
        query1=' '.join((str(query1), query1.return_clause(context))),
    )


class OrQuery(CompoundQuery):
    """OR query."""

    def __init__(self, *args):
        """Initialize."""
        assert len(args) == 2
        super().__init__(*args)
        query0 = AndQuery(args[0], args[1])
        query1 = AndQuery(args[1], args[0])
        self._subqueries = [query0, query1]

    def __str__(self):
        """Get query string."""
        return union_string(
            *self._subqueries,
            context=self.context,
        )

    @property
    def logic(self):
        """Get conditions."""
        return ' OR '.join(
            f'({query.logic})' for query in self.subqueries
        )


class XorQuery(CompoundQuery):
    """XOR query."""

    def __init__(self, *args):
        """Initialize."""
        assert len(args) == 2
        super().__init__(*args)
        query0 = AndQuery(args[0], args[1])
        query1 = AndQuery(args[1], args[0])
        self._subqueries = [query0, query1]

    def __str__(self):
        """Get query string."""
        return union_string(
            *self._subqueries,
            context=self.context,
        )

    @property
    def logic(self):
        """Get conditions."""
        return ' XOR '.join(
            f'({query.logic})' for query in self.subqueries
        )


def transpile_compound(qgraph, **kwargs):
    """Restate compound qgraph.

    We want to use AND, NOT, OPTIONAL, and UNION, not OR and XOR.
    "x OR y" -> "(x AND OPTIONAL y) UNION (y AND OPTIONAL x)"
    "x XOR y" -> "(x AND NOT y) UNION (y AND NOT x)"
    Collapse nested operators, e.g. "x AND (y AND z)" -> "x AND y AND z"
    """
    def nest_op(operator, *args):
        """Generate a nested set of operations from a flat expression."""
        if len(args) > 2:
            return [operator, args[0], nest_op(operator, *args[1:])]
        else:
            return [operator, *args]

    if isinstance(qgraph, list):
        # if qgraph[0] in ('OR', 'XOR'):
        #     qgraph = nest_op(*qgraph)

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
    query = get_match_clause(
        qgraph,
        **kwargs,
    )
    return query


def get_query(qgraph, **kwargs):
    """Generate a Cypher query to extract the answer maps for a question.

    Returns the query as a string.
    """
    clauses = []
    if isinstance(qgraph, list):
        expr = parse_compound(qgraph)
        matches = re.finditer(r'{{ (qg_(?:\d+(?:_\d+)*)*) }}', expr)
        sub_qgraphs = dict()
        qids = dict()
        clauses = []
        for match in matches:
            sub_qgraph = qgraph
            for idx in match[1].split('_')[1:]:
                sub_qgraph = sub_qgraph[int(idx)]
            sub_qgraphs[match[1]] = sub_qgraph
            query = get_match_clause(
                sub_qgraph,
                max_connectivity=kwargs.pop('max_connectivity', -1)
            )
            qids[match[1]] = query.qids
            clauses.append(str(query))
        template = Template(expr)
        qnodes = [
            el
            for value in sub_qgraphs.values()
            for el in value['nodes']
        ]
        qedges = [
            el
            for value in sub_qgraphs.values()
            for el in value['edges']
        ]
        clauses.append('WITH ' + ', '.join(
            el['id'] for el in qnodes + qedges
        ))
        clauses.append('WHERE ' + template.render(**{
            key: '(' + ' AND '.join(
                f'({qid} IS NOT NULL)'
                for qid in value
            ) + ')'
            for key, value in qids.items()
        }))
    else:
        qnodes = qgraph['nodes']
        qedges = qgraph['edges']

    # assemble result (bindings) and associated (result) kgraph
    node_bindings = [
        (
            '[ni IN collect(DISTINCT `{0}`.id) '
            '| {{qg_id:"{0}", kg_id:ni}}]'
        ).format(
            qnode['id'],
        ) if qnode.get('set', False) else
        '[{{qg_id:"{0}", kg_id:`{0}`.id}}]'.format(qnode['id'])
        for qnode in qnodes
    ]
    edge_bindings = [
        (
            '[ei IN collect(DISTINCT toString(id(`{0}`))) '
            '| {{qg_id:"{0}", kg_id:ei}}]'
        ).format(
            qedge['id'],
        ) if kwargs.get('relationship_id', 'property') == 'internal' else
        (
            '[ei IN collect(DISTINCT `{0}`.id) '
            '| {{qg_id:"{0}", kg_id:ei}}]'
        ).format(
            qedge['id'],
        )
        for qedge in qedges
    ]
    knodes = ' + '.join([
        'collect(DISTINCT `{0}`)'.format(qnode['id'])
        for qnode in qnodes
    ])
    kedges = ' + '.join([
        'collect(DISTINCT `{0}`)'.format(qedge['id'])
        for qedge in qedges
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
