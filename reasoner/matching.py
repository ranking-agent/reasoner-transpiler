"""MATCHing tools."""
from reasoner.nesting import Query


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
    edge_filters = [
        f'({c})'
        for c in source_node.filters + target_node.filters + eref.filters
    ]
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
