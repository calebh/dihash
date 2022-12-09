# dihash
Python implementation of directed graph hashing, from the paper "Directed Graph Hashing"

# Dependencies
- Python 3
- NetworkX: https://networkx.org/
- pynauty: The main repository now supports computing orbits, which means using a forked version is no longer necessary. See https://github.com/pdobsan/pynauty for more details

# How to Use
The primary graph hashing algorithm has the following definiton:

```
(g_hash, node_hashes) = dihash.hash_graph(g, hash_nodes=True, apply_quotient=False, string_hash_fun=hash_sha256)
```

`hash_graph` has the following inputs:
- g: A NetworkX digraph. Each node should have a 'label' entry in its node attribute dictionary. The value of this entry should be a string which determines the label of that node.
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
1a04a11e6643d72321fe9a6742d5a136cb57416711de3bc88cac8c49eee85227
{0: '223fd1e16ea9d95a5007ec9f38d85609ea57a11d0c37f387e762a6b9c64eaac5', 1: '223fd1e16ea9d95a5007ec9f38d85609ea57a11d0c37f387e762a6b9c64eaac5', 2: '223fd1e16ea9d95a5007ec9f38d85609ea57a11d0c37f387e762a6b9c64eaac5'}
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
dd9e82ad81a8ddf421beace1904e131609cf0d0f363f14e54b1139f869462d09
5caf61e88fa34a9e2d3d7bb06cb585ccc06955ab54531a5431982e139c93f9a7
5caf61e88fa34a9e2d3d7bb06cb585ccc06955ab54531a5431982e139c93f9a7
dd9e82ad81a8ddf421beace1904e131609cf0d0f363f14e54b1139f869462d09
9c004ab952e1b947fd76b308b6ba87edc33c7df7e57ae170e47006a3be38be75
```

`multigraph_to_digraph` is an auxillary function that converts a node labelled NetworkX MultiDiGraph into an isomorphic NetworkX DiGraph. This is useful if you wish to hash a MultiDiGraph.

```
g_prime = dihash.multigraph_to_digraph(g)
```

`multigraph_to_digraph` has the following inputs:
- g: A NetworkX multi-edged digraph with node labels defined in the node attribute dictionary via the 'label' key

`multigraph_to_digraph` returns the following value:
- g_prime: A NetworkX digraph with intermediate nodes inserted for every edge of the input. The labels of the intermediate node is the number of times an edge appears in the multi-edged digraph.

Example:

```
g = nx.MultiDiGraph()
g.add_node(0)
g.add_node(1)
g.nodes[0]['label'] = 'a'
g.nodes[1]['label'] = 'b'
g.add_edge(0, 1)
g.add_edge(0, 1)

g_prime = dihash.multigraph_to_digraph(g)

print(list(g_prime.nodes()))
print(list(g_prime.edges()))
print(g_prime.nodes[(0,1)]['label']) # (0, 1) is the intermediate node inserted between 0 and 1
```

The following output is printed:

```
[0, 1, (0, 1)]
[(0, (0, 1)), ((0, 1), 1)]
2
```