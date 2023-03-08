import pytest
from reasoner_transpiler.matching import EdgeReference

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

def test_directed():
    """For a directed parent predicate, all the children should be directed.  This should just have the
    subpredicates.  There's no WHERE block needed because all of the canonical versions of the predicates
    point the same direction by construction, and these are included in the --> syntax of the cypher.
    That happens in EdgeReference.str() if reference.directed is True."""
    edge= {"subject": "s", "object": "o", "predicates": "biolink:affects"}
    ref = EdgeReference("e0", edge, invert=True)
    preds = ref.label.split('|')
    assert len(preds) == 11
    assert ref.directed
    assert len(ref.filters) == 0
