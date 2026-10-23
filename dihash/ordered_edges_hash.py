import functools
from collections import defaultdict

import networkx as nx

from dihash.global_hash import _orbit_indices
from dihash.util import invert_list, hash_sha256, encode

def _port_successors(g, u):
    succ = sorted(((v, v_attr['port']) for (v, v_attr) in g[u].items()), key=lambda tup: tup[1])
    for i in range(1, len(succ)):
        if succ[i - 1][1] == succ[i][1]:
            raise ValueError(f"Node {u} has two outgoing edges with port {succ[i][1]}; ports must be distinct")
    for (v, _) in succ:
        yield v

def _dfs(start, succ_iter):
    """
    Preorder (discovery order) of a depth-first search from start that explores the out-edges of each node in the\
    order given by succ_iter.
    """
    discovered = {start}
    yield start

    stack = [succ_iter(start)]

    while len(stack) > 0:
        for node in stack[-1]:
            if node not in discovered:
                discovered.add(node)
                yield node
                stack.append(succ_iter(node))
                break
        else:
            stack.pop()

def _ordered_edges_hash(g, node, string_hash_fun):
    discovery_order = []
    succ_iter = functools.partial(_port_successors, g)
    for reachable_node in _dfs(node, succ_iter):
        discovery_order.append(reachable_node)

    labels = [g.nodes[n]['label'] for n in discovery_order]

    order_lookup = invert_list(discovery_order)

    out_seq = [[order_lookup[succ] for succ in succ_iter(node)] for node in discovery_order]

    return (string_hash_fun(encode((labels, out_seq))), discovery_order, order_lookup)

def ordered_edges_node_hash(g, node, string_hash_fun=hash_sha256):
    """
    Returns the hash of a node, solely determined by the reachable graph from that node. The graph is canonized\
    based on the DFS traversal order.

    :param g: An input directed graph, with edges having a label called 'port'. The outgoing edges of a node should\
    have non-duplicate port numbers.
    :param node: The node to compute the hash of.
    :param string_hash_fun: The string hashing function to use. Default is SHA-256
    :return:
    """
    return _ordered_edges_hash(g, node, string_hash_fun=string_hash_fun)[0]

def ordered_edges_sc_global_hash(g, hash_nodes=False, string_hash_fun=hash_sha256):
    """
    Returns the hash of an entire strongly connected ordered graph, along with the hash of the nodes in the graph

    :param g: A strongly connected digraph. Edges in the graph should have a label called 'port', whose value is the port\
    identifier of that edge. The outgoing edges of a node should have non-duplicate port numbers. The port numbers\
    are used to order the DFS from the nodes.
    :param hash_nodes: If hash_nodes is True, the return value is (g_hash, node_hashes). Otherwise only the graph hash\
    is returned
    :param string_hash_fun: The string hashing function to use. Default is SHA-256
    :return: If hash_nodes is True, returns a tuple of (g_hash, node_hashes). Otherwise returns only the hash of the\
    entire strongly connected graph.
    """
    if not nx.is_strongly_connected(g):
        raise AssertionError("Input graph is not strongly connected")

    g_hash = None
    canon_order_lookup = dict()

    orbits = defaultdict(list)

    for n in g.nodes:
        (n_hash, _, order_lookup) = _ordered_edges_hash(g, n, string_hash_fun=string_hash_fun)

        if hash_nodes:
            orbits[n_hash].append(n)

        if g_hash is None or n_hash < g_hash:
            g_hash = n_hash
            canon_order_lookup = order_lookup

    if not hash_nodes:
        return g_hash
    else:
        orbit_partition = list(orbits.values())
        orbit_mapping = _orbit_indices(canon_order_lookup, orbit_partition)

        node_hashes = dict()
        for n in g.nodes:
            node_hashes[n] = string_hash_fun(encode((orbit_mapping[n], g_hash)))

        return (g_hash, node_hashes)