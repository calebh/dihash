"""
Randomized differential tests: every hash in the library is compared, on many pairs of small random graphs, with an
independent brute-force decision procedure for the equivalence it is supposed to realize (see brute_force.py).
Half of the pairs are a graph and a shuffled isomorphic copy (fresh node names, random insertion order), so these
tests also check that hashes do not depend on node names or insertion order.
"""
import os
import random

import networkx as nx
import pytest

import dihash
from dihash.local_hash import LocalHashVariant, local_hash, local_sc_hash
from dihash.merkle_hash import merkle_hash, GlobalMH, LocalMH, OrderedGlobalMH, OrderedLocalMH
from dihash.ordered_hash import (ordered_node_hash, ordered_sc_global_hash, ordered_local_hash, ordered_sc_local_hash,
                                 _canonical_partition)

import brute_force as bf

# Number of random graph pairs per test; raise it (e.g. DIHASH_TRIALS=5000) for a more thorough search
TRIALS = int(os.environ.get("DIHASH_TRIALS", 150))
MAX_NODES = int(os.environ.get("DIHASH_MAX_NODES", 6))


def pairs(seed, ordered=False, trials=None, max_nodes=None, multi=False):
    trials = TRIALS if trials is None else trials
    max_nodes = MAX_NODES if max_nodes is None else max_nodes
    rng = random.Random(seed + int(os.environ.get("DIHASH_SEED", 0)))
    for _ in range(trials):
        yield bf.random_pair(rng, max_nodes=max_nodes, ordered=ordered, multi=multi)


def sccs_of(g):
    return [g.subgraph(c).copy() for c in nx.strongly_connected_components(g)]


# ---------------------------------------------------------------------------------------------------------------------
# Global hashing (Section 3)
# ---------------------------------------------------------------------------------------------------------------------

def test_global_graph_hash_iff_isomorphic():
    for (g1, g2) in pairs(1):
        assert (dihash.global_hash(g1) == dihash.global_hash(g2)) == bf.is_isomorphic(g1, g2)


def test_global_node_hash_iff_rooted_isomorphic():
    for (g1, g2) in pairs(2):
        (_, h1) = dihash.global_hash(g1, hash_nodes=True)
        (_, h2) = dihash.global_hash(g2, hash_nodes=True)
        isos = list(bf.isomorphisms(g1, g2))
        for u in g1:
            for v in g2:
                assert (h1[u] == h2[v]) == any(f[u] == v for f in isos), (u, v)


def test_global_node_hash_iff_same_orbit():
    for (g, _) in pairs(3):
        (_, h) = dihash.global_hash(g, hash_nodes=True)
        auts = list(bf.isomorphisms(g, g))
        for u in g:
            for v in g:
                assert (h[u] == h[v]) == any(a[u] == v for a in auts)


# ---------------------------------------------------------------------------------------------------------------------
# Local hashing (Section 4)
# ---------------------------------------------------------------------------------------------------------------------

def test_local_hash_iff_unfoldings_isomorphic():
    for (g1, g2) in pairs(4):
        (h1, h2) = (local_hash(g1), local_hash(g2))
        (t1, t2) = bf.unfolding_classes(g1, g2)
        for u in g1:
            for v in g2:
                assert (h1[u] == h2[v]) == (t1[u] == t2[v]), (u, v)


def test_local_hash_bisimulation_iff_bisimilar():
    for (g1, g2) in pairs(5):
        h1 = local_hash(g1, variant=LocalHashVariant.BISIMULATION)
        h2 = local_hash(g2, variant=LocalHashVariant.BISIMULATION)
        bisim = bf.bisimulation_classes(g1, g2)
        for u in g1:
            for v in g2:
                assert (h1[u] == h2[v]) == bisim(u, v), (u, v)


