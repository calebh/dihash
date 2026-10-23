"""
Regression tests for bugs found while verifying the library against the paper, plus the worked examples and
counterexamples from the paper "Directed Graph Hashing".
"""
import functools
import hashlib

import networkx as nx
import pytest

import dihash
from dihash.util import encode
from dihash.local_hash import LocalHashVariant, local_hash, local_sc_hash
from dihash.merkle_hash import merkle_hash, MerkleHashVariant, GlobalMH, LocalMH, OrderedGlobalMH, OrderedLocalMH
from dihash.ordered_hash import _dfs, _port_successors, ordered_node_hash, ordered_sc_global_hash

UNF = LocalHashVariant.UNFOLDING
BISIM = LocalHashVariant.BISIMULATION


def build(labels, edges):
    """labels: dict node -> label. edges: (s, t) pairs, or (s, t, port) triples for ordered graphs."""
    g = nx.DiGraph()
    for (n, l) in labels.items():
        g.add_node(n, label=l)
    for e in edges:
        if len(e) == 3:
            g.add_edge(e[0], e[1], port=e[2])
        else:
            g.add_edge(e[0], e[1])
    return g


def same_labels(nodes, label="a"):
    return {n: label for n in nodes}


def merkle(g, variant):
    return merkle_hash(g, variant)[2]


# ---------------------------------------------------------------------------------------------------------------------
# Bugs found during verification
# ---------------------------------------------------------------------------------------------------------------------

def test_merkle_variants_can_be_constructed():
    """GlobalMH() and OrderedGlobalMH() used to raise in MerkleHashVariant.__init__, so the global Merkle variants
    could not be used at all."""
    g = build(same_labels(range(3)), [(0, 1), (1, 2), (2, 0)])
    for variant in [GlobalMH(), OrderedGlobalMH(), LocalMH(UNF), LocalMH(BISIM)]:
        assert isinstance(variant, MerkleHashVariant)
    assert len(set(merkle(g, GlobalMH()).values())) == 1
    with pytest.raises(ValueError):
        MerkleHashVariant()
    with pytest.raises(NotImplementedError):
        merkle_hash(g, OrderedLocalMH())


def test_bisimulation_variant_on_graphs_with_edges():
    """The bisimulation quotient is a DiGraph, whose edges are pairs; unpacking them as (s, t, key) triples crashed on
    every graph with at least one edge."""
    cycle = build(same_labels(range(3)), [(0, 1), (1, 2), (2, 0)])
    loop = build(same_labels(["s"]), [("s", "s")])
    h_cycle = local_hash(cycle, variant=BISIM)
    assert len(set(h_cycle.values())) == 1
    assert local_hash(loop, variant=BISIM)["s"] == h_cycle[0]
    (sc_hash, sc_nodes) = local_sc_hash(cycle, variant=BISIM)
    assert sc_hash == local_sc_hash(loop, variant=BISIM)[0]
    assert len(set(sc_nodes.values())) == 1

    # Duplicated bisimilar successors are ignored by bisimulation but not by unfolding isomorphism
    g = build({"x": "a", "x1": "b", "y": "a", "y1": "b", "y2": "b"}, [("x", "x1"), ("y", "y1"), ("y", "y2")])
    assert local_hash(g, variant=BISIM)["x"] == local_hash(g, variant=BISIM)["y"]
    assert local_hash(g, variant=UNF)["x"] != local_hash(g, variant=UNF)["y"]


def test_dfs_is_a_depth_first_preorder():
    """_dfs used to iterate the bottom of its stack and never mark nodes as discovered, so it visited only the root's
    direct successors (and ordered hashing raised KeyError on any graph of depth >= 2)."""
    g = build(same_labels("rabc"), [("r", "a", 0), ("r", "b", 1), ("a", "c", 0), ("c", "r", 0), ("b", "c", 0)])
    assert list(_dfs("r", functools.partial(_port_successors, g))) == ["r", "a", "c", "b"]
    # port numbers, not insertion order, decide the order of exploration
    h = build(same_labels("rab"), [("r", "a", 7), ("r", "b", 2)])
    assert list(_dfs("r", functools.partial(_port_successors, h))) == ["r", "b", "a"]
    # every reachable node exactly once
    diamond = build(same_labels("rpqs"), [("r", "p", 0), ("r", "q", 1), ("p", "s", 0), ("q", "s", 0)])
    assert list(_dfs("r", functools.partial(_port_successors, diamond))) == ["r", "p", "s", "q"]


