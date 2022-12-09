import hashlib
import networkx as nx
import pynauty

# Convert a NetworkX graph to a nauty graph
# Input should be a NetworkX digraph with node labels represented as strings, stored in the 'label'
# field of the NetworkX node attribute dictionary
def nauty_graph(g):
    # Map each node to a natural number 0,...,n-1 in an arbitrary order. The number of a node is a node index
    node_to_idx = {n: i for (i, n) in enumerate(g.nodes)}
    # Convert the NetworkX adjacency information to use the node indices
    adj_dict = {node_to_idx[s]: [node_to_idx[t] for t in g.successors(s)] for s in g.nodes}

    # Dictionary mapping node labels to a set of node indices
    colorings_lookup = {}
    for n in g.nodes:
        label = g.nodes[n]['label']
        if label not in colorings_lookup:
            colorings_lookup[label] = set()
        colorings_lookup[label].add(node_to_idx[n])

    # Convert the dictionary into a list of sets. Each set contains node indices with identical labels
    colorings = [nodes for (_, nodes) in colorings_lookup.items()]

    # Construct the pynauty graph
    nauty_g = pynauty.Graph(g.order(), directed=True, adjacency_dict=adj_dict, vertex_coloring=colorings)

    # Return the node to index conversion function and the nauty graph
    return (node_to_idx, nauty_g)

# Returns a list of nodes, ordered in the canonical order
def canonize(idx_to_node, nauty_g):
    canon = pynauty.canon_label(nauty_g)
    return [idx_to_node[i] for i in canon]

# Returns a list of lists of nodes, each list is an orbit
def orbits(idx_to_node, nauty_g):
    # orbs gives the orbits of the graph. Two nodes i,j are in the same orbit if and only if orbs[i] == orbs[j]
    (_, _, _, orbs, num_orbits) = pynauty.autgrp(nauty_g)

    # orbits_lookup maps an orbit identifier to a list of nodes in that orbit
    orbits_lookup = {}
    for i in range(len(orbs)):
        orb_label = orbs[i]
        if orb_label not in orbits_lookup:
            orbits_lookup[orb_label] = []
        orbits_lookup[orb_label].append(idx_to_node[i])

    # Now dispose of the orbit identifier, we are only interested in the orbit groupings
    return list(orbits_lookup.values())

# Analyze a NetworkX graph, returning a list of nodes in canonical order and a list of orbits
def analyze_graph(g):
    (node_to_idx, nauty_g) = nauty_graph(g)
    idx_to_node = invert_dict(node_to_idx)
    return (canonize(idx_to_node, nauty_g), orbits(idx_to_node, nauty_g))

def compose_dicts(d2, d1):
    return {k: d2.get(v) for (k, v) in d1.items()}

# Converts a multigraph to a digraph by inserting a node for every edge,
# where the label of that node is the number of edges between the two nodes
def multigraph_to_digraph(g):
    output = nx.DiGraph()
    for n in g.nodes:
        output.add_node(n)
        output.nodes[n]['label'] = g.nodes[n]['label']
    for s in g.nodes:
        for t in g.successors(s):
            output.add_node((s, t))
            output.nodes[(s, t)]['label'] = str(g.number_of_edges(s, t))
            output.add_edge(s, (s, t))
            output.add_edge((s, t), t)
    return output

# Computes the quotient graph G/Orb
# Input can be either a MultiDiGraph or a DiGraph
# Return result is a MultiDiGraph
def quotient_graph(g):
    if isinstance(g, nx.DiGraph):
        g = nx.MultiDiGraph(g)
    original_nodes = frozenset(g.nodes)
    g_digraph = multigraph_to_digraph(g)
    (node_to_idx, nauty_g) = nauty_graph(g_digraph)
    idx_to_node = invert_dict(node_to_idx)
    orbs = orbits(idx_to_node, nauty_g)
    output = nx.MultiDiGraph()
    node_to_quotient_idx = {}
    # Filter out the orbits of the intermediate edge nodes
    orbs = [o for o in orbs if o[0] in original_nodes]
    for (i, o) in enumerate(orbs):
        representative_idx = i
        output.add_node(representative_idx)
        output.nodes[representative_idx]['label'] = g.nodes[o[0]]['label']
        for node in o:
            node_to_quotient_idx[node] = representative_idx
    for o in orbs:
        representative = o[0]
        quotient_representative_idx = node_to_quotient_idx[representative]
        for target in g.successors(representative):
            quotient_target_idx = node_to_quotient_idx[target]
            for i in range(g.number_of_edges(representative, target)):
                output.add_edge(quotient_representative_idx, quotient_target_idx)
    return (node_to_quotient_idx, output)

# Computes the quotient graph (G/Orb)/Orb... until a fixpoint is reached
# Input can be either a MultiDiGraph or a DiGraph
# Return result is a MultiDiGraph
def quotient_fixpoint(g):
    prev = g
    (sigma, output) = quotient_graph(g)
    while output.number_of_nodes() < prev.number_of_nodes():
        prev = output
        (sigma_prime, output) = quotient_graph(output)
        sigma = compose_dicts(sigma_prime, sigma)
    return (sigma, output)

def invert_dict(d):
    return {v: k for (k, v) in d.items()}

def invert_list(lst):
    ret = {}
    for (i, elem) in enumerate(lst):
        ret[elem] = i
    return ret