@pytest.mark.parametrize("variant", [LocalHashVariant.UNFOLDING, LocalHashVariant.BISIMULATION])
def test_local_strongly_connected_hash(variant):
    """Local component hash (Algorithm "Local Component Hash"): on strongly connected graphs, node hashes are equal iff
    the unfoldings are isomorphic (resp. the nodes are bisimilar); the graph hash is invariant under isomorphism."""
    rng = random.Random(6)
    for (g1, g2) in pairs(6):
        for s1 in sccs_of(g1):
            for s2 in sccs_of(g2):
                (gh1, h1) = local_sc_hash(s1, variant=variant)
                (gh2, h2) = local_sc_hash(s2, variant=variant)
                if variant == LocalHashVariant.UNFOLDING:
                    (t1, t2) = bf.unfolding_classes(s1, s2)
                    same = lambda u, v: t1[u] == t2[v]
                else:
                    same = bf.bisimulation_classes(s1, s2)
                for u in s1:
                    for v in s2:
                        assert (h1[u] == h2[v]) == same(u, v), (u, v)
            (copy, mapping) = bf.shuffled_copy(rng, s1)
            (gh_copy, h_copy) = local_sc_hash(copy, variant=variant)
            assert gh_copy == local_sc_hash(s1, variant=variant)[0]


def test_local_strongly_connected_hash_rejects_non_scc():
    g = nx.DiGraph()
    g.add_node(0, label='a')
    g.add_node(1, label='a')
    g.add_edge(0, 1)
    with pytest.raises(AssertionError):
        local_sc_hash(g)


# ---------------------------------------------------------------------------------------------------------------------
# Ordered outgoing edges (Section 5)
# ---------------------------------------------------------------------------------------------------------------------

MULTI = pytest.mark.parametrize("multi", [False, True], ids=["digraph", "multidigraph"])


@MULTI
def test_ordered_node_hash_iff_ordered_rooted_isomorphic(multi):
    for (g1, g2) in pairs(7, ordered=True, multi=multi):
        h1 = {u: ordered_node_hash(g1, u) for u in g1}
        h2 = {v: ordered_node_hash(g2, v) for v in g2}
        for u in g1:
            for v in g2:
                assert (h1[u] == h2[v]) == bf.ordered_rooted_isomorphic(g1, u, g2, v), (u, v)


def test_ordered_sc_global_hash():
    """On strongly connected ordered graphs: graph hashes are equal iff the graphs are ordered-isomorphic, and node
    hashes are equal iff some ordered isomorphism maps one node to the other (orbits within one graph)."""
    for (g1, g2) in pairs(8, ordered=True):
        for s1 in sccs_of(g1):
            for s2 in sccs_of(g2):
                (gh1, h1) = ordered_sc_global_hash(s1, hash_nodes=True)
                (gh2, h2) = ordered_sc_global_hash(s2, hash_nodes=True)
                assert gh1 == ordered_sc_global_hash(s1)  # hash_nodes=False returns the same graph hash
                assert (gh1 == gh2) == bf.is_isomorphic(s1, s2, ordered=True)
                for u in s1:
                    for v in s2:
                        assert (h1[u] == h2[v]) == bf.ordered_rooted_isomorphic(s1, u, s2, v), (u, v)


@MULTI
def test_ordered_local_hash_iff_ordered_unfoldings_isomorphic(multi):
    for (g1, g2) in pairs(15, ordered=True, multi=multi):
        (h1, h2) = (ordered_local_hash(g1), ordered_local_hash(g2))
        (t1, t2) = bf.unfolding_classes(g1, g2, ordered=True)
        for u in g1:
            for v in g2:
                assert (h1[u] == h2[v]) == (t1[u] == t2[v]), (u, v)


@MULTI
def test_ordered_sc_local_hash(multi):
    """On strongly connected ordered graphs: node hashes are equal iff the ordered unfoldings are isomorphic, and graph
    hashes are equal iff some node of one graph has the same ordered unfolding as some node of the other."""
    for (g1, g2) in pairs(16, ordered=True, multi=multi):
        for s1 in sccs_of(g1):
            for s2 in sccs_of(g2):
                (gh1, h1) = ordered_sc_local_hash(s1)
                (gh2, h2) = ordered_sc_local_hash(s2)
                (t1, t2) = bf.unfolding_classes(s1, s2, ordered=True)
                some_pair_equivalent = False
                for u in s1:
                    for v in s2:
                        assert (h1[u] == h2[v]) == (t1[u] == t2[v]), (u, v)
                        some_pair_equivalent |= t1[u] == t2[v]
                assert (gh1 == gh2) == some_pair_equivalent


