"""Tools for compiling QGraph into Cypher query."""
from functools import reduce
from operator import and_, or_

from reasoner.util import mapize


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

    def __init__(self, node_id, node, anonymous=False):
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
        self.name = '`' + node_id + '`' if not anonymous else ''
        self.labels = node.pop('type', ['named_thing'])
        if not isinstance(self.labels, list):
            self.labels = [self.labels]

        props = {}
        self._filters = []
        curie = node.pop('curie', None)
        if isinstance(curie, list) and len(curie) == 1:
            curie = curie[0]
        if isinstance(curie, str):
            props['id'] = curie
        elif isinstance(curie, list):
            self._filters.append(' OR '.join([
                '{0}.id = {1}'.format(
                    self.name,
                    cypher_prop_string(ci)
                )
                for ci in curie
            ]))
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
        self._hints = []
        if curie:
            self._hints.append(f'USING INDEX {self.name}:{self.labels[0]}(id)')
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
            return []
        return self._filters

    @property
    def hints(self):
        """Return hints for the cypher node reference.

        To be appended to the MATCH clause.
        """
        if self._num > 1:
            return []
        return self._hints


class MissingReference(NodeReference):
    """Missing node reference object."""

    def __init__(self, name):  # pylint: disable=super-init-not-called
        """Initialize."""
        self.name = f'`{name}`'
        self._num = 2


class EdgeReference():
    """Edge reference object."""

    def __init__(self, edge_id, edge, anonymous=False):
        """Create an edge reference."""
        self.name = edge_id if not anonymous else ''
        self.label = edge.get('type', None)
        self.filters = []

        if isinstance(self.label, list):
            self.filters.append(' OR '.join(
                f'type({self.name}) = "{predicate}"'
                for predicate in self.label
            ))
            self.label = None

        self.directed = edge.get('directed', bool(self.label))

    def __str__(self):
        """Return the cypher edge reference."""
        return '-[`{0}`{1}]-'.format(
            self.name,
            ':' + self.label if self.label else '',
        ) + ('>' if self.directed else '')


def build_match_clause(
        *patterns,
        filters=None,
        hints=None,
        use_hints=False,
):
    """Build MATCH clause (and subclauses) from components."""
    query = ''
    query += 'MATCH ' + ', '.join(patterns)
    if use_hints and hints:
        query += ' ' + ' '.join(hints)
    if filters:
        if len(filters) > 1:
            filters = [f'({f})' for f in filters]
        query += ' WHERE ' + ' AND '.join(filters)

    return query


def match_edge(qedge_id, qedge, node_references, **kwargs):
    """Get MATCH clause for edge."""
    eref = EdgeReference(qedge_id, qedge)
    source_node = node_references[qedge['source_id']]
    target_node = node_references[qedge['target_id']]
    pattern = f'{source_node}{eref}{target_node}'
    edge_filters = [f'({c})' for c in [
        source_node.filters, target_node.filters, eref.filters
    ] if c]
    max_connectivity = kwargs.get('max_connectivity', -1)
    if max_connectivity > -1:
        edge_filters.append('(size( {0}-[]-() ) < {1})'.format(
            target_node,
            max_connectivity,
        ))
    return build_match_clause(
        pattern,
        hints=source_node.hints + target_node.hints,
        filters=edge_filters,
        **kwargs,
    )


def match_query(qgraph, **kwargs):
    """Generate a Cypher MATCH clause.

    Returns the query fragment as a string.
    """
    mapize(qgraph)

    # sets of ids
    defined_nodes = set(qgraph['nodes'])
    defined_edges = set(qgraph['edges'])
    referenced_nodes = set(
        [e['source_id'] for e in qgraph['edges'].values()]
        + [e['target_id'] for e in qgraph['edges'].values()]
    )

    # generate internal node and edge variable names
    node_references = {
        qnode_id: NodeReference(qnode_id, qnode)
        for qnode_id, qnode in qgraph['nodes'].items()
    }
    for node_id in referenced_nodes - defined_nodes:  # reference-only nodes
        node_references[node_id] = MissingReference(node_id)

    clauses = []

    # match orphaned nodes
    for node_id in defined_nodes - referenced_nodes:
        clauses.append(build_match_clause(
            str(node_references[node_id]),
            hints=node_references[node_id].hints,
            filters=node_references[node_id].filters,
            **kwargs,
        ))

    # match edges
    for qedge_id, qedge in qgraph['edges'].items():
        clauses.append(match_edge(
            qedge_id,
            qedge,
            node_references,
            **kwargs,
        ))

    return Query(
        ' '.join(clauses),
        qids=defined_nodes | defined_edges,
        references=defined_nodes | referenced_nodes | defined_edges,
        qgraph=qgraph,
    )


