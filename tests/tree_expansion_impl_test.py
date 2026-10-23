import networkx as nx
from dihash import tree_expansion_hash

def build(labels, edges):
    G = nx.DiGraph()
    for n, l in labels.items():
        G.add_node(n, label=l)
    G.add_edges_from(edges)
    return G

def test1():
    # 1. Self-loop 'a', 2-cycle of 'a's, 3-cycle of 'a's, and a chain of 'a's
    #    feeding into a self-loop all have the identical infinite unary 'a' tree.
    G = build(
        {**{"u": "a"},
         **{f"c{i}": "a" for i in range(2)},
         **{f"d{i}": "a" for i in range(3)},
         **{f"e{i}": "a" for i in range(3)}},
        [("u", "u"),
         ("c0", "c1"), ("c1", "c0"),
         ("d0", "d1"), ("d1", "d2"), ("d2", "d0"),
         ("e0", "e1"), ("e1", "e2"), ("e2", "e2")],
    )
    h = tree_expansion_hash(G)
    vals = set(h.values())
    assert len(vals) == 1, f"expected all equal, got {len(vals)} distinct"
    print("1. bisimilar cycles/chains collapse to one hash: OK")

def test2():
    # 2. Distinct trees get distinct hashes; identical finite trees agree.
    G = build(
        {"a1": "a", "b1": "b", "a2": "a", "b2": "b", "a3": "a", "c3": "c"},
        [("a1", "b1"), ("a2", "b2"), ("a3", "c3")],
    )
    h = tree_expansion_hash(G)
    assert h["a1"] == h["a2"]
    assert h["b1"] == h["b2"]
    assert h["a1"] != h["a3"]
    assert h["b1"] != h["c3"]
    assert h["a1"] != h["b1"]
    print("2. finite trees: equal trees match, different trees differ: OK")

def test3():
    # 3. Multiset (not set/sequence) of children matters.
    #    x has children (b, b); y has children (b); z has children (b, b, b).
    G = build(
        {"x": "a", "xb1": "b", "xb2": "b",
         "y": "a", "yb1": "b",
         "z": "a", "zb1": "b", "zb2": "b", "zb3": "b"},
        [("x", "xb1"), ("x", "xb2"), ("y", "yb1"),
         ("z", "zb1"), ("z", "zb2"), ("z", "zb3")],
    )
    h = tree_expansion_hash(G)
    assert len({h["x"], h["y"], h["z"]}) == 3
    print("3. child multiplicities distinguish nodes: OK")

def test4():
    # 4. Sink label vs non-sink with same label differ; sinks with same label agree.
    G = build({"s1": "a", "s2": "a", "p": "a", "q": "b"}, [("p", "q")])
    h = tree_expansion_hash(G)
    assert h["s1"] == h["s2"]
    assert h["s1"] != h["p"]
    print("4. sinks vs non-sinks: OK")

def test5():
    # 5. Mixed stabilization times: a sink stabilizes in round 1 while a long
    #    chain of distinct labels stabilizes later; results must still be
    #    consistent with an identical structure elsewhere in the graph.
    labels = {"t": "z"}
    edges = []
    for i in range(6):
        labels[f"m{i}"] = "m"
        labels[f"n{i}"] = "m"
    for i in range(5):
        edges += [(f"m{i}", f"m{i+1}"), (f"n{i}", f"n{i+1}")]
    G = build(labels, edges)
    h = tree_expansion_hash(G)
    for i in range(6):
        assert h[f"m{i}"] == h[f"n{i}"]
    assert len({h[f"m{i}"] for i in range(6)}) == 6  # different depths differ
    print("5. chains of equal labels, depth-sensitive, twin-consistent: OK")

def test6():
    # 6. Non-bisimilar cycles with same labels but different branching.
    #    u: self-loop with ONE extra child vs v: self-loop with TWO extra children.
    G = build(
        {"u": "a", "ub": "b", "v": "a", "vb1": "b", "vb2": "b"},
        [("u", "u"), ("u", "ub"), ("v", "v"), ("v", "vb1"), ("v", "vb2")],
    )
    h = tree_expansion_hash(G)
    assert h["u"] != h["v"]
    print("6. cyclic nodes with different branching differ: OK")

def test7():
    # 7. Determinism across runs and node-insertion order.
    G1 = build({"a": "x", "b": "y", "c": "y"}, [("a", "b"), ("a", "c"), ("b", "c")])
    G2 = nx.DiGraph()
    for n, l in [("c", "y"), ("a", "x"), ("b", "y")]:
        G2.add_node(n, label=l)
    G2.add_edges_from([("b", "c"), ("a", "c"), ("a", "b")])
    assert tree_expansion_hash(G1) == tree_expansion_hash(G2)
    print("7. deterministic, order-independent: OK")

def test8():
    # 8. Empty graph.
    assert tree_expansion_hash(nx.DiGraph()) == {}
    print("8. empty graph: OK")

def test9():
    # 9. Bisimilar nodes inside ONE graph whose reachable subgraphs have
    #    different concrete sizes (self-loop vs 2-cycle in the same graph,
    #    each also pointing at a shared sink) — must agree.
    G = build(
        {"u": "a", "p": "a", "q": "a", "s": "b"},
        [("u", "u"), ("u", "s"), ("p", "q"), ("q", "p"), ("p", "s"), ("q", "s")],
    )
    h = tree_expansion_hash(G)
    assert h["u"] == h["p"] == h["q"]
    print("9. bisimilar nodes with different reachable-set sizes agree: OK")

def test10():
    G = build(
        {i: "label" for i in range(8)},
        [
            (0, 1), (0, 2), (0, 3), (0, 4),
            (1, 5), (2, 6), (3, 7), (4, 7),
            (5, 0), (6, 0), (7, 0)
        ]
    )
    h = tree_expansion_hash(G)
    assert h[5] == h[6] == h[7]
    assert h[1] == h[2] == h[3] == h[4]
    assert (h[0] != h[3]) and (h[0] != h[5])
    print("10. Diamond graph test passed")

test1()
test2()
test3()
test4()
test5()
test6()
test7()
test8()
test9()
test10()
print("\nAll tests passed.")