def test_canonical_partition_is_invariant_under_renumbering():
    """The block ids computed by the DFA minimization must not depend on how the states are numbered: this is what
    makes them usable as a canonical order."""
    rng = random.Random(17)
    for _ in range(4 * TRIALS):
        n = rng.randint(1, rng.choice([12, 40]))
        keys = [rng.choice("ab") for _ in range(n)]
        out = [[rng.randrange(n) for _ in range(rng.choice([0, 1, 1, 2, 2, 3]))] for _ in range(n)]
        (block, num_blocks) = _canonical_partition(keys, out)
        perm = list(range(n))
        rng.shuffle(perm)  # state p is renamed perm[p]
        inverse = [0] * n
        for (p, q) in enumerate(perm):
            inverse[q] = p
        keys2 = [keys[inverse[q]] for q in range(n)]
        out2 = [[perm[t] for t in out[inverse[q]]] for q in range(n)]
        (block2, num_blocks2) = _canonical_partition(keys2, out2)
        assert num_blocks2 == num_blocks
        assert all(block2[perm[p]] == block[p] for p in range(n))
        # and the partition is the coarsest stable one: equal blocks <=> equal ordered unfoldings
        g = nx.MultiDiGraph()
        for p in range(n):
            g.add_node(p, label=keys[p])
        for p in range(n):
            for (port, t) in enumerate(out[p]):
                g.add_edge(p, t, port=port)
        (t1, _) = bf.unfolding_classes(g, g, ordered=True)
        for p in range(n):
            for q in range(n):
                assert (block[p] == block[q]) == (t1[p] == t1[q])


def node_splitting_variants(seed, ordered, multi=False, rounds=3, strongly_connected=False):
    """Yields (g, h, origin): h arises from g by up to `rounds` unfolding-preserving node splits (see
    brute_force.split_node), so every node of h must hash like its origin in g under any unfolding-based hash. With
    strongly_connected=True, only pairs where both g and h are strongly connected are yielded."""
    rng = random.Random(seed)
    yielded = 0
    while yielded < TRIALS:
        g = bf.random_digraph(rng, rng.randint(2 if strongly_connected else 1, MAX_NODES), rng.choice([0.3, 0.45, 0.6]),
                              rng.choice([["a"], ["a", "b"]]), ordered=ordered, multi=multi)
        if strongly_connected and not nx.is_strongly_connected(g):
            continue
        (h, origin) = (g, {n: n for n in g.nodes})
        for _ in range(rng.randint(1, rounds)):
            result = bf.split_node(rng, h, ordered)
            if result is None:
                break
            (h, step) = result
            origin = {n: origin[step[n]] for n in h.nodes}
        if strongly_connected and not nx.is_strongly_connected(h):
            continue
        (h, rename) = bf.shuffled_copy(rng, h)
        yielded += 1
        yield (g, h, {rename[n]: origin[n] for n in rename})


@MULTI
def test_ordered_local_hashes_are_invariant_under_node_splitting(multi):
    """Graphs with the same minimal quotient but different sizes: the hashes must not depend on anything but the
    unfolding (this catches canonical orders that are only canonical up to isomorphism of the whole input)."""
    for (g, h, origin) in node_splitting_variants(20, ordered=True, multi=multi):
        (hg, hh) = (ordered_local_hash(g), ordered_local_hash(h))
        assert all(hh[n] == hg[origin[n]] for n in h.nodes)
        if nx.is_strongly_connected(g) and nx.is_strongly_connected(h):
            ((gg, ng), (gh, nh)) = (ordered_sc_local_hash(g), ordered_sc_local_hash(h))
            assert gg == gh and all(nh[n] == ng[origin[n]] for n in h.nodes)


