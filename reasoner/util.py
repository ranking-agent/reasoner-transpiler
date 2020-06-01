"""Reasoner API conversion utilities."""


def mapize(qgraph):
    """Turn *nodes/*edges into maps."""
    if isinstance(qgraph, list):
        for operand in qgraph[1:]:
            mapize(operand)
        return
    qnodes = {
        qnode.pop('id'): qnode
        for qnode in qgraph['nodes']
    }
    qedges = {
        qedge.pop('id'): qedge
        for qedge in qgraph['edges']
    }
    qgraph['nodes'] = qnodes
    qgraph['edges'] = qedges
