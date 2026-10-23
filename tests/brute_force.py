"""
Independent brute-force decision procedures for the equivalences that the dihash hashes are supposed to realize
(see the paper "Directed Graph Hashing"). These are deliberately naive -- exhaustive search, greatest fixpoints and
deep truncated unfoldings -- and share no code with the library, so they can serve as ground truth on small graphs.

Graphs are NetworkX DiGraphs whose nodes carry a string 'label'. Ordered graphs additionally carry an integer 'port'
on every edge; the out-edges of a node are ordered by port.
"""
import itertools
import random

import networkx as nx


# ---------------------------------------------------------------------------------------------------------------------
# Random graph generation
# ---------------------------------------------------------------------------------------------------------------------

def random_digraph(rng, n, p, alphabet, ordered=False, loops=True):
    """Random labeled digraph with nodes 0..n-1. If ordered, every edge gets a distinct (per source) port number,
    drawn from a sparse range so that sorting by port is actually exercised."""
    g = nx.DiGraph()
    for i in range(n):
        g.add_node(i, label=rng.choice(alphabet))
    for i in range(n):
        targets = [j for j in range(n) if (loops or i != j) and rng.random() < p]
        ports = rng.sample(range(3 * n + 3), len(targets))
        for (j, port) in zip(targets, ports):
            if ordered:
                g.add_edge(i, j, port=port)
            else:
                g.add_edge(i, j)
    return g


def shuffled_copy(rng, g):
    """An isomorphic copy of g with fresh node names and randomized node/edge insertion order.
    Returns (copy, mapping from old to new node names)."""
    nodes = list(g.nodes)
    names = [f"v{i}" for i in range(len(nodes))]
    rng.shuffle(names)
    mapping = dict(zip(nodes, names))
    h = nx.DiGraph()
    order = nodes[:]
    rng.shuffle(order)
    for n in order:
        h.add_node(mapping[n], **g.nodes[n])
    edges = list(g.edges(data=True))
    rng.shuffle(edges)
    for (s, t, d) in edges:
        h.add_edge(mapping[s], mapping[t], **d)
    return (h, mapping)


def random_pair(rng, max_nodes=6, ordered=False, probabilities=(0.15, 0.3, 0.45), copy_probability=0.4):
    """A pair of random graphs; with probability copy_probability the second is a shuffled isomorphic copy."""
    alphabet = rng.choice([["a"], ["a", "b"]])
    p = rng.choice(probabilities)
    g1 = random_digraph(rng, rng.randint(1, max_nodes), p, alphabet, ordered=ordered)
    if rng.random() < copy_probability:
        g2 = shuffled_copy(rng, g1)[0]
    else:
        g2 = random_digraph(rng, rng.randint(1, max_nodes), p, alphabet, ordered=ordered)
    return (g1, g2)


# ---------------------------------------------------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------------------------------------------------

def successors(g, u, ordered):
    if ordered:
        return [v for (v, d) in sorted(g[u].items(), key=lambda item: item[1]['port'])]
    return list(g.successors(u))


def scc_map(g):
    """Maps every node to the frozenset of nodes of its strongly connected component."""
    ret = {}
    for comp in nx.strongly_connected_components(g):
        comp = frozenset(comp)
        for n in comp:
            ret[n] = comp
    return ret


def scc_height(g):
    """Height of the SCC of every node: the number of edges on a longest path from it in the condensation."""
    cond = nx.condensation(g)
    height = {}
    for c in reversed(list(nx.topological_sort(cond))):
        height[c] = max((height[d] + 1 for d in cond.successors(c)), default=0)
    return {n: height[cond.graph['mapping'][n]] for n in g.nodes}


def induced(g, nodes):
    return g.subgraph(nodes).copy()


# ---------------------------------------------------------------------------------------------------------------------
# Isomorphism (exhaustive search)
# ---------------------------------------------------------------------------------------------------------------------

def isomorphisms(g1, g2, ordered=False):
    """All label-preserving isomorphisms g1 -> g2 (as dicts). For ordered graphs, out-sequences must be preserved."""
    n1, n2 = list(g1.nodes), list(g2.nodes)
    if len(n1) != len(n2) or g1.number_of_edges() != g2.number_of_edges():
        return
    e1 = set(g1.edges)
    e2 = set(g2.edges)
    for perm in itertools.permutations(n2):
        f = dict(zip(n1, perm))
        if any(g1.nodes[u]['label'] != g2.nodes[f[u]]['label'] for u in n1):
            continue
        if {(f[s], f[t]) for (s, t) in e1} != e2:
            continue
        if ordered and any([f[v] for v in successors(g1, u, True)] != successors(g2, f[u], True) for u in n1):
            continue
        yield f


def is_isomorphic(g1, g2, ordered=False):
    return next(isomorphisms(g1, g2, ordered), None) is not None


def rooted_isomorphic(g1, u, g2, v, ordered=False):
    return any(f[u] == v for f in isomorphisms(g1, g2, ordered))


def ordered_rooted_isomorphic(g1, u, g2, v):
    """Is there an ordered isomorphism of the subgraphs reachable from u and v mapping u to v? In an ordered graph such
    an isomorphism is forced, so a simultaneous traversal decides it."""
    f, finv = {u: v}, {v: u}
    todo = [u]
    while todo:
        a = todo.pop()
        b = f[a]
        sa, sb = successors(g1, a, True), successors(g2, b, True)
        if g1.nodes[a]['label'] != g2.nodes[b]['label'] or len(sa) != len(sb):
            return False
        for (x, y) in zip(sa, sb):
            if x in f or y in finv:
                if f.get(x) != y or finv.get(y) != x:
                    return False
            else:
                f[x], finv[y] = y, x
                todo.append(x)
    return True