@MULTI
def test_ordered_sc_local_hash_is_invariant_under_node_splitting(multi):
    """Strongly connected graphs with isomorphic minimal quotients but different sizes must get the same graph hash.
    This requires the second refinement stage on the quotient: the block order computed on the graph itself is only
    canonical up to isomorphism of the graph."""
    for (g, h, origin) in node_splitting_variants(22, ordered=True, multi=multi, rounds=6, strongly_connected=True):
        ((gg, ng), (gh, nh)) = (ordered_sc_local_hash(g), ordered_sc_local_hash(h))
        assert gg == gh and all(nh[n] == ng[origin[n]] for n in h.nodes)
        (_, _, mg) = merkle_hash(g, OrderedLocalMH())
        (_, _, mh) = merkle_hash(h, OrderedLocalMH())
        assert all(mh[n] == mg[origin[n]] for n in h.nodes)


def test_local_sc_hash_is_invariant_under_node_splitting():
    for (g, h, origin) in node_splitting_variants(23, ordered=False, rounds=6, strongly_connected=True):
        for variant in (LocalHashVariant.UNFOLDING, LocalHashVariant.BISIMULATION):
            ((gg, ng), (gh, nh)) = (local_sc_hash(g, variant=variant), local_sc_hash(h, variant=variant))
            assert gg == gh and all(nh[n] == ng[origin[n]] for n in h.nodes)


def test_local_hashes_are_invariant_under_node_splitting():
    for (g, h, origin) in node_splitting_variants(21, ordered=False):
        for variant in (LocalHashVariant.UNFOLDING, LocalHashVariant.BISIMULATION):
            (hg, hh) = (local_hash(g, variant=variant), local_hash(h, variant=variant))
            assert all(hh[n] == hg[origin[n]] for n in h.nodes)
            if nx.is_strongly_connected(g) and nx.is_strongly_connected(h):
                ((gg, ng), (gh, nh)) = (local_sc_hash(g, variant=variant), local_sc_hash(h, variant=variant))
                assert gg == gh and all(nh[n] == ng[origin[n]] for n in h.nodes)


# ---------------------------------------------------------------------------------------------------------------------
# Merkle hashing (Section 6)
# ---------------------------------------------------------------------------------------------------------------------

def test_merkle_global_iff_global_merkle_equivalent():
    for (g1, g2) in pairs(9):
        (_, _, h1) = merkle_hash(g1, GlobalMH())
        (_, _, h2) = merkle_hash(g2, GlobalMH())
        eq = bf.merkle_global_equivalence(g1, g2)
        for u in g1:
            for v in g2:
                assert (h1[u] == h2[v]) == eq(u, v), (u, v)


@MULTI
def test_merkle_ordered_global_iff_global_merkle_equivalent(multi):
    for (g1, g2) in pairs(10, ordered=True, multi=multi):
        (_, _, h1) = merkle_hash(g1, OrderedGlobalMH())
        (_, _, h2) = merkle_hash(g2, OrderedGlobalMH())
        eq = bf.merkle_global_equivalence(g1, g2, ordered=True)
        for u in g1:
            for v in g2:
                assert (h1[u] == h2[v]) == eq(u, v), (u, v)


def test_merkle_local_iff_annotated_unfoldings_isomorphic():
    """Local Merkle variant: equal hashes iff the SCC-annotated unfoldings are isomorphic (Proposition in Sec. 6)."""
    for (g1, g2) in pairs(11):
        (_, _, h1) = merkle_hash(g1, LocalMH(LocalHashVariant.UNFOLDING))
        (_, _, h2) = merkle_hash(g2, LocalMH(LocalHashVariant.UNFOLDING))
        (t1, t2) = bf.unfolding_classes(g1, g2, annotate=True)
        for u in g1:
            for v in g2:
                assert (h1[u] == h2[v]) == (t1[u] == t2[v]), (u, v)


def test_merkle_local_bisimulation_iff_annotated_bisimilar():
    """Bisimulation flavour of the local Merkle variant: equal hashes iff the nodes are bisimilar when every edge is
    labeled by whether it stays inside its SCC."""
    for (g1, g2) in pairs(12):
        (_, _, h1) = merkle_hash(g1, LocalMH(LocalHashVariant.BISIMULATION))
        (_, _, h2) = merkle_hash(g2, LocalMH(LocalHashVariant.BISIMULATION))
        bisim = bf.bisimulation_classes(g1, g2, annotate=True)
        for u in g1:
            for v in g2:
                assert (h1[u] == h2[v]) == bisim(u, v), (u, v)


