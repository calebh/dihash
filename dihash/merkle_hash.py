import functools
from enum import Enum

import networkx as nx

from dihash.local_hash import local_strongly_connected_hash
from dihash.util import encode, hash_sha256
from dihash.global_hash import global_hash

class MerkleHashVariant(Enum):
    GLOBAL = 0
    LOCAL = 1

def hash_scc(g, cond, scc, scc_hashes, node_hashes, string_hash_fun, comp_hash):
    if scc in scc_hashes:
        return

    scc_members = frozenset(cond.nodes[scc]['members'])
    scc_graph = g.subgraph(scc_members).copy()

    for s in scc_members:
        non_scc_succs = frozenset(g.successors(s)) - scc_members
        # Recursively hash all nodes that are the target of an edge from within the scc to outside the scc
        for t in non_scc_succs:
            if t not in node_hashes:
                t_scc = cond.graph['mapping'][t]
                hash_scc(g, cond, t_scc, scc_hashes, node_hashes, string_hash_fun)
        non_scc_succs_hashes = sorted([node_hashes[t] for t in non_scc_succs])
        scc_graph.nodes[s]['label'] = string_hash_fun(encode((g.nodes[s]['label'], non_scc_succs_hashes)))

    (scc_hash, scc_node_hashes) = comp_hash(scc_graph)

    scc_hashes[scc] = scc_hash
    node_hashes.update(scc_node_hashes)

def merkle_hash(g, variant: MerkleHashVariant, nodes_to_hash=None, precomputed_hashes=None, string_hash_fun=hash_sha256):
    if precomputed_hashes is None:
        node_hashes = {}
    else:
        node_hashes = precomputed_hashes.copy()

    scc_hashes = {}
    cond = nx.algorithms.components.condensation(g)
    if nodes_to_hash is None:
        roots = {n for (n, d) in cond.in_degree() if d == 0}
    else:
        roots = {cond.graph['mapping'][n] for n in nodes_to_hash}

    match variant:
        case MerkleHashVariant.GLOBAL:
            component_hash = functools.partial(global_hash, hash_nodes=True, string_hash_fun=string_hash_fun)
        case MerkleHashVariant.LOCAL:
            component_hash = functools.partial(local_strongly_connected_hash, string_hash_fun=string_hash_fun)

    for r in roots:
        hash_scc(g, cond, r, scc_hashes, node_hashes, string_hash_fun, component_hash)

    return (scc_hashes, cond, node_hashes)