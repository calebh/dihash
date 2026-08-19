"""
Canonical, graph-independent tree-expansion hashing.

Pipeline
--------
1. Color refinement on the input graph to *global* stabilization. The
   converged partition identifies exactly the tree-equal (counting-bisimilar)
   nodes.
2. Quotient multi-digraph Q: one node per class, carrying the common label;
   edges from a class are the edges of any representative, retargeted to
   classes and kept with multiplicity (well-defined because the converged
   partition is a counting bisimulation).
3. On Q, run refinement with per-node reachable-partition stabilization.
   When node n stabilizes at round k = stab(n), the round-k colors are
   pairwise distinct on reachable(n): the stabilized partition of a
   reachable set is a counting bisimulation, and Q is reduced (distinct
   nodes have distinct tree expansions), so the partition is discrete.
   Sorting reachable(n) by the round-stab(n) colors therefore yields a
   strict total order. Crucially the *whole subgraph* is ordered by colors
   from n's own stabilization round -- NOT by each member's own frozen
   hash, which can tie across distinct classes.
4. The final hash of n is the digest of the canonically ordered adjacency
   serialization of reachable(n) in Q: root index, then per class in order
   its label digest and sorted (target-index * multiplicity) edge list.

Canonicity: stab(n), every color used, the order, the indices, and hence
the serialization are all functions of T(n) alone (refinement is autonomous
on reachable sets; the stabilization round is determined by the tree). So
the same tree expansion hashes identically in *any* graph. Completeness:
the serialization injectively encodes the rooted labeled multigraph, whose
unrolling from the root is exactly T(n).
"""

import networkx as nx
from .util import hash_sha256, to_str

# --------------------------------------------------------------------------
# Shared refinement machinery (works for DiGraph and MultiDiGraph: child
# colors are collected per *edge*, so parallel edges count with multiplicity)
# --------------------------------------------------------------------------

def _refine_round(G, colors, label_digest, string_hash_fun, memo):
    new_colors = {}
    for n in G.nodes:
        children = sorted(colors[t] for _, t in G.out_edges(n))
        signature = to_str((label_digest[n], children))
        digest = memo.get(signature)
        if digest is None:
            digest = string_hash_fun(signature)
            memo[signature] = digest
        new_colors[n] = digest
    return new_colors


def _partition_unchanged(nodes, old_colors, new_colors):
    """True iff old and new colors induce the same partition on `nodes`.

    Refinement only splits classes, so it suffices to check that every old
    class maps onto a single new color."""
    old_to_new = {}
    for n in nodes:
        prev = old_colors[n]
        seen = old_to_new.get(prev)
        if seen is None:
            old_to_new[prev] = new_colors[n]
        elif seen != new_colors[n]:
            return False
    return True


def _globally_stable_colors(G, string_hash_fun):
    """Colors at the first round whose refinement changes no class globally."""
    label_digest = {n: string_hash_fun(G.nodes[n]["label"]) for n in G.nodes}
    colors = dict(label_digest)
    nodes = list(G.nodes)
    while True:
        new_colors = _refine_round(G, colors, label_digest, string_hash_fun, {})
        if _partition_unchanged(nodes, colors, new_colors):
            return new_colors
        colors = new_colors


# --------------------------------------------------------------------------
# Step 2: quotient multi-digraph
# --------------------------------------------------------------------------

def quotient_multidigraph(G, class_of):
    """Quotient of G by the partition `class_of` (node -> class id).

    Edges of one representative per class are used; for the converged
    refinement partition this is representative-independent, including
    multiplicities."""
    Q = nx.MultiDiGraph()
    representative = {}
    for n in G.nodes:
        c = class_of[n]
        if c not in representative:
            representative[c] = n
            Q.add_node(c, label=G.nodes[n]["label"])
    for c, r in representative.items():
        for _, t in G.out_edges(r):
            Q.add_edge(c, class_of[t])
    return Q


# --------------------------------------------------------------------------
# Steps 3-4: canonical ordering and serialization on the reduced quotient
# --------------------------------------------------------------------------

def _serialize_reachable(Q: nx.MultiDiGraph, root, reach, round_colors, string_hash_fun):
    order = sorted(reach, key=lambda x: round_colors[x])
    if len({round_colors[x] for x in reach}) != len(reach):
        raise AssertionError(
            "colors not discrete on a stabilized reachable set of a "
            "reduced quotient -- this should be impossible")
    index = {x: i for i, x in enumerate(order)}
    root_idx = index[root]
    adj_list = sorted([(index[s], index[t]) for (s, t, _) in Q.edges if s in reach and t in reach])
    labels = [Q.nodes[x]["label"] for x in order]
    return string_hash_fun(to_str((root_idx, labels, adj_list)))

def _canonical_quotient_hashes(Q, string_hash_fun):
    nodes = list(Q.nodes)
    if not nodes:
        return {}
    label_digest = {n: string_hash_fun(Q.nodes[n]["label"]) for n in nodes}
    reachable = {n: nx.descendants(Q, n) | {n} for n in nodes}
    colors = dict(label_digest)
    final_hash = {}
    stable = set()
    while len(stable) < len(nodes):
        new_colors = _refine_round(Q, colors, label_digest, string_hash_fun, {})
        for n in nodes:
            if n in stable:
                continue
            if _partition_unchanged(reachable[n], colors, new_colors):
                stable.add(n)
                # Order n's WHOLE reachable set by the colors of n's own
                # stabilization round (uniform round per subgraph).
                final_hash[n] = _serialize_reachable(Q, n, reachable[n], colors, string_hash_fun)
        colors = new_colors
    return final_hash

# --------------------------------------------------------------------------
# Public entry point
# --------------------------------------------------------------------------

def canonical_tree_hashes(G, string_hash_fun=hash_sha256):
    """Hash every node of a directed graph by its tree expansion.

    Guarantee (modulo hash collisions): two nodes -- in the same graph or in
    different graphs -- receive the same hash iff their (possibly infinite)
    tree expansions are equal.
    """
    if G.number_of_nodes() == 0:
        return {}
    class_of = _globally_stable_colors(G, string_hash_fun)
    Q = quotient_multidigraph(G, class_of)
    quotient_hash = _canonical_quotient_hashes(Q, string_hash_fun)
    return {n: quotient_hash[class_of[n]] for n in G.nodes}