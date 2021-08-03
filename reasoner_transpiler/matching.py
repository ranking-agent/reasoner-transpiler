"""MATCHing tools."""
from typing import List

from bmt import Toolkit

from .nesting import Query
from .util import ensure_list, snake_case, space_case, pascal_case

biolink_version = "1.8.0"
bmt = Toolkit(schema=(
    "https://raw.githubusercontent.com/"
    f"biolink/biolink-model/{biolink_version}/"
    "biolink-model.yaml"
))


def cypher_prop_string(value):
    """Convert property value to cypher string representation."""
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, str):
        return "\"{0}\"".format(
            value.replace("\"", "\\\"")
        )
    if isinstance(value, (float, int)):
        return str(value)
    raise ValueError(f"Unsupported property type: {type(value).__name__}.")


class NodeReference():
    """Node reference object."""

    def __init__(self, node_id, node, **kwargs):
        """Create a node reference.

        All node properties of types [str, bool, float/int] will be enforced
        verbatim EXCEPT for the following reserved properties:
        * categories
        * ids
        * name
        * is_set
        Un-reserved properties with other types will be coerced to str.
        """
        max_connectivity = kwargs.get("max_connectivity", -1)
        anonymous = kwargs.get("anonymous", False)

        node = dict(node)  # shallow copy
        self.name = "`" + node_id + "`" if not anonymous else ""

        props = {}
        self._filters = []
        self.labels = []

        category = node.pop("categories", None)
        if isinstance(category, list) and len(category) == 1:
            category = category[0]
        if isinstance(category, list):
            self._filters.append(" OR ".join([
                "{1} in labels({0})".format(
                    self.name,
                    cypher_prop_string(ci)
                )
                for ci in category
            ]))
        elif category is not None:
            # coerce to a string
            self.labels = [str(category)]

        curie = node.pop("ids", None)
        if isinstance(curie, list) and len(curie) == 1:
            curie = curie[0]
        if isinstance(curie, list):
            self._filters.append(" OR ".join([
                "{0}.id = {1}".format(
                    self.name,
                    cypher_prop_string(ci)
                )
                for ci in curie
            ]))
        elif curie is not None:
            # coerce to a string
            props["id"] = str(curie)

        if max_connectivity > -1:
            self._filters.append("size( ({0})-[]-() ) < {1} + 1".format(
                self.name,
                max_connectivity,
            ))

        props.update(
            (key, value)
            for key, value in node.items()
            if key not in ("name", "is_set")
        )

        self.prop_string = " {" + ", ".join([
            f"`{key}`: {cypher_prop_string(value)}"
            for key, value in props.items()
            if value is not None
        ]) + "}" if props else ""
        self._hints = []
        if curie and self.labels:
            self._hints.append(f"USING INDEX {self.name}:{self.labels[0]}(id)")
        self._num = 0

    def __str__(self):
        """Return the cypher node reference."""
        self._num += 1
        if self._num > 1:
            return f"({self.name})"
        return f"({self.name}" \
            + "".join(f":`{label}`" for label in self.labels) \
            + f"{self.prop_string})"

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
        self.name = f"`{name}`"
        self._num = 2


class EdgeReference():
    """Edge reference object."""

    def __init__(self, edge_id, edge, anonymous=False):
        """Create an edge reference."""
        edge = dict(edge)  # make shallow copy
        _subject = edge.pop("subject")
        _object = edge.pop("object")
        self.name = edge_id if not anonymous else ""
        self.predicates: List[str] = ensure_list(
            edge.pop("predicates", []) or []
        )
        self.filters = []
        self.label = None

        self.inverse_predicates = []
        self.directed = False
        for predicate in self.predicates:
            el = bmt.get_element(space_case(predicate[8:]))
            if el is None:
                continue
            inverse = el.inverse
            symmetric = el.symmetric
            # relationship is directed if any provided predicate is asymmetrical
            if not symmetric:
                self.directed = True
            if inverse is not None:
                self.inverse_predicates.append(f"biolink:{snake_case(inverse)}")
            elif symmetric:
                self.inverse_predicates.append(predicate)

        # get all descendant predicates
        self.predicates = [
            f"biolink:{snake_case(p)}"
            for predicate in self.predicates
            for p in bmt.get_descendants(space_case(predicate[8:]))
        ]
        self.inverse_predicates = [
            f"biolink:{snake_case(p)}"
            for predicate in self.inverse_predicates
            for p in bmt.get_descendants(space_case(predicate[8:]))
        ]

        self.label = "|".join(
            f"`{predicate}`"
            for predicate in self.predicates + self.inverse_predicates
        )

        if self.inverse_predicates:
            self.directed = False
            self.filters.append(" OR ".join([
                "(type(`{0}`) in [{1}] AND startNode(`{0}`) = `{2}`)".format(
                    self.name,
                    ", ".join([
                        f"\"{predicate}\""
                        for predicate in self.predicates
                    ]),
                    _subject,
                ),
                "(type(`{0}`) in [{1}] AND startNode(`{0}`) = `{2}`)".format(
                    self.name,
                    ", ".join([
                        f"\"{predicate}\""
                        for predicate in self.inverse_predicates
                    ]),
                    _object,
                ),
            ]))

        props = {}
        props.update(
            (key, value)
            for key, value in edge.items()
            if key not in ("name",)
        )

        self.prop_string = " {" + ", ".join([
            f"`{key}`: {cypher_prop_string(value)}"
            for key, value in props.items()
            if value is not None
        ]) + "}" if props else ""

    def __str__(self):
        """Return the cypher edge reference."""
        return "-[`{0}`{1}]-".format(
            self.name,
            (
                (f":{self.label}" if self.label else "")
                + f"{self.prop_string}"
            ),
        ) + (">" if self.directed else "")


def build_match_clause(
        *patterns,
        filters=None,
        hints=None,
        **kwargs,
):
    """Build MATCH clause (and subclauses) from components."""
    query = ""
    query += "MATCH " + ", ".join(patterns)
    if kwargs.get("use_hints", False) and hints:
        query += " " + " ".join(hints)
    if filters:
        if len(filters) > 1:
            filters = [f"({f})" for f in filters]
        query += " WHERE " + " AND ".join(filters)

    return query


def match_edge(qedge_id, qedge, node_references, **kwargs):
    """Get MATCH clause for edge."""
    eref = EdgeReference(qedge_id, qedge)
    source_node = node_references[qedge["subject"]]
    target_node = node_references[qedge["object"]]
    pattern = f"{source_node}{eref}{target_node}"
    edge_filters = [
        f"({c})"
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
    defined_nodes = set(qgraph["nodes"])
    defined_edges = set(qgraph["edges"])
    referenced_nodes = set(
        [e["subject"] for e in qgraph["edges"].values()]
        + [e["object"] for e in qgraph["edges"].values()]
    )

    # generate internal node and edge variable names
    node_references = {
        qnode_id: NodeReference(qnode_id, qnode, **kwargs)
        for qnode_id, qnode in qgraph["nodes"].items()
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
    for qedge_id, qedge in qgraph["edges"].items():
        clauses.append(match_edge(
            qedge_id,
            qedge,
            node_references,
            **kwargs,
        ))

    return Query(
        " ".join(clauses),
        qids=defined_nodes | defined_edges,
        references=defined_nodes | referenced_nodes | defined_edges,
        qgraph=qgraph,
    )
