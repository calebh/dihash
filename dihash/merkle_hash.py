import functools

import networkx as nx

from dihash.local_hash import local_sc_hash, LocalHashVariant
from dihash.ordered_hash import ordered_sc_global_hash, _port_successors
from dihash.util import encode, hash_sha256
from dihash.global_hash import global_hash

class MerkleHashVariant:
    def __init__(self):
        if type(self) is MerkleHashVariant:
            raise ValueError("You should be constructing a particular variant using a child class of MerkleHashVariant")

class GlobalMH(MerkleHashVariant):
    """
    This indicates that global graph hashing should be used within an SCC. As such, this implementation may run
    in exponential time.
    """
    pass

class LocalMH(MerkleHashVariant):
    """
    This indicates that local graph hashing should be used within an SCC, This implementation runs in poly time.
    """

    def __init__(self, local_hash_variant: LocalHashVariant):
        """
        :param local_hash_variant: Determines if unfolding or bisimulation equivalence should be used within the SCC\
        and on outgoing edges
        """
        self.local_hash_variant = local_hash_variant

class OrderedGlobalMH(MerkleHashVariant):
    """
    This indicates that the edges of the graph are ordered, and as such an ordered aware variant of the algorithm
    should be used. This implementation runs in poly time.
    """
    pass

class OrderedLocalMH(MerkleHashVariant):
    pass

def _hash_scc(g, cond, root_scc, scc_hashes, node_hashes, string_hash_fun, comp_hash, variant: MerkleHashVariant):
    # Post-order traversal of the condensation graph with an explicit stack (a recursive traversal exceeds Python's
    # recursion limit on long chains of SCCs). An SCC is hashed once all SCCs it points to have been hashed.
    stack = [(root_scc, False)]
    while len(stack) > 0:
        (scc, children_done) = stack.pop()
        if scc in scc_hashes:
            continue

        scc_members = frozenset(cond.nodes[scc]['members'])

        if not children_done:
            stack.append((scc, True))
            for s in scc_members:
                # Hash all nodes that are the target of an edge from within the scc to outside the scc first
                for t in frozenset(g.successors(s)) - scc_members:
                    if t not in node_hashes:
                        t_scc = cond.graph['mapping'][t]
                        if t_scc not in scc_hashes:
                            stack.append((t_scc, False))
            continue

        scc_graph = g.subgraph(scc_members).copy()

        for s in scc_members:
            non_scc_succs = frozenset(g.successors(s)) - scc_members
            if isinstance(variant, OrderedGlobalMH):
                new_labels = [node_hashes[t] if t in non_scc_succs else "*" for t in _port_successors(g, s)]
            else:
                if isinstance(variant, LocalMH) and variant.local_hash_variant == LocalHashVariant.BISIMULATION:
                    new_labels = sorted({node_hashes[t] for t in non_scc_succs})
                else:
                    new_labels = sorted(node_hashes[t] for t in non_scc_succs)
            scc_graph.nodes[s]['label'] = string_hash_fun(encode((g.nodes[s]['label'], new_labels)))

        (scc_hash, scc_node_hashes) = comp_hash(scc_graph)

        scc_hashes[scc] = scc_hash
        node_hashes.update(scc_node_hashes)

def merkle_hash(g: nx.DiGraph, variant: MerkleHashVariant, nodes_to_hash=None, precomputed_hashes=None, string_hash_fun=hash_sha256):
    """
    Computes a recursive Merkle hash by recursing over the condensation graph.

    :param g: A NetworkX directed graph
    :param variant: The particular Merkle hash variant to use. See the docstrings for the subclasses of\
    MerkleHashVariant for more info.
    :param nodes_to_hash: The nodes that we want to compute the Merkle hash of
    :param precomputed_hashes: A precomputed dict of node Merkle hashes. This parameter should be a dict mapping\
    nodes to hashes. This parameter is useful for graphs that are built up over time. In this case we can\
    simulate a graph built up over time.
    :param string_hash_fun: The string hashing function to use.
    :return: A tuple with three elements (scc_hashes, cond, node_hashes). The scc_hashes is a dict of SCCs to their\
    overall hashes. cond is the condensation graph computed in the Merkle hashes using the\
    nx.algorithms.components.condensation function. node_hashes maps nodes to their hashes.
    """
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

    if isinstance(variant, GlobalMH):
        component_hash = functools.partial(global_hash, hash_nodes=True, string_hash_fun=string_hash_fun)
    elif isinstance(variant, LocalMH):
        component_hash = functools.partial(local_sc_hash, variant=variant.local_hash_variant, string_hash_fun=string_hash_fun)
    elif isinstance(variant, OrderedGlobalMH):
        component_hash = functools.partial(ordered_sc_global_hash, hash_nodes=True, string_hash_fun=string_hash_fun)
    elif isinstance(variant, OrderedLocalMH):
        # It should be possible to implement an OrderedLocalMHVariant using DFA partition refinement. With the order of the
        # edges, this algorithm should be even faster than LocalMHVariant
        raise NotImplementedError("At the moment ordered local Merkle-hashing is not implemented. It should be possible to implement this efficiently using DFA partition refinement.")
    else:
        raise NotImplementedError(f"Unknown variant {variant}")

    for r in roots:
        _hash_scc(g, cond, r, scc_hashes, node_hashes, string_hash_fun, component_hash, variant)

    return (scc_hashes, cond, node_hashes)