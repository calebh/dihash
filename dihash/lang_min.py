import functools

import networkx as nx
import matplotlib.pyplot as plt

def lt_metric(a_lst, b_lst):
    if len(a_lst) < len(b_lst):
        return True
    elif len(a_lst) > len(b_lst):
        return False
    else:
        for (a, b) in zip(a_lst, b_lst):
            if a < b:
                return True
            elif b > a:
                return False
        return False

def make_comparator(less_than):
    def compare(x, y):
        if less_than(x, y):
            return -1
        elif less_than(y, x):
            return 1
        else:
            return 0
    return compare

lt_comparator = make_comparator(lt_metric)

def lt_lst_metric(a_lst_lst, b_lst_lst):
    pass

class DistinguishingTable:
    def __init__(self):
        self.markings = set()

    def mark(self, a, b):
        # Mark a and b as distinguishable
        self.markings.add(frozenset([a, b]))

    def is_marked(self, a, b):
        # Returns True if a and b are distinguishable
        return frozenset([a, b]) in self.markings

class MetricTable:
    def __init__(self):
        self.candidate_distinguishers = dict()
        self.commited_distinguishers = dict()

    def lookup(self, a, b):
        return self.commited_distinguishers[(a, b)]

    def is_marked(self, a, b):
        return (a, b) in self.commited_distinguishers

    def add_candidate(self, a, b, distinguisher):
        if (a, b) not in self.candidate_distinguishers:
            self.candidate_distinguishers[(a, b)] = [distinguisher]
        else:
            self.candidate_distinguishers[(a, b)].append(distinguisher)

    def commit(self) -> bool:
        for (pair, candidates) in self.candidate_distinguishers.items():
            min_distinguisher = candidates[0]
            for i in range(1, len(candidates)):
                c = candidates[i]
                if lt_metric(c, min_distinguisher):
                    min_distinguisher = c
            self.commited_distinguishers[pair] = min_distinguisher
        ret = len(self.candidate_distinguishers) > 0
        self.candidate_distinguishers.clear()
        return ret

def pairs(lst):
    ret = []
    for i in range(len(lst)):
        for j in range(i, len(lst)):
            ret.append((lst[i], lst[j]))
    return ret

def is_distinguishable(table, a, bs):
    # Returns True if a is distinguishable from all nodes b in bs
    for b in bs:
        if not table.is_marked(a, b):
            return False
    # If we're here, then all pairs (a, b) are marked
    return True

def minimize_table(g: nx.DiGraph) -> DistinguishingTable:
    table = DistinguishingTable()
    metric_table = MetricTable()

    node_pairs = pairs(list(g.nodes))

    for (n, m) in node_pairs:
        n_label = g.nodes[n]['label']
        m_label = g.nodes[m]['label']
        if n_label != m_label:
            table.mark(n, m)
            metric_table.add_candidate(n, m, [n_label])
            metric_table.add_candidate(m, n, [m_label])
    metric_table.commit()

    table_updated = True
    while table_updated:
        table_updated = False
        for (n, m) in node_pairs:
            if not table.is_marked(n, m):
                for n_neighbor in g.neighbors(n):
                    if is_distinguishable(table, n_neighbor, g.neighbors(m)):
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

def canonize(minimized_graph, certificate=False):
    metric_table = MetricTable()

    for n in minimized_graph.nodes:
        for m in minimized_graph.nodes:
            n_label = minimized_graph.nodes[n]['label']
            m_label = minimized_graph.nodes[m]['label']
            if n_label != m_label:
                metric_table.add_candidate(n, m, [n_label])
                metric_table.add_candidate(m, n, [m_label])
            else:
                if minimized_graph.out_degree(m) == 0:
                    for n_neighbor in minimized_graph.neighbors(n):
                        n_neighbor_label = minimized_graph.nodes[n_neighbor]['label']
                        metric_table.add_candidate(n, m, [n_label, n_neighbor_label])
    metric_table.commit()

    table_updated = True
    while table_updated:
        for n in minimized_graph.nodes:
            n_label = minimized_graph.nodes[n]['label']
            for m in minimized_graph.nodes:
                if not metric_table.is_marked(n, m):
                    for n_neighbor in minimized_graph.neighbors(n):
                        if is_distinguishable(metric_table, n_neighbor, minimized_graph.neighbors(m)):
                            for m_neighbor in minimized_graph.neighbors(m):
                                neighbor_distinguisher = metric_table.lookup(n_neighbor, m_neighbor)
                                metric_table.add_candidate(n, m, [n_label] + neighbor_distinguisher)
        table_updated = metric_table.commit()

    canonical_order = []
    for n in minimized_graph.nodes:
        dist = []
        for m in minimized_graph.nodes:
            if metric_table.is_marked(n, m):
                dist.append(tuple(metric_table.lookup(n, m)))
        # Remove duplicate distinguishers
        dist = list(set(dist))
        dist.sort()
        canonical_order.append((n, tuple(dist)))
    canonical_order.sort(key=lambda pair: pair[1])
    if not certificate:
        canonical_order = [n for (n, _) in canonical_order]
    return canonical_order

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
g.add_edge(6, 10)
g.add_edge(7, 10)
g.add_edge(8, 10)
g.add_edge(9, 10)
g.nodes[10]['label'] = 'x'

#g.add_node(11)
#g.add_edge(10, 11)
#g.nodes[11]['label'] = 'zz'

fig=plt.figure()
min_g = minimize(g)
nx.draw(min_g, labels={n: f"{n}: {min_g.nodes[n]['label']}" for n in min_g.nodes})
plt.show()
order = canonize(min_g)
print(order)

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

min_g = minimize(g2)
nx.draw(min_g, labels={n: min_g.nodes[n]['label'] for n in min_g.nodes})
plt.show()
order = canonize(min_g)
print(order)

g3 = nx.DiGraph()
g3.add_node(0)
g3.add_node(1)
g3.add_edge(0, 1)
g3.nodes[0]['label'] = 'b'
g3.nodes[1]['label'] = 'b'

min_g = minimize(g3)
nx.draw(min_g, labels={n: min_g.nodes[n]['label'] for n in min_g.nodes})
plt.show()
order = canonize(min_g)
print(order)

g4 = nx.DiGraph()
g4.add_node(0)
g4.add_node(1)
g4.add_node(2)
g4.add_node(3)
g4.add_node(4)
g4.add_node(5)

g4.nodes[0]['label'] = 'a'
g4.nodes[1]['label'] = 'b'
g4.nodes[2]['label'] = 'b'
g4.nodes[3]['label'] = 'c'
g4.nodes[4]['label'] = 'c'
g4.nodes[5]['label'] = 'c'

g4.add_edge(0, 1)
g4.add_edge(0, 2)
g4.add_edge(1, 3)
g4.add_edge(1, 4)
g4.add_edge(0, 2)
g4.add_edge(2, 5)
g4.add_edge(3, 0)
g4.add_edge(4, 0)
g4.add_edge(5, 0)

min_g = minimize(g4)
nx.draw(min_g, labels={n: min_g.nodes[n]['label'] for n in min_g.nodes})
plt.show()
