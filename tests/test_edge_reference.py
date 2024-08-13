import pytest
from ast import literal_eval
from reasoner_transpiler.matching import EdgeReference, set_predicates_in_graph
from reasoner_transpiler.exceptions import NoPossibleResultsException

def test_symmetric():
    """When a parent is symmetric, it can have both symmetric and directed children.   All of the symmetric and only the canonical directed children
    should appear in the label.   So in this example, only "biomarker_for" should appear, not "has_biomarker".
    There is no need to include the direction of the directed edge, because whichever is found will be consistant with the
    symmetric parent."""
    edge = {"subject": "s", "object": "o", "predicates": "biolink:correlated_with"}
    ref = EdgeReference("e0",edge,invert=True)
    preds = ref.label.split('|')
    assert len(preds) == 6
    assert "`biolink:biomarker_for`" in preds
    assert not ref.directed
    assert len(ref.filters) == 0
    assert not ref.cypher_invert

def test_directed_canonical():
    """For a directed parent predicate, all the children should be directed.  This should just have the
    subpredicates.  There's no WHERE block needed because all of the canonical versions of the predicates
    point the same direction by construction, and these are included in the --> syntax of the cypher.
    That happens in EdgeReference.str() if reference.directed is True."""
    edge= {"subject": "s", "object": "o", "predicates": "biolink:affects"}
    ref = EdgeReference("e0", edge, invert=True)
    preds = ref.label.split('|')
    assert len(preds) == 10
    assert ref.directed
    assert len(ref.filters) == 0
    assert not ref.cypher_invert

def test_noncanonical():
    """If we send in a non-canonical (and by definition directed) query, we expect that we'll have a directed
    query with the reversed edge, the canonical predicate (and sub-predicates), no where clause."""
    edge= {"subject": "s", "object": "o", "predicates": "biolink:affected_by"}
    ref = EdgeReference("e0", edge, invert=True)
    preds = ref.label.split('|')
    assert len(preds) == 10
    assert "`biolink:has_adverse_event`" in preds
    assert "`biolink:has_side_effect`" in preds
    assert ref.directed
    assert len(ref.filters) == 0
    #assert that the edge was reversed
    assert ref.cypher_invert

def test_multiple_canonical():
    """Make sure that the canonical logic is applied when there are multiple (canonical) predicates"""
    edge= {"subject": "s", "object": "o", "predicates": ["biolink:ameliorates_condition", "biolink:affects"]}
    ref = EdgeReference("e0", edge, invert=True)
    preds = ref.label.split('|')
    #  affects, affects_response_to, ameliorates_condition, decreases_response_to, disrupts, exacerbates_condition,
    #  has_adverse_event, has_side_effect, increases_response_to, regulates
    assert len(preds) == 10
    assert ref.directed
    assert len(ref.filters) == 0
    assert not ref.cypher_invert

def test_multiple_noncanonical():
    """Make sure that the canonical logic is applied when there are multiple (noncanonical) predicates"""
    edge = {"subject": "s", "object": "o", "predicates": ["biolink:condition_ameliorated_by",
                                                          "biolink:likelihood_affected_by"]}
    ref = EdgeReference("e0", edge, invert=True)
    preds = ref.label.split('|')
    expected_preds = [ f"`biolink:{x}`" for x in ["ameliorates_condition", "predisposes_to_condition",
                                                  "preventative_for_condition", "affects_likelihood_of"]]
    assert set(preds) == set(expected_preds)  # order doesn't matter
    assert ref.directed
    assert len(ref.filters) == 0
    assert ref.cypher_invert

def parse_filter(filter):
    """A helper that takes the string filter and breaks it into a dict for comparison to expectations.
    Filters look like this:
    ['(type(`e0`) in ["biolink:treats", "biolink:ameliorates"] AND startNode(`e0`) = `s`) OR ...
    each OR creates a dict item relating the start node to its predicates:
    {"s": set(["biolink:treats", "biolink:ameliorates"])}
    """
    parsed_filter = {}
    clauses = filter.split(" OR ")
    for clause in clauses:
        subclauses = clause[1:-1].split(" AND ")
        for subclause in subclauses:
            if subclause.startswith("startNode"):
                startnode = subclause[-2] #s or o
            else:
                predicate_set = set( literal_eval(subclause.split(" in ")[-1]))
        parsed_filter[startnode] = predicate_set
    return parsed_filter

