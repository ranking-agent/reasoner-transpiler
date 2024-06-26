"""MATCHing tools."""
import os
from typing import Dict, List

from bmt import Toolkit

from .exceptions import InvalidPredicateError, InvalidQualifierError, InvalidQualifierValueError
from .nesting import Query
from .util import ensure_list, snake_case, space_case, pascal_case


BIOLINK_MODEL_VERSION = os.environ.get('BL_VERSION', '4.1.6')
BIOLINK_MODEL_SCHEMA_URL = f"https://raw.githubusercontent.com/biolink/biolink-model/v{BIOLINK_MODEL_VERSION}/biolink-model.yaml"
PREDICATE_MAP_URL = f"https://raw.githubusercontent.com/biolink/biolink-model/v{BIOLINK_MODEL_VERSION}/predicate_mapping.yaml"

bmt = Toolkit(schema=BIOLINK_MODEL_SCHEMA_URL, predicate_map=PREDICATE_MAP_URL)
ALL_BIOLINK_ENUMS = bmt.view.all_enums().keys()


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
        * set_interpretation
        Un-reserved properties with other types will be coerced to str.
        """
        max_connectivity = kwargs.get("max_connectivity", -1)
        self.anonymous = kwargs.get("anonymous", False)

        node = dict(node)  # shallow copy
        self.name = f"`{node_id}`"

        props = {}
        self._filters = []
        self.labels = []

        category = node.pop("categories", None)
        if isinstance(category, list) and len(category) == 1:
            category = category[0]
        if isinstance(category, list):
            self.labels = ['biolink:NamedThing']
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
            self._filters.append("{0}.id in [{1}]".format(
                self.name,
                ", ".join([
                    cypher_prop_string(ci)
                    for ci in curie
                ])
            ))
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
            if key not in ("name", "set_interpretation", "constraints")
        )

        self.prop_string = "{" + ", ".join([
            f"`{key}`: {cypher_prop_string(value)}"
            for key, value in props.items()
            if value is not None and not key.startswith("_")
        ]) + "}" if props else ""
        self._hints = []
        if curie and self.labels:
            self._hints.append(f"USING INDEX {self.name}:`{self.labels[0]}`(id)")
        self._num = 0

    def __str__(self):
        """Return the cypher node reference."""
        self._num += 1
        if self._num > 1:
            return f"({self.name})"
        ref = "("
        elements = []
        if not self.anonymous:
            elements.append(self.name)
        if self.labels:
            elements.append("".join(f":`{label}`" for label in self.labels))
        elements = ["".join(elements)]
        if self.prop_string:
            elements.append(self.prop_string)
        ref = "({})".format(" ".join(elements))
        return ref

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

    def __init__(
        self,
        edge_id,
        edge,
        anonymous=False,
        invert=True,
        **kwargs
    ):
        """Create an edge reference."""
        edge = dict(edge)  # make shallow copy
        _subject = edge.pop("subject")
        _object = edge.pop("object")
        self.name = edge_id if not anonymous else ""
        self.predicates: List[str] = ensure_list(
            edge.pop("predicates", []) or []
        )

        # "related_to" has every predicate as a descendent, it's inclusion is equivalent to no/any predicate
        if 'biolink:related_to' in self.predicates:
            self.predicates = []

        self.filters = []
        self.qualifier_filters = ""
        self.label = None  #What goes in the [] on the edge in cypher
        self.length = edge.pop("_length", (1, 1))
        invert = invert and edge.pop("_invert", True)

        self.inverse_predicates = []
        self.directed = False # Controls whether there is an arrow on the edge in cypher
        self.symmetric = True # Whether the original top-level predicates are all symmetric
        self.cypher_invert = False # If true, then the cypher source node will be subject, if false then object
        for predicate in self.predicates:
            el = bmt.get_element(space_case(predicate[8:]))
            if el:
                inverse_predicate = el.inverse
                if inverse_predicate is not None:
                    self.inverse_predicates.append(f"biolink:{snake_case(inverse_predicate)}")
                # TODO remove the following elif -
                # this is only here because this version of the biolink model doesn't have subclass as the inverse of
                # superclass, but that will be fixed in future versions
                elif predicate == 'biolink:superclass_of':
                    self.inverse_predicates.append(f"biolink:subclass_of")

                # if symmetric add to inverse list so we query in both directions
                if el.symmetric:
                    self.inverse_predicates.append(predicate)
                else:
                    self.symmetric = False
            else:
                error_message = f"Invalid predicate error: (predicate: {predicate}) is not " \
                                f"a valid biolink model predicate."
                raise InvalidPredicateError(error_message=error_message)

        # relationship is directed if any provided predicate is asymmetrical
        if not self.symmetric:
            self.directed = True

        # get all the descendants of the predicates and add them to the query as well
        # NOTE - the "if bmt.get_element(p)" check is here because some predicates in the biolink model
        # were failing to return an element even when they exist (because they had underscores in them)
        # this should be fixed in future versions, we could remove it, but it's safer to leave
        predicates = []
        for predicate in self.predicates:
            for predicate_descendant in bmt.get_descendants(space_case(predicate[8:])):
                element = bmt.get_element(predicate_descendant)
                if element and (element.annotations.get('canonical_predicate', False) or
                                'symmetric' in element and element['symmetric']):
                    predicates.append(f"biolink:{snake_case(predicate_descendant)}")
        self.predicates = predicates

        if not invert:
            self.inverse_predicates = []
        inverse_predicates = []
        for predicate in self.inverse_predicates:
            for predicate_descendant in bmt.get_descendants(space_case(predicate[8:])):
                element = bmt.get_element(predicate_descendant)
                if element and (element.annotations.get('canonical_predicate', False) or
                                'symmetric' in element and element['symmetric']):
                    inverse_predicates.append(f"biolink:{snake_case(predicate_descendant)}")
        self.inverse_predicates = inverse_predicates

        unique_preds = list(set(self.predicates + self.inverse_predicates))
        #Having the predicates sorted doesn't matter to neo4j, but it helps in testing b/c we get a consistent string.
        unique_preds.sort()
        self.label = "|".join(
            f"`{predicate}`"
            for predicate in unique_preds
        )

        # We only need the WHERE clause if: we have canonical edges pointing in opposite directions.  In that
        # case we need a non-directed edge and a where clause that points the right ones in different directions
        if not self.symmetric:
            if self.inverse_predicates and self.predicates:
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
            #If we have inverse_predicates and not self.predicates then it means that everything in predicates
            # was non-canonical and we reversed them all so we need to invert the edge
            elif self.inverse_predicates:
                self.cypher_invert=True
        constraints = ["attribute_constraints", "qualifier_constraints"]
        other_non_prop_attributes = ["name", "knowledge_type"]
        self.qualifier_filters = self.__qualifier_filters(edge, edge_id)
        props = {}
        props.update(
            (key, value)
            for key, value in edge.items()
            if key not in set(constraints + other_non_prop_attributes) and not key.startswith("_")
        )

        self.prop_string = " {" + ", ".join([
            f"`{key}`: {cypher_prop_string(value)}"
            for key, value in props.items()
            if value is not None
        ]) + "}" if props else ""

    def __qualifier_filters(self, edge , edge_id):
        constraints = edge.get("qualifier_constraints", [])
        ors = []
        for constraint in constraints:
            ands = []
            for constraint_filter in constraint.get("qualifier_set", []):
                # also handle "qualifier_set": [{ }]
                if not constraint_filter:
                    continue

                qualifier_type = constraint_filter['qualifier_type_id']
                queried_qualifier_value = constraint_filter['qualifier_value']

                if not bmt.is_qualifier(qualifier_type):
                    raise InvalidQualifierError(f'Invalid qualifier in query: {qualifier_type}')

                # we should do something like this but it does not work without knowing the association type of the edge
                # if not bmt.validate_qualifier(qualifier_type_id=qualifier_type, qualifier_value=queried_qualifier_value):
                #    raise InvalidQualifierError(f'Invalid qualifier requested, {qualifier_type}:{queried_qualifier_value}')

                qualifier_value_plus_descendants = [queried_qualifier_value]
                if qualifier_type != 'qualified_predicate': # qualified_predicate doesn't have an enum as values so the following does not apply
                    permissible_value = False
                    for enum_for_qualifier_values in ALL_BIOLINK_ENUMS:
                        if bmt.is_permissible_value_of_enum(enum_name=enum_for_qualifier_values, value=queried_qualifier_value):
                            permissible_value = True
                            qualifier_value_plus_descendants += bmt.get_permissible_value_descendants(permissible_value=queried_qualifier_value,
                                                                                                      enum_name=enum_for_qualifier_values)
                    if not permissible_value:
                        raise InvalidQualifierValueError(f'Invalid value for qualifier {qualifier_type} in query: {queried_qualifier_value}')

                # Join qualifier value hierarchy with an or
                qualifier_where_condition = " ( " + " OR ".join([f"`{edge_id}`.{qualifier_type} = {cypher_prop_string(qualifier_value)}" for qualifier_value in set(qualifier_value_plus_descendants)]) + " ) "
                ands.append(qualifier_where_condition)
            # if qualifier set is empty ; loop to the next
            if not len(ands):
                continue
            # join contraints in a single qualifier set with `AND`
            ands = ' ( ' + ' AND '.join(ands) + ' ) '
            ors.append(ands)
        # join multiple qualifier sets with `OR`
        return ' OR '.join(ors)

    def __str__(self):
        """Return the cypher edge reference."""
        elements = [
            f":{self.label}" if self.label else "",
        ]
        if not self.length == (1, 1):
            elements.append("*{}..{}".format(
                self.length[0] if self.length[0] is not None else "",
                self.length[1] if self.length[1] is not None else "",
            ))
        elements.append(f"{self.prop_string}")
        return "-[`{0}`{1}]-".format(
            self.name,
            "".join(elements),
        ) + (">" if self.directed else "")


def build_match_clause(
        *patterns,
        filters=None,
        hints=None,
        qualifier_filters="",
        **kwargs,
):
    """Build MATCH clause (and subclauses) from components."""
    query = ""
    query += "MATCH " + ", ".join(patterns)
    reg_filters_cypher = ""
    qualifier_filters_cypher = ""
    combine_op = ""
    has_filters = False
    if kwargs.get("use_hints", False) and hints:
        query += " " + " ".join(hints)
    if filters or qualifier_filters:
        if len(filters):
            has_filters = True
            if len(filters) > 1:
                filters = [f"({f})" for f in filters]
                reg_filters_cypher += " ( " + " AND ".join(filters) + " ) "
            else:
                reg_filters_cypher += " ( " + filters[0] + " ) "

        if len(qualifier_filters):
            has_filters = True
            qualifier_filters_cypher += f"({qualifier_filters})"

        if len(filters) and len(qualifier_filters):
            combine_op = " AND "
    if has_filters:
        query += " WHERE " + reg_filters_cypher + combine_op + qualifier_filters_cypher

    return query


def match_edge(
    qedge_id,
    qedge,
    node_references: Dict[str, NodeReference],
    invert=True,
    **kwargs,
):
    """Get MATCH clause for edge."""
    eref = EdgeReference(qedge_id, qedge, invert=invert, **kwargs)
    if eref.cypher_invert:
        source_node = node_references[qedge["object"]]
        target_node = node_references[qedge["subject"]]
    else:
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
        qualifier_filters=eref.qualifier_filters,
        **kwargs,
    )


def match_query(qgraph, subclass=True, **kwargs):
    """Generate a Cypher MATCH clause.

    Returns the query fragment as a string.
    """
    #If there's no label on a query node, neo4j can't use an index.  This makes such queries basically
    # neo4j killers.   So when there is no category, we add NamedThing which will use an indx.
    for qnode_id, qnode in qgraph["nodes"].items():
        if qnode.get("ids", None) is not None and qnode.get("categories",None) is None:
            qnode["categories"] = ["biolink:NamedThing"]

    # find all of the qnode ids that have subclass or superclass edges connected to them
    qnode_ids_with_hierarchy_edges = set()
    for qedge_id, qedge in qgraph["edges"].items():
        predicates = qedge.get("predicates", None)
        if predicates and ("biolink:subclass_of" in predicates or "biolink:superclass_of" in predicates):
            qnode_ids_with_hierarchy_edges.add(qedge['subject'])
            qnode_ids_with_hierarchy_edges.add(qedge['object'])

    if subclass:
        superclasses = {
            qnode_id + "_superclass": {
                "ids": qnode.pop("ids"),
                "categories": qnode.pop("categories", None),
                "_return": False,
            }
            for qnode_id, qnode in qgraph["nodes"].items()
            if qnode.get("ids", None) is not None and qnode_id not in qnode_ids_with_hierarchy_edges
        }

        if 'subclass_depth' in kwargs:
            if not isinstance(kwargs['subclass_depth'], int):
                raise TypeError(f"Unsupported subclass_depth type: {type(kwargs['subclass_depth']).__name__}.")
            elif kwargs['subclass_depth'] < 0:
                raise ValueError(f"Parameter subclass_depth must be a positive integer.")
            else:
                subclass_depth = kwargs['subclass_depth']
        else:
            subclass_depth = 1
        subclass_edges = {
            qnode_id[:-11] + "_subclass_edge": {
                "subject": qnode_id[:-11],
                "object": qnode_id,
                "predicates": ["biolink:subclass_of"],
                "_length": (0, subclass_depth),
                "_invert": False,
                "_return": False,
            }
            for qnode_id in superclasses
        }
        qgraph["nodes"].update(superclasses)
        qgraph["edges"].update(subclass_edges)

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