class Query():
    """Cypher query segment."""

    def __init__(
            self,
            string,
            qids=None,
            references=None,
            qgraph=None,
    ):
        """Initialize."""
        self._string = string
        self._qids = qids
        self._references = references
        self._qgraph = qgraph

    @property
    def qgraph(self):
        """Get qgraph."""
        return self._qgraph

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

    def compile(self, **kwargs):
        """Wrap hidden _compile method."""
        context = kwargs.get('context', set())
        context_ids = {
            var[3:-1] for var in context
            if var.startswith('id(')
        }

        clauses = []
        clauses.extend([
            f'CALL apoc.get.nodes($`id({var})`) YIELD node as {var}'
            for var in context_ids & self.references
        ])
        context = {
            var[3:-1] if var.startswith('id(')
            else var
            for var in context
        }
        kwargs['context'] = context

        return_ = kwargs.pop('return_', False)
        wrap = kwargs.pop('wrap', False)

        optional = kwargs.pop('optional', False)

        if (
                not optional
                and not wrap
                and not isinstance(self, CompoundQuery)
                and len(self.references) >= 5
        ):
            # there are probably at least two edges here
            wrap = True
            kwargs.update(
                optional=True,
            )
        elif not optional and not isinstance(self, CompoundQuery):
            clauses.append('OPTIONAL')

        if wrap:
            clauses.append(self._compile_wrapped(**kwargs))
        else:
            clauses.append(self._compile(**kwargs))

        if optional:
            clauses.append((
                'WITH CASE WHEN count(*) > 0 '
                + 'THEN collect([{0}]) '.format(
                    ', '.join(self.qids - context)
                )
                + 'ELSE [[]] '
                + 'END AS results '
                + 'UNWIND results as result '
                + 'WITH {0}'.format(', '.join(
                    f'result[{idx}] AS {qid}'
                    for idx, qid in enumerate(self.qids - context)
                ))
            ))

        if return_:
            clauses.append(self.return_clause(**kwargs))

        return ' '.join(clauses)

    def _compile_wrapped(self, **kwargs):
        """Compile wrapped query."""
        context = kwargs.pop('context', set())
        inner_context = {
            f'id({var})'
            for var in context & self.references
        }
        return (
            'CALL apoc.cypher.run(\'{query}\', {{{params}}}) '
            'YIELD value '
            'WITH {accessors}'
        ).format(
            query=(
                self.compile(context=inner_context, return_=True, **kwargs)
                .replace('\\', '\\\\')
                .replace('\'', '\\\'')
            ),
            params=', '.join(
                f'`{var}`: {var}'
                for var in inner_context
            ),
            accessors=', '.join(
                [
                    f'value.{qid} AS {qid}'
                    for qid in self.qids - context
                ]
                + list(context)
            )
        )

    def _compile(self, **kwargs):  # pylint: disable=unused-argument
        """Return query string."""
        return self._string

    @property
    def references(self):
        """Get references."""
        return self._references

    @property
    def qids(self):
        """Get qids."""
        return self._qids

    def where_clause(self, context=None):
        """Get WHERE clause."""
        if context is None:
            context = set()
        return 'WHERE ' + self.logic

    def return_clause(self, **kwargs):
        """Get RETURN clause."""
        context = kwargs.get('context', set())
        return 'RETURN ' + ', '.join(self.qids - context)

    def __and__(self, other):
        """AND two queries together."""
        return AndQuery(self, other)

    def __invert__(self):
        """NOT query."""
        return NotQuery(self)

    def __or__(self, other):
        """OR queries."""
        return OrQuery(self, other)

    def __xor__(self, other):
        """XOR queries."""
        return XorQuery(self, other)