def test_multiple_conflicting():
    """Suppose that there are two predicates, one canonical, one not.  e.g. ameliorates_condition(canonical) and
    condition_predisposed_by(non canonical).   In this case, we expect a non-directed cypher edge with all canonical
    predicates, and a where clause separating out the ones going left to right from the ones going right to left."""
    edge = {"subject": "s", "object": "o", "predicates": ["biolink:ameliorates_condition",
                                                          "biolink:likelihood_affected_by"]}
    ref = EdgeReference("e0", edge, invert=True)
    preds = ref.label.split('|')
    #Make sure that the label contains only canonical predicates
    expected_preds = [ f"`biolink:{x}`" for x in ["ameliorates_condition", "predisposes_to_condition",
                                                  "preventative_for_condition", "affects_likelihood_of"]]
    assert set(preds) == set(expected_preds) #order doesn't matter
    assert not ref.directed
    #filters should look like:
    #['(type(`e0`) in ["biolink:treats", "biolink:ameliorates"] AND startNode(`e0`) = `s`) OR (type(`e0`) in ["biolink:predisposes", "biolink:prevents", "biolink:affects_risk_for"] AND startNode(`e0`) = `o`)']
    expected_filter = {"s": set(["biolink:ameliorates_condition"]),
                       "o": set(["biolink:predisposes_to_condition",
                                 "biolink:preventative_for_condition",
                                 "biolink:affects_likelihood_of"])}
    assert len(ref.filters) == 1
    parsed_filter = parse_filter(ref.filters[0])
    assert parsed_filter == expected_filter
    assert not ref.cypher_invert

def test_symmetric_canonical():
    """Two predicates.  One symmetric, one canonical/directed.   We would expect a non-directed, non-inverted cypher
    And a where clause.   the canonical should be in one of the subclauses, and all subclasses of the symmetric
    (including any canonical/directed subclasses) should be in both."""
    edge = {"subject": "s", "object": "o", "predicates": ["biolink:correlated_with", "biolink:affects_likelihood_of"]}
    ref = EdgeReference("e0", edge, invert=True)
    preds = ref.label.split('|')
    # Make sure that the label contains only canonical predicates
    correlated_sub_preds = ["correlated_with", "biomarker_for", "coexpressed_with", "negatively_correlated_with",
                            "positively_correlated_with", "occurs_together_in_literature_with"]
    likelihood_of_sub_preds = ["predisposes_to_condition", "preventative_for_condition", "affects_likelihood_of"]
    expected_preds = [f"`biolink:{x}`" for x in correlated_sub_preds + likelihood_of_sub_preds]
    assert set(preds) == set(expected_preds)  # order doesn't matter
    assert not ref.directed
    expected_filter = {"s": set([f"biolink:{x}" for x in correlated_sub_preds + likelihood_of_sub_preds]),
                       "o": set([f"biolink:{x}" for x in correlated_sub_preds])}
    assert len(ref.filters) == 1
    parsed_filter = parse_filter(ref.filters[0])
    assert parsed_filter == expected_filter
    assert not ref.cypher_invert

