"""Tools for compiling QGraph into Cypher query."""


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
        ]) + '}'
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


def get_match_clause(qgraph, max_connectivity=-1):
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
    for node_id in orphaned_nodes:
        clauses.append(
            f'MATCH {node_references[node_id]}'
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
            f'MATCH {source_node}{eref}{target_node}'
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

    return ' '.join(clauses)


def get_query(qgraph, **kwargs):
    """Generate a Cypher query to extract the answer maps for a question.

    Returns the query as a string.
    """
    qnodes, qedges = qgraph['nodes'], qgraph['edges']

    clauses = []

    # get MATCH clause
    match_string = get_match_clause(
        qgraph,
        max_connectivity=kwargs.pop('max_connectivity', -1)
    )
    if match_string:
        clauses.append(match_string)

    # collects sets in WITH clause
    node_id_accessor = [
        'collect(DISTINCT `{0}`.id) AS `{0}`'.format(qnode['id'])
        if qnode.get('set', False) else
        '[`{0}`.id] AS `{0}`'.format(qnode['id'])
        for qnode in qnodes
    ]
    if kwargs.get('relationship_id', 'property') == 'internal':
        edge_id_accessor = [
            'collect(DISTINCT toString(id({0}))) AS `{0}`'.format(qedge['id'])
            for qedge in qedges
        ]
    else:
        edge_id_accessor = [
            'collect(DISTINCT `{0}`.id) AS `{0}`'.format(qedge['id'])
            for qedge in qedges
        ]
    if node_id_accessor or edge_id_accessor:
        clauses.append('WITH {0}'.format(
            ', '.join(node_id_accessor + edge_id_accessor)
        ))

    # add RETURN clause
    node_dicts = [
        '[ni IN `{0}` | {{qg_id:"{0}", kg_id:ni}}]'.format(qnode['id'])
        for qnode in qnodes
    ]
    edge_dicts = [
        '[ei IN `{0}` | {{qg_id:"{0}", kg_id:ei}}]'.format(qedge['id'])
        for qedge in qedges
    ]
    answer_return_string = (
        'RETURN {0} AS node_bindings, {1} AS edge_bindings'
    ).format(
        ' + '.join(node_dicts) or '[]',
        ' + '.join(edge_dicts) or '[]',
    )
    clauses.append(answer_return_string)

    # add SKIP and LIMIT sub-clauses
    if 'skip' in kwargs:
        clauses.append(f'SKIP {kwargs["skip"]}')
    if 'limit' in kwargs:
        clauses.append(f'LIMIT {kwargs["limit"]}')

    return ' '.join(clauses)
