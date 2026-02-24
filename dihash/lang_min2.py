from itertools import product
from functools import cmp_to_key
import networkx as nx

def merge(g: nx.DiGraph, equivalence_classes: list[frozenset]) -> nx.DiGraph:
    # This dictionary maps nodes to their equivalence classes
    class_mapping = dict()
    ret = nx.DiGraph()
    # Add a node for each equivalence class
    for eq_cls in equivalence_classes:
        label = None
        for n in eq_cls:
            class_mapping[n] = eq_cls
            label = g.nodes[n]['label']
        ret.add_node(eq_cls)
        ret.nodes[eq_cls]['label'] = label
    # Add edges between the equivalence classes
    for (u, v) in g.edges:
        u_prime = class_mapping[u]
        v_prime = class_mapping[v]
        ret.add_edge(u_prime, v_prime)
    if 'label' in g.graph:
        ret.graph['label'] = g.graph['label']
    return ret

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

class DistinguishingTable:
    def __init__(self):
        self.markings = dict()

    def get(self, a, b):
        return self.markings[(a, b)]

    def mark(self, a, b, dist_str: list):
        if self.is_marked(a, b):
            raise ValueError(f"The node pair ({a}, {b}) is already marked with a distinguishing string")
        else:
            self.markings[(a, b)] = dist_str

    def is_marked(self, a, b):
        return (a, b) in self.markings

    def is_sub_language(self, a, b):
        return not self.is_marked(a, b) and self.is_marked(b, a)

    def is_eq_language(self, a, b):
        return not self.is_marked(a, b) and not self.is_marked(b, a)

def min_dist_str(g: nx.DiGraph, table: DistinguishingTable, a, bs: list):
    # Returns True if a is distinguishable from all nodes b in bs
    ret = None
    for b in bs:
        if not table.is_marked(a, b):
            return None
        else:
            str = table.get(a, b)
            if ret is None or lt_metric(str, ret):
                ret = str
    if ret is None:
        # The loop did not iterate once. In this case, the distinguishing string will be
        # the label of a alone
        return [g.nodes[a]['label']]
    else:
        # If we're here, then all pairs (a, b) are marked
        return ret

def minimize_table(g: nx.DiGraph) -> DistinguishingTable:
    table = DistinguishingTable()

    for (n, m) in product(g.nodes, g.nodes):
        if n == m:
            continue
        n_label = g.nodes[n]['label']
        m_label = g.nodes[m]['label']
        if n_label != m_label:
            table.mark(n, m, [n_label])

    table_updated = True
    while table_updated:
        table_updated = False
        for (n, m) in product(g.nodes, g.nodes):
            if n == m:
                continue
            if not table.is_marked(n, m):
                min_s = None
                for n_neighbor in g.neighbors(n):
                    s = min_dist_str(g, table, n_neighbor, g.neighbors(m))
                    if s is not None and (min_s is None or lt_metric(s, min_s)):
                        min_s = s
                if min_s is not None:
                    n_label = g.nodes[n]['label']
                    table.mark(n, m, [n_label] + min_s)
                    table_updated = True

    return table

def equivalence_classes(g: nx.DiGraph, table: DistinguishingTable, table_t: DistinguishingTable) -> list[frozenset]:
    merge_map = dict()
    for n in g.nodes:
        merge_map[n] = [n]

    def should_merge(a, b):
        return table_t.is_eq_language(a, b) or (table_t.is_sub_language(a, b) and table.is_sub_language(a, b))

    for (n, m) in product(g.nodes, g.nodes):
        cls_n = merge_map[n]
        cls_m = merge_map[m]
        if cls_n is not cls_m:
            if should_merge(n, m):
                cls_n.extend(cls_m)
                merge_map[m] = cls_n

    return [frozenset(xs) for xs in merge_map.values()]

def reachable_subgraph(g: nx.DiGraph, start_node):
    reachable_nodes = nx.descendants(g, start_node) | {start_node}
    return g.subgraph(reachable_nodes).copy()

def minimize(g: nx.DiGraph, start_node) -> nx.DiGraph:
    g = reachable_subgraph(g, start_node)
    table = minimize_table(g)
    table_t = minimize_table(g.reverse())
    eq_classes = equivalence_classes(g, table, table_t)
    return (merge(g, eq_classes), table, table_t)

def canonize(g: nx.DiGraph, table: DistinguishingTable):
    def sym_diff_metric(u, v):
        if table.is_marked(u, v) and table.is_marked(v, u):
            str_u = table.get(u, v)
            str_v = table.get(v, u)
            # Computing str_v < str_u is not a typo, it's what
            # we actually want to do
            return lt_metric(str_v, str_u)
        elif table.is_marked(v, u):
            return True
        elif table.is_marked(u, v):
            return False
        else:
            raise ValueError(f"The table indicates that the languages for {u} and {v} are equal")
    sym_diff_comparator = make_comparator(sym_diff_metric)

    # TODO: Alter proof so it works without reverse here
    return sorted(g.nodes, key=cmp_to_key(sym_diff_comparator), reverse=True)

def hash(g: nx.DiGraph, start_node):
    (g_prime, table, table_t) = minimize(g, start_node)
    table_t = minimize_table(g_prime.reverse())
    print(canonize(g_prime, table_t))

g = nx.DiGraph()
for i in range(6):
    g.add_node(i)
g.add_edge(0, 1)
g.add_edge(1, 0)
g.add_edge(1, 2)
g.add_edge(0, 2)
g.add_edge(0, 3)
g.add_edge(3, 4)
g.add_edge(3, 5)
g.nodes[0]['label'] = 'a'
g.nodes[1]['label'] = 'f'
g.nodes[2]['label'] = 'b'
g.nodes[3]['label'] = 'b'
g.nodes[4]['label'] = 'c'
g.nodes[5]['label'] = 'e'

table = minimize_table(g)

assert(table.is_sub_language(2, 3))

h = nx.DiGraph()
h.add_node(0)
h.add_node(1)
h.add_node(2)
h.add_node(3)

h.add_edge(0, 1)
h.add_edge(1, 0)
h.add_edge(0, 2)
h.add_edge(1, 2)
h.add_edge(2, 3)

h.nodes[0]['label'] = 'a'
h.nodes[1]['label'] = 'a'
h.nodes[2]['label'] = 'b'
h.nodes[3]['label'] = 'c'

hash(h, 0)