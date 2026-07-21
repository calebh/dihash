"""
Directed graph node hashing via color refinement with Merkle-style hash
compaction and per-node stabilization.

Semantics
---------
The hash of a node is determined by its (possibly infinite) tree expansion:
the tree obtained by unrolling all walks leaving the node. Two nodes whose
tree expansions are equal receive the same hash.

The algorithm is color refinement (1-dimensional Weisfeiler-Leman restricted
to successors). Conceptually, iteration k assigns each node the nested
multiset

    C_0(n) = label(n)
    C_{k+1}(n) = ( label(n), {{ C_k(s) : s in successors(n) }} )

which is exactly the depth-k tree expansion of n, built bottom-up. Instead of
materializing these nested multisets we compact them Merkle-tree style: each
node's color is a single digest computed from its label digest and the sorted
digests of its successors' colors from the previous round. Because the
construction is bottom-up, the digest of a shared subtree is computed once per
round and reused by every node that hangs it off a successor edge (a memo
table additionally collapses identical signatures within a round).

Stabilization
-------------
A node n is *stable* at the first iteration whose refinement step fails to
change the partition (the grouping of nodes into color classes) of the
subgraph reachable from n. Note the color *values* keep changing every round;
what stabilizes is the induced partition. Since the reachable set of n is
closed under successors, refinement restricted to it is autonomous, so once
its partition stops changing it never changes again -- freezing at the first
stable iteration is sound.

Different nodes may stabilize at different iterations, so the returned
dictionary generally mixes digests from different rounds. This is consistent:
two nodes with equal tree expansions have identical color values at *every*
round, and the set of tree expansions occurring in their reachable sets is
determined by the tree expansion itself, so they also stabilize at the same
round and thus receive the same final digest.

Complexity: O(I * (V + E)) for the refinement itself and O(I * sum |reach(n)|)
for the stability bookkeeping, where I <= V + 1 is the number of iterations.
"""

import hashlib

import networkx as nx
from .util import hash_sha256, to_str


def tree_expansion_hash(G, string_hash_fun=hash_sha256):
    """Hash every node of a directed graph by its tree expansion.

    Parameters
    ----------
    G : networkx.DiGraph
        Directed graph; every node must carry a string attribute "label".
    string_hash_fun : callable
        String -> digest-string hash function (default: SHA-256 hex digest).

    Returns
    -------
    dict
        Mapping of each node to its final (stable) hash digest.
    """
    nodes = list(G.nodes)
    if not nodes:
        return {}

    # Hash labels once. Combining *digests* (fixed-length, fixed-alphabet)
    # rather than raw labels keeps the encoding unambiguous even if labels
    # contain the separator characters used below.
    label_digest = {n: string_hash_fun(G.nodes[n]["label"]) for n in nodes}

    # Reachable set of each node (including the node itself). Needed to
    # decide, per node, when the partition of its reachable subgraph stops
    # changing.
    reachable = {n: nx.descendants(G, n) | {n} for n in nodes}

    # Round 0: the color of a node is the digest of its label
    # (depth-0 tree expansion).
    colors = dict(label_digest)

    final_hash = {}
    stable = set()

    # Color refinement only ever refines the global partition, and the global
    # partition over V nodes can refine at most V - 1 times. The first round
    # in which the partition of a node's reachable subgraph does not change,
    # that node is done; a round with no global change finishes everyone, so
    # the loop runs at most V + 1 times.
    while len(stable) < len(nodes):
        # ---- Refinement step (bottom-up Merkle compaction) ----
        # signature = label digest + sorted successor digests of the previous
        # round. Sorting encodes the *multiset* of child subtrees. The memo
        # table shares the digest computation among nodes whose depth-k
        # subtrees are identical.
        memo = {}
        new_colors = {}
        for n in nodes:
            children = sorted(colors[s] for s in G.successors(n))
            signature = to_str((label_digest[n], children))
            digest = memo.get(signature)
            if digest is None:
                digest = string_hash_fun(signature)
                memo[signature] = digest
            new_colors[n] = digest

        # ---- Per-node stability check ----
        # The partition of reachable(n) is unchanged by this round iff every
        # old color class within reachable(n) maps to a single new color
        # (refinement can only split classes, never merge them, so this is
        # the full old-partition == new-partition test).
        for n in nodes:
            if n in stable:
                continue
            old_to_new = {}
            unchanged = True
            for m in reachable[n]:
                prev = colors[m]
                seen = old_to_new.get(prev)
                if seen is None:
                    old_to_new[prev] = new_colors[m]
                elif seen != new_colors[m]:
                    unchanged = False
                    break
            if unchanged:
                stable.add(n)
                # The node's final hash is its digest from the round in
                # which it became stable.
                final_hash[n] = new_colors[n]

        colors = new_colors

    return final_hash