import hashlib
import networkx as nx
import pynauty

def nauty_graph(g):
    node_to_idx = {n: i for (i, n) in enumerate(g.nodes)}
    adj_dict = {node_to_idx[s]: [node_to_idx[t] for t in g.successors(s)] for s in g.nodes}

    colorings_lookup = {}
    for n in g.nodes:
        label = g.nodes[n]['label']
        if label not in colorings_lookup:
            colorings_lookup[label] = set()
        colorings_lookup[label].add(node_to_idx[n])

    colorings = [nodes for (_, nodes) in colorings_lookup.items()]

    nauty_g = pynauty.Graph(g.order(), directed=True, adjacency_dict=adj_dict, vertex_coloring=colorings)
    return (node_to_idx, nauty_g)

# Returns a list of nodes, ordered in the canonical order
def canonize(g):
    (node_to_idx, nauty_g) = nauty_graph(g)
    idx_to_node = invert_dict(node_to_idx)
    canon = pynauty.canon_label(nauty_g)
    return [idx_to_node[i] for i in canon]

# Returns a list of lists of nodes, each list is an orbit
def orbits(g):
    (node_to_idx, nauty_g) = nauty_graph(g)
    idx_to_node = invert_dict(node_to_idx)
    (_, _, _, orbs, num_orbits) = pynauty.autgrp(nauty_g)

    orbits_lookup = {}
    for i in range(len(orbs)):
        orb_label = orbs[i]
        if orb_label not in orbits_lookup:
            orbits_lookup[orb_label] = []
        orbits_lookup[orb_label].append(idx_to_node[i])

    return list(orbits_lookup.values())

def invert_dict(d):
    return {v: k for (k, v) in d.items()}

def invert_list(lst):
    ret = {}
    for (i, elem) in enumerate(lst):
        ret[elem] = i
    return ret

def sort_orbits(canonization_mapping, orbits):
    def min_canon_node(nodes):
        return min([canonization_mapping[n] for n in nodes])

    return sorted(orbits, key=min_canon_node)

def canonical_orbits_mapping(canonization_mapping, sorted_orbits):
    ret = {}
    for (i, orb) in enumerate(sorted_orbits):
        for n in orb:
            ret[n] = i

    return ret

def hash_str(s):
    #return s
    return hashlib.sha256(s.encode('utf-8')).hexdigest()

def hash_strs(strs):
    return hash_str(",".join(sorted(strs)))

def escape(s):
    # Replace backslashes with double backslash and quotes with escaped quotes
    return s.replace('\\', '\\\\').replace('"', '\\"')

def adj_list_to_str(adj_list):
    return "[" + ",".join(["(" + str(s) + "," + str(t) + ")" for (s, t) in adj_list]) + "]"

def hash_scc(g, cond, scc, collapse_orbits=True):
    if cond.nodes[scc]['hash'] is not None:
        return

    for succ in cond.successors(scc):
        hash_scc(g, cond, succ, collapse_orbits=collapse_orbits)

    scc_members = set(cond.nodes[scc]['members'])
    for n in scc_members:
        non_scc_succs = set(g.successors(n)) - scc_members
        non_scc_succs_hashes = [g.nodes[n]['hash'] for n in non_scc_succs]
        g.nodes[n]['nonrec_hash'] = hash_str('"' + escape(g.nodes[n]['label']) + '",' + hash_strs(non_scc_succs_hashes))

    scc_graph = g.subgraph(scc_members).copy()
    for n in scc_graph.nodes:
        scc_graph.nodes[n]['label'] = scc_graph.nodes[n]['nonrec_hash']

    canonization = canonize(scc_graph)
    canonization_mapping = invert_list(canonization)

    orbs = orbits(scc_graph)
    sorted_orbits = sort_orbits(canonization_mapping, orbs)
    scc_canon_orbits_mapping = canonical_orbits_mapping(canonization_mapping, sorted_orbits)

    if collapse_orbits:
        collapsed_scc = nx.DiGraph()
        for i in range(len(orbs)):
            collapsed_scc.add_node(i)
        for (s, t) in scc_graph.edges:
            collapsed_scc.add_edge(scc_canon_orbits_mapping[s], scc_canon_orbits_mapping[t])
        coll_scc_canon_adj_list = sorted(list(collapsed_scc.edges))
        coll_scc_nonrec_hashes = [scc_graph.nodes[orb[0]]['nonrec_hash'] for orb in sorted_orbits]
        coll_scc_adj_list_str = adj_list_to_str(coll_scc_canon_adj_list)
        scc_hash = hash_str("[" + ",".join(coll_scc_nonrec_hashes) + "]," + coll_scc_adj_list_str)
    else:
        scc_canon_adj_list = sorted([(canonization_mapping[s], canonization_mapping[t]) for (s, t) in scc_graph.edges])
        scc_canon_nonrec_hashes = [scc_graph.nodes[n]['nonrec_hash'] for n in canonization]
        scc_canon_adj_list_str = adj_list_to_str(scc_canon_adj_list)
        scc_hash = hash_str("[" + ",".join(scc_canon_nonrec_hashes) + "]," + scc_canon_adj_list_str)

    cond.nodes[scc]['hash'] = scc_hash
    for n in scc_members:
        n_hash = hash_str(str(scc_canon_orbits_mapping[n]) + "," + scc_hash)
        g.nodes[n]['hash'] = n_hash

def hash_graph(g, collapse_orbits=True):
    cond = nx.algorithms.components.condensation(g)
    for scc in cond.nodes:
        cond.nodes[scc]['hash'] = None
    roots = [n for (n, d) in cond.in_degree() if d == 0]
    for r in roots:
        hash_scc(g, cond, r, collapse_orbits=collapse_orbits)

def exact_graph_hash(g):
    canonization = canonize(g)
    canon_mapping = invert_list(canonization)
    canon_adj_list = sorted([(canon_mapping[s], canon_mapping[t]) for (s, t) in g.edges])
    labels_str = "[" + ",".join(['"' + escape(g.nodes[n]['label']) + '"' for n in canonization]) + "]"
    g_hash = hash_str(labels_str + "," + adj_list_to_str(canon_adj_list))
    canon_orbits_mapping = canonical_orbits_mapping(canon_mapping, sort_orbits(canon_mapping, orbits(g)))
    for n in g.nodes:
        n_hash = hash_str(str(canon_orbits_mapping[n]) + "," + g_hash)
        g.nodes[n]['hash'] = n_hash