def test_ordered_hash_of_deep_graphs():
    path5 = build(same_labels(range(5)), [(i, i + 1, 0) for i in range(4)])
    path4 = build(same_labels(range(4)), [(i, i + 1, 0) for i in range(3)])
    assert ordered_node_hash(path5, 0) != ordered_node_hash(path4, 0)
    assert ordered_node_hash(path5, 1) == ordered_node_hash(path4, 0)
    cycle = build(same_labels(range(3)), [(0, 1, 0), (1, 2, 0), (2, 0, 0)])
    (g_hash, node_hashes) = ordered_sc_global_hash(cycle, hash_nodes=True)
    assert len(set(node_hashes.values())) == 1


def test_ordered_input_validation():
    """Duplicate ports would make the DFS order depend on insertion order; the strongly connected canonization is only
    meaningful (orbits!) on strongly connected graphs."""
    dup = build(same_labels("rab"), [("r", "a", 0), ("r", "b", 0)])
    with pytest.raises(ValueError):
        ordered_node_hash(dup, "r")
    path = build(same_labels("ab"), [("a", "b", 0)])
    with pytest.raises(AssertionError):
        ordered_sc_global_hash(path)


@pytest.mark.parametrize("make_variant", [GlobalMH, lambda: LocalMH(UNF), lambda: LocalMH(BISIM)],
                         ids=["global", "local-unfolding", "local-bisimulation"])
def test_merkle_long_chain_of_sccs(make_variant):
    """The recursive traversal of the condensation exceeded Python's recursion limit for chains of ~1000 SCCs."""
    n = 3000
    chain = build(same_labels(range(n)), [(i, i + 1) for i in range(n - 1)])
    hashes = merkle(chain, make_variant())
    assert len(hashes) == n and len(set(hashes.values())) == n


def test_custom_string_hash_function_is_used_everywhere(monkeypatch):
    """No code path may silently fall back to the default SHA-256 when another string hash is requested."""
    md5 = lambda s: hashlib.md5(s.encode('utf-8')).hexdigest()

    def forbidden(*args, **kwargs):
        raise AssertionError("hashlib.sha256 called although string_hash_fun was given")

    g = build({0: "a", 1: "b", 2: "a", 3: "c"}, [(0, 1), (1, 0), (1, 2), (2, 3), (3, 3)])
    o = build({0: "a", 1: "b", 2: "a"}, [(0, 1, 0), (1, 0, 0), (1, 2, 1), (2, 0, 0)])
    monkeypatch.setattr(hashlib, "sha256", forbidden)
    outputs = [dihash.global_hash(g, string_hash_fun=md5)]
    outputs += list(dihash.global_hash(g, hash_nodes=True, string_hash_fun=md5)[1].values())
    for variant in (UNF, BISIM):
        outputs += list(local_hash(g, variant=variant, string_hash_fun=md5).values())
        outputs += list(local_sc_hash(o, variant=variant, string_hash_fun=md5)[1].values())
    outputs += [ordered_node_hash(o, 0, string_hash_fun=md5)]
    outputs += list(ordered_sc_global_hash(o, hash_nodes=True, string_hash_fun=md5)[1].values())
    for (graph, variant) in [(g, GlobalMH()), (g, LocalMH(UNF)), (g, LocalMH(BISIM)), (o, OrderedGlobalMH())]:
        outputs += list(merkle_hash(graph, variant, string_hash_fun=md5)[2].values())
    assert all(len(h) == 32 for h in outputs)


def test_encoding_is_injective_on_tricky_strings():
    values = ["a,b", ["a", "b"], ["a,b"], 'a"', 'a\\"', 'a\\', ["a\\", '"'], ['a\\"'], "", [""], [], (), ("",),
              [[]], ([],), 1, "1", [1], ["1"], -1, "[1]", "(1)", ("a", ["b", "c"]), ("a", ["b"], "c")]
    encodings = [encode(v) for v in values]
    assert len(set(encodings)) == len(values)


# ---------------------------------------------------------------------------------------------------------------------
# Examples from the paper
# ---------------------------------------------------------------------------------------------------------------------

def test_figure_orbits():
    """Figure 1: three labels, five orbits; equal labels do not imply equal orbits."""
    labels = {"t": "x", "l": "x", "r": "x", "bo": "x", "ct": "z", "cb": "z", "dl": "y", "dr": "y", "el": "z", "er": "z"}
    edges = [("t", "l"), ("l", "t"), ("t", "r"), ("r", "t"), ("l", "bo"), ("bo", "l"), ("r", "bo"), ("bo", "r"),
             ("t", "ct"), ("bo", "cb"), ("l", "dl"), ("dl", "el"), ("r", "dr"), ("dr", "er")]
    (_, h) = dihash.global_hash(build(labels, edges), hash_nodes=True)
    classes = {}
    for (n, x) in h.items():
        classes.setdefault(x, set()).add(n)
    assert sorted(map(sorted, classes.values())) == sorted(map(sorted, [{"t", "bo"}, {"l", "r"}, {"ct", "cb"},
                                                                         {"dl", "dr"}, {"el", "er"}]))