# ---------------------------------------------------------------------------------------------------------------------
# Unfoldings (deep truncations, interned so that equality is a cheap integer comparison)
# ---------------------------------------------------------------------------------------------------------------------

class Unfolder:
    """Assigns every truncated unfolding an integer id; equal ids <=> isomorphic truncations. One Unfolder must be
    shared by all graphs that are compared. With annotate=True every tree edge is marked internal/external according
    to the SCCs of its graph (the SCC-annotated unfolding of the paper)."""

    def __init__(self):
        self.table = {}

    def _intern(self, key):
        return self.table.setdefault(key, len(self.table))

    def ids(self, g, depth, ordered=False, annotate=False):
        sccs = scc_map(g) if annotate else None
        current = {u: self._intern(("leaf", g.nodes[u]['label'])) for u in g.nodes}
        for _ in range(depth):
            nxt = {}
            for u in g.nodes:
                kids = [((v in sccs[u]) if annotate else None, current[v]) for v in successors(g, u, ordered)]
                kids = tuple(kids) if ordered else tuple(sorted(kids, key=repr))
                nxt[u] = self._intern(("node", g.nodes[u]['label'], kids))
            current = nxt
        return current


def unfolding_classes(g1, g2, ordered=False, annotate=False):
    """Returns (ids1, ids2): equal ids <=> isomorphic (possibly annotated, possibly ordered) unfoldings. Depth
    2(n1+n2)+2 exceeds the number of refinement rounds needed on the disjoint union, so truncations decide."""
    depth = 2 * (g1.order() + g2.order()) + 2
    unf = Unfolder()
    return (unf.ids(g1, depth, ordered, annotate), unf.ids(g2, depth, ordered, annotate))


# ---------------------------------------------------------------------------------------------------------------------
# Bisimilarity (greatest fixpoint on the disjoint union)
# ---------------------------------------------------------------------------------------------------------------------

def bisimulation_classes(g1, g2, annotate=False):
    """Returns a function bisim(u, v) for u in g1, v in g2. With annotate=True, edges are labeled internal/external
    according to the SCCs of their own graph and must be matched with edges of the same kind."""
    nodes = [(1, u) for u in g1.nodes] + [(2, v) for v in g2.nodes]
    graphs = {1: g1, 2: g2}
    sccs = {1: scc_map(g1), 2: scc_map(g2)}

    def label(x):
        return graphs[x[0]].nodes[x[1]]['label']

    def succ(x):
        (i, u) = x
        return [((v in sccs[i][u]) if annotate else None, (i, v)) for v in graphs[i].successors(u)]

    rel = {(x, y) for x in nodes for y in nodes if label(x) == label(y)}
    changed = True
    while changed:
        changed = False
        for (x, y) in list(rel):
            sx, sy = succ(x), succ(y)
            forth = all(any(m == k and (x2, y2) in rel for (k, y2) in sy) for (m, x2) in sx)
            back = all(any(m == k and (x2, y2) in rel for (m, x2) in sx) for (k, y2) in sy)
            if not (forth and back):
                rel.discard((x, y))
                changed = True
    return lambda u, v: ((1, u), (2, v)) in rel


# ---------------------------------------------------------------------------------------------------------------------
# Global Merkle equivalence (Definition "Merkle equivalences" with ~ = rooted isomorphism), by direct recursion
# ---------------------------------------------------------------------------------------------------------------------

def merkle_global_equivalence(g1, g2, ordered=False):
    """Returns eq(u, v) for u in g1, v in g2 deciding the global Merkle equivalence by searching for a bijection of
    the two SCCs (exponential; small graphs only)."""
    c1, c2 = scc_map(g1), scc_map(g2)
    memo = {}

    def eq(u, v):
        if (u, v) in memo:
            return memo[(u, v)]
        memo[(u, v)] = False  # never consulted recursively: external successors have smaller height
        S, T = c1[u], c2[v]
        result = False
        if len(S) == len(T):
            s_list = sorted(S, key=repr)
            for perm in itertools.permutations(sorted(T, key=repr)):
                f = dict(zip(s_list, perm))
                if f[u] == v and _merkle_witness(g1, g2, S, T, f, eq, ordered):
                    result = True
                    break
        memo[(u, v)] = result
        return result

    return eq


def _merkle_witness(g1, g2, S, T, f, eq, ordered):
    for x in S:
        y = f[x]
        if g1.nodes[x]['label'] != g2.nodes[y]['label']:
            return False
        sx, sy = successors(g1, x, ordered), successors(g2, y, ordered)
        if ordered:
            if len(sx) != len(sy):
                return False
            for (a, b) in zip(sx, sy):
                if (a in S) != (b in T):
                    return False
                if a in S and f[a] != b:
                    return False
                if a not in S and not eq(a, b):
                    return False
        else:
            if sorted((f[a] for a in sx if a in S), key=repr) != sorted((b for b in sy if b in T), key=repr):
                return False
            ext_x = [a for a in sx if a not in S]
            ext_y = [b for b in sy if b not in T]
            if len(ext_x) != len(ext_y):
                return False
            remaining = list(ext_y)
            for a in ext_x:
                for (i, b) in enumerate(remaining):
                    if eq(a, b):
                        remaining.pop(i)
                        break
                else:
                    return False
    return True
