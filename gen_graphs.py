import networkx as nx
from itertools import product
import dihash

# Some functions for generating all possible directed graphs, with duplicate
# graphs removed.

def generate_graphs_generic(num_nodes, add_graph_fun):
	true_false = [True, False]
	combinations = [true_false for _ in range(num_nodes * num_nodes)]
	graphs = []
	count = 0
	for edges in product(*combinations):
		count += 1
		g = nx.DiGraph()
		for i in range(num_nodes):
			g.add_node(i)
			g.nodes[i]['label'] = ''
		for i in range(num_nodes):
			for j in range(num_nodes):
				if edges[i * num_nodes + j]:
					g.add_edge(i, j)
		if add_graph_fun(graphs, g):
			graphs.append(g)
	return graphs

# Generate all possible graphs, with duplicate cheking via the dihash.hash_graph function
def generate_graphs(num_nodes):
	graph_hashes = set()
	def add_graph_fun(graphs, g):
		(g_hash, _) = dihash.hash_graph(g, hash_nodes=False)
		ret = g_hash not in graph_hashes
		graph_hashes.add(g_hash)
		return ret
	return generate_graphs_generic(num_nodes, add_graph_fun)

# Generate all possible graphs, with duplicate checking via nx.is_isomorphic function
def generate_graphs_nx_iso(num_nodes):
	def add_graph_fun(graphs, g):
		for h in graphs:
			if nx.is_isomorphic(g, h):
				return False
		return True
	return generate_graphs_generic(num_nodes, add_graph_fun)
