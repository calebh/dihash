import hashlib
import networkx as nx
import pynauty
import math

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

    # It turns out that the order of the vertex_coloring passed to nauty is important
    ordered_labels = sorted(colorings_lookup.keys())

    # Convert the dictionary into a list of sets. Each set contains node indices with identical labels
    colorings = [colorings_lookup[label] for label in ordered_labels]

    # Construct the pynauty graph
    nauty_g = pynauty.Graph(g.order(), directed=True, adjacency_dict=adj_dict, vertex_coloring=colorings)

    # Return the node to index conversion function and the nauty graph
    return (node_to_idx, nauty_g)

# Returns a list of nodes, ordered in the canonical order
def canonize(idx_to_node, nauty_g):
    canon = pynauty.canon_label(nauty_g)
    return [idx_to_node[i] for i in canon]

def escape(s):
    # Replace backslashes with double backslash and quotes with escaped quotes
    return s.replace('\\', '\\\\').replace('"', '\\"')

def to_str(data):
    if isinstance(data, list):
        return "[{}]".format(",".join([to_str(elem) for elem in data]))
    elif isinstance(data, str):
        return '"{}"'.format(escape(data))
    elif isinstance(data, tuple):
        return "({})".format(",".join([to_str(elem) for elem in data]))
    elif isinstance(data, int):
        return str(data)
    else:
        raise TypeError("Unable to call to_str on " + str(data))

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
def analyze_graph(g, compute_orbits):
    (node_to_idx, nauty_g) = nauty_graph(g)
    idx_to_node = invert_dict(node_to_idx)
    if compute_orbits:
        orbs = orbits(idx_to_node, nauty_g)
    else:
        orbs = None
    return (canonize(idx_to_node, nauty_g), orbs)

def compose_dicts(d2, d1):
    return {k: d2.get(v) for (k, v) in d1.items()}

# Returns the number of bits needed to represent an integer input x
def num_to_bit_counts(x):
    return math.ceil(math.log2(x + 1))

# Encodes a node-edge labeled digraph as a node labeled digraph via the conversion
# outlined in the nauty manual, section 14
def edge_labeled_digraph_to_digraph(g):
    edge_labels = set()
    for (s, t) in g.edges():
        edge_labels.add(g.edges[(s, t)]['label'])
    # The manual doesn't say that edges need to be sorted, but we've
    # experimentally verified that changing the edge label order changes
    # g_out due to propogated changes to the created layers. Fortunately
    # we can order our labels.
    edge_layers = sorted(list(edge_labels))
    num_layers = num_to_bit_counts(len(edge_layers))
    format_str = '{0:0' + str(num_layers) + 'b}'
    edge_layer_to_bits = {label: format_str.format(i + 1) for (i, label) in enumerate(edge_layers)}
    g_out = nx.DiGraph()
    # Add the nodes for each layer
    for layer_i in range(num_layers):
        for n in g.nodes():
            g_out.add_node((layer_i, n))
            g_out.nodes[(layer_i, n)]['label'] = g.nodes[n]['label']
    # Create the edges in each layer
    for layer_i in range(num_layers):
        for (s, t) in g.edges():
            edge_label = g.edges[(s, t)]['label']
            from_end_i = -(layer_i + 1)
            # Only add an edge if the bit corresponding to this layer, and the edge label
            # is set to 1
            if edge_layer_to_bits[edge_label][from_end_i] == '1':
                g_out.add_edge((layer_i, s), (layer_i, t))
    # Create the vertical threads for each node
    # Each node in the layer is connected in one direction to the node above it
    for layer_i in range(num_layers - 1):
        for n in g.nodes():
            g_out.add_edge((layer_i, n), (layer_i + 1, n))
    return (g_out, edge_layers)

# g is a MultiDiGraph. This function returns the maximum number of parallel edges in the MultiDiGraph
# If g has no edges, 1 is returned
def max_num_multiedges(g):
    if len(g.edges()) > 0:
        return max(g.number_of_edges(s,t) for (s, t) in g.edges())
    else:
        return 1

# Converts a multigraph to an edge labeled digraph. The edges are labeled with
# the number of edges between two nodes
def multigraph_to_edge_labeled_digraph(g):
    output = nx.DiGraph()
    for n in g.nodes:
        output.add_node(n)
        output.nodes[n]['label'] = g.nodes[n]['label']
    for (s, t) in g.edges():
        output.add_edge(s, t)
    for (s, t) in g.edges():
        output.edges[(s, t)]['label'] = str(g.number_of_edges(s, t))
    return output

# Computes the quotient graph G/Orb
# Input can be either a MultiDiGraph or a DiGraph
# Return result is a MultiDiGraph
def quotient_graph(g):
    if isinstance(g, nx.DiGraph):
        g = nx.MultiDiGraph(g)
    (g_digraph, _) = edge_labeled_digraph_to_digraph(multigraph_to_edge_labeled_digraph(g))
    (node_to_idx, nauty_g) = nauty_graph(g_digraph)
    idx_to_node = invert_dict(node_to_idx)
    # orbs is a list of orbits. Each orbit contains a list of nodes,
    # each node is encoded as (layer_i, node) where layer_i is the layer
    # of the edge encoding and node is a reference to a node in the original graph
    orbs = orbits(idx_to_node, nauty_g)
    output = nx.MultiDiGraph()
    node_to_quotient_idx = {}

    # Filter out the orbits of everything except the first layer
    orbs = [o for o in orbs if o[0][0] == 0]
    for (i, o) in enumerate(orbs):
        representative_idx = i
        output.add_node(representative_idx)
        output.nodes[representative_idx]['label'] = g.nodes[o[0][1]]['label']
        for (_, node) in o:
            node_to_quotient_idx[node] = representative_idx

    for o in orbs:
        # Arbitrarily pick the first node in the orbit
        (_, representative) = o[0]
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

