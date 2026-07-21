import networkx as nx

from dihash import canonical_tree_hashes
from dihash.util import hash_sha256
from dihash.tree_expansion_impl import _globally_stable_colors

def build(labels, edges):
    G = nx.DiGraph()
    for n, l in labels.items():
        G.add_node(n, label=l)
    G.add_edges_from(edges)
    return G

def test1():
    # ---- 1. The counterexample is fixed: a(b) vs a(b(c)) now differ ----------
    G = build({"n": "r", "u": "a", "b1": "b", "v": "a", "w": "b", "z": "c"},
              [("n", "u"), ("n", "v"), ("u", "b1"), ("v", "w"), ("w", "z")])
    h = canonical_tree_hashes(G)
    assert h["u"] != h["v"]
    assert h["b1"] != h["w"]
    print("1. old counterexample separated: OK")

def test2():
    G = build(
        {i: "label" for i in range(8)},
        [
            (0, 1), (0, 2), (0, 3), (0, 4),
            (1, 5), (2, 6), (3, 7), (4, 7),
            (5, 0), (6, 0), (7, 0)
        ]
    )
    G_hash = canonical_tree_hashes(G)
    assert G_hash[5] == G_hash[6] == G_hash[7]
    assert G_hash[1] == G_hash[2] == G_hash[3] == G_hash[4]
    assert (G_hash[0] != G_hash[3]) and (G_hash[0] != G_hash[5])

    H = build(
        {i: "label" for i in [0, 1, 2, 3, 4, 5, 7]},
        [
            (0, 1), (0, 2), (0, 3), (0, 4),
            (1, 5), (2, 5), (3, 7), (4, 7),
            (5, 0), (7, 0)
        ])
    H_hash = canonical_tree_hashes(H)

    for n in H.nodes:
        assert G_hash[n] == H_hash[n]

    print("2. Diamond graph test passed")


def test3():
    # ---- 3. Cross-graph canonicity: same tree, different ambient graphs ------
    # G1: just a -> b.   G2: contains a -> b AND a deep chain that forces more
    # refinement rounds globally.  The a(b)-node must hash identically.
    G1 = build({"p": "a", "q": "b"}, [("p", "q")])
    G2 = build({"p2": "a", "q2": "b", "x": "a", "y": "b", "zz": "c", "t": "d"},
               [("p2", "q2"), ("x", "y"), ("y", "zz"), ("zz", "t")])
    h1 = canonical_tree_hashes(G1)
    h2 = canonical_tree_hashes(G2)
    assert h1["p"] == h2["p2"]
    assert h1["q"] == h2["q2"]
    assert h2["p2"] != h2["x"]
    print("3. cross-graph canonicity for identical trees: OK")

def test4():
    # ---- 4. Bisimilar cycles/chains collapse (same as before) ----------------
    G = build({**{"u": "a"}, **{f"c{i}": "a" for i in range(2)},
               **{f"d{i}": "a" for i in range(3)}, **{f"e{i}": "a" for i in range(3)}},
              [("u", "u"), ("c0", "c1"), ("c1", "c0"),
               ("d0", "d1"), ("d1", "d2"), ("d2", "d0"),
               ("e0", "e1"), ("e1", "e2"), ("e2", "e2")])
    h = canonical_tree_hashes(G)
    assert len(set(h.values())) == 1
    # and across graphs too: a lone self-loop elsewhere matches
    G_loop = build({"s": "a"}, [("s", "s")])
    assert canonical_tree_hashes(G_loop)["s"] == h["u"]
    print("4. bisimilar structures collapse, across graphs too: OK")

def test5():
    # ---- 5. All labels equal: order is structural, not label-sorting ---------
    # a-sink vs a-self-loop vs a-node-with-two-sink-children: all separated.
    G = build({"s": "a", "l": "a", "m": "a", "k1": "a", "k2": "a"},
              [("l", "l"), ("m", "k1"), ("m", "k2")])
    h = canonical_tree_hashes(G)
    assert len({h["s"], h["l"], h["m"]}) == 3
    assert h["k1"] == h["k2"] == h["s"]
    print("5. identical labels, structurally distinct: separated: OK")

def test6():
    # ---- 6. Multiplicities matter: a(b) vs a(b,b) ----------------------------
    G = build({"x": "a", "xb": "b", "y": "a", "yb1": "b", "yb2": "b"},
              [("x", "xb"), ("y", "yb1"), ("y", "yb2")])
    h = canonical_tree_hashes(G)
    assert h["x"] != h["y"]
    # quotient of y's side has a genuine parallel edge: y-class -> b-class x2
    print("6. edge multiplicities preserved and distinguishing: OK")

def test7():
    # ---- 7. Root marking: 2-cycle with distinct labels -----------------------
    G = build({"a": "a", "b": "b"}, [("a", "b"), ("b", "a")])
    h = canonical_tree_hashes(G)
    assert h["a"] != h["b"]        # same reachable class set, different root
    print("7. root index distinguishes nodes sharing a reachable set: OK")

def test8():
    # ---- 8. Determinism under node-insertion order ---------------------------
    G1 = build({"n": "r", "u": "a", "b1": "b", "v": "a", "w": "b", "z": "c"},
               [("n", "u"), ("n", "v"), ("u", "b1"), ("v", "w"), ("w", "z")])
    G2 = nx.DiGraph()
    for n, l in [("z", "c"), ("v", "a"), ("w", "b"), ("n", "r"), ("b1", "b"), ("u", "a")]:
        G2.add_node(n, label=l)
    G2.add_edges_from([("v", "w"), ("n", "v"), ("w", "z"), ("u", "b1"), ("n", "u")])
    h1 = canonical_tree_hashes(G1)
    h2 = canonical_tree_hashes(G2)
    assert h1 == h2
    print("8. insertion-order independent: OK")

# ---- 9. Randomized differential check against ground truth ---------------
# Ground truth for tree equality on a finite graph: colors at the globally
# stable round of the DISJOINT UNION of the graphs under comparison (sound
# within one refinement run, as proved).  Canonical hashes computed per
# graph separately must induce exactly the same equivalence.
def test9():
    import random
    random.seed(7)
    def random_graph(n_nodes, n_labels, p):
        G = nx.DiGraph()
        for i in range(n_nodes):
            G.add_node(i, label=random.choice("ab cdef"[:n_labels]))
        for i in range(n_nodes):
            for j in range(n_nodes):
                if random.random() < p:
                    G.add_edge(i, j)
        return G

    for trial in range(200):
        A = random_graph(random.randint(1, 7), random.randint(1, 3), 0.25)
        B = random_graph(random.randint(1, 7), random.randint(1, 3), 0.25)
        U = nx.union(A, B, rename=("A", "B"))
        truth = _globally_stable_colors(U, hash_sha256)
        hA, hB = canonical_tree_hashes(A), canonical_tree_hashes(B)
        joint = {**{f"A{n}": hA[n] for n in A}, **{f"B{n}": hB[n] for n in B}}
        for x in U.nodes:
            for y in U.nodes:
                same_tree = truth[x] == truth[y]
                same_hash = joint[x] == joint[y]
                assert same_tree == same_hash, (trial, x, y)
    print("9. 200 randomized cross-graph trials match ground truth: OK")


test1()
test2()
test3()
test4()
test5()
test6()
test7()
test8()
test9()
print("\nAll tests passed.")