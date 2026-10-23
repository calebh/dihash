[![Latest Release](https://img.shields.io/pypi/v/dihash.svg)](https://pypi.python.org/pypi/dihash/)
[![PyPI Statistics](https://img.shields.io/pypi/dm/dihash.svg)](https://pypistats.org/packages/dihash)

# dihash
Python implementation of directed graph hashing, from the paper "Directed Graph Hashing"

dihash hashes node-labeled directed graphs, and the individual nodes within them. Every hash function comes with an exact guarantee: two nodes receive the same hash if and only if they are equivalent in a precise sense (up to collisions of the underlying string hash such as SHA-256). The library offers several notions of equivalence:

| Function | Two nodes receive the same hash if and only if | Running time |
| --- | --- | --- |
| `global_hash` | some isomorphism of their graphs maps one node onto the other. Within one graph: the nodes are in the same automorphism orbit | Exponential in the worst case (uses nauty), fast in practice |
| `local_hash` (unfolding) | the (possibly infinite) trees obtained by unfolding the graph from the two nodes are isomorphic | Polynomial |
| `local_hash` (bisimulation) | the two nodes are bisimilar | Polynomial |
| `ordered_node_hash` | the subgraphs reachable from the two nodes are isomorphic, respecting the order of the outgoing edges | Linear |
| `ordered_local_hash` | the trees obtained by unfolding the graph from the two nodes are isomorphic, respecting the order of the outgoing edges | O(m log² n), using DFA minimization |
| `merkle_hash` | the nodes are equivalent component by component, see [Merkle Graph Hashing](#merkle-graph-hashing) | Depends on the variant |

The global hash looks at the whole graph. The local hashes only look at what can be observed by following edges forward from a node. The Merkle hashes recurse over the strongly connected components of the graph, like a Merkle tree, which is useful for graphs that are built up over time.

# Now on PyPi

This project is now on PyPi and can be directly installed with pip. If you have problems with the pynauty dependency, see the "Dependencies" section below.

```
pip install dihash
```

# Version 2.0
dihash has been updated to 2.0, which is a rewrite of 1.0 with bugfixes and cleaner code. An updated version of the paper is now available on arXiv at https://arxiv.org/abs/2002.06653. Unit tests have been added, as well as a benchmarking script. The hashes of 2.0 are not backward compatible with 1.0 due to a re-write of the string encoding function.

# Version 2.1
A critical bug has been fixed with the color ordering passed to pynauty. Previously I had assumed that the order of the node colors passed to pynauty did not matter, however testing revealed this not to be the case. The issue was resolved by sorting the coloring by label lexiographical order before passing to pynauty.

# Version 3.0
dihash 3.0 follows the new version of the paper (source in `papers/soda`) and reorganizes the library around the notions of equivalence above:
- `hash_graph` has been renamed to `global_hash`. It now returns only the graph hash unless `hash_nodes=True` is passed.
- New `local_hash` and `local_sc_hash` functions hash nodes by their unfoldings or up to bisimulation, in polynomial time.
- New functions for graphs whose outgoing edges are ordered (`ordered_node_hash`, `ordered_sc_global_hash`, `ordered_local_hash` and `ordered_sc_local_hash`). Ordered graphs may be MultiDiGraphs, so that a node can link to the same target more than once.
- `merkle_hash_graph` has been replaced by `merkle_hash`, which takes a variant argument selecting how each strongly connected component is hashed.
- The `apply_quotient` option, `hash_graph_node_set`, and the edge-label and multigraph encoding functions have been removed. Graph-level labels (`g.graph['label']`) are no longer used.
- Every hash is now tested against independent brute-force decision procedures for its equivalence (see "Running the Tests").

Graph hashes computed by `global_hash` are the same as those of `hash_graph` in 2.1 (for graphs without a graph-level label). Node hashes can differ from 2.1, because a node's hash now uses the smallest canonical index in its orbit, as in the paper, instead of the rank of its orbit among all orbits. Merkle hashes are not backward compatible.

# Dependencies
- Python 3.7 or newer
- NetworkX: https://networkx.org/
- pynauty: The main repository now supports computing orbits, which means using a forked version is no longer necessary. See https://github.com/pdobsan/pynauty for more details. Note that when we installed pynauty with pip3, we had to run `pip install --no-binary pynauty pynauty` since the default binary gave segmentation faults. pynauty does not seem to have Windows support, which means that Linux/Unix is a requirement for this library as well.

On Debian and Ubuntu, building pynauty from source with the system Python can fail with `AttributeError: install_layout`. This comes from the system's patched setuptools, and is fixed by installing into a virtual environment with an up-to-date setuptools:

```
python3 -m venv venv
. venv/bin/activate
pip install --upgrade pip setuptools wheel
pip install --no-binary pynauty pynauty
pip install dihash
```

# How to Use
All functions take NetworkX digraphs. Each node should have a 'label' entry in its node attribute dictionary, and the value of this entry should be a string which determines the label of that node. Hashes are returned as hex digest strings.

The functions are found in the following modules:

```
import dihash                                  # global_hash, local_hash, local_sc_hash, merkle_hash
from dihash.local_hash import LocalHashVariant
from dihash.merkle_hash import GlobalMH, LocalMH, OrderedGlobalMH, OrderedLocalMH
from dihash.ordered_hash import ordered_node_hash, ordered_sc_global_hash, ordered_local_hash, ordered_sc_local_hash
```

## Global Graph Hashing
The global graph hashing algorithm has the following definition:

```
g_hash = dihash.global_hash(g, hash_nodes=False, string_hash_fun=hash_sha256)
(g_hash, node_hashes) = dihash.global_hash(g, hash_nodes=True, string_hash_fun=hash_sha256)
```

`global_hash` has the following inputs:
- g: A NetworkX digraph. Each node should have a 'label' entry in its node attribute dictionary. The value of this entry should be a string which determines the label of that node.
- hash_nodes: A boolean value. If true, global_hash also returns a dictionary giving the hashes of all nodes in the graph.
- string_hash_fun: A function which maps strings to a string. The default value, hash_sha256 hashes by using hashlib.sha256 and converting to the result to a hex digest.

`global_hash` has the following outputs:
- g_hash: A hex digest of the hash of the entire graph. Two graphs have the same hash if and only if they are isomorphic (with an isomorphism that preserves the node labels).
- node_hashes: Only returned if hash_nodes is True. A dictionary mapping nodes to their hash hex digests. Two nodes have the same hash if and only if some isomorphism of their graphs maps one onto the other. In particular, the nodes of a single graph have the same hash if and only if they lie in the same automorphism orbit.

The graph is canonized with nauty, so `global_hash` may take exponential time in the worst case.

Example:

```
import networkx as nx
import dihash

g = nx.DiGraph()
g.add_node(0, label='a')
g.add_node(1, label='a')
g.add_node(2, label='a')
g.add_edge(0, 1)
g.add_edge(1, 2)
g.add_edge(2, 0)

(g_hash, node_hashes) = dihash.global_hash(g, hash_nodes=True)

print(g_hash)
print(node_hashes)
```

The following output is printed:

```
b37deb748c68bd738fdb647aa638ad8654c690d8ce14507fd21f1f299faf7ed5
{0: 'ad6321ae4eb544ab1f00db6436938427e01176cc3b4fed44ef0c6a0a88a0a7c3', 1: 'ad6321ae4eb544ab1f00db6436938427e01176cc3b4fed44ef0c6a0a88a0a7c3', 2: 'ad6321ae4eb544ab1f00db6436938427e01176cc3b4fed44ef0c6a0a88a0a7c3'}
```

## Local Graph Hashing
The local graph hashing algorithm has the following definition:

```
node_hashes = dihash.local_hash(g, variant=LocalHashVariant.UNFOLDING, string_hash_fun=hash_sha256)
```

`local_hash` has the following inputs:
- g: A NetworkX digraph. Each node should have a 'label' entry in its node attribute dictionary. The value of this entry should be a string which determines the label of that node.
- variant: Either `LocalHashVariant.UNFOLDING` or `LocalHashVariant.BISIMULATION`.
  - With `LocalHashVariant.UNFOLDING`, two nodes have the same hash if and only if their unfoldings are isomorphic. The unfolding of a node is the (possibly infinite) tree obtained by starting at the node and repeatedly adding the successors of each node as its children.
  - With `LocalHashVariant.BISIMULATION`, two nodes have the same hash if and only if they are bisimilar. Bisimulation is like unfolding equivalence, except that it ignores how many times equivalent children are repeated.
- string_hash_fun: A function which maps strings to a string. The default value, hash_sha256 hashes by using hashlib.sha256 and converting to the result to a hex digest.

`local_hash` has the following output:
- node_hashes: A dictionary mapping nodes to their hash hex digests.

Because the hash of a node only depends on what is reachable from it, nodes in different graphs can be compared directly. Unlike `global_hash`, `local_hash` runs in polynomial time.

Example:

```
import networkx as nx
import dihash
from dihash.local_hash import LocalHashVariant

# A single node with a self-loop
g1 = nx.DiGraph()
g1.add_node('u', label='a')
g1.add_edge('u', 'u')

# Two nodes in a 2-cycle, with the same label
g2 = nx.DiGraph()
g2.add_node('p', label='a')
g2.add_node('q', label='a')
g2.add_edge('p', 'q')
g2.add_edge('q', 'p')

# A node with one child, and a node with two children (all children labeled 'b')
g3 = nx.DiGraph()
g3.add_node('x', label='a')
g3.add_node('x1', label='b')
g3.add_node('y', label='a')
g3.add_node('y1', label='b')
g3.add_node('y2', label='b')
g3.add_edge('x', 'x1')
g3.add_edge('y', 'y1')
g3.add_edge('y', 'y2')

h1 = dihash.local_hash(g1)
h2 = dihash.local_hash(g2)
h3 = dihash.local_hash(g3)
print(h1['u'] == h2['p'] == h2['q'])  # Both unfold to an infinite path of 'a' nodes
print(h3['x'] == h3['y'])             # The unfoldings have different numbers of children

b3 = dihash.local_hash(g3, variant=LocalHashVariant.BISIMULATION)
print(b3['x'] == b3['y'])             # x and y are bisimilar
```

The following output is printed:

```
True
False
True
```

For strongly connected graphs there is a faster function that also returns a hash for the whole graph:

```
(sc_hash, sc_node_hashes) = dihash.local_sc_hash(sc_graph, variant=LocalHashVariant.UNFOLDING, string_hash_fun=hash_sha256)
```

The input `sc_graph` must be strongly connected, otherwise an AssertionError is raised. The node hashes satisfy the same guarantee as those of `local_hash`, but they are computed with a different encoding, so the two functions return different hash values for the same node. `sc_hash` is the hash of the graph obtained by merging all nodes with equal hashes.

## Ordered Outgoing Edges
In many applications the outgoing edges of a node are ordered, for example the links of a web page. dihash supports this by reading a 'port' entry from each edge's attribute dictionary. The outgoing edges of a node are ordered by their port values, which must be distinct for each node. To let a node link to the same target more than once (with different ports), use a NetworkX MultiDiGraph.

The ordered node hashing algorithm has the following definition:

```
node_hash = ordered_node_hash(g, node, string_hash_fun=hash_sha256)
```

`ordered_node_hash` has the following inputs:
- g: A NetworkX DiGraph or MultiDiGraph. Each node should have a 'label' entry in its node attribute dictionary, and each edge should have a 'port' entry in its edge attribute dictionary. A ValueError is raised if two outgoing edges of a node have the same port.
- node: The node to hash.
- string_hash_fun: A function which maps strings to a string. The default value, hash_sha256 hashes by using hashlib.sha256 and converting to the result to a hex digest.

`ordered_node_hash` has the following output:
- node_hash: A hex digest of the hash of the node. Two nodes have the same hash if and only if there is an isomorphism between the subgraphs reachable from them that maps one node onto the other and preserves labels and the order of the outgoing edges.

The hash is computed by a depth-first search from the node, so it runs in linear time in the size of the reachable subgraph.

For strongly connected graphs with ordered edges, a global hash and the automorphism orbits can be computed in polynomial time:

```
g_hash = ordered_sc_global_hash(g, hash_nodes=False, string_hash_fun=hash_sha256)
(g_hash, node_hashes) = ordered_sc_global_hash(g, hash_nodes=True, string_hash_fun=hash_sha256)
```

The input `g` must be strongly connected, otherwise an AssertionError is raised. Two strongly connected graphs have the same `g_hash` if and only if they are isomorphic (preserving labels and edge order), and two nodes have the same hash if and only if some such isomorphism maps one onto the other. This runs in O(n(n+m)) time for a graph with n nodes and m edges.

Example:

```
import networkx as nx
from dihash.ordered_hash import ordered_node_hash, ordered_sc_global_hash

# The same links, in two different orders
g1 = nx.DiGraph()
g2 = nx.DiGraph()
for g in (g1, g2):
    g.add_node('r', label='root')
    g.add_node('x', label='page')
    g.add_node('y', label='page')
g1.add_edge('r', 'x', port=0)
g1.add_edge('r', 'y', port=1)
g1.add_edge('x', 'y', port=0)
g1.add_edge('x', 'r', port=1)
g2.add_edge('r', 'x', port=0)
g2.add_edge('r', 'y', port=1)
g2.add_edge('x', 'r', port=0)
g2.add_edge('x', 'y', port=1)

print(ordered_node_hash(g1, 'r') == ordered_node_hash(g2, 'r'))

# A strongly connected ordered graph: every node links to 'a' first, then to 'b'
c = nx.DiGraph()
c.add_node('a', label='page')
c.add_node('b', label='page')
c.add_edge('a', 'a', port=0)
c.add_edge('a', 'b', port=1)
c.add_edge('b', 'a', port=0)
c.add_edge('b', 'b', port=1)
(c_hash, node_hashes) = ordered_sc_global_hash(c, hash_nodes=True)
print(node_hashes['a'] == node_hashes['b'])  # No ordered automorphism exchanges a and b
```

The following output is printed:

```
False
False
```

The ordered local hashing algorithm has the following definition:

```
node_hashes = ordered_local_hash(g, string_hash_fun=hash_sha256)
```

`ordered_local_hash` has the following inputs:
- g: A NetworkX DiGraph or MultiDiGraph. Each node should have a 'label' entry in its node attribute dictionary, and each edge should have a 'port' entry in its edge attribute dictionary. A ValueError is raised if two outgoing edges of a node have the same port.
- string_hash_fun: A function which maps strings to a string. The default value, hash_sha256 hashes by using hashlib.sha256 and converting to the result to a hex digest.

`ordered_local_hash` has the following output:
- node_hashes: A dictionary mapping nodes to their hash hex digests. Two nodes (in the same graph or in different graphs) have the same hash if and only if their ordered unfoldings are isomorphic. The ordered unfolding of a node is the (possibly infinite) tree obtained by unfolding the graph from the node, with the children of every tree node ordered by port. In other words, two nodes have the same hash if and only if they cannot be told apart by following outgoing edges by their position.

The graph is treated as a deterministic automaton, in which following the k-th outgoing edge of a node is a transition, and is minimized with Hopcroft's algorithm. The running time is therefore O(m log² n) for a graph with n nodes and m edges, no matter how deep the graph is.

For strongly connected graphs there is also a function that returns a hash for the whole graph:

```
(g_hash, node_hashes) = ordered_sc_local_hash(g, string_hash_fun=hash_sha256)
```

The input `g` must be strongly connected, otherwise an AssertionError is raised. The node hashes satisfy the same guarantee as those of `ordered_local_hash`, but they are computed with a different encoding, so the two functions return different hash values for the same node. `g_hash` is the hash of the graph obtained by merging all nodes with equal hashes. Two strongly connected graphs therefore have the same `g_hash` if and only if some node of one graph has the same ordered unfolding as some node of the other.

Example:

```
import networkx as nx
from dihash.ordered_hash import ordered_local_hash, ordered_sc_local_hash

# Every node links to 'a' first, then to 'b'
c = nx.DiGraph()
c.add_node('a', label='page')
c.add_node('b', label='page')
c.add_edge('a', 'a', port=0)
c.add_edge('a', 'b', port=1)
c.add_edge('b', 'a', port=0)
c.add_edge('b', 'b', port=1)
node_hashes = ordered_local_hash(c)
print(node_hashes['a'] == node_hashes['b'])  # a and b cannot be told apart by following links

# A single page that links to itself twice. A MultiDiGraph allows repeated links.
d = nx.MultiDiGraph()
d.add_node('p', label='page')
d.add_edge('p', 'p', port=0)
d.add_edge('p', 'p', port=1)
print(ordered_sc_local_hash(c)[0] == ordered_sc_local_hash(d)[0])  # Merging a and b gives d
```

The following output is printed:

```
True
True
```

## Merkle Graph Hashing
The Merkle graph hashing algorithm processes the strongly connected components (SCCs) of the graph in reverse topological order. Each node is relabeled with its own label together with the hashes of its successors outside its SCC, and then the relabeled SCC is hashed on its own. Like a Merkle tree, the hash of a node depends only on the nodes reachable from it. This makes Merkle hashing useful for graphs that are built up over time.

The Merkle graph hashing algorithm has the following definition:

```
(scc_hashes, cond, node_hashes) = dihash.merkle_hash(g, variant, nodes_to_hash=None, precomputed_hashes=None, string_hash_fun=hash_sha256)
```

`merkle_hash` has the following inputs:
- g: A NetworkX digraph. Each node should have a 'label' entry in its node attribute dictionary. The value of this entry should be a string which determines the label of that node. For the ordered variants, each edge should have a 'port' entry, and g may be a MultiDiGraph.
- variant: Determines how each SCC is hashed. It should be one of the following:
  - `GlobalMH()`: Each SCC is hashed with `global_hash`. Two nodes have the same hash if and only if there is an isomorphism between their SCCs that maps one node onto the other, preserves labels, and matches the successors outside the SCC with successors that have equal hashes. This variant may take exponential time in the worst case.
  - `LocalMH(LocalHashVariant.UNFOLDING)`: Each SCC is hashed with `local_sc_hash`. Two nodes have the same hash if and only if their unfoldings are isomorphic, when every edge is marked by whether it stays inside its SCC or leaves it. This variant runs in polynomial time.
  - `LocalMH(LocalHashVariant.BISIMULATION)`: As above, but up to bisimulation instead of unfolding isomorphism.
  - `OrderedGlobalMH()`: For graphs with ordered edges (see "Ordered Outgoing Edges"). Each SCC is hashed with `ordered_sc_global_hash`, and the positions of the links that leave the SCC are recorded. This variant runs in polynomial time.
  - `OrderedLocalMH()`: For graphs with ordered edges. Each SCC is hashed with `ordered_sc_local_hash`, and the positions of the links that leave the SCC are recorded. Two nodes have the same hash if and only if their ordered unfoldings are isomorphic, when every edge is marked by whether it stays inside its SCC or leaves it. This variant runs in O(m log² n) time, and is much faster than `OrderedGlobalMH` on large SCCs.
- nodes_to_hash: A list of nodes to hash in the graph. If nodes_to_hash is None, all nodes in the input graph will be hashed.
- precomputed_hashes: A dictionary mapping nodes to their hashes (should be encoded as a string hexdigest). This parameter is useful if you are hashing graphs built up over time. If a node has a hash set in the dictionary, that node's precomputed hash will be used instead of recursively hashing the graph. The precomputed hashes must have been computed with the same variant and string_hash_fun.
- string_hash_fun: A function which maps strings to a string. The default value, hash_sha256 hashes by using hashlib.sha256 and converting to the result to a hex digest.

`merkle_hash` has the following outputs:
- scc_hashes: A dictionary mapping strongly connected component integer IDs to string hex digests. The integers represent specific strongly connected components in the input graph. To retrieve the SCC integer ID for some node n, use `cond.graph['mapping'][n]`.
- cond: The condensation digraph of the input graph, computed using [`nx.algorithms.components.condensation`](https://networkx.org/documentation/stable/reference/algorithms/generated/networkx.algorithms.components.condensation.html).
- node_hashes: A dictionary mapping nodes to hashes. This dictionary includes the hashes of all nodes that were involved in the computation of `merkle_hash`.

Like Merkle trees, the Merkle hashes do not distinguish between a subgraph that is shared and two separate copies of it: if two nodes point to the same node `s`, they get the same hashes as if they each pointed to their own copy of `s`.

Example:

```
import networkx as nx
import dihash
from dihash.merkle_hash import GlobalMH

g = nx.DiGraph()
for n in range(7):
    g.add_node(n, label='a')

g.add_edge(0, 1)
g.add_edge(0, 2)

g.add_edge(1, 5)
g.add_edge(4, 6)

g.add_edge(1, 2)
g.add_edge(2, 1)
g.add_edge(2, 3)
g.add_edge(3, 2)
g.add_edge(3, 4)
g.add_edge(4, 3)

(scc_hashes, cond, node_hashes) = dihash.merkle_hash(g, GlobalMH())

print(node_hashes[1])
print(node_hashes[2])
print(node_hashes[3])
print(node_hashes[4])
print(scc_hashes[cond.graph['mapping'][1]]) # Print the hash for the SCC containing node 1
```

The following output is printed:

```
0794c37c25dd026eab1c46c607a7a44f1faaf32f8d0f7dfdaf7728a25707a9dc
bfc739cd7c6a58b48424e223aac326ef10dec739405c1b53f4f7d43a155f3184
bfc739cd7c6a58b48424e223aac326ef10dec739405c1b53f4f7d43a155f3184
0794c37c25dd026eab1c46c607a7a44f1faaf32f8d0f7dfdaf7728a25707a9dc
85b266c448a1a204f192fe227db6b2e220435ec240cc6dfea844594af8534d5d
```

The global and local variants differ inside cycles. A node with a self-loop and a node in a 2-cycle have different SCCs, so the global variant distinguishes them, but their unfoldings are identical, so the local variant does not:

```
import networkx as nx
import dihash
from dihash.local_hash import LocalHashVariant
from dihash.merkle_hash import GlobalMH, LocalMH

loop = nx.DiGraph()
loop.add_node('u', label='a')
loop.add_edge('u', 'u')

two_cycle = nx.DiGraph()
two_cycle.add_node('p', label='a')
two_cycle.add_node('q', label='a')
two_cycle.add_edge('p', 'q')
two_cycle.add_edge('q', 'p')

glob_loop = dihash.merkle_hash(loop, GlobalMH())[2]
glob_cycle = dihash.merkle_hash(two_cycle, GlobalMH())[2]
loc_loop = dihash.merkle_hash(loop, LocalMH(LocalHashVariant.UNFOLDING))[2]
loc_cycle = dihash.merkle_hash(two_cycle, LocalMH(LocalHashVariant.UNFOLDING))[2]

print(glob_loop['u'] == glob_cycle['p'])  # The SCCs have different sizes
print(loc_loop['u'] == loc_cycle['p'])    # The unfoldings inside the SCCs are isomorphic
```

The following output is printed:

```
False
True
```

When a graph grows over time, previously computed hashes can be reused. Adding a node whose edges point only to existing nodes does not change the hashes of the existing nodes:

```
import networkx as nx
import dihash
from dihash.merkle_hash import GlobalMH

g = nx.DiGraph()
g.add_node('a', label='a')
g.add_node('b', label='b')
g.add_edge('a', 'b')
g.add_edge('b', 'a')
(_, _, hashes) = dihash.merkle_hash(g, GlobalMH())

# Later, a new node is added that points into the existing graph
g.add_node('c', label='c')
g.add_edge('c', 'a')
(_, _, new_hashes) = dihash.merkle_hash(g, GlobalMH(), nodes_to_hash=['c'], precomputed_hashes=hashes)

(_, _, from_scratch) = dihash.merkle_hash(g, GlobalMH())
print(new_hashes['c'] == from_scratch['c'])
```

The following output is printed:

```
True
```

## Using a Different String Hash Function
Every function takes a `string_hash_fun` argument, which is used for all of the hashing that the function performs. For example, to use SHA-3 instead of SHA-256:

```
import hashlib
import networkx as nx
import dihash

def hash_sha3(s):
    return hashlib.sha3_256(s.encode('utf-8')).hexdigest()

g = nx.DiGraph()
g.add_node(0, label='a')
print(dihash.global_hash(g, string_hash_fun=hash_sha3) != dihash.global_hash(g))
```

The following output is printed:

```
True
```

# Running the Tests
The tests use pytest. From the root of the repository, run:

```
pip install pytest
python -m pytest tests
```

The tests in `tests/differential_test.py` compare every hash function, on many pairs of small random graphs, with an independent brute-force decision procedure for its equivalence (in `tests/brute_force.py`). For a more thorough search, increase the number of random graph pairs, the graph size, or change the random seed:

```
DIHASH_TRIALS=3000 DIHASH_MAX_NODES=7 DIHASH_SEED=1 python -m pytest tests/differential_test.py
```

# Further Examples

For further examples, see the test scripts in the `tests` folder. `tests/regression_test.py` contains the examples and counterexamples from the paper.