# (g_hash, node_hashes) = dihash.hash_graph(g, hash_nodes=True, apply_quotient=False, string_hash_fun=hash_sha256)
#
# hash_graph has the following inputs:
# - g: A NetworkX digraph. Each node should have a 'label' entry in its node attribute dictionary. The value of this entry should be a string which determines the label of that node. g may optionally have a graph attribute named 'label', which is a label for the entire graph
# - hash_nodes: A boolean value. If true, hash_graph also returns a dictionary giving the hashes of all nodes in the graph
# - apply_quotient: A boolean value. If true, the input graph g is run through the quotient_fixpoint function, which computes (G/Orb)/Orb... prior to hashing the graph.
# - string_hash_fun: A function which maps strings to a string. The default value, hash_sha256 hashes by using hashlib.sha256 and converting to the result to a hex digest.
#
# hash_graph has the following outputs:
# - g_hash: A hex digest of the hash of the entire graph
# - node_hashes: If hash_nodes is False, this value is None. If hash_nodes is True, this value is a dictionary mapping nodes to their hash hex digests.
def hash_graph(g, hash_nodes=True, apply_quotient=False, string_hash_fun=hash_sha256):
    original_graph = g
    original_nodes = frozenset(original_graph.nodes())
    if apply_quotient:
        (sigma, quotient_multigraph) = quotient_fixpoint(original_graph)
        if max_num_multiedges(quotient_multigraph) == 1:
            # If there are no multiedges, simply convert back to an ordinary DiGraph
            g = nx.DiGraph(quotient_multigraph)
        else:
            # Otherwise we have to encode the multigraph into a digraph
            (quotient_digraph, edge_labels) = edge_labeled_digraph_to_digraph(multigraph_to_edge_labeled_digraph(quotient_multigraph))
            # Map n to nodes on the first layer, then compose with the mapping from (0,n) to the node in the quotient graph
            sigma = compose_dicts({n: (0, n) for n in original_nodes}, sigma)
            # The parallel edges in the multigraph were converted to edge labels, and then implicitly
            # encoded in the structure of quotient_digraph. We lost the value of the labels, so we
            # need to take that into account. Here we save the edge labels as a global
            # property of the graph
            if 'label' in original_graph.graph:
                quotient_digraph.graph['label'] = to_str((quotient_digraph.graph['label'], edge_labels))
            else:
                quotient_digraph.graph['label'] = to_str(edge_labels)
            g = quotient_digraph
    else:
        # sigma is the identity mapping
        sigma = {n: n for n in g.nodes()}
    (canonization, orbs) = analyze_graph(g, hash_nodes)
    canon_mapping = invert_list(canonization)
    canon_adj_list = sorted([(canon_mapping[s], canon_mapping[t]) for (s, t) in g.edges])
    canon_labels = [g.nodes[n]['label'] for n in canonization]
    if 'label' in g.graph:
        g_summary = (g.graph['label'], canon_labels, canon_adj_list)
    else:
        g_summary = (canon_labels, canon_adj_list)
    g_hash = string_hash_fun(to_str(g_summary))
    node_hashes = None
    if hash_nodes:
        ordered_orbits = sort_orbits(canon_mapping, orbs)
        # Note that this indexing scheme departs slightly from the paper. Instead of mapping from nodes to the minimum
        # node index in the same orbit, we map from nodes to the index of the orbit, where the index of the orbit
        # is computed based on its order of appearance in ordered_orbits.
        canon_orbits_mapping = canonical_orbits_mapping(ordered_orbits)
        node_hashes = {}
        for n in original_nodes:
            quotient_node = sigma[n]
            node_hashes[n] = string_hash_fun(to_str((canon_orbits_mapping[quotient_node], g_hash)))
    return (g_hash, node_hashes)

# Compute the hashes of nodes in a graph where we have pointers to all the nodes in the node_set
# This is in contrast to the node_hashes in the hash_graph function, where we are assuming
# that we only want the hashes of one pointer into the graph
def hash_graph_node_set(g, node_set, apply_quotient=False, string_hash_fun=hash_sha256):
    # Copy the graph because we're going to need to mutate it
    g = g.copy()
    if len(node_set) >= 2:
        for n in g.nodes():
            if n in node_set:
                # Add a pointer label for each node in the node_set
                g.nodes[n]['label'] = to_str(('ptr', g.nodes[n]['label']))
            else:
                g.nodes[n]['label'] = to_str(('nonptr', g.nodes[n]['label']))            
    (g_hash, node_hashes) = hash_graph(g, hash_nodes=True, apply_quotient=apply_quotient, string_hash_fun=string_hash_fun)
    node_hashes = {n : node_hashes[n] for n in node_set}
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
        non_scc_succs_hashes = sorted([node_hashes[t] for t in non_scc_succs])
        scc_graph.nodes[s]['label'] = string_hash_fun(to_str((g.nodes[s]['label'], non_scc_succs_hashes)))

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