def test_ordered_edge_order_must_be_serialized():
    """Example: sorting the relabeled adjacency list loses the port order. These graphs are not ordered-isomorphic."""
    g1 = build({"r": "r", "x": "x", "y": "y"}, [("r", "x", 0), ("r", "y", 1), ("x", "y", 0), ("x", "r", 1)])
    g2 = build({"r": "r", "x": "x", "y": "y"}, [("r", "x", 0), ("r", "y", 1), ("x", "r", 0), ("x", "y", 1)])
    assert ordered_node_hash(g1, "r") != ordered_node_hash(g2, "r")


def test_bisimulation_example():
    """Example: a1 and a2 are bisimilar but have different unfoldings; the naive variant (multiset refinement, then
    collapse) leaves a color tie. The corrected variant hashes u like the node u of the graph where a1, a2 are merged."""
    labels = {"u": "U", "a1": "A", "a2": "A", "b": "B", "x": "X", "x2": "X"}
    g = build(labels, [("u", "a1"), ("u", "b"), ("b", "a2"), ("a1", "x"), ("a2", "x"), ("a2", "x2")])
    merged = build({"u": "U", "a": "A", "b": "B", "x": "X"}, [("u", "a"), ("u", "b"), ("b", "a"), ("a", "x")])
    hb = local_hash(g, variant=BISIM)
    assert hb["a1"] == hb["a2"]
    assert hb["u"] == local_hash(merged, variant=BISIM)["u"]
    hu = local_hash(g, variant=UNF)
    assert hu["a1"] != hu["a2"]


def test_merkle_examples():
    """Examples separating rooted isomorphism, global Merkle, local Merkle and unfolding equivalence."""
    loop = build({"u": "a"}, [("u", "u")])
    two_cycle = build({"p": "a", "q": "a"}, [("p", "q"), ("q", "p")])
    lead_in = build({"v": "a", "w": "a"}, [("v", "w"), ("w", "w")])

    # self-loop vs 2-cycle: same unfolding and same local Merkle hash, different global Merkle hash
    assert local_hash(loop)["u"] == local_hash(two_cycle)["p"]
    assert merkle(loop, LocalMH(UNF))["u"] == merkle(two_cycle, LocalMH(UNF))["p"]
    assert merkle(loop, GlobalMH())["u"] != merkle(two_cycle, GlobalMH())["p"]

    # self-loop vs a node leading into a self-loop: same unfolding, different local Merkle hash
    assert local_hash(loop)["u"] == local_hash(lead_in)["v"]
    assert merkle(loop, LocalMH(UNF))["u"] != merkle(lead_in, LocalMH(UNF))["v"]

    # shared sink vs two copies of the sink: different reachable subgraphs, same global Merkle hash
    shared = build(same_labels("xpqs"), [("x", "p"), ("x", "q"), ("p", "s"), ("q", "s")])
    copies = build(same_labels(["x", "p", "q", "s1", "s2"]), [("x", "p"), ("x", "q"), ("p", "s1"), ("q", "s2")])
    assert merkle(shared, GlobalMH())["x"] == merkle(copies, GlobalMH())["x"]
    assert dihash.global_hash(shared) != dihash.global_hash(copies)

    # ordered: s(a) = (a, b), s(b) = (a, b) -- every node has the same ordered unfolding, but exchanging a and b maps
    # s(a) to (b, a) != s(b), so a and b lie in different orbits and the global variant separates them
    o = build(same_labels("ab"), [("a", "a", 0), ("a", "b", 1), ("b", "a", 0), ("b", "b", 1)])
    h = merkle(o, OrderedGlobalMH())
    assert h["a"] != h["b"]
    assert ordered_node_hash(o, "a") != ordered_node_hash(o, "b")
    # whereas s(a) = (b, a), s(b) = (a, b) has the automorphism exchanging a and b
    sym = build(same_labels("ab"), [("a", "b", 0), ("a", "a", 1), ("b", "a", 0), ("b", "b", 1)])
    h = merkle(sym, OrderedGlobalMH())
    assert h["a"] == h["b"]
