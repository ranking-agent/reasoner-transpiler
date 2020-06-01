"""Reasoner API conversion utilities."""


def mapize(qgraph):
    """Turn *nodes/*edges into maps."""
    if isinstance(qgraph, list):
        return [qgraph[0]] + [
            mapize(operand)
            for operand in qgraph[1:]
        ]
    qnodes = {
        qnode['id']: {
            key: value
            for key, value in qnode.items()
            if key != 'id'
        }
        for qnode in qgraph['nodes']
    }
    qedges = {
        qedge['id']: {
            key: value
            for key, value in qedge.items()
            if key != 'id'
        }
        for qedge in qgraph['edges']
    }
    return {
        'nodes': qnodes,
        'edges': qedges,
    }
