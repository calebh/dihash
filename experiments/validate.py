"""
Validation table of the paper (Table "Validation against brute-force equivalence checks").

Compares every hash of the library with the independent brute-force decision procedures in tests/brute_force.py on
random pairs of small labeled graphs, and prints the number of node pairs (or graphs) checked per scheme as JSON.
Any disagreement raises an AssertionError.

Usage: python experiments/validate.py [--trials N]
The paper uses the default of 3000 random pairs per scheme (results/validation.json).
"""
import argparse
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / 'tests'), str(ROOT)]

import networkx as nx

import brute_force as bf
import dihash
from dihash.local_hash import local_hash, local_sc_hash, LocalHashVariant as V
from dihash.ordered_hash import ordered_node_hash, ordered_sc_global_hash, ordered_local_hash, ordered_sc_local_hash
from dihash.merkle_hash import merkle_hash, GlobalMH, LocalMH, OrderedGlobalMH, OrderedLocalMH

parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
parser.add_argument('--trials', type=int, default=3000, help='random graph pairs per scheme (default: 3000)')
TRIALS = parser.parse_args().trials

count = {}


def add(key, n=1):
    count[key] = count.get(key, 0) + n


def check(condition, msg):
    if not condition:
        raise AssertionError(msg)


def sccs(g):
    return [g.subgraph(c).copy() for c in nx.strongly_connected_components(g)]


def pairs(seed, ordered=False, multi=False):
    rng = random.Random(seed)
    for _ in range(TRIALS):
        yield bf.random_pair(rng, max_nodes=6, ordered=ordered, multi=multi)


# Global graph and node hashes
for g1, g2 in pairs(1):
    iso = list(bf.isomorphisms(g1, g2))
    gh1, h1 = dihash.global_hash(g1, hash_nodes=True)
    gh2, h2 = dihash.global_hash(g2, hash_nodes=True)
    check((gh1 == gh2) == bool(iso), "global")
    add("global_graph")
    for u in g1:
        for v in g2:
            check((h1[u] == h2[v]) == any(f[u] == v for f in iso), "global node")
            add("global_node")

# Local hash, bisimulation hash and the two local component hashes (digraphs and multidigraphs)
for multi in (False, True):
    for g1, g2 in pairs(2 + multi, multi=multi):
        t1, t2 = bf.unfolding_classes(g1, g2)
        bis = bf.bisimulation_classes(g1, g2)
        l1, l2 = local_hash(g1), local_hash(g2)
        b1, b2 = local_hash(g1, variant=V.BISIMULATION), local_hash(g2, variant=V.BISIMULATION)
        for u in g1:
            for v in g2:
                check((l1[u] == l2[v]) == (t1[u] == t2[v]), "local")
                add("local")
                check((b1[u] == b2[v]) == bis(u, v), "bisim")
                add("bisim")
        for s1 in sccs(g1):
            for s2 in sccs(g2):
                (_, c1), (_, c2) = local_sc_hash(s1), local_sc_hash(s2)
                (_, d1), (_, d2) = local_sc_hash(s1, variant=V.BISIMULATION), local_sc_hash(s2, variant=V.BISIMULATION)
                u1, u2 = bf.unfolding_classes(s1, s2)
                sb = bf.bisimulation_classes(s1, s2)
                for u in s1:
                    for v in s2:
                        check((c1[u] == c2[v]) == (u1[u] == u2[v]), "comp")
                        add("comp")
                        check((d1[u] == d2[v]) == sb(u, v), "comp bisim")
                        add("comp_bisim")

# Ordered node hash, ordered local hash and the ordered component hashes (digraphs and multidigraphs)
for multi in (False, True):
    for g1, g2 in pairs(4 + multi, ordered=True, multi=multi):
        t1, t2 = bf.unfolding_classes(g1, g2, ordered=True)
        o1 = {u: ordered_node_hash(g1, u) for u in g1}
        o2 = {v: ordered_node_hash(g2, v) for v in g2}
        l1, l2 = ordered_local_hash(g1), ordered_local_hash(g2)
        for u in g1:
            for v in g2:
                check((o1[u] == o2[v]) == bf.ordered_rooted_isomorphic(g1, u, g2, v), "ord node")
                add("ord_node")
                check((l1[u] == l2[v]) == (t1[u] == t2[v]), "ord local")
                add("ord_local")
        for s1 in sccs(g1):
            for s2 in sccs(g2):
                gg1, n1 = ordered_sc_global_hash(s1, hash_nodes=True)
                gg2, n2 = ordered_sc_global_hash(s2, hash_nodes=True)
                check((gg1 == gg2) == bf.is_isomorphic(s1, s2, ordered=True), "ord sc global graph")
                _, m1 = ordered_sc_local_hash(s1)
                _, m2 = ordered_sc_local_hash(s2)
                u1, u2 = bf.unfolding_classes(s1, s2, ordered=True)
                for u in s1:
                    for v in s2:
                        check((n1[u] == n2[v]) == bf.ordered_rooted_isomorphic(s1, u, s2, v), "ord sc global")
                        add("ord_sc_global")
                        check((m1[u] == m2[v]) == (u1[u] == u2[v]), "ord sc local")
                        add("ord_sc_local")

# Merkle hashes: global, local and bisimulation
for g1, g2 in pairs(6):
    eq = bf.merkle_global_equivalence(g1, g2)
    a1, a2 = bf.unfolding_classes(g1, g2, annotate=True)
    ab = bf.bisimulation_classes(g1, g2, annotate=True)
    G1, G2 = merkle_hash(g1, GlobalMH())[2], merkle_hash(g2, GlobalMH())[2]
    L1, L2 = merkle_hash(g1, LocalMH(V.UNFOLDING))[2], merkle_hash(g2, LocalMH(V.UNFOLDING))[2]
    B1, B2 = merkle_hash(g1, LocalMH(V.BISIMULATION))[2], merkle_hash(g2, LocalMH(V.BISIMULATION))[2]
    for u in g1:
        for v in g2:
            check((G1[u] == G2[v]) == eq(u, v), "merkle glob")
            add("merkle_glob")
            check((L1[u] == L2[v]) == (a1[u] == a2[v]), "merkle loc")
            add("merkle_loc")
            check((B1[u] == B2[v]) == ab(u, v), "merkle bisim")
            add("merkle_bisim")

# Ordered Merkle hashes: global and local (digraphs and multidigraphs)
for multi in (False, True):
    for g1, g2 in pairs(7 + multi, ordered=True, multi=multi):
        eq = bf.merkle_global_equivalence(g1, g2, ordered=True)
        a1, a2 = bf.unfolding_classes(g1, g2, ordered=True, annotate=True)
        G1, G2 = merkle_hash(g1, OrderedGlobalMH())[2], merkle_hash(g2, OrderedGlobalMH())[2]
        L1, L2 = merkle_hash(g1, OrderedLocalMH())[2], merkle_hash(g2, OrderedLocalMH())[2]
        for u in g1:
            for v in g2:
                check((G1[u] == G2[v]) == eq(u, v), "ord merkle glob")
                add("ord_merkle_glob")
                check((L1[u] == L2[v]) == (a1[u] == a2[v]), "ord merkle loc")
                add("ord_merkle_loc")

print(json.dumps(count))
