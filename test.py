import networkx as nx
from dihash import hash_graph

g = nx.DiGraph()
g.add_node(0)
g.add_node(1)
g.add_node(2)
g.add_node(3)
g.add_node(4)
g.add_node(5)
g.add_edge(0, 1)
g.add_edge(1, 0)
g.add_edge(0, 2)
g.add_edge(2, 3)
g.add_edge(3, 2)
g.add_edge(1, 4)
g.add_edge(4, 5)
g.add_edge(5, 4)
g.nodes[0]['label'] = 'hello world'
g.nodes[1]['label'] = 'hello world'
g.nodes[2]['label'] = 'hello world'
g.nodes[3]['label'] = 'hello world'
g.nodes[4]['label'] = 'hello world'
g.nodes[5]['label'] = 'hello world'

hash_graph(g, collapse_orbits=True)

for n in g.nodes:
    print(str(n) + ": " + g.nodes[n]['hash'])