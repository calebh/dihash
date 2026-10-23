from __future__ import annotations

from enum import Enum

import networkx as nx

from .partition import canonical_count_partition, bisimulation_partition
from .util import hash_sha256, encode, invert_list

class LocalHashVariant(Enum):
    UNFOLDING = 0
    BISIMULATION = 1

# --------------------------------------------------------------------------------------------------------------------
# Local hashing in O((n+m) log^2 n) time
#
# 1. Compute the equivalence classes (isomorphic unfoldings, or bisimilarity) by partition refinement, and form the
#    quotient Q, in which distinct nodes are never equivalent.
# 2. Hash Q like a Merkle tree over its strongly connected components, sinks first. Each component, relabeled with the
#    hashes of its external successors, is serialized once, in a canonical order given by the block ids of a canonical
#    partition refinement. On Q this distinguishes exactly the non-equivalent nodes, so no node's reachable subgraph
#    ever has to be serialized on its own.
# --------------------------------------------------------------------------------------------------------------------

def _graph_lists(G):
    """
    Converts a NetworkX DiGraph or MultiDiGraph into lists: (nodes, labels, succ), where succ[i] lists the indices of\
    the successors of nodes[i], once per edge.
    """
    nodes = list(G.nodes)
    index = invert_list(nodes)
    labels = [G.nodes[n]['label'] for n in nodes]
    succ = [[index[t] for (_, t) in G.out_edges(n)] for n in nodes]
    return (nodes, labels, succ)

def _equivalence_classes(keys, succ, variant: LocalHashVariant):
    if variant == LocalHashVariant.BISIMULATION:
        return bisimulation_partition(keys, succ)
    return canonical_count_partition(keys, succ)

def _quotient_lists(labels, keys, succ, block, num_blocks, variant: LocalHashVariant):
    """
    The quotient by the equivalence classes: one node per block, with the label of any member and the blocks of its\
    successors (with multiplicity for unfoldings, as a set for bisimulation). This is independent of the member chosen.
    """
    representative = [None] * num_blocks
    for p in range(len(succ)):
        if representative[block[p]] is None:
            representative[block[p]] = p
    q_labels = [labels[r] for r in representative]
    q_keys = [keys[r] for r in representative]
    if variant == LocalHashVariant.BISIMULATION:
        q_succ = [sorted({block[t] for t in succ[r]}) for r in representative]
    else:
        q_succ = [sorted(block[t] for t in succ[r]) for r in representative]
    return (q_labels, q_keys, q_succ)

def _sc_hash_lists(labels, succ, variant: LocalHashVariant, string_hash_fun):
    """
    Local hash of a strongly connected graph given as lists (see _graph_lists). Returns (g_hash, node_hashes) with\
    node_hashes a list indexed like labels.
    """
    keys = [encode(label) for label in labels]
    # Stage 1: equivalence classes and the quotient
    (block, num_blocks) = _equivalence_classes(keys, succ, variant)
    (q_labels, q_keys, q_succ) = _quotient_lists(labels, keys, succ, block, num_blocks, variant)
    # Stage 2: canonical refinement of the quotient. No two of its nodes are equivalent, so its coarsest stable
    # partition is discrete (for bisimulation too, since counting refinement is finer than bisimulation), and the
    # canonical block ids are a canonical order of its nodes
    (canon_index, num_canon) = canonical_count_partition(q_keys, q_succ)
    if num_canon != num_blocks:
        raise AssertionError("Refinement of a reduced quotient is not discrete - this should be impossible")
    order = [None] * num_blocks
    for c in range(num_blocks):
        order[canon_index[c]] = c
    canon_labels = [q_labels[c] for c in order]
    canon_succ = [sorted(canon_index[t] for t in q_succ[c]) for c in order]
    g_hash = string_hash_fun(encode((canon_labels, canon_succ)))
    node_hashes = [string_hash_fun(encode((canon_index[block[p]], g_hash))) for p in range(len(succ))]
    return (g_hash, node_hashes)