@MULTI
def test_merkle_ordered_local_iff_annotated_ordered_unfoldings_isomorphic(multi):
    """Ordered local Merkle variant: equal hashes iff the SCC-annotated ordered unfoldings are isomorphic."""
    for (g1, g2) in pairs(18, ordered=True, multi=multi):
        (_, _, h1) = merkle_hash(g1, OrderedLocalMH())
        (_, _, h2) = merkle_hash(g2, OrderedLocalMH())
        (t1, t2) = bf.unfolding_classes(g1, g2, ordered=True, annotate=True)
        for u in g1:
            for v in g2:
                assert (h1[u] == h2[v]) == (t1[u] == t2[v]), (u, v)


@MULTI
def test_ordered_merkle_implication_chain(multi):
    """Ordered: global Merkle => local Merkle => ordered unfolding isomorphism."""
    for (g1, g2) in pairs(19, ordered=True, multi=multi):
        (_, _, glob1) = merkle_hash(g1, OrderedGlobalMH())
        (_, _, glob2) = merkle_hash(g2, OrderedGlobalMH())
        (_, _, loc1) = merkle_hash(g1, OrderedLocalMH())
        (_, _, loc2) = merkle_hash(g2, OrderedLocalMH())
        (unf1, unf2) = (ordered_local_hash(g1), ordered_local_hash(g2))
        for u in g1:
            for v in g2:
                if glob1[u] == glob2[v]:
                    assert loc1[u] == loc2[v]
                if loc1[u] == loc2[v]:
                    assert unf1[u] == unf2[v]


def test_merkle_implication_chain():
    """rooted isomorphism => global Merkle => local Merkle => unfolding isomorphism (Proposition in Sec. 6)."""
    for (g1, g2) in pairs(13):
        (_, _, glob1) = merkle_hash(g1, GlobalMH())
        (_, _, glob2) = merkle_hash(g2, GlobalMH())
        (_, _, loc1) = merkle_hash(g1, LocalMH(LocalHashVariant.UNFOLDING))
        (_, _, loc2) = merkle_hash(g2, LocalMH(LocalHashVariant.UNFOLDING))
        (unf1, unf2) = (local_hash(g1), local_hash(g2))
        for u in g1:
            for v in g2:
                if glob1[u] == glob2[v]:
                    assert loc1[u] == loc2[v]
                if loc1[u] == loc2[v]:
                    assert unf1[u] == unf2[v]


@pytest.mark.parametrize("make_variant", [GlobalMH, lambda: LocalMH(LocalHashVariant.UNFOLDING),
                                          lambda: LocalMH(LocalHashVariant.BISIMULATION)],
                         ids=["global", "local-unfolding", "local-bisimulation"])
def test_merkle_nodes_to_hash_and_precomputed_hashes(make_variant):
    """Hashing only some nodes, or reusing precomputed hashes of an earlier graph, gives the same hashes as hashing
    everything from scratch. Adding a node whose edges point only into the existing graph changes no existing hash."""
    rng = random.Random(14)
    for _ in range(60):
        g = bf.random_digraph(rng, rng.randint(1, 7), rng.choice([0.15, 0.3]), ["a", "b"])
        (_, _, full) = merkle_hash(g, make_variant())
        some = rng.sample(list(g.nodes), rng.randint(1, g.order()))
        (_, _, partial) = merkle_hash(g, make_variant(), nodes_to_hash=some)
        for n in partial:
            assert partial[n] == full[n]
        for n in some:
            assert n in partial

        bigger = g.copy()
        bigger.add_node("new", label="a")
        for n in rng.sample(list(g.nodes), rng.randint(0, g.order())):
            bigger.add_edge("new", n)
        (_, _, incremental) = merkle_hash(bigger, make_variant(), nodes_to_hash=["new"], precomputed_hashes=full)
        (_, _, scratch) = merkle_hash(bigger, make_variant())
        assert incremental["new"] == scratch["new"]
        for n in g.nodes:
            assert scratch[n] == full[n]
