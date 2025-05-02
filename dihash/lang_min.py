import networkx as nx
import matplotlib.pyplot as plt

class DistinguishingTable:
    def __init__(self):
        self.markings = set()

    def mark(self, a, b):
        # Mark a and b as distinguishable
        self.markings.add(frozenset([a, b]))

    def is_marked(self, a, b):
        # Returns True if a and b are distinguishable
        return frozenset([a, b]) in self.markings

def pairs(lst):
    ret = []
    for i in range(len(lst)):
        for j in range(i, len(lst)):
            ret.append((lst[i], lst[j]))
    return ret

def minimize_table(g: nx.DiGraph) -> DistinguishingTable:
    table = DistinguishingTable()

    node_pairs = pairs(list(g.nodes))

    for (n, m) in node_pairs:
        n_label = g.nodes[n]['label']
        m_label = g.nodes[m]['label']
        if n_label != m_label:
            table.mark(n, m)

    def is_distinguishable(a, bs):
        # Returns True if a is distinguishable from all nodes b in bs
        for b in bs:
            if not table.is_marked(a, b):
                return False
        return True

    table_updated = True
    while table_updated:
        table_updated = False
        for (n, m) in node_pairs:
            if not table.is_marked(n, m):
                for n_neighbor in g.neighbors(n):
                    if is_distinguishable(n_neighbor, g.neighbors(m)):
                        table.mark(n, m)
                        table_updated = True

    return table

def equivalence_classes(g: nx.DiGraph, table: DistinguishingTable) -> list[list]:
    equivalence_classes: list[list] = []
    for n in g.nodes:
        found_class = False
        for cls in equivalence_classes:
            representative = cls[0]
            if not table.is_marked(n, representative):
                cls.append(n)
                found_class = True
                break
        if not found_class:
            equivalence_classes.append([n])

    return equivalence_classes

def minimize(g: nx.DiGraph):
    table = minimize_table(g)
    eq_classes = equivalence_classes(g, table)
    def label(nodes):
        n = list(nodes)[0]
        return {'label': g.nodes[n]['label']}
    return nx.quotient_graph(g, eq_classes, node_data=label)


g = nx.DiGraph()

g.add_node(0)
g.nodes[0]['label'] = 'x'

g.add_node(1)
g.add_node(2)
g.add_node(3)
g.add_edge(0, 1)
g.add_edge(0, 2)
g.add_edge(0, 3)
g.nodes[1]['label'] = 'a'
g.nodes[2]['label'] = 'b'
g.nodes[3]['label'] = 'c'

g.add_node(4)
g.add_node(5)
g.add_edge(1, 4)
g.add_edge(1, 5)
g.nodes[4]['label'] = 'b'
g.nodes[5]['label'] = 'c'

g.add_node(6)
g.add_node(7)
g.add_edge(2, 6)
g.add_edge(2, 7)
g.nodes[6]['label'] = 'c'
g.nodes[7]['label'] = 'a'

g.add_node(8)
g.add_node(9)
g.add_edge(3, 8)
g.add_edge(3, 9)
g.nodes[8]['label'] = 'a'
g.nodes[9]['label'] = 'b'

g.add_node(10)
g.add_edge(4, 10)
g.add_edge(5, 10)
g.add_edge(5, 10)
g.add_edge(6, 10)
g.add_edge(7, 10)
g.add_edge(8, 10)
g.add_edge(9, 10)
g.nodes[10]['label'] = 'z'

#fig=plt.figure()
min_g = minimize(g)
nx.draw(min_g, labels={n: min_g.nodes[n]['label'] for n in min_g.nodes})
plt.show()

input("Continue?")

g2 = nx.DiGraph()
g2.add_node(0)
g2.add_node(1)
g2.add_node(2)
g2.add_edge(0, 1)
g2.add_edge(1, 2)
g2.add_edge(2, 0)
g2.nodes[0]['label'] = 'a'
g2.nodes[1]['label'] = 'a'
g2.nodes[2]['label'] = 'b'

print(minimize_table(g2))