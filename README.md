# dihash
Python implementation of directed graph hashing, from the paper "Directed Graph Hashing"

# Version 2.0
dihash has been updated to 2.0, which is a rewrite of 1.0 with bugfixes and cleaner code. An updated version of the paper will be forthcoming. Unit tests have been added, as well as a benchmarking script. The hashes of 2.0 are not backward compatible with 1.0 due to a re-write of the string encoding function.

# Dependencies
- Python 3
- NetworkX: https://networkx.org/
- pynauty: The main repository now supports computing orbits, which means using a forked version is no longer necessary. See https://github.com/pdobsan/pynauty for more details. Note that when we installed pynauty with pip3, we had to run `pip install --no-binary pynauty pynauty` since the default binary gave segmentation faults.

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

For further examples, see the unit test script `test.py`.