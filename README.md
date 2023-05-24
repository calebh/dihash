# dihash
Python implementation of directed graph hashing, from the paper "Directed Graph Hashing"

# Now on PyPi

This project is now on PyPi and can be directly installed with pip. If you have problems with the pynauty dependency, see the "Dependencies" section below.

```
pip install dihash
```

# Version 2.0
dihash has been updated to 2.0, which is a rewrite of 1.0 with bugfixes and cleaner code. An updated version of the paper is now available on arXiv at https://arxiv.org/abs/2002.06653. Unit tests have been added, as well as a benchmarking script. The hashes of 2.0 are not backward compatible with 1.0 due to a re-write of the string encoding function.

# Version 2.1
A critical bug has been fixed with the color ordering passed to pynauty. Previously I had assumed that the order of the node colors passed to pynauty did not matter, however testing revealed this not to be the case. The issue was resolved by sorting the coloring by label lexiographical order before passing to pynauty.

# Dependencies
- Python 3
- NetworkX: https://networkx.org/
- pynauty: The main repository now supports computing orbits, which means using a forked version is no longer necessary. See https://github.com/pdobsan/pynauty for more details. Note that when we installed pynauty with pip3, we had to run `pip install --no-binary pynauty pynauty` since the default binary gave segmentation faults. pynauty does not seem to have Windows support, which means that Linux/Unix is a requirement for this library as well.

# How to Use
The primary graph hashing algorithm has the following definiton:

```
(g_hash, node_hashes) = dihash.hash_graph(g, hash_nodes=True, apply_quotient=False, string_hash_fun=hash_sha256)
```

`hash_graph` has the following inputs:
- g: A NetworkX digraph. Each node should have a 'label' entry in its node attribute dictionary. The value of this entry should be a string which determines the label of that node. g may optionally have a graph attribute named 'label', which is a label for the entire graph
- hash_nodes: A boolean value. If true, hash_graph also returns a dictionary giving the hashes of all nodes in the graph
- apply_quotient: A boolean value. If true, the input graph g is run through the quotient_fixpoint function, which computes (G/Orb)/Orb... prior to hashing the graph.
- string_hash_fun: A function which maps strings to a string. The default value, hash_sha256 hashes by using hashlib.sha256 and converting to the result to a hex digest.

`hash_graph` has the following outputs:
- g_hash: A hex digest of the hash of the entire graph
- node_hashes: If hash_nodes is False, this value is None. If hash_nodes is True, this value is a dictionary mapping nodes to their hash hex digests.

Example:

```
g = nx.DiGraph()
g.add_node(0)
g.add_node(1)
g.add_node(2)
g.nodes[0]['label'] = 'a'
g.nodes[1]['label'] = 'a'
g.nodes[2]['label'] = 'a'

g.add_edge(0, 1)
g.add_edge(1, 2)
g.add_edge(2, 0)

(g_hash, node_hashes) = dihash.hash_graph(g, apply_quotient=False)

print(g_hash)
print(node_hashes)
```

The following output is printed:

```
b37deb748c68bd738fdb647aa638ad8654c690d8ce14507fd21f1f299faf7ed5
{0: 'ad6321ae4eb544ab1f00db6436938427e01176cc3b4fed44ef0c6a0a88a0a7c3', 1: 'ad6321ae4eb544ab1f00db6436938427e01176cc3b4fed44ef0c6a0a88a0a7c3', 2: 'ad6321ae4eb544ab1f00db6436938427e01176cc3b4fed44ef0c6a0a88a0a7c3'}
```

The Merkle graph hashing algorithm has the following definition:

```
(scc_hashes, cond, node_hashes) = merkle_hash_graph(g, nodes_to_hash=None, apply_quotient=False, precomputed_hashes=None, string_hash_fun=hash_sha256)
```

`merkle_hash_graph` has the following inputs:
- g: A NetworkX digraph. Each node should have a 'label' entry in its node attribute dictionary. The value of this entry should be a string which determines the label of that node.
- nodes_to_hash: A list of nodes to hash in the graph. If nodes_to_hash is None, all nodes in the input graph will be hashed.
- apply_quotient: A boolean value. If true, the SCCs in the hashing function will be run through the quotient_fixpoint function prior to hashing.
- precomputed_hashes: A dictionary mapping nodes to their hashes (should be encoded as a string hexdigest). This parameter is useful if you are hashing graphs built up over time. If a node has a hash set in the dictionary, that node's precomputed hash will be used instead of recursively hashing the graph.
- string_hash_fun: A function which maps strings to a string. The default value, hash_sha256 hashes by using hashlib.sha256 and converting to the result to a hex digest.

