"""MATCHing tools."""
from typing import List

from bmt import Toolkit

from reasoner.nesting import Query
from reasoner.util import ensure_list, snake_case, space_case, pascal_case

bmt = Toolkit()


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

    def __init__(self, node_id, node, **kwargs):
        """Create a node reference.

        All node properties of types [str, bool, float/int] will be enforced
        verbatim EXCEPT for the following reserved properties:
        * category
        * id
        * name
        * is_set
        Un-reserved properties with other types will be coerced to str.
        """
        max_connectivity = kwargs.get('max_connectivity', -1)
        anonymous = kwargs.get('anonymous', False)

        node = dict(node)  # shallow copy
        self.name = '`' + node_id + '`' if not anonymous else ''
        self.labels = node.pop('category', None) or []
        if not isinstance(self.labels, list):
            self.labels = [self.labels]

        props = {}
        self._filters = []
        curie = node.pop('id', None)
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

        if max_connectivity > -1:
            self._filters.append('size( ({0})-[]-() ) < {1} + 1'.format(
                self.name,
                max_connectivity,
            ))

        props.update(
            (key, value)
            for key, value in node.items()
            if key not in ('name', 'is_set')
        )

        self.prop_string = ' {' + ', '.join([
            f'`{key}`: {cypher_prop_string(props[key])}' for key in props
        ]) + '}' if props else ''
        self._hints = []
        if curie and self.labels:
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
        self.predicates: List[str] = ensure_list(edge.get('predicate', []))
        self.filters = []
        self.label = None

        # relationship is directed if any provided predicate is asymmetrical
        self.directed = any(
            not bmt.get_element(space_case(predicate[8:])).symmetric
            for predicate in self.predicates
        )

        # get all descendant predicates
        self.predicates = [
            f"biolink:{snake_case(p)}"
            for predicate in self.predicates
            for p in bmt.get_descendants(space_case(predicate[8:]))
        ]

        if len(self.predicates) == 1:
            self.label = self.predicates[0]
        elif len(self.predicates) > 1:
            self.filters.append(' OR '.join(
                f'type({self.name}) = "{predicate}"'
                for predicate in self.predicates
            ))

        props = {}
        props.update(
            (key, value)
            for key, value in edge.items()
            if key not in ('name', 'predicate', "subject", "object")
        )

        self.prop_string = ' {' + ', '.join([
            f'`{key}`: {cypher_prop_string(value)}'
            for key, value in props.items()
            if value is not None
        ]) + '}' if props else ''

    def __str__(self):
        """Return the cypher edge reference."""
        return '-[`{0}`{1}]-'.format(
            self.name,
            (
                (f':`{self.label}`' if self.label else '')
                + f'{self.prop_string}'
            ),
        ) + ('>' if self.directed else '')


def build_match_clause(
        *patterns,
        filters=None,
        hints=None,
        **kwargs,
):
    """Build MATCH clause (and subclauses) from components."""
    query = ''
    query += 'MATCH ' + ', '.join(patterns)
    if kwargs.get('use_hints', False) and hints:
        query += ' ' + ' '.join(hints)
    if filters:
        if len(filters) > 1:
            filters = [f'({f})' for f in filters]
        query += ' WHERE ' + ' AND '.join(filters)

    return query


def match_edge(qedge_id, qedge, node_references, **kwargs):
    """Get MATCH clause for edge."""
    eref = EdgeReference(qedge_id, qedge)
    source_node = node_references[qedge['subject']]
    target_node = node_references[qedge['object']]
    pattern = f'{source_node}{eref}{target_node}'
    edge_filters = [
        f'({c})'
        for c in source_node.filters + target_node.filters + eref.filters
    ]
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
        [e['subject'] for e in qgraph['edges'].values()]
        + [e['object'] for e in qgraph['edges'].values()]
    )

    # generate internal node and edge variable names
    node_references = {
        qnode_id: NodeReference(qnode_id, qnode, **kwargs)
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