# --------------------------------------------------------------------------------------------------------------------
# Public entry points
# --------------------------------------------------------------------------------------------------------------------

def local_hash(G, variant=LocalHashVariant.UNFOLDING, string_hash_fun=hash_sha256):
    """
    Hash every node of a directed graph by its tree expansion. When using the unfolding variant, two nodes in the same\
    graph or in different graphs will receive the same hash if and only if their (possibly infinite) tree expansions\
    are isomorphic. When using the bisimulation variant, the two nodes will receive the same hash if and only if\
    they are bisimilar.

    Runs in O((n+m) log^2 n) time for a graph with n nodes and m edges, plus the cost of hashing strings of total\
    length O(n+m) hashes.

    :param G: A NetworkX DiGraph or MultiDiGraph. Each node should have a 'label' entry in its node attribute\
    dictionary. In a MultiDiGraph, parallel edges count with multiplicity for the unfolding variant.
    :param variant: LocalHashVariant.UNFOLDING or LocalHashVariant.BISIMULATION.
    :param string_hash_fun: The string hashing function to use. By default use SHA-256
    :return: A dictionary mapping nodes to their hashes.
    """
    (nodes, labels, succ) = _graph_lists(G)
    if not nodes:
        return {}
    keys = [encode(label) for label in labels]
    (block, num_blocks) = _equivalence_classes(keys, succ, variant)
    (q_labels, _, q_succ) = _quotient_lists(labels, keys, succ, block, num_blocks, variant)

    quotient = nx.DiGraph()
    quotient.add_nodes_from(range(num_blocks))
    quotient.add_edges_from((c, t) for c in range(num_blocks) for t in q_succ[c])
    cond = nx.condensation(quotient)

    q_hash = [None] * num_blocks
    for scc in reversed(list(nx.topological_sort(cond))):
        component = sorted(cond.nodes[scc]['members'])
        inside = invert_list(component)
        # Relabel with the (multi)set of hashes of the external successors; q_succ is already a set for bisimulation
        relabeled = [(q_labels[c], sorted(q_hash[t] for t in q_succ[c] if t not in inside)) for c in component]
        internal_succ = [[inside[t] for t in q_succ[c] if t in inside] for c in component]
        (_, component_hashes) = _sc_hash_lists(relabeled, internal_succ, variant, string_hash_fun)
        for (c, h) in zip(component, component_hashes):
            q_hash[c] = h

    return {n: q_hash[block[p]] for (p, n) in enumerate(nodes)}

def local_sc_hash(sc_graph, variant=LocalHashVariant.UNFOLDING, string_hash_fun=hash_sha256):
    """
    Computes the hash of a strongly connected graph, along with the hashes of the nodes in the graph. Two nodes (in the\
    same graph or in different graphs) receive the same hash if and only if their unfoldings are isomorphic (or, for the\
    bisimulation variant, if they are bisimilar). The graph hash is the hash of the graph obtained by merging all nodes\
    with equal hashes. Runs in O((n+m) log^2 n) time, plus the cost of hashing.

    :param sc_graph: A strongly connected NetworkX DiGraph or MultiDiGraph.
    :param variant: The type of local equivalence to use. Either unfolding or bisimulation variants are supported.
    :param string_hash_fun: The string hashing function to use. By default use SHA-256
    :return: A tuple of (sc_hash, sc_node_hashes), were sc_hash gives the hash of the entire graph, and\
    sc_node_hashes is a dictionary mapping nodes to their hashes.
    """
    if not nx.is_strongly_connected(sc_graph):
        raise AssertionError("Input graph is not strongly connected")
    (nodes, labels, succ) = _graph_lists(sc_graph)
    (sc_hash, node_hashes) = _sc_hash_lists(labels, succ, variant, string_hash_fun)
    return (sc_hash, {n: h for (n, h) in zip(nodes, node_hashes)})