`merkle_hash_graph` has the following outputs:
- scc_hashes: A dictionary mapping strongly connected component integer IDs to string hex digests. The integers represent specific strongly connected components in the input graph. To retrieve the SCC integer ID for some node n, use `cond.graph['mapping'][n]`.
- cond: The condensation digraph of the input graph, computed using [`nx.algorithms.components.condensation`](https://networkx.org/documentation/stable/reference/algorithms/generated/networkx.algorithms.components.condensation.html).
- node_hashes: A dictionary mapping nodes to hashes. This dictionary includes the hashes of all nodes that were involved in the computation of `merkle_hash_graph`.

Example:

```
g = nx.DiGraph()
g.add_node(0)
g.add_node(1)
g.add_node(2)
g.add_node(3)
g.add_node(4)
g.add_node(5)
g.add_node(6)

g.nodes[0]['label'] = 'a'
g.nodes[1]['label'] = 'a'
g.nodes[2]['label'] = 'a'
g.nodes[3]['label'] = 'a'
g.nodes[4]['label'] = 'a'
g.nodes[5]['label'] = 'a'
g.nodes[6]['label'] = 'a'

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

(scc_hashes, cond, node_hashes) = dihash.merkle_hash_graph(g, apply_quotient=False)

print(node_hashes[1])
print(node_hashes[2])
print(node_hashes[3])
print(node_hashes[4])
print(scc_hashes[cond.graph['mapping'][0]]) # Print the hash for the SCC containing node 0
```

The following output is printed:

```
0794c37c25dd026eab1c46c607a7a44f1faaf32f8d0f7dfdaf7728a25707a9dc
4ad992c5399689c950e46ec0b4ae4921457f94a319ecba4b3d1f66d8ef00463b
4ad992c5399689c950e46ec0b4ae4921457f94a319ecba4b3d1f66d8ef00463b
0794c37c25dd026eab1c46c607a7a44f1faaf32f8d0f7dfdaf7728a25707a9dc
e9abdcec4447c828c2f259e8bf30e5bf0001da93e3e09fa01654e6d54018d42a
```

If we want to simultaneously create multiple node pointers into the given input graph, we can use the hash_graph_node_set function. This function has the following signature:

```
(g_hash, node_hashes) = hash_graph_node_set(g, node_set, apply_quotient=False, string_hash_fun=hash_sha256)
```

The node_set input should be a set of nodes that we want to create pointers for into the graph. The function works by modifying the labels of the graph nodes.

Example:
```
# Create a cycle graph with 4 nodes
g2 = nx.DiGraph()
g2.add_node(1)
g2.add_node(2)
g2.add_node(3)
g2.add_node(4)

g2.nodes[1]['label'] = 'node_label'
g2.nodes[2]['label'] = 'node_label'
g2.nodes[3]['label'] = 'node_label'
g2.nodes[4]['label'] = 'node_label'

g2.add_edge(1, 2)
g2.add_edge(2, 3)
g2.add_edge(3, 4)
g2.add_edge(4, 1)

(g_hash5, node_hashes5) = dihash.hash_graph_node_set(g2, {1, 2})
(g_hash6, node_hashes6) = dihash.hash_graph_node_set(g2, {3, 4})

assert(g_hash5 == g_hash6)
assert(node_hashes5[1] != node_hashes5[2])
assert(node_hashes6[3] != node_hashes6[4])
assert(node_hashes5[1] == node_hashes6[3])
assert(node_hashes5[2] == node_hashes6[4])
```

The edge labeled digraph encoding algorithm has the following definition:

`(g_out, edge_labels) = edge_labeled_digraph_to_digraph(g)`

The input graph `g` with edge labels (defined in the 'label' property of the edge) is converted to a node-labeled digraph via the encoding described in Section 14 of the nauty User's manual. Since the values of the edge labels are erased, the return value `edge_labels` is a sorted list of the set of edge labels in the input graph. If you want to hash an edge labeled digraph, remember to encode `edge_labels` as a string and assign it as the label of `g_out`.

The multigraph encoding algorithm has the following definition:

`g_out = multigraph_to_edge_labeled_digraph(g)`

The input graph `g` is a node labeled multigraph. Parallel (duplicate) edges are encoded in the edge label of `g_out`. The label is defined to be the number of edges encoded as a base 10 string.

`multigraph_to_edge_labeled_digraph` is an auxillary function that converts a node labelled NetworkX MultiDiGraph into an isomorphic NetworkX edge labeled DiGraph. This is

```
g_prime = dihash.multigraph_to_digraph(g)
```

Example:

```
g = nx.MultiDiGraph()
g.add_node(0)
g.add_node(1)
g.nodes[0]['label'] = 'a'
g.nodes[1]['label'] = 'b'
g.add_edge(0, 1)
g.add_edge(0, 1)

g_prime = dihash.multigraph_to_edge_labeled_digraph(g)

print(list(g_prime.nodes()))
print(list(g_prime.edges()))
print(g_prime.edges[0,1]['label'])
```

The following output is printed:

```
[0, 1]
[(0, 1)]
2
```

# Further Examples

For further examples, see the unit test script `tests/hash_impl_test.py`.