def test_symmetric_noncanonical():
    """Two predicates.  One symmetric, one noncanonical/directed.   We would expect a non-directed, non-inverted cypher
    And a where clause.   the canonical should be in one of the subclauses, and all subclasses of the symmetric
    (including any canonical/directed subclasses) should be in both. Note that the ameliorates subpredicates
    have the object as the starting node in this case, unlike the canonical case above"""
    edge = {"subject": "s", "object": "o", "predicates": ["biolink:correlated_with", "biolink:likelihood_affected_by"]}
    ref = EdgeReference("e0", edge, invert=True)
    preds = ref.label.split('|')
    # Make sure that the label contains only canonical predicates
    correlated_sub_preds = ["correlated_with", "biomarker_for", "coexpressed_with", "negatively_correlated_with",
                            "positively_correlated_with", "occurs_together_in_literature_with"]
    ameliorates_sub_preds = ["predisposes_to_condition", "preventative_for_condition", "affects_likelihood_of"]
    expected_preds = [f"`biolink:{x}`" for x in correlated_sub_preds + ameliorates_sub_preds]
    assert set(preds) == set(expected_preds)  # order doesn't matter
    assert not ref.directed
    expected_filter = {"o": set([f"biolink:{x}" for x in correlated_sub_preds + ameliorates_sub_preds]),
                       "s": set([f"biolink:{x}" for x in correlated_sub_preds])}
    assert len(ref.filters) == 1
    parsed_filter = parse_filter(ref.filters[0])
    assert parsed_filter == expected_filter
    assert not ref.cypher_invert

def test_related_to():
    """If the predicate is the top-level predicate, we don't really need any subpredicates etc.  We'll accept any
    edge."""
    edge = {"subject": "s", "object": "o", "predicates": ["biolink:related_to"]}
    ref = EdgeReference("e0", edge, invert=True)
    assert ref.label == ""
    assert not ref.directed
    assert not ref.cypher_invert
    assert len(ref.filters) == 0

def test_no_predicate():
    """If the predicate is missing, we'll accept any edge."""
    edge = {"subject": "s", "object": "o"}
    ref = EdgeReference("e0", edge, invert=True)
    assert ref.label == ""
    assert not ref.directed
    assert not ref.cypher_invert
    assert len(ref.filters) == 0


def test_predicates_in_graph_setting():
    """Make sure that predicates aren't included if they aren't in the graph"""
    edge = {"subject": "s", "object": "o", "predicates": ["biolink:treats_or_applied_or_studied_to_treat"]}
    ref = EdgeReference("e0", edge, invert=True)
    preds = ref.label.split('|')
    expected_preds = [f"`biolink:{x}`" for x in ["ameliorates_condition", "applied_to_treat",
                                                 "beneficial_in_models_for", "in_clinical_trials_for",
                                                 "in_preclinical_trials_for",
                                                 "preventative_for_condition", "studied_to_treat",
                                                 "treats", "treats_or_applied_or_studied_to_treat"]]
    assert set(preds) == set(expected_preds)

    set_predicates_in_graph(["biolink:ameliorates_condition", "biolink:applied_to_treat",
                             "biolink:beneficial_in_models_for", "biolink:in_clinical_trials_for",
                             "biolink:in_preclinical_trials_for"])

    """Make sure that predicates aren't included if they aren't in the graph"""
    edge = {"subject": "s", "object": "o", "predicates": ["biolink:treats_or_applied_or_studied_to_treat"]}
    ref = EdgeReference("e0", edge, invert=True)
    preds = ref.label.split('|')
    expected_preds = [f"`biolink:{x}`" for x in ["ameliorates_condition", "applied_to_treat",
                                                 "beneficial_in_models_for", "in_clinical_trials_for",
                                                 "in_preclinical_trials_for"]]
    assert set(preds) == set(expected_preds)


def test_predicates_in_graph_setting_no_results():

    set_predicates_in_graph(["biolink:affects", "biolink:is_nonsense_variant_of"])

    # related_to should get turned into no predicates but shouldn't throw the NoPossibleResultsException
    edge = {"subject": "s", "object": "o", "predicates": ["biolink:related_to"]}
    ref = EdgeReference("e0", edge, invert=True)
    preds = ref.label.split('|')
    expected_preds = ['']
    assert preds == expected_preds

    # treats_or_applied_or_studied_to_treat nor it's descendants are in the graph, throw NoPossibleResultsException
    edge = {"subject": "s", "object": "o", "predicates": ["biolink:treats_or_applied_or_studied_to_treat"]}
    with pytest.raises(NoPossibleResultsException):
        ref = EdgeReference("e0", edge, invert=True)
