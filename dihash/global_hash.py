import pynauty
from .util import invert_list, encode, hash_sha256, invert_dict

def _nauty_graph(g):
    """
    Convert a NetworkX graph to a nauty graph

    :param g: A NetworkX digraph with node labels represented as strings, stored in the 'label' field of the NetworkX\
    node attribute dictionary
    :return: A nauty graph
    """
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

    # It turns out that the order of the vertex_coloring passed to nauty is important
    ordered_labels = sorted(colorings_lookup.keys())

    # Convert the dictionary into a list of sets. Each set contains node indices with identical labels
    colorings = [colorings_lookup[label] for label in ordered_labels]

    # Construct the pynauty graph
    nauty_g = pynauty.Graph(g.order(), directed=True, adjacency_dict=adj_dict, vertex_coloring=colorings)

    # Return the node to index conversion function and the nauty graph
    return (node_to_idx, nauty_g)

def _canonize(idx_to_node, nauty_g):
    """
    Returns a list of nodes, ordered in the canonical order
    """
    canon = pynauty.canon_label(nauty_g)
    return [idx_to_node[i] for i in canon]

def _orbits(idx_to_node, nauty_g):
    """
    Returns a list of lists of nodes, each list is an orbit
    """
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

def _analyze_graph(g, compute_orbits):
    """
    Analyze a NetworkX graph, returning a list of nodes in canonical order and a list of orbits
    """
    (node_to_idx, nauty_g) = _nauty_graph(g)
    idx_to_node = invert_dict(node_to_idx)
    if compute_orbits:
        orbs = _orbits(idx_to_node, nauty_g)
    else:
        orbs = None
    return (_canonize(idx_to_node, nauty_g), orbs)

def _orbit_indices(canon_mapping, orbits):
    ret = dict()
    for orb in orbits:
        min_idx = min(canon_mapping[n] for n in orb)
        for n in orb:
            ret[n] = min_idx
    return ret

def global_hash(g, hash_nodes=False, string_hash_fun=hash_sha256):
    """
    Computes a global graph hashing using nauty

    :param g: A NetworkX digraph. Each node should have a 'label' entry in its node attribute dictionary. The value of\
    this entry should be a string which determines the label of that node. g may optionally have a graph attribute\
    named 'label', which is a label for the entire graph
    :param hash_nodes: A boolean value. If True, hash_graph also returns a dictionary giving the hashes of all nodes in\
    the graph
    :param string_hash_fun: A function which maps strings to a string. The default value, hash_sha256 hashes by using\
    hashlib.sha256 and converting to the result to a hex digest.
    :return: The graph hash as a hex digest if hash_nodes is False. Otherwise returns the tuple (g_hash, node_hashes)\
    if hash_nodes is True. node_hashes is a dictionary mapping nodes to their hash hex digests.
    """
    (canonization, orbs) = _analyze_graph(g, compute_orbits=hash_nodes)
    canon_mapping = invert_list(canonization)
    adj_list_in_canon_order = sorted((canon_mapping[s], canon_mapping[t]) for (s, t) in g.edges)
    labels_in_canon_order = [g.nodes[n]['label'] for n in canonization]
    if 'label' in g.graph:
        g_summary = (g.graph['label'], labels_in_canon_order, adj_list_in_canon_order)
    else:
        g_summary = (labels_in_canon_order, adj_list_in_canon_order)
    g_hash = string_hash_fun(encode(g_summary))
    if not hash_nodes:
        return g_hash
    else:
        node_hashes = dict()
        orbit_mapping = _orbit_indices(canon_mapping, orbs)
        for n in g.nodes:
            node_hashes[n] = string_hash_fun(encode((orbit_mapping[n], g_hash)))
        return (g_hash, node_hashes)