# Sort a set of orbits by the minimum canonical index
def sort_orbits(canonization_mapping, orbits):
    def min_canon_node(nodes):
        return min([canonization_mapping[n] for n in nodes])

    return sorted(orbits, key=min_canon_node)

# Map nodes to the index of their orbit
def canonical_orbits_mapping(sorted_orbits):
    ret = {}
    for (i, orb) in enumerate(sorted_orbits):
        for n in orb:
            ret[n] = i
    return ret

def hash_sha256(s):
    return hashlib.sha256(s.encode('utf-8')).hexdigest()

def hash_strs(strs, string_hash_fun=hash_sha256):
    return string_hash_fun(",".join(sorted(strs)))

def escape(s):
    # Replace backslashes with double backslash and quotes with escaped quotes
    return s.replace('\\', '\\\\').replace('"', '\\"')

def adj_list_to_str(adj_list):
    return "[" + ",".join(["(" + str(s) + "," + str(t) + ")" for (s, t) in adj_list]) + "]"

# (g_hash, node_hashes) = dihash.hash_graph(g, hash_nodes=True, apply_quotient=False, string_hash_fun=hash_sha256)
# hash_graph has the following inputs:
# - g: A NetworkX digraph. Each node should have a 'label' entry in its node attribute dictionary. The value of this entry should be a string which determines the label of that node.
# - hash_nodes: A boolean value. If true, hash_graph also returns a dictionary giving the hashes of all nodes in the graph
# - apply_quotient: A boolean value. If true, the input graph g is run through the quotient_fixpoint function, which computes (G/Orb)/Orb... prior to hashing the graph.
# - string_hash_fun: A function which maps strings to a string. The default value, hash_sha256 hashes by using hashlib.sha256 and converting to the result to a hex digest.
# hash_graph has the following outputs:
# - g_hash: A hex digest of the hash of the entire graph
# - node_hashes: If hash_nodes is False, this value is None. If hash_nodes is True, this value is a dictionary mapping nodes to their hash hex digests.
def hash_graph(g, hash_nodes=True, apply_quotient=False, string_hash_fun=hash_sha256):
    original_graph = g
    original_nodes = frozenset(original_graph.nodes())
    if apply_quotient:
        (sigma, quotient_multigraph) = quotient_fixpoint(original_graph)
        quotient_digraph = multigraph_to_digraph(quotient_multigraph)
        g = quotient_digraph
    else:
        sigma = {n: n for n in g.nodes()}
    (canonization, orbs) = analyze_graph(g)
    canon_mapping = invert_list(canonization)
    canon_adj_list = sorted([(canon_mapping[s], canon_mapping[t]) for (s, t) in g.edges])
    labels_str = "[" + ",".join(['"' + escape(g.nodes[n]['label']) + '"' for n in canonization]) + "]"
    g_hash = string_hash_fun(labels_str + "," + adj_list_to_str(canon_adj_list))
    ordered_orbits = sort_orbits(canon_mapping, orbs)
    # Note that this indexing scheme departs slightly from the paper. Instead of mapping from nodes to the minimum
    # node index in the same orbit, we map from nodes to the index of the orbit, where the index of the orbit
    # is computed based on its order of appearance in ordered_orbits.
    canon_orbits_mapping = canonical_orbits_mapping(ordered_orbits)
    node_hashes = None
    if hash_nodes:
        node_hashes = {}
        for n in original_nodes:
            quotient_node = sigma[n]
            node_hashes[n] = string_hash_fun(str(canon_orbits_mapping[quotient_node]) + "," + g_hash)
    return (g_hash, node_hashes)

def hash_scc(g, cond, scc, scc_hashes, node_hashes, apply_quotient, string_hash_fun):
    if scc in scc_hashes:
        return

    scc_members = frozenset(cond.nodes[scc]['members'])

    scc_graph = g.subgraph(scc_members).copy()

    for s in scc_members:
        non_scc_succs = frozenset(g.successors(s)) - scc_members
        # Recursively hash all nodes that are the target of an edge from within the scc to outside the scc
        for t in non_scc_succs:
            if t not in node_hashes:
                t_scc = cond.graph['mapping'][t]
                hash_scc(g, cond, t_scc, scc_hashes, node_hashes, apply_quotient, string_hash_fun)
        non_scc_succs_hashes = [node_hashes[t] for t in non_scc_succs]
        scc_graph.nodes[s]['label'] = string_hash_fun('"' + escape(g.nodes[s]['label']) + '",' + hash_strs(non_scc_succs_hashes, string_hash_fun))

    (scc_hash, scc_node_hashes) = hash_graph(scc_graph, hash_nodes=True, apply_quotient=apply_quotient, string_hash_fun=string_hash_fun)

    scc_hashes[scc] = scc_hash
    node_hashes.update(scc_node_hashes)

def merkle_hash_graph(g, nodes_to_hash=None, apply_quotient=False, precomputed_hashes=None, string_hash_fun=hash_sha256):
    if precomputed_hashes is None:
        node_hashes = {}
    else:
        node_hashes = precomputed_hashes.copy()
    scc_hashes = {}
    cond = nx.algorithms.components.condensation(g)
    if nodes_to_hash is None:
        roots = {n for (n, d) in cond.in_degree() if d == 0}
    else:
        roots = {cond.graph['mapping'][n] for n in nodes_to_hash}
    for r in roots:
        hash_scc(g, cond, r, scc_hashes, node_hashes, apply_quotient, string_hash_fun)
    return (scc_hashes, cond, node_hashes)