class CompoundQuery(Query):
    """Compound query."""

    def __init__(self, *subqueries):  # pylint: disable=super-init-not-called
        """Initialize."""
        self.subqueries = subqueries

    @property
    def qids(self):
        """Get qids."""
        return reduce(
            or_,
            [subquery.qids for subquery in self.subqueries]
        )

    @property
    def qgraph(self):
        """Get qgraph."""
        qnodes = dict()
        qedges = dict()
        for subquery in self.subqueries:
            qnodes.update(subquery.qgraph['nodes'])
            qedges.update(subquery.qgraph['edges'])
        return {
            'nodes': qnodes,
            'edges': qedges,
        }

    @property
    def logic(self):
        """Return whether qid is required."""
        conditions = [
            query.logic for query in self.subqueries
            if query.logic
        ]
        if len(conditions) > 1:
            conditions = [
                f'({condition})' for condition in conditions
            ]
        return ' AND '.join(conditions)

    @property
    def references(self):
        """Get references."""
        return reduce(
            or_,
            (query.references for query in self.subqueries),
        )


class AndQuery(CompoundQuery):
    """Compound query segment."""

    def _compile(self, **kwargs):
        """Get query string."""
        context = kwargs.pop('context', set())
        subquery_strings = []
        for query in self.subqueries:
            subquery_strings.append(query.compile(context=context, **kwargs))
            context = context | query.qids

        return ' '.join(subquery_strings)


class NotQuery(CompoundQuery):
    """Not query segment."""

    def _compile(self, **kwargs):
        """Return query string."""
        return self.subqueries[0].compile(**kwargs)

    @property
    def logic(self):
        """Return whether qid is required."""
        return f'NOT ({super().logic})'


class AltQuery(CompoundQuery):
    """Alternative query.

    Superclass for OrQuery and XorQuery.
    """

    def __init__(self, *args):
        """Initialize."""
        assert len(args) == 2
        super().__init__(*args)

    def _compile(self, **kwargs):
        """Get query string."""
        if self.subqueries[0].qids & self.subqueries[1].qids:
            return self._compile_union(**kwargs, return_=True)
        else:
            query = AndQuery(self.subqueries[0], self.subqueries[1])
            context = kwargs.get('context', set())
            return (
                query.compile(**kwargs)
                + ' WITH ' + ', '.join(self.qids | context)
            )

    def _compile_union(self, **kwargs):
        """Get query string."""
        query0 = AndQuery(self.subqueries[0], self.subqueries[1])
        query1 = AndQuery(self.subqueries[1], self.subqueries[0])

        query = UnionQuery(query0, query1)
        return query.compile(wrap=True, **kwargs)


class UnionQuery(CompoundQuery):
    """UNION query."""

    def __init__(self, *args, **kwargs):
        """Initialize."""
        super().__init__(*args, **kwargs)
        self.return_ = None
        self.context = None

    def compile(self, **kwargs):
        """Return query string."""
        assert kwargs.get('return_', False)
        self.return_ = kwargs.pop('return_', set())
        self.context = kwargs.pop('context', set())
        context = {
            var[3:-1] if var.startswith('id(')
            else var
            for var in self.context
        }
        return super().compile(context=context, **kwargs)

    def _compile(self, **kwargs):
        """Return query string."""
        kwargs.update(
            context=self.context,
            return_=self.return_,
        )

        return ' UNION '.join(
            subquery.compile(
                **kwargs,
            )
            for subquery in self.subqueries
        )


class OrQuery(AltQuery):
    """OR query."""

    @property
    def logic(self):
        """Get conditions."""
        return ' OR '.join(
            f'({query.logic})' for query in self.subqueries
        )


class XorQuery(AltQuery):
    """XOR query."""

    @property
    def logic(self):
        """Get conditions."""
        return ' XOR '.join(
            f'({query.logic})' for query in self.subqueries
        )


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
    clauses = []
    query = transpile_compound(qgraph)
    clauses.append(query.compile